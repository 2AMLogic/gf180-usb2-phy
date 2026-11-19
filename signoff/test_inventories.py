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
        """The registry holding just the analog item and one always-fine peer."""
        return mock.patch.dict(
            inventories.ITEMS,
            {
                "2.analog": inventories.Item(
                    artifact="signoff/evidence/inventory-analog-layout.json",
                    envelope="signoff/evidence/t1-item-2-analog-layout.json",
                    title="Layout (analog partition)",
                    builder=inventories.build_analog_layout_inventory,
                ),
                "10": inventories.Item(
                    artifact="signoff/evidence/inventory-repo-hygiene.json",
                    envelope="signoff/evidence/t1-item-10-repo-hygiene.json",
                    title="Repo hygiene",
                    builder=lambda root: {"schema_version": 1, "files": []},
                ),
            },
            clear=True,
        )

    def test_write_all_writes_nothing_when_the_set_is_partial(self):
        evidence = self.root / "signoff/evidence"
        evidence.mkdir(parents=True)
        sentinel = evidence / "inventory-repo-hygiene.json"
        sentinel.write_text('{"untouched": true}\n')
        del self.entries["beta"]  # the partial set
        self.write_sidecar()

        patch = self._isolate()
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

        patch = self._isolate()
        patch.start()
        self.addCleanup(patch.stop)
        self.assertFalse(signoff_check.regen(self.root, manifest))
        self.assertEqual(manifest.read_text(), before)


class _PinsFixture(unittest.TestCase):
    """A temp tree holding just the three pin files `_pins` reads, in sync."""

    KLT = "0.9.0"
    ENGINE = "0.30.12"
    PDK = "c6d73a35f524070e85faff4a6a9eef49553ebc2b"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.write_ci(self.ENGINE)
        self.write_setup(self.ENGINE)
        self.write_env_doc(self.ENGINE)

    def write_ci(self, engine: str | None) -> None:
        installs = [f'"klayout-tools=={self.KLT}"']
        if engine:
            installs.append(f'"klayout=={engine}"')
        installs.append('"cocotb==2.0.1"')
        path = self.root / ".github" / "workflows" / "ci.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "python3 -m pip install --disable-pip-version-check \\\n"
            "            " + " \\\n            ".join(installs) + "\n"
        )

    def write_setup(self, engine: str | None) -> None:
        lines = [f'KLT_VERSION="{self.KLT}"']
        if engine:
            lines.append(f'KLAYOUT_VERSION="{engine}"')
        lines += ['COCOTB_PIN="2.0.1"', f'VOLARE_GF180MCU_VERSION="{self.PDK}"']
        path = self.root / "scripts" / "setup-env.sh"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n")

    def write_env_doc(self, engine: str | None) -> None:
        lines = [f'pip install "klayout-tools=={self.KLT}"']
        if engine:
            lines.append(f'pip install "klayout=={engine}"')
        lines.append(f"volare enable {self.PDK}")
        path = self.root / "docs" / "environment-setup.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n")

    def pins(self) -> dict:
        return inventories._pins(self.root)

    def assert_refuses(self, needle: str):
        with self.assertRaises(inventories.AuditError) as caught:
            self.pins()
        self.assertIn(needle, str(caught.exception))


class PinSyncTests(_PinsFixture):
    """The pin audit must sync-check the klayout engine like every other pin.

    `_pins` enforced klt, cocotb and the PDK commit but not the engine wheel
    issue #472 pinned (`KLAYOUT_VERSION`, `"klayout==X"` and the env-doc row,
    added by #475) -- a setup-env/CI engine divergence would surface only as
    a worker regenerating different GDS bytes. These cases pin the checks
    down: a synced tree passes and reports `klayout_engine`; a desynced
    setup-env/CI pair, either pin absent, or the version missing from the
    env doc each raise `AuditError`; and `klayout-tools==` must not satisfy
    the engine regex (issue #477).
    """

    def test_a_synced_tree_passes_and_reports_the_engine_pin(self):
        self.assertEqual(
            self.pins(),
            {
                "klayout_tools_ci_and_grader": self.KLT,
                "klayout_tools_setup_env": self.KLT,
                "klayout_engine": self.ENGINE,
                "cocotb": "2.0.1",
                "gf180mcu_open_pdks": self.PDK,
            },
        )

    def test_a_desynced_setup_env_ci_engine_pair_fails(self):
        self.write_ci("0.30.13")
        with self.assertRaises(inventories.AuditError) as caught:
            self.pins()
        message = str(caught.exception)
        self.assertIn("pins the klayout engine", message)
        # the error names both files a bumper must edit together
        self.assertIn("scripts/setup-env.sh", message)
        self.assertIn(".github/workflows/ci.yml", message)

    def test_an_engine_pin_missing_from_ci_fails(self):
        # `klayout-tools==0.9.0` alone must not satisfy the engine regex:
        # the opening quote anchors `"klayout==` away from it.
        self.write_ci(None)
        self.assert_refuses("no pinned `klayout==X` engine install")

    def test_an_engine_pin_missing_from_setup_env_fails(self):
        self.write_setup(None)
        self.assert_refuses("no KLAYOUT_VERSION pin")

    def test_an_engine_pin_missing_from_the_env_doc_fails(self):
        self.write_env_doc(None)
        self.assert_refuses("does not record the klayout engine pin")


