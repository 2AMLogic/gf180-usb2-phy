"""Pin sim/shared-pad-bus's DUT fragment to the exported cells (issue #119).

The experiment's DUT is the five ``design/netlist/`` cells concatenated
verbatim, because the harness's klt deck transport cannot ship nested
``.include`` closures. This test keeps that file from drifting away from the
generated cells it stands in for.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DUT = REPO / "sim" / "shared-pad-bus" / "testbench" / "shared_pad_dut.spice"
CELLS = (
    "differential_driver",
    "se_receiver_dp",
    "se_receiver_dm",
    "differential_receiver",
    "dplus_pullup",
)


class SharedPadDutTest(unittest.TestCase):
    def test_dut_is_verbatim_concatenation_of_exported_cells(self):
        text = DUT.read_text()
        for cell in CELLS:
            body = (REPO / "design" / "netlist" / f"{cell}.spice").read_text().rstrip("\n")
            self.assertIn(body + "\n", text, f"{cell}: DUT copy differs from design/netlist")

    def test_dut_holds_exactly_the_five_cells(self):
        defs = [ln.split()[1] for ln in DUT.read_text().splitlines() if ln.lower().startswith(".subckt")]
        self.assertEqual(sorted(CELLS), sorted(defs))


if __name__ == "__main__":
    unittest.main()
