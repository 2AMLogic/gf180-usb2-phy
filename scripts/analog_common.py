#!/usr/bin/env python3
"""Helpers shared by the analog signoff harnesses (issue #380).

Why this module exists: ``scripts/analog_erc.py`` and
``scripts/analog_lvs.py`` each used to carry byte-identical private copies
of ``sh()``, ``sha256()`` and ``discover_blocks()`` (plus the ``REPO_ROOT``
and ``DECK`` constants), with docstrings that had already drifted apart
while the code stayed identical. Two copies of ``discover_blocks`` were
not cosmetic bloat: ERC's ``grade_lvs_pairing()`` reads the LVS harness's
per-block artifacts, so the two harnesses are coupled at runtime while
free to drift at the source level -- the moment one copy of the glob was
edited and the other not (exactly what the #339 receiver merge both
docstrings anticipated), the two signoff harnesses would disagree about
what blocks exist, and a stream would be ERC'd without being LVS'd (or
ERC would fail with a confusing "no committed LVS report"). The operator
ruling on issue #380 (2026-11-17) settled the placement: one shared
module imported by both harnesses, following the precedent
``scripts/klt_resolve.py`` already set.

This ends the standalone-per-script property for the two harnesses:
replaying a frozen ``analog-erc`` or ``analog-lvs`` record now needs
``analog_erc.py`` / ``analog_lvs.py`` **and** this file present in
``scripts/``. Existing frozen records are not edited; the superseding
records minted with this change say so.

Zero dependencies beyond the Python 3 standard library.
"""

from __future__ import annotations

import glob
import hashlib
import os
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECK = "gf180mcu"


def sh(cmd: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def discover_blocks(gds_dir: str) -> list[str]:
    """Block names from the committed streams, sorted, never hard-coded.

    #339 may merge the two single-ended receivers and #252-style work may
    add streams; both are picked up by this glob with no edit here.
    """
    return sorted(
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(gds_dir, "*.gds"))
    )
