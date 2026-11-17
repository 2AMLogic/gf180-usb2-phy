#!/usr/bin/env python3
"""Self-test for `scripts/check_signoff_report.py`.

The parity check is the only thing standing between "CI re-runs the
manifest so it cannot rot" as a documented intention and as an enforced
property: a checker that silently stops catching a drifted report, an
error render, or a "stale graders don't count as failure" misreading is
worse than no checker. Each behavior the checker's contract names gets an
executable test here.

Method: build a throwaway fixture repo in a temp dir, copy the *real*
`check_signoff_report.py` into its `scripts/` directory (the checker
resolves its repo root and default manifest/report paths from `__file__`),
commit a fixture manifest + committed report, and put a **stub `klt`** on
the fixture's `$PATH` that replays canned renders. Nothing is
monkeypatched, and no real `klt`, PDK, or network is involved -- the stub
exists because this test exercises the *checker's* contract, not `klt
signoff`'s grading (the real `klt` exercises the real checker in
`npm run check:ci` and every CI run). The stub's behavior is parameterized
by its own name.

Zero dependencies beyond the Python 3 standard library.

Runs both ways: directly (`python3 scripts/test_check_signoff_report.py`,
an explicit `npm run lint` step) and under the scripts/ directory sweep
(`python3 -m unittest discover -s scripts -t scripts -p 'test_*.py'`,
which collects these tests with everything else).
Exit codes: 0 all tests pass, non-zero at least one did not.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CHECKER = SCRIPT_DIR / "check_signoff_report.py"
KLT_RESOLVE = SCRIPT_DIR / "klt_resolve.py"

#: The fixture repo's klt pin. `BASE_REPORT`'s `build.version` is
#: `0.5.0+gfixture` -- same release, a PEP 440 local segment apart -- so a
#: stub replaying BASE_REPORT passes the checker's version gate while the
#: mismatch tests below move both sides together.
FIXTURE_PIN = "0.5.0"

#: A minimal, well-formed tier-report shape for the fixture: every field
#: the real checker reads (tier summary block, one T1 item, build block).
#: The stub `klt` replays variants of this; the fixture's committed report
#: starts as the `accepted` variant.
BASE_REPORT = {
    "schema_version": 1,
    "block": "fixture-block",
    "kind": "digital",
    "tier": None,
    "t1_item_count": 2,
    "t1_met_count": 1,
    "build_t1_item_count": 2,
    "source_doc": "docs/design-evidence-tiers.md",
    "source_doc_content_hash": "sha256:" + "a" * 64,
    "build": {
        "version": "0.5.0+gfixture",
        "package_version": "0.5.0",
        "git_commit": "fixturecommit" * 4,
        "git_tag": None,
        "dirty": False,
        "is_release": False,
    },
    "items": [
        {
            "tier": "T1",
            "id": 3,
            "title": "DRC clean",
            "partition": "digital",
            "status": "met",
            "reason": None,
            "graded_by_build": True,
            "text": "fixture item text",
            "notes": [],
            "citation": {
                "file": "verification/records/fixture-drc/artifacts/f/drc-report.json",
                "command": None,
                "kind": "drc",
                "check_status": "clean",
                "content_hash": "sha256:" + "b" * 64,
                "input_verified": True,
                "exit_status": 0,
                "coverage": {
                    "layers_in_stream_without_rules": [],
                    "rules_skipped": [],
                    "deck_scope": ["7.13 Metaln"],
                },
            },
        },
        {
            "tier": "T1",
            "id": 1,
            "title": "Design sources",
            "partition": "digital",
            "status": "unmet",
            "reason": "no_evidence",
            "graded_by_build": True,
            "text": "fixture item text",
            "notes": [],
            "citation": None,
        },
    ],
}


def _write_stub(bin_dir: Path, name: str, exit_code: int, payload: dict | None) -> None:
    stub = bin_dir / name
    payload_json = json.dumps(payload)
    stub.write_text(
        "#!/bin/sh\n"
        f"cat <<'EOF'\n{payload_json}\nEOF\n"
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def build_fixture_repo(tmp: Path) -> tuple[Path, Path]:
    repo = tmp / "fixture-repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy(CHECKER, repo / "scripts" / "check_signoff_report.py")
    # The checker now imports its klt resolution/version gate from a sibling
    # module and reads the pin from setup-env.sh, so the fixture carries
    # both -- the pin deliberately matches BASE_REPORT's build.version.
    shutil.copy(KLT_RESOLVE, repo / "scripts" / "klt_resolve.py")
    (repo / "scripts" / "setup-env.sh").write_text(
        "#!/bin/sh\n"
        f'KLT_VERSION="{FIXTURE_PIN}"\n'
        'VOLARE_PDK_FAMILY="gf180mcu"\n',
        encoding="utf-8",
    )
    (repo / "manifests").mkdir()
    manifest = {
        "block": "fixture-block",
        "kind": "digital",
        "evidence": {
            "3": {
                "file": "verification/records/fixture-drc/artifacts/f/drc-report.json",
                "content_hash": "sha256:" + "b" * 64,
            }
        },
    }
    (repo / "manifests" / "gf180-usb2-phy.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (repo / "manifests" / "t1-signoff-report.json").write_text(
        json.dumps(BASE_REPORT), encoding="utf-8"
    )
    bin_dir = repo / "stub-bin"
    bin_dir.mkdir()
    # `klt` (the name the checker invokes) replays the accepted render.
    _write_stub(bin_dir, "klt", 3, BASE_REPORT)
    return repo, bin_dir


def run_checker(repo: Path, bin_dir: Path) -> subprocess.CompletedProcess[str]:
    """Run the fixture checker against its stub klt via the *explicit*
    `--klt` override. The default resolution (the interpreter's own
    `python -m klayout_tools.cli`) is unit-tested in
    `test_klt_resolve.py`; driving it here would run whatever klayout_tools
    the host python can import -- 0.9.3.dev on a dev box -- right over the
    stub, so every end-to-end case pins the stub explicitly instead."""
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    return subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "check_signoff_report.py"),
            "--klt",
            str(bin_dir / "klt"),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


class TestCheckSignoffReport(unittest.TestCase):
    """One test per behavior of the checker's contract; each builds a fresh
    fixture repo so cases stay isolated."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="signoff-report-selftest-")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_parity_accepted(self) -> None:
        """An exit-3 render equal to the committed report passes (sees OK)."""
        repo, bin_dir = build_fixture_repo(self.tmp)
        result = run_checker(repo, bin_dir)
        self.assertEqual(
            0,
            result.returncode,
            f"parity render (exit 3, identical report) should exit 0; "
            f"stdout={result.stdout!r} stderr={result.stderr!r}",
        )
        self.assertIn("OK:", result.stdout)

    def test_exit_zero_render_accepted(self) -> None:
        """An exit-0 render (every T1 item met) is a clean run, not a failure."""
        repo, bin_dir = build_fixture_repo(self.tmp)
        accepted = json.loads(
            (repo / "manifests" / "t1-signoff-report.json").read_text(encoding="utf-8")
        )
        _write_stub(bin_dir, "klt", 0, accepted)
        result = run_checker(repo, bin_dir)
        self.assertEqual(
            0,
            result.returncode,
            f"exit-0 render should be accepted; stderr={result.stderr!r}",
        )

    def test_exit_one_render_rejected(self) -> None:
        """A klt error render (exit 1) fails the check, never parses as parity."""
        repo, bin_dir = build_fixture_repo(self.tmp)
        _write_stub(bin_dir, "klt", 1, {"error": {"message": "fixture error envelope"}})
        result = run_checker(repo, bin_dir)
        self.assertNotEqual(
            0,
            result.returncode,
            "an error render (klt exit 1) must FAIL the check, but it exited 0",
        )
        self.assertIn(
            "exited 1",
            result.stderr,
            f"the failure should name the unexpected klt exit, got: {result.stderr!r}",
        )

    def test_drifted_render_rejected(self) -> None:
        """A fresh render that diverges from the committed report FAILS -- the
        rot case this checker exists to catch (a hash-pin flips an item to
        `unmet`/`stale_evidence`, a tier boundary moves, a build drifts)."""
        repo, bin_dir = build_fixture_repo(self.tmp)
        drifted = json.loads(
            (repo / "manifests" / "t1-signoff-report.json").read_text(encoding="utf-8")
        )
        drifted["items"][0]["status"] = "unmet"
        drifted["items"][0]["reason"] = "stale_evidence"
        drifted["items"][0]["citation"]["coverage"]["rules_skipped"] = ["metaltop.width.1"]
        drifted["t1_met_count"] = 0
        _write_stub(bin_dir, "klt", 3, drifted)
        result = run_checker(repo, bin_dir)
        self.assertNotEqual(
            0,
            result.returncode,
            "a drifted fresh render must FAIL the check, but it exited 0",
        )
        self.assertIn(
            "stale_evidence",
            result.stderr,
            f"the drift failure should show the diverging fields, got: {result.stderr!r}",
        )

    def test_missing_report_rejected(self) -> None:
        """No committed report at all is a failure, not a silent pass."""
        repo, bin_dir = build_fixture_repo(self.tmp)
        (repo / "manifests" / "t1-signoff-report.json").unlink()
        result = run_checker(repo, bin_dir)
        self.assertNotEqual(
            0,
            result.returncode,
            "a missing committed report must FAIL the check, but it exited 0",
        )

    def test_version_gate_passes_on_the_pinned_klt(self) -> None:
        """A fresh render from the pinned klt (local segment aside) passes
        the version gate -- the stub replays BASE_REPORT, whose
        `build.version` `0.5.0+gfixture` matches the fixture pin 0.5.0."""
        repo, bin_dir = build_fixture_repo(self.tmp)
        result = run_checker(repo, bin_dir)
        self.assertEqual(
            0,
            result.returncode,
            f"pinned-klt render should pass the version gate; "
            f"stderr={result.stderr!r}",
        )

    def test_version_gate_rejects_an_unpinned_klt(self) -> None:
        """A render from any other klt -- here 9.9.9 -- must FAIL naming
        both versions, even when parity otherwise holds (issue #431: PR
        #430 froze a record whose pinned version contradicted its
        artifacts)."""
        repo, bin_dir = build_fixture_repo(self.tmp)
        rendered = json.loads(
            (repo / "manifests" / "t1-signoff-report.json").read_text(encoding="utf-8")
        )
        rendered["build"]["version"] = "9.9.9+gdeadbee"
        # Move the committed report with it, so *parity* holds and only the
        # version gate can catch the run.
        (repo / "manifests" / "t1-signoff-report.json").write_text(
            json.dumps(rendered), encoding="utf-8"
        )
        _write_stub(bin_dir, "klt", 3, rendered)
        result = run_checker(repo, bin_dir)
        self.assertNotEqual(
            0,
            result.returncode,
            "a render from an unpinned klt must FAIL the check, but it exited 0",
        )
        self.assertIn("9.9.9", result.stderr)
        self.assertIn(FIXTURE_PIN, result.stderr)

    def test_version_gate_rejects_a_report_with_no_version(self) -> None:
        """A render that carries no klt version at all cannot be gated, so
        it fails naming the pin rather than passing silently."""
        repo, bin_dir = build_fixture_repo(self.tmp)
        rendered = json.loads(
            (repo / "manifests" / "t1-signoff-report.json").read_text(encoding="utf-8")
        )
        del rendered["build"]
        (repo / "manifests" / "t1-signoff-report.json").write_text(
            json.dumps(rendered), encoding="utf-8"
        )
        _write_stub(bin_dir, "klt", 3, rendered)
        result = run_checker(repo, bin_dir)
        self.assertNotEqual(
            0,
            result.returncode,
            "a version-less render must FAIL the check, but it exited 0",
        )
        self.assertIn(FIXTURE_PIN, result.stderr)


if __name__ == "__main__":
    unittest.main()
