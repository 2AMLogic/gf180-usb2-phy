#!/usr/bin/env python3
"""Unit tests for the evidence-record linter (``sim/harness/evidence_lint.py``).

    python3 -m unittest discover -s sim/tests -v

Companion to ``test_harness.py`` in this directory (same in-process,
no-PDK-required style) and to ``verification/test_check_records.py``
(same intent -- one executable negative case per violation class the
linter's docstring names -- applied here to the sibling ``sim/`` checker,
which previously had none). See issue that filed this: the corner-id-grammar
and log-count-vs-predecessor paths were entirely unexercised.

Most checks below build an in-memory-ish evidence tree under a plain temp
directory (no git needed -- ``list_evidence_paths`` falls back to a
filesystem walk when the root is not a git checkout) and call the linter's
functions directly. Only the append-only check is inherently git-shaped, so
that gets its own fixture with a real temp repo. A final smoke test drives
the packaged CLI end-to-end (``sim/check_records.py`` as a subprocess)
against a throwaway repo, mirroring ``verification/test_check_records.py``'s
"exercise the shipped entry point" methodology.

``EndToEndCliTests`` copies ``verification/check_records.py`` into its
throwaway fixture repo alongside ``sim/``: per issue #16,
``sim/harness/evidence_lint.py`` imports its record-id grammar, field-block
parser, and git merge-base plumbing from ``verification/check_records.py``
rather than carrying its own copies, so a standalone fixture repo needs both
directories to run the packaged CLI at all.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SIM_DIR.parent
sys.path.insert(0, str(SIM_DIR))

from harness import evidence_lint as lint  # noqa: E402

CHECK_RECORDS_PY = SIM_DIR / "check_records.py"
VERIFICATION_CHECK_RECORDS_PY = REPO_ROOT / "verification" / "check_records.py"
HARNESS_DIR = SIM_DIR / "harness"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-c",
            "user.name=evidence-lint-selftest",
            "-c",
            "user.email=selftest@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}: {result.stderr.strip()}")
    return result.stdout


def make_record_text(
    record_id: str,
    *,
    supersedes: str = "(none)",
    omit_field: str | None = None,
    extra_lines: str = "",
) -> str:
    """A record body satisfying ``sim/README.md``'s nine required fields."""
    fields = [
        ("Record ID", record_id),
        ("Claim", "fixture claim, not a real spec claim"),
        ("Netlist provenance", "schematic (`sim/demo/testbench/demo.spice`)"),
        ("Corner matrix run", "fixture corner matrix"),
        ("Statistical convention", "N/A (fixture)"),
        ("Result", "**Overall: PASS** (fixture)" + extra_lines),
        ("Links", "Testbench: `sim/demo/testbench/demo.spice`"),
        ("Timestamp / author", "2026-01-01T00:00:00Z, selftest"),
        ("Supersedes", supersedes),
    ]
    bullets = "\n".join(f"- **{name}**: {value}" for name, value in fields if name != omit_field)
    return f"# Record {record_id}\n\n{bullets}\n"


def write_record(root: Path, slug: str, record_id: str, **kwargs) -> Path:
    path = root / "sim" / slug / lint.RECORDS_DIR / f"{record_id}{lint.RECORD_SUFFIX}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(make_record_text(record_id, **kwargs), encoding="utf-8")
    return path


def write_snapshot(root: Path, slug: str, record_id: str) -> Path:
    path = root / "sim" / slug / lint.SNAPSHOT_DIR / f"{record_id}{lint.SNAPSHOT_SUFFIX}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("* fixture netlist\n", encoding="utf-8")
    return path


def write_corner_log(root: Path, slug: str, record_id: str, corner_id: str) -> Path:
    path = root / "sim" / slug / lint.CORNERS_DIR / record_id / f"{corner_id}{lint.LOG_SUFFIX}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("* fixture log\n", encoding="utf-8")
    return path


def full_fixture(root: Path, slug: str, record_id: str, n_logs: int = 1, **kwargs) -> Path:
    """A complete, passing evidence tree for one record: record + snapshot +
    ``n_logs`` corner logs (default corner ids, always valid grammar)."""
    path = write_record(root, slug, record_id, **kwargs)
    write_snapshot(root, slug, record_id)
    corner_ids = ["tt_27c_3.30v", "ff_-40c_2.97v", "ss_125c_3.63v", "fs_27c_nosupply"][:n_logs]
    for corner_id in corner_ids:
        write_corner_log(root, slug, record_id, corner_id)
    return path


