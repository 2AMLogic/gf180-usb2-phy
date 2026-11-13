#!/usr/bin/env python3
"""Emit `klt sim` Monte Carlo requests for the differential-receiver rows.

Statistical row classified in spec/decisions/0007-analog-statistical-rows.md:
the §4 differential input sensitivity (|D+ - D-| > 200 mV over a 0.8-2.5 V
common-mode range) is decided by MOS-pair mismatch, so the 45-corner matrix
alone cannot validate it. This script expresses the Monte Carlo campaign as
`klt sim` requests (`monte_carlo`, N samples per corner) that
`KLT_SIM_BACKEND=batch` sends to the Spot fleet. It only WRITES requests; it
never dispatches and never runs ngspice.

Two variants of the same request, differing only in the deck's mismatch switch:

* ``mismatch`` -- ``sw_stat_mismatch = 1``: the measurement campaign.
* ``control``  -- ``sw_stat_mismatch = 0``: the deterministic negative control.
  gf180mcu draws mismatch from ngspice's own RNG, so the control klt documents
  for such decks is the deck's own switch off; every sigma must be exactly 0.
* ``degraded`` -- ``sw_stat_mismatch = 1`` plus a series DC offset of
  ``DEGRADED_OFFSET_V`` in the D+ leg of every receiver: the seeded known-bad
  variant `klt yield-samples --negative-control` needs. ``control`` is better
  than nominal, so its yield cannot degrade; this one pushes the input-referred
  threshold outside the ratified +/-200 mV limit, so a detector that works must
  see the yield fall. The limits are not touched. ``degraded`` (+offset) breaks
  the threshold and ``lo_*`` rows; the three ``hi_*`` rows (output high at
  +200 mV) stay in limits for it, so ``degraded_neg`` (-offset) is the known-bad
  variant for those.

Process corners are the harness's five MOS corners crossed with the §8.1
temperature and supply axes (the same 45 points as
``sim/diff-receiver-sensitivity``), so the MC results are combined with, not
instead of, the process corners.

    python3 sim/diff-receiver-mc/build_requests.py WORKDIR [--n N] [--seed S]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
REPO = SIM.parent
sys.path.insert(0, str(SIM))

from harness import corners as corners_mod  # noqa: E402
from harness import testbench as tb_mod  # noqa: E402
from harness.pdk import find_pdk  # noqa: E402

SOURCE_TB = SIM / "diff-receiver-sensitivity"
MODELS_LIB = "libs.tech/ngspice/sm141064.ngspice"
VARY = "mismatch"
DEFAULT_N = 100
DEFAULT_SEED = 20261017
DEFAULT_TIMEOUT_S = 300
# variant -> (sw_stat_mismatch, series offset in the D+ leg, volts)
DEGRADED_OFFSET_V = 0.25
VARIANTS = {
    "mismatch": (1, 0.0),
    "control": (0, 0.0),
    "degraded": (1, DEGRADED_OFFSET_V),
    "degraded_neg": (1, -DEGRADED_OFFSET_V),
}


def strip_end(text: str) -> str:
    """Drop top-level `.end` lines so the text can be inlined."""
    return "\n".join(l for l in text.splitlines() if l.strip().lower() != ".end")


def inject_offset(fragment: str, offset_v: float) -> str:
    """Insert a series DC source into each receiver's D+ leg (edp<k> VCVS)."""
    out, n = [], 0
    for line in fragment.splitlines():
        m = re.match(r"^(edp(\d+))\s+DP\d+\s+(CM\d+)\s+(.*)$", line, re.IGNORECASE)
        if m:
            name, k, cm, rest = m.groups()
            out.append(f"{name} DPI{k} {cm} {rest}")
            out.append(f"vos{k} DP{k} DPI{k} dc {offset_v!r}")
            n += 1
        else:
            out.append(line)
    if n == 0:
        raise SystemExit("inject_offset: no edp<k> D+ source found in the testbench fragment")
    return "\n".join(out)


