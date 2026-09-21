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

Usage:
    python3 scripts/test_check_signoff_report.py
Exit codes: 0 all cases behave as specified, 1 at least one did not.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CHECKER = SCRIPT_DIR / "check_signoff_report.py"

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
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / "check_signoff_report.py")],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def case_parity_accepted(tmp: Path) -> list[str]:
    """An exit-3 render equal to the committed report passes (sees OK)."""
    repo, bin_dir = build_fixture_repo(tmp)
    result = run_checker(repo, bin_dir)
    errors = []
    if result.returncode != 0:
        errors.append(
            f"parity render (exit 3, identical report) should exit 0, got "
            f"{result.returncode}; stdout={result.stdout!r} stderr={result.stderr!r}"
        )
    if "OK:" not in result.stdout:
        errors.append(f"accepted case should print an OK line, got {result.stdout!r}")
    return errors


def case_exit_zero_render_accepted(tmp: Path) -> list[str]:
    """An exit-0 render (every T1 item met) is a clean run, not a failure."""
    repo, bin_dir = build_fixture_repo(tmp)
    accepted = json.loads(
        (repo / "manifests" / "t1-signoff-report.json").read_text(encoding="utf-8")
    )
    _write_stub(bin_dir, "klt", 0, accepted)
    result = run_checker(repo, bin_dir)
    if result.returncode != 0:
        return [
            f"exit-0 render should be accepted (exit 0), got "
            f"{result.returncode}; stderr={result.stderr!r}"
        ]
    return []


def case_exit_one_render_rejected(tmp: Path) -> list[str]:
    """A klt error render (exit 1) fails the check, never parses as parity."""
    repo, bin_dir = build_fixture_repo(tmp)
    _write_stub(bin_dir, "klt", 1, {"error": {"message": "fixture error envelope"}})
    result = run_checker(repo, bin_dir)
    if result.returncode == 0:
        return [
            "an error render (klt exit 1) must FAIL the check, but it exited 0"
        ]
    if "exited 1" not in result.stderr:
        return [
            f"the failure should name the unexpected klt exit, got: {result.stderr!r}"
        ]
    return []


def case_drifted_render_rejected(tmp: Path) -> list[str]:
    """A fresh render that diverges from the committed report FAILS -- the
    rot case this checker exists to catch (a hash-pin flips an item to
    `unmet`/`stale_evidence`, a tier boundary moves, a build drifts)."""
    repo, bin_dir = build_fixture_repo(tmp)
    drifted = json.loads(
        (repo / "manifests" / "t1-signoff-report.json").read_text(encoding="utf-8")
    )
    drifted["items"][0]["status"] = "unmet"
    drifted["items"][0]["reason"] = "stale_evidence"
    drifted["items"][0]["citation"]["coverage"]["rules_skipped"] = ["metaltop.width.1"]
    drifted["t1_met_count"] = 0
    _write_stub(bin_dir, "klt", 3, drifted)
    result = run_checker(repo, bin_dir)
    if result.returncode == 0:
        return ["a drifted fresh render must FAIL the check, but it exited 0"]
    if "stale_evidence" not in result.stderr:
        return [
            f"the drift failure should show the diverging fields, got: {result.stderr!r}"
        ]
    return []


def case_missing_report_rejected(tmp: Path) -> list[str]:
    """No committed report at all is a failure, not a silent pass."""
    repo, bin_dir = build_fixture_repo(tmp)
    (repo / "manifests" / "t1-signoff-report.json").unlink()
    result = run_checker(repo, bin_dir)
    if result.returncode == 0:
        return ["a missing committed report must FAIL the check, but it exited 0"]
    return []


_CASES = [
    ("parity accepted (exit 3 + identical report)", case_parity_accepted),
    ("exit-0 render accepted", case_exit_zero_render_accepted),
    ("error render (klt exit 1) rejected", case_exit_one_render_rejected),
    ("drifted fresh render rejected", case_drifted_render_rejected),
    ("missing committed report rejected", case_missing_report_rejected),
]


def main() -> int:
    # Importable as a module without side effects; only a direct run tests.
    failures = []
    for name, case in _CASES:
        with tempfile.TemporaryDirectory() as tmp_str:
            errors = case(Path(tmp_str))
        if errors:
            failures.append((name, errors))
            print(f"FAIL: {name}")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"OK:   {name}")
    total = len(_CASES)
    if failures:
        print(f"\n{len(failures)}/{total} case(s) FAILED")
        return 1
    print(f"\nall {total} cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
