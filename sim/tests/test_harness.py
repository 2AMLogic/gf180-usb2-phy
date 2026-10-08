#!/usr/bin/env python3
"""Unit tests for the PVT harness. No PDK and no ngspice required.

    python3 -m unittest discover -s sim/tests -v

Trimmed from the sibling gf180-bandgap repository's sim/tests/test_harness.py
(same PDK) per CLAUDE.md's "Harness bootstrap" instruction: this keeps the
tests that exercise generic harness machinery (corner grid, deck composition,
measurement parsing, check evaluation, record id allocation, matrix
conformance, record rendering) and drops the bandgap-specific DUT-swap
fixtures (sim/dut/, sim/device-*/, sim/suite/) that this repo does not have
yet.
"""

from __future__ import annotations

import datetime
import json
import sys
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

SIM_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_DIR))

from harness import cli, corners, klt_backend, report, runner, testbench  # noqa: E402
from harness.pdk import Pdk  # noqa: E402


def fake_pdk(root: Path) -> Pdk:
    (root / "libs.tech" / "ngspice").mkdir(parents=True, exist_ok=True)
    (root / "libs.tech" / "ngspice" / "sm141064.ngspice").write_text("* fake\n")
    (root / "libs.tech" / "ngspice" / "design.ngspice").write_text("* fake\n")
    (root / "SOURCES").write_text("open_pdks deadbeef\n")
    return Pdk(path=root, variant=root.name, source="test")


class CornerTests(unittest.TestCase):
    def test_pvt_axes_match_the_mandated_grid(self):
        self.assertEqual(corners.DEFAULT_TEMPERATURES_C, (-40.0, 27.0, 125.0))
        self.assertAlmostEqual(corners.DEFAULT_SUPPLY_TOLERANCE, 0.10)

    def test_supply_points_are_nominal_plus_minus_ten_percent(self):
        self.assertEqual(corners.supply_points(3.3, 0.10), [2.97, 3.3, 3.63])

    def test_zero_tolerance_collapses_the_voltage_axis(self):
        self.assertEqual(corners.supply_points(3.3, 0.0), [3.3])

    def test_every_corner_names_one_section_per_device_family(self):
        for name, corner in corners.CORNERS.items():
            with self.subTest(corner=name):
                self.assertEqual(len(corner.sections), 6, corner.sections)
                self.assertEqual(len(set(corner.sections)), 6, corner.sections)

    def test_corner_sets_expand_and_deduplicate(self):
        resolved = corners.resolve_corners(["mos", "tt"])
        self.assertEqual([c.name for c in resolved], ["tt", "ff", "ss", "fs", "sf"])

    def test_unknown_corner_is_rejected(self):
        with self.assertRaises(KeyError):
            corners.resolve_corners(["nope"])

    def test_grid_is_full_factorial_and_ordered(self):
        grid = corners.build_grid(corners.resolve_corners(["mos"]), (-40, 27, 125), [2.97, 3.3, 3.63])
        self.assertEqual(len(grid), 5 * 3 * 3)
        self.assertEqual(len({p.corner_id for p in grid}), 45)

    def test_corner_id_matches_the_ratified_naming(self):
        """sim/README.md: <corner-id> is <process>_<temp>c_<supply>v."""
        grid = corners.build_grid(
            corners.resolve_corners(["tt", "ss", "ff"]), (-40, 27, 125), [2.97, 3.3, 3.63]
        )
        ids = {p.corner_id for p in grid}
        self.assertIn("tt_27c_3.30v", ids)
        self.assertIn("ss_-40c_2.97v", ids)
        self.assertIn("ff_125c_3.63v", ids)


class TestbenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def _write(self, netlist: str, manifest: dict | None = None) -> Path:
        """Lay out sim/<slug>/testbench/ the way sim/README.md specifies."""
        tb_dir = self.dir / "an-experiment" / "testbench"
        tb_dir.mkdir(parents=True, exist_ok=True)
        (tb_dir / "x.spice").write_text(netlist)
        base = {"name": "x", "netlist": "x.spice", "measure": {"vout": "v(out)"}}
        base.update(manifest or {})
        (tb_dir / "tb.json").write_text(json.dumps(base))
        return tb_dir

    def test_loads_a_valid_manifest(self):
        tb = testbench.load(self._write("v1 out 0 dc {vdd_val}\n"))
        self.assertEqual(tb.name, "x")
        self.assertEqual(tb.measure, {"vout": "v(out)"})
        self.assertEqual(tb.temperatures_c, (-40.0, 27.0, 125.0))

    def test_experiment_slug_comes_from_the_directory_layout(self):
        tb_dir = self._write("v1 out 0 dc {vdd_val}\n")
        # Loadable by testbench dir *and* by experiment dir.
        for target in (tb_dir, tb_dir.parent):
            with self.subTest(target=target.name):
                tb = testbench.load(target)
                self.assertEqual(tb.experiment, "an-experiment")
                self.assertEqual(tb.experiment_dir.name, "an-experiment")

    def test_discover_finds_experiments_not_bare_manifest_dirs(self):
        self._write("v1 out 0 dc {vdd_val}\n")
        found = testbench.discover(self.dir)
        self.assertEqual([p.name for p in found], ["an-experiment"])

    def test_rejects_netlists_that_pin_the_temperature(self):
        with self.assertRaises(ValueError) as ctx:
            testbench.load(self._write("v1 out 0 dc 3.3\n.temp 27\n"))
        self.assertIn(".temp", str(ctx.exception))

    def test_rejects_netlists_that_include_models_themselves(self):
        with self.assertRaises(ValueError):
            testbench.load(self._write('.lib "models" typical\nv1 out 0 dc 3.3\n'))

    def test_rejects_a_manifest_without_measurements(self):
        with self.assertRaises(ValueError):
            testbench.load(self._write("v1 out 0 dc 3.3\n", {"measure": {}}))

    def test_derive_accepts_control_block_measurement_statements(self):
        tb = testbench.load(
            self._write(
                "v1 out 0 dc {vdd_val}\n",
                {"derive": ["meas tran t_r TRIG v(out) VAL=0.3 RISE=1 TARG v(out) VAL=2.7 RISE=1"]},
            )
        )
        self.assertEqual(len(tb.derive), 1)
        self.assertTrue(tb.derive[0].startswith("meas tran"))

    def test_derive_rejects_statements_that_would_own_the_deck(self):
        for bad in (".endc", "quit", "write out.raw v(out)", "shell rm -rf /", ""):
            with self.subTest(statement=bad):
                with self.assertRaises(ValueError) as ctx:
                    testbench.load(self._write("v1 out 0 dc 3.3\n", {"derive": [bad]}))
                self.assertIn("derive", str(ctx.exception))

    def test_the_repo_smoke_testbench_is_valid(self):
        tb = testbench.load(SIM_DIR / "smoke-inverter")
        self.assertEqual(tb.nominal_supply_v, 3.3)
        self.assertEqual(tb.experiment, "smoke-inverter")
        self.assertIn("vm", tb.measure)
        self.assertIn("vm", tb.checks)


class DeckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        (root / "tb").mkdir()
        (root / "tb" / "x.spice").write_text("v1 out 0 dc {vdd_val}\n")
        (root / "tb" / "tb.json").write_text(
            json.dumps(
                {
                    "name": "x",
                    "netlist": "x.spice",
                    "measure": {"vout": "v(out)", "iq": "-i(v1)"},
                    "params": {"cload": "1p"},
                    "options": ["reltol=1e-5"],
                }
            )
        )
        self.tb = testbench.load(root / "tb")
        self.pdk = fake_pdk(root / "gf180mcuD")
        self.point = corners.build_grid(corners.resolve_corners(["ss"]), (125,), [3.63])[0]
        self.deck = runner.compose_deck(self.tb, self.pdk, self.point)

    def test_deck_sets_the_pvt_point(self):
        self.assertIn(".param vdd_val=3.63", self.deck)
        self.assertIn(".param vdd_nom=3.3", self.deck)
        self.assertIn(".temp 125", self.deck)

    def test_deck_includes_design_switches_before_model_sections(self):
        design_at = self.deck.index("design.ngspice")
        lib_at = self.deck.index("sm141064.ngspice")
        self.assertLess(design_at, lib_at)

    def test_deck_selects_every_section_of_the_corner(self):
        for section in self.point.corner.sections:
            self.assertIn(f'sm141064.ngspice" {section}', self.deck)

    def test_deck_carries_manifest_params_and_options(self):
        self.assertIn(".param cload=1p", self.deck)
        self.assertIn(".options reltol=1e-5", self.deck)

    def test_deck_emits_one_measurement_vector_per_measure_entry(self):
        self.assertIn("let m_vout = v(out)", self.deck)
        self.assertIn("let m_iq = -i(v1)", self.deck)
        self.assertIn("print m_vout", self.deck)
        self.assertTrue(self.deck.rstrip().endswith(".end"))

    def test_derive_statements_run_after_the_analyses_and_before_the_measures(self):
        root = Path(self.tb.directory)
        manifest = json.loads((root / "tb.json").read_text())
        manifest["analyses"] = ["tran 1n 100n"]
        manifest["derive"] = ["meas tran t_r TRIG v(out) VAL=0.3 RISE=1 TARG v(out) VAL=2.7 RISE=1"]
        manifest["measure"] = {"trise_ns": "t_r*1e9"}
        (root / "tb.json").write_text(json.dumps(manifest))
        deck = runner.compose_deck(testbench.load(root), self.pdk, self.point)
        analysis_at = deck.index("tran 1n 100n")
        derive_at = deck.index("meas tran t_r")
        measure_at = deck.index("let m_trise_ns")
        self.assertLess(analysis_at, derive_at)
        self.assertLess(derive_at, measure_at)


class ParseTests(unittest.TestCase):
    def test_parses_print_output(self):
        text = "\n".join(
            [
                "Circuit: * x",
                "m_vout = 1.2003456789e+00",
                "m_iq = -4.5e-05",
                "v(other) = 9.9",
                "m_bad = not_a_number",
            ]
        )
        self.assertEqual(
            runner.parse_measurements(text), {"vout": 1.2003456789, "iq": -4.5e-05}
        )


