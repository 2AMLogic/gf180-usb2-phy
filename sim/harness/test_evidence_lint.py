#!/usr/bin/env python3
"""Self-test for `sim/check_records.py` (implementation: `evidence_lint.py`).

Mirrors `verification/test_check_records.py`: build a throwaway git repo in a
temp dir, copy the *real* linter files into it, and run
`sim/check_records.py` as a subprocess exactly the way `npm run lint` and
`sim/selftest.sh` do. Nothing is monkeypatched, so this exercises the shipped
entry point rather than a stand-in.

Filed against issue #16: before this file existed, the corner-id grammar and
the log-count-vs-predecessor check -- both specific to the `sim/` evidence
convention -- had zero executable coverage (`verification/`'s self-test only
exercises the JSON-metadata / content-hash-freshness checks that have no
`sim/` equivalent). This file closes that gap.

`sim/harness/evidence_lint.py` imports its record-id grammar, field-block
parser, and git merge-base plumbing from `verification/check_records.py`
(see that module's docstring), so the fixture repo needs a copy of both
files -- not just `sim/check_records.py` -- to run standalone.

Zero dependencies beyond the Python 3 standard library and `git`.

Usage:
    python3 sim/harness/test_evidence_lint.py
Exit codes: 0 all cases behave as specified, 1 at least one did not.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SIM_DIR.parent
CHECK_RECORDS = SIM_DIR / "check_records.py"
EVIDENCE_LINT = SIM_DIR / "harness" / "evidence_lint.py"
HARNESS_INIT = SIM_DIR / "harness" / "__init__.py"
VERIFICATION_CHECK_RECORDS = REPO_ROOT / "verification" / "check_records.py"

BASE_REF = "refs/heads/fixture-base"

SLUG = "smoke"
BASE_ID = "20260101-000000-abc1234"
BASE_LOGS = ["tt_27c_3.30v.log", "ff_27c_3.30v.log"]  # 2 logs


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
    slug: str,
    *,
    supersedes: str | None = None,
    omit_field: str | None = None,
) -> str:
    """Render a record that satisfies the convention in `sim/README.md`,
    optionally omitting one required field so a negative case can be built
    from it."""
    fields = [
        ("Record ID", record_id),
        ("Claim", "None -- harness self-test fixture claim, not a spec claim."),
        ("Netlist provenance", f"schematic (`sim/{slug}/testbench/fixture.spice`)"),
        ("Corner matrix run", "fixture subset, self-test only (not a spec claim)"),
        ("Statistical convention", "N/A (fixture)"),
        ("Result", "**Overall: PASS** (fixture)"),
        ("Links", f"Testbench: `sim/{slug}/testbench/fixture.spice`"),
        ("Timestamp / author", "2026-01-01T00:00:00Z, selftest"),
        ("Supersedes", supersedes or "(none)"),
    ]
    bullets = "\n".join(
        f"- **{name}**: {value}" for name, value in fields if name != omit_field
    )
    return f"# Record {record_id}\n\n{bullets}\n"


def write_record(
    repo: Path,
    record_id: str,
    slug: str,
    *,
    logs: list[str],
    supersedes: str | None = None,
    omit_field: str | None = None,
    write_snapshot: bool = True,
    write_record_file: bool = True,
) -> None:
    """Write one record's summary file, netlist snapshot, and corner logs."""
    experiment = repo / "sim" / slug
    if write_record_file:
        records_dir = experiment / "records"
        records_dir.mkdir(parents=True, exist_ok=True)
        (records_dir / f"{record_id}.md").write_text(
            make_record(record_id, slug, supersedes=supersedes, omit_field=omit_field),
            encoding="utf-8",
        )
    if write_snapshot:
        snapshot_dir = experiment / "netlist-snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        (snapshot_dir / f"{record_id}.spice").write_text(
            "* fixture netlist snapshot\n", encoding="utf-8"
        )
    if logs:
        corner_dir = experiment / "corners" / record_id
        corner_dir.mkdir(parents=True, exist_ok=True)
        for name in logs:
            (corner_dir / name).write_text("* fixture ngspice log\n", encoding="utf-8")


