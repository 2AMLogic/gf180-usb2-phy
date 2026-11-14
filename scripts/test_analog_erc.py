#!/usr/bin/env python3
"""Self-test for ``analog_erc.py``: spec shape, verdict gating, LVS pairing.

These cases pin the contracts the item-11.analog claim rests on without
running klt, klayout or the PDK, so they run in CI:

  * **stream discovery** comes from the committed ``*.gds`` glob, never a
    hard-coded block list, and the supply names come from
    ``layout/analog/provenance.json`` -- so ``dplus_pullup``'s ``VPU_REG``
    needs no special case and a renamed rail cannot be missed;
  * **the spec shape** declares what the item requires and nothing that
    would weaken it: both supplies ``kind: "supply"``, a narrowed n-well tap
    (never ``tap_is_dedicated``), an asserted substrate region, and no
    ``nets[].roles`` ownership claim;
  * **the negative control really is wrong**, in the two ways the record
    says it is -- the substrate tie points at the positive rail and an
    unlabelled supply is declared -- and is otherwise byte-identical to the
    real spec apart from its ``_comment``;
  * **every verdict gate bites**: a clean report passes, and a report that
    is clean except for one gate (a skipped tie, a split rail, a degenerate
    assertion, an ungraded assertion, a tap with no metal-wired pad) fails on
    exactly that gate. A grader that cannot fail is not a grader;
  * **the control grader refuses a control that came back clean**, which is
    the failure mode that would make the control decorative;
  * **the committed analog-LVS reports still pair both supplies** of every
    block, at ``status: "match"`` -- item 11's other half, re-checked here
    rather than asserted in prose, with no klt needed.

Usage:
    python3 scripts/test_analog_erc.py   (or: python3 -m pytest scripts/test_analog_erc.py)
Exit codes: 0 all cases behave as specified, 1 otherwise.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analog_erc as aerc  # noqa: E402


def _clean_report(positive: str = "VDD", ground: str = "VSS") -> dict:
    """The shape a passing `klt erc` run returns, reduced to what is graded."""
    return {
        "erc_status": "clean",
        "erc_finding_count": 0,
        "erc_findings": [],
        "nets": [
            {"name": positive, "matched_islands": 1},
            {"name": ground, "matched_islands": 1},
        ],
        "erc_coverage": {
            "checked": [
                aerc.work_id("erc.missing_tie", aerc.NWELL_TIE),
                aerc.work_id("erc.missing_tie", aerc.SUBSTRATE_TIE),
            ],
            "skipped": [],
            "inapplicable": [
                {"id": "erc.supply_short", "reason": "substrate_continuity_not_modelled"}
            ],
            "checked_by_well_assertion": [
                aerc.work_id("erc.missing_tie", aerc.SUBSTRATE_TIE)
            ],
            "layers_in_stream_without_declaration": [],
            "well_assertion_coverage": [],
        },
    }


def _good_facts() -> dict:
    return {
        "asserted_polygons": 6,
        "substrate_tap_area_outside_assertion_um2": 0.0,
        "asserted_polygons_without_a_tap": 0,
        "extent_uncovered_fraction": 0.98,
        "tap_narrowing_removed_um2": 84.56,
    }


def _good_census() -> dict:
    return {"metal_wired_taps_per_asserted_polygon": [1, 1, 1, 1, 1, 1]}


class TestDiscovery(unittest.TestCase):
    def test_blocks_come_from_the_committed_streams(self):
        blocks = aerc.discover_blocks(str(ROOT / aerc.GDS_DIR))
        self.assertEqual(blocks, sorted(blocks))
        self.assertIn("dplus_pullup", blocks)
        self.assertTrue(blocks, "no committed analog streams found")

    def test_every_stream_has_a_committed_spec(self):
        for block in aerc.discover_blocks(str(ROOT / aerc.GDS_DIR)):
            self.assertTrue(
                (ROOT / aerc.spec_path(block)).is_file(),
                f"{aerc.spec_path(block)} is missing",
            )

    def test_supply_names_are_read_from_the_provenance_sidecar(self):
        self.assertEqual(aerc.supply_nets(str(ROOT), "dplus_pullup"), ("VPU_REG", "VSS"))
        self.assertEqual(aerc.supply_nets(str(ROOT), "se_receiver_dp"), ("VDD", "VSS"))

    def test_unknown_block_is_a_loud_error(self):
        with self.assertRaises(aerc.HarnessError):
            aerc.supply_nets(str(ROOT), "no_such_block")


class TestSpecShape(unittest.TestCase):
    def setUp(self):
        self.spec = aerc.build_spec("demo", "VDD", "VSS", [[0.0, 0.0, 1.0, 1.0]])

    def test_gate_role_is_first_and_carries_an_active_layer(self):
        first = self.spec["stackup"][0]
        self.assertEqual(first["role"], "gate")
        self.assertEqual(first["active_layer"], "22/0")
        for entry in self.spec["stackup"][1:]:
            self.assertNotIn("role", entry)

    def test_no_metal4_or_metal5_is_declared(self):
        layers = {entry["layer"] for entry in self.spec["stackup"]}
        self.assertNotIn("46/0", layers)
        self.assertNotIn("81/0", layers)

    def test_both_supplies_are_kind_supply_and_claim_no_roles(self):
        self.assertEqual([n["name"] for n in self.spec["nets"]], ["VDD", "VSS"])
        for net in self.spec["nets"]:
            self.assertEqual(net["kind"], "supply")
            self.assertNotIn("roles", net)

    def test_nwell_tie_is_narrowed_and_never_asserted_dedicated(self):
        tie = self.spec["ties"][0]
        self.assertEqual(tie["name"], aerc.NWELL_TIE)
        self.assertEqual(tie["well_layer"], "21/0")
        self.assertEqual(tie["tap_requires"], ["32/0"])
        self.assertNotIn("tap_is_dedicated", tie)
        self.assertEqual(tie["net"], "VDD")

    def test_substrate_tie_asserts_its_region_and_narrows_its_tap(self):
        tie = self.spec["ties"][1]
        self.assertEqual(tie["name"], aerc.SUBSTRATE_TIE)
        self.assertIsNone(tie["well_layer"])
        self.assertEqual(tie["well_boxes"], [[0.0, 0.0, 1.0, 1.0]])
        self.assertEqual(tie["tap_requires"], ["31/0"])
        self.assertNotIn("tap_is_dedicated", tie)
        self.assertEqual(tie["net"], "VSS")

    def test_spec_is_a_pure_function_of_its_inputs(self):
        again = aerc.build_spec("demo", "VDD", "VSS", [[0.0, 0.0, 1.0, 1.0]])
        self.assertEqual(self.spec, again)


class TestControlSpec(unittest.TestCase):
    def setUp(self):
        self.real = aerc.build_spec("demo", "VDD", "VSS", [[0.0, 0.0, 1.0, 1.0]])
        self.control, self.absent = aerc.build_control_spec(self.real, "VDD", "VSS")

    def test_control_points_the_substrate_tie_at_the_positive_rail(self):
        tie = next(t for t in self.control["ties"] if t["name"] == aerc.SUBSTRATE_TIE)
        self.assertEqual(tie["net"], "VDD")

    def test_control_declares_a_supply_the_layout_cannot_carry(self):
        self.assertEqual(self.absent, "VSS_NOT_IN_LAYOUT")
        self.assertIn(self.absent, [n["name"] for n in self.control["nets"]])

    def test_control_changes_nothing_else(self):
        stripped_real = {k: v for k, v in self.real.items() if k != "_comment"}
        stripped_control = {k: v for k, v in self.control.items() if k != "_comment"}
        stripped_control["nets"] = [
            n for n in stripped_control["nets"] if n["name"] != self.absent
        ]
        for tie in stripped_control["ties"]:
            if tie["name"] == aerc.SUBSTRATE_TIE:
                tie["net"] = "VSS"
        self.assertEqual(stripped_real, stripped_control)

    def test_control_does_not_mutate_the_real_spec(self):
        self.assertEqual(self.real["ties"][1]["net"], "VSS")
        self.assertEqual(len(self.real["nets"]), 2)


class TestRunVerdict(unittest.TestCase):
    def grade(self, report=None, facts=None, census=None):
        return aerc.grade_run(
            report or _clean_report(),
            "VDD",
            "VSS",
            facts or _good_facts(),
            census or _good_census(),
        )

    def test_a_clean_run_passes_every_gate(self):
        verdict = self.grade()
        self.assertTrue(verdict["passed"], verdict["gates"])

    def test_a_skipped_tie_fails(self):
        report = _clean_report()
        report["erc_status"] = "clean_partial"
        report["erc_coverage"]["skipped"] = [
            {"id": aerc.work_id("erc.missing_tie", aerc.SUBSTRATE_TIE),
             "reason": "degenerate_well_assertion"}
        ]
        verdict = self.grade(report)
        self.assertFalse(verdict["passed"])
        self.assertFalse(verdict["gates"]["no_skipped_work"])
        self.assertFalse(verdict["gates"]["erc_status_clean"])

    def test_an_unchecked_tie_fails_even_with_zero_findings(self):
        report = _clean_report()
        report["erc_coverage"]["checked"] = [
            aerc.work_id("erc.missing_tie", aerc.NWELL_TIE)
        ]
        verdict = self.grade(report)
        self.assertFalse(verdict["passed"])
        self.assertFalse(verdict["gates"]["substrate_tie_checked"])

    def test_a_split_rail_fails(self):
        report = _clean_report()
        report["nets"][1]["matched_islands"] = 2
        verdict = self.grade(report)
        self.assertFalse(verdict["passed"])
        self.assertFalse(verdict["gates"]["ground_supply_one_island"])

    def test_an_assertion_spanning_the_die_fails(self):
        facts = _good_facts()
        facts["extent_uncovered_fraction"] = 0.004
        verdict = self.grade(facts=facts)
        self.assertFalse(verdict["passed"])
        self.assertFalse(verdict["gates"]["assertion_not_whole_extent"])

    def test_a_tap_outside_the_assertion_fails(self):
        facts = _good_facts()
        facts["substrate_tap_area_outside_assertion_um2"] = 0.42
        verdict = self.grade(facts=facts)
        self.assertFalse(verdict["passed"])
        self.assertFalse(verdict["gates"]["every_substrate_tap_inside_assertion"])

    def test_an_unnarrowed_tap_fails(self):
        facts = _good_facts()
        facts["tap_narrowing_removed_um2"] = 0.0
        verdict = self.grade(facts=facts)
        self.assertFalse(verdict["passed"])
        self.assertFalse(verdict["gates"]["tap_narrowing_is_real"])

    def test_a_partition_finer_than_the_metal_supports_fails(self):
        """The gate that keeps CLUSTER_GAP_UM from being tuned too fine."""
        census = {"metal_wired_taps_per_asserted_polygon": [1, 1, 0, 1, 1, 1]}
        verdict = self.grade(census=census)
        self.assertFalse(verdict["passed"])
        self.assertFalse(verdict["gates"]["every_asserted_polygon_has_a_metal_wired_tap"])

    def test_an_ungraded_assertion_fails(self):
        report = _clean_report()
        report["erc_coverage"]["checked_by_well_assertion"] = []
        verdict = self.grade(report)
        self.assertFalse(verdict["passed"])
        self.assertFalse(verdict["gates"]["substrate_tie_graded_by_well_assertion"])

    def test_undeclared_drawn_layers_fail(self):
        report = _clean_report()
        report["erc_coverage"]["layers_in_stream_without_declaration"] = ["46/0"]
        verdict = self.grade(report)
        self.assertFalse(verdict["passed"])
        self.assertFalse(verdict["gates"]["no_undeclared_drawn_layers"])

    def test_the_supply_short_disclosure_is_carried_into_the_verdict(self):
        """It is inapplicable on every run, so it must be visible, not dropped."""
        verdict = self.grade()
        self.assertEqual(
            [entry["reason"] for entry in verdict["inapplicable"]],
            ["substrate_continuity_not_modelled"],
        )


class TestControlVerdict(unittest.TestCase):
    def _failing_control(self, polygons: int = 2) -> dict:
        return {
            "erc_status": "violations",
            "erc_finding_count": polygons + 1,
            "erc_findings": [
                {"rule": "erc.missing_tie", "layer": aerc.SUBSTRATE_TIE, "net": "VDD"}
                for _ in range(polygons)
            ]
            + [{"rule": "erc.unconnected_net", "net": "VSS_NOT_IN_LAYOUT"}],
            "nets": [
                {"name": "VDD", "matched_islands": 1},
                {"name": "VSS", "matched_islands": 1},
                {"name": "VSS_NOT_IN_LAYOUT", "matched_islands": 0},
            ],
        }

    def test_a_control_that_fails_in_both_ways_passes(self):
        verdict = aerc.grade_control(self._failing_control(), "VSS_NOT_IN_LAYOUT", 2)
        self.assertTrue(verdict["passed"], verdict["gates"])

    def test_a_clean_control_is_refused(self):
        report = self._failing_control()
        report["erc_status"] = "clean"
        report["erc_findings"] = []
        report["nets"][2]["matched_islands"] = 1
        verdict = aerc.grade_control(report, "VSS_NOT_IN_LAYOUT", 2)
        self.assertFalse(verdict["passed"])
        self.assertFalse(verdict["gates"]["erc_status_not_clean"])

    def test_a_control_missing_one_polygon_is_refused(self):
        verdict = aerc.grade_control(self._failing_control(polygons=1), "VSS_NOT_IN_LAYOUT", 2)
        self.assertFalse(verdict["passed"])
        self.assertFalse(
            verdict["gates"]["every_asserted_polygon_reports_missing_tie"]
        )

    def test_a_control_with_no_asserted_polygons_is_refused(self):
        """Zero findings out of zero polygons must not read as a pass."""
        report = self._failing_control(polygons=0)
        verdict = aerc.grade_control(report, "VSS_NOT_IN_LAYOUT", 0)
        self.assertFalse(verdict["passed"])


class TestLvsPairing(unittest.TestCase):
    """Item 11's other half, re-read from the committed analog-LVS reports."""

    def test_every_block_pairs_both_of_its_supplies_at_status_match(self):
        for block in aerc.discover_blocks(str(ROOT / aerc.GDS_DIR)):
            positive, ground = aerc.supply_nets(str(ROOT), block)
            result = aerc.grade_lvs_pairing(str(ROOT), block, positive, ground)
            self.assertTrue(result["passed"], f"{block}: {result['gates']}")
            self.assertEqual(result["lvs_status"], "match")

    def test_an_unpaired_supply_is_refused(self):
        with self.assertRaises(aerc.HarnessError):
            aerc.grade_lvs_pairing(str(ROOT), "no_such_block", "VDD", "VSS")


