#!/usr/bin/env python3
"""Self-test for the per-plan process isolation in ``gen_analog_layout.py``.

Issue #335: the byte order of a generated stream depended on which other
plans had run earlier in the same interpreter, so a block's recorded
``gds_sha256`` stopped reproducing when a sibling plan started executing.
The fix runs every plan in its own process. These cases pin that contract
without needing klt or the PDK (both are stubbed), so they run in CI:

  * a run with more than one plan sends *every* plan through the isolated
    path, and a lone plan runs in-process (it already owns its interpreter);
  * a child (``--emit-block-report``) never isolates again -- no recursion;
  * a block that fails to execute still comes back as an entry and does not
    stop its siblings;
  * an isolated run that reports nothing fails the whole run (exit 1), and a
    stale entry file from an earlier run is never mistaken for a fresh one.

Issue #346: LVS found every committed stream mismatching on the same three
things -- floating PMOS wells, an untied substrate, and a labelled port set
that was not the schematic's. All three are decided by
``_netlist_pin_map()`` / ``_write_pin_labels()``, so these cases pin that
contract too, on synthetic plan/digest inputs (klt is stubbed here as well):

  * every device body resolves to the net the schematic puts it on, and is
    tied through one of its group's own tap pads;
  * a group whose devices disagree on their body net is a reported problem,
    never a silent short, and a group with no tap pad is reported untied
    rather than tied to nothing;
  * the terminal map covers one-pin nets, which the plan's own ``nets[]``
    omits because there is nothing to route;
  * a tap pad takes its via on the port point, not inset like a full-height
    source/drain strip -- a 0.42um pad cannot hold an inset 0.26um via.

Issue #406: the body strap's two inputs become measurements, not assertions.
``StrapBodyPadsTests`` calls ``_strap_body_pads()`` directly on real klayout
geometry (skipped where ``klayout.db`` is not importable -- it needs the
boolean engine, not a stub; CI installs klayout-tools first):

  * a strap leg is measured against every leg drawn for an earlier group in
    the same run -- legs are accumulated explicitly instead of trusting
    KLayout's live-view regions (``klt_m1`` re-read the cell through lazy
    evaluation, an implementation detail, not a contract);
  * the tap-pad square is derived from the stream at each port coordinate
    and checked against ``PAD_SQUARE_UM``: drift is refused with a problem,
    not silently absorbed;
  * a tap pad with no metal-1 at its port is refused loudly, never silently
    falling back to the constant.

Issue #427: the report's ``bbox_um`` was klt's plan-stage envelope while
``gds_path`` named the post-scripted-routing stream -- for
``differential_driver`` that envelope was ~19% low in height, because the
upper-metal tracks ``_complete_routing()`` draws are absent from the plan
stream. ``BlockBboxSourceTests`` pins, on real fixture streams (needs
``klayout.db``, like ``StrapBodyPadsTests``):

  * a scripted block's ``bbox_um`` is the extent of the stream at
    ``gds_path``, measured after ``_complete_routing()``; the plan-stage
    envelope survives only under ``plan_bbox_um``;
  * a non-scripted block whose plan envelope already matches its stream
    emits the same value either way.

Usage:
    python3 scripts/test_gen_analog_layout.py
Exit codes: 0 all cases behave as specified, 1 otherwise.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import gen_analog_layout as gal  # noqa: E402


def _entry(block: str, status: str = "executed") -> dict:
    """A block entry with just the keys the report/summary path reads."""
    if status != "executed":
        return {"block": block, "status": status, "message": "stubbed failure"}
    return {
        "block": block,
        "status": status,
        "klt_exit_code": 0,
        "gds_path": f"layout/analog/out/{block}.gds",
        "device_group_count": 1,
        "net_count": 2,
        "routed_net_count": 2,
        "klt_routed_net_count": 2,
        "unrouted_nets": [],
        "unmapped_netlist_nets": [],
        "bbox_um": None,
        "warning_count": 0,
        "drc": {"status": "clean", "violation_count": 0, "by_rule": {}},
        "routing": {
            "snapped_instances": 0,
            "l2n_net_count": 2,
            "shorts": [],
            "problems": [],
            "methods": {"klt-plan": 2, "scripted": 0},
        },
    }


class _Stubs:
    """Make ``main()`` reach the dispatch without klt, klayout or a PDK."""

    def __enter__(self):
        self.saved_modules = {
            name: sys.modules.get(name) for name in ("klayout_tools", "klayout", "klayout.db")
        }
        kt = types.ModuleType("klayout_tools")
        kt.__version__ = "0.0.0-stub"
        klayout = types.ModuleType("klayout")
        kdb = types.ModuleType("klayout.db")
        klayout.db = kdb
        sys.modules.update({"klayout_tools": kt, "klayout": klayout, "klayout.db": kdb})
        self.saved_env = os.environ.get("PDK_ROOT")
        os.environ["PDK_ROOT"] = "/nonexistent-stub-pdk"
        return self

    def __exit__(self, *exc):
        for name, mod in self.saved_modules.items():
            if mod is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod
        if self.saved_env is None:
            os.environ.pop("PDK_ROOT", None)
        else:
            os.environ["PDK_ROOT"] = self.saved_env
        return False


class IsolationDispatchTests(unittest.TestCase):
    """Which plans go through a child process, and which run in-process."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = self._tmp.name
        self.isolated: list[str] = []
        self.in_process: list[str] = []
        self._real = (gal._execute_plan, gal._execute_plan_isolated)

        def fake_isolated(plan_path, out_dir, keep_work):
            block = Path(plan_path).stem
            self.isolated.append(block)
            return _entry(block)

        def fake_in_process(plan_path, out_dir, keep_work, final_dir):
            block = Path(plan_path).stem
            self.in_process.append(block)
            return _entry(block)

        gal._execute_plan_isolated = fake_isolated
        gal._execute_plan = fake_in_process

    def tearDown(self):
        gal._execute_plan, gal._execute_plan_isolated = self._real
        self._tmp.cleanup()

    def run_main(self, *argv):
        buf = io.StringIO()
        with _Stubs(), contextlib.redirect_stdout(buf):
            rc = gal.main(["--out-dir", self.out, "--format", "json", *argv])
        return rc, buf.getvalue()

    def test_every_plan_is_isolated_when_more_than_one_runs(self):
        rc, out = self.run_main()
        self.assertEqual(rc, 0)
        plans = sorted(p.stem for p in Path(gal.PLAN_DIR).glob("*.json"))
        self.assertGreater(len(plans), 1, "the repo should carry several plans")
        # Every plan ran in its own process; none shared this interpreter.
        self.assertEqual(sorted(self.isolated), plans)
        self.assertEqual(self.in_process, [])
        report = json.loads(out)
        self.assertEqual([b["block"] for b in report["blocks"]], plans)

    def test_two_selected_blocks_are_both_isolated(self):
        rc, _ = self.run_main("--blocks", "dplus_pullup", "differential_receiver")
        self.assertEqual(rc, 0)
        self.assertEqual(sorted(self.isolated), ["differential_receiver", "dplus_pullup"])
        self.assertEqual(self.in_process, [])

    def test_a_lone_plan_runs_in_process(self):
        # One plan already has an interpreter to itself -- spawning a child
        # would cost a process and change nothing.
        rc, _ = self.run_main("--blocks", "dplus_pullup")
        self.assertEqual(rc, 0)
        self.assertEqual(self.in_process, ["dplus_pullup"])
        self.assertEqual(self.isolated, [])

    def test_a_child_never_isolates_again(self):
        entry_path = os.path.join(self.out, "entry.json")
        rc, out = self.run_main(
            "--blocks", "dplus_pullup", "--emit-block-report", entry_path
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self.isolated, [], "a child must not spawn grandchildren")
        self.assertEqual(self.in_process, ["dplus_pullup"])
        # The child writes the entry and prints no report of its own.
        self.assertEqual(out, "")
        with open(entry_path, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["block"], "dplus_pullup")

    def test_execute_failed_in_one_block_does_not_stop_the_others(self):
        def failing(plan_path, out_dir, keep_work):
            block = Path(plan_path).stem
            self.isolated.append(block)
            if block == "differential_driver":
                return _entry(block, status="execute-failed")
            return _entry(block)

        gal._execute_plan_isolated = failing
        rc, out = self.run_main()
        self.assertEqual(rc, 0, "a block that cannot execute is reported, not fatal")
        report = json.loads(out)
        by_block = {b["block"]: b for b in report["blocks"]}
        self.assertEqual(by_block["differential_driver"]["status"], "execute-failed")
        self.assertEqual(report["summary"]["executed"], len(by_block) - 1)
        for block, entry in by_block.items():
            if block != "differential_driver":
                self.assertEqual(entry["status"], "executed", block)


