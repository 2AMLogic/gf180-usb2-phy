#!/usr/bin/env python3
"""The `klt sim` Monte Carlo request shape both receiver MC campaigns share.

`sim/diff-receiver-mc/` and `sim/se-receiver-mc/` express their statistical
rows (spec/decisions/0007-analog-statistical-rows.md) as `monte_carlo` `klt
sim` requests. The two campaigns test different spec rows against different
testbenches, but the *request* -- the corner matrix, the measurement mapping,
the `monte_carlo` block -- and the *deck layout* around the testbench fragment
are identical for both, so one implementation of each lives here.

Commit `b135f85` (closing #322) first de-duplicated `assemble_deck()` by
extracting it into the differential builder and having the single-ended one
path-load that script with `importlib`. This module is the same single
implementation with its home corrected: `sim/harness/` is the package both
builders already import (`harness.testbench`, `harness.pdk`), so the
dependency is experiment -> library rather than experiment -> experiment, and
a hyphenated directory no longer has to be reached by file path.

What stays per-campaign, deliberately: each builder's own `inject_offset()`,
`build_deck()`, `VARIANTS` and `DEGRADED_OFFSET_V`. Those differ on purpose
(0.25 V differential vs 0.9 V single-ended; a VCVS D+ leg vs a single input
node) and must not be unified here.

These builders only WRITE requests; nothing in this module dispatches or runs
ngspice.
"""
from __future__ import annotations

from pathlib import Path

from . import corners as corners_mod
from . import klt_backend

VARY = "mismatch"
DEFAULT_N = 100
DEFAULT_SEED = 20261017
DEFAULT_TIMEOUT_S = 300


def strip_end(text: str) -> str:
    """Drop top-level `.end` lines so the text can be inlined."""
    return "\n".join(l for l in text.splitlines() if l.strip().lower() != ".end")


def assemble_deck(header: str, tb, pdk, sw_stat_mismatch: int, fragment: str) -> str:
    """Lay out the deck both Monte Carlo campaigns share.

    `header` is the generated-by comment line and `fragment` the already
    prepared (stripped, offset-injected) testbench fragment; everything in
    between -- the options, the params, the inlined PDK `design.ngspice`, the
    `sw_stat_mismatch` override and the inlined DUT -- is identical for the
    differential and single-ended campaigns, which is why it lives here and
    both `sim/diff-receiver-mc/build_requests.py` and
    `sim/se-receiver-mc/build_requests.py` call this rather than copying it.
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


def build_request(tb, pdk, manifest: dict, n: int, seed: int,
                  timeout_s: int = DEFAULT_TIMEOUT_S) -> dict:
    cl = corners_mod.resolve_corners(list(tb.corners))
    supplies = corners_mod.supply_points(tb.nominal_supply_v, tb.supply_tolerance)
    process = [{"name": c.name, "sections": list(c.sections)} for c in cl]
    analysis = tb.analyses[0].split(None, 1)
    checks = manifest.get("checks", {})
    # One implementation of the `klt_measure` entry -> `measurements[]` mapping,
    # shared with the PVT-corner path. It carries the `limits` division by
    # `scale` that this campaign needs: `klt sim` reports the raw `.meas` value,
    # so unscaled, the ratified +/-200 mV bound would be graded against volts
    # (commit 3a6e489, and the regraded 2026-11-05 campaign in README.md).
    measurements = [
        klt_backend.measurement(name, entry, checks.get(name))
        for name, entry in manifest["klt_measure"].items()
    ]
    return {
        "netlist": "body.spice",
        "engine": "ngspice",
        "models": {"pdk": pdk.variant, "lib": klt_backend.MODELS_LIB},
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
