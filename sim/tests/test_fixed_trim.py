#!/usr/bin/env python3
"""Self-test for sim/dplus-pullup-tolerance/analyze_fixed_trim.py.

    python3 sim/tests/test_fixed_trim.py

The script turns recorded corner logs into a pass/fail claim about
``spec/usb2-device-phy.md`` §5 ("one trim code, set at test, holds ±5 % over
the temperature and supply axes"), so it needs a testbench of its own -- a
claim produced by unverified analysis code is exactly what CLAUDE.md's "no
claim without a testbench" rule is about. Two things are worth pinning:

- the log parser reads the ``print rvec`` sweep table and nothing else in the
  log (the same file also carries the scalar ``m_*`` measurement lines and an
  operating-point dump, either of which a sloppier regex would swallow);
- the verdict logic really is *fixed*-code -- it must FAIL a grid where every
  corner has *some* good code but no single code works across temperature,
  which is precisely the case the per-corner harness check cannot catch and
  this script exists to catch.

It runs against synthesised logs, not against the committed evidence, so it
keeps passing after a re-run mints a new record.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SIM_DIR / "dplus-pullup-tolerance" / "analyze_fixed_trim.py"


def load_script(experiment_dir: Path):
    """Import the analysis script with its EXPERIMENT_DIR pointed at a fixture."""
    spec = importlib.util.spec_from_file_location("analyze_fixed_trim", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.EXPERIMENT_DIR = experiment_dir
    return module


def write_log(path: Path, resistances: list[float]) -> None:
    """A corner log shaped like the harness writes one: sweep table + scalars."""
    lines = [
        "Circuit: * dplus-pullup-tolerance @ tt_27c_3.30v",
        "",
        "Index   v-sweep         rvec            ",
        "-" * 80,
    ]
    for index, value in enumerate(resistances):
        lines.append(f"{index}\t{index + 0.5:.10e}\t{value:.10e}\t")
        # A decoy row in the same shape but a different sweep grid: the parser
        # must key on the code axis, not on "three numbers on a line".
    lines += [
        "",
        "0\t9.9000000000e+01\t1.2345000000e+03\t",
        "m_r_code0_ohm = 2.1409346053e+03",
        "m_best_err_pct = 8.9367819166e-01",
    ]
    path.write_text("\n".join(lines) + "\n")


class FixedTrimTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        (self.dir / "records").mkdir()
        (self.dir / "records" / "20260101-000000-abc1234.md").write_text("# fixture\n")
        self.corners = self.dir / "corners" / "20260101-000000-abc1234"
        self.corners.mkdir(parents=True)
        self.module = load_script(self.dir)

    def _grid(self, drift_pct_per_step: float) -> None:
        """One process corner over the full (T, V) grid.

        Code c has resistance 1500*(1 + (c-16)*0.03), so code 16 is exactly
        nominal at the calibration point; every non-calibration point is
        shifted by ``drift_pct_per_step`` per step away from 27 C / 3.30 V.
        """
        for temp, tstep in (("-40", -1), ("27", 0), ("125", 1)):
            for supply, vstep in (("2.97", -1), ("3.30", 0), ("3.63", 1)):
                drift = 1.0 + (abs(tstep) + abs(vstep)) * drift_pct_per_step / 100.0
                table = [1500.0 * (1 + (c - 16) * 0.03) * drift for c in range(32)]
                write_log(self.corners / f"tt_{temp}c_{supply}v.log", table)

    def test_parser_reads_the_code_table_and_ignores_everything_else(self):
        self._grid(0.0)
        table = self.module.read_code_table(self.corners / "tt_27c_3.30v.log")
        self.assertEqual(len(table), 32)
        self.assertAlmostEqual(table[16], 1500.0)
        self.assertNotIn(1234.5, table)

    def test_corner_id_parses_under_the_ratified_grammar(self):
        self.assertEqual(self.module.parse_corner_id("ss_-40c_2.97v"), ("ss", "-40", "2.97"))
        self.assertEqual(self.module.parse_corner_id("res_ff_125c_3.63v"), ("res_ff", "125", "3.63"))

    def test_a_stable_grid_passes(self):
        self._grid(1.0)          # worst point drifts 2 % from calibration
        self.assertEqual(self.module.main(["analyze"]), 0)

    def test_a_grid_that_drifts_off_the_calibration_code_fails(self):
        # Every corner still has *some* code inside ±5 % -- the ladder spans
        # ±48 % -- but the code chosen at 27 C / 3.30 V drifts 8 % away at the
        # extremes, which is the failure only a fixed-code analysis sees.
        self._grid(4.0)
        self.assertEqual(self.module.main(["analyze"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
