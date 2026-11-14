#!/usr/bin/env python3
"""Self-test for `scripts/check_decision_records.py` (issue #378).

A drift checker that silently stops catching drift is worse than none, so each
of the three properties gets both a pass case and a fail case, built in a
throwaway git repository (the checker reads `git ls-files`, not a glob) — the
same pattern as `scripts/test_check_artifact_manifests.py`. The live tree is
used for exactly one assertion: that it passes. Every *failure* mode is a
fixture, so the suite keeps meaning once the tree is conforming.

Usage:
    python3 scripts/test_check_decision_records.py
Exit codes: 0 all cases behave as specified, 1 otherwise.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_decision_records", ROOT / "scripts" / "check_decision_records.py")
cdr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cdr)

ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}

# The two paths the checker exempts from property (a). Named here rather than
# imported so that emptying or widening the constant in the checker shows up
# as a test failure instead of being silently mirrored.
EXEMPT_PAIR = (
    "0007-analog-statistical-rows.md",
    "0007-retire-bootstrap-harness-counter.md",
)


class Fixture(unittest.TestCase):
    """A throwaway repo with a `spec/` tree the fixtures mutate."""

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.git("init", "-q", "-b", "main")

    # --- plumbing ---------------------------------------------------------
    def git(self, *a):
        return subprocess.run(["git", "-C", str(self.root), *a], env=ENV,
                              check=True, capture_output=True).stdout.decode()

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def track(self):
        """Stage everything, so `git ls-files` sees it."""
        self.git("add", "-A")

    def record(self, name, h1_number=None):
        """Write `spec/decisions/<name>` with an H1 matching its prefix."""
        number = h1_number if h1_number is not None else name[:4]
        self.write(f"{cdr.RECORDS_DIR}/{name}",
                   f"# DR-{number} — fixture {name}\n\n- **Status**: Accepted\n")

    def index(self, *entries):
        """Write a `spec/usb2-device-phy.md` whose §12.1 lists `entries`.

        Each entry is a record filename, or an explicit (label, target) pair
        for the mislabelled / dangling-link fixtures.
        """
        rows = []
        for e in entries:
            label, target = (e[:4], e) if isinstance(e, str) else e
            rows.append(f"| [DR-{label}](decisions/{target}) | fixture "
                        f"decision. | fixture affects |")
        self.write(cdr.SPEC, "\n".join([
            "# Fixture spec", "", "## 12. Ratification", "",
            cdr.HEADING, "",
            "Preamble prose that the parser must skip.", "",
            "| Record | Decision | Affects |", "|---|---|---|",
            *rows, "", "## 13. References", "", "Tail prose.", "",
        ]) + "\n")

    def conforming(self):
        """A minimal tree that satisfies (a), (b) and (c)."""
        names = ["0001-first.md", "0002-second.md"]
        for n in names:
            self.record(n)
        self.index(*names)
        self.track()
        return names

    # --- assertions -------------------------------------------------------
    def check(self):
        return cdr.check(self.root)

    def assertPasses(self):
        self.assertEqual(self.check(), [])
        self.assertEqual(self.run_main(), 0)

    def assertFails(self, prop, *needles):
        errs = self.check()
        self.assertTrue(errs, "expected a violation, got none")
        hits = [e for e in errs if e.startswith(f"({prop})")]
        self.assertTrue(hits, f"no ({prop}) violation in {errs}")
        for needle in needles:
            self.assertTrue(any(needle in e for e in hits),
                            f"{needle!r} not in {hits}")
        self.assertEqual(self.run_main(), 1)
        return hits

    def run_main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            return cdr.main(["--root", str(self.root)])


class RealTree(unittest.TestCase):
    """The one assertion made against the live tree: it conforms."""

    def test_real_tree_passes(self):
        self.assertEqual(cdr.check(ROOT), [])

    def test_real_tree_exemption_is_exactly_the_known_pair(self):
        self.assertEqual(
            cdr.DUPLICATE_PREFIX_EXEMPTION,
            frozenset(f"{cdr.RECORDS_DIR}/{n}" for n in EXEMPT_PAIR))
        for path in cdr.DUPLICATE_PREFIX_EXEMPTION:
            self.assertTrue((ROOT / path).is_file(), f"{path} is gone")

    def test_real_tree_exemption_is_self_documenting(self):
        """Reading the checker must tell you what the exemption is and why."""
        src = (ROOT / "scripts" / "check_decision_records.py").read_text()
        head = src.split("RECORD_NAME_RE", 1)[0]
        for needle in (*EXEMPT_PAIR, "#381", "historical", "SINGLE-ENTRY"):
            self.assertIn(needle, head)


class Conforming(Fixture):
    def test_minimal_tree_passes(self):
        self.conforming()
        self.assertPasses()

    def test_no_tracked_records_is_a_run_error(self):
        self.index("0001-first.md")
        self.track()
        with self.assertRaises(cdr.CheckError):
            self.check()
        self.assertEqual(self.run_main(), 2)


class PropertyA(Fixture):
    """(a) the NNNN prefix is unique, modulo one single-entry exemption."""

    def test_unique_prefixes_pass(self):
        self.conforming()
        self.assertPasses()

    def test_duplicate_prefix_fails(self):
        names = ["0001-first.md", "0002-second.md", "0002-also-second.md"]
        for n in names:
            self.record(n)
        self.index(*names)
        self.track()
        self.assertFails("a", "DR-0002", "0002-second.md",
                         "0002-also-second.md")

    def test_the_exempt_0007_pair_passes(self):
        names = ["0001-first.md", *EXEMPT_PAIR]
        for n in names:
            self.record(n)
        self.index(*names)
        self.track()
        self.assertPasses()

    def test_a_third_0007_record_fails_with_the_exemption_in_place(self):
        """The exemption is single-entry: it is a set of two exact paths."""
        names = ["0001-first.md", *EXEMPT_PAIR, "0007-synthetic-third.md"]
        for n in names:
            self.record(n)
        self.index(*names)
        self.track()
        hits = self.assertFails("a", "DR-0007", "0007-synthetic-third.md")
        self.assertTrue(any("3 records" in h for h in hits), hits)

    def test_half_the_exempt_pair_plus_a_stranger_fails(self):
        """A near-miss set must not inherit the pair's exemption."""
        names = ["0001-first.md", EXEMPT_PAIR[0], "0007-impostor.md"]
        for n in names:
            self.record(n)
        self.index(*names)
        self.track()
        self.assertFails("a", "DR-0007", "0007-impostor.md")

    def test_a_collision_on_another_number_is_never_exempt(self):
        names = ["0003-a.md", "0003-b.md"]
        for n in names:
            self.record(n)
        self.index(*names)
        self.track()
        self.assertFails("a", "DR-0003")


