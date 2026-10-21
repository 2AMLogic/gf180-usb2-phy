#!/usr/bin/env python3
"""Self-test for `verification/check_statistical_na.py` (standard library only)."""
from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_statistical_na as chk  # noqa: E402


def fixture(root: Path, spec: bytes, pinned: str | None) -> None:
    (root / "spec").mkdir()
    (root / "verification").mkdir()
    (root / "spec" / "usb2-device-phy.md").write_bytes(spec)
    if pinned is not None:
        (root / "verification" / "statistical-claims-na.md").write_text(
            f"<!-- statistical-na: spec_sha256={pinned} -->\n"
        )


def main() -> int:
    failures = []
    spec = b"spec v1\n"
    good = hashlib.sha256(spec).hexdigest()
    cases = [
        ("bound", spec, good, True),
        ("stale", spec, hashlib.sha256(b"other").hexdigest(), False),
        ("missing statement", spec, None, False),
    ]
    for name, body, pinned, ok in cases:
        with tempfile.TemporaryDirectory() as d:
            fixture(Path(d), body, pinned)
            if (chk.check(Path(d)) == []) != ok:
                failures.append(name)
    # The committed statement must be bound to the committed spec.
    if chk.check(Path(__file__).resolve().parent.parent):
        failures.append("committed statement is stale")
    for f in failures:
        print(f"FAIL: {f}", file=sys.stderr)
    print("ok" if not failures else f"{len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
