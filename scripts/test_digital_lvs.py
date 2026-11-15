#!/usr/bin/env python3
"""Self-test for ``digital_lvs.py``'s label-resolution guard.

The harness abstracts every standard cell as a black box and deliberately
supplies no ``--abstract-cell-lef`` (issue #392: since klt 0.9.0 the LEF's
pins are *unioned* with the label-resolved set, injecting floating well
pins that fail the power/ground half). The extract report is the one place
that says how each abstracted type's pins were resolved, so the guard
``unlabelled_abstract_cells`` must name every type that resolved any other
way -- or that does not say at all -- rather than let the run pass silently.

These cases pin that contract without running klt or the PDK, so they run
in CI:

  * every type ``in_cell_labels`` with ``lef_path: null`` -- the committed
    records' shape -- passes;
  * a type resolved from a LEF fallback (``resolution_source:
    "lef_abstract"``, the enum member klt's extract report documents) is named;
  * a type carrying the **LEF-union shape** -- ``resolution_source``
    still ``"in_cell_labels"`` but ``lef_path`` set and the LEF's extra
    pins appended (klayout-tools#3749; the payload that caused issue #392)
    -- is named, which a ``resolution_source``-only check cannot see;
  * a type with no ``resolution_source`` at all is named, not waved through;
  * an empty ``abstracted_cells`` list passes (nothing was abstracted);
  * a missing ``abstracted_cells`` key passes (the report predates the key).

The union-shape fixture below is lifted verbatim from the committed
LEF-union capture ``20261115-002602-b2da113`` (append-only, frozen), and a
case runs the guard over that capture itself, so the suite bites on the
real report rather than on a plausible-looking guess about it.

Usage:
    python3 scripts/test_digital_lvs.py      (or: python3 -m unittest scripts/test_digital_lvs.py)
Exit codes: 0 all cases behave as specified, 1 otherwise.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import digital_lvs as dlvs  # noqa: E402


class UnlabelledAbstractCellsTest(unittest.TestCase):
    def test_all_label_resolved_passes(self):
        report = {
            "abstracted_cells": [
                {
                    "cell": "gf180mcu_fd_sc_mcu9t5v0__and2_1",
                    "instance_count": 9,
                    "pin_count": 5,
                    "resolution_source": "in_cell_labels",
                    "lef_path": None,
                },
                {
                    "cell": "gf180mcu_fd_sc_mcu9t5v0__clkinv_1",
                    "instance_count": 164,
                    "pin_count": 4,
                    "resolution_source": "in_cell_labels",
                    "lef_path": None,
                },
            ]
        }
        self.assertEqual(dlvs.unlabelled_abstract_cells(report), [])

    def test_lef_abstract_resolved_type_is_named(self):
        """The per-cell-type fallback path names its LEF in ``resolution_source``.

        ``lef_abstract`` is the enum member klt's extract report documents
        (``klayout_tools/extract.py``: ``"in_cell_labels" | "lef_abstract"``);
        the ``"lef"`` value an earlier fixture used is not something the
        tool ever writes.
        """
        report = {
            "abstracted_cells": [
                {
                    "cell": "gf180mcu_fd_sc_mcu9t5v0__and2_1",
                    "instance_count": 9,
                    "pin_count": 5,
                    "resolution_source": "in_cell_labels",
                    "lef_path": None,
                },
                {
                    "cell": "gf180mcu_fd_sc_mcu9t5v0__fill_1",
                    "instance_count": 12,
                    "pin_count": 3,
                    "resolution_source": "lef_abstract",
                },
            ]
        }
        self.assertEqual(
            dlvs.unlabelled_abstract_cells(report),
            ["gf180mcu_fd_sc_mcu9t5v0__fill_1"],
        )

    def test_lef_union_shape_is_named(self):
        """The issue-#392 payload: the union keeps ``in_cell_labels``.

        klt's LEF merge (klayout-tools#3749) appends the LEF's pins to a
        type whose pins were already fully resolved from labels, keeping
        ``resolution_source`` at ``in_cell_labels`` while setting
        ``lef_path``. This entry is lifted verbatim from the committed
        LEF-union capture ``20261115-002602-b2da113`` -- the report whose
        injected ``VNW``/``VPW`` pins failed the power half -- and a guard
        keyed on the source field alone passes it silently.
        """
        report = {
            "abstracted_cells": [
                {
                    "cell": "gf180mcu_fd_sc_mcu9t5v0__and2_1",
                    "instance_count": 9,
                    "pin_count": 7,
                    "resolution_source": "in_cell_labels",
                    "lef_path": (
                        "/home/ubuntu/.volare/volare/gf180mcu/versions/"
                        "c6d73a35f524070e85faff4a6a9eef49553ebc2b.bak-20261015T153815Z/"
                        "gf180mcuC/libs.ref/gf180mcu_fd_sc_mcu9t5v0/lef/"
                        "gf180mcu_fd_sc_mcu9t5v0.lef"
                    ),
                },
                {
                    "cell": "gf180mcu_fd_sc_mcu9t5v0__clkinv_1",
                    "instance_count": 164,
                    "pin_count": 4,
                    "resolution_source": "in_cell_labels",
                    "lef_path": None,
                },
            ]
        }
        self.assertEqual(
            dlvs.unlabelled_abstract_cells(report),
            ["gf180mcu_fd_sc_mcu9t5v0__and2_1"],
        )

    def test_guard_fires_on_the_real_lef_union_capture(self):
        """Run the guard over the committed LEF-union extract report itself.

        ``20261115-002602-b2da113`` is frozen history (append-only,
        superseded), so its bytes -- 62 of 64 types with a non-null
        ``lef_path``, every one still ``in_cell_labels`` -- are stable, and
        this is the payload a ``resolution_source``-only guard passed on
        its way to issue #392's power mismatch.
        """
        capture = (
            ROOT
            / "verification"
            / "records"
            / "digital-lvs"
            / "artifacts"
            / "20261115-002602-b2da113"
            / "extract-report.json"
        )
        report = json.loads(capture.read_text(encoding="utf-8"))
        named = dlvs.unlabelled_abstract_cells(report)
        self.assertEqual(len(named), 62)
        self.assertIn("gf180mcu_fd_sc_mcu9t5v0__and2_1", named)

    def test_missing_resolution_source_is_named(self):
        report = {
            "abstracted_cells": [
                {
                    "cell": "gf180mcu_fd_sc_mcu9t5v0__clkinv_2",
                    "instance_count": 4,
                    "pin_count": 4,
                }
            ]
        }
        self.assertEqual(
            dlvs.unlabelled_abstract_cells(report),
            ["gf180mcu_fd_sc_mcu9t5v0__clkinv_2"],
        )

    def test_empty_abstracted_cells_passes(self):
        self.assertEqual(dlvs.unlabelled_abstract_cells({"abstracted_cells": []}), [])

    def test_missing_abstracted_cells_key_passes(self):
        self.assertEqual(dlvs.unlabelled_abstract_cells({"net_count": 366}), [])


if __name__ == "__main__":
    unittest.main()
