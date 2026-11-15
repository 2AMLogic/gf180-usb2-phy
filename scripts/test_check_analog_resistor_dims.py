#!/usr/bin/env python3
"""Self-test for ``check_analog_resistor_dims.py``: comparison and verdict half.

These cases pin the contracts the drawn-dimension check rests on, without
running klayout, klt or the PDK, so they run in ``npm run lint`` on a bare
``python3`` (the klayout-dependent measurement half of the check is exercised
by CI's own step against the real streams, not here):

  * **the comparison is exact and integer**: a drawn ``L``/``W`` in database
    units equals the netlist ``r_length``/``r_width`` or it does not -- there
    is no epsilon and no tolerance anywhere in the verdict logic;
  * **the allow-list bites in both directions**: a ``dplus_pullup`` trim
    segment drawn at its sanctioned length passes *only* while it stays at
    that exact value -- drawn at any other length (including the netlist
    value) it fails, and a deviation whose allow-list entry is dropped fails
    too;
  * **an allow-list entry that is no longer needed is itself a failure**
    (stale entry), and an entry naming a resistor that does not exist is a
    structural error -- the allow-list may never silently outlive the state
    it was written for;
  * **orientation is reported, not assumed**: a device whose marker extent
    matches transposed is an orientation finding, distinct from a dimension
    mismatch;
  * **every fail-loud guard raises**: ``num != 1`` or ``dummy != 0`` on a
    plan group, ``m != 1`` or a missing ``m`` in the netlist, a device class
    with no marker layer, a join missing in either direction, a resistor
    instance without the ``XR`` prefix, an unparsable dimension value, and a
    zero-resistor report -- each is an error, never a silent pass;
  * **the committed allow-list is exactly the five DR-0010 entries**, each
    naming the decision record and carrying the expected drawn value from
    DR-0010's Drawn L column.

Usage:
    python3 scripts/test_check_analog_resistor_dims.py
        (or: python3 -m pytest scripts/test_check_analog_resistor_dims.py)
Exit codes: 0 all cases behave as specified, 1 otherwise.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_analog_resistor_dims as card  # noqa: E402


def _netlist(inst: str, l_nm: int, w_nm: int, model: str = "ppolyf_u", m: int = 1):
    return card.NetlistResistor(
        instance=inst, model=model, l_nm=l_nm, w_nm=w_nm, m=m
    )


def _one_row(netlist, measured, allow_list=None):
    if allow_list is None:
        allow_list = card.ALLOW_LIST
    rows = card.compare("dplus_pullup", netlist, measured, allow_list)
    assert len(rows) == 1, f"expected exactly one row, got {len(rows)}"
    return rows[0]


class CompareTests(unittest.TestCase):
    """The pure comparison/verdict logic, driven from synthetic dicts."""

    def test_clean_all_match(self):
        netlist = {
            "XR1": _netlist("XR1", 3800, 2000, "ppolyf_u_1k"),
            "XR2": _netlist("XR2", 2800, 2000, "ppolyf_u_1k"),
        }
        measured = {"XR1": (3800, 2000), "XR2": (2800, 2000)}
        rows = card.compare("se_receiver_dp", netlist, measured)
        self.assertEqual([r.verdict for r in rows], ["match", "match"])
        self.assertFalse(any(card.verdict_fails(r) for r in rows))

    def test_unallowlisted_l_difference_fails(self):
        # XRBIAS carries no allow-list entry: any difference is a failure.
        row = _one_row(
            {"XRBIAS": _netlist("XRBIAS", 400000, 2000)},
            {"XRBIAS": (400010, 2000)},
        )
        self.assertEqual(row.verdict, "fail")
        self.assertTrue(card.verdict_fails(row))

    def test_unallowlisted_w_difference_fails(self):
        row = _one_row(
            {"XRBIAS": _netlist("XRBIAS", 400000, 2000)},
            {"XRBIAS": (400000, 2010)},
        )
        self.assertEqual(row.verdict, "fail")
        self.assertTrue(card.verdict_fails(row))

    def test_allowlisted_deviation_passes(self):
        # XR0 as committed: netlist asks 0.343 um, DR-0010 sanctions 0.420 um.
        row = _one_row({"XR0": _netlist("XR0", 343, 4000)}, {"XR0": (420, 4000)})
        self.assertEqual(row.verdict, "allow_listed")
        self.assertFalse(card.verdict_fails(row))
        self.assertIn(card.DR0010_DECISION, row.note)

    def test_allowlisted_instance_drawn_at_other_value_fails(self):
        # The negative control: drawn at 0.345 um -- neither the netlist value
        # nor the sanctioned one. Must fail naming the instance.
        row = _one_row({"XR0": _netlist("XR0", 343, 4000)}, {"XR0": (345, 4000)})
        self.assertEqual(row.verdict, "allow_list_mismatch")
        self.assertTrue(card.verdict_fails(row))
        self.assertEqual(row.instance, "XR0")

    def test_dropped_allowlist_entry_fails(self):
        # The other negative control: the deviation is real but the entry is
        # gone. An unexplained deviation must fail.
        row = _one_row(
            {"XR0": _netlist("XR0", 343, 4000)},
            {"XR0": (420, 4000)},
            allow_list={},
        )
        self.assertEqual(row.verdict, "fail")
        self.assertTrue(card.verdict_fails(row))

    def test_exact_match_with_allowlist_entry_is_stale(self):
        # If a regeneration ever draws the netlist length exactly, the entry
        # is no longer needed and must be pruned deliberately.
        row = _one_row({"XR0": _netlist("XR0", 343, 4000)}, {"XR0": (343, 4000)})
        self.assertEqual(row.verdict, "stale_allow_list")
        self.assertTrue(card.verdict_fails(row))

    def test_transposed_measured_reports_orientation(self):
        # L and W swapped relative to the netlist: an orientation finding,
        # distinct from a dimension mismatch, never an allow-listed pass.
        row = _one_row({"XR1": _netlist("XR1", 2000, 1000)}, {"XR1": (1000, 2000)})
        self.assertEqual(row.verdict, "orientation")
        self.assertTrue(card.verdict_fails(row))

    def test_transposed_against_allowlisted_value_is_orientation(self):
        row = _one_row({"XR0": _netlist("XR0", 343, 4000)}, {"XR0": (4000, 420)})
        self.assertEqual(row.verdict, "orientation")
        self.assertTrue(card.verdict_fails(row))

    def test_compare_fails_loud_on_unmeasured_instance(self):
        with self.assertRaises(card.CheckError):
            card.compare(
                "dplus_pullup",
                {"XR0": _netlist("XR0", 343, 4000)},
                {},
            )


class AllowListShapeTests(unittest.TestCase):
    """The committed allow-list is exactly the five DR-0010 entries."""

    def test_exactly_five_entries_all_dplus_pullup(self):
        self.assertEqual(
            sorted(card.ALLOW_LIST),
            sorted(
                ("dplus_pullup", f"XR{i}") for i in range(5)
            ),
        )

    def test_every_entry_names_the_decision_record(self):
        for key, entry in card.ALLOW_LIST.items():
            self.assertEqual(
                entry["decision"],
                card.DR0010_DECISION,
                f"{key} must name {card.DR0010_DECISION}",
            )

    def test_expected_values_match_dr0010_drawn_l_column(self):
        expected = {
            ("dplus_pullup", "XR0"): (420, 4000),
            ("dplus_pullup", "XR1"): (685, 4000),
            ("dplus_pullup", "XR2"): (1370, 4000),
            ("dplus_pullup", "XR3"): (2745, 4000),
            ("dplus_pullup", "XR4"): (5485, 4000),
        }
        for key, (l_nm, w_nm) in expected.items():
            entry = card.ALLOW_LIST[key]
            self.assertEqual((entry["l_nm"], entry["w_nm"]), (l_nm, w_nm))


class AllowListCoverageTests(unittest.TestCase):
    def test_entry_for_unknown_resistor_is_error(self):
        rows = [
            card.Row(
                block="dplus_pullup", instance="XR0", model="ppolyf_u",
                nl_l_nm=343, nl_w_nm=4000, drawn_l_nm=420, drawn_w_nm=4000,
                verdict="allow_listed", note=card.DR0010_DECISION,
            )
        ]
        with self.assertRaisesRegex(card.CheckError, "XR9"):
            card.check_allowlist_coverage(
                rows, {("dplus_pullup", "XR9"): card.ALLOW_LIST[("dplus_pullup", "XR0")],
                       ("dplus_pullup", "XR0"): card.ALLOW_LIST[("dplus_pullup", "XR0")]}
            )

    def test_empty_report_is_error(self):
        with self.assertRaisesRegex(card.CheckError, "zero-resistor"):
            card.ensure_nonempty([])


class ParseNetlistTests(unittest.TestCase):
    def _write(self, tmp: Path, text: str) -> Path:
        p = tmp / "block.spice"
        p.write_text(text, encoding="utf-8")
        return p

    def test_resistor_line_parsed_in_integer_dbu(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            p = self._write(
                Path(d),
                ".subckt b a vss\n"
                "XMP0 a a vss vss pfet_03v3 L=0.28u W=2u nf=1 m=1\n"
                "XR0 a b vss ppolyf_u r_width=4u r_length=0.343u m=1\n"
                "XRSER b c rm1 r_width=2u r_length=800u m=1\n"
                ".ends\n",
            )
            res = card.parse_netlist_resistors(p)
        self.assertEqual(sorted(res), ["XR0", "XRSER"])
        self.assertEqual(res["XR0"].l_nm, 343)
        self.assertEqual(res["XR0"].w_nm, 4000)
        self.assertEqual(res["XR0"].model, "ppolyf_u")
        self.assertEqual(res["XRSER"].l_nm, 800_000)
        self.assertEqual(res["XRSER"].w_nm, 2000)

    def test_continuation_line_joined(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            p = self._write(
                Path(d),
                "XR1 a b vss ppolyf_u r_width=4u\n+ r_length=11.43u m=1\n",
            )
            res = card.parse_netlist_resistors(p)
        self.assertEqual(res["XR1"].l_nm, 11430)

    def test_m_not_one_raises(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            p = self._write(
                Path(d), "XR0 a b vss ppolyf_u r_width=4u r_length=2u m=2\n"
            )
            with self.assertRaisesRegex(card.CheckError, "m=2"):
                card.parse_netlist_resistors(p)

    def test_missing_m_raises(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            p = self._write(
                Path(d), "XR0 a b vss ppolyf_u r_width=4u r_length=2u\n"
            )
            with self.assertRaisesRegex(card.CheckError, "XR0"):
                card.parse_netlist_resistors(p)

    def test_instance_without_xr_prefix_raises(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            p = self._write(
                Path(d), "XCAP a b vss ppolyf_u r_width=4u r_length=2u m=1\n"
            )
            with self.assertRaisesRegex(card.CheckError, "XR prefix"):
                card.parse_netlist_resistors(p)

    def test_unparsable_dimension_raises(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            p = self._write(
                Path(d), "XR0 a b vss ppolyf_u r_width=4n r_length=2u m=1\n"
            )
            with self.assertRaisesRegex(card.CheckError, "r_width"):
                card.parse_netlist_resistors(p)

    def test_param_to_nm_units(self):
        self.assertEqual(card.param_to_nm("4u", "r_width"), 4000)
        self.assertEqual(card.param_to_nm("11.43u", "r_length"), 11430)
        with self.assertRaises(card.CheckError):
            card.param_to_nm("4", "r_width")
        with self.assertRaises(card.CheckError):
            card.param_to_nm("-4u", "r_width")

    def test_param_subnanometre_value_raises(self):
        with self.assertRaisesRegex(card.CheckError, "whole number"):
            card.param_to_nm("0.3435u", "r_length")

    def test_dbu_to_nm_on_half_nm_grid(self):
        # The regenerated streams are dbu=0.0005: 840 dbu is exactly 420 nm.
        self.assertEqual(card.dbu_to_nm(840, 0.0005, "x"), 420)
        self.assertEqual(card.dbu_to_nm(3800, 0.001, "x"), 3800)

    def test_dbu_to_nm_refuses_off_grid_dimension(self):
        with self.assertRaisesRegex(card.CheckError, "whole"):
            card.dbu_to_nm(841, 0.0005, "x")


class PlanGroupTests(unittest.TestCase):
    def _group(self, **params):
        g = {
            "id": "r_seg0",
            "devices": [{"name": "0", "device_class": "PPOLYF_U"}],
            "generator": "res_array",
            "params": {"num": 1, "dummy": 0},
        }
        g["params"].update(params)
        return g

    def test_res_array_groups_indexed_by_device_name(self):
        groups = card.load_res_array_groups(
            {"device_groups": [self._group()]}
        )
        self.assertIn("0", groups)
        self.assertEqual(groups["0"]["id"], "r_seg0")

    def test_non_res_array_generators_skipped(self):
        mos = {
            "id": "mn_x",
            "devices": [{"name": "N_X", "device_class": "NFET"}],
            "generator": "mos_array",
            "params": {"num": 4, "dummy": 2},
        }
        groups = card.load_res_array_groups({"device_groups": [mos]})
        self.assertEqual(groups, {})

    def test_num_not_one_raises(self):
        with self.assertRaisesRegex(card.CheckError, "num=2"):
            card.load_res_array_groups(
                {"device_groups": [self._group(num=2)]}
            )

    def test_dummy_not_zero_raises(self):
        with self.assertRaisesRegex(card.CheckError, "dummy=1"):
            card.load_res_array_groups(
                {"device_groups": [self._group(dummy=1)]}
            )

    def test_group_with_multiple_devices_raises(self):
        g = self._group()
        g["devices"].append({"name": "1", "device_class": "PPOLYF_U"})
        with self.assertRaisesRegex(card.CheckError, "r_seg0"):
            card.load_res_array_groups({"device_groups": [g]})

    def test_duplicate_device_name_raises(self):
        with self.assertRaisesRegex(card.CheckError, "0"):
            card.load_res_array_groups(
                {"device_groups": [self._group(), self._group()]}
            )


class JoinTests(unittest.TestCase):
    def test_missing_group_for_netlist_instance_raises(self):
        netlist = {"XR0": _netlist("XR0", 343, 4000)}
        groups = {"BASE": {"id": "r_base", "devices": [{"name": "BASE"}]}}
        with self.assertRaisesRegex(card.CheckError, "XR0"):
            card.validate_join("dplus_pullup", netlist, groups)

    def test_missing_netlist_for_group_device_raises(self):
        netlist = {"XR0": _netlist("XR0", 343, 4000)}
        groups = {"0": {"id": "r_seg0", "devices": [{"name": "0"}]},
                  "9": {"id": "r_seg9", "devices": [{"name": "9"}]}}
        with self.assertRaisesRegex(card.CheckError, "r_seg9"):
            card.validate_join("dplus_pullup", netlist, groups)

    def test_balanced_join_passes(self):
        netlist = {"XR0": _netlist("XR0", 343, 4000),
                   "XRBASE": _netlist("XRBASE", 11430, 4000)}
        groups = {"0": {"id": "r_seg0", "devices": [{"name": "0"}]},
                  "BASE": {"id": "r_base", "devices": [{"name": "BASE"}]}}
        card.validate_join("dplus_pullup", netlist, groups)


class MarkerLayerTests(unittest.TestCase):
    def test_known_device_classes(self):
        self.assertEqual(card.marker_layer_for("PPOLYF_U"), (110, 5))
        self.assertEqual(card.marker_layer_for("PPOLYF_U_1K"), (110, 5))
        self.assertEqual(card.marker_layer_for("RM1"), (110, 11))

    def test_unknown_device_class_raises(self):
        with self.assertRaisesRegex(card.CheckError, "MOSCAP"):
            card.marker_layer_for("MOSCAP")


if __name__ == "__main__":
    unittest.main(verbosity=2)