def assemble_deck(header: str, tb, pdk, sw_stat_mismatch: int, fragment: str) -> str:
    """Lay out the deck both Monte Carlo campaigns share.

    `header` is the generated-by comment line and `fragment` the already
    prepared (stripped, offset-injected) testbench fragment; everything in
    between -- the options, the params, the inlined PDK `design.ngspice`, the
    `sw_stat_mismatch` override and the inlined DUT -- is identical for the
    differential and single-ended campaigns, which is why it lives here and
    `sim/se-receiver-mc/build_requests.py` calls this rather than copying it.
    """
    design = Path(pdk.design_include).read_text()
    return "\n".join([
        header,
        ".options wnflag=1",
        f".param vdd_nom={tb.nominal_supply_v!r}",
        f".param vdd_val={tb.nominal_supply_v!r}",
        ".param temp_c=27.0",
        "* ---- begin inlined design.ngspice (PDK) ----",
        strip_end(design).rstrip(),
        "* ---- end inlined design.ngspice ----",
        # after design.ngspice, which defaults it to 0.
        f".param sw_stat_mismatch = {sw_stat_mismatch}",
        "* ---- begin inlined DUT ----",
        strip_end(Path(tb.dut).read_text()).rstrip(),
        "* ---- end inlined DUT ----",
        "* ---- begin testbench fragment ----",
        fragment,
        "* ---- end testbench fragment ----",
        "",
    ])


def build_deck(tb, pdk, sw_stat_mismatch: int, offset_v: float = 0.0) -> str:
    """Self-contained deck: the fleet stages only the request's netlist."""
    fragment = strip_end(Path(tb.netlist).read_text()).rstrip()
    if offset_v:
        fragment = inject_offset(fragment, offset_v)
    return assemble_deck(
        "* diff-receiver-mc -- GENERATED by sim/diff-receiver-mc/build_requests.py, do not edit",
        tb, pdk, sw_stat_mismatch, fragment,
    )


def build_request(tb, pdk, manifest: dict, n: int, seed: int,
                  timeout_s: int = DEFAULT_TIMEOUT_S) -> dict:
    cl = corners_mod.resolve_corners(list(tb.corners))
    supplies = corners_mod.supply_points(tb.nominal_supply_v, tb.supply_tolerance)
    process = [{"name": c.name, "sections": list(c.sections)} for c in cl]
    analysis = tb.analyses[0].split(None, 1)
    checks = manifest["checks"]
    measurements = []
    for name, entry in manifest["klt_measure"].items():
        m = {"name": name, "spice": entry["spice"]}
        if "scale" in entry:
            m["scale"] = entry["scale"]
        # `klt sim` reports the raw `.meas` value and does not apply `scale`, so the
        # ratified limits (in the check's unit, e.g. mV) are divided by it here, as
        # sim/harness/klt_backend.py does; unscaled, +/-200 would be compared with volts.
        k_scale = float(entry.get("scale", 1.0))
        limits = {k: checks[name][k] / k_scale for k in ("min", "max") if k in checks.get(name, {})}
        if limits:
            m["limits"] = limits
        measurements.append(m)
    return {
        "netlist": "body.spice",
        "engine": "ngspice",
        "models": {"pdk": pdk.variant, "lib": MODELS_LIB},
        "corners": {
            "process": process,
            "supply_v": {manifest.get("klt_supply_source", "vsup"): supplies},
            "temperature_c": list(tb.temperatures_c),
        },
        "analysis": {"kind": analysis[0], "args": analysis[1] if len(analysis) > 1 else ""},
        "measurements": measurements,
        "monte_carlo": {"n": n, "seed": seed, "vary": VARY},
        "options": {"timeout_s": timeout_s, "keep_artifacts": False},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("workdir", type=Path)
    ap.add_argument("--n", type=int, default=DEFAULT_N, help="samples per corner point")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--timeout-s", type=int, default=DEFAULT_TIMEOUT_S,
                    help="options.timeout_s per unit (size from a measured fleet pilot)")
    ap.add_argument("--variant", choices=sorted(VARIANTS), action="append",
                    help="write only this variant (repeatable); default both")
    args = ap.parse_args(argv)

    tb = tb_mod.load(SOURCE_TB)
    pdk = find_pdk()
    manifest = json.loads((SOURCE_TB / "testbench" / "tb.json").read_text())
    for variant, (switch, offset_v) in VARIANTS.items():
        if args.variant and variant not in args.variant:
            continue
        d = args.workdir / variant
        d.mkdir(parents=True, exist_ok=True)
        (d / "body.spice").write_text(build_deck(tb, pdk, switch, offset_v))
        (d / "request.json").write_text(
            json.dumps(build_request(tb, pdk, manifest, args.n, args.seed, args.timeout_s), indent=2) + "\n"
        )
        print(f"wrote {d}/request.json (sw_stat_mismatch={switch}, offset={offset_v} V, n={args.n}, seed={args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