class PropertyB(Fixture):
    """(b) each record's H1 DR-NNNN matches its own filename prefix."""

    def test_matching_h1_passes(self):
        self.conforming()
        self.assertPasses()

    def test_mismatched_h1_fails(self):
        self.record("0001-first.md")
        self.record("0002-second.md", h1_number="0009")
        self.index("0001-first.md", "0002-second.md")
        self.track()
        self.assertFails("b", "H1 says DR-0009", "filename says DR-0002")

    def test_missing_h1_fails(self):
        self.conforming()
        self.write(f"{cdr.RECORDS_DIR}/0002-second.md",
                   "Status: Accepted\n\n# DR-0002 — H1 is not the first line\n")
        self.track()
        self.assertFails("b", "is not a '# DR-NNNN ...' H1")

    def test_empty_record_fails(self):
        self.conforming()
        self.write(f"{cdr.RECORDS_DIR}/0002-second.md", "")
        self.track()
        self.assertFails("b", "file is empty")

    def test_both_live_0007_h1s_already_match_their_prefixes(self):
        """Property (b) holds on the real tree unchanged (issue #378 AC)."""
        for name in EXEMPT_PAIR:
            first = (ROOT / cdr.RECORDS_DIR / name).read_text().splitlines()[0]
            self.assertRegex(first, r"^# DR-0007\b")