class IsolatedRunContractTests(unittest.TestCase):
    """What ``_execute_plan_isolated`` asks of the child, and how it fails."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = self._tmp.name
        self.plan = os.path.join(self.out, "dplus_pullup.json")
        Path(self.plan).write_text("{}", encoding="utf-8")
        self.entry_path = os.path.join(self.out, "dplus_pullup-block-report.json")
        self._real_run = subprocess.run
        self.calls: list[list[str]] = []

    def tearDown(self):
        subprocess.run = self._real_run
        self._tmp.cleanup()

    def fake_child(self, *, rc=0, payload=None, stderr=""):
        def runner(argv, **kwargs):
            self.calls.append(list(argv))
            if payload is not None:
                with open(self.entry_path, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle)
            return subprocess.CompletedProcess(argv, rc, "", stderr)

        subprocess.run = runner

    def test_child_argv_restricts_the_run_to_one_block(self):
        self.fake_child(payload=_entry("dplus_pullup"))
        entry = gal._execute_plan_isolated(self.plan, self.out, False)
        self.assertEqual(entry["block"], "dplus_pullup")
        argv = self.calls[0]
        self.assertEqual(argv[0], sys.executable)
        self.assertEqual(os.path.basename(argv[1]), "gen_analog_layout.py")
        self.assertEqual(argv[argv.index("--blocks") + 1], "dplus_pullup")
        self.assertEqual(argv[argv.index("--out-dir") + 1], self.out)
        self.assertEqual(argv[argv.index("--emit-block-report") + 1], self.entry_path)
        # Only one block is ever named, so the child cannot see a sibling.
        self.assertEqual(argv.count("--blocks"), 1)
        self.assertNotIn("--keep-work", argv)
        self.assertNotIn("--deliver", argv)
        self.assertNotIn("--check", argv)

    def test_keep_work_is_forwarded_only_when_asked(self):
        self.fake_child(payload=_entry("dplus_pullup"))
        gal._execute_plan_isolated(self.plan, self.out, True)
        self.assertIn("--keep-work", self.calls[0])

    def test_execute_failed_entry_is_returned_verbatim(self):
        payload = _entry("dplus_pullup", status="execute-failed")
        self.fake_child(payload=payload)
        self.assertEqual(gal._execute_plan_isolated(self.plan, self.out, False), payload)

    def test_a_child_that_fails_without_a_report_fails_the_run(self):
        self.fake_child(rc=1, stderr="boom")
        with self.assertRaises(SystemExit) as caught:
            with contextlib.redirect_stderr(io.StringIO()):
                gal._execute_plan_isolated(self.plan, self.out, False)
        self.assertEqual(caught.exception.code, 1)

    def test_a_child_that_exits_zero_without_a_report_fails_the_run(self):
        self.fake_child(rc=0)  # no payload written
        with self.assertRaises(SystemExit) as caught:
            with contextlib.redirect_stderr(io.StringIO()):
                gal._execute_plan_isolated(self.plan, self.out, False)
        self.assertEqual(caught.exception.code, 1)

    def test_a_stale_entry_is_never_mistaken_for_a_fresh_one(self):
        # An entry left by an earlier run must be removed before the child
        # starts, or a silent child would hand back last run's hash.
        with open(self.entry_path, "w", encoding="utf-8") as handle:
            json.dump(_entry("dplus_pullup"), handle)
        self.fake_child(rc=0)  # child writes nothing this time
        with self.assertRaises(SystemExit) as caught:
            with contextlib.redirect_stderr(io.StringIO()):
                gal._execute_plan_isolated(self.plan, self.out, False)
        self.assertEqual(caught.exception.code, 1)
        self.assertFalse(os.path.exists(self.entry_path))

    def test_child_stderr_is_forwarded_not_swallowed(self):
        self.fake_child(payload=_entry("dplus_pullup"), stderr="klt warning: hi\n")
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            gal._execute_plan_isolated(self.plan, self.out, False)
        self.assertIn("klt warning: hi", buf.getvalue())


class ChildFlagUsageTests(unittest.TestCase):
    """``--emit-block-report`` is an internal flag; misuse is a usage error."""

    def usage_error(self, *argv):
        with self.assertRaises(SystemExit) as caught:
            with contextlib.redirect_stderr(io.StringIO()):
                gal.main(list(argv))
        return caught.exception.code

    def test_needs_exactly_one_block(self):
        self.assertEqual(self.usage_error("--emit-block-report", "/tmp/x"), 2)
        self.assertEqual(
            self.usage_error(
                "--emit-block-report", "/tmp/x", "--blocks", "dplus_pullup",
                "se_receiver_dp",
            ),
            2,
        )

    def test_incompatible_with_deliver_and_check(self):
        for flag in ("--deliver", "--check"):
            self.assertEqual(
                self.usage_error(
                    "--emit-block-report", "/tmp/x", "--blocks", "dplus_pullup", flag
                ),
                2,
            )

    def test_hidden_from_help(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit):
            gal.main(["--help"])
        self.assertNotIn("--emit-block-report", buf.getvalue())


# ---------------------------------------------------------------------------
# Issue #346: body ties and the labelled port set
# ---------------------------------------------------------------------------


def _mos_ports(prefix: str = "U0", taps: int = 4) -> list[dict]:
    """``mos_array``-shaped ports: three terminals plus corner tap pads."""
    ports = [
        {"name": f"{prefix}_S", "x_um": 0.21, "y_um": 2.0, "direction_deg": 180},
        {"name": f"{prefix}_D", "x_um": 1.29, "y_um": 2.0, "direction_deg": 0},
        {"name": f"{prefix}_G", "x_um": 0.75, "y_um": 4.96, "direction_deg": 90},
    ]
    corners = [(-0.65, -0.86, 270), (-0.65, 6.28, 90), (2.15, -0.86, 270), (2.15, 6.28, 90)]
    for index, (x, y, direction) in enumerate(corners[:taps]):
        ports.append(
            {"name": f"TAP_PAD{index}", "x_um": x, "y_um": y, "direction_deg": direction}
        )
    return ports


class _KltPlanStub:
    """Stand in for the two ``layout_plan_execute`` internals
    ``_netlist_pin_map`` reads, so these cases need no klt install."""

    def __enter__(self):
        import klayout_tools  # noqa: F401  -- may itself be a _Stubs module

        self.saved = sys.modules.get("klayout_tools.layout_plan_execute")
        module = types.ModuleType("klayout_tools.layout_plan_execute")
        module._TERMINAL_SUFFIXES = {
            "mos_array": {"S": "S", "D": "D", "G": "G"},
            "res_array": {"A": "A", "B": "B"},
        }

        def owned(ports, suffix):
            marker = f"_{suffix}"
            return [p["name"] for p in ports if p["name"].endswith(marker)]

        module._device_owned_port_names = owned
        sys.modules["klayout_tools.layout_plan_execute"] = module
        return self

    def __exit__(self, *exc):
        if self.saved is None:
            sys.modules.pop("klayout_tools.layout_plan_execute", None)
        else:
            sys.modules["klayout_tools.layout_plan_execute"] = self.saved
        return False


class BodyTieTests(unittest.TestCase):
    """``_netlist_pin_map``: causes A and B of issue #346."""

    def setUp(self):
        self._stubs = _Stubs().__enter__()
        self._klt = _KltPlanStub().__enter__()
        self.addCleanup(self._klt.__exit__, None, None, None)
        self.addCleanup(self._stubs.__exit__, None, None, None)

    @staticmethod
    def _inputs(bodies=("VSS", "VDD"), taps=4):
        response = {
            "device_groups": [
                {"id": "mn_a", "generator": "mos_array",
                 "devices": [{"name": "NA", "device_class": "NFET"}]},
                {"id": "mp_a", "generator": "mos_array",
                 "devices": [{"name": "PA", "device_class": "PFET"}]},
            ]
        }
        compose = {
            "blocks": [
                {"id": "mn_a", "generator_report": {"ports": _mos_ports(taps=taps)}},
                {"id": "mp_a", "generator_report": {"ports": _mos_ports(taps=taps)}},
            ]
        }
        digest = {
            "devices": [
                {"name": "NA", "device_class": "NFET",
                 "terminals": {"S": "VSS", "D": "OUT", "G": "IN", "B": bodies[0]}},
                {"name": "PA", "device_class": "PFET",
                 "terminals": {"S": "VDD", "D": "OUT", "G": "IN", "B": bodies[1]}},
            ],
            "nets": [],
        }
        return response, compose, digest

    def test_every_drawn_tap_pad_is_tied_to_its_schematic_net(self):
        pin_map = gal._netlist_pin_map(*self._inputs())
        self.assertEqual(
            {net: [p["block"] for p in pins] for net, pins in pin_map["ties"].items()},
            {"VSS": ["mn_a"] * 4, "VDD": ["mp_a"] * 4},
        )
        self.assertEqual(pin_map["problems"], [])
        self.assertEqual(pin_map["untied"], [])
        for pins in pin_map["ties"].values():
            for pin in pins:
                self.assertTrue(pin["port"].startswith(gal.TAP_PAD_PREFIX))
        # Every drawn pad of the group appears exactly once, in a stable order.
        for pins in pin_map["ties"].values():
            self.assertEqual(
                [p["port"] for p in pins],
                [f"TAP_PAD{i}" for i in range(4)],
            )

    def test_a_pfet_group_ties_its_nwell_pads_too(self):
        # The n-well side: the same tie rule covers a pfet group's drawn
        # n-well pads -- one tie pin per drawn pad, not one per group.
        pin_map = gal._netlist_pin_map(*self._inputs())
        ports = {p["name"] for p in _mos_ports()}
        tied = {p["port"] for p in pin_map["ties"]["VDD"]}
        self.assertEqual(tied, {name for name in ports if name.startswith("TAP_PAD")})

    def test_the_escape_pad_is_still_a_bottom_facing_one(self):
        # The strap carries the group's pads to the rail through ONE escape
        # per group, and that escape keeps dropping straight into the bottom
        # channel: the bottom-facing pad nearest the group's x centre. The
        # tied SET is no longer all-bottom-facing -- the stub's two 90-facing
        # corner pads are tied too, which is what the old assertion could not
        # express.
        pin_map = gal._netlist_pin_map(*self._inputs())
        ports = {p["name"]: p for p in _mos_ports()}
        for net, pins in pin_map["ties"].items():
            by_block: dict[str, list[dict]] = {}
            for pin in pins:
                by_block.setdefault(pin["block"], []).append(ports[pin["port"]])
            for block, pad_ports in by_block.items():
                escape = gal._tap_pad_pin(pad_ports)
                self.assertIsNotNone(escape)
                self.assertEqual(ports[escape]["direction_deg"], 270)

    def test_terminal_map_covers_one_pin_nets(self):
        # 'IN' has a single terminal, so the plan's own nets[] omits it -- it
        # still has to be resolvable, or the port cannot be labelled.
        pin_map = gal._netlist_pin_map(*self._inputs())
        self.assertEqual(
            sorted(pin_map["terminals"]), ["IN", "OUT", "VDD", "VSS"]
        )
        self.assertEqual(
            [(p["block"], p["port"]) for p in pin_map["terminals"]["IN"]],
            [("mn_a", "U0_G"), ("mp_a", "U0_G")],
        )

    def test_disagreeing_bodies_are_a_problem_not_a_short(self):
        response, compose, digest = self._inputs()
        digest["devices"].append(
            {"name": "PB", "device_class": "PFET",
             "terminals": {"S": "VDD", "D": "OUT", "G": "IN", "B": "VPU_REG"}}
        )
        response["device_groups"][1]["devices"].append(
            {"name": "PB", "device_class": "PFET"}
        )
        pin_map = gal._netlist_pin_map(response, compose, digest)
        self.assertNotIn("VPU_REG", pin_map["ties"])
        self.assertNotIn("VDD", pin_map["ties"])
        self.assertEqual(len(pin_map["problems"]), 1)
        self.assertIn("mp_a", pin_map["problems"][0])

    def test_a_group_without_tap_pads_is_reported_untied(self):
        pin_map = gal._netlist_pin_map(*self._inputs(taps=0))
        self.assertEqual(pin_map["ties"], {})
        self.assertEqual(
            sorted((u["block"], u["net"]) for u in pin_map["untied"]),
            [("mn_a", "VSS"), ("mp_a", "VDD")],
        )
        self.assertEqual(pin_map["problems"], [])

    def test_a_resistors_second_terminal_is_not_a_body(self):
        response = {
            "device_groups": [
                {"id": "r_1", "generator": "res_array",
                 "devices": [{"name": "1", "device_class": "PPOLYF_U_1K"}]}
            ]
        }
        compose = {
            "blocks": [
                {"id": "r_1", "generator_report": {"ports": [
                    {"name": "R0_A", "x_um": 0.0, "y_um": 1.0, "direction_deg": 180},
                    {"name": "R0_B", "x_um": 4.0, "y_um": 1.0, "direction_deg": 0},
                ]}}
            ]
        }
        digest = {
            "devices": [
                {"name": "1", "device_class": "PPOLYF_U_1K",
                 "terminals": {"A": "VREF", "B": "VDD", "W": "VSS"}}
            ],
            "nets": [],
        }
        pin_map = gal._netlist_pin_map(response, compose, digest)
        # B is a wired terminal here, W is the body -- and with no tap pad of
        # its own it is reported untied, reaching ground through the shared
        # substrate the nfet groups tie.
        self.assertEqual(
            [(p["block"], p["port"]) for p in pin_map["terminals"]["VDD"]],
            [("r_1", "R0_B")],
        )
        self.assertEqual(pin_map["untied"], [{"block": "r_1", "net": "VSS"}])
        self.assertEqual(pin_map["ties"], {})


