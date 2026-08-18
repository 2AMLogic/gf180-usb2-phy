# layout

GDS/OASIS and DRC/LVS evidence for this PHY. Two halves, tracked separately
because they landed at very different maturity (issue #25, T1 checklist item
2).

## Digital — `layout/digital/` (delivered)

`usb_utmi_phy.gds` / `usb_utmi_phy.def` / `usb_utmi_phy_routed.v` — the real
PHY digital logic (`rtl/usb_utmi_phy.v` and every submodule it instantiates:
`usb_nrzi_encoder`, `usb_nrzi_decoder`, `usb_bit_stuffer`,
`usb_bit_destuffer`, `usb_sync_detector`, `usb_eop_detector`,
`usb_line_state_decode`), synthesized (`klt synthesize`, Yosys) and
place-and-routed (`klt place-and-route`, OpenROAD) against the gf180mcu
`gf180mcu_fd_sc_mcu9t5v0` standard-cell library. Reproducible from a
committed, real request-file flow — see `flow/README.md`'s "Digital
synthesis + place-and-route" section for the exact commands, and
`verification/records/place-and-route/` for the measurement (342 standard
cells, 0 setup/hold/antenna violations at the 12 MHz spec clock rate, ~68 MHz
`fmax`).

**Not DRC-clean, not LVS-checked.** `verification/records/digital-drc/`
records a real (non-fabricated) DRC run against this exact GDS: 153
violations, all `Metal1` space/width violations at standard-cell row gaps,
root-caused to `klt place-and-route`'s v1 scope having no filler-cell /
power-rail-stitching stage (that command's own docs name this as deliberate
"Out of scope," not a bug — see that record for the full verification
chain, including cross-checking against
[klayout-tools#1028](https://github.com/2AMLogic/klayout-tools/issues/1028)).
LVS is not attempted at all by this issue. Both DRC-clean and LVS-clean
digital signoff are separate T1 checklist items (issue #25's own "Related"
section names items 3 and 4) this layout unblocks, not something issue #25
itself completes.

## Analog — attempted against klt's layout-plan path, **not delivered**

No GDS/OASIS is committed for the five analog blocks
(`differential_driver`, `differential_receiver`, `dplus_pullup`,
`se_receiver_dm`, `se_receiver_dp` — `design/*.sch` /
`design/netlist/*.spice`). This is a measured tooling result, not an untried
assumption: the attempt is committed and re-runnable, and its raw output is
recorded under `verification/records/analog-layout/`.

### What was attempted

klayout-tools now ships the netlist-driven layout-plan compiler/executor that
the earlier revision of this file recorded as missing
([klayout-tools#1116](https://github.com/2AMLogic/klayout-tools/issues/1116),
closed): a plan (`klt.layout_plan.request/1`, `docs/cli/layout-plan.md`)
declares how a netlist's devices group onto `klt gen` generators, and Phase C
(`klayout_tools.layout_plan_execute`, klayout-tools PR #1158 + #1161)
generates, places, and routes them through `klt gen-compose`. This repo's klt
pin was moved forward to `b3e284f` specifically to consume it (see
`docs/environment-setup.md`).

`layout/analog/plans/*.json` are the resulting committed plans — one per
block, one `device_groups[]` entry per netlist device (`mos_array` with
`rows`/`cols` 1 and `dummy` 0 for each MOS, `res_array` with `num` 1 and
`dummy` 0 for each poly resistor), every group in a single `rows[]` row.
`scripts/gen_analog_layout.py` executes them and runs `klt drc` on each
result. Nothing here is hand-drawn: `klt draw` remains the wrong tool for a
layout claim (its own docs: "no PDK awareness and no rule checking").

### What actually happened

| Block | Outcome |
|---|---|
| `differential_receiver` | 11 device groups placed, **DRC-clean** (0 violations, curated `gf180mcu` deck), **0 of 8 nets routed** |
| `se_receiver_dm` | 13 device groups placed, **DRC-clean**, **0 of 9 nets routed** |
| `se_receiver_dp` | 13 device groups placed, **DRC-clean**, **0 of 9 nets routed** |
| `differential_driver` | **cannot be ingested** — its series-termination resistors are `rm1` (metal-1) devices, which klt's curated `gf180mcu` deck does not know |
| `dplus_pullup` | **cannot be ingested** — its pull-up switches carry `nf=10`, which klt's subckt-call → plain-element conversion refuses to represent |

A block of placed devices with none of its nets wired is not a layout. It is
not committed as one, and no analog GDS is committed under `layout/` — per
`CLAUDE.md`'s rule against making a claim the evidence does not support.
Re-run `scripts/gen_analog_layout.py` (below) to reproduce the artifacts
under `layout/analog/out/` (gitignored) for inspection; the same artifacts
are frozen in the evidence record.

### Why nothing routed — root causes, not guesses

Every failure is reported by klt itself in the response's
`nets[].legs[].reason`; the frozen JSON responses are in the evidence
record's `artifacts/`. Four distinct classes, none of them a plan-authoring
mistake:

1. **A same-facing port pair cannot be connected — including a plain CMOS
   inverter.** Every `mos_array` block exposes `U0_S` on its left edge and
   `U0_D` on its right, with no orientation/mirror field anywhere in the plan
   or `gen-compose` contract. A two-block plan (one nfet, one pfet) routes
   the shared *gate* net and fails the shared *drain* net, because the route
   would have to re-enter one of its own endpoint blocks. Both receiver
   blocks' output stages are exactly that inverter.
2. **No obstacle avoidance.** Any net whose endpoints are not immediate
   neighbours fails with "crosses N µm through unrelated block X's bbox …
   the route is not point-to-point between only the two connected blocks".
   Sweeping placement (1/2/4/6/13 groups per row × 2/10/20/30 µm spacing)
   never moved the routed-net count off 0 — a real netlist is not a
   Hamiltonian path over its devices.
3. **Single drawing layer, so `VDD`/`VSS`/bias buses short.** A net touching
   several blocks fails with "bussing this net across the block would draw a
   silent short to that pad; route to a `layer_role` with a metal2/via stack
   instead" — and no such two-layer role exists in `gen-compose` today.
4. **One failed leg fails the whole net**, discarding the geometry of legs
   that were individually routable.

Two further gaps surfaced in the same exercise, and are why the committed
plans look the way they do:

- **`rows[]` stacking has no inter-row margin.** Multi-row placement puts
  vertically adjacent groups at 0.00 µm and only *warns* that this is closer
  than the blocks' own declared `drc_hints.min_spacing_um`. The committed
  plans therefore use a single row — which is also why the placement DRC
  comes back clean.
- **`diff_pair`'s netlist-derived sizing ignores `params.splits`**, drawing
  each matched device `splits ×` (default 2×) its schematic width, with no
  warning. That is why the plans use one `mos_array` group per device rather
  than grouping the genuinely matched pairs (input pair, load pair) into
  `diff_pair` groups, which is what a hand layout would do.

### Friction filed

Per `CLAUDE.md`'s friction protocol, each gap is filed generically against
the tool, not this design:

- [klayout-tools#1163](https://github.com/2AMLogic/klayout-tools/issues/1163)
  — `layout_plan`'s `netlist` block silently drops `device_map`, so a netlist
  with a device outside the curated deck cannot be planned at all (the
  `differential_driver` blocker); `device_map` itself assumes a 4-terminal
  MOS shape, so a 2-terminal unknown subcircuit has no escape hatch either.
- [klayout-tools#1164](https://github.com/2AMLogic/klayout-tools/issues/1164)
  — Phase C routes 0/N nets on a real full-custom block: same-facing ports,
  no obstacle avoidance, single-layer buses, all-or-nothing legs, plus the
  zero inter-row margin above.
- [klayout-tools#1165](https://github.com/2AMLogic/klayout-tools/issues/1165)
  — `diff_pair` netlist-derived sizing ignores `params.splits`.

The `dplus_pullup` blocker (`nf=10`) is a deliberate, documented refusal in
klt's subckt-call conversion, whose own error text prescribes the fix —
"flatten it in the schematic netlist (one device per drawn gate)". Flattening
a 10-finger device in `design/dplus_pullup.sch` would change a design source
to suit a tool, and the simulation evidence under `sim/` was taken against
the current netlist, so it is not done here; it belongs to whoever next
revisits that schematic, with a decision record.

### What would have to be true to deliver analog layout

Either klayout-tools#1164's routing gaps close (orientation control alone
makes the inverter case routable; obstacle avoidance and a two-layer bus role
make the rest reachable), **or** this repo grows a bespoke block-specific
layout generator in the shape of
[`gf180-bandgap`](https://github.com/2AMLogic/gf180-bandgap)'s
`generate.py`/`plan.py` — a whole layout engine, far outside this issue, and
exactly the duplication the friction protocol exists to avoid. The first is
the right bet; this record exists so that when it lands, re-measuring is one
command rather than a re-derivation.

## Regenerating

Both halves need `scripts/setup-env.sh`'s environment (venv + pinned `klt` +
gf180mcu PDK) — see `docs/environment-setup.md`.

```bash
./scripts/setup-env.sh
source .venv/bin/activate

# --- digital: synthesis -> place-and-route -> routed GDS (layout/digital/)
ln -sf "$(pwd)/scripts/openroad-docker.sh" .venv/bin/openroad   # if no native openroad
PDK=gf180mcuD klt synthesize flow/request-usb-utmi-phy-synth.json --format json
PDK=gf180mcuD klt place-and-route flow/request-usb-utmi-phy-par.json --format json

# --- analog: execute the committed layout plans, then DRC each result
PDK_ROOT=$HOME/.volare python3 scripts/gen_analog_layout.py            # text report
PDK_ROOT=$HOME/.volare python3 scripts/gen_analog_layout.py --format json
```

`scripts/gen_analog_layout.py` writes each block's GDS, its raw Phase C
response JSON, and a combined `analog-layout-report.json` under
`layout/analog/out/` (gitignored scratch), and prints one verdict line per
block. Its exit code is about *the run*, never about the quality of the
layout: `0` means every plan executed and every blocked block was probed,
`1` means the run itself failed (no klt, no PDK, unexpected exception). Read
the report for the verdict — as of this writing it ends `analog layout NOT
delivered`.

It also probes the two blocks that have no committed plan, so their ingestion
errors are re-measured live rather than quoted from prose. If either ever
ingests, the script says so explicitly (`status:
ingest-unexpectedly-succeeded`) and tells you to author its plan.

See `flow/README.md` for the digital flow's full detail and
`verification/README.md` for the evidence-record convention that
`verification/records/place-and-route/`, `verification/records/digital-drc/`,
and `verification/records/analog-layout/` all follow.