class TestCommittedSpecs(unittest.TestCase):
    """The committed specs are what the harness would write today.

    The geometry half of that (the `well_boxes` derivation) needs klayout and
    is gated inside `analog_erc.py` itself on every run; what is checked here
    is everything else -- that no committed spec has drifted in a way that
    does not need a GDS to see.
    """

    def test_every_committed_spec_matches_the_builder_apart_from_its_boxes(self):
        for block in aerc.discover_blocks(str(ROOT / aerc.GDS_DIR)):
            committed = json.loads((ROOT / aerc.spec_path(block)).read_text())
            positive, ground = aerc.supply_nets(str(ROOT), block)
            boxes = committed["ties"][1]["well_boxes"]
            self.assertEqual(
                committed,
                aerc.build_spec(block, positive, ground, boxes),
                f"{aerc.spec_path(block)} differs from build_spec()",
            )

    def test_every_committed_spec_asserts_at_least_one_substrate_region(self):
        for block in aerc.discover_blocks(str(ROOT / aerc.GDS_DIR)):
            committed = json.loads((ROOT / aerc.spec_path(block)).read_text())
            boxes = committed["ties"][1]["well_boxes"]
            self.assertTrue(boxes, f"{block}: empty well_boxes")
            self.assertEqual(boxes, sorted(boxes), f"{block}: well_boxes not sorted")
            for box in boxes:
                self.assertEqual(len(box), 4)
                self.assertLess(box[0], box[2], f"{block}: degenerate box {box}")
                self.assertLess(box[1], box[3], f"{block}: degenerate box {box}")

    def test_no_committed_spec_declares_a_relaxing_key(self):
        forbidden = ("tap_is_dedicated", "well_complement_of")
        for block in aerc.discover_blocks(str(ROOT / aerc.GDS_DIR)):
            raw = (ROOT / aerc.spec_path(block)).read_text()
            spec = json.loads(raw)
            for tie in spec["ties"]:
                for key in forbidden:
                    self.assertNotIn(key, tie, f"{block}: {tie['name']} declares {key}")
            self.assertNotIn("ties_disclosure", spec)


if __name__ == "__main__":
    unittest.main(verbosity=2)
