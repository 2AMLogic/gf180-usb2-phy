#!/usr/bin/env python3
"""Summarize the issue #123 RX synchronization experiment artifacts.

Reads the raw JSON written by `test_usb_rx_sync_candidate.py`
(`USB_RXSYNC_OUT_DIR`) and prints the tables quoted in the evidence
record, so every number there is reproducible from the committed
artifacts. Stdlib only; reads data, never executes it.

Usage:
    python3 verification/rx_sync_candidate_summary.py \\
        --baseline  <dir>/baseline-grid-matrix.json \\
        --candidate <dir>/candidate-grid-matrix.json \\
        [--skew <dir>/skew-injection-sweep.json] \\
        [--historical <usb-rx-clock-tolerance-matrix.json>]

Receive pass/fail is reported separately from harness success: a grid
whose harness passed can still contain any number of measured failures,
and those stay failures here.
"""

import argparse
import json
from collections import Counter, OrderedDict

CMP_KEYS = ("pass", "reason", "received_bytes", "rx_error_seen", "first_mismatch_index",
            "rx_active_seen", "rx_active_ended")


def load(path):
    """Load an artifact; columnar (`columns`/`rows`) docs get `cases`."""
    with open(path) as f:
        doc = json.load(f)
    if "rows" in doc:
        doc["cases"] = [dict(zip(doc["columns"], r)) for r in doc["rows"]]
    return doc


def grid_key(c):
    return (c["offset"], c["phase"], c["pattern"], c["post_sync_bytes"])


def summarize_grid(doc):
    cases = doc["cases"]
    n = len(cases)
    fails = [c for c in cases if not c["pass"]]
    unclaimed = [c for c in cases if c["coincident_host_edges"] > 0]
    claimed = [c for c in cases if c["coincident_host_edges"] == 0]
    print(f"## grid: {doc['design']} ({doc['grid']}, {n} cases)")
    print(f"receive pass {n - len(fails)}/{n}; measured failures {len(fails)} "
          f"({sum(not c['rx_error_seen'] for c in fails)} never raised RxError)")
    print("failure reasons:", dict(Counter(c["reason"] for c in fails)))
    print(f"cases with a host edge coincident with a DUT edge (unclaimed): {len(unclaimed)}; "
          f"excluding them: pass {sum(c['pass'] for c in claimed)}/{len(claimed)}")
    print("manufactured SE0/SE1 in any grid case:",
          sum(c["manufactured_se0_samples"] + c["manufactured_se1_samples"] > 0 for c in cases))
    phases = [p[0] for p in doc["phases"]]
    print("phases (columns):", " ".join(phases))
    table = OrderedDict()
    for c in cases:
        table.setdefault((c["offset"], c["post_sync_bytes"]), {}).setdefault(c["phase"], []).append(
            c["pass"])
    lengths = doc["lengths"]
    offsets = [o[0] for o in doc["offsets"]]
    print("| offset | " + " | ".join(f"{n} B" for n in lengths) + " |")
    print("|---|" + "---|" * len(lengths))
    for off in offsets:
        cells = []
        for nb in lengths:
            row = table[(off, nb)]
            s = ""
            for ph in phases:
                v = row[ph]
                s += "P" if all(v) else ("F" if not any(v) else "m")
            cells.append(s)
        print(f"| {off} | " + " | ".join(cells) + " |")
    print()


def compare(a, b, label_a, label_b, keyf_a=grid_key, keyf_b=grid_key):
    ia = {keyf_a(c): c for c in a}
    ib = {keyf_b(c): c for c in b}
    common = sorted(set(ia) & set(ib), key=str)
    diffs = [k for k in common if any(ia[k].get(x) != ib[k].get(x) for x in CMP_KEYS)]
    claimed = [k for k in diffs
               if not ia[k].get("coincident_host_edges") and not ib[k].get("coincident_host_edges")]
    print(f"## {label_a} vs {label_b}: {len(common)} common cases, "
          f"{len(diffs)} differ in {', '.join(CMP_KEYS)}; "
          f"{len(claimed)} of those have no host edge coincident with a DUT edge")
    for k in diffs[:20]:
        print("  ", k, {x: (ia[k].get(x), ib[k].get(x)) for x in CMP_KEYS
                        if ia[k].get(x) != ib[k].get(x)})
    print()
    return diffs


