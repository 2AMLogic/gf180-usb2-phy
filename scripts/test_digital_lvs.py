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

  * every type ``in_cell_labels`` -- the committed records' shape -- passes;
  * a type resolved from a LEF (``resolution_source: "lef"``) is named;
  * a type with no ``resolution_source`` at all is named, not waved through;
  * an empty ``abstracted_cells`` list passes (nothing was abstracted);
  * a missing ``abstracted_cells`` key passes (the report predates the key).

Usage:
    python3 scripts/test_digital_lvs.py      (or: python3 -m unittest scripts/test_digital_lvs.py)
Exit codes: 0 all cases behave as specified, 1 otherwise.
"""

from __future__ import annotations

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

    def test_lef_resolved_type_is_named(self):
        report = {
            "abstracted_cells": [
                {
                    "cell": "gf180mcu_fd_sc_mcu9t5v0__and2_1",
                    "instance_count": 9,
                    "pin_count": 7,
                    "resolution_source": "in_cell_labels",
                },
                {
                    "cell": "gf180mcu_fd_sc_mcu9t5v0__fill_1",
                    "instance_count": 12,
                    "pin_count": 3,
                    "resolution_source": "lef",
                },
            ]
        }
        self.assertEqual(
            dlvs.unlabelled_abstract_cells(report),
            ["gf180mcu_fd_sc_mcu9t5v0__fill_1"],
        )

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
