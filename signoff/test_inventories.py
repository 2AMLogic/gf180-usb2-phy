#!/usr/bin/env python3
"""Self-test for the T1 item 2.analog audit in `signoff/inventories.py`.

The audit behind item 2.analog exists to make one guarantee: a **partial**
analog layout set is never attested. These cases pin that guarantee down with
temp-dir fixtures -- a plan with no delivered GDS, a GDS that is gone, a GDS
whose bytes no longer match the sidecar, a block the sidecar calls dirty, and
a block whose routing does not account for all of its nets. Each must raise
`AuditError`, and `write_all` must write nothing when one does.

Usage:
    python3 signoff/test_inventories.py
Exit codes: 0 all cases behave as specified, 1 otherwise.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "signoff"))
import check as signoff_check  # noqa: E402
import inventories  # noqa: E402

BLOCKS = ("alpha", "beta", "gamma")


class _AnalogFixture(unittest.TestCase):
    """A temp tree with one plan, netlist and delivered GDS per block."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "layout/analog/plans").mkdir(parents=True)
        (self.root / "design/netlist").mkdir(parents=True)
        self.entries = {}
        for name in BLOCKS:
            gds = self.write(f"layout/analog/{name}.gds", f"gds-{name}".encode())
            self.write(f"design/netlist/{name}.spice", f"net-{name}".encode())
            self.write(f"layout/analog/plans/{name}.json", f"plan-{name}".encode())
            self.entries[name] = {
                "block": name,
                "gds": f"layout/analog/{name}.gds",
                "gds_sha256": gds,
                "netlist_sha256": hashlib.sha256(f"net-{name}".encode()).hexdigest(),
                "plan_sha256": hashlib.sha256(f"plan-{name}".encode()).hexdigest(),
                "klt_version": "0.9.0",
                "regeneration_command": "python3 scripts/gen_analog_layout.py --deliver",
                "routing_method": {"klt-plan": 1, "scripted": 3},
                "net_count": 4,
                "drc": {"status": "clean", "violation_count": 0},
            }
        self.write_sidecar()

    def write(self, rel: str, data: bytes) -> str:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    def write_sidecar(self) -> None:
        (self.root / "layout/analog/provenance.json").write_text(
            json.dumps({"schema_version": 1, "blocks": list(self.entries.values())}, indent=2)
        )

    def build(self):
        return inventories.build_analog_layout_inventory(self.root)

    def assert_refuses(self, needle: str):
        with self.assertRaises(inventories.AuditError) as caught:
            self.build()
        self.assertIn(needle, str(caught.exception))


class AnalogLayoutInventoryTests(_AnalogFixture):
    """Every way the analog set can be incomplete must refuse."""

    # -- the complete set is attested -------------------------------------
    def test_complete_set_builds_and_lists_every_stream(self):
        inventory = self.build()
        self.assertEqual([b["block"] for b in inventory["blocks"]], sorted(BLOCKS))
        for block in inventory["blocks"]:
            for key in ("gds", "plan", "netlist"):
                self.assertTrue(block[key]["sha256"].startswith("sha256:"), key)
        self.assertTrue(inventory["sidecar"]["sha256"].startswith("sha256:"))
        self.assertTrue(any("LVS" in claim for claim in inventory["not_claimed"]))

    # -- the refusals ------------------------------------------------------
    def test_refuses_a_plan_with_no_delivered_gds(self):
        """The exact partial-set case: a planned block nobody delivered."""
        del self.entries["beta"]
        self.write_sidecar()
        self.assert_refuses("no delivered GDS for beta")

    def test_refuses_when_a_delivered_gds_is_absent_from_the_tree(self):
        (self.root / "layout/analog/gamma.gds").unlink()
        self.assert_refuses("layout/analog/gamma.gds")

    def test_refuses_a_gds_whose_bytes_no_longer_match_the_sidecar(self):
        self.write("layout/analog/alpha.gds", b"tampered")
        self.assert_refuses("does not hash to the gds_sha256")

    def test_refuses_a_block_the_sidecar_does_not_call_drc_clean(self):
        self.entries["beta"]["drc"] = {"status": "violations", "violation_count": 3}
        self.write_sidecar()
        self.assert_refuses("not 'clean'")

    def test_accepts_the_bare_single_method_routing_form(self):
        # The sidecar collapses a one-method block to that method's bare name
        # (issue #346): it still accounts for every net.
        self.entries["gamma"]["routing_method"] = "scripted"
        self.write_sidecar()
        inventory = self.build()
        entry = next(b for b in inventory["blocks"] if b["block"] == "gamma")
        self.assertEqual(entry["routing_method"], {"scripted": entry["net_count"]})

    def test_refuses_a_block_whose_routing_leaves_nets_unaccounted(self):
        self.entries["gamma"]["routing_method"] = {"klt-plan": 1, "scripted": 1}
        self.write_sidecar()
        self.assert_refuses("accounts for 2 of 4 nets")

    def test_refuses_a_block_with_no_recorded_net_count(self):
        self.entries["alpha"].pop("net_count")
        self.write_sidecar()
        self.assert_refuses("records no net_count")

    def test_refuses_when_there_are_no_plans_at_all(self):
        for plan in (self.root / "layout/analog/plans").glob("*.json"):
            plan.unlink()
        self.assert_refuses("no analog layout plans found")


class RegenRefusalTests(_AnalogFixture):
    """A failed audit must leave every committed file untouched."""

    def _isolate(self):
        """Registries holding just the analog item and one always-fine peer."""
        return (
            mock.patch.dict(
                inventories.INVENTORY_BUILDERS,
                {
                    "2.analog": inventories.build_analog_layout_inventory,
                    "10": lambda root: {"schema_version": 1, "files": []},
                },
                clear=True,
            ),
            mock.patch.dict(
                inventories.ITEM_ARTIFACTS,
                {
                    "2.analog": "signoff/evidence/inventory-analog-layout.json",
                    "10": "signoff/evidence/inventory-repo-hygiene.json",
                },
                clear=True,
            ),
            mock.patch.dict(
                inventories.ITEM_ENVELOPES,
                {
                    "2.analog": "signoff/evidence/t1-item-2-analog-layout.json",
                    "10": "signoff/evidence/t1-item-10-repo-hygiene.json",
                },
                clear=True,
            ),
        )

    def test_write_all_writes_nothing_when_the_set_is_partial(self):
        evidence = self.root / "signoff/evidence"
        evidence.mkdir(parents=True)
        sentinel = evidence / "inventory-repo-hygiene.json"
        sentinel.write_text('{"untouched": true}\n')
        del self.entries["beta"]  # the partial set
        self.write_sidecar()

        patches = self._isolate()
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        with self.assertRaises(inventories.AuditError):
            inventories.write_all(self.root)

        # The peer inventory built fine; it must still not have been written.
        self.assertEqual(sentinel.read_text(), '{"untouched": true}\n')
        self.assertFalse((evidence / "inventory-analog-layout.json").exists())
        self.assertFalse((evidence / "t1-item-2-analog-layout.json").exists())

    def test_check_regen_reports_failure_and_leaves_the_manifest_alone(self):
        (self.root / "signoff/evidence").mkdir(parents=True)
        manifest = self.root / "manifests/gf180-usb2-phy.json"
        manifest.parent.mkdir(parents=True)
        before = json.dumps({"evidence": {}}, indent=2) + "\n"
        manifest.write_text(before)
        del self.entries["gamma"]  # the partial set
        self.write_sidecar()

        patches = self._isolate()
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.assertFalse(signoff_check.regen(self.root, manifest))
        self.assertEqual(manifest.read_text(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
