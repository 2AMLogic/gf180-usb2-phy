#!/usr/bin/env python3
"""Check that the digital "no statistical row" statement is bound to the spec.

`verification/statistical-claims-na.md` carries a marker
`<!-- statistical-na: spec_sha256=<hex> -->`. This recomputes the SHA-256 of
`spec/usb2-device-phy.md` and fails if it differs, so a spec change cannot
leave the statement silently stale.

    python3 verification/check_statistical_na.py [--repo-root DIR]

Exit 0 bound, 1 stale/missing. Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

MARKER = re.compile(r"<!--\s*statistical-na:\s*spec_sha256=([0-9a-f]{64})\s*-->")


def check(root: Path) -> list[str]:
    statement = root / "verification" / "statistical-claims-na.md"
    spec = root / "spec" / "usb2-device-phy.md"
    if not statement.is_file():
        return [f"missing {statement}"]
    found = MARKER.findall(statement.read_text())
    if len(found) != 1:
        return [f"{statement}: expected exactly one statistical-na marker, found {len(found)}"]
    actual = hashlib.sha256(spec.read_bytes()).hexdigest()
    if found[0] != actual:
        return [
            f"{statement}: pinned spec_sha256 {found[0]} != current {actual}; "
            "re-read the statement against the changed spec and supersede it"
        ]
    return []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    errors = check(ap.parse_args(argv).repo_root)
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if not errors:
        print("statistical-claims-na.md: bound to current spec")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
