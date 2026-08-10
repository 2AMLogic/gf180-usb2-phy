# sim/harness — the PVT corner runner

Reproducible ngspice simulation against the gf180mcu PDK. This document covers
**how to run** the harness and **how to write a testbench**.

The *output* of a run — directory layout, record-id format, the summary record
field set, and the append-only rule — is defined by
[`sim/README.md`](../README.md), not here. That convention is authoritative;
this harness exists to produce records that conform to it.

This package is ported from the sibling
[`gf180-bandgap`](https://github.com/2AMLogic/gf180-bandgap) repository's own
`sim/harness/` (same PDK, so the environment setup applies directly) per
`CLAUDE.md`'s "Harness bootstrap" instruction. The harness machinery below
(corner sweep engine, evidence-record schema, report format, PDK resolution)
ported essentially unchanged; what did **not** port is `gf180-bandgap`'s
bandgap-specific spec rows and testbench content — this repo's PVT corners and
pass/fail bounds come from [`spec/usb2-device-phy.md`](../../spec/usb2-device-phy.md).
This repo also has not yet ported `gf180-bandgap`'s `sim/suite/` (spec-line
test suite runner), `sim/dut/` (swappable top-level DUT convention), or
`sim/device-*/` (device-characterization) patterns — those apply once
`design/` has real schematics to test; see the smoke-inverter section below
for the throwaway cell that exists today.

```
sim/
  run_corners.py            CLI entry point (stdlib python3, no venv)
  env.sh                    `source sim/env.sh` to export the same PDK to your shell
  selftest.sh               harness acceptance test (unit tests + end-to-end PVT run)
  check_records.py          evidence-record format + append-only checker
  pdk.json                  committed PDK defaults (variant, extra search roots)
  harness/                  the runner itself (this directory)
  tools/                    helper scripts (mk_dut.py)
  tests/                    harness unit tests (no PDK, no ngspice required)
  .work/                    generated ngspice decks (git-ignored, disposable)

  <experiment-slug>/        one per claim under test -- see sim/README.md
    testbench/               tb.json + netlist fragment      <- you write these
    netlist-snapshots/       frozen netlist per record       <- the harness writes these
    corners/<record-id>/     raw <corner-id>.log per PVT point
    records/<record-id>.md   append-only summary record
```

## Quick start

```bash
python3 sim/run_corners.py --check-env     # is ngspice + the PDK present?
python3 sim/run_corners.py --list          # experiments, corners, corner sets
python3 sim/run_corners.py smoke-inverter  # run the full PVT grid, mint a record
bash sim/selftest.sh                       # prove the harness works (writes nothing)
```

## Prerequisites

| Tool | Why | Install |
|---|---|---|
| `ngspice` | simulation | `brew install ngspice` / `apt-get install ngspice` |
| gf180mcu PDK | device models | `pip install volare && volare enable --pdk gf180mcu <hash>` |
| `xschem` | schematic capture (optional for simulation) | `brew install xschem` / distro package |
| python3 ≥ 3.9 | the harness | stdlib only, no packages |

See [`docs/environment-setup.md`](../../docs/environment-setup.md) → "Analog
toolchain" for what a clean machine actually needed to get this working.

The harness never hardcodes a PDK path. It resolves one, in order:

1. `GF180_PDK_PATH` — the *variant* directory, e.g. `~/.volare/gf180mcuD`
   (the one containing `libs.tech/`).
2. `PDK_ROOT` (+ `PDK`, default `gf180mcuD`) — the open_pdks / OpenLane convention.
3. `sim/pdk.local.json` — machine-local, git-ignored.
4. `sim/pdk.json` — committed defaults.
5. Built-in search roots: `~/.volare`, `~/.ciel`, `/usr/share/pdk`,
   `/usr/local/share/pdk`, `~/share/pdk`, `/opt/pdk`.

If nothing is found the runner exits 3 with install instructions rather than
producing a misleading result. `sim/run_corners.py --print-env` emits the
resolved paths as shell exports; `source sim/env.sh` applies them so that an
interactive ngspice or xschem session uses the identical PDK.

## The PVT grid

`spec/usb2-device-phy.md` §8.1 fixes this repo's mandated PVT matrix at **45
corners**: the 5-corner gf180mcu process set (`tt`, `ss`, `ff`, `fs`, `sf`) ×
3 temperatures × 3 supply points. That is exactly the harness's `mos` corner
set (the default `CORNER_SET` in `harness/corners.py`) — use it unless a
testbench specifically needs the resistor/BJT-skew corners below.

