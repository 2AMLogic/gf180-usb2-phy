#!/usr/bin/env python3
"""Compare committed ``klt sim`` envelopes with the evidence records they re-emit.

For each analog bench, read the per-corner table of an existing evidence
record (``sim/<bench>/records/<id>.md``) and the matching ``klt sim`` envelope
(``klt-sim-report.json``), and write

* ``docs/analog-envelope-agreement.md``  -- per-row summary (worst delta and
  where it falls), and
* ``docs/analog-envelope-agreement.csv`` -- every (bench, corner, row) pair
  with both values and the delta.

Read-only with respect to records and envelopes (they are append-only
evidence); this script only writes the two files above.

    python3 sim/envelope_agreement.py            # regenerate both files
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SIM = REPO / "sim"
DOCS = REPO / "docs"

# bench -> (spec row ids it covers, record id compared against, envelope dir id,
#           envelope-measurement -> (record column, scale applied to the envelope value))
BENCHES = {
    "diff-receiver-sensitivity": ("receiver-thresholds", "20261008-193113-2e9f63e", "20261017-194653-49d005c"),
    "se-receiver-dp-thresholds": ("receiver-thresholds", "20260817-203631-a408cb6", "20261017-194832-49d005c"),
    "se-receiver-dm-thresholds": ("receiver-thresholds", "20260817-203654-a408cb6", "20261017-195101-49d005c"),
    "driver-signal-quality": ("rise-fall-time, crossover-voltage, full-speed-signal-quality", "20261015-104027-d109790", "20261015-104027-d109790"),
    "dplus-pullup-tolerance": ("dplus-pullup-tolerance", "20260905-185112-6bfe679", "20261017-195431-49d005c"),
}

FINDINGS = """
## Findings

All five benches pass at all 45 corners in the envelopes, and no cited
envelope disagrees with its record about a pass/fail verdict. Agreement by
bench:

- **`diff-receiver-sensitivity`, `driver-signal-quality`**: identical to the
  record to printed precision (relative delta at the level of floating-point
  rounding). The driver envelope *is* the run the record transcribes, so that
  comparison checks the transcription only.
- **`se-receiver-dp-thresholds`, `se-receiver-dm-thresholds`**:
  `vth_v` and `out_at_vih` identical. `out_at_vil` differs by ~9e-4 relative
  at the worst corner, but the quantity is ~2e-9 of the rail (leakage level,
  limit is -0.05..0.1), so the difference is simulator noise on a
  zero-signal output.
- **`dplus-pullup-tolerance`: a real disagreement, not noise.** `r_code0_ohm`
  agrees (<=2.3e-6 relative). `r_code31_ohm`, `r_best_ohm`, `best_code`,
  `best_err_pct` and `trim_step_pct` differ from record `20260905-185112-6bfe679`
  by up to 3 %, 1 code, and 0.4 percentage points of tolerance (worst:
  `best_err_pct` 0.538 % in the record vs 0.144 % in the envelope at
  `ff_125c_2.97v`). Both are far inside the +/-5 % bound, so no verdict moves,
  but the numbers are not the record's. What was checked:
  * The bench netlist change made for `klt sim` (the pull-up supply, enable
    and trim bits follow `v(vdd)` instead of being separate sources at
    `{vdd_val}`) is neutral: the bench's netlist, run through the local
    harness on this host (netlists compared, not the `measure` spelling),
    reproduces the envelope, e.g. `fs_125c_3.63v` `r_best_ohm` 1523.14,
    `best_code` 18, `best_err_pct` 1.54284, both ways. The local `measure`
    is not the pre-#188 one: #188 changed its comparison from `>` to `gt`
    (ngspice-46 parses `>` as I/O redirection), so the pre-#188 bench
    would not run on ngspice-46.
  * The envelope matches the local harness on the same ngspice-46 and the same
    PDK build (`open_pdks c6d73a35`, the fleet's PDK stamp matches).
  * The record was taken with **ngspice-47** (its own text says so), and its
    `r_best_ohm`/`best_code` expressions spell the comparison with `>`, which
    ngspice-46's control language parses as I/O redirection (the pre-#188
    local `measure` failed outright on ngspice-46 for that reason; both the
    local `measure` and the `klt_measure` now spell it `gt`). `r_code31_ohm` has no comparison in it and
    still differs (1070.37 vs 1067.75 at that corner), so the `>` spelling does
    not explain everything.
  * Not established: whether ngspice-47 vs 46 accounts for the remaining
    difference. It could not be tested here (no ngspice-47 on this host). The
    envelope is the evidence for the current tree; the older record is left
    unedited.