class BodyStrapTests(unittest.TestCase):
    """``_body_strap_boxes``: the perimeter rule, measured not asserted.

    ``mos_array`` draws every tap pad on the cell boundary -- pad columns at
    the left/right edges, pad rows across the bottom/top and down the sides
    -- so a strap confined to the pads' own coordinates cannot reach the
    device. These tests pin that confinement: no box covers a device port,
    and every pad is covered.
    """

    CORNER_PADS = [(-0.65, -0.86), (-0.65, 7.28), (1.93, -0.86), (1.93, 7.28)]
    # A tall mn_2dm-shaped group: corners plus mid-side pads.
    SIDE_PADS = [
        (-0.65, -0.86), (-0.65, 32.28), (1.93, -0.86), (1.93, 32.28),
        (-0.86, 15.71), (2.14, 15.71),
    ]
    DEVICE_PORTS = [(0.21, 2.0), (1.29, 2.0), (0.75, 4.96)]  # S, D, G

    @staticmethod
    def _covers(boxes, point):
        x, y = point
        return any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in boxes)

    def test_corner_pads_make_a_perimeter_ring(self):
        boxes = gal._body_strap_boxes(self.CORNER_PADS)
        self.assertEqual(len(boxes), 4)  # two verticals, two horizontals
        for pad in self.CORNER_PADS:
            self.assertTrue(self._covers(boxes, pad), pad)
        for port in self.DEVICE_PORTS:
            self.assertFalse(self._covers(boxes, port), port)

    def test_side_pads_ride_the_columns_and_never_cross_the_cell(self):
        boxes = gal._body_strap_boxes(self.SIDE_PADS)
        for pad in self.SIDE_PADS:
            self.assertTrue(self._covers(boxes, pad), pad)
        for port in self.DEVICE_PORTS:
            self.assertFalse(self._covers(boxes, port), port)
        # No horizontal at the side pads' own row: a strip across the cell
        # interior there would cross the source/drain strips of a tall cell.
        # (The perimeter verticals legitimately span the row; a horizontal
        # would be a thin box centred on it.)
        side_y = 15.71
        self.assertFalse(
            any(
                abs(y0 - (side_y - gal.WIRE_UM / 2)) < 1e-9
                and x0 < 0.5 < x1
                for x0, y0, x1, y1 in boxes
            )
        )

    def test_collinear_pads_get_one_strip(self):
        boxes = gal._body_strap_boxes([(-0.65, -0.86), (1.93, -0.86)])
        self.assertEqual(len(boxes), 1)
        x0, y0, x1, y1 = boxes[0]
        self.assertEqual((x0, x1), (-0.65 - 0.14, 1.93 + 0.14))
        self.assertAlmostEqual(y1 - y0, gal.WIRE_UM)

    def test_a_single_pad_needs_nothing(self):
        self.assertEqual(gal._body_strap_boxes([(1.0, 1.0)]), [])
        self.assertEqual(gal._body_strap_boxes([]), [])

    def test_an_interior_column_never_reaches_the_device(self):
        pads = self.CORNER_PADS + [(0.4, 3.0)]  # between both columns and rows
        boxes = gal._body_strap_boxes(pads)
        for pad in pads:
            self.assertTrue(self._covers(boxes, pad), pad)
        for port in self.DEVICE_PORTS:
            self.assertFalse(self._covers(boxes, port), port)
        # The interior pad gets its own column, and that column is a pad band
        # (0.28 um wide), never a plate that could short across the device.
        column = [b for b in boxes if abs(b[0] - 0.26) < 1e-9]
        self.assertEqual(len(column), 1)
        x0, y0, x1, y1 = column[0]
        self.assertAlmostEqual(x1 - x0, gal.WIRE_UM)