class PropertyC(Fixture):
    """(c) §12.1 indexes every record exactly once, and nothing else."""

    def test_complete_index_passes(self):
        self.conforming()
        self.assertPasses()

    def test_unindexed_record_fails(self):
        for n in ("0001-first.md", "0002-second.md"):
            self.record(n)
        self.index("0001-first.md")  # 0002 omitted
        self.track()
        self.assertFails("c", "have no row", "0002-second.md")

    def test_row_for_a_nonexistent_record_fails(self):
        self.record("0001-first.md")
        self.index("0001-first.md", "0002-never-existed.md")
        self.track()
        self.assertFails("c", "0002-never-existed.md", "no such record")

    def test_row_whose_link_target_is_a_dead_path_fails(self):
        self.record("0001-first.md")
        self.index("0001-first.md", ("0001", "0001-renamed-away.md"))
        self.track()
        self.assertFails("c", "0001-renamed-away.md", "no such record")

    def test_record_indexed_twice_fails(self):
        self.record("0001-first.md")
        self.index("0001-first.md", "0001-first.md")
        self.track()
        self.assertFails("c", "2 rows in", "indexed exactly once")

    def test_mislabelled_row_fails(self):
        """A row's DR-NNNN must identify the record it links to."""
        for n in ("0001-first.md", "0002-second.md"):
            self.record(n)
        self.index("0001-first.md", ("0009", "0002-second.md"))
        self.track()
        self.assertFails("c", "labelled DR-0009", "0002-second.md")

    def test_missing_heading_is_a_run_error(self):
        self.conforming()
        text = (self.root / cdr.SPEC).read_text().replace(cdr.HEADING, "### 12.1 Gone")
        self.write(cdr.SPEC, text)
        self.track()
        with self.assertRaises(cdr.CheckError):
            self.check()
        self.assertEqual(self.run_main(), 2)

    def test_empty_table_is_a_run_error(self):
        for n in ("0001-first.md", "0002-second.md"):
            self.record(n)
        self.index()
        self.track()
        with self.assertRaises(cdr.CheckError):
            self.check()
        self.assertEqual(self.run_main(), 2)

    def test_rows_after_the_next_heading_are_not_part_of_12_1(self):
        """A DR row in §13 must not satisfy §12.1's index."""
        for n in ("0001-first.md", "0002-second.md"):
            self.record(n)
        self.index("0001-first.md")
        text = (self.root / cdr.SPEC).read_text().replace(
            "Tail prose.",
            "| [DR-0002](decisions/0002-second.md) | x | y |")
        self.write(cdr.SPEC, text)
        self.track()
        self.assertFails("c", "0002-second.md", "have no row")


class Discovery(Fixture):
    """What counts as a record: git-tracked, and named NNNN-*.md."""

    def test_non_record_filenames_are_skipped_not_failed(self):
        names = self.conforming()
        self.write(f"{cdr.RECORDS_DIR}/README.md", "# How to write a record\n")
        self.write(f"{cdr.RECORDS_DIR}/template.md", "# DR-NNNN — template\n")
        self.track()
        self.assertPasses()
        records, skipped = cdr.tracked_records(self.root)
        self.assertEqual(records,
                         [f"{cdr.RECORDS_DIR}/{n}" for n in sorted(names)])
        self.assertEqual(skipped, [f"{cdr.RECORDS_DIR}/README.md",
                                   f"{cdr.RECORDS_DIR}/template.md"])

    def test_the_skip_is_reported_on_success_not_silent(self):
        self.conforming()
        self.write(f"{cdr.RECORDS_DIR}/README.md", "# How to write a record\n")
        self.track()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cdr.main(["--root", str(self.root)]), 0)
        self.assertIn("skipped 1 non-record file", out.getvalue())
        self.assertIn("README.md", out.getvalue())

    def test_untracked_scratch_file_does_not_change_the_verdict(self):
        """Reads git ls-files, not a glob (issue #378 test plan)."""
        self.conforming()
        self.write(f"{cdr.RECORDS_DIR}/0002-untracked-duplicate.md",
                   "# DR-0002 — scratch copy\n")
        # deliberately NOT staged
        self.assertPasses()
        records, _ = cdr.tracked_records(self.root)
        self.assertNotIn(f"{cdr.RECORDS_DIR}/0002-untracked-duplicate.md",
                         records)

    def test_tracking_that_same_file_does_change_the_verdict(self):
        """The control for the test above: the skip is tracking, not the name."""
        self.conforming()
        self.write(f"{cdr.RECORDS_DIR}/0002-untracked-duplicate.md",
                   "# DR-0002 — scratch copy\n")
        self.track()
        self.assertFails("a", "DR-0002")

    def test_a_non_git_root_is_a_run_error(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        with self.assertRaises(cdr.CheckError):
            cdr.tracked_records(Path(td.name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
