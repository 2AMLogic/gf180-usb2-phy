# flow

Synthesis and place-and-route recipes (Yosys, OpenROAD), driven through
`klt`. Pattern ported from
[`sky130-modexp`](https://github.com/2AMLogic/sky130-modexp)'s `flow/`
(digital half of issue #2's harness bootstrap, per `CLAUDE.md`), re-targeted
from sky130 to **gf180mcu** — see "Why this differs from `sky130-modexp`"
below.

## Contents

- `request-harness-counter-synth.json` — a checked-in `klt synthesize`
  request (`klt.synthesize.request/1`) that synthesizes
  `rtl/harness_counter.v` (the throwaway smoke-test vehicle described in
  `rtl/README.md`, not real PHY logic) against the gf180mcu
  `gf180mcu_fd_sc_mcu9t5v0` standard-cell library at the `tt_025C_1v80`
  corner, unconstrained (`clock_period_ns: null`).
- `request-usb-utmi-phy-synth.json` / `request-usb-utmi-phy-par.json` — the
  real PHY digital flow (issue #25): `klt synthesize` then
  `klt place-and-route`, synthesizing and routing `rtl/usb_utmi_phy.v` and
  every submodule it instantiates against gf180mcu. See "Digital
  synthesis + place-and-route" below.

## Running the harness-counter smoke synthesis

```bash
PDK=gf180mcuD klt synthesize flow/request-harness-counter-synth.json --format json
```

`PDK=gf180mcuD` (or `--pdk gf180mcuD` via `PDK_ROOT`/`klt pdk find`
resolution) selects which of the fetched gf180mcu variants
(`gf180mcuA`/`B`/`C`/`D`) to resolve the standard-cell liberty from — see
`docs/environment-setup.md` § "Digital toolchain" for how the PDK is
provisioned locally. `klt synthesize` runs Yosys (`read_verilog` →
`hierarchy` → `synth` → `dfflibmap` → `abc -liberty` → `clean` →
`stat`/`write_verilog`) and reports `instance_count`, `area_um2`, and a
per-cell-type breakdown; `timing` is always `null` (deferred to a future
OpenROAD/OpenSTA step per `klt`'s own documented contract).

Scratch output lands under `flow/.klt/synthesize/` (gitignored). Real
evidence — the raw JSON envelope, a mapped-netlist snapshot, and the Yosys
script snapshot — is captured as an append-only record under
`verification/records/synthesis-smoke/`, following the convention in
`verification/README.md`; that convention, not this directory, is where a
synthesis *claim* is substantiated.

## Why this differs from `sky130-modexp`

`sky130-modexp`'s `flow/` holds only a one-line README — its synthesis
recipe lives as an ad-hoc shell heredoc in `docs/baseline.md` rather than a
checked-in request file, because that repo's synthesis request was
generated fresh per run rather than committed. This repo commits the
request file directly (`request-harness-counter-synth.json`) so the
"synthesis recipe driven through `klt`" is a concrete, reviewable artifact
rather than prose describing how to construct one. The `pdk` block is the
one place a mechanical port from sky130 would have been silently wrong:
`cell_library` and `corner` name a gf180mcu standard-cell library
(`gf180mcu_fd_sc_mcu9t5v0`) and one of its liberty corners
(`tt_025C_1v80`), not `sky130_fd_sc_hd`/`tt_025C_1v80`.

## Digital synthesis + place-and-route (issue #25)

The real PHY digital logic — `rtl/usb_utmi_phy.v` (the top-level UTMI
wrapper) and every submodule it instantiates (`usb_nrzi_encoder`,
`usb_nrzi_decoder`, `usb_bit_stuffer`, `usb_bit_destuffer`,
`usb_sync_detector`, `usb_eop_detector`, `usb_line_state_decode` — issues
#31/#32) — synthesizes and place-and-routes to a committed, routed GDS
under `layout/digital/`, via two chained request files:

```bash
# 1. Synthesize (Yosys)
PDK=gf180mcuD klt synthesize flow/request-usb-utmi-phy-synth.json --format json

# 2. OpenROAD needs to be on $PATH -- see docs/environment-setup.md's
#    "OpenROAD" section if it isn't (this repo provisions it via the
#    pinned openroad/orfs Docker image, scripts/openroad-docker.sh).

# 3. Place and route (OpenROAD), consuming step 1's netlist_path output
PDK=gf180mcuD klt place-and-route flow/request-usb-utmi-phy-par.json --format json
```

`request-usb-utmi-phy-par.json`'s `netlist` field
(`.klt/synthesize/usb_utmi_phy_synth.v`) is step 1's own scratch output
path, resolved relative to the request file's own directory (`flow/`) —
running step 1 first is required before step 3 can find it. Both steps'
scratch output lands under `flow/.klt/` (gitignored); the committed,
evidence-backed copies of the routed GDS/DEF/as-built netlist live under
`layout/digital/`, and the measurement is recorded under
`verification/records/place-and-route/` (synthesis + P&R) and
`verification/records/digital-drc/` (the DRC leg — **not clean**, see
that record for the honestly-reported violation count and root cause).

### Power delivery (`request.power`)

`request-usb-utmi-phy-par.json` carries a `power` block, and it is what makes
the resulting layout DRC-clean. It names the `VDD`/`VSS` rails and a
three-strap standard-cell PDN, which drives `tapcell` +
`add_global_connection`/`global_connect` + `pdngen` at the end of the
floorplan stage and `filler_placement` + `global_connect` at the end of the
route stage. Without it, `klt place-and-route` writes a DEF with no
`SPECIALNETS` section at all, every cell's `VDD`/`VSS` pin belonging to no
net and every inter-cell row gap left unbridged — which is exactly the 153
`Metal1` violations the superseded DRC record reports.

The strap geometry is **not invented here**. It is transcribed from
OpenROAD-flow-scripts' own gf180 platform PDN config,
`flow/platforms/gf180/openROAD/pdn/pdn_grid_strategy_9t_6M.cfg`, read out of
the pinned `openroad/orfs` image: `Metal1` 0.900 µm followpins at 5.040 µm
pitch; `Metal4` 4.480 µm wide / 0.56 µm spacing at 44.8 µm pitch, 22.4 µm
offset; `Metal5` 4.480 µm at 89.6 µm pitch, 44.8 µm offset; and the
`Metal1`→`Metal4` via stack tuned `-max_columns 5 -ongrid {Metal2 Metal3
Metal4} -split_cuts {Metal3 0.128}`. The `Metal4`→`Metal5` pair takes klt's
default bare `add_pdn_connect`, matching that config's own second line.
Tapcell / endcap / filler masters are not in the request at all — klt
resolves them per cell library from its own ORFS-sourced tables.

`request-usb-utmi-phy-par.json`'s `floorplan.site` is
`GF018hv5v_green_sc9` (`gf180mcu_fd_sc_mcu9t5v0`'s own LEF `SITE` name,
read directly from the resolved PDK's tech LEF — this is not the
sky130-style `unithd`-shaped name); `io.layer_h`/`io.layer_v` are
`Metal3`/`Metal2` (gf180mcu's routing range for this cell library starts
at `Metal2`, not `Metal1` — see `docs/cli/place-and-route.md` in
`klayout-tools` for why). `constraints.clock_period_ns` is `83.333`
(12 MHz — `spec/usb2-device-phy.md` §3's UTMI interface clock rate, the
full-speed-only target this repo is scoped to per `CLAUDE.md`).

### What this flow does *not* produce

Tapcells, the PDN and filler cells **are** produced, via the `power` block
above. What is still absent from the routed GDS/DEF: **no metal (density)
fill**, no `DONT_USE_CELLS` exclusion, and no IO ring — this is a core-only
block-level implementation, and pad assignment is a test-chip integration
question. The curated `gf180mcu` DRC deck this repo runs has no density
rules, so a clean DRC here is not a density-clean claim; that is stated in
the DRC record rather than implied.

Also not produced here: any **post-layout, extracted-parasitic**
simulation. The multi-corner timing this flow reports is liberty plus
OpenROAD's own estimated RC, not a SPICE re-run against an extracted
netlist.

### Downstream signoff legs

DRC and LVS are separate commands run against the committed artifacts, not
part of this flow:

```bash
PDK=gf180mcuD klt drc layout/digital/usb_utmi_phy.gds \
    --deck gf180mcu --top usb_utmi_phy --format json     # -> "clean", 0 violations
PDK=gf180mcuD python3 scripts/digital_lvs.py              # -> "match", 0 mismatches
PDK=gf180mcuD python3 scripts/digital_lvs.py --negative-control
```

`layout/README.md` § "Digital" summarises both verdicts and their scope;
`verification/records/digital-drc/` and `verification/records/digital-lvs/`
hold the evidence.
