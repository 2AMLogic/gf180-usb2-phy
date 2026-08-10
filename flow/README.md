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

## Running it

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

## Place-and-route (not yet exercised here)

`klt place-and-route` exists (`klt --help`) but is out of scope for this
bootstrap issue — see the parent epic (#2) and the analog sub-issue (#6)
for the maturity-ladder sequencing. `openroad` provisioning notes will land
in `docs/environment-setup.md` when that rung is taken up.
