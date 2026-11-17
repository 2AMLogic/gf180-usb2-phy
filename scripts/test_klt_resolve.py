#!/usr/bin/env python3
"""Self-test for ``scripts/klt_resolve.py``: klt resolution + version gate.

These pin the two contracts issue #431 rests on, without running a real
klt, klayout or the PDK, so they run in CI:

  * **resolution** -- ``klt_argv()`` prefers the interpreter's own klt
    (``python -m klayout_tools.cli``) whenever ``klayout_tools`` is
    importable, and falls back to a bare ``klt`` only when it is not --
    the PR #430 failure was a harness silently grading with an unpinned
    klt from ``$PATH``;
  * **the pin has one source of truth** -- ``pinned_klt_version()`` parses
    ``KLT_VERSION=`` from ``scripts/setup-env.sh`` (never a second
    hard-coded copy), and falls back to asking the resolved klt itself
    only when the file cannot be parsed;
  * **the gate bites** -- a report whose klt version matches the pin
    passes (a PEP 440 local segment like ``+gabc`` does not count as a
    mismatch), a report from any other klt -- a ``.dev`` build included --
    fails naming both versions, and a report carrying no version at all
    fails naming the pin.

The import branch is forced by seeding ``sys.modules`` (a ``None`` entry
makes ``import`` raise ``ImportError``), so both branches are exercised
deterministically on every host, pinned venv or not.

Zero dependencies beyond the Python 3 standard library.

Usage:
    python3 scripts/test_klt_resolve.py   (or: python3 -m pytest scripts/test_klt_resolve.py)
Exit codes: 0 all tests pass, non-zero at least one did not.
"""

from __future__ import annotations

import stat
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import klt_resolve as kr  # noqa: E402


def _stub_klt(bin_dir: Path, name: str, stdout: str, exit_code: int = 0) -> Path:
    """An executable stub whose `--version` output is `stdout`."""
    stub = bin_dir / name
    stub.write_text(
        "#!/bin/sh\n"
        f"cat <<'EOF'\n{stdout}\nEOF\n"
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return stub


def _fake_klayout_tools() -> dict[str, types.ModuleType]:
    pkg = types.ModuleType("klayout_tools")
    cli = types.ModuleType("klayout_tools.cli")
    pkg.cli = cli
    return {"klayout_tools": pkg, "klayout_tools.cli": cli}


class TestKltArgv(unittest.TestCase):
    def test_importable_prefers_the_interpreters_own_klt(self):
        with patch.dict(sys.modules, _fake_klayout_tools()):
            self.assertEqual(kr.klt_argv(), [sys.executable, "-m", "klayout_tools.cli"])

    def test_not_importable_falls_back_to_path_klt(self):
        # A None entry in sys.modules makes `import klayout_tools.cli` raise
        # ImportError, forcing the fallback branch on any host.
        with patch.dict(sys.modules, {"klayout_tools": None, "klayout_tools.cli": None}):
            self.assertEqual(kr.klt_argv(), ["klt"])


class TestPinnedKltVersion(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="klt-resolve-selftest-")
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def _setup_env(self, pin: str | None) -> Path:
        setup_env = self.dir / "setup-env.sh"
        lines = ["#!/bin/sh", 'echo "fixture"']
        if pin is not None:
            lines.insert(1, f'KLT_VERSION="{pin}"')
        setup_env.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return setup_env

    def test_pin_comes_from_setup_env(self):
        self.assertEqual(kr.pinned_klt_version(self._setup_env("1.2.3")), "1.2.3")

    def test_no_pin_in_file_falls_back_to_the_resolved_klt(self):
        stub = _stub_klt(self.dir, "klt-stub", "klt 9.9.9+gdeadbee")
        version = kr.pinned_klt_version(self._setup_env(None), klt=[str(stub)])
        self.assertEqual(version, "9.9.9+gdeadbee")

    def test_missing_file_falls_back_to_the_resolved_klt(self):
        stub = _stub_klt(self.dir, "klt-stub", "klt 9.9.9")
        version = kr.pinned_klt_version(self.dir / "no-such-setup-env.sh", klt=[str(stub)])
        self.assertEqual(version, "9.9.9")

    def test_both_routes_failed_is_a_loud_error(self):
        with self.assertRaises(kr.KltVersionError):
            kr.pinned_klt_version(self.dir / "no-such-setup-env.sh", klt=["no-such-klt"])

    def test_repo_pin_parses_as_a_release_version(self):
        # The real repo pin (the single source of truth this gate defends):
        # a bare X.Y.Z, today 0.9.0 -- asserted by shape, not by literal,
        # so a deliberate pin bump does not break this test.
        self.assertRegex(kr.pinned_klt_version(), r"^\d+\.\d+\.\d+$")


class TestVersionGate(unittest.TestCase):
    PIN = "0.9.0"

    def _report(self, **provenance) -> dict:
        return {"erc_status": "clean", "provenance": {"klt_version": None, **provenance}}

    def test_matching_version_passes_and_is_returned_normalized(self):
        report = self._report(klt_version="0.9.0+g5dbbad0")
        self.assertEqual(
            kr.require_pinned_klt_version(report, self.PIN, "fixture"),
            "0.9.0",
        )

    def test_dev_of_another_version_fails_naming_both_versions(self):
        report = self._report(klt_version="0.9.3.dev234+g5ed4e55bffbd")
        with self.assertRaises(kr.KltVersionError) as ctx:
            kr.require_pinned_klt_version(report, self.PIN, "fixture")
        self.assertIn("0.9.3.dev234", str(ctx.exception))
        self.assertIn(self.PIN, str(ctx.exception))

    def test_missing_version_fails_naming_the_pin(self):
        with self.assertRaises(kr.KltVersionError) as ctx:
            kr.require_pinned_klt_version({"erc_status": "clean"}, self.PIN, "fixture")
        self.assertIn(self.PIN, str(ctx.exception))

    def test_signoff_report_build_block_is_read_too(self):
        report = {"build": {"version": "0.9.0", "package_version": "0.9.0"}}
        self.assertEqual(
            kr.require_pinned_klt_version(report, self.PIN, "fixture"), "0.9.0"
        )
        self.assertEqual(kr.report_klt_version({"build": {"package_version": "0.9.0"}}), "0.9.0")

    def test_report_version_lookup_order(self):
        self.assertEqual(
            kr.report_klt_version({"provenance": {"klt_version": "1.0.0"}}), "1.0.0"
        )
        self.assertIsNone(kr.report_klt_version({}))
        self.assertIsNone(kr.report_klt_version({"provenance": {}}))
        self.assertIsNone(kr.report_klt_version({"build": {}}))


if __name__ == "__main__":
    unittest.main()