def build_fixture_repo(tmp: Path) -> Path:
    """A minimal repo with one valid record committed, and `BASE_REF`
    pointing at that commit so the append-only check has a base to diff."""
    repo = tmp / "fixture"
    (repo / "sim" / "harness").mkdir(parents=True)
    (repo / "verification").mkdir(parents=True)

    shutil.copyfile(CHECK_RECORDS, repo / "sim" / "check_records.py")
    shutil.copyfile(HARNESS_INIT, repo / "sim" / "harness" / "__init__.py")
    shutil.copyfile(EVIDENCE_LINT, repo / "sim" / "harness" / "evidence_lint.py")
    shutil.copyfile(
        VERIFICATION_CHECK_RECORDS, repo / "verification" / "check_records.py"
    )

    write_record(repo, BASE_ID, SLUG, logs=BASE_LOGS)

    _git(repo, "init", "--quiet")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: initial record")
    _git(repo, "update-ref", BASE_REF, "HEAD")
    return repo


def run_linter(repo: Path) -> tuple[int, str]:
    result = subprocess.run(
        [
            sys.executable,
            str(repo / "sim" / "check_records.py"),
            "--base-ref",
            BASE_REF,
            "--require-append-only",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


def record_path(repo: Path, slug: str, record_id: str) -> Path:
    return repo / "sim" / slug / "records" / f"{record_id}.md"


# --- cases -------------------------------------------------------------
# Each case mutates a fresh fixture repo and returns nothing; the harness
# asserts the expected exit code and a substring of the linter's output.


def case_valid(repo: Path) -> None:
    """Control: an untouched fixture must pass, or every negative case below
    would pass for the wrong reason."""


def case_missing_required_field(repo: Path) -> None:
    new_id = "20260102-000000-abc1234"
    write_record(repo, new_id, SLUG, logs=["tt_27c_3.30v.log"], omit_field="Claim")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: record missing Claim")


def case_bad_record_id_grammar(repo: Path) -> None:
    write_record(repo, "not-a-record-id", SLUG, logs=["tt_27c_3.30v.log"])
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: malformed record id")


def case_missing_netlist_snapshot(repo: Path) -> None:
    new_id = "20260102-000000-abc1234"
    write_record(
        repo, new_id, SLUG, logs=["tt_27c_3.30v.log"], write_snapshot=False
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: record with no netlist snapshot")


def case_no_corner_logs(repo: Path) -> None:
    new_id = "20260102-000000-abc1234"
    write_record(repo, new_id, SLUG, logs=[])
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: record with no corner logs")


def case_bad_corner_id_grammar(repo: Path) -> None:
    new_id = "20260102-000000-abc1234"
    write_record(repo, new_id, SLUG, logs=["not-a-corner-id.log"])
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: record with malformed corner-id log")


def case_dangling_supersedes(repo: Path) -> None:
    new_id = "20260102-000000-abc1234"
    write_record(
        repo,
        new_id,
        SLUG,
        logs=["tt_27c_3.30v.log"],
        supersedes="20250101-000000-deadbee",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: supersedes a nonexistent record")


def case_self_referencing_supersedes(repo: Path) -> None:
    new_id = "20260102-000000-abc1234"
    write_record(repo, new_id, SLUG, logs=["tt_27c_3.30v.log"], supersedes=new_id)
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: supersedes itself")


def case_head_has_fewer_logs_than_predecessor(repo: Path) -> None:
    """The current head of a supersession chain must carry at least as many
    raw per-corner logs as the record it supersedes (sim/README.md) -- the
    log-count-vs-predecessor check, previously uncovered by any test."""
    new_id = "20260102-000000-abc1234"
    write_record(
        repo,
        new_id,
        SLUG,
        logs=["tt_27c_3.30v.log"],  # 1 log, fewer than BASE_ID's 2
        supersedes=BASE_ID,
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: head with fewer logs than predecessor")


def case_superseded_record_exempt_from_log_count(repo: Path) -> None:
    """A record that is no longer the head of its supersession chain is not
    re-checked against the log-count-vs-predecessor rule -- only the current
    head is. `mid` legitimately has fewer logs than `BASE_ID`, but once
    `head` supersedes `mid`, `mid` is frozen history and exempt."""
    mid_id = "20260102-000000-abc1234"
    head_id = "20260103-000000-abc1234"
    write_record(
        repo, mid_id, SLUG, logs=["tt_27c_3.30v.log"], supersedes=BASE_ID
    )
    write_record(
        repo, head_id, SLUG, logs=["tt_27c_3.30v.log"], supersedes=mid_id
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: supersede the fewer-logs record")


def case_edited_existing_record(repo: Path) -> None:
    path = record_path(repo, SLUG, BASE_ID)
    path.write_text(
        path.read_text(encoding="utf-8").replace("fixture claim", "edited claim"),
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: edit an existing record")


def case_deleted_existing_record(repo: Path) -> None:
    _git(repo, "rm", "--quiet", f"sim/{SLUG}/records/{BASE_ID}.md")
    _git(repo, "commit", "--quiet", "-m", "fixture: delete an existing record")


def case_new_record_is_a_pure_addition(repo: Path) -> None:
    """Adding a record must NOT trip the append-only check -- otherwise the
    convention would forbid the very thing it exists to allow."""
    new_id = "20260102-000000-abc1234"
    write_record(repo, new_id, SLUG, logs=["tt_27c_3.30v.log"])
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "fixture: add a new record")


CASES = [
    # (name, mutation, expected_exit, expected_substring)
    ("valid record passes", case_valid, 0, "append-only: clean"),
    (
        "record missing a required field fails",
        case_missing_required_field,
        1,
        "missing required field **Claim**",
    ),
    (
        "malformed record id fails",
        case_bad_record_id_grammar,
        1,
        "not a <YYYYMMDD>-<HHMMSS>-<short-git-sha> record id",
    ),
    (
        "record with no netlist snapshot fails",
        case_missing_netlist_snapshot,
        1,
        "no frozen netlist at",
    ),
    (
        "record with no corner logs fails",
        case_no_corner_logs,
        1,
        "no raw per-corner logs at",
    ),
    (
        "malformed corner-id log name fails",
        case_bad_corner_id_grammar,
        1,
        "does not parse as <process>_<temp>c_<supply>",
    ),
    (
        "supersedes naming a nonexistent record fails",
        case_dangling_supersedes,
        1,
        "which has no record at",
    ),
    (
        "supersedes pointing at itself fails",
        case_self_referencing_supersedes,
        1,
        "points at this record itself",
    ),
    (
        "head with fewer logs than its Supersedes predecessor fails",
        case_head_has_fewer_logs_than_predecessor,
        1,
        "fewer than its Supersedes predecessor",
    ),
    (
        "a superseded record is exempt from the log-count check",
        case_superseded_record_exempt_from_log_count,
        0,
        "append-only: clean",
    ),
    (
        "edited existing record fails (append-only)",
        case_edited_existing_record,
        1,
        "sim/ evidence is append-only",
    ),
    (
        "deleted existing record fails (append-only)",
        case_deleted_existing_record,
        1,
        "sim/ evidence is append-only",
    ),
    (
        "adding a new record is allowed",
        case_new_record_is_a_pure_addition,
        0,
        "append-only: clean",
    ),
]


def main() -> int:
    for path, label in (
        (CHECK_RECORDS, "sim/check_records.py"),
        (EVIDENCE_LINT, "sim/harness/evidence_lint.py"),
        (VERIFICATION_CHECK_RECORDS, "verification/check_records.py"),
    ):
        if not path.exists():
            print(f"FATAL: {label} not found at {path}", file=sys.stderr)
            return 1

    print(f"== evidence_lint.py self-test ({len(CASES)} cases) ==")
    failures = 0
    for name, mutate, expected_exit, expected_substring in CASES:
        with tempfile.TemporaryDirectory(prefix="sim-evidence-lint-selftest-") as tmpdir:
            repo = build_fixture_repo(Path(tmpdir))
            mutate(repo)
            exit_code, output = run_linter(repo)

            problems = []
            if exit_code != expected_exit:
                problems.append(f"exit {exit_code}, expected {expected_exit}")
            if expected_substring not in output:
                problems.append(f"output missing {expected_substring!r}")

            if problems:
                failures += 1
                print(f"FAIL: {name}")
                for problem in problems:
                    print(f"  - {problem}")
                print("  --- linter output ---")
                for line in output.splitlines():
                    print(f"  | {line}")
            else:
                print(f"OK:   {name}")

    print()
    if failures:
        print(f"FAIL: {failures}/{len(CASES)} self-test case(s) did not behave as specified")
        return 1
    print(f"PASS: all {len(CASES)} self-test cases behaved as specified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
