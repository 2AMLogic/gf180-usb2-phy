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


if __name__ == "__main__":
    unittest.main()
