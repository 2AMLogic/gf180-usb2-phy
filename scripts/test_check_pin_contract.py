#!/usr/bin/env python3
"""Self-test for `scripts/check_pin_contract.py`.

A contract checker that silently stops catching drift is worse than none, so
each disagreement class gets a test: copy the real record, RTL and netlists
into a temp tree, mutate one thing, and assert the checker fails (and that
the unmutated copy passes).

Usage:
    python3 scripts/test_check_pin_contract.py
Exit codes: 0 all cases behave as specified, 1 otherwise.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_pin_contract as cpc  # noqa: E402


class PinContractTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for rel in (cpc.RECORD, cpc.RTL):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / rel, self.root / rel)
        (self.root / "design/netlist").mkdir(parents=True)
        for f in (ROOT / "design/netlist").glob("*.spice"):
            shutil.copy(f, self.root / "design/netlist" / f.name)

    def tearDown(self):
        self._tmp.cleanup()

    def edit(self, rel, old, new, count=1):
        p = self.root / rel
        s = p.read_text()
        self.assertIn(old, s)
        p.write_text(s.replace(old, new, count))

    def test_real_tree_passes(self):
        self.assertEqual(cpc.check(self.root), [])

    def test_renamed_netlist_pin_fails(self):
        self.edit("design/netlist/dplus_pullup.spice", "PU_EN", "PU_ENABLE", count=-1)
        errs = cpc.check(self.root)
        self.assertTrue(any("PU_EN" in e for e in errs), errs)
        self.assertEqual(cpc.main(["--root", str(self.root)]), 1)

    def test_renamed_rtl_port_fails(self):
        self.edit(cpc.RTL, "output wire txdp,", "output wire txd_p,")
        errs = cpc.check(self.root)
        self.assertTrue(any("txdp" in e for e in errs), errs)

    def test_rtl_direction_flip_fails(self):
        self.edit(cpc.RTL, "input  wire rxdp,", "output wire rxdp,")
        self.assertTrue(any("rxdp" in e for e in cpc.check(self.root)))

    def test_netlist_direction_change_fails(self):
        self.edit("design/netlist/dplus_pullup.spice", "PU_EN:I", "PU_EN:O")
        self.assertTrue(any("PU_EN" in e for e in cpc.check(self.root)))

    def test_new_uncovered_pin_fails(self):
        self.edit("design/netlist/differential_driver.spice",
                  ".subckt differential_driver VDD", ".subckt differential_driver TXOE VDD")
        self.assertTrue(any("not covered" in e or "TXOE" in e for e in cpc.check(self.root)))

    # Every digital side has now landed (PU_EN #112, txoe #113, trim #115),
    # so no real row is planned-dig any more. Revert one landed row to its
    # former planned status and assert the existing port trips the check:
    # landing a follow-up without flipping its row must still fail.
    def test_planned_pin_landing_without_table_update_fails(self):
        self.edit(cpc.RECORD, "| I | current | integrator | test-time code |",
                  "| I | planned-dig #115 | integrator | test-time code |")
        self.assertTrue(any("planned" in e and "trim" in e for e in cpc.check(self.root)))

    # TXOE's analog side is still planned-ana #114: adding the netlist pin
    # without flipping the row must fail with a "planned" error.
    def test_planned_analog_landing_without_table_update_fails(self):
        self.edit("design/netlist/differential_driver.spice",
                  ".subckt differential_driver VDD", ".subckt differential_driver TXOE VDD")
        self.assertTrue(any("planned" in e and "TXOE" in e for e in cpc.check(self.root)))

    # --- trim[4:0] (#115): the current TRIM rows pin a five-bit input.
    def test_trim_rows_are_current_five_bit_input(self):
        rows = cpc.parse_table((self.root / cpc.RECORD).read_text())
        trim = [r for r in rows if r["pin"].startswith("TRIM")]
        self.assertEqual([r["dport"] for r in trim], [f"trim[{i}]" for i in range(5)])
        self.assertTrue(all(r["status"] == "current" and r["ddir"] == "input" for r in trim))
        self.assertEqual([r["apin"] for r in trim], [f"dplus_pullup.TRIM{i}" for i in range(5)])
        ports = cpc.parse_verilog_ports((self.root / cpc.RTL).read_text())
        self.assertEqual(ports["trim"], ("input", 5))

    def test_missing_trim_port_fails(self):
        self.edit(cpc.RTL, "input  wire [4:0] trim,\n", "")
        errs = cpc.check(self.root)
        self.assertTrue(any("'trim' missing" in e for e in errs), errs)
        self.assertEqual(cpc.main(["--root", str(self.root)]), 1)

    def test_too_narrow_trim_bus_fails(self):
        self.edit(cpc.RTL, "input  wire [4:0] trim,", "input  wire [3:0] trim,")
        errs = cpc.check(self.root)
        self.assertTrue(any("TRIM4" in e and "outside trim width 4" in e for e in errs), errs)

    def test_trim_direction_flip_fails(self):
        self.edit(cpc.RTL, "input  wire [4:0] trim,", "output wire [4:0] trim,")
        self.assertTrue(any("port trim is output" in e for e in cpc.check(self.root)))

    def test_bad_table_is_parse_error(self):
        self.edit(cpc.RECORD, cpc.BEGIN, "")
        self.assertEqual(cpc.main(["--root", str(self.root)]), 2)


if __name__ == "__main__":
    unittest.main()
