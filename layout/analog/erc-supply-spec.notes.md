# `klt erc` analog supply specs — field-by-field rationale

The committed specs are `layout/analog/erc-supply-spec-<block>.json`, one per
stream under `layout/analog/*.gds`. They are the T1 item **11.analog** (power
delivery, structural) artifact for this block's analog partition (issue #248);
the digital partition's counterpart is `layout/digital/erc-supply-spec.json`,
which carries its own rationale inline in a `_comment`.

This file carries the analog rationale instead of five copies of a long
`_comment`. Each spec's own `_comment` is the short form — the run command,
the supply names, and the one-sentence derivation of its substrate assertion —
and that short form travels with the spec's content hash, which the evidence
record and the signoff manifest both pin.

Harness: `scripts/analog_erc.py`. It derives every `well_boxes` list from the
GDS, **refuses to run if a committed spec no longer matches that derivation**,
runs `klt erc` per stream, runs a deliberately-wrong control per stream, and
counts the tap wiring the ERC model cannot see. Reproduce with:

```bash
./scripts/setup-env.sh                       # the pinned klt + PDK
PDK=gf180mcuD .venv/bin/python scripts/analog_erc.py --klt .venv/bin/klt
```

Frozen evidence: `verification/records/analog-erc/`.

## Why one spec per stream

Two things differ per stream and neither factors out.

- **The supply names differ.** `differential_driver`, `differential_receiver`,
  `se_receiver_dp` and `se_receiver_dm` run off `VDD`/`VSS`. `dplus_pullup`
  runs off `VPU_REG`/`VSS` and draws no `VDD` label anywhere — a shared spec
  declaring `VDD` would resolve zero labelled islands on that stream and
  report `erc.unconnected_net`, which would be a spec artifact and not a
  layout defect. The harness reads each stream's pair from
  `layout/analog/provenance.json`'s own `body_tie_nets`, so `VPU_REG` needs
  no special case anywhere.
- **The substrate assertion is per-stream geometry** — see
  "The substrate tie" below.

A single spec was tried first and rejected for the first reason alone. The
sibling precedent for per-stream naming is `gf180-trng`'s
`layout/analog/erc-supply-spec-<block>.json`.

## `stackup`

| entry | layer | why |
|---|---|---|
| `poly2` | `30/0`, `role: "gate"`, `active_layer: "22/0"` | `klt erc`'s own contract: `stackup[0]` must be the gate role. `active_layer` (Comp `22/0`) makes the gate denominator `poly ∩ diff` instead of raw poly area, which keeps the salicide-blocked poly-resistor bodies — drawn on this same `30/0` layer — out of `gates[]` (`docs/cli/erc.md`, "Gate area"). All five streams draw such bodies (`SAB` 49/0 + `RES_MK` 110/5, 1–6 per stream). |
| `Metal1` | `34/0`, `label_layer: "34/10"` | The only layer any of these streams puts text on, verified from each stream's own inventory rather than assumed: `klt layers --flattened --include-text` reports `34/10` carrying exactly one text per pin (7 on `differential_driver`, 9 on `dplus_pullup`, 5 on `differential_receiver`, 4 on each single-ended receiver) and no text on any other layer. Each supply therefore has exactly **one** label, which is what makes `erc.unconnected_net`'s labelled-island count a meaningful "one island per supply" test. |
| `Metal2` | `36/0` | drawn in all five streams |
| `Metal3` | `42/0` | the top metal any of these streams draws |

`Metal4` (`46/0`) and `Metal5` (`81/0`) are **not** declared: no analog stream
draws a single shape on either (checked with `klt layers`, not assumed), so
declaring them would add two empty conductor regions. The digital spec
declares all five because its P&R power grid uses Metal4/Metal5 straps.

Layer numbers are gf180mcu's own drawn layers from the PDK's
`libs.tech/klayout/tech/gf180mcu.lyp` at the pinned open_pdks revision, and
cross-checked against klayout-tools' curated `gf180mcu` deck layer table
(`klayout_tools/decks/gf180mcu.py`) — identical.

## `vias`

`Contact` `33/0` (poly2↔Metal1), `Via1` `35/0` (Metal1↔Metal2), `Via2` `38/0`
(Metal2↔Metal3). `Via3`/`Via4` are absent from these streams along with
Metal4/Metal5.

## `nets`

Both supplies are `kind: "supply"`, which is what makes a short between them
report as the severe `erc.supply_short` rather than the general
`erc.multiply_driven_net`. Each must resolve to exactly **one** electrical
island: `erc.unconnected_net` fires both on zero matches (nothing in the
layout carries the label) and on more than one (the rail is split into pieces
that never touch), so zero findings of that rule naming a declared supply is
the "one island per supply" verdict rather than merely an absence.