class PinAnchorTests(unittest.TestCase):
    """A tap pad's via goes on the port point, a strip's is inset."""

    def test_tap_pad_pin_prefers_the_bottom_pad_nearest_the_centre(self):
        with _Stubs():
            pads = [
                {"name": "TAP_PAD0", "x_um": -0.65, "y_um": -0.86, "direction_deg": 270},
                {"name": "TAP_PAD1", "x_um": -0.65, "y_um": 6.28, "direction_deg": 90},
                {"name": "TAP_PAD2", "x_um": 2.15, "y_um": -0.86, "direction_deg": 270},
                {"name": "TAP_PAD3", "x_um": 2.15, "y_um": 6.28, "direction_deg": 90},
                {"name": "TAP_PAD4", "x_um": 0.70, "y_um": -0.86, "direction_deg": 270},
            ]
            self.assertEqual(gal._tap_pad_pin(pads), "TAP_PAD4")
            self.assertIsNone(gal._tap_pad_pin([{"name": "U0_S", "x_um": 0.0}]))

    def test_anchor_rule(self):
        # A tap pad escapes down like a source/drain, but takes its via on
        # the port point the way a gate pad does: the pad is 0.42um square
        # and the via 0.26um, so an inset via would not fit inside it.
        with _Stubs():
            self.assertEqual(gal._pin_anchor("U0_G"), ("top", "centre"))
            self.assertEqual(gal._pin_anchor("U0_S"), ("bottom", "inset"))
            self.assertEqual(gal._pin_anchor("R0_A"), ("bottom", "inset"))
            self.assertEqual(gal._pin_anchor("TAP_PAD0"), ("bottom", "centre"))
            self.assertEqual(gal._pin_anchor("TAP_PAD7"), ("bottom", "centre"))


