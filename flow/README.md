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

Per `klt place-and-route`'s own documented v1 scope, the routed GDS/DEF
this flow produces has **no tapcell insertion, no power-grid (PDN)
generation, no metal fill, no filler-cell insertion**, and no
`DONT_USE_CELLS` exclusion — core-only floorplanning, no IO ring. This is
exactly why the committed DRC record for this layout
(`verification/records/digital-drc/`) is not clean: real (non-abutted, at
40% utilization) gaps between adjacent same-row standard-cell instances
leave each cell's own `Metal1` power-rail edge exposed with no filler cell
bridging it, a genuine (not fabricated, not a `klt drc` engine false
positive — see that record and
[klayout-tools#1028](https://github.com/2AMLogic/klayout-tools/issues/1028))
DRC violation. LVS is not attempted by this issue either — see the
place-and-route record's "Coverage gaps" for why; both DRC-clean and
LVS-clean signoff are separate T1 checklist items (#25's own "Related"
section) this layout unblocks rather than completes.
