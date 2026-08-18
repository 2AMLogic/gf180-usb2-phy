#!/usr/bin/env python3
"""Does one trim code, set once at test, hold ±5 % over temperature and supply?

``sim/dplus-pullup-tolerance``'s evidence record answers the question the
harness can ask on its own: *at each PVT corner independently*, is there a trim
code inside 1.425-1.575 kΩ? That is a necessary condition, but it is not the
whole of what ``spec/usb2-device-phy.md`` §5 requires. §5's mechanism is "a
trimmed/calibrated resistor (e.g., a binary-weighted trim ladder set **at
test**)" -- one code is burned in per die, at whatever the tester's ambient
and supply are, and it then has to hold ±5 % across the *whole* temperature and
supply envelope of §8.1. A per-corner "some code fits" result would still pass
if the winning code changed from corner to corner, which no real part can do.

This script closes that gap from the same evidence, without re-simulating: the
corner logs the harness already wrote contain the full 32-code resistance table
(``print rvec``) at every one of the 45 points. So for each process corner it

1. picks the code that best hits 1.5 kΩ at the calibration point -- 27 °C at
   the nominal 3.30 V supply, which is the tester condition;
2. holds that code fixed and reads its resistance at all nine
   (temperature, supply) points of that process corner;
3. reports the worst deviation, against §5's ±5 % window.

It reads recorded evidence and writes nothing into the evidence tree, so it is
safe to re-run. Usage::

    python3 sim/dplus-pullup-tolerance/analyze_fixed_trim.py            # newest record
    python3 sim/dplus-pullup-tolerance/analyze_fixed_trim.py <record-id>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent

NOMINAL_OHM = 1500.0
TOLERANCE_PCT = 5.0
CAL_TEMP_C = "27"
CAL_SUPPLY_V = "3.30"

#: ``print rvec`` in a DC sweep emits "<index>\t<sweep value>\t<value>".
_ROW_RE = re.compile(r"^(\d+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$")


def latest_record_id() -> str:
    records = sorted((EXPERIMENT_DIR / "records").glob("*.md"))
    if not records:
        raise SystemExit(f"no records under {EXPERIMENT_DIR / 'records'}")
    return records[-1].stem


def read_code_table(log: Path) -> list[float]:
    """The 32 effective pull-up resistances, indexed by trim code."""
    values: list[float] = []
    for line in log.read_text().splitlines():
        match = _ROW_RE.match(line)
        if not match:
            continue
        index, sweep, value = int(match.group(1)), float(match.group(2)), float(match.group(3))
        if index != len(values) or abs(sweep - (index + 0.5)) > 1e-6:
            continue
        values.append(value)
    return values


def parse_corner_id(corner_id: str) -> tuple[str, str, str]:
    """``ss_-40c_2.97v`` -> ``("ss", "-40", "2.97")`` (see sim/README.md)."""
    process, temp, supply = corner_id.rsplit("_", 2)
    return process, temp.rstrip("c"), supply.rstrip("v")


def main(argv: list[str]) -> int:
    record_id = argv[1] if len(argv) > 1 else latest_record_id()
    corners_dir = EXPERIMENT_DIR / "corners" / record_id
    if not corners_dir.is_dir():
        raise SystemExit(f"no corner logs at {corners_dir}")

    tables: dict[tuple[str, str, str], list[float]] = {}
    for log in sorted(corners_dir.glob("*.log")):
        table = read_code_table(log)
        if table:
            tables[parse_corner_id(log.stem)] = table

    processes = sorted({p for p, _, _ in tables})
    print(f"record   : {record_id}")
    print(f"logs     : {len(tables)} corner(s) under sim/dplus-pullup-tolerance/corners/{record_id}/")
    print(f"criterion: one trim code chosen at {CAL_TEMP_C} °C / {CAL_SUPPLY_V} V, held across")
    print(f"           that process corner's whole (T, V) grid, must stay inside "
          f"±{TOLERANCE_PCT:g} % of {NOMINAL_OHM:g} Ω (spec §5)")
    print()
    header = (f"{'process':<9}{'code':>6}{'R@cal Ω':>12}{'min Ω':>12}{'max Ω':>12}"
              f"{'worst %':>10}  verdict")
    print(header)
    print("-" * len(header))

    overall_ok = True
    for process in processes:
        calibration = tables.get((process, CAL_TEMP_C, CAL_SUPPLY_V))
        if calibration is None:
            print(f"{process:<9}  no calibration point in this record")
            overall_ok = False
            continue
        code = min(range(len(calibration)), key=lambda c: abs(calibration[c] - NOMINAL_OHM))
        held = [table[code] for (p, _, _), table in tables.items() if p == process]
        worst = max(abs(r - NOMINAL_OHM) / NOMINAL_OHM * 100.0 for r in held)
        ok = worst <= TOLERANCE_PCT
        overall_ok &= ok
        print(f"{process:<9}{code:>6}{calibration[code]:>12.1f}{min(held):>12.1f}"
              f"{max(held):>12.1f}{worst:>10.2f}  {'PASS' if ok else 'FAIL'}")

    print()
    print(f"Overall: {'PASS' if overall_ok else 'FAIL'} -- a single per-die trim code "
          f"{'holds' if overall_ok else 'does NOT hold'} ±{TOLERANCE_PCT:g} % over the "
          "temperature and supply axes of spec §8.1.")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
