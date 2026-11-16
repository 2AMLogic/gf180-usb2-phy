#!/usr/bin/env python3
"""Self-test for `verification/check_records.py`.

The record linter is the only thing standing between "append-only evidence"
as a documented intention and append-only evidence as an enforced property.
A linter that silently stops catching a violation class is worse than no
linter, so each violation class the convention names in
`verification/README.md` gets an executable negative test here.

Method: build a throwaway git repo in a temp dir, copy the *real*
`check_records.py` into its `verification/` directory (the linter resolves
its repo root from `__file__`, so the copy lints the fixture repo), and run
it as a subprocess exactly the way `npm run lint` and CI do. Nothing is
monkeypatched, so this exercises the shipped entry point rather than a
stand-in.

Zero dependencies beyond the Python 3 standard library and `git`.

Runs both ways: directly (`python3 verification/test_check_records.py`,
an explicit `npm run lint` step) and under unittest discovery
(`python3 -m unittest discover -s verification -t verification
-p 'test_check_records.py'`).
Exit codes: 0 all tests pass, non-zero at least one did not.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LINTER = SCRIPT_DIR / "check_records.py"

BASE_REF = "refs/heads/fixture-base"

DUMMY_RTL = "module dut(input wire clk); endmodule\n"


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-c",
            "user.name=record-linter-selftest",
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
        raise RuntimeError(
            f"git {' '.join(args)} failed in {repo}: {result.stderr.strip()}"
        )
    return result.stdout


def make_record(
    record_id: str,
    experiment: str,
    *,
    inputs: list[tuple[str, str]],
    supersedes: str | None = None,
    omit_field: str | None = None,
    omit_provenance_key: str | None = None,
) -> str:
    """Render a record that satisfies the convention in
    `verification/README.md`, optionally omitting one required prose field
    so a negative case can be built from it."""
    meta = {
        "record_id": record_id,
        "experiment": experiment,
        "supersedes": supersedes,
        "git_revision": "0" * 40,
        "provenance": {
            "klt_version": "0.0.0-selftest",
            "pdk": {"name": "n/a", "version": "n/a"},
            "deck": {"content_hash": "n/a"},
            "inputs": [
                {"path": path, "content_hash": content_hash}
                for path, content_hash in inputs
            ],
        },
    }
    if omit_provenance_key is not None:
        meta["provenance"].pop(omit_provenance_key)
    fields = [
        ("Record ID", record_id),
        ("Claim", "`docs/baseline.md#the-measurement` -- fixture claim"),
        ("Design provenance", "rtl (`rtl/dut.v` @ `" + "0" * 40 + "`)"),
        ("Run configuration", "fixture run, no real simulator invoked"),
        ("Statistical convention", "N/A (fixture)"),
        ("Result", "**Overall: PASS** (fixture)"),
        ("klt provenance", "klt 0.0.0-selftest; PDK: n/a; deck content_hash: n/a"),
        ("Links", "Design under test: `rtl/dut.v`"),
        ("Timestamp / author", "2026-01-01T00:00:00Z, selftest"),
        ("Supersedes", supersedes or "none"),
    ]
    bullets = "\n".join(
        f"- **{name}**: {value}" for name, value in fields if name != omit_field
    )
    return (
        "<!-- record-meta\n"
        + json.dumps(meta, indent=2)
        + "\n-->\n\n"
        + f"# Record {record_id}\n\n"
        + bullets
        + "\n"
    )


def build_fixture_repo(tmp: Path) -> Path:
    """A minimal repo with one valid record committed, and `BASE_REF`
    pointing at that commit so the append-only check has a base to diff."""
    repo = tmp / "fixture"
    (repo / "rtl").mkdir(parents=True)
    (repo / "verification" / "records" / "demo" / "records").mkdir(parents=True)

    (repo / "rtl" / "dut.v").write_text(DUMMY_RTL, encoding="utf-8")
    shutil.copyfile(LINTER, repo / "verification" / "check_records.py")

    record = make_record(
        "20260101-000000-abc1234",
        "demo",
        inputs=[("rtl/dut.v", _sha256_text(DUMMY_RTL))],
    )
    (
        repo / "verification" / "records" / "demo" / "records" / "20260101-000000-abc1234.md"
    ).write_text(record, encoding="utf-8")

    _git(repo, "init", "--quiet")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: initial record")
    _git(repo, "update-ref", BASE_REF, "HEAD")
    return repo


def run_linter(repo: Path) -> tuple[int, str]:
    result = subprocess.run(
        [
            sys.executable,
            str(repo / "verification" / "check_records.py"),
            "--base-ref",
            BASE_REF,
            "--require-append-only",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


def record_path(repo: Path, experiment: str, record_id: str) -> Path:
    return (
        repo / "verification" / "records" / experiment / "records" / f"{record_id}.md"
    )


# --- cases -----------------------------------------------------------------
# Each case mutates a fresh fixture repo and returns nothing; the TestCase
# below asserts the expected exit code and a substring of the linter's output.


def case_valid(repo: Path) -> None:
    """Control: an untouched fixture must pass, or every negative case below
    would pass for the wrong reason."""


def case_missing_required_field(repo: Path) -> None:
    new_id = "20260102-000000-abc1234"
    path = record_path(repo, "demo", new_id)
    path.write_text(
        make_record(
            new_id,
            "demo",
            inputs=[("rtl/dut.v", _sha256_text(DUMMY_RTL))],
            omit_field="Claim",
        ),
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: record missing Claim")


def case_missing_required_meta_key(repo: Path) -> None:
    new_id = "20260102-000000-abc1234"
    record_path(repo, "demo", new_id).write_text(
        make_record(
            new_id,
            "demo",
            inputs=[("rtl/dut.v", _sha256_text(DUMMY_RTL))],
            omit_provenance_key="klt_version",
        ),
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: record missing klt_version")


def case_edited_existing_record(repo: Path) -> None:
    path = record_path(repo, "demo", "20260101-000000-abc1234")
    path.write_text(
        path.read_text(encoding="utf-8").replace("fixture claim", "edited claim"),
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: edit an existing record")


def case_deleted_existing_record(repo: Path) -> None:
    _git(
        repo,
        "rm",
        "--quiet",
        "verification/records/demo/records/20260101-000000-abc1234.md",
    )
    _git(repo, "commit", "--quiet", "-m", "fixture: delete an existing record")


def case_stale_provenance_hash(repo: Path) -> None:
    (repo / "rtl" / "dut.v").write_text(
        DUMMY_RTL + "// the RTL changed after the record was minted\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: change the cited source")


def case_superseded_record_exempt_from_freshness(repo: Path) -> None:
    """A superseded record is frozen history: it may legitimately cite a
    source that has since changed. Only the live record must be fresh."""
    new_rtl = DUMMY_RTL + "// v2\n"
    (repo / "rtl" / "dut.v").write_text(new_rtl, encoding="utf-8")
    new_id = "20260103-000000-abc1234"
    record_path(repo, "demo", new_id).write_text(
        make_record(
            new_id,
            "demo",
            inputs=[("rtl/dut.v", _sha256_text(new_rtl))],
            supersedes="20260101-000000-abc1234",
        ),
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: supersede the first record")


def case_bad_record_id_grammar(repo: Path) -> None:
    bad = record_path(repo, "demo", "not-a-record-id")
    bad.write_text(
        make_record(
            "not-a-record-id",
            "demo",
            inputs=[("rtl/dut.v", _sha256_text(DUMMY_RTL))],
        ),
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: malformed record id")


def case_dangling_supersedes(repo: Path) -> None:
    new_id = "20260104-000000-abc1234"
    record_path(repo, "demo", new_id).write_text(
        make_record(
            new_id,
            "demo",
            inputs=[("rtl/dut.v", _sha256_text(DUMMY_RTL))],
            supersedes="20250101-000000-deadbee",
        ),
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: supersedes a nonexistent record")


def case_new_record_is_a_pure_addition(repo: Path) -> None:
    """Adding a record must NOT trip the append-only check -- otherwise the
    convention would forbid the very thing it exists to allow."""
    new_id = "20260105-000000-abc1234"
    record_path(repo, "demo", new_id).write_text(
        make_record(
            new_id, "demo", inputs=[("rtl/dut.v", _sha256_text(DUMMY_RTL))]
        ),
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: add a new record")


class TestCheckRecords(unittest.TestCase):
    """One test per violation class (or exempted behavior) the convention
    names; each runs its `case_*` mutation against a fresh fixture repo and
    asserts the linter's exit code plus one substring of its output."""

    def setUp(self) -> None:
        if not LINTER.exists():
            self.fail(f"{LINTER} not found")
        tmpdir = tempfile.TemporaryDirectory(prefix="record-linter-selftest-")
        self.addCleanup(tmpdir.cleanup)
        self.tmp = Path(tmpdir.name)

    def _run_case(self, mutate) -> tuple[int, str]:
        repo = build_fixture_repo(self.tmp)
        mutate(repo)
        return run_linter(repo)

    def test_valid_record_passes(self) -> None:
        """Control: an untouched fixture must pass, or every negative case
        below would pass for the wrong reason."""
        exit_code, output = self._run_case(case_valid)
        self.assertEqual(0, exit_code, f"linter output:\n{output}")
        self.assertIn("PASS: all records valid", output)

    def test_record_missing_required_field_fails(self) -> None:
        exit_code, output = self._run_case(case_missing_required_field)
        self.assertEqual(1, exit_code, f"linter output:\n{output}")
        self.assertIn("missing required field bullet `- **Claim**:`", output)

    def test_record_missing_required_meta_key_fails(self) -> None:
        exit_code, output = self._run_case(case_missing_required_meta_key)
        self.assertEqual(1, exit_code, f"linter output:\n{output}")
        self.assertIn("provenance missing required key `klt_version`", output)

    def test_edited_existing_record_fails(self) -> None:
        exit_code, output = self._run_case(case_edited_existing_record)
        self.assertEqual(1, exit_code, f"linter output:\n{output}")
        self.assertIn("append-only violation", output)

    def test_deleted_existing_record_fails(self) -> None:
        exit_code, output = self._run_case(case_deleted_existing_record)
        self.assertEqual(1, exit_code, f"linter output:\n{output}")
        self.assertIn("append-only violation", output)

    def test_stale_provenance_hash_fails(self) -> None:
        exit_code, output = self._run_case(case_stale_provenance_hash)
        self.assertEqual(1, exit_code, f"linter output:\n{output}")
        self.assertIn("is stale", output)

    def test_superseded_record_exempt_from_freshness(self) -> None:
        exit_code, output = self._run_case(case_superseded_record_exempt_from_freshness)
        self.assertEqual(0, exit_code, f"linter output:\n{output}")
        self.assertIn("PASS: all records valid", output)

    def test_bad_record_id_grammar_fails(self) -> None:
        exit_code, output = self._run_case(case_bad_record_id_grammar)
        self.assertEqual(1, exit_code, f"linter output:\n{output}")
        self.assertIn("is not a valid record-id", output)

    def test_dangling_supersedes_fails(self) -> None:
        exit_code, output = self._run_case(case_dangling_supersedes)
        self.assertEqual(1, exit_code, f"linter output:\n{output}")
        self.assertIn("which has no record", output)

    def test_new_record_is_a_pure_addition(self) -> None:
        exit_code, output = self._run_case(case_new_record_is_a_pure_addition)
        self.assertEqual(0, exit_code, f"linter output:\n{output}")
        self.assertIn("no append-only violations", output)


if __name__ == "__main__":
    unittest.main()
