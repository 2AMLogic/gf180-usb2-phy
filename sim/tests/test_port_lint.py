"""Self-test for sim/harness/port_lint.py (issue #267)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_DIR))

from harness import port_lint  # noqa: E402

DEFS = {"drv": ["VDD", "VSS", "A", "OE", "DP"]}


class PortLintTest(unittest.TestCase):
    def test_matching_count_passes(self):
        self.assertEqual([], port_lint.check_text("Xd 1 0 a oe dp drv\n", DEFS, "t"))

    def test_missing_net_flagged(self):
        problems = port_lint.check_text("Xd 1 0 a dp drv\n", DEFS, "t")
        self.assertEqual(1, len(problems))
        self.assertIn("4 net(s)", problems[0])

    def test_continuation_and_params_handled(self):
        text = "Xd 1 0 a\n+ oe dp drv m=2\n"
        self.assertEqual([], port_lint.check_text(text, DEFS, "t"))

    def test_unknown_subckt_ignored(self):
        self.assertEqual([], port_lint.check_text("Xq 1 2 other\n", DEFS, "t"))

    def test_repo_testbenches_are_clean(self):
        self.assertEqual([], port_lint.check_repo(SIM_DIR.parent))


if __name__ == "__main__":
    unittest.main()
