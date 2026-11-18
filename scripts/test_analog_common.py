#!/usr/bin/env python3
"""Self-test for ``analog_common.py``: the shared stream discovery, once.

``discover_blocks`` used to be characterised twice -- once per harness copy
(``test_analog_lvs.py``'s ``DiscoverBlocks``, ``test_analog_erc.py``'s
``TestDiscovery``) while the function itself lived byte-identically in both
harnesses. Issue #380 moved the one copy into ``analog_common.py``, so its
contract is pinned here, once:

  * **stream discovery** comes from the committed ``*.gds`` glob, never a
    hard-coded block list (#339 may merge the two single-ended receivers,
    #252-style work may add streams), is sorted, and is not confused by
    sibling files;
  * ``REPO_ROOT`` still resolves to the repo root from the shared module's
    own location (both harnesses import it, so a path regression here
    breaks both at once -- which is the point);
  * ``DECK`` is the gf180mcu deck both harnesses pin.

Usage:
    python3 scripts/test_analog_common.py   (or: python3 -m pytest scripts/test_analog_common.py)
Exit codes: 0 all cases behave as specified, 1 otherwise.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analog_common as acommon  # noqa: E402


class DiscoverBlocks(unittest.TestCase):
    def test_discovers_from_gds_glob_sorted(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("zeta.gds", "alpha.gds", "mid.gds"):
                Path(d, name).write_bytes(b"")
            # Sibling files that are not streams must not become blocks.
            Path(d, "alpha.json").write_text("{}")
            Path(d, "notes.md").write_text("x")
            self.assertEqual(acommon.discover_blocks(d), ["alpha", "mid", "zeta"])

    def test_empty_dir_yields_no_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(acommon.discover_blocks(d), [])

    def test_block_list_is_not_hard_coded(self):
        """A merged/renamed stream is picked up with no edit to the module."""
        with tempfile.TemporaryDirectory() as d:
            Path(d, "se_receiver_merged.gds").write_bytes(b"")
            self.assertEqual(acommon.discover_blocks(d), ["se_receiver_merged"])


class ModuleContract(unittest.TestCase):
    def test_repo_root_resolves_to_this_repo_from_the_shared_location(self):
        self.assertEqual(acommon.REPO_ROOT, str(ROOT))

    def test_deck_is_gf180mcu(self):
        self.assertEqual(acommon.DECK, "gf180mcu")


if __name__ == "__main__":
    unittest.main(verbosity=2)