class _StubPoint:
    def __init__(self, corner_id):
        self.corner_id = corner_id


class _StubResult:
    def __init__(self, corner_id, measurements, status="ok"):
        self.point = _StubPoint(corner_id)
        self.measurements = measurements
        self.status = status


class ChecksTests(unittest.TestCase):
    def setUp(self):
        self.results = [
            _StubResult("a", {"v": 1.0}),
            _StubResult("b", {"v": 1.2}),
            _StubResult("c", {"v": 0.8}),
        ]
        self.summary = report.summarize(self.results, ["v"])

    def test_summary_finds_the_extremes(self):
        stats = self.summary["v"]
        self.assertEqual((stats["min"], stats["min_at"]), (0.8, "c"))
        self.assertEqual((stats["max"], stats["max_at"]), (1.2, "b"))
        self.assertAlmostEqual(stats["spread_pct"], 40.0)

    def test_min_max_violations_are_reported_with_their_corner(self):
        failures = report.evaluate_checks({"v": {"min": 0.9}}, self.results, self.summary)
        self.assertEqual(len(failures), 1)
        self.assertEqual((failures[0]["kind"], failures[0]["at"]), ("min", "c"))

    def test_max_spread_violation(self):
        failures = report.evaluate_checks(
            {"v": {"max_spread_pct": 10.0}}, self.results, self.summary
        )
        self.assertEqual(failures[0]["kind"], "max_spread_pct")

    def test_min_spread_catches_a_grid_that_never_moved(self):
        flat = [_StubResult("a", {"v": 1.0}), _StubResult("b", {"v": 1.0})]
        summary = report.summarize(flat, ["v"])
        failures = report.evaluate_checks({"v": {"min_spread_pct": 5.0}}, flat, summary)
        self.assertEqual(failures[0]["kind"], "min_spread_pct")

    def test_passing_checks_produce_no_failures(self):
        self.assertEqual(
            report.evaluate_checks(
                {"v": {"min": 0.5, "max": 1.5, "max_spread_pct": 50.0}},
                self.results,
                self.summary,
            ),
            [],
        )