class ItemRecordTests(unittest.TestCase):
    """One record per item: a registry entry cannot under-specify an item."""

    def test_a_record_omitting_envelope_is_rejected(self):
        # The split tables this registry replaced let an item be built and
        # written while no envelope, manifest citation or drift-gate line
        # ever covered it; a required field makes that a construction error.
        with self.assertRaises(TypeError):
            inventories.Item(
                artifact="signoff/evidence/inventory-x.json",
                title="X",
                builder=lambda root: {},
            )


class Item8BindingTests(unittest.TestCase):
    """Item 8 binds docs/characterization-report.md directly (issue #420).

    The report is a hand-assembled Markdown artifact, so unlike every other
    item there is no inventory to re-derive: the envelope is the report's
    repo path plus its live hash. These cases pin the binding down -- a
    regenerated envelope verifies, and a report edited without a re-pin, an
    envelope stripped of `provenance.input.path`, or a manifest pin that does
    not match the report each fail `verify_item` with the reason named.
    Before #420 the envelope carried a `content_hash` with no `path`, which
    the grader silently never checked and nothing in-repo re-computed.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        report = self.root / "docs" / "characterization-report.md"
        report.parent.mkdir(parents=True)
        report.write_text("# characterization report\n\nper-row verdicts.\n")
        (self.root / "manifests").mkdir()
        self.manifest_path = self.root / "manifests" / "gf180-usb2-phy.json"
        self.envelope_path = self.root / "manifests" / "item8-characterization.json"
        self._write_manifest(self._hash())
        self._write_envelope()

    def _hash(self) -> str:
        digest = hashlib.sha256(
            (self.root / "docs" / "characterization-report.md").read_bytes()
        ).hexdigest()
        return f"sha256:{digest}"

    def _manifest(self) -> dict:
        return json.loads(self.manifest_path.read_text())

    def _write_manifest(self, content_hash: str) -> None:
        manifest = {"evidence": {"8": {"file": "manifests/item8-characterization.json",
                                       "content_hash": content_hash}}}
        self.manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    def _write_envelope(self, env: dict | None = None) -> None:
        if env is None:
            env = inventories.build_envelope(self.root, "8")
        self.envelope_path.write_text(json.dumps(env, indent=2) + "\n")

    def _problems(self) -> list[str]:
        return inventories.verify_item(self.root, "8", self._manifest())

    def test_a_regenerated_envelope_verifies(self):
        self.assertEqual(self._problems(), [])

    def test_the_envelope_is_derived_from_the_tree(self):
        # `--regen` must reproduce the committed envelope byte-for-byte in
        # content: the summary is a constant, the hash comes from the file.
        committed = json.loads(self.envelope_path.read_text())
        self.assertEqual(committed, inventories.build_envelope(self.root, "8"))

    def test_the_envelope_declares_t1_item_and_the_repo_path(self):
        committed = json.loads(self.envelope_path.read_text())
        self.assertEqual(committed["t1_item"], 8)
        self.assertEqual(committed["source"], "docs/characterization-report.md")
        self.assertEqual(
            committed["provenance"]["input"]["path"],
            {"path": "docs/characterization-report.md", "scope": "repo"},
        )

    def test_a_report_edited_without_a_repin_fails(self):
        report = self.root / "docs" / "characterization-report.md"
        report.write_text(report.read_text() + "\nan unpinning edit.\n")
        problems = self._problems()
        self.assertTrue(any("hashes to" in p for p in problems), problems)
        self.assertTrue(any("content_hash is stale" in p for p in problems), problems)
        # The documented remedy re-pins against the edited report...
        env = inventories.build_envelope(self.root, "8")
        self.assertEqual(env["provenance"]["input"]["content_hash"], self._hash())
        # ...and with the re-pinned envelope and pin the item verifies again.
        self._write_envelope(env)
        self._write_manifest(self._hash())
        self.assertEqual(self._problems(), [])

    def test_an_envelope_without_provenance_path_fails(self):
        # The pre-#420 shape: a declared content_hash with no path, which the
        # grader silently never verified (input_verified: null).
        env = inventories.build_envelope(self.root, "8")
        del env["provenance"]["input"]["path"]
        self._write_envelope(env)
        problems = self._problems()
        self.assertTrue(any("provenance.input.path" in p for p in problems), problems)

    def test_a_manifest_pin_that_does_not_match_the_report_fails(self):
        self._write_manifest("sha256:" + "00" * 32)
        problems = self._problems()
        self.assertTrue(any("pins sha256:" in p and "hashes to" in p for p in problems),
                        problems)


if __name__ == "__main__":
    unittest.main(verbosity=2)
