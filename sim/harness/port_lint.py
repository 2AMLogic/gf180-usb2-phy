"""Port-count lint for testbench subcircuit instances (issue #267).

A ``.subckt`` instance with the wrong number of nets still parses in ngspice
when the extra/missing node happens to line up, and silently leaves a port
floating or mis-bound. This checks every ``X`` instance in
``sim/*/testbench/*.spice`` whose subcircuit is defined under
``design/netlist/*.spice`` against that definition's port list.
Stdlib only.
"""

from __future__ import annotations

import re
from pathlib import Path


def _logical_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        if raw.startswith("+") and lines:
            lines[-1] += " " + raw[1:]
        else:
            lines.append(raw)
    return lines


def subckt_ports(netlist_dir: Path) -> dict[str, list[str]]:
    """Map lower-cased subckt name -> ports for every .subckt in the dir."""
    defs: dict[str, list[str]] = {}
    for path in sorted(netlist_dir.glob("*.spice")):
        for line in _logical_lines(path.read_text()):
            tok = line.split()
            if len(tok) >= 2 and tok[0].lower() == ".subckt":
                defs[tok[1].lower()] = [t for t in tok[2:] if "=" not in t]
    return defs


def check_text(text: str, defs: dict[str, list[str]], label: str) -> list[str]:
    problems = []
    for line in _logical_lines(text):
        if not line[:1] in ("X", "x"):
            continue
        tok = [t for t in line.split() if "=" not in t]
        if len(tok) < 2:
            continue
        name = tok[-1].lower()
        if name not in defs:
            continue
        nets = len(tok) - 2
        if nets != len(defs[name]):
            problems.append(
                f"{label}: instance {tok[0]} of {name} passes {nets} net(s), "
                f"subckt declares {len(defs[name])} port(s) "
                f"({' '.join(defs[name])})"
            )
    return problems


def check_repo(root: Path) -> list[str]:
    defs = subckt_ports(root / "design" / "netlist")
    problems: list[str] = []
    for tb in sorted((root / "sim").glob("*/testbench/*.spice")):
        problems += check_text(tb.read_text(), defs, str(tb.relative_to(root)))
    return problems
