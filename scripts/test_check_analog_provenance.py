#!/usr/bin/env python3
"""Self-test for `scripts/check_analog_provenance.py` (temp-dir fixtures).

Usage:
    python3 scripts/test_check_analog_provenance.py
Exit codes: 0 all cases behave as specified, 1 otherwise.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_analog_provenance as cap  # noqa: E402


def _h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "layout/analog/plans").mkdir(parents=True)
        (self.root / "design/netlist").mkdir(parents=True)
        blocks = []
        for name in ("alpha", "beta"):
            self.write(f"layout/analog/{name}.gds", f"gds-{name}".encode())
            self.write(f"design/netlist/{name}.spice", f"net-{name}".encode())
            self.write(f"layout/analog/plans/{name}.json", f"plan-{name}".encode())
            blocks.append(
                {
                    "block": name,
                    "gds": f"layout/analog/{name}.gds",
                    "gds_sha256": _h(f"gds-{name}".encode()),
                    "netlist_sha256": _h(f"net-{name}".encode()),
                    "plan_sha256": _h(f"plan-{name}".encode()),
                    "drc": {"status": "clean", "violation_count": 0},
                }
            )
        self.blocks = blocks
        self.save()

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, data):
        (self.root / rel).write_bytes(data)

    def save(self):
        doc = {"schema_version": 1, "blocks": self.blocks}
        self.write(cap.SIDECAR, json.dumps(doc).encode())

    def errors(self):
        return cap.check(self.root)[0]

    def test_all_match_passes(self):
        errs, ok = cap.check(self.root)
        self.assertEqual(errs, [])
        self.assertEqual(len(ok), 2)
        self.assertEqual(cap.main(["--root", str(self.root)]), 0)

    def test_edited_netlist_fails(self):
        self.write("design/netlist/beta.spice", b"changed")
        errs = self.errors()
        self.assertTrue(any("beta" in e and "netlist_sha256" in e and "stale" in e for e in errs), errs)
        self.assertEqual(cap.main(["--root", str(self.root)]), 1)

    def test_edited_plan_fails(self):
        self.write("layout/analog/plans/alpha.json", b"changed")
        errs = self.errors()
        self.assertTrue(any("alpha" in e and "plan_sha256" in e for e in errs), errs)

    def test_edited_gds_fails(self):
        self.write("layout/analog/alpha.gds", b"changed")
        errs = self.errors()
        self.assertTrue(any("alpha" in e and "gds_sha256" in e for e in errs), errs)

    def test_unlisted_gds_fails(self):
        self.write("layout/analog/gamma.gds", b"orphan")
        errs = self.errors()
        self.assertTrue(any("gamma" in e and "no entry" in e for e in errs), errs)

    def test_missing_listed_gds_fails(self):
        (self.root / "layout/analog/beta.gds").unlink()
        errs = self.errors()
        self.assertTrue(any("beta" in e and "missing" in e for e in errs), errs)

    def test_missing_or_dirty_drc_fails(self):
        del self.blocks[0]["drc"]
        self.blocks[1]["drc"] = {"status": "violations", "violation_count": 3}
        self.save()
        errs = self.errors()
        self.assertTrue(any("alpha" in e and "drc" in e for e in errs), errs)
        self.assertTrue(any("beta" in e and "drc.status" in e for e in errs), errs)

    def test_plan_only_block_passes(self):
        # Plan and netlist exist, no GDS, no sidecar entry (e.g. a driver awaiting layout).
        self.write("design/netlist/delta.spice", b"net-delta")
        self.write("layout/analog/plans/delta.json", b"plan-delta")
        self.assertEqual(self.errors(), [])

    def test_real_tree_passes(self):
        self.assertEqual(cap.check(ROOT)[0], [])


if __name__ == "__main__":
    unittest.main()
