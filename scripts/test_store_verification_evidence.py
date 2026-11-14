"""Regression tests for scripts/store_verification_evidence.py (issue #366).

Offline and hermetic: every test injects a ``put`` (the seam
``evidence_store.store_files`` already exposes) and a ``preflight``, so no
network, no broker and no ``klt`` are needed. The point under test is the
fail-closed contract -- that a failure installs *nothing* -- plus the per-file
exclusion that keeps signoff-cited artefacts committed.
"""

import argparse
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sve = _load("store_verification_evidence", "scripts/store_verification_evidence.py")
chk = _load("check_artifact_manifests", "scripts/check_artifact_manifests.py")
evidence_store = sve.evidence_store
StoreError = sve.StoreError

REPO = "owner/repo"
EXPERIMENT = "post-layout-pvt"
RID = "20261015-011505-32db02a"
#: The signoff-cited artefact in the real record this issue measured: it sits
#: beside ~8 MiB of uncited siblings and must stay committed (#375).
CITED = "sta-corners.json"
ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}


def fake_put(files, repo_root):
    """Stand in for ``evidence_store.put_files``: same ``(manifest, empty)``
    contract, no broker. Mirrors its zero-byte rule (empty files are not
    storable objects, so their names are returned instead)."""
    entries, empty = [], []
    for path, name in files:
        sha, size = evidence_store.sha256_file(Path(path))
        if size == 0:
            empty.append(name)
            continue
        entries.append({
            "sha256": sha, "size": size, "kind": "evidence",
            "producer": {"tool": "klt", "version": "0.7.0", "loom.repo": REPO,
                         "commit": None},
            "uri": f"artifact:evidence/owner__repo/{sha[:2]}/{sha}", "name": name})
    if not entries:
        raise StoreError("nothing to store: every staged file is empty")
    return {"schema_version": 1,
            "entries": sorted(entries, key=lambda e: e["name"])}, sorted(empty)


def refusing_put(files, repo_root):
    raise StoreError("artifact broker refused this caller (HTTP 403)")


def no_broker_preflight(repo_root):
    raise StoreError("no artifact broker configured ($KLT_ARTIFACT_BROKER is unset)")