def _klayout_available() -> bool:
    try:
        import klayout.db  # noqa: F401
    except ImportError:
        return False
    return True


@unittest.skipUnless(
    _klayout_available(),
    "needs the real klayout.db boolean engine (installed by CI's "
    "klayout-tools step; a bare lint host skips these)",
)
class StrapBodyPadsTests(unittest.TestCase):
    """``_strap_body_pads`` called directly, on real klayout geometry.

    These are the first cases to exercise the strap's clearance path itself
    (the classes above pin the pure helpers it calls). They need the real
    ``klayout.db`` boolean engine, so they skip on a bare lint host and run
    wherever klayout is importable (CI installs klayout-tools before the
    unittest leg). Issue #406's two observations, pinned as contracts:

    * **cross-group leg clearance is measured**: two groups on different
      body nets, close enough that the second group's leg would pass 0.22 um
      from the first group's drawn leg, get that leg refused. On the
      pre-#406 generator this case passes too -- ``klt_m1`` turned out to
      be a live view, not a snapshot, so the old code already measured the
      clearance through KLayout's lazy regions. The test pins the invariant
      across klayout versions; the #406 fix stops relying on the
      implementation detail;
    * **the pad square is measured, not assumed**: a stream whose tap pads
      are not ``PAD_SQUARE_UM`` square is refused with a drift problem (the
      standard ``scripts/analog_erc.py`` holds itself to), its pads left
      their own escape stubs;
    * **a tap pad with no metal-1 at its port is refused loudly** -- never
      silently absorbed by falling back to the constant.
    """

    def _strap(self, groups, pad_size=None, padless_pads=()):
        """Run ``_strap_body_pads`` on a synthetic stream.

        ``groups`` is a list of ``(net, block, pads)`` with ``pads`` a list
        of ``(x, y)`` um tap-pad centres; each group also gets a ``U0_S``
        device port well outside its strap boxes, so the non-tap-port
        refusal never fires. ``pad_size`` is the drawn pad square (default
        the committed one); a pad named in ``padless_pads`` gets no
        metal-1 at all.

        Returns ``(strapped, problems, stats, ctx)``; ``ctx`` carries the
        built layout (``top``, ``geo``, ``layer``) so a case can measure the
        delivered metal instead of trusting the stats.
        """
        import klayout.db as kdb

        layout = kdb.Layout()
        layout.dbu = 0.001
        top = layout.create_cell("TOP")
        geo = gal._Geometry(layout)
        layer = layout.layer(*gal.M1)
        dev_m1 = kdb.Region()
        ports: dict[tuple[str, str], tuple[float, float]] = {}
        nets: list[dict] = []
        half = (pad_size or gal.PAD_SQUARE_UM) / 2.0
        for net, block, pads in groups:
            pins = []
            for i, (x, y) in enumerate(pads):
                name = f"TAP_PAD{i}"
                ports[(block, name)] = (x, y)
                pins.append({"block": block, "port": name})
                if (block, name) not in padless_pads:
                    dev_m1.insert(geo.box(x - half, y - half, x + half, y + half))
            ports[(block, "U0_S")] = (-9.0, -9.0)
            pins.append({"block": block, "port": "U0_S"})
            nets.append({"net": net, "pins": pins})
        return (
            *gal._strap_body_pads(geo, top, nets, ports, dev_m1),
            {"top": top, "geo": geo, "layer": layer},
        )

    def test_a_leg_is_measured_against_legs_drawn_for_earlier_groups(self):
        # The cross-group clearance invariant, on the adversarial fixture:
        # g_a (a four-pad ring) sorts first ("AAA" < "BBB"); its column leg
        # is cut by g_b's pads, and its mid-band piece lands at x in
        # [-0.14, 0.14]. g_b's column leg would then run 0.22 um from that
        # drawn piece (0.36 - 0.14) -- inside the WIRE_UM clearance every
        # checked leg honours. The measured contract: g_b's mid-band metal
        # is refused. Both groups end unstrapped (their rings are split by
        # the cuts), so their pads fall back to per-pad stubs -- the
        # fail-safe path.
        #
        # This fixture is deliberately closer than any mos_array arrangement
        # can draw (0.42 um pads cannot approach a 0.28 um leg strip this
        # tightly without cutting it first), and on the pre-#406 generator
        # it PASSES TOO -- `klt_m1` turned out to be a live view, not a
        # snapshot, so the old code already measured this clearance at
        # runtime. What the test pins is that the invariant no longer
        # depends on that KLayout implementation detail: with the legs
        # accumulated explicitly, an eagerly-materialising Region in some
        # future klayout cannot silently reopen the gap.
        import klayout.db as kdb

        strapped, problems, stats, ctx = self._strap(
            [
                ("AAA", "g_a", [(0.0, 0.0), (0.0, 3.0)]),
                ("BBB", "g_b", [(0.5, 0.0), (0.5, 3.0)]),
            ]
        )
        self.assertEqual(problems, [])
        self.assertEqual(strapped, set())
        self.assertEqual(stats["legs_drawn"], 5)
        self.assertEqual(stats["legs_dropped"], 0)
        self.assertEqual(stats["groups_strapped"], 2)
        self.assertEqual(stats["pad_square_um"], [[0.42, 0.42]])
        # The near-miss zone itself: g_b's strip (x in [0.36, 0.64]) between
        # its two pad rows must carry no strap metal at all -- the pieces
        # there sit closer than WIRE_UM to g_a's drawn mid-band leg. Read
        # back the actual top-cell metal, not the stats, so the assertion
        # measures the delivered geometry.
        drawn = kdb.Region(ctx["top"].begin_shapes_rec(ctx["layer"]))
        zone = kdb.Region(ctx["geo"].box(0.36, 0.21, 0.64, 2.79))
        self.assertTrue((drawn & zone).is_empty())

    def test_two_groups_far_apart_both_strap(self):
        # The accumulation must not over-block: a neighbour far outside any
        # sized band straps exactly as before the change, and the measured
        # pad square is recorded in the stats.
        strapped, problems, stats, _ctx = self._strap(
            [
                ("AAA", "g_a", [(0.0, 0.0), (0.0, 3.0)]),
                ("BBB", "g_b", [(6.0, 0.0), (6.0, 3.0)]),
            ]
        )
        self.assertEqual(problems, [])
        self.assertEqual(stats["groups_strapped"], 2)
        self.assertEqual(stats["legs_drawn"], 2)
        self.assertEqual(stats["legs_dropped"], 0)
        self.assertEqual(stats["pad_square_um"], [[0.42, 0.42]])

    def test_a_pad_square_that_drifts_from_the_committed_size_is_refused(self):
        # The pad square is measured from the stream, not taken from the
        # constant: pads drawn 0.5 um square do not match PAD_SQUARE_UM, so
        # the group is refused with a drift problem -- naming both the
        # observed and the committed size -- and its pads are left their own
        # escape stubs. Never silently strapped with a carve-out sized for
        # the wrong square.
        strapped, problems, stats, _ctx = self._strap(
            [("AAA", "g_a", [(0.0, 0.0), (0.0, 3.0)])], pad_size=0.5
        )
        self.assertEqual(strapped, set())
        self.assertEqual(len(problems), 1)
        self.assertIn("g_a", problems[0])
        self.assertIn("0.5", problems[0])
        self.assertIn("0.42", problems[0])
        self.assertEqual(stats["legs_drawn"], 0)
        self.assertEqual(stats["groups_strapped"], 0)
        self.assertEqual(stats["pad_square_um"], [[0.5, 0.5]])

    def test_a_tap_pad_with_no_metal1_at_its_port_is_refused_loudly(self):
        # No silent fallback to PAD_SQUARE_UM: a port with nothing drawn on
        # it is a generator this rule does not understand, so the group is
        # refused and the missing metal reported by port name.
        strapped, problems, stats, _ctx = self._strap(
            [("AAA", "g_a", [(0.0, 0.0), (0.0, 3.0)])],
            padless_pads={("g_a", "TAP_PAD1")},
        )
        self.assertEqual(strapped, set())
        self.assertEqual(len(problems), 1)
        self.assertIn("g_a", problems[0])
        self.assertIn("TAP_PAD1", problems[0])
        self.assertEqual(stats["legs_drawn"], 0)
        self.assertEqual(stats["groups_strapped"], 0)