"""

ROW = re.compile(r"^\s*\|\s*`([^`]+)`\s*\|(.*)\|\s*(PASS|FAIL|ERROR)\s*\|\s*$")


def parse_record(path: Path) -> tuple[list[str], dict[tuple, list[float]]]:
    """(measurement column names, {(process, temp_c, vdd): [values]})."""
    header: list[str] | None = None
    rows: dict[tuple, list[float]] = {}
    for line in path.read_text().splitlines():
        if header is None and line.strip().startswith("| corner-id"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            header = cells[1:-1]
            continue
        m = ROW.match(line)
        if not m or header is None:
            continue
        cid = m.group(1)
        proc, temp, vdd = re.fullmatch(r"([a-z]+)_(-?\d+)c_([\d.]+)v", cid).groups()
        vals = [float(c.strip()) for c in m.group(2).split("|")]
        if len(vals) != len(header):
            continue
        rows[(proc, float(temp), round(float(vdd), 2))] = vals
        if len(rows) == 45:
            break
    return header or [], rows


def envelope_values(path: Path) -> dict[tuple, dict[str, float]]:
    report = json.loads(path.read_text())
    out: dict[tuple, dict[str, float]] = {}
    for c in report["corners"]:
        vdd = next(iter(c["supply_v"].values()))
        key = (c["process"], float(c["temperature_c"]), round(float(vdd), 2))
        out[key] = {m["name"]: m["value"] for m in c["measurements"] if m.get("value") is not None}
    return out


def find_envelope(bench: str, env_id: str | None) -> Path | None:
    base = SIM / bench / "corners"
    if env_id:
        p = base / env_id / "klt-sim-report.json"
        return p if p.is_file() else None
    found = sorted(base.glob("*/klt-sim-report.json"))
    return found[-1] if found else None


def main() -> int:
    csv_rows = []
    summary = []
    for bench, (rowid, rec_id, env_id) in BENCHES.items():
        env_path = find_envelope(bench, env_id)
        if env_path is None:
            print(f"skip {bench}: no envelope committed", file=sys.stderr)
            continue
        cols, rec = parse_record(SIM / bench / "records" / f"{rec_id}.md")
        env = envelope_values(env_path)
        tb = json.loads((SIM / bench / "testbench" / "tb.json").read_text())
        scale = {
            n: float(e.get("scale", 1.0)) if isinstance(e, dict) else 1.0
            for n, e in (tb.get("klt_measure") or {}).items()
        }
        for i, col in enumerate(cols):
            worst = (0.0, None)
            n = 0
            for key, vals in sorted(rec.items()):
                ev = env.get(key, {}).get(col)
                if ev is None:
                    continue
                ev *= scale.get(col, 1.0)
                rv = vals[i]
                delta = ev - rv
                rel = abs(delta) / abs(rv) if rv else (0.0 if delta == 0 else float("inf"))
                cid = f"{key[0]}_{int(key[1])}c_{key[2]:.2f}v"
                csv_rows.append([bench, cid, col, f"{rv:.6g}", f"{ev:.6g}", f"{delta:.3g}", f"{rel:.3g}"])
                n += 1
                if abs(delta) >= worst[0]:
                    worst = (abs(delta), (cid, rv, ev, rel))
            summary.append((bench, col, n, worst))

    DOCS.mkdir(exist_ok=True)
    with (DOCS / "analog-envelope-agreement.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["bench", "corner", "row", "record_value", "envelope_value", "delta", "relative_delta"])
        w.writerows(csv_rows)

    md = [
        "# Analog `klt sim` envelopes vs. the committed evidence records",
        "",
        "Generated by `sim/envelope_agreement.py`; do not edit by hand. For each",
        "bench, the committed `klt sim` envelope (`sim/<bench>/corners/<id>/",
        "klt-sim-report.json`) is compared corner-by-corner with the per-corner",
        "table of the evidence record named below. Every (corner, row) pair is in",
        "`analog-envelope-agreement.csv`; this page keeps the worst case per row.",
        "",
        "| bench | row (measurement) | corners compared | worst corner | record | envelope | relative delta |",
        "|---|---|---|---|---|---|---|",
    ]
    for bench, col, n, (absd, info) in summary:
        if info is None:
            md.append(f"| `{bench}` | `{col}` | 0 | n/a | n/a | n/a | n/a |")
            continue
        cid, rv, ev, rel = info
        md.append(f"| `{bench}` | `{col}` | {n} | `{cid}` | {rv:.6g} | {ev:.6g} | {rel:.2g} |")
    md.append(FINDINGS)
    (DOCS / "analog-envelope-agreement.md").write_text("\n".join(md) + "\n")
    print(f"wrote {len(csv_rows)} comparisons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