def check(root: Path) -> list:
    """Run the non-git checks (record/experiment validation) and return the
    problem list -- what ``main()`` prints, minus the append-only stage."""
    paths, _source = lint.list_evidence_paths(root)
    experiments = lint.collect_experiments(paths)
    return lint.check_experiments(root, experiments)


def problem_paths(problems) -> list[str]:
    return [str(problem) for problem in problems]


class RecordIdGrammarTests(unittest.TestCase):
    def test_valid_id(self):
        self.assertIsNone(lint.validate_record_id("20260315-093000-abc1234"))

    def test_malformed_id(self):
        reason = lint.validate_record_id("not-a-record-id")
        self.assertIsNotNone(reason)
        self.assertIn("not a <YYYYMMDD>-<HHMMSS>-<short-git-sha>", reason)

    def test_impossible_date_rejected(self):
        # Regex-shaped but not a real calendar date/time -- only the sim-side
        # checker validates this (verification/check_records.py's grammar
        # check is a bare regex match with no strptime step), so this
        # exercises a code path that had zero coverage before this file.
        reason = lint.validate_record_id("20260230-250000-abc1234")
        self.assertIsNotNone(reason)
        self.assertIn("impossible date/time", reason)


class CornerIdGrammarTests(unittest.TestCase):
    def test_simple_valid(self):
        self.assertIsNone(lint.parse_corner_id("tt_27c_3.30v"))

    def test_negative_temperature_valid(self):
        self.assertIsNone(lint.parse_corner_id("ff_-40c_2.97v"))

    def test_multi_token_process_valid(self):
        self.assertIsNone(lint.parse_corner_id("bjt_ff_27c_nosupply"))
        self.assertIsNone(lint.parse_corner_id("res_typical_-40c_2.97v"))

    def test_node_prefixed_supply_valid(self):
        self.assertIsNone(lint.parse_corner_id("tt_27c_nwell2p97v"))

    def test_nosupply_literal_valid(self):
        self.assertIsNone(lint.parse_corner_id("tt_27c_nosupply"))

    def test_too_few_parts_invalid(self):
        reason = lint.parse_corner_id("tt_27c")
        self.assertIsNotNone(reason)
        self.assertIn("does not parse", reason)

    def test_uppercase_process_invalid(self):
        reason = lint.parse_corner_id("TT_27c_3.30v")
        self.assertIsNotNone(reason)
        self.assertIn("process field", reason)

    def test_non_numeric_temperature_invalid(self):
        reason = lint.parse_corner_id("tt_room_3.30v")
        self.assertIsNotNone(reason)
        self.assertIn("temperature field", reason)

    def test_malformed_supply_invalid(self):
        reason = lint.parse_corner_id("tt_27c_threevolts")
        self.assertIsNotNone(reason)
        self.assertIn("supply field", reason)


class ParseFieldsTests(unittest.TestCase):
    def test_continuation_lines_join_into_value(self):
        text = "- **Result**: line one\n  line two\n  line three\n- **Links**: x\n"
        fields, duplicates = lint.parse_fields(text)
        self.assertEqual([], duplicates)
        self.assertEqual("line one\nline two\nline three", fields["Result"].value)

    def test_duplicate_field_detected(self):
        text = "- **Claim**: first\n- **Claim**: second\n"
        fields, duplicates = lint.parse_fields(text)
        self.assertEqual(["Claim"], duplicates)
        # First occurrence wins in the map -- consistent with check_record's
        # "field appears more than once" problem being reported alongside
        # (not instead of) the normal required-field presence check.
        self.assertEqual("first", fields["Claim"].value)