class _PlanExecutorStub:
    """Stand in for ``klayout_tools.layout_plan_execute`` (and
    ``klayout_tools.layout_plan``) during ``_execute_plan``: a fake executor
    that writes the plan-stage stream itself -- at ``options.output``, where
    the real one writes -- and reports the envelope matching it, plus the
    error names and ``exit_code_for`` the caller imports at call time.
    """

    def __init__(self, block, extent_um):
        self.block = block
        self.extent_um = extent_um  # (x0, y0, x1, y1) of the fake klt stream

    def __enter__(self):
        import klayout.db as kdb

        executor = self

        def fake_execute(request, request_dir=None, work_dir=None):
            layout = kdb.Layout()
            layout.dbu = 0.001
            top = layout.create_cell(executor.block)
            x0, y0, x1, y1 = executor.extent_um
            top.shapes(layout.layer(*gal.M1)).insert(
                kdb.Box(int(x0 * 1000), int(y0 * 1000), int(x1 * 1000), int(y1 * 1000))
            )
            layout.write(request["options"]["output"])
            return {"bbox_um": dict(zip(("x0", "y0", "x1", "y1"), executor.extent_um)), "nets": []}

        module = types.ModuleType("klayout_tools.layout_plan_execute")
        module.LayoutPlanExecuteError = type("LayoutPlanExecuteError", (Exception,), {})
        module.execute_layout_plan_document = fake_execute
        module.exit_code_for = lambda response: 0
        module.compose = lambda *args, **kwargs: None
        plan_module = types.ModuleType("klayout_tools.layout_plan")
        plan_module.LayoutPlanError = type("LayoutPlanError", (Exception,), {})
        self.saved = (
            sys.modules.get("klayout_tools.layout_plan_execute"),
            sys.modules.get("klayout_tools.layout_plan"),
        )
        sys.modules["klayout_tools.layout_plan_execute"] = module
        sys.modules["klayout_tools.layout_plan"] = plan_module
        return self

    def __exit__(self, *exc):
        for name, saved in zip(
            ("klayout_tools.layout_plan_execute", "klayout_tools.layout_plan"), self.saved
        ):
            if saved is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved
        return False


