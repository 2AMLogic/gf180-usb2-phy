#!/usr/bin/env python3
"""Self-test for ``scripts/klt_run.py``: the npm scripts' klt wrapper.

`npm run test` / `npm run check:all` used to invoke a bare ``klt`` from
``$PATH`` -- no resolution, no pin check (issue #438). The wrapper gives
them the same two halves every Python harness gets from
``klt_resolve.py``; these cases pin that contract without running a real
klt, klayout or the PDK, so they run in CI:

  * **resolution + gating** -- the requested command only runs when the
    resolved klt's own ``--version`` matches the repo pin (a PEP 440
    local segment like ``+gabc`` does not count as a mismatch); anything
    else -- another version, or no version reported at all -- fails
    loudly naming both versions, before the command runs;
  * **pass-through** -- the requested arguments reach the resolved klt
    verbatim and its exit status propagates, so ``npm``'s ``&&`` chains
    keep their meaning.

The klt side is an executable shell stub seeded into
``klt_argv``/``pinned_klt_version`` via ``unittest.mock.patch.object``,
so both gate branches are exercised deterministically on every host,
pinned venv or not.

Usage:
    python3 scripts/test_klt_run.py    (or: python3 -m pytest scripts/test_klt_run.py)
Exit codes: 0 all cases behave as specified, 1 otherwise.
"""

from __future__ import annotations

import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import klt_run as krun  # noqa: E402


def _stub_klt(bin_dir: Path, version_stdout: str, version_exit: int = 0) -> Path:
    """An executable stub: `--version` prints `version_stdout`; any other
    invocation records its arguments beside itself and exits 0."""
    invoked = bin_dir / "invoked.txt"
    stub = bin_dir / "klt-stub"
    stub.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "--version" ]; then\n'
        f"  printf '%s\\n' '{version_stdout}'\n"
        f"  exit {version_exit}\n"
        "fi\n"
        f": > '{invoked}'\n"
        'for arg in "$@"; do printf \'%s\\n\' "$arg" >> '
        f"'{invoked}'; done\n"
        "exit 0\n",
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return stub


class TestKltRun(unittest.TestCase):
    PIN = "1.2.3"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="klt-run-selftest-")
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def _patch_klt(self, version_stdout: str, version_exit: int = 0) -> Path:
        stub = _stub_klt(self.dir, version_stdout, version_exit)
        for name, value in (
            ("klt_argv", [str(stub)]),
            ("pinned_klt_version", self.PIN),
        ):
            patcher = patch.object(krun, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        return stub

    def test_no_arguments_is_a_usage_error(self):
        self.assertEqual(krun.main([]), 2)

    def test_pinned_klt_runs_the_requested_command_verbatim(self):
        self._patch_klt(f"klt {self.PIN}")
        argv = ["lvs", "req.json", "--format", "json"]
        self.assertEqual(krun.main(argv), 0)
        invoked = (self.dir / "invoked.txt").read_text().splitlines()
        self.assertEqual(invoked, argv)

    def test_local_version_segment_still_runs(self):
        """`1.2.3+gabc` is the pin `1.2.3` -- the wrapper must not reject it."""
        self._patch_klt(f"klt {self.PIN}+g5dbbad0")
        self.assertEqual(krun.main(["--version"]), 0)

    def test_unpinned_klt_is_refused_naming_both_versions(self):
        self._patch_klt("klt 9.9.9.dev1+gdeadbee")
        with self.assertRaises(SystemExit) as ctx:
            krun.main(["erc", "x.gds"])
        message = str(ctx.exception)
        self.assertIn("9.9.9.dev1", message)
        self.assertIn(self.PIN, message)
        # Refusal happens before the command runs -- nothing was invoked.
        self.assertFalse((self.dir / "invoked.txt").exists())

    def test_klt_reporting_no_version_is_refused(self):
        self._patch_klt("", version_exit=1)
        with self.assertRaises(SystemExit) as ctx:
            krun.main(["erc", "x.gds"])
        self.assertIn("--version", str(ctx.exception))
        self.assertFalse((self.dir / "invoked.txt").exists())

    def test_missing_klt_binary_is_an_actionable_refusal(self):
        """Fallback klt not on $PATH and klayout_tools not importable: the
        gate refuses with its error contract, not a raw traceback."""
        missing = str(self.dir / "no-such-klt")
        for name, value in (
            ("klt_argv", [missing]),
            ("pinned_klt_version", self.PIN),
        ):
            patcher = patch.object(krun, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        with self.assertRaises(SystemExit) as ctx:
            krun.main(["erc", "x.gds"])
        self.assertIn("--version", str(ctx.exception))
        self.assertIn(missing, str(ctx.exception))
        self.assertFalse((self.dir / "invoked.txt").exists())

    def test_child_exit_status_propagates(self):
        """npm's `&&` chains keep their meaning: klt's exit status is the
        wrapper's, uncaptured and unadorned."""
        stub = _stub_klt(self.dir, f"klt {self.PIN}")
        argv = ["functional-verification", "request.json"]
        with patch.object(krun, "resolve_gated_klt", return_value=[str(stub)]):
            with patch.object(
                krun.subprocess, "run", return_value=Mock(returncode=3)
            ) as run:
                self.assertEqual(krun.main(argv), 3)
        self.assertEqual(run.call_args.args[0], [str(stub)] + argv)


if __name__ == "__main__":
    unittest.main(verbosity=2)