class Base(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name) / "repo"
        self.root.mkdir()
        self.git("init", "-q", "-b", "main")
        # The staging tree must be git-ignored; evidence_store refuses one
        # inside the tracked tree, and this helper keeps that rule.
        (self.root / ".gitignore").write_text("sim/.work/\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "c")
        self.stage = self.root / "sim" / ".work" / ".stage" / EXPERIMENT / RID
        self.stage.mkdir(parents=True)
        self.record = sve.record_path(self.root, EXPERIMENT, RID)
        self.record.parent.mkdir(parents=True)
        self.record.write_text("# record\n\nLinks: none.\n", encoding="utf-8")
        self.manifest = evidence_store.manifest_path(self.root, EXPERIMENT, RID)

    def git(self, *a):
        return subprocess.run(["git", "-C", str(self.root), *a], env=ENV, check=True,
                              capture_output=True).stdout.decode()

    def stage_file(self, rel, data=b"bytes"):
        p = self.stage / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def args(self, **kw):
        base = dict(experiment=EXPERIMENT, record_id=RID, stage_dir=str(self.stage),
                    exclude=[], record=None, repo_root=str(self.root))
        base.update(kw)
        return argparse.Namespace(**base)

    def run_ok(self, **kw):
        return sve.run(self.args(**kw), put=fake_put, preflight=lambda root: None)

    def manifests_on_disk(self):
        d = self.root / "manifests" / "artifacts"
        return sorted(p.name for p in d.glob("*")) if d.is_dir() else []

    def assert_nothing_installed(self, before):
        self.assertEqual(self.manifests_on_disk(), [],
                         "a manifest was installed on a failure path")
        self.assertEqual(self.record.read_text(), before,
                         "the record was modified on a failure path")


class Stores(Base):
    def test_installs_exactly_one_manifest_naming_the_tree_paths(self):
        self.stage_file("extract-defnames-defpins-output.json", b"{}" * 100)
        self.stage_file("logs/icarus.log", b"transcript\n")
        mpath = self.run_ok()
        self.assertEqual(mpath, self.manifest)
        self.assertEqual(self.manifests_on_disk(),
                         [f"{EXPERIMENT}-{RID}.manifest.json"])
        manifest = json.loads(self.manifest.read_text())
        self.assertEqual([e["name"] for e in manifest["entries"]], [
            f"verification/records/{EXPERIMENT}/artifacts/{RID}/"
            "extract-defnames-defpins-output.json",
            f"verification/records/{EXPERIMENT}/artifacts/{RID}/logs/icarus.log"])

    def test_entry_names_are_canonical_to_the_checker(self):
        # The writer and the CI checker must agree on the root, or a stored
        # record would be refused by the very check that guards it.
        self.stage_file("a.json")
        self.run_ok()
        manifest = json.loads(self.manifest.read_text())
        self.assertEqual(chk.manifest_problems(manifest), [])
        for e in manifest["entries"]:
            self.assertTrue(chk.canonical_name(e["name"]), e["name"])

    def test_appends_to_the_hand_authored_record_without_rewriting_it(self):
        self.stage_file("a.json")
        before = self.record.read_text()
        self.run_ok()
        after = self.record.read_text()
        self.assertTrue(after.startswith(before), "the record was rewritten, not appended")
        self.assertIn(sve.SECTION_HEADING, after)
        self.assertIn("klt artifact verify", after)
        self.assertIn(f"{EXPERIMENT}-{RID}.manifest.json", after)

    def test_zero_byte_file_is_listed_not_stored(self):
        self.stage_file("a.json")
        self.stage_file("empty.log", b"")
        self.run_ok()
        manifest = json.loads(self.manifest.read_text())
        self.assertEqual([e["name"].rsplit("/", 1)[-1] for e in manifest["entries"]],
                         ["a.json"])
        self.assertIn("empty, not stored", self.record.read_text())


class Exclusion(Base):
    def test_cited_file_is_neither_stored_nor_removed(self):
        self.stage_file("extract-defnames-defpins-output.json", b"big" * 100)
        cited = self.stage_file(CITED, b"cited bytes")
        self.run_ok(exclude=[CITED])
        names = [e["name"].rsplit("/", 1)[-1]
                 for e in json.loads(self.manifest.read_text())["entries"]]
        self.assertEqual(names, ["extract-defnames-defpins-output.json"])
        self.assertNotIn(CITED, names)
        # left in the staging tree for the caller to commit into the record dir
        self.assertTrue(cited.is_file())
        self.assertEqual(cited.read_bytes(), b"cited bytes")

    def test_absolute_exclude_path_works(self):
        self.stage_file("a.json")
        cited = self.stage_file(CITED)
        self.run_ok(exclude=[str(cited)])
        self.assertEqual(len(json.loads(self.manifest.read_text())["entries"]), 1)

    def test_excluding_a_nested_file_works(self):
        self.stage_file("a.json")
        self.stage_file("reports/erc-supply-report.json")
        self.run_ok(exclude=["reports/erc-supply-report.json"])
        self.assertEqual([e["name"].rsplit("/", 1)[-1]
                          for e in json.loads(self.manifest.read_text())["entries"]],
                         ["a.json"])

    def test_typod_exclude_is_refused_before_anything_is_stored(self):
        # A silently-ignored exclusion would store a signoff-cited artefact
        # and strip it from the tree. Fail closed instead.
        self.stage_file("a.json")
        with self.assertRaises(StoreError) as cm:
            self.run_ok(exclude=["sta-corner.json"])  # missing the 's'
        self.assertIn("not a file in the staging directory", str(cm.exception))
        self.assertEqual(self.manifests_on_disk(), [])

    def test_excluding_everything_stores_nothing_and_installs_nothing(self):
        self.stage_file(CITED)
        with self.assertRaises(StoreError) as cm:
            self.run_ok(exclude=[CITED])
        self.assertIn("nothing staged to store", str(cm.exception))
        self.assertEqual(self.manifests_on_disk(), [])


class FailsClosed(Base):
    def test_absent_broker_installs_nothing(self):
        self.stage_file("a.json")
        before = self.record.read_text()
        with self.assertRaises(StoreError) as cm:
            sve.run(self.args(), put=fake_put, preflight=no_broker_preflight)
        self.assertIn("no artifact broker configured", str(cm.exception))
        self.assert_nothing_installed(before)

    def test_failing_put_installs_nothing(self):
        self.stage_file("a.json")
        before = self.record.read_text()
        with self.assertRaises(StoreError) as cm:
            sve.run(self.args(), put=refusing_put, preflight=lambda root: None)
        self.assertIn("refused this caller", str(cm.exception))
        self.assert_nothing_installed(before)

    def test_existing_manifest_is_never_overwritten(self):
        self.stage_file("a.json")
        self.manifest.parent.mkdir(parents=True, exist_ok=True)
        self.manifest.write_text('{"schema_version": 1, "entries": []}\n')
        before = self.record.read_text()
        with self.assertRaises(StoreError) as cm:
            self.run_ok()
        self.assertIn("refusing to overwrite evidence", str(cm.exception))
        self.assertEqual(self.record.read_text(), before)
        self.assertEqual(self.manifest.read_text(),
                         '{"schema_version": 1, "entries": []}\n')

    def test_missing_record_is_refused(self):
        self.stage_file("a.json")
        self.record.unlink()
        with self.assertRaises(StoreError) as cm:
            self.run_ok()
        self.assertIn("write the record first", str(cm.exception))
        self.assertEqual(self.manifests_on_disk(), [])

    def test_record_already_stored_is_refused(self):
        self.stage_file("a.json")
        self.run_ok()
        self.manifest.unlink()  # only the record's section remains
        with self.assertRaises(StoreError) as cm:
            self.run_ok()
        self.assertIn("evidence is stored already", str(cm.exception))
        self.assertEqual(self.manifests_on_disk(), [])

    def test_staging_inside_the_tracked_tree_is_refused(self):
        tracked = self.root / "verification" / "records" / EXPERIMENT / "artifacts" / RID
        tracked.mkdir(parents=True)
        (tracked / "a.json").write_bytes(b"x")
        before = self.record.read_text()
        with self.assertRaises(StoreError) as cm:
            sve.run(self.args(stage_dir=str(tracked)), put=fake_put,
                    preflight=lambda root: None)
        self.assertIn("inside the tracked tree", str(cm.exception))
        self.assert_nothing_installed(before)

    def test_missing_stage_dir_is_refused(self):
        with self.assertRaises(StoreError) as cm:
            sve.run(self.args(stage_dir=str(self.root / "nope")), put=fake_put,
                    preflight=lambda root: None)
        self.assertIn("does not exist", str(cm.exception))

    def test_bad_experiment_slug_is_refused_before_preflight(self):
        self.stage_file("a.json")
        called = []
        with self.assertRaises(ValueError):
            sve.run(self.args(experiment="../etc"), put=fake_put,
                    preflight=lambda root: called.append(root))
        self.assertEqual(called, [], "preflight ran despite an invalid slug")

    def test_symlink_in_the_stage_is_refused(self):
        self.stage_file("a.json")
        os.symlink(self.root / "verification", self.stage / "link")
        before = self.record.read_text()
        with self.assertRaises(StoreError) as cm:
            self.run_ok()
        self.assertIn("symlink", str(cm.exception))
        self.assert_nothing_installed(before)


class NoByteFallback(Base):
    def test_no_option_offers_to_commit_the_bytes(self):
        # DR-0008 point 3 and this issue's acceptance criteria: the helper
        # must expose no escape hatch that writes the bytes into git.
        opts = []
        for action in sve.build_parser()._actions:
            opts += list(action.option_strings)
        joined = " ".join(opts).lower()
        for banned in ("commit", "keep-bytes", "fallback", "no-store", "in-tree",
                       "local", "force", "legacy"):
            self.assertNotIn(banned, joined, f"a --*{banned}* option exists: {opts}")

    def test_no_environment_variable_switches_it_off(self):
        src = (ROOT / "scripts" / "store_verification_evidence.py").read_text()
        self.assertNotIn("environ.get", src)
        self.assertNotIn("getenv", src)

    def test_cli_reports_exit_1_and_installs_nothing_when_the_broker_is_absent(self):
        self.stage_file("a.json")
        before = self.record.read_text()
        # This exercises the real preflight, so make the absence explicit
        # rather than inheriting whatever the host has set.
        prior = os.environ.pop(evidence_store.ENV_BROKER, None)
        if prior is not None:
            self.addCleanup(os.environ.__setitem__, evidence_store.ENV_BROKER, prior)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = sve.main(["--experiment", EXPERIMENT, "--record-id", RID,
                           "--stage-dir", str(self.stage),
                           "--repo-root", str(self.root)])
        self.assertEqual(rc, sve.EXIT_STORE)
        self.assertIn("nothing was written under manifests/", err.getvalue())
        self.assert_nothing_installed(before)


class NamePrefix(unittest.TestCase):
    def test_prefix_is_exactly_the_in_tree_path(self):
        self.assertEqual(sve.name_prefix(EXPERIMENT, RID),
                         f"verification/records/{EXPERIMENT}/artifacts/{RID}")

    def test_prefix_sits_under_a_checker_evidence_root(self):
        self.assertTrue(sve.name_prefix(EXPERIMENT, RID).startswith(chk.EVIDENCE_ROOTS))


if __name__ == "__main__":
    unittest.main()