class CheckRecordTests(unittest.TestCase):
    def test_complete_record_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full_fixture(root, "demo", "20260101-000000-abc1234")
            self.assertEqual([], check(root))

    def test_missing_required_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full_fixture(root, "demo", "20260101-000000-abc1234", omit_field="Claim")
            problems = problem_paths(check(root))
            self.assertTrue(any("missing required field **Claim**" in p for p in problems), problems)

    def test_record_id_disagrees_with_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_record(root, "demo", "20260101-000000-abc1234")
            # Overwrite with a body whose Record ID field names a different id.
            path.write_text(make_record_text("20260102-000000-abc1234"), encoding="utf-8")
            write_snapshot(root, "demo", "20260101-000000-abc1234")
            write_corner_log(root, "demo", "20260101-000000-abc1234", "tt_27c_3.30v")
            problems = problem_paths(check(root))
            self.assertTrue(any("filename says" in p for p in problems), problems)

    def test_missing_netlist_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_record(root, "demo", "20260101-000000-abc1234")
            write_corner_log(root, "demo", "20260101-000000-abc1234", "tt_27c_3.30v")
            problems = problem_paths(check(root))
            self.assertTrue(any("no frozen netlist" in p for p in problems), problems)

    def test_missing_corner_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_record(root, "demo", "20260101-000000-abc1234")
            write_snapshot(root, "demo", "20260101-000000-abc1234")
            problems = problem_paths(check(root))
            self.assertTrue(any("no raw per-corner logs" in p for p in problems), problems)

    def test_bad_corner_id_grammar_in_log_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_record(root, "demo", "20260101-000000-abc1234")
            write_snapshot(root, "demo", "20260101-000000-abc1234")
            # Fewer than the three underscore-separated parts the grammar
            # requires (<process>_<temp>c_<supply>).
            write_corner_log(root, "demo", "20260101-000000-abc1234", "bad_corner")
            problems = problem_paths(check(root))
            self.assertTrue(any("does not parse" in p for p in problems), problems)

    def test_dangling_supersedes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full_fixture(
                root,
                "demo",
                "20260102-000000-abc1234",
                supersedes="20260101-000000-deadbee",
            )
            problems = problem_paths(check(root))
            self.assertTrue(any("which has no record at" in p for p in problems), problems)

    def test_self_referencing_supersedes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full_fixture(
                root,
                "demo",
                "20260101-000000-abc1234",
                supersedes="20260101-000000-abc1234",
            )
            problems = problem_paths(check(root))
            self.assertTrue(any("points at this record itself" in p for p in problems), problems)

    def test_orphan_snapshot_with_no_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_snapshot(root, "demo", "20260101-000000-abc1234")
            problems = problem_paths(check(root))
            self.assertTrue(any("orphan: no summary record" in p for p in problems), problems)

    def test_orphan_corner_dir_with_no_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_corner_log(root, "demo", "20260101-000000-abc1234", "tt_27c_3.30v")
            problems = problem_paths(check(root))
            self.assertTrue(any("orphan: no summary record" in p for p in problems), problems)


class LogCountVsPredecessorTests(unittest.TestCase):
    """The 'current head must carry >= its predecessor's logs' rule, and the
    exemption for a record that is itself superseded -- entirely uncovered
    before this file existed."""

    def test_head_with_fewer_logs_than_predecessor_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full_fixture(root, "demo", "20260101-000000-abc1234", n_logs=3)
            full_fixture(
                root,
                "demo",
                "20260102-000000-abc1234",
                n_logs=1,
                supersedes="20260101-000000-abc1234",
            )
            problems = problem_paths(check(root))
            self.assertTrue(any("fewer than its" in p for p in problems), problems)

    def test_head_with_at_least_as_many_logs_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full_fixture(root, "demo", "20260101-000000-abc1234", n_logs=1)
            full_fixture(
                root,
                "demo",
                "20260102-000000-abc1234",
                n_logs=3,
                supersedes="20260101-000000-abc1234",
            )
            self.assertEqual([], check(root))

    def test_superseded_record_exempt_from_the_rule(self):
        # Chain: A (1 log) <- B (3 logs, supersedes A) <- C (1 log, supersedes B).
        # B is no longer the head, so B is never re-checked against A even
        # though a head-vs-predecessor comparison would normally apply to it.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full_fixture(root, "demo", "20260101-000000-abc1234", n_logs=1)
            full_fixture(
                root,
                "demo",
                "20260102-000000-abc1234",
                n_logs=3,
                supersedes="20260101-000000-abc1234",
            )
            full_fixture(
                root,
                "demo",
                "20260103-000000-abc1234",
                n_logs=3,
                supersedes="20260102-000000-abc1234",
            )
            self.assertEqual([], check(root))


