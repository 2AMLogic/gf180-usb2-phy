#!/usr/bin/env python3
"""Check the digital<->analog pin contract of DR-0004 against the sources.

The pin table in ``spec/decisions/0004-digital-analog-pin-contract.md``
(between the ``pin-contract`` markers) is compared with

  * the ``.subckt`` pin lists (and ``*.PININFO`` directions) of every
    ``design/netlist/*.spice``, and
  * the module ports of ``usb_utmi_phy`` in ``rtl/usb_utmi_phy.v``.

Rules:
  * ``current`` rows: the named port / pin must exist with the stated
    direction (digital: input/output; analog: I/O/B per PININFO).
  * ``planned #N`` rows (both sides), ``planned-dig #N`` (digital side only;
    analog pin already exists) and ``planned-ana #N``: the planned side must
    NOT exist yet. Landing the follow-up therefore forces the table row to
    be flipped to ``current``.
  * every module port and every ``.subckt`` pin must be covered by a row.

Zero dependencies beyond the Python 3 standard library.

Usage:
    python3 scripts/check_pin_contract.py [--root DIR]
Exit codes: 0 contract holds, 1 disagreement (each printed), 2 usage/parse
error.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RECORD = "spec/decisions/0004-digital-analog-pin-contract.md"
RTL = "rtl/usb_utmi_phy.v"
NETLIST_GLOB = "design/netlist/*.spice"
MODULE = "usb_utmi_phy"
BEGIN, END = "<!-- pin-contract:begin -->", "<!-- pin-contract:end -->"


class ParseError(Exception):
    pass


def parse_table(text: str) -> list[dict]:
    if BEGIN not in text or END not in text:
        raise ParseError(f"{RECORD}: pin-contract markers not found")
    block = text.split(BEGIN, 1)[1].split(END, 1)[0]
    rows = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip().strip("`") for c in line.strip("|").split("|")]
        if cells[0] in ("Contract pin",) or set(cells[0]) <= {"-"}:
            continue
        if len(cells) != 8:
            raise ParseError(f"table row has {len(cells)} cells, want 8: {line}")
        keys = ("pin", "dport", "ddir", "apin", "adir", "status", "owner", "src")
        row = dict(zip(keys, cells))
        if not re.fullmatch(r"current|planned(-dig|-ana)? #\d+(-\d+)?", row["status"]):
            raise ParseError(f"bad status {row['status']!r} in row {row['pin']}")
        rows.append(row)
    if not rows:
        raise ParseError(f"{RECORD}: empty pin table")
    return rows


def parse_verilog_ports(text: str) -> dict[str, tuple[str, int]]:
    """Return {port: (direction, width)} for MODULE."""
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    m = re.search(rf"\bmodule\s+{MODULE}\s*\((.*?)\)\s*;", text, flags=re.S)
    if not m:
        raise ParseError(f"{RTL}: module {MODULE} header not found")
    ports: dict[str, tuple[str, int]] = {}
    direction, width = None, 1
    for item in m.group(1).split(","):
        item = item.strip()
        if not item:
            continue
        d = re.match(r"(input|output|inout)\b", item)
        if d:
            direction, width = d.group(1), 1
            r = re.search(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", item)
            if r:
                width = abs(int(r.group(1)) - int(r.group(2))) + 1
        if direction is None:
            raise ParseError(f"{RTL}: port without direction: {item}")
        name = re.findall(r"[A-Za-z_]\w*", re.sub(r"\[[^\]]*\]", "", item))[-1]
        ports[name] = (direction, width)
    return ports


def parse_netlists(root: Path) -> dict[str, dict[str, str]]:
    """Return {subckt: {pin: dir}}; dir from *.PININFO (default '?')."""
    cells: dict[str, dict[str, str]] = {}
    files = sorted(root.glob(NETLIST_GLOB))
    if not files:
        raise ParseError(f"no netlists match {NETLIST_GLOB}")
    for f in files:
        cur, lines = None, f.read_text().splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.lower().startswith(".subckt"):
                toks = line.split()
                while i + 1 < len(lines) and lines[i + 1].startswith("+"):
                    i += 1
                    toks += lines[i][1:].split()
                cur = toks[1]
                pins = [t for t in toks[2:] if "=" not in t]
                cells[cur] = {p: "?" for p in pins}
            elif line.startswith("*.PININFO") and cur:
                for tok in line.split()[1:]:
                    p, _, d = tok.partition(":")
                    if p in cells[cur]:
                        cells[cur][p] = d
            elif line.lower().startswith(".ends"):
                cur = None
            i += 1
    return cells


def check(root: Path) -> list[str]:
    rows = parse_table((root / RECORD).read_text())
    ports = parse_verilog_ports((root / RTL).read_text())
    cells = parse_netlists(root)
    errs: list[str] = []
    covered_ports: set[str] = set()
    covered_pins: set[tuple[str, str]] = set()
    dir_map = {"input": "input", "output": "output", "inout": "inout"}

    for r in rows:
        planned_dig = r["status"].startswith(("planned #", "planned-dig"))
        planned_ana = r["status"].startswith(("planned #", "planned-ana"))
        # --- digital side
        if r["dport"] != "-":
            m = re.fullmatch(r"(\w+)(?:\[(\d+)(?::(\d+))?\])?", r["dport"])
            if not m:
                errs.append(f"{r['pin']}: unparseable digital port {r['dport']!r}")
                continue
            base, hi, lo = m.group(1), m.group(2), m.group(3)
            exists = base in ports
            if planned_dig:
                if exists:
                    errs.append(f"{r['pin']}: planned but port {base!r} already in {RTL}; flip row to current")
            elif not exists:
                errs.append(f"{r['pin']}: port {base!r} missing from {RTL}")
            else:
                covered_ports.add(base)
                d, w = ports[base]
                if dir_map.get(r["ddir"]) != d:
                    errs.append(f"{r['pin']}: port {base} is {d}, table says {r['ddir']}")
                if hi is not None:
                    want = int(hi) + 1 if lo is not None else None
                    if lo is not None and (int(lo) != 0 or w != want):
                        errs.append(f"{r['pin']}: port {base} width {w}, table says [{hi}:{lo}]")
                    if lo is None and int(hi) >= w:
                        errs.append(f"{r['pin']}: bit {hi} outside {base} width {w}")
                elif w != 1:
                    errs.append(f"{r['pin']}: port {base} is {w} bits wide, table says scalar")
        elif r["ddir"] != "-":
            errs.append(f"{r['pin']}: digital port '-' but direction {r['ddir']!r}")
        # --- analog side
        if r["apin"] != "-":
            cell, _, pin = r["apin"].partition(".")
            have = cell in cells and pin in cells[cell]
            if planned_ana:
                if have:
                    errs.append(f"{r['pin']}: planned but {r['apin']} already in netlist; flip row to current")
            elif cell not in cells:
                errs.append(f"{r['pin']}: subckt {cell!r} not found in {NETLIST_GLOB}")
            elif pin not in cells[cell]:
                errs.append(f"{r['pin']}: pin {pin!r} missing from .subckt {cell}")
            else:
                covered_pins.add((cell, pin))
                if cells[cell][pin] != r["adir"]:
                    errs.append(f"{r['pin']}: {r['apin']} is {cells[cell][pin]} in PININFO, table says {r['adir']}")
        elif r["adir"] != "-":
            errs.append(f"{r['pin']}: analog pin '-' but direction {r['adir']!r}")

    for p in ports:
        if p not in covered_ports:
            errs.append(f"{RTL}: port {p!r} not covered by a current row in the pin table")
    for cell, pins in cells.items():
        for p in pins:
            if (cell, p) not in covered_pins:
                errs.append(f"design/netlist: {cell}.{p} not covered by a current row in the pin table")
    return errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args(argv)
    try:
        errs = check(args.root)
    except (ParseError, OSError) as e:
        print(f"check_pin_contract: {e}", file=sys.stderr)
        return 2
    for e in errs:
        print(f"FAIL {e}")
    if errs:
        return 1
    print("check_pin_contract: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
