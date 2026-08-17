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

## Analog — not delivered (blocked, evidenced)

No GDS/OASIS exists yet for the five analog schematic blocks
(`differential_driver`, `differential_receiver`, `dplus_pullup`,
`se_receiver_dm`, `se_receiver_dp` — `design/*.sch` /
`design/netlist/*.spice`). This is a real, investigated tooling gap, not an
oversight:

- `klt gen` only runs *named* primitive generators (`mos_array`,
  `res_array`, `guard_ring`, `diff_pair`, `bjt_array`, `esd_device`,
  `bond_pad`) — matched-array-shaped device groups, not arbitrary
  full-custom circuits. Every one of these five blocks' devices is a single
  sized instance or a small handful of differently-sized instances (not a
  matched array), so the primitive generators cover, at best, a minority of
  each circuit.
- `klt gen-compose` places and wires already-generated `klt gen` blocks, but
  its own router is two-pin only (`gen_compose.py`'s own docstring: "bundle
  (>2-pin) routing is out of scope this phase"). Every one of these five
  schematics has real >2-pin nets (`VDD`/`VSS` supply rails touching many
  devices at minimum), so even a fully hand-authored `klt gen-compose`
  request cannot route them.
- There is no `klt` verb between "here is a block's netlist" and "here is
  its placed, routed layout" for a full-custom circuit at all —
  [klayout-tools#346](https://github.com/2AMLogic/klayout-tools/issues/346)
  (closed) already spiked this exact gap
  (`docs/design/netlist-driven-layout-spike.md` in that repo), citing
  `gf180-bandgap`'s bespoke, non-reusable
  `generate.py`/`netlist_model.py`/`plan.py` as the only working precedent
  for this class of block, but the spike shipped only a proposed contract
  and phase breakdown — no implementation phase has landed.

Per this issue's own "Realism / partial-completion guidance" and
`CLAUDE.md`'s rule against fabricating a result, this PR does not attempt a
hand-drawn or otherwise non-tool-verified GDS for these blocks (`klt draw`
is explicitly "no PDK awareness and no rule checking" — the wrong tool for a
layout claim, not a workaround for the primitive-generator gap above).
Friction filed:
[klayout-tools#1116](https://github.com/2AMLogic/klayout-tools/issues/1116)
— a second real-block data point on top of #346, asking for that spike's
Phase A/B (netlist ingestion digest, then the declarative plan contract) to
become actual Builder-sized follow-up issues.

## Regenerating

```bash
./scripts/setup-env.sh
source .venv/bin/activate
ln -sf "$(pwd)/scripts/openroad-docker.sh" .venv/bin/openroad   # if no native openroad

PDK=gf180mcuD klt synthesize flow/request-usb-utmi-phy-synth.json --format json
PDK=gf180mcuD klt place-and-route flow/request-usb-utmi-phy-par.json --format json
```

See `flow/README.md` for the full flow and `verification/README.md` for the
evidence-record convention `verification/records/place-and-route/` and
`verification/records/digital-drc/` follow.