class AppendOnlyTests(unittest.TestCase):
    """Git-shaped, unlike the rest of this file -- needs a real repo."""

    def _base_repo(self, root: Path) -> None:
        full_fixture(root, "demo", "20260101-000000-abc1234")
        _git(root, "init", "--quiet")
        _git(root, "add", "-A")
        _git(root, "commit", "--quiet", "-m", "fixture: initial record")
        _git(root, "update-ref", "refs/heads/fixture-base", "HEAD")

    def test_editing_a_committed_record_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._base_repo(root)
            path = root / "sim" / "demo" / lint.RECORDS_DIR / "20260101-000000-abc1234.md"
            path.write_text(path.read_text() + "\nedited after commit\n", encoding="utf-8")
            problems, skip_reason = lint.check_append_only(root, "refs/heads/fixture-base")
            self.assertIsNone(skip_reason)
            self.assertTrue(any("modified" in str(p) for p in problems), problems)

    def test_deleting_a_committed_record_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._base_repo(root)
            (root / "sim" / "demo" / lint.RECORDS_DIR / "20260101-000000-abc1234.md").unlink()
            problems, skip_reason = lint.check_append_only(root, "refs/heads/fixture-base")
            self.assertIsNone(skip_reason)
            self.assertTrue(any("deleted" in str(p) for p in problems), problems)

    def test_adding_a_new_record_is_not_a_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._base_repo(root)
            full_fixture(root, "demo", "20260102-000000-abc1234")
            problems, skip_reason = lint.check_append_only(root, "refs/heads/fixture-base")
            self.assertIsNone(skip_reason)
            self.assertEqual([], problems)

    def test_unresolvable_base_ref_is_skipped_not_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._base_repo(root)
            problems, skip_reason = lint.check_append_only(root, "refs/heads/no-such-branch")
            self.assertEqual([], problems)
            self.assertIsNotNone(skip_reason)


class EndToEndCliTests(unittest.TestCase):
    """Drive the packaged CLI (sim/check_records.py) as a subprocess against
    a throwaway fixture repo -- the 'shipped entry point' check, mirroring
    verification/test_check_records.py's methodology."""

    def _fixture_repo(self, root: Path, *, git_init: bool = True) -> None:
        (root / "sim").mkdir()
        (root / "verification").mkdir()
        import shutil

        shutil.copyfile(CHECK_RECORDS_PY, root / "sim" / "check_records.py")
        shutil.copytree(HARNESS_DIR, root / "sim" / "harness")
        shutil.copyfile(
            VERIFICATION_CHECK_RECORDS_PY, root / "verification" / "check_records.py"
        )
        full_fixture(root, "demo", "20260101-000000-abc1234")
        if git_init:
            _git(root, "init", "--quiet")
            _git(root, "add", "-A")
            _git(root, "commit", "--quiet", "-m", "fixture: initial record")

    def _run(self, root: Path, *extra_args: str) -> tuple[int, str]:
        result = subprocess.run(
            [sys.executable, str(root / "sim" / "check_records.py"), *extra_args],
            cwd=root,
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout + result.stderr

    def test_valid_fixture_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture_repo(root)
            exit_code, output = self._run(root)
            self.assertEqual(0, exit_code, output)

    def test_broken_fixture_fails_with_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # No git init here: list_evidence_paths falls back to a plain
            # filesystem walk, so a log removed from disk is actually absent
            # from what the CLI sees (a git-tracked fixture would keep
            # reporting the pre-deletion `git ls-files` entry until the
            # deletion itself is staged, which isn't what this case tests).
            self._fixture_repo(root, git_init=False)
            corners_dir = root / "sim" / "demo" / lint.CORNERS_DIR / "20260101-000000-abc1234"
            for log in corners_dir.glob("*.log"):
                log.unlink()
            exit_code, output = self._run(root)
            self.assertEqual(1, exit_code, output)
            self.assertIn("no raw per-corner logs", output)


if __name__ == "__main__":
    unittest.main()
