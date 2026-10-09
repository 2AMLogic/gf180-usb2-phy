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
  this script exists to catch;
- the verdict is *only* reached on complete evidence (issue #136). The
  required matrix comes from the experiment's ratified ``tb.json`` -- five
  process families x nine (temperature, supply) points = 45 corners -- not
  from whichever log names happen to be on disk, and every corner must carry
  a 32-code table of finite values. An empty directory, a lone calibration
  log, a missing corner or process family, a truncated table, or nonfinite
  data must all come back as "incomplete evidence" (exit 2), never as
  ``Overall: PASS`` and never as an uncaught exception.

It runs against synthesised logs, not against the committed evidence, so it
keeps passing after a re-run mints a new record.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import shutil
import tempfile
import unittest
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SIM_DIR / "dplus-pullup-tolerance" / "analyze_fixed_trim.py"
#: The real, ratified manifest -- fixtures copy it so the required matrix the
#: tests exercise is the one the harness actually runs, not a test-local copy.
MANIFEST = SIM_DIR / "dplus-pullup-tolerance" / "testbench" / "tb.json"

PROCESSES = ("tt", "ff", "ss", "fs", "sf")
TEMPS = (("-40", -1), ("27", 0), ("125", 1))
SUPPLIES = (("2.97", -1), ("3.30", 0), ("3.63", 1))


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
        (self.dir / "testbench").mkdir()
        shutil.copy(MANIFEST, self.dir / "testbench" / "tb.json")
        self.corners = self.dir / "corners" / "20260101-000000-abc1234"
        self.corners.mkdir(parents=True)
        self.module = load_script(self.dir)

    @staticmethod
    def _table(drift: float) -> list[float]:
        """Code c is 1500*(1 + (c-16)*0.03)*drift, so code 16 is nominal at cal."""
        return [1500.0 * (1 + (c - 16) * 0.03) * drift for c in range(32)]

    def _grid(self, drift_pct_per_step: float, processes=PROCESSES) -> None:
        """Every process family over the full (T, V) grid -- the 45-corner matrix.

        Every non-calibration point is shifted by ``drift_pct_per_step`` per
        step away from 27 C / 3.30 V.
        """
        for process in processes:
            for temp, tstep in TEMPS:
                for supply, vstep in SUPPLIES:
                    drift = 1.0 + (abs(tstep) + abs(vstep)) * drift_pct_per_step / 100.0
                    write_log(self.corners / f"{process}_{temp}c_{supply}v.log", self._table(drift))

    def _run(self) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = self.module.main(["analyze"])
        return code, out.getvalue()

    def _assert_incomplete(self, *needles: str) -> str:
        code, text = self._run()
        self.assertEqual(code, self.module.EXIT_INCOMPLETE, text)
        self.assertNotEqual(code, 0)
        self.assertNotIn("Overall: PASS", text)
        self.assertIn("INCOMPLETE EVIDENCE", text)
        for needle in needles:
            self.assertIn(needle, text)
        return text

    # -- parser ------------------------------------------------------------

    def test_parser_reads_the_code_table_and_ignores_everything_else(self):
        self._grid(0.0)
        table = self.module.read_code_table(self.corners / "tt_27c_3.30v.log")
        self.assertEqual(len(table), 32)
        self.assertAlmostEqual(table[16], 1500.0)
        self.assertNotIn(1234.5, table)

    def test_corner_id_parses_under_the_ratified_grammar(self):
        self.assertEqual(self.module.parse_corner_id("ss_-40c_2.97v"), ("ss", "-40", "2.97"))
        self.assertEqual(self.module.parse_corner_id("res_ff_125c_3.63v"), ("res_ff", "125", "3.63"))

    def test_required_matrix_is_the_ratified_45_corners(self):
        matrix = self.module.required_matrix()
        self.assertEqual(len(matrix), 45)
        self.assertEqual({p for p, _, _ in matrix}, set(PROCESSES))
        self.assertIn(("ss", "-40", "2.97"), matrix)
        self.assertIn(("ff", "125", "3.63"), matrix)
        self.assertIn(("tt", "27", "3.30"), matrix)

    # -- verdicts on complete evidence ---------------------------------------

    def test_a_stable_full_matrix_passes(self):
        self._grid(1.0)          # worst point drifts 2 % from calibration
        code, text = self._run()
        self.assertEqual(code, 0, text)
        self.assertIn("Overall: PASS", text)
        self.assertIn("45 of 45", text)

    def test_a_full_matrix_that_drifts_off_the_calibration_code_fails(self):
        # Every corner still has *some* code inside ±5 % -- the ladder spans
        # ±48 % -- but the code chosen at 27 C / 3.30 V drifts 8 % away at the
        # extremes, which is the failure only a fixed-code analysis sees.
        self._grid(4.0)
        code, text = self._run()
        self.assertEqual(code, 1, text)
        self.assertIn("Overall: FAIL", text)

    # -- negative controls: incomplete evidence ------------------------------

    def test_an_empty_corner_directory_is_incomplete_not_pass(self):
        self._assert_incomplete("0 of 45", "missing")

    def test_a_lone_calibration_log_is_incomplete_not_pass(self):
        write_log(self.corners / "tt_27c_3.30v.log", [1500.0] * 32)
        self._assert_incomplete("1 of 45", "missing")

    def test_a_missing_extreme_corner_is_incomplete(self):
        self._grid(1.0)
        (self.corners / "ss_-40c_2.97v.log").unlink()
        self._assert_incomplete("ss_-40c_2.97v")

    def test_a_missing_process_family_is_incomplete(self):
        self._grid(1.0, processes=("tt", "ff", "ss", "fs"))
        text = self._assert_incomplete("36 of 45", "sf_27c_3.30v")
        self.assertIn("process family sf", text)

    def test_a_truncated_table_is_incomplete(self):
        self._grid(1.0)
        write_log(self.corners / "ff_125c_3.63v.log", self._table(1.0)[:20])
        self._assert_incomplete("ff_125c_3.63v", "20 of 32")

    def test_a_log_with_no_table_is_incomplete(self):
        self._grid(1.0)
        (self.corners / "fs_27c_2.97v.log").write_text("ngspice crashed\n")
        self._assert_incomplete("fs_27c_2.97v", "no `print rvec` code table")

    def test_a_calibration_log_with_a_malformed_table_is_incomplete_not_indexerror(self):
        # The code chosen at calibration (16) is past the end of the truncated
        # table at another point: before #136 this was an IndexError.
        self._grid(1.0)
        write_log(self.corners / "tt_125c_3.63v.log", self._table(1.0)[:10])
        self._assert_incomplete("tt_125c_3.63v")

    def test_nonfinite_values_are_incomplete(self):
        self._grid(1.0)
        # ngspice prints a NaN as the bare token "nan"; it must be reported,
        # not skipped by the row regex and mistaken for a shorter table.
        path = self.corners / "sf_-40c_3.63v.log"
        lines = path.read_text().splitlines()
        row = next(i for i, line in enumerate(lines) if line.startswith("16\t"))
        lines[row] = "16\t1.6500000000e+01\tnan\t"
        path.write_text("\n".join(lines) + "\n")
        self._assert_incomplete("sf_-40c_3.63v", "code 16", "nonfinite")

    def test_infinite_values_are_incomplete(self):
        self._grid(1.0)
        table = self._table(1.0)
        table[3] = float("inf")
        write_log(self.corners / "tt_27c_3.30v.log", table)
        self._assert_incomplete("tt_27c_3.30v", "code 3", "nonfinite")

    def test_an_unexpected_log_is_incomplete(self):
        self._grid(1.0)
        write_log(self.corners / "tt_85c_3.30v.log", self._table(1.0))
        write_log(self.corners / "garbage.log", self._table(1.0))
        self._assert_incomplete("tt_85c_3.30v", "garbage", "unexpected")


class CommittedEvidenceTests(unittest.TestCase):
    """Every committed record is still analyzable -- complete or explained.

    Not a verdict check (that is what the record itself is for); this pins that
    the stricter validation neither crashes on nor silently rejects the
    historical evidence the README quotes.
    """

    def test_committed_records_are_analyzable(self):
        module = load_script(SCRIPT.parent)
        corners_root = SCRIPT.parent / "corners"
        record_ids = sorted(p.name for p in corners_root.iterdir() if p.is_dir())
        self.assertTrue(record_ids)
        for record_id in record_ids:
            with self.subTest(record=record_id):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = module.main(["analyze", record_id])
                text = out.getvalue()
                self.assertIn(code, (0, 1, module.EXIT_INCOMPLETE), text)
                if code == module.EXIT_INCOMPLETE:
                    self.assertIn("INCOMPLETE EVIDENCE", text)
                else:
                    self.assertIn("45 of 45", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