class RecordIdTests(unittest.TestCase):
    def test_record_id_matches_the_ratified_shape(self):
        """sim/README.md: <record-id> is <YYYYMMDD>-<HHMMSS>-<short-git-sha>."""
        when = datetime.datetime(2026, 7, 29, 15, 30, 0, tzinfo=datetime.timezone.utc)
        self.assertEqual(report.format_record_id("1a7ef75", when), "20260729-153000-1a7ef75")
        self.assertRegex(
            report.format_record_id("1a7ef75", when), r"^\d{8}-\d{6}-[0-9a-f]{7}$"
        )

    def test_allocation_never_reuses_an_existing_record_id(self):
        when = datetime.datetime(2026, 7, 29, 15, 30, 0, tzinfo=datetime.timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            records = Path(tmp)
            first = report.allocate_record_id(SIM_DIR, records, when)
            (records / f"{first}.md").write_text("# first\n")
            second = report.allocate_record_id(SIM_DIR, records, when)
            self.assertNotEqual(first, second)
            self.assertRegex(second, r"^\d{8}-\d{6}-")
            # the existing record was not touched
            self.assertEqual((records / f"{first}.md").read_text(), "# first\n")

    def test_write_record_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            experiment = Path(tmp) / "an-experiment"
            (experiment / report.RECORDS_DIR).mkdir(parents=True)
            (experiment / report.RECORDS_DIR / "20260729-153000-abc1234.md").write_text("keep\n")
            with self.assertRaises(report.RecordExists):
                report.write_record(
                    {"record_id": "20260729-153000-abc1234"}, experiment
                )


class MatrixConformanceTests(unittest.TestCase):
    """sim/README.md requires the full mandated matrix, or a stated reason."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        tb_dir = Path(self.tmp.name) / "an-experiment" / "testbench"
        tb_dir.mkdir(parents=True)
        (tb_dir / "x.spice").write_text("v1 out 0 dc {vdd_val}\n")
        (tb_dir / "tb.json").write_text(
            json.dumps({"name": "x", "netlist": "x.spice", "measure": {"vout": "v(out)"}})
        )
        self.tb = testbench.load(tb_dir)

    def _grid(self, corner_names, temps, supplies):
        return corners.build_grid(corners.resolve_corners(corner_names), temps, supplies)

    def test_full_matrix_is_recognised(self):
        grid = self._grid(["mos"], (-40, 27, 125), corners.supply_points(3.3, 0.10))
        self.assertEqual(report.matrix_conformance(self.tb, grid), {"full": True, "missing": []})

    def test_missing_temperature_is_flagged(self):
        grid = self._grid(["mos"], (27,), corners.supply_points(3.3, 0.10))
        result = report.matrix_conformance(self.tb, grid)
        self.assertFalse(result["full"])
        self.assertTrue(any("temperature" in m for m in result["missing"]))

    def test_missing_supply_and_process_are_flagged(self):
        grid = self._grid(["tt"], (-40, 27, 125), [3.3])
        result = report.matrix_conformance(self.tb, grid)
        self.assertFalse(result["full"])
        self.assertTrue(any("supply" in m for m in result["missing"]))
        self.assertTrue(any("process" in m for m in result["missing"]))


class RecordRenderingTests(unittest.TestCase):
    """The rendered record carries exactly the fields sim/README.md lists."""

    RATIFIED_FIELDS = (
        "Record ID",
        "Claim",
        "Netlist provenance",
        "Corner matrix run",
        "Statistical convention",
        "Result",
        "Links",
        "Timestamp / author",
        "Supersedes",
    )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        tb_dir = root / "smoke-cell" / "testbench"
        tb_dir.mkdir(parents=True)
        (tb_dir / "x.spice").write_text("v1 out 0 dc {vdd_val}\n")
        (tb_dir / "tb.json").write_text(
            json.dumps(
                {
                    "name": "smoke-cell",
                    "netlist": "x.spice",
                    "measure": {"vout": "v(out)"},
                    "checks": {"vout": {"min": 0.0, "max": 10.0}},
                }
            )
        )
        self.tb = testbench.load(tb_dir)
        self.pdk = fake_pdk(root / "gf180mcuD")
        self.points = corners.build_grid(
            corners.resolve_corners(["mos"]), (-40, 27, 125), corners.supply_points(3.3, 0.10)
        )
        self.results = [
            runner.PointResult(point=p, status="ok", measurements={"vout": 1.0 + i * 0.01})
            for i, p in enumerate(self.points)
        ]
        self.record = report.build_record(
            tb=self.tb,
            pdk=self.pdk,
            points=self.points,
            results=self.results,
            ngspice="ngspice-46",
            repo_root=SIM_DIR,
            record_id="20260729-153000-1a7ef75",
            started_utc="2026-07-29T15:30:00+00:00",
            wall_seconds=9.5,
            claim="spec/usb2-device-phy.md#example",
        )

    def test_every_ratified_field_is_present_and_in_order(self):
        text = report.render_record(self.record, "smoke-cell")
        positions = []
        for field in self.RATIFIED_FIELDS:
            marker = f"**{field}**"
            self.assertIn(marker, text, f"missing ratified field {field!r}")
            positions.append(text.index(marker))
        self.assertEqual(positions, sorted(positions), "fields are out of ratified order")

    def test_links_point_at_the_ratified_paths(self):
        text = report.render_record(self.record, "smoke-cell")
        self.assertIn("sim/smoke-cell/testbench/x.spice", text)
        self.assertIn("sim/smoke-cell/netlist-snapshots/20260729-153000-1a7ef75.spice", text)
        self.assertIn("sim/smoke-cell/corners/20260729-153000-1a7ef75/", text)

    def test_result_table_uses_corner_ids_and_reports_overall_verdict(self):
        text = report.render_record(self.record, "smoke-cell")
        self.assertIn("`tt_-40c_2.97v`", text)
        self.assertIn("`ff_125c_3.63v`", text)
        self.assertIn("**Overall: PASS**", text)

    def test_a_full_matrix_run_says_so(self):
        text = report.render_record(self.record, "smoke-cell")
        self.assertIn("Full PVT matrix per CLAUDE.md", text)

    def test_environment_section_names_the_real_pdk_provenance(self):
        text = report.render_record(self.record, "smoke-cell")
        provenance = self.pdk.provenance()
        self.assertIn(str(provenance["open_pdks_version"]), text)
        self.assertIn(provenance["variant"], text)
        self.assertNotIn("open_pdks `None`", text)

    def test_netlist_snapshot_is_frozen_and_append_only(self):
        experiment = self.tb.experiment_dir
        path = report.write_netlist_snapshot(self.tb, experiment, "20260729-153000-1a7ef75")
        self.assertEqual(path.parent.name, report.SNAPSHOT_DIR)
        self.assertIn("v1 out 0 dc {vdd_val}", path.read_text())
        self.assertIn(self.tb.netlist_sha256, path.read_text())
        with self.assertRaises(report.RecordExists):
            report.write_netlist_snapshot(self.tb, experiment, "20260729-153000-1a7ef75")


# --------------------------------------------------------------------------
# klt sim backend (sim/harness/klt_backend.py) and its CLI dispatch. No PDK,
# no ngspice and no klt: the `klt sim` subprocess is stubbed with canned
# JSON reports, so these exercise only the harness side of the protocol.
# --------------------------------------------------------------------------

KLT_MEASURE = {
    "vth_mv": {"spice": ".meas dc vth_mv WHEN v(out)=v(mid) CROSS=1", "scale": 1000.0},
    "vhi": {"spice": ".meas dc vhi FIND v(out) AT=0.2"},
    "vlo": "v(out)[0]",
}


class _KltFixture(unittest.TestCase):
    """A two-measurement-family testbench + a 2x2x2 grid (tt/ff, -40/27 C, 2.97/3.3 V)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pdk = fake_pdk(self.root / "pdk" / "gf180mcuD")
        self.manifest = {
            "name": "kltx",
            "netlist": "x.spice",
            "measure": {"vth_mv": "1000*vth", "vhi": "v(out)", "vlo": "v(out)"},
            "analyses": ["dc vsw -0.5 0.5 0.001"],
            "corners": ["tt", "ff"],
            "temperatures_c": [-40, 27],
            "supply_tolerance": 0.1,
            "klt_supply_source": "vsup",
            "klt_measure": KLT_MEASURE,
        }
        self.tb_dir = self.root / "kltx-exp" / "testbench"
        self.tb_dir.mkdir(parents=True)
        (self.tb_dir / "x.spice").write_text("vsup vdd 0 dc {vdd_val}\n")
        self._write_manifest()
        self.points = corners.build_grid(
            corners.resolve_corners(["tt", "ff"]), (-40, 27), [2.97, 3.3]
        )
        self.workdir = self.root / "work"

    def _write_manifest(self, **overrides):
        manifest = dict(self.manifest, **overrides)
        manifest = {k: v for k, v in manifest.items() if v is not None}
        (self.tb_dir / "tb.json").write_text(json.dumps(manifest))
        self.tb = testbench.load(self.tb_dir)
        return manifest

    def _request(self, manifest=None, points=None, backend=None, rvc=None) -> dict:
        path = klt_backend.build_request(
            self.tb, self.pdk, self.points if points is None else points, self.workdir,
            123, backend, self.manifest if manifest is None else manifest, rvc,
        )
        return json.loads(path.read_text())

    @staticmethod
    def corner(process, temp, vdd, values, status="ok", **extra):
        c = {
            "corner_id": f"{process}/{temp}/{vdd}",
            "process": process,
            "temperature_c": temp,
            "supply_v": {"vsup": vdd},
            "status": status,
            "runtime_s": 0.5,
            "measurements": [{"name": n, "value": v} for n, v in values.items()],
        }
        c.update(extra)
        return c

    def full_report(self, values=None) -> dict:
        """A passing report with every grid corner, deliberately in reverse order."""
        corners_out = []
        for i, p in enumerate(reversed(self.points)):
            vals = values(p) if values else {"vth_mv": 0.001 * (i + 1), "vhi": 3.0, "vlo": 0.1}
            corners_out.append(self.corner(p.corner.name, p.temp_c, p.vdd, vals))
        return {
            "status": "pass",
            "corners": corners_out,
            "provenance": {"klt_version": "9.9.9"},
            "environment": {"engine_version": "45", "remote": {"job_id": "job-1"}},
        }

    def run_stubbed(self, stdout, returncode=0, stderr="", **kwargs):
        """Run run_grid_klt with `klt sim` replaced by a canned CompletedProcess."""
        if not isinstance(stdout, str):
            stdout = json.dumps(stdout)
        completed = subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)
        with mock.patch.object(klt_backend.subprocess, "run", return_value=completed) as run:
            out = klt_backend.run_grid_klt(
                self.tb, self.pdk, self.points, self.workdir, self.manifest, **kwargs
            )
        self.last_cmd = run.call_args.args[0]
        return out


