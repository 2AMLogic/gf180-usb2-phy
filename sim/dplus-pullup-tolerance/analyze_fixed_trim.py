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

A verdict is only reached on *complete* evidence (issue #136). Before any
electrical number is computed, the record's corner logs are checked against the
required matrix -- derived from this experiment's ``testbench/tb.json`` through
the harness's own corner/supply expansion, and never smaller than the ratified
floor (five MOS process families x -40/27/125 °C x nominal ±10 % supply = 45
corners) -- and every required corner must carry a 32-code table of finite,
positive resistances. Missing, unparseable, truncated, unexpected, or nonfinite
data is listed corner by corner and the script exits ``EXIT_INCOMPLETE`` (2)
with ``Overall: INCOMPLETE EVIDENCE``; it never reports PASS on a partial grid.

Exit codes: 0 PASS, 1 FAIL (complete evidence, a code drifts out of ±5 %),
2 incomplete evidence (no verdict).

It reads recorded evidence and writes nothing into the evidence tree, so it is
safe to re-run. Usage::

    python3 sim/dplus-pullup-tolerance/analyze_fixed_trim.py            # newest record
    python3 sim/dplus-pullup-tolerance/analyze_fixed_trim.py <record-id>
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent
SIM_DIR = EXPERIMENT_DIR.parent
if str(SIM_DIR) not in sys.path:
    sys.path.insert(0, str(SIM_DIR))

from harness import corners as corners_mod

NOMINAL_OHM = 1500.0
TOLERANCE_PCT = 5.0
CAL_TEMP_C = "27"
CAL_SUPPLY_V = "3.30"
CODE_COUNT = 32

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_INCOMPLETE = 2

#: ``print rvec`` in a DC sweep emits "<index>\t<sweep value>\t<value>".
#: ``nan``/``inf`` are matched on purpose so they are *reported*, not skipped.
_NUM = r"[-+0-9.eE]+|[-+]?(?:nan|inf(?:inity)?)"
_ROW_RE = re.compile(rf"^(\d+)\s+({_NUM})\s+({_NUM})\s*$", re.IGNORECASE)

Corner = tuple[str, str, str]


def latest_record_id() -> str:
    records = sorted((EXPERIMENT_DIR / "records").glob("*.md"))
    if not records:
        raise SystemExit(f"no records under {EXPERIMENT_DIR / 'records'}")
    return records[-1].stem


def inspect_code_table(log: Path) -> tuple[list[float], list[str]]:
    """The trim-code resistance table in ``log`` and what is wrong with it.

    Returns ``(values, problems)``; ``problems`` is empty only for a table of
    exactly ``CODE_COUNT`` finite, positive resistances indexed 0..31.
    """
    values: list[float] = []
    extra_rows = 0
    for line in log.read_text(errors="replace").splitlines():
        match = _ROW_RE.match(line)
        if not match:
            continue
        try:
            index, sweep, value = int(match.group(1)), float(match.group(2)), float(match.group(3))
        except ValueError:
            continue
        if abs(sweep - (index + 0.5)) > 1e-6:
            continue
        if index == len(values) and index < CODE_COUNT:
            values.append(value)
        elif index >= CODE_COUNT and index == len(values) + extra_rows:
            extra_rows += 1

    problems: list[str] = []
    if not values:
        problems.append("no `print rvec` code table found")
        return values, problems
    if len(values) < CODE_COUNT:
        problems.append(f"code table truncated: {len(values)} of {CODE_COUNT} codes")
    if extra_rows:
        problems.append(f"code table has {extra_rows} row(s) past code {CODE_COUNT - 1}")
    for code, value in enumerate(values):
        if not math.isfinite(value):
            problems.append(f"nonfinite resistance at code {code} ({value!r})")
        elif value <= 0.0:
            problems.append(f"non-positive resistance at code {code} ({value:g} Ω)")
    return values, problems


def read_code_table(log: Path) -> list[float]:
    """The (up to 32) effective pull-up resistances, indexed by trim code."""
    return inspect_code_table(log)[0]


def parse_corner_id(corner_id: str) -> Corner:
    """``ss_-40c_2.97v`` -> ``("ss", "-40", "2.97")`` (see sim/README.md)."""
    process, temp, supply = corner_id.rsplit("_", 2)
    if not (temp.endswith("c") and supply.endswith("v")):
        raise ValueError(f"{corner_id!r} is not <process>_<temp>c_<supply>v")
    return process, temp[:-1], supply[:-1]


def corner_name(corner: Corner) -> str:
    process, temp, supply = corner
    return f"{process}_{temp}c_{supply}v"


def required_matrix() -> list[Corner]:
    """Every (process, temp, supply) the record must cover, in harness order.

    The experiment's ``tb.json`` is expanded exactly as ``run_corners.py``
    expands it, then unioned with the ratified floor (``harness.corners``
    defaults: the five MOS families, -40/27/125 °C, nominal ±10 %), so a
    narrowed manifest can widen nothing away. Discovered log names play no
    part: they are what is being checked, not what defines the check.
    """
    manifest_path = EXPERIMENT_DIR / "testbench" / "tb.json"
    if not manifest_path.is_file():
        raise SystemExit(f"no testbench manifest at {manifest_path}: cannot derive the required matrix")
    manifest = json.loads(manifest_path.read_text())
    nominal = float(manifest.get("nominal_supply_v", corners_mod.DEFAULT_NOMINAL_SUPPLY_V))
    tolerance = float(manifest.get("supply_tolerance", corners_mod.DEFAULT_SUPPLY_TOLERANCE))
    temps = [float(t) for t in manifest.get("temperatures_c", corners_mod.DEFAULT_TEMPERATURES_C)]
    processes = corners_mod.resolve_corners(list(manifest.get("corners", ())) or None)

    grids = [
        corners_mod.build_grid(processes, temps, corners_mod.supply_points(nominal, tolerance)),
        corners_mod.build_grid(
            corners_mod.resolve_corners([corners_mod.DEFAULT_CORNER_SET]),
            corners_mod.DEFAULT_TEMPERATURES_C,
            corners_mod.supply_points(nominal, corners_mod.DEFAULT_SUPPLY_TOLERANCE),
        ),
    ]
    matrix: list[Corner] = []
    for grid in grids:
        for point in grid:
            corner = parse_corner_id(point.corner_id)
            if corner not in matrix:
                matrix.append(corner)
    return matrix


def collect_evidence(corners_dir: Path, required: list[Corner]) -> tuple[dict[Corner, list[float]], list[str]]:
    """Validated tables for every required corner, plus a diagnostic per defect."""
    tables: dict[Corner, list[float]] = {}
    diagnostics: list[str] = []
    seen: set[Corner] = set()
    for log in sorted(corners_dir.glob("*.log")) if corners_dir.is_dir() else []:
        try:
            corner = parse_corner_id(log.stem)
        except ValueError:
            diagnostics.append(f"{log.name}: unexpected log, name is not a <process>_<temp>c_<supply>v corner id")
            continue
        if corner not in required:
            diagnostics.append(f"{log.name}: unexpected corner {log.stem}, not in the required matrix")
            continue
        seen.add(corner)
        values, problems = inspect_code_table(log)
        if problems:
            diagnostics.extend(f"{log.name}: {problem}" for problem in problems)
            continue
        tables[corner] = values

    missing = [c for c in required if c not in seen]
    by_process: dict[str, list[Corner]] = {}
    for corner in missing:
        by_process.setdefault(corner[0], []).append(corner)
    per_process = {p: sum(1 for c in required if c[0] == p) for p in by_process}
    for process, absent in by_process.items():
        names = ", ".join(corner_name(c) for c in absent)
        if len(absent) == per_process[process]:
            diagnostics.append(f"process family {process}: all {len(absent)} corners missing ({names})")
        else:
            diagnostics.append(f"process family {process}: {len(absent)} corner(s) missing ({names})")
    return tables, diagnostics


def main(argv: list[str]) -> int:
    record_id = argv[1] if len(argv) > 1 else latest_record_id()
    corners_dir = EXPERIMENT_DIR / "corners" / record_id
    required = required_matrix()
    tables, diagnostics = collect_evidence(corners_dir, required)

    print(f"record   : {record_id}")
    print(f"corners  : {len(tables)} of {len(required)} required corner(s) usable under "
          f"sim/dplus-pullup-tolerance/corners/{record_id}/")
    if not corners_dir.is_dir():
        diagnostics.insert(0, f"no corner-log directory at {corners_dir}")

    if diagnostics or len(tables) != len(required):
        print()
        print("INCOMPLETE EVIDENCE -- no fixed-trim verdict is computed until every required")
        print(f"corner supplies a {CODE_COUNT}-code table of finite resistances:")
        for line in diagnostics:
            print(f"  - {line}")
        print()
        print("Overall: INCOMPLETE EVIDENCE -- the record does not cover the temperature and "
              "supply axes of spec §8.1, so it can neither pass nor fail spec §5.")
        return EXIT_INCOMPLETE

    processes = list(dict.fromkeys(p for p, _, _ in required))
    print(f"criterion: one trim code chosen at {CAL_TEMP_C} °C / {CAL_SUPPLY_V} V, held across")
    print(f"           that process corner's whole (T, V) grid, must stay inside "
          f"±{TOLERANCE_PCT:g} % of {NOMINAL_OHM:g} Ω (spec §5)")
    print()
    header = (f"{'process':<9}{'code':>6}{'R@cal Ω':>12}{'min Ω':>12}{'max Ω':>12}"
              f"{'worst %':>10}  verdict")
    print(header)
    print("-" * len(header))

    overall_ok = True
    for process in sorted(processes):
        calibration = tables.get((process, CAL_TEMP_C, CAL_SUPPLY_V))
        if calibration is None:
            # Only reachable if the manifest's matrix omits the tester point.
            print(f"{process:<9}  no calibration point ({CAL_TEMP_C} °C / {CAL_SUPPLY_V} V) "
                  "in the required matrix")
            print()
            print("Overall: INCOMPLETE EVIDENCE -- no calibration point to choose a code at.")
            return EXIT_INCOMPLETE
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
    return EXIT_PASS if overall_ok else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main(sys.argv))
