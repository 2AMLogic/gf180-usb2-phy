#!/usr/bin/env python3
"""Offline check of ``layout/analog/provenance.json`` against the tree.

``scripts/gen_analog_layout.py --check`` regenerates every block and so needs
the PDK and klt's layout executor. This check needs neither: it only re-hashes
files, so CI can run it on every PR. For each ``blocks[]`` entry:

  * ``gds``, ``design/netlist/<block>.spice`` and
    ``layout/analog/plans/<block>.json`` must hash to the recorded
    ``gds_sha256`` / ``netlist_sha256`` / ``plan_sha256``;
  * the entry must carry a ``drc`` object with ``status == "clean"``;
  * every ``layout/analog/*.gds`` must have an entry.

A block with a plan but no GDS yet (not listed in the sidecar) passes.

Zero dependencies beyond the Python 3 standard library.
Usage: python3 scripts/check_analog_provenance.py [--root DIR]
Exit codes: 0 consistent, 1 drift found, 2 unreadable sidecar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SIDECAR = "layout/analog/provenance.json"
GDS_DIR = "layout/analog"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(root: Path) -> tuple[list[str], list[str]]:
    """Return (errors, per-block OK lines)."""
    with open(root / SIDECAR, encoding="utf-8") as handle:
        blocks = json.load(handle)["blocks"]
    errors: list[str] = []
    ok: list[str] = []
    listed: set[str] = set()
    for entry in blocks:
        block = entry["block"]
        gds_rel = entry.get("gds", f"{GDS_DIR}/{block}.gds")
        listed.add(gds_rel)
        before = len(errors)
        inputs = (
            ("gds_sha256", root / gds_rel),
            ("netlist_sha256", root / "design/netlist" / f"{block}.spice"),
            ("plan_sha256", root / GDS_DIR / "plans" / f"{block}.json"),
        )
        for key, path in inputs:
            if not path.is_file():
                errors.append(f"{block}: {path.relative_to(root)} is missing ({key})")
            elif key not in entry:
                errors.append(f"{block}: {key} is not recorded")
            elif _sha256(path) != entry[key]:
                errors.append(f"{block}: {key} is stale (input changed since delivery)")
        drc = entry.get("drc")
        if not isinstance(drc, dict):
            errors.append(f"{block}: no drc object recorded")
        elif drc.get("status") != "clean":
            errors.append(f"{block}: drc.status is {drc.get('status')!r}, not 'clean'")
        if len(errors) == before:
            ok.append(f"{block}: OK")
    for gds in sorted((root / GDS_DIR).glob("*.gds")):
        rel = gds.relative_to(root).as_posix()
        if rel not in listed:
            errors.append(f"{gds.stem}: {rel} has no entry in {SIDECAR}")
    return errors, ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args(argv)
    try:
        errors, ok = check(args.root)
    except (OSError, KeyError, ValueError) as e:
        print(f"check_analog_provenance: {e}", file=sys.stderr)
        return 2
    for line in ok:
        print(line)
    for e in errors:
        print(f"FAIL {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