class KltRequestTests(_KltFixture):
    def test_request_carries_grid_axes_measurements_and_analysis(self):
        req = self._request()
        self.assertEqual(req["netlist"], "body.spice")
        self.assertEqual(req["engine"], "ngspice")
        self.assertEqual(req["models"]["pdk"], "gf180mcuD")
        self.assertEqual([c["name"] for c in req["corners"]["process"]], ["tt", "ff"])
        self.assertEqual(
            req["corners"]["process"][0]["sections"], list(corners.CORNERS["tt"].sections)
        )
        self.assertEqual(req["corners"]["supply_v"], {"vsup": [2.97, 3.3]})
        self.assertEqual(req["corners"]["temperature_c"], [-40.0, 27.0])
        self.assertEqual(req["analysis"], {"kind": "dc", "args": "vsw -0.5 0.5 0.001"})
        self.assertEqual(
            req["measurements"],
            [
                {"name": "vth_mv", "spice": KLT_MEASURE["vth_mv"]["spice"]},
                {"name": "vhi", "spice": KLT_MEASURE["vhi"]["spice"]},
                {"name": "vlo", "expr": "v(out)[0]"},
            ],
        )
        self.assertEqual(req["options"], {"timeout_s": 123, "keep_artifacts": True})

    def test_body_includes_pdk_design_file_and_testbench(self):
        self._request()
        body = (self.workdir / "body.spice").read_text()
        self.assertIn(f'.include "{self.pdk.design_include}"', body)
        self.assertIn(f'.include "{self.tb.netlist}"', body)
        self.assertIn(".param vdd_nom=3.3", body)

    def test_no_backend_and_no_version_check_leave_klt_defaults(self):
        req = self._request()
        self.assertNotIn("backend", req)
        self.assertNotIn("batch", req)

    def test_backend_and_runner_version_check_are_propagated(self):
        req = self._request(backend="batch", rvc="warn")
        self.assertEqual(req["backend"], "batch")
        self.assertEqual(req["batch"], {"runner_version_check": "warn"})

    def test_supply_source_name_comes_from_the_manifest(self):
        manifest = self._write_manifest(klt_supply_source="vdd_src")
        req = self._request(manifest=manifest)
        self.assertEqual(list(req["corners"]["supply_v"]), ["vdd_src"])

    def test_missing_klt_measure_is_refused(self):
        manifest = self._write_manifest(klt_measure=None)
        with self.assertRaisesRegex(klt_backend.KltError, "klt_measure"):
            self._request(manifest=manifest)

    def test_mismatched_measurement_keys_are_refused(self):
        for bad in (
            {"vth_mv": "x", "vhi": "x"},                       # one missing
            dict(KLT_MEASURE, extra="v(out)"),                 # one extra
            {"vth_mv": "x", "vhi": "x", "vlow": "x"},          # one misspelt
        ):
            with self.subTest(keys=sorted(bad)):
                with self.assertRaisesRegex(klt_backend.KltError, "differ from measure keys"):
                    self._request(manifest=dict(self.manifest, klt_measure=bad))

    def test_malformed_klt_measure_entry_is_refused(self):
        for bad in ({"scale": 2.0}, {"spice": 3}, 42):
            with self.subTest(entry=bad):
                manifest = dict(self.manifest, klt_measure=dict(KLT_MEASURE, vhi=bad))
                with self.assertRaisesRegex(klt_backend.KltError, "klt_measure"):
                    self._request(manifest=manifest)

    def test_more_than_one_analysis_is_refused(self):
        manifest = self._write_manifest(analyses=["op", "dc vsw 0 1 0.1"])
        with self.assertRaisesRegex(klt_backend.KltError, "exactly one analysis"):
            self._request(manifest=manifest)

    def test_non_factorial_grid_is_refused(self):
        dropped = self.points[:-1]
        with self.assertRaisesRegex(klt_backend.KltError, "full factorial"):
            self._request(points=dropped)

    def test_duplicate_cannot_mask_a_missing_point(self):
        # Same length as the full grid, same axis values -- but one point is
        # duplicated and another is absent. A count-only check would pass this.
        tampered = self.points[:-1] + [self.points[0]]
        self.assertEqual(len(tampered), len(self.points))
        with self.assertRaisesRegex(klt_backend.KltError, "full factorial"):
            self._request(points=tampered)