**`nets[].roles` is deliberately not declared, and that costs this evidence
something.** Declaring the roles a supply *owns* turns on the severed-rail
measurement (`nets[].unlabelled_islands`, klayout-tools#2510/#2524) and is
strictly better evidence where it applies. It does not apply here: in all five
streams the supplies share `Metal1`, `Metal2` and `Metal3` with every signal
net, so no role is owned by a supply. Declaring ownership anyway would be a
false claim about the layout *and* would report every unlabelled internal
signal net as `erc.unlabelled_conductor`. The consequence is recorded rather
than hidden: the met citation's `power_delivery.supply_unlabelled_islands`
is `{}` — klt's honest "not measured", never a fabricated zero — so a grader
can see the severed-rail question was not asked on these streams.

## `ties`

### `nwell_pos_tap` — the n-well side, drawn geometry, no assertion

```json
{"name": "nwell_pos_tap", "well_layer": "21/0", "tap_layer": "22/0",
 "tap_requires": ["32/0"], "connect_to": "Metal1", "net": "<positive rail>"}
```

Every drawn `Nwell` (`21/0`) shape must hold a tap that reaches the positive
rail. The tap is `Comp ∩ Nplus` — exactly the `Comp && Nplus` n-tap the
klt erc docs name for gf180mcu, and the same boolean the PDK's own
`layers_definitions.lvs` and the curated deck's `comp.tap_distance.nwell.*`
rules use. `tap_requires` is load-bearing: a bare `22/0` tap layer would match
every PMOS source/drain contact in the same well, and klt grades such a
declaration `skipped` / `degenerate_tap_declaration` rather than checked
(klayout-tools#2199). With the narrowing it is reported in
`erc_coverage.checked`, with no assertion list, on all five streams — this
half is an ordinary geometrically-derived pass. Wells per stream: 17
(`differential_driver`), 12 (`dplus_pullup`), 4 each for the three receivers.

### `substrate_neg_tap` — the substrate side, an asserted region

```json
{"name": "substrate_neg_tap", "well_layer": null, "well_boxes": [...],
 "tap_layer": "22/0", "tap_requires": ["31/0"], "connect_to": "Metal1",
 "net": "VSS"}
```

These are **native-substrate** blocks: `klt layers` finds no `LVPWELL`
(`204/0`) and no other pwell/tub layer anywhere in the five streams, unlike
the digital partition's standard-cell rows, which do draw `204/0`. There is
therefore nothing drawn to name on the well side, and the declarable form is
`well_layer: null` plus `well_boxes` asserting the substrate region
(klayout-tools#2255). The tap is `Comp ∩ Pplus` outside the n-well — the
`PCOMP outside Nwell` substrate tap the PDK's own DRM rule DF.14 is about.

**The boxes are derived, not hand-typed.** One mechanical rule, re-run on
every harness invocation and gated against the committed spec:

```
substrate diffusion = Comp (22/0) − Nwell (21/0)
groups              = that region closed over a 1.1 µm proximity gap
                      (sized(+1.1 µm), merged, intersected back with the
                      diffusion — the closure only says which shapes belong
                      together, it is not part of the asserted region)
well_boxes          = the bounding box of each group's own diffusion
```

An asserted region is the caller's word, so klt grades this tie under its own
`erc_coverage.checked_by_well_assertion` bucket and the met citation names it
in `power_delivery.ties_checked_by_well_assertion`. Four properties make it
evidence rather than assertion, all measured per stream into the harness
summary's `assertion` block and gated in its `verdict`:

1. **every drawn substrate tap is inside the assertion** —
   `substrate_tap_area_outside_assertion_um2` is `0.0` on all five streams, so
   zero `erc.missing_tie` is a statement about all 84/28/24/28/28 of them;
2. **every asserted polygon holds a tap** —
   `asserted_polygons_without_a_tap` is `0`, so no polygon is carried by its
   neighbours;
3. **the assertion is nothing like the whole die** —
   `extent_uncovered_fraction` is 0.989–0.997, far above the 0.01 at which
   klt skips an assertion as `degenerate_well_assertion`;
4. **the `Pplus` narrowing removes real geometry** —
   `tap_narrowing_removed_um2` is 7.7–348.2 µm², so the tap side is not
   `degenerate_tap_declaration` either.

### Why 1.1 µm, and what the number buys

The gap is chosen by measurement (`scripts/analog_erc.py --gap-scan`), not
taste. Polygons per stream, in the committed stream order, with the
`erc.missing_tie` count each produces:

| gap (µm) | polygons | `erc.missing_tie` | `erc_status` |
|---|---|---|---|
| 0.6 – 1.03 | 51 / 18 / 18 / 18 / 18 | 34 / 12 / 12 / 12 / 12 | violations |
| **1.04 – 1.15** | **17 / 6 / 6 / 6 / 6** | **0** | **clean** |
| 1.16 – 1.25 | 4 / 2 / 6 / 2 / 2 | 0 | clean |
| ≥ 1.3 | 1 / 2 / 6 / 2 / 2 | 0 | clean |

1.1 µm sits in the middle of the clean plateau whose partition is finest.
That partition is not an arbitrary win: its polygon count equals, on every
stream, the number of body-tie pads that actually reach the ground rail
through metal (17 / 6 / 6 / 6 / 6), and the harness measures the distribution
directly — `metal_wired_taps_per_asserted_polygon` is `[1, 1, …]` on all five
streams. So the asserted partition is exactly the generator's own device
groups, one metal-wired body-tie pad each, which is the finest substrate
partition the drawn metal supports.

The gate `every_asserted_polygon_has_a_metal_wired_tap` makes that
self-checking: a gap set too fine cannot pass quietly, it fails the run. The
constant is a granularity knob with a verified floor, not a tuned magic
number.

## What this evidence does **not** establish

Stated here, and quoted in the evidence record, because the clean verdict is
narrower than it looks.

- **Not every drawn body-tie pad is wired to the rail.** `klt erc` joins
  conductors only through the declared `stackup`/`vias`; it has no device
  recognition and does not model substrate conduction. The harness therefore
  counts what the model cannot see (`census`): of the drawn substrate tap pads
  — 84 / 28 / 24 / 28 / 28 — **all** are contacted, but only **17 / 6 / 6 / 6
  / 6** reach `VSS` through `Contact`/`Metal1`/`Via*`/`Metal2-3`. The rest sit
  on isolated `Metal1` pads and are tied only through the substrate itself,
  which is what `klt lvs`'s deck-based extraction sees (and why its
  `body_verification.status` reads `verified` on all five streams while this
  ERC model cannot corroborate it). That is a layout observation, not a
  defect this item grades; it is filed as
  [#361](https://github.com/2AMLogic/gf180-usb2-phy/issues/361).
- **`erc.supply_short` is not computed.** Every one of these runs records it
  in `erc_coverage.inapplicable` with reason
  `substrate_continuity_not_modelled` (klayout-tools#4384): with two or more
  `kind: "supply"` nets declared, klt discloses that rails which are one
  conductor through a shared substrate read as separate clean islands. Zero
  `erc.supply_short` findings here is therefore "the declared stack shows no
  short", not "no short exists". The independent check is item 4's own LVS,
  which pairs the two supplies as distinct nets and reports `status: "match"`
  on all five streams — the cross-check klt's own disclosure asks for.
- **The severed-rail half is not measured**, for the `nets[].roles` reason
  above.
- **No antenna verdict.** `--pdk` is deliberately not passed, so the antenna
  half rolls `status: "not_checked"` and the process exits 4 — the same
  contract and the same exit code the digital ERC citation carries. Item 11
  grades `erc_status` and `erc_coverage`, not `status`
  (`docs/cli/erc.md`, "Two verdicts"), and an antenna verdict is explicitly
  not this item's subject (klayout-tools#1994). Adding `--pdk` would put an
  unrelated pass/fail into this item's citation for no gain to it.
- **Nothing about IR drop, EM, or latch-up margin.** Item 11 is the
  structural question. `klt power` is a different item and is not run here.

## Rejected alternatives

- **One shared spec for all five streams** — impossible: `dplus_pullup`'s
  supply is `VPU_REG`, and the substrate assertion is per-stream geometry.
- **One shared spec for digital and analog** — the stackups differ (no
  Metal4/Metal5 here, no `LVPWELL` tie here) and the label layers differ.
- **`well_complement_of` (klayout-tools#3750), i.e. substrate = extent −
  Nwell** — geometrically exact and needs no boxes, and rejected anyway: on
  these streams the n-well is 1.6–38.7% of the extent, so the complement is one
  die-sized polygon and `erc.missing_tie` degrades to "does any contact
  anywhere reach `VSS`", satisfied by any one pad. That is precisely the
  unfalsifiable pass the whole `ties[]` machinery exists to refuse, and klt's
  own degeneracy test would be a coin-flip against it (uncovered fraction
  0.016 on `se_receiver_dp` against a 0.01 threshold).
- **`ties_disclosure` instead of a declared substrate tie** — what
  `gf180-trng`'s analog specs do, because that block's streams draw no
  implant layers at all. These streams *do* draw `Nplus`/`Pplus`, so the tie
  is expressible and a disclosure would be a weaker claim than the truth
  supports (klt renders it `supply_spec_disclosed_unexpressible`, still
  unmet).
- **One asserted box per drawn tap pad** — the natural "finest possible"
  choice, and it reports 34 / 12 / 12 / 12 / 12 `erc.missing_tie` findings,
  for the metal-wiring reason in "What this evidence does not establish". It
  is the 0.6–1.03 µm row of the gap table above; it is not a cleaner spec, it
  is a claim this layout's metal does not support. If
  [#361](https://github.com/2AMLogic/gf180-usb2-phy/issues/361) wires every
  drawn pad, this becomes the right granularity and the gap drops to ≤ 1.03 µm
  in the same change.
- **`tap_is_dedicated: true`** — would clear the degeneracy test without
  `tap_requires`, and would be false: `Comp` `22/0` is every device's
  source/drain layer here, not a tap-only layer.
- **`--pdk gf180mcu`** — see "No antenna verdict" above.
