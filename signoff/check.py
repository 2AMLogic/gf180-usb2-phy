#!/usr/bin/env python3
"""Drift check for the artifact-anchored T1 citations (items 1, 2.digital, 9, 10).

    python3 signoff/check.py            # the gate `npm run check:ci` runs
    python3 signoff/check.py --regen    # rebuild inventories, envelopes, manifest pins

`klt signoff` (>= 0.7.0) proves that the artifact an envelope is bound to still
re-hashes to the pinned value. It cannot tell whether an inventory is complete
or whether a file it describes has since changed. This script re-derives every
inventory (`signoff/inventories.py`) from the live tree and fails on any
changed, missing or newly added member, and on any disagreement between the
manifest pin, the envelope and the bound artifact.

It does not render the report: `scripts/check_signoff_report.py` already
re-renders `manifests/t1-signoff-report.json` and fails on drift. It does not
run the gates that need xschem, yosys, OpenROAD or the PDK; each envelope's
`summary` says so.

Pure stdlib; no klt, no PDK.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import inventories  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = "manifests/gf180-usb2-phy.json"


def fail(msg: str) -> None:
    print(f"FAIL {msg}", file=sys.stderr)


def _sort_key(key: str) -> tuple[int, str]:
    number, _, partition = key.partition(".")
    return int(number), partition


def check_anchored_evidence(root: Path = REPO_ROOT, manifest_path: Path | None = None) -> bool:
    manifest_path = manifest_path or root / MANIFEST
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, ValueError) as exc:
        fail(f"{manifest_path}: unreadable manifest ({exc})")
        return False
    ok = True
    for key in inventories.ITEM_ENVELOPES:
        problems = inventories.verify_item(root, key, manifest)
        for problem in problems:
            fail(problem)
        if problems:
            ok = False
            print(
                f"     T1 item {key}: if the change is intended, review it and run "
                "python3 signoff/check.py --regen",
                file=sys.stderr,
            )
        else:
            print(
                f"ok   T1 item {key}: {inventories.ITEM_ARTIFACTS[key]} is bound and "
                "describes the current tree"
            )
    return ok


def regen(root: Path = REPO_ROOT, manifest_path: Path | None = None) -> bool:
    """Rebuild inventories/envelopes and re-pin their manifest citations.

    Refuses (writes nothing) when the audit fails: no `pass` envelope is ever
    written over a claim the tree does not support.
    """
    manifest_path = manifest_path or root / MANIFEST
    try:
        pins = inventories.write_all(root)
    except inventories.AuditError as exc:
        fail(f"audit failed, nothing written: {exc}")
        return False
    manifest = json.loads(manifest_path.read_text())
    evidence = manifest["evidence"]
    for key, content_hash in pins.items():
        evidence[key] = {"file": inventories.ITEM_ENVELOPES[key], "content_hash": content_hash}
    manifest["evidence"] = dict(sorted(evidence.items(), key=lambda kv: _sort_key(kv[0])))
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote inventories, envelopes and manifest pins for T1 items {', '.join(pins)}")
    print("     now re-render manifests/t1-signoff-report.json with `klt signoff`")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--regen",
        action="store_true",
        help="rebuild the inventories, envelopes and manifest pins from the current tree",
    )
    args = parser.parse_args(argv)
    if args.regen:
        return 0 if regen() else 1
    return 0 if check_anchored_evidence() else 1


if __name__ == "__main__":
    raise SystemExit(main())