class KltRunGridTests(_KltFixture):
    def test_command_line_and_backend_info(self):
        _, info = self.run_stubbed(self.full_report(), backend="batch", runner_version_check="warn")
        self.assertEqual(self.last_cmd[:2], ["klt", "sim"])
        self.assertEqual(self.last_cmd[2], str(self.workdir / "request.json"))
        self.assertIn("--format", self.last_cmd)
        self.assertEqual(self.last_cmd[-2:], ["--backend", "batch"])
        req = json.loads((self.workdir / "request.json").read_text())
        self.assertEqual(req["batch"], {"runner_version_check": "warn"})
        self.assertEqual(info["backend"], "batch")
        self.assertEqual(info["klt_exit_code"], 0)
        self.assertEqual(info["klt_status"], "pass")
        self.assertEqual(info["klt_version"], "9.9.9")
        self.assertEqual(info["engine_version"], "45")
        self.assertEqual(info["remote"], {"job_id": "job-1"})
        self.assertTrue((self.workdir / "klt-report.json").is_file())

    def test_default_backend_passes_no_backend_flag(self):
        _, info = self.run_stubbed(self.full_report())
        self.assertNotIn("--backend", self.last_cmd)
        self.assertEqual(info["backend"], "request-default")

    def test_results_come_back_in_grid_order_with_scaling(self):
        def values(p):
            # Encode the point in the value so a mis-mapping is visible.
            tag = {"tt": 0, "ff": 1}[p.corner.name] * 100 + (p.temp_c + 40) + p.vdd
            return {"vth_mv": tag / 1000.0, "vhi": tag, "vlo": -tag}

        seen = []
        results, _ = self.run_stubbed(self.full_report(values), on_result=seen.append)
        self.assertEqual([r.point for r in results], self.points)
        self.assertEqual(seen, results)
        for r in results:
            tag = {"tt": 0, "ff": 1}[r.point.corner.name] * 100 + (r.point.temp_c + 40) + r.point.vdd
            with self.subTest(point=r.point.corner_id):
                self.assertEqual(r.status, "ok")
                self.assertAlmostEqual(r.measurements["vth_mv"], tag)   # x1000 scale
                self.assertAlmostEqual(r.measurements["vhi"], tag)      # dict, no scale
                self.assertAlmostEqual(r.measurements["vlo"], -tag)     # expr string
                self.assertEqual(r.missing, [])

    def test_float_noise_in_reported_axes_still_maps(self):
        report_ = self.full_report()
        for c in report_["corners"]:
            c["supply_v"]["vsup"] += 1e-9
            c["temperature_c"] = c["temperature_c"] + 1e-9
        results, _ = self.run_stubbed(report_)
        self.assertTrue(all(r.status == "ok" for r in results))

    def test_corner_missing_from_report_is_an_error_point(self):
        report_ = self.full_report()
        report_["corners"] = report_["corners"][1:]   # drops the last grid point
        results, _ = self.run_stubbed(report_)
        self.assertEqual([r.status for r in results[:-1]], ["ok"] * (len(self.points) - 1))
        self.assertEqual(results[-1].status, "error")
        self.assertIn("corner missing", results[-1].message)
        self.assertEqual(results[-1].missing, list(self.tb.measure))

    def test_missing_measurement_fails_the_point(self):
        report_ = self.full_report()
        target = self.points[0]
        for c in report_["corners"]:
            if (c["process"], c["temperature_c"], c["supply_v"]["vsup"]) == (
                target.corner.name, target.temp_c, target.vdd
            ):
                c["measurements"] = [m for m in c["measurements"] if m["name"] != "vhi"]
        results, _ = self.run_stubbed(report_)
        self.assertEqual(results[0].status, "failed")
        self.assertEqual(results[0].missing, ["vhi"])
        self.assertIn("vth_mv", results[0].measurements)

    def test_corner_with_no_usable_measurements_is_an_error(self):
        report_ = self.full_report()
        report_["corners"][-1]["measurements"] = [
            {"name": "vth_mv", "value": None},          # failed .meas
            {"name": "vhi", "value": "nan-ish"},        # non-numeric
            {"value": 1.0},                             # no name
            "garbage",                                  # not an object
        ]
        results, _ = self.run_stubbed(report_)
        # reversed order: the report's last corner is the grid's first point
        self.assertEqual(results[0].status, "error")
        self.assertEqual(sorted(results[0].missing), ["vhi", "vlo", "vth_mv"])

    def test_corner_error_status_carries_diagnostics(self):
        report_ = self.full_report()
        report_["corners"][-1].update(
            status="error",
            measurements=[],
            diagnostics=[{"code": "E_CONV", "message": "timestep too small"}, "junk"],
        )
        results, _ = self.run_stubbed(report_)
        self.assertEqual(results[0].status, "error")
        self.assertIn("E_CONV: timestep too small", results[0].message)

    def test_measurements_not_in_the_testbench_are_ignored(self):
        report_ = self.full_report()
        for c in report_["corners"]:
            c["measurements"].append({"name": "stray", "value": 1.0})
        results, _ = self.run_stubbed(report_)
        self.assertTrue(all("stray" not in r.measurements for r in results))
        self.assertTrue(all(r.status == "ok" for r in results))

    def test_malformed_corner_entries_become_missing_points(self):
        report_ = self.full_report()
        report_["corners"][-1]["supply_v"] = "3.3"            # not a map
        report_["corners"][-2]["temperature_c"] = "hot"       # not a number
        report_["corners"].append("not-a-corner")
        results, _ = self.run_stubbed(report_)
        self.assertEqual(results[0].status, "error")
        self.assertEqual(results[1].status, "error")
        self.assertTrue(all(r.status == "ok" for r in results[2:]))

    def test_non_json_output_raises_and_keeps_stdout(self):
        with self.assertRaisesRegex(klt_backend.KltError, r"no JSON report \(exit 2\)"):
            self.run_stubbed("Traceback: boom", returncode=2, stderr="fleet down")
        self.assertEqual((self.workdir / "klt-stdout.txt").read_text(), "Traceback: boom")
        self.assertEqual((self.workdir / "klt-stderr.txt").read_text(), "fleet down")

    def test_json_that_is_not_a_report_object_raises(self):
        for bad in ([], "\"pass\"", {"corners": "none"}):
            with self.subTest(stdout=bad):
                with self.assertRaisesRegex(klt_backend.KltError, "not a report object"):
                    self.run_stubbed(bad if isinstance(bad, str) else json.dumps(bad))

    def test_failed_klt_run_with_report_marks_every_point_error(self):
        report_ = {"status": "error", "corners": [], "diagnostics": [{"code": "E_SKEW"}]}
        results, info = self.run_stubbed(report_, returncode=1)
        self.assertEqual({r.status for r in results}, {"error"})
        self.assertIn("klt status error", results[0].message)
        self.assertEqual(info["klt_exit_code"], 1)
        self.assertEqual(info["klt_status"], "error")

    def test_klt_not_on_path_is_a_klt_error(self):
        with mock.patch.object(klt_backend.subprocess, "run", side_effect=FileNotFoundError("klt")):
            with self.assertRaisesRegex(klt_backend.KltError, "not found"):
                klt_backend.run_grid_klt(
                    self.tb, self.pdk, self.points, self.workdir, self.manifest
                )

    def test_logs_are_copied_from_artifacts_or_synthesised(self):
        report_ = self.full_report()
        art = self.root / "corner0.log"
        art.write_text("real ngspice log\n")
        report_["corners"][-1]["artifacts"] = {"log": str(art)}   # grid point 0
        log_dir = self.root / "logs"
        results, _ = self.run_stubbed(report_, log_dir=log_dir)
        self.assertEqual(results[0].log, f"{self.points[0].corner_id}.log")
        self.assertEqual((log_dir / results[0].log).read_text(), "real ngspice log\n")
        synthesized = (log_dir / results[1].log).read_text()
        self.assertIn("klt sim corner", synthesized)
        self.assertIn('"status": "ok"', synthesized)


