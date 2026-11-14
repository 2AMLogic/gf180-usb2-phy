#!/usr/bin/env python3
"""Check `spec/decisions/` against §12.1's index in `spec/usb2-device-phy.md`.

§12.1 ("Post-ratification decision records") is a hand-written table that
`spec/README.md` documents as the spec's decision log. Being hand-written, it
can be skipped: between DR-0002 and DR-0008 seven consecutive records landed
without touching it, the index drifted to 3 of 11 rows, and with nothing
listing the numbers already taken, **DR-0007 was allocated twice** (issue
#378). This checker removes the hand-maintained property by deriving the same
facts from the record files themselves.

Three properties over the *tracked* files in ``spec/decisions/``
(``git ls-files``, so an untracked scratch file cannot change the verdict):

  * **(a) unique numbers** — each ``NNNN`` filename prefix is used by exactly
    one record, with one documented historical exemption
    (``DUPLICATE_PREFIX_EXEMPTION`` below). Any other collision fails,
    including a third file joining the exempt pair.
  * **(b) H1 agreement** — each record's ``# DR-NNNN`` H1 matches its own
    filename prefix.
  * **(c) index completeness** — every record has exactly one row in §12.1,
    every row links to a record that exists, and a row's ``DR-NNNN`` label
    agrees with the record it links to.

Files in ``spec/decisions/`` whose names are not ``NNNN-*.md`` are **skipped**,
not failed, so a ``README.md`` there is allowed; the skipped names are printed
on success so the skip is never silent.

Zero dependencies beyond the Python 3 standard library; needs ``git`` on PATH.

Usage:
    python3 scripts/check_decision_records.py [--root DIR]
Exit codes: 0 all three properties hold, 1 violation (each printed),
2 usage / parse / git error.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

RECORDS_DIR = "spec/decisions"
SPEC = "spec/usb2-device-phy.md"
HEADING = "### 12.1 Post-ratification decision records"

# --- property (a)'s one exemption -----------------------------------------
# A historical collision, not a loosened rule: DR-0007 was allocated twice
# while §12.1 listed only DR-0001, so these two *different* decisions both
# ship an H1 reading "# DR-0007". Both are already cited in the wild by the
# abbreviated "DR-0007" form, and
# `0007-retire-bootstrap-harness-counter.md` cannot be renamed at all — two
# frozen append-only evidence records cite it by path
# (verification/records/functional-smoke/records/20261020-033000-4be8f5b.md:58
# and verification/records/synthesis-smoke/records/20261020-033001-4be8f5b.md:72),
# and `verification/check_records.py --require-append-only` enforces that in
# CI. Resolving the collision is therefore an operator ruling, open as
# **issue #381** (renumber the analog record to DR-0011 / keep this exemption
# permanently / renumber the harness-counter record). Whichever way #381
# rules, this constant is what it removes or makes permanent.
#
# The exemption is SINGLE-ENTRY: it names exactly this pair of paths. It is
# matched as a set, so a third `0007-*` record — or any other duplicated
# prefix — still fails property (a).
DUPLICATE_PREFIX_EXEMPTION = frozenset({
    f"{RECORDS_DIR}/0007-analog-statistical-rows.md",
    f"{RECORDS_DIR}/0007-retire-bootstrap-harness-counter.md",
})

RECORD_NAME_RE = re.compile(r"^(\d{4})-.+\.md$")
H1_RE = re.compile(r"^#\s+DR-(\d{4})\b")
ROW_LINK_RE = re.compile(r"^\|\s*\[DR-(\d{4})\]\(([^)]+)\)\s*\|")


class CheckError(Exception):
    """Something made the check impossible to run (vs. a violation)."""


def git(root: Path, *args: str) -> bytes:
    try:
        p = subprocess.run(["git", "-C", str(root), *args], check=False,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           env={**os.environ, "GIT_NO_LAZY_FETCH": "1"})
    except OSError as exc:
        raise CheckError(f"cannot run git: {exc}") from exc
    if p.returncode != 0:
        raise CheckError(f"git {' '.join(args)} failed: "
                         f"{p.stderr.decode('utf-8', 'replace').strip()}")
    return p.stdout


def tracked_records(root: Path) -> tuple[list[str], list[str]]:
    """Return (record paths, skipped non-record paths), both sorted.

    Reads ``git ls-files`` rather than globbing the directory, so an untracked
    scratch file in ``spec/decisions/`` does not change the verdict.
    """
    out = git(root, "ls-files", "-z", "--", RECORDS_DIR)
    paths = [p.decode("utf-8", "surrogateescape")
             for p in out.split(b"\0") if p]
    records, skipped = [], []
    for path in paths:
        name = path.rsplit("/", 1)[-1]
        (records if RECORD_NAME_RE.match(name) else skipped).append(path)
    if not records:
        raise CheckError(f"no decision records tracked under {RECORDS_DIR}/")
    return sorted(records), sorted(skipped)


def parse_index(text: str) -> list[tuple[int, str, str]]:
    """Return [(line_no, 'DR-NNNN' label digits, link target)] from §12.1.

    The table is the §12.1 block: everything from the heading to the next
    Markdown heading. Only ``| [DR-NNNN](target) | …`` rows are collected.
    """
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == HEADING)
    except StopIteration:
        raise CheckError(f"{SPEC}: heading {HEADING!r} not found") from None
    rows = []
    for offset, line in enumerate(lines[start + 1:], start=start + 2):
        if line.startswith("#"):
            break
        m = ROW_LINK_RE.match(line)
        if m:
            rows.append((offset, m.group(1), m.group(2)))
    if not rows:
        raise CheckError(f"{SPEC}: §12.1 contains no decision-record rows")
    return rows


def check(root: Path) -> list[str]:
    """Return a list of violation messages; empty means all three hold."""
    records, _ = tracked_records(root)
    errs: list[str] = []

    # --- (a) unique NNNN prefix, modulo the single-entry exemption
    by_prefix: dict[str, list[str]] = {}
    for path in records:
        prefix = RECORD_NAME_RE.match(path.rsplit("/", 1)[-1]).group(1)
        by_prefix.setdefault(prefix, []).append(path)
    for prefix, paths in sorted(by_prefix.items()):
        if len(paths) == 1:
            continue
        if frozenset(paths) == DUPLICATE_PREFIX_EXEMPTION:
            continue
        errs.append(
            f"(a) DR-{prefix} is allocated to {len(paths)} records: "
            + ", ".join(paths)
            + " — allocate the next free number instead; the only exempt "
              "collision is the historical pair "
            + ", ".join(sorted(DUPLICATE_PREFIX_EXEMPTION))
            + " (see issue #381)")

    # --- (b) H1 agrees with the filename prefix
    for path in records:
        prefix = RECORD_NAME_RE.match(path.rsplit("/", 1)[-1]).group(1)
        try:
            first = (root / path).read_text().splitlines()[:1]
        except OSError as exc:
            raise CheckError(f"cannot read {path}: {exc}") from exc
        if not first:
            errs.append(f"(b) {path}: file is empty, "
                        "want a '# DR-NNNN ...' H1")
            continue
        m = H1_RE.match(first[0])
        if not m:
            errs.append(f"(b) {path}: first line is not a '# DR-NNNN ...' "
                        f"H1: {first[0].strip()!r}")
        elif m.group(1) != prefix:
            errs.append(f"(b) {path}: H1 says DR-{m.group(1)}, "
                        f"filename says DR-{prefix}")

    # --- (c) §12.1 indexes every record exactly once, and nothing else
    try:
        spec_text = (root / SPEC).read_text()
    except OSError as exc:
        raise CheckError(f"cannot read {SPEC}: {exc}") from exc
    spec_dir = str(Path(SPEC).parent)
    rows = parse_index(spec_text)

    indexed: dict[str, list[int]] = {}
    for line_no, label, target in rows:
        path = os.path.normpath(f"{spec_dir}/{target}")
        indexed.setdefault(path, []).append(line_no)
        if path not in records:
            errs.append(f"(c) {SPEC}:{line_no}: row [DR-{label}] links to "
                        f"{target} — no such record is tracked under "
                        f"{RECORDS_DIR}/")
            continue
        prefix = RECORD_NAME_RE.match(path.rsplit("/", 1)[-1]).group(1)
        if label != prefix:
            errs.append(f"(c) {SPEC}:{line_no}: row is labelled DR-{label} "
                        f"but links to {target} (DR-{prefix})")
    for path, line_nos in sorted(indexed.items()):
        if len(line_nos) > 1:
            errs.append(f"(c) {path} has {len(line_nos)} rows in §12.1 "
                        f"(lines {', '.join(str(n) for n in line_nos)}); "
                        "each record is indexed exactly once")
    missing = [p for p in records if p not in indexed]
    if missing:
        errs.append(f"(c) {len(missing)} record(s) tracked under "
                    f"{RECORDS_DIR}/ have no row in {SPEC} §12.1: "
                    + ", ".join(missing))
    return errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path,
                    default=Path(__file__).resolve().parents[1])
    args = ap.parse_args(argv)
    try:
        records, skipped = tracked_records(args.root)
        errs = check(args.root)
    except CheckError as exc:
        print(f"check_decision_records: {exc}", file=sys.stderr)
        return 2
    for e in errs:
        print(f"FAIL {e}")
    if errs:
        return 1
    # Print the skipped names too: property (a)/(b)/(c) ignore them by
    # design, so the skip must be visible rather than silent.
    note = ""
    if skipped:
        note = (f"; skipped {len(skipped)} non-record file(s) "
                f"(name is not NNNN-*.md): " + ", ".join(skipped))
    print(f"check_decision_records: OK — {len(records)} records, "
          f"all indexed in {SPEC} §12.1{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