@unittest.skipUnless(
    _klayout_available(),
    "needs the real klayout.db (it writes the fixture streams; installed by "
    "CI's klayout-tools step, same as StrapBodyPadsTests)",
)
class BlockBboxSourceTests(unittest.TestCase):
    """``bbox_um`` is measured from the stream ``gds_path`` names.

    The cases run ``_execute_plan()`` on a miniature of the real pipeline:
    the fake executor writes the plan-stage stream and reports its envelope;
    the stubbed ``_complete_routing`` extends it -- which is what the real
    scripted pass does with its upper-metal tracks -- and writes the final
    stream. Negative coordinates are in every fixture (issue #427's whole
    point was a stream dipping below y=0).
    """

    def setUp(self):
        import klayout.db as kdb

        self.kdb = kdb
        self._tmp = tempfile.TemporaryDirectory(prefix="gal-bbox-")
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name
        # _execute_plan never needs klt here, but it always runs DRC and --
        # on the scripted path -- reads the plan's netlist digest.
        self._saved_drc = gal._run_drc
        gal._run_drc = lambda gds_path: {
            "status": "clean",
            "violation_count": 0,
            "by_rule": {},
        }
        self.addCleanup(setattr, gal, "_run_drc", self._saved_drc)
        self._saved_digest = gal._netlist_digest
        gal._netlist_digest = lambda plan_path, request: {}
        self.addCleanup(setattr, gal, "_netlist_digest", self._saved_digest)

    def _measure(self, path):
        """The top-cell extent of the stream at ``path``, read independently
        of the generator's own measurement."""
        layout = self.kdb.Layout()
        layout.read(path)
        box = layout.top_cell().dbbox()
        return {"x0": box.left, "y0": box.bottom, "x1": box.right, "y1": box.top}

    def _run(self, block, extent, route_to=None):
        out_dir = os.path.join(self.tmp, "out")
        os.makedirs(out_dir, exist_ok=True)
        plan_path = os.path.join(self.tmp, f"{block}.json")
        with open(plan_path, "w", encoding="utf-8") as handle:
            json.dump({}, handle)

        if route_to is not None:
            kdb = self.kdb

            def fake_routing(klt_gds, out_gds, response, compose_request,
                             klt_routed, digest):
                layout = kdb.Layout()
                layout.read(klt_gds)
                top = layout.top_cell()
                x0, y0, x1, y1 = route_to
                top.shapes(layout.layer(*gal.M2)).insert(
                    kdb.Box(int(x0 * 1000), int(y0 * 1000), int(x1 * 1000), int(y1 * 1000))
                )
                layout.write(out_gds)
                return {
                    "routed": {},
                    "snapped_instances": 0,
                    "l2n_net_count": 0,
                    "shorts": [],
                    "problems": [],
                    "methods": {"klt-plan": 0, "scripted": 0},
                    "body_ties": {},
                    "pin_labels": {},
                }

            self._saved_routing = gal._complete_routing
            gal._complete_routing = fake_routing
            self.addCleanup(setattr, gal, "_complete_routing", self._saved_routing)

        with _PlanExecutorStub(block, extent):
            return gal._execute_plan(
                plan_path,
                out_dir,
                keep_work=False,
                final_dir=out_dir if route_to is not None else None,
            )

    def test_a_scripted_block_reports_its_own_streams_extent(self):
        # The plan-stage stream spans 0..4 x 0..3; the scripted pass extends
        # it to -2..5 x -3.5..6.25. The emitted envelope must be the final
        # stream's -- measured from the file -- never the plan response's.
        result = self._run(
            "differential_receiver",
            extent=(0.0, 0.0, 4.0, 3.0),
            route_to=(-2.0, -3.5, 5.0, 6.25),
        )
        expected = {"x0": -2.0, "y0": -3.5, "x1": 5.0, "y1": 6.25}
        self.assertEqual(result["status"], "executed")
        self.assertEqual(result["bbox_um"], expected)
        self.assertNotEqual(result["bbox_um"], result["plan_bbox_um"])
        self.assertEqual(
            result["plan_bbox_um"], {"x0": 0.0, "y0": 0.0, "x1": 4.0, "y1": 3.0}
        )
        # bbox_um describes the stream gds_path names: re-measure it.
        self.assertEqual(
            self._measure(os.path.join(gal.REPO_ROOT, result["gds_path"])), expected
        )

    def test_a_non_scripted_block_whose_plan_envelope_matches_emits_it(self):
        # gds_path is klt's own output here, so the measured envelope equals
        # the plan response's: a healthy non-scripted block keeps its value
        # -- but it now comes from the stream (negative coordinates
        # included), not from the response.
        result = self._run("not_a_deliverable_block", extent=(0.0, -2.5, 3.0, 4.0))
        expected = {"x0": 0.0, "y0": -2.5, "x1": 3.0, "y1": 4.0}
        self.assertEqual(result["status"], "executed")
        self.assertEqual(result["bbox_um"], expected)
        self.assertEqual(result["plan_bbox_um"], expected)
        self.assertEqual(
            self._measure(os.path.join(gal.REPO_ROOT, result["gds_path"])), expected
        )


if __name__ == "__main__":
    unittest.main()