class KltCliTests(_KltFixture):
    def setUp(self):
        super().setUp()
        self.calls = []
        patches = [
            mock.patch.object(cli, "find_pdk", return_value=self.pdk),
            mock.patch.object(cli, "WORK_DIR", self.root / ".work"),
            mock.patch.object(
                cli.report, "git_provenance",
                return_value={"commit": "a" * 40, "short": "aaaaaaa", "branch": "t", "dirty": False},
            ),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def fake_run_grid_klt(self, tb, pdk, points, workdir, manifest, **kwargs):
        self.calls.append({"manifest": manifest, **kwargs})
        results = [
            runner.PointResult(point=p, status="ok",
                               measurements={"vth_mv": 1.0, "vhi": 3.0, "vlo": 0.0})
            for p in points
        ]
        return results, {"backend": kwargs.get("backend") or "request-default",
                         "engine_version": "45", "klt_version": "9.9.9",
                         "klt_status": "pass", "remote": None, "klt_exit_code": 0,
                         "wall_seconds": 0.0}

    def main(self, *extra, ngspice="ngspice-44"):
        argv = [str(self.tb_dir), "--no-write", "--quiet", *extra]
        ng = (mock.patch.object(cli.runner, "ngspice_version", return_value=ngspice)
              if ngspice else
              mock.patch.object(cli.runner, "ngspice_version",
                                side_effect=runner.NgspiceMissing("no ngspice")))
        out, err = io.StringIO(), io.StringIO()
        with ng, redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_backend_klt_dispatches_to_klt_backend(self):
        with mock.patch.object(cli.klt_backend, "run_grid_klt", side_effect=self.fake_run_grid_klt), \
             mock.patch.object(cli.runner, "run_grid") as local:
            code, out, _ = self.main("--backend", "klt")
        self.assertEqual(code, cli.EXIT_OK)
        local.assert_not_called()
        self.assertEqual(len(self.calls), 1)
        self.assertIsNone(self.calls[0]["backend"])
        self.assertIsNone(self.calls[0]["runner_version_check"])
        self.assertEqual(self.calls[0]["manifest"]["klt_measure"], KLT_MEASURE)
        self.assertIn("klt sim", out)

    def test_backend_name_and_version_check_are_forwarded(self):
        with mock.patch.object(cli.klt_backend, "run_grid_klt", side_effect=self.fake_run_grid_klt):
            code, _, _ = self.main("--backend", "klt:batch", "--klt-runner-version-check", "warn")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(self.calls[0]["backend"], "batch")
        self.assertEqual(self.calls[0]["runner_version_check"], "warn")

    def test_default_backend_is_the_local_runner(self):
        def local(tb, pdk, points, workdir, **kwargs):
            return self.fake_run_grid_klt(tb, pdk, points, workdir, {})[0]

        with mock.patch.object(cli.klt_backend, "run_grid_klt") as klt, \
             mock.patch.object(cli.runner, "run_grid", side_effect=local) as run_local:
            code, _, _ = self.main()
        self.assertEqual(code, cli.EXIT_OK)
        klt.assert_not_called()
        run_local.assert_called_once()

    def test_klt_error_maps_to_the_environment_exit_code(self):
        boom = klt_backend.KltError("klt sim produced no JSON report")
        with mock.patch.object(cli.klt_backend, "run_grid_klt", side_effect=boom):
            code, _, err = self.main("--backend", "klt")
        self.assertEqual(code, cli.EXIT_ENVIRONMENT)
        self.assertIn("no JSON report", err)

    def test_unknown_backend_is_refused_before_running(self):
        with mock.patch.object(cli.klt_backend, "run_grid_klt") as klt, \
             mock.patch.object(cli.runner, "run_grid") as local:
            code, _, err = self.main("--backend", "klt-batch")
        self.assertEqual(code, cli.EXIT_ENVIRONMENT)
        self.assertIn("unknown --backend", err)
        klt.assert_not_called()
        local.assert_not_called()

    def test_klt_backend_does_not_need_local_ngspice(self):
        with mock.patch.object(cli.klt_backend, "run_grid_klt", side_effect=self.fake_run_grid_klt):
            code, _, _ = self.main("--backend", "klt", ngspice=None)
        self.assertEqual(code, cli.EXIT_OK)

    def test_local_backend_still_needs_ngspice(self):
        with mock.patch.object(cli.runner, "run_grid") as local:
            code, _, err = self.main(ngspice=None)
        self.assertEqual(code, cli.EXIT_ENVIRONMENT)
        self.assertIn("no ngspice", err)
        local.assert_not_called()


if __name__ == "__main__":
    unittest.main()