def latency_shift(base, cand):
    ib = {grid_key(c): c for c in base}
    shifts = Counter()
    for c in cand:
        b = ib.get(grid_key(c))
        if b is None or not (b["pass"] and c["pass"]):
            continue
        for k in ("rx_active_rise_edge", "first_rx_valid_edge", "rx_active_fall_edge"):
            shifts[(k, c[k] - b[k])] += 1
    print("## candidate - baseline status-edge shift over cases passing in both:")
    for (k, d), n in sorted(shifts.items()):
        print(f"   {k}: {d:+d} clocks in {n} cases")
    print()


def summarize_skew(doc):
    cases = doc["cases"]
    print(f"## skew x injection sweep ({len(cases)} cases, offset 0, "
          f"{cases[0]['post_sync_bytes']} B, all phases x patterns)")
    print("| design | skew | pass (all) | pass (excl. coincident) | cases w/ manuf. SE0 | "
          "max SE0 run | cases w/ SE1 | max SE1 run | eop_pulses!=1 | bus_reset | "
          "dropped (no RxActive) | silent corruption (RxActive, RxError low) |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    groups = OrderedDict()
    for c in cases:
        groups.setdefault((c["design"], c["skew"]), []).append(c)
    for (d, sk), cs in groups.items():
        cl = [c for c in cs if c["coincident_host_edges"] == 0]
        print(f"| {d} | {sk} | {sum(c['pass'] for c in cs)}/{len(cs)} | "
              f"{sum(c['pass'] for c in cl)}/{len(cl)} | "
              f"{sum(c['manufactured_se0_samples'] > 0 for c in cs)} | "
              f"{max(c['manufactured_se0_max_run'] for c in cs)} | "
              f"{sum(c['manufactured_se1_samples'] > 0 for c in cs)} | "
              f"{max(c['manufactured_se1_max_run'] for c in cs)} | "
              f"{sum(c['eop_pulses'] != 1 for c in cs)} | "
              f"{sum(c['bus_reset_samples'] > 0 for c in cs)} | "
              f"{sum(not c['rx_active_seen'] for c in cs)} | "
              f"{sum(c['rx_active_seen'] and not c['pass'] and not c['rx_error_seen'] for c in cs)} |")
    print("failure reasons by design:")
    for d in OrderedDict((c["design"], 1) for c in cases):
        print("  ", d, dict(Counter(c["reason"] for c in cases if c["design"] == d and not c["pass"])))
    skew_key = lambda c: (c["skew"], c["phase"], c["pattern"])  # noqa: E731
    base = [c for c in cases if c["design"] == "baseline"]
    for d in ("candidate", "candidate+inj_both"):
        compare(base, [c for c in cases if c["design"] == d], "skew baseline", f"skew {d}",
                skew_key, skew_key)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--skew")
    ap.add_argument("--historical")
    a = ap.parse_args()
    base, cand = load(a.baseline), load(a.candidate)
    summarize_grid(base)
    summarize_grid(cand)
    compare(base["cases"], cand["cases"], "baseline", "candidate")
    latency_shift(base["cases"], cand["cases"])
    if a.historical:
        hist = load(a.historical)["cases"]
        hk = lambda c: (c["offset"], f"{c['phase_eighths']}/8" if c["phase_eighths"] else  # noqa: E731
                        "0/8(coincident)", c["pattern"], c["post_sync_bytes"])
        compare(hist, base["cases"], "historical record matrix (unwrapped usb_utmi_phy)",
                "wrapper baseline", hk, grid_key)
    if a.skew:
        summarize_skew(load(a.skew))


if __name__ == "__main__":
    main()