- **Temperature**: −40, 27, 125 °C
- **Voltage**: nominal ±10 % (3.3 V flavor → 2.97 / 3.3 / 3.63 V)
- **Process**: see below

gf180mcu has no single global corner switch — each device family carries its
own `.lib` section in `sm141064.ngspice`, so a named corner here is a bundle of
six sections (MOS, resistor, BJT, diode, MOS cap, MIM cap):

| Corner | Meaning |
|---|---|
| `tt` | everything typical |
| `ff` / `ss` | every device family fast / slow |
| `fs` / `sf` | fast-N/slow-P and slow-N/fast-P, passives typical |
| `res_ff` / `res_ss` | resistor sheet rho skewed, rest typical |
| `bjt_ff` / `bjt_ss` | BJT skewed, rest typical |

Corner sets: `tt` (1, debugging only), `mos` (5 — **this repo's spec-mandated
default**, matching `spec/usb2-device-phy.md` §8.1's 45-corner matrix), `full`
(9 — adds the resistor/BJT-skew corners; only needed for a circuit whose
accuracy rides on passives, which is not this repo's default case the way it
was `gf180-bandgap`'s).

Each point becomes one `<corner-id>` — `<process>_<temp>c_<supply>v`, the
naming `sim/README.md` ratifies — and one raw log under
`corners/<record-id>/`.

Override any axis from the command line:

```bash
python3 sim/run_corners.py smoke-inverter --corner-set full -j 8
python3 sim/run_corners.py smoke-inverter --corners tt res_ss --temps -40 125
python3 sim/run_corners.py smoke-inverter --supply 5.0 --supply-tol 0.10   # a 5 V flavor
```

**Subsets need a reason.** `sim/README.md` requires every record's *Corner
matrix run* field to be the full mandated matrix "unless the record states why
a subset was used". The runner enforces that: if the grid you asked for is
missing a mandated temperature, a mandated supply, or has fewer than three
process corners, it refuses to write a record unless you supply
`--subset-reason '<why>'` (which is copied verbatim into the record), or pass
`--no-write` because you are only debugging.

```bash
# debugging: runs, records nothing
python3 sim/run_corners.py smoke-inverter --corners tt --temps 27 --supply-tol 0 --no-write

# a deliberate, justified subset: runs and records, with the reason on the record
python3 sim/run_corners.py smoke-inverter --corners tt --temps 27 \
    --subset-reason "nominal-only debugging sweep; not a spec claim"
```

## Writing a testbench

Create `sim/<experiment-slug>/testbench/` with a manifest and a netlist
fragment. The slug is the experiment directory from `sim/README.md`: one per
distinct claim under test, kebab-case.

`tb.json`:

```json
{
  "name": "my-experiment",
  "description": "one line, shows up in --list and in the record",
  "claim": "spec/usb2-device-phy.md#driver-characteristics",
  "netlist": "my_tb.spice",
  "nominal_supply_v": 3.3,
  "supply_tolerance": 0.1,
  "temperatures_c": [-40, 27, 125],
  "corners": ["mos"],
  "analyses": ["op"],
  "params": {"iload": "10u"},
  "options": ["reltol=1e-5"],
  "measure": {"vref": "v(vref)", "iq_ua": "-i(vsup)*1e6"},
  "checks": {"vref": {"min": 1.15, "max": 1.25, "max_spread_pct": 2.0}}
}
```

`claim` is the default for the record's **Claim** field — the ratified spec
line this experiment substantiates. `--claim` overrides it per run.

`dut` (optional) names the **device under test**: a second fragment holding
nothing but subcircuit definitions, `.include`d ahead of the testbench. That
indirection is what lets several testbenches share one netlist, and what lets
the *same* testbench re-run unedited against a different one — see
`sim/tools/mk_dut.py`'s docstring for how to generate one from an xschem
export once `design/` has schematics. No testbench in this repo uses `dut`
yet; `smoke-inverter`'s netlist below is self-contained instead.

`subset_reason` (optional) pre-declares why this experiment's grid is a
deliberate subset of the mandated PVT matrix — for a testbench that sweeps an
axis internally, say. `--subset-reason` still overrides it, and either way the
text is copied verbatim onto the record, which is where `sim/README.md` wants
the justification to live.

The netlist is a **fragment**, not a complete deck. It must not contain
`.include`, `.lib`, `.temp`, `.control`, `.endc` or `.end` — the harness owns
all of those, which is what lets one netlist sweep the whole grid unedited.
The loader rejects fragments that break this rule instead of silently pinning
every corner to 27 °C. The harness hands the fragment:

| Parameter | Value |
|---|---|
| `vdd_val` | supply for this PVT point |
| `vdd_nom` | nominal supply, for ratio measurements |
| `temp_c` | temperature for this PVT point (also applied via `.temp`) |

Each `measure` entry becomes `let m_<name> = <expr>` followed by `print` inside
the control block, so the expression must reduce to a **scalar**: fine for
`op`; for `tran`/`ac` reduce with `maximum()`, `mean()`, `v(out)[0]`, etc.

`checks` are evaluated after the sweep:

| Key | Applies to | Meaning |
|---|---|---|
| `min` / `max` | every point | hard limit; failure names the offending corner-id |
| `max_spread_pct` | the grid | `(max−min)/\|mean\|` must stay under the limit |
| `min_spread_pct` | the grid | must *exceed* it — asserts the sweep really moved |

`min_spread_pct` is a harness-integrity check: if `.temp` or a `.lib` section
silently failed to apply, a strongly PVT-sensitive measurement would come back
flat, and this catches that instead of reporting a suspiciously perfect result.

## What a run writes

One run mints one `<record-id>` (`<YYYYMMDD>-<HHMMSS>-<short-git-sha>`) and
writes, under `sim/<experiment-slug>/`:

| Path | Contents |
|---|---|
| `records/<record-id>.md` | the append-only summary record (the nine fields from `sim/README.md`, plus an Environment section with PDK / ngspice / harness / git provenance and the per-corner model sections) |
| `netlist-snapshots/<record-id>.spice` | verbatim frozen copy of the testbench fragment, with its sha256 |
| `corners/<record-id>/<corner-id>.log` | raw ngspice output, one file per PVT point |

Nothing is ever overwritten: the runner refuses to write over an existing
record or snapshot, and mints a later record-id if one is somehow already
taken. Corrections and re-runs get a new record-id and reference the prior one
with `--supersedes <record-id>`. Do not edit or delete anything under
`records/`, `netlist-snapshots/` or `corners/` — see the append-only rule in
`sim/README.md`.

A run taken against a dirty working tree says so in the record's **Netlist
provenance** field and is not citable as a clean-tree result.

Exit codes: `0` pass · `1` a check failed · `2` a simulation failed or did not
converge · `3` environment problem (no ngspice, no PDK, bad manifest,
unjustified PVT subset).

Generated decks land in `sim/.work/<experiment-slug>/<record-id>/` and are
git-ignored, so a failing corner can be reproduced by hand with
`ngspice -b sim/.work/<slug>/<record-id>/<corner-id>.spice`.

## sim/smoke-inverter/ — the harness acceptance test

`sim/smoke-inverter/` is throwaway smoke-test infrastructure to prove the
harness works end-to-end, **not** a real PHY sub-block — `design/` has no
schematics yet, so there is no driver or receiver to test. It exercises a
single minimum-size CMOS inverter (`nfet_03v3`/`pfet_03v3`) in three static
states: gate grounded (VOH), gate at VDD (VOL), and self-biased gate-tied-to-
drain (the switching threshold VM). VM is the PVT probe: it tracks the
NMOS/PMOS strength ratio, so a flat VM across the grid would mean `.temp` /
the corner `.lib` sections never took effect.

Run it with `bash sim/selftest.sh`, or directly with
`python3 sim/run_corners.py smoke-inverter`.

Once `design/` has a real driver or receiver schematic, its testbench belongs
in its own `sim/<experiment-slug>/` directory (per `sim/README.md`) that
substantiates an actual `spec/usb2-device-phy.md` row — `smoke-inverter`
stays as the harness's own acceptance check and is not meant to grow into
that testbench.

## xschem

Once `design/xschemrc` exists and resolves the PDK the same way the harness
does (see `gf180-bandgap`'s `design/xschemrc` for the pattern to port), a
schematic session looks like:

```bash
source sim/env.sh
cd design && xschem
```

Schematic netlists would be written to `design/netlist/`. To simulate a
schematic, strip it to a fragment (or netlist a testbench schematic without
its `.control`/`.end` block) and point a `tb.json` at it — the corner runner
is agnostic about whether the fragment was typed or generated.

Note: xschem itself is not required to run any of the above; the corner
runner only needs ngspice and the PDK.
