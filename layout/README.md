# layout

GDS/OASIS and DRC/LVS evidence for this PHY. Two halves, tracked separately
because they landed at very different maturity (issue #25, T1 checklist item
2).

## Digital — `layout/digital/` (delivered, DRC-clean, LVS-matched)

`usb_utmi_phy.gds` / `usb_utmi_phy.def` / `usb_utmi_phy_routed.v` — the real
PHY digital logic (`rtl/usb_utmi_phy.v` and every submodule it instantiates:
`usb_nrzi_encoder`, `usb_nrzi_decoder`, `usb_bit_stuffer`,
`usb_bit_destuffer`, `usb_sync_detector`, `usb_eop_detector`,
`usb_line_state_decode`), synthesized (`klt synthesize`, Yosys) and
place-and-routed (`klt place-and-route`, OpenROAD) against the gf180mcu
`gf180mcu_fd_sc_mcu9t5v0` standard-cell library. Reproducible from a
committed, real request-file flow — see `flow/README.md`'s "Digital
synthesis + place-and-route" section for the exact commands, and
`verification/records/place-and-route/` for the measurement: 342 mapped
standard cells becoming 1206 placed instances after tapcell/PDN/filler
insertion, 0 setup/hold/antenna/router-DRC violations at the 12 MHz spec
clock rate, ~68.5 MHz `fmax`, and every one of the cell library's 15 liberty
corners (1v8, 3v3 and 5v0 families) positive on both setup and hold.

**DRC-clean** — `verification/records/digital-drc/records/20260825-224815-6a83263.md`:
`klt drc --deck gf180mcu` reports `status: "clean"`, `violation_count: 0`
against this exact GDS.

**LVS-matched** — `verification/records/digital-lvs/records/20260825-224930-6a83263.md`:
gate-level LVS of this GDS against `usb_utmi_phy_routed.v` (the as-built,
post-CTS netlist) is a `status: "match"` with 0 mismatches, and a negative
control on a deliberately-broken reference is correctly rejected. Driven by
`scripts/digital_lvs.py`, which documents the three real asymmetries between
the two sides (physical-only filler cells, unconnected CTS load pins, and
`assign`-aliased output ports) and how each is handled. That script exists
because nothing upstream joins `klt place-and-route`'s outputs to a `klt lvs`
verdict — filed generically as
[klayout-tools#1419](https://github.com/2AMLogic/klayout-tools/issues/1419);
if it closes, most of the script should become deletable.

**What that does and does not say.** The curated `gf180mcu` deck is klt's own
rule set, not the foundry sign-off deck; no metal/density fill is inserted, so
this is not a density-clean claim. LVS holds the standard cells as black boxes
— it verifies the *assembly*, not the foundry's library. There is no IO ring
or pad frame (core-only), and no post-layout extracted-parasitic simulation.

**History.** Until 2026-08-25 this layout was **not** DRC-clean: 153 `Metal1`
space/width violations at standard-cell row gaps, root-caused to
`klt place-and-route`'s v1 scope having no filler-cell / power-rail-stitching
stage, and cross-checked against
[klayout-tools#1028](https://github.com/2AMLogic/klayout-tools/issues/1028).
That record
(`verification/records/digital-drc/records/20260817-202448-0956748.md`) is
superseded, not deleted — it remains the correct account of what a PDN-less
place-and-route produces. The fix was upstream: `klt` 0.3.0 added the optional
`request.power` block (tapcell + `pdngen` + `filler_placement`), which
`flow/request-usb-utmi-phy-par.json` now uses.

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
pin was moved forward to `b3e284f` specifically to consume it, and then again
to `07b1f04f` (issue #52) to consume the fixes named under "Friction filed"
below (see `docs/environment-setup.md`).

`layout/analog/plans/*.json` are the resulting committed plans — one per
block, one `device_groups[]` entry per netlist device (`mos_array` with
`rows`/`cols` 1 and `dummy` 0 for each MOS, `res_array` with `num` 1 and
`dummy` 0 for each poly resistor), every group in a single `rows[]` row.
`scripts/gen_analog_layout.py` executes them and runs `klt drc` on each
result. Nothing here is hand-drawn: `klt draw` remains the wrong tool for a
layout claim (its own docs: "no PDK awareness and no rule checking").

### What actually happened

Two runs exist, against two `klt` pins, over byte-identical inputs
(design netlists, plans, and the driver script never changed between them
— see `verification/records/analog-layout/` for the content hashes that
prove it). The pin moved specifically because the three friction issues
the first run filed (klayout-tools#1163, #1164, #1165) all closed upstream
within hours of that run, and the pin this repo carried predated every one
of the fixes (issue #52's investigation).

| Block | 2026-08-18, `klt` 0.2.0 @ `b3e284f` | 2026-08-26, `klt` 0.3.0 @ `07b1f04` |
|---|---|---|
| `differential_receiver` | 11 groups placed, **DRC-clean**, **0/8 nets routed** | 11 groups placed, **0/8 nets routed (unchanged)**, DRC **19 violations** (`metal1.width.1`) |
| `se_receiver_dm` | 13 groups placed, **DRC-clean**, **0/9 nets routed** | 13 groups placed, **0/9 nets routed (unchanged)**, DRC **22 violations** |
| `se_receiver_dp` | 13 groups placed, **DRC-clean**, **0/9 nets routed** | 13 groups placed, **0/9 nets routed (unchanged)**, DRC **22 violations** |
| `differential_driver` | **cannot be ingested** — series-termination resistors are `rm1` (metal-1) devices, unknown to klt's curated `gf180mcu` deck | **cannot be ingested — identical error text, verbatim** |
| `dplus_pullup` | **cannot be ingested** — pull-up switches carry `nf=10`, which klt's subckt-call → plain-element conversion refuses to represent | **cannot be ingested — identical error text, verbatim** |

A block of placed devices with none of its nets wired is not a layout. It
is not committed as one, and no analog GDS is committed under `layout/` —
per `CLAUDE.md`'s rule against making a claim the evidence does not
support. Re-run `scripts/gen_analog_layout.py` (below) to reproduce the
artifacts under `layout/analog/out/` (gitignored) for inspection; the same
artifacts are frozen in the three evidence records.

**A third run (2026-09-05, issue #61): re-measured after klayout-tools#1424
closed, found unchanged.** klayout-tools#1424 (the DRC regression named
below) was closed `NOT_PLANNED` on 2026-08-26 — the maintainer refuted the
issue's claimed mechanism ("polygon-miter code" in `gen_compose.py`) via
direct source inspection, and invited a re-run with a concrete repro if the
violations still reproduce. They do: this repo's `klt` pin has not moved
since the 2026-08-26 run (nothing upstream needed consuming), so the re-run
is byte-for-byte identical in every input and every output — same 19/22/22
`metal1.width.1` violations, on byte-identical polygons, same 0/8, 0/9, 0/9
routed-net counts, `cmp`-identical GDS files. The closure corrected the
*claimed mechanism*, not the observed symptom: the tapered/mitered
quadrilaterals the closed issue described are still produced, against the
exact commit the maintainer's source inspection covered (verified directly,
not assumed — see the record). See
`verification/records/analog-layout/records/20260905-200628-80cb14c.md`
for the full comparison and the independent re-verification that the
inspected and pinned commits are code-identical for the relevant files.

**Why the routed-net count didn't move even though three friction issues
closed.** All three fixes are real and confirmed present in the newer
`klt` (checked directly against its own shipped docs, not assumed):
`netlist.device_map` now threads through a layout plan (#1163's fix), a
per-`device_groups[]` `orientation` field (`"mirror_x"`/`"mirror_y"`/
`"rotate_180"`) now exists to resolve same-facing ports (#1166, one of
#1164's five decomposed children), and a real two-layer
`routing.layer_role: "metal2"` bus role with via-drop now exists for
cross-block supply/bias nets (closing root-cause class 3 from the original
diagnosis below). **All three are opt-in fields that the committed plans
under `layout/analog/plans/` predate and do not use** — landing upstream
does not retroactively change what an already-written plan asks for. Using
them for real (mirroring the load/output-stage devices so the CMOS-inverter
drain net stops fighting a same-facing port pair; putting `VDD`/`VSS`/bias
on a `metal2` bus) is genuine per-block analog layout design work, not a
mechanical re-run — and, per this file's "not in scope" framing, is
explicitly the line this repo does not cross into a bespoke block-specific
generator. This record states the capability exists and is unused, rather
than either claiming it closes the gap or re-deriving a whole routing
design under time pressure.

**A regression, found only because the same inputs were run twice — filed,
then closed as refuted, then re-confirmed to still reproduce.** The three
now-DRC-violating blocks are not evidence of worse placement — they are
evidence of a real behavior change in `klt` itself. Per `gen-compose.md`'s
own docs, a partially-routable net's *accepted* legs are now kept in the
output (klayout-tools#1169). What the raw Phase C response for each block
shows going further: legs whose own `reason` reports a **rejected**
candidate route still leave geometry behind, and that geometry is a
mitered dead end — a quadrilateral whose two long edges sit exactly at the
requested backbone width, cut off at the unterminated end by a diagonal
edge that tapers to a single point. A shape that tapers to zero width
cannot satisfy any positive minimum-width rule, so every one of the
19/22/22 violations is exactly that shape, on the rule that checks metal
width, and none of them come from device generation or placement. The
pre-fix `klt` was DRC-clean specifically because a rejected leg drew
nothing at all. Filed generically as
[klayout-tools#1424](https://github.com/2AMLogic/klayout-tools/issues/1424)
— **closed `NOT_PLANNED` on 2026-08-26**, the maintainer refuting the
issue's claimed mechanism (no `kdb.Polygon`/miter construction exists in
`gen_compose.py`; every rejected leg's `points_um` is `None` before the GDS
writer ever runs) via direct source inspection. A follow-up re-measurement
(issue #61, 2026-09-05) found the violations still reproduce, byte-for-byte
identical, against the exact commit that source inspection covered — see
"What actually happened" above and
`verification/records/analog-layout/records/20260905-200628-80cb14c.md`.
The refutation settled the claimed *mechanism*; it did not make the
observed violations go away, and root-causing the discrepancy further is
left as an open follow-up rather than attempted here.

### Why nothing routed — root causes, not guesses (as diagnosed 2026-08-18)

**This section is the original diagnosis and is now partly historical** —
per "Friction filed" above, classes 1 and 3 have shipped fixes upstream
(an `orientation` field, and a real `metal2` bus role) that this repo's
committed plans do not yet use. Kept verbatim because it is still the
correct account of why the *committed* plans read the way they do, and
because classes 2 and 4 are unconfirmed either way (not re-tested, since
the routed-net count didn't move — see "What actually happened").

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
the tool, not this design. **Update (issue #52, 2026-08-26): all three
below are now `CLOSED`/`COMPLETED` upstream** (closed 2026-08-18, the same
day they were filed) — `layout/analog/plans/` and this repo's `klt` pin
were advanced to `07b1f04f` specifically to consume the fixes (see
"What actually happened" above for why the routed-net count didn't move
regardless, and klayout-tools#1424 for a regression the same
re-measurement surfaced, closed `NOT_PLANNED` as of 2026-08-26 and
re-confirmed as of 2026-09-05, per the entry below, to still reproduce):

- [klayout-tools#1163](https://github.com/2AMLogic/klayout-tools/issues/1163)
  (closed) — `layout_plan`'s `netlist` block silently dropped `device_map`.
  Fixed: `device_map` now threads through. Does **not** unblock
  `differential_driver` — the fix is explicitly MOS-shaped-4-terminal only,
  and `rm1` is a 2-terminal metal resistor.
- [klayout-tools#1164](https://github.com/2AMLogic/klayout-tools/issues/1164)
  (closed, decomposed into #1166–#1170, all closed) — Phase C routed 0/N
  nets on a real full-custom block. Fixed: a `device_groups[]`/`blocks[]`
  `orientation` field (mirror/rotate) and a real two-layer
  `routing.layer_role: "metal2"` bus role (with via-drop) now exist. Both
  are opt-in and unused by the committed plans — see above.
- [klayout-tools#1165](https://github.com/2AMLogic/klayout-tools/issues/1165)
  (closed) — `diff_pair` netlist-derived sizing ignored `params.splits`.
  Fixed upstream; not exercised here since the committed plans use
  `mos_array`, not `diff_pair`, for exactly the reason this issue names
  below.
- [klayout-tools#1424](https://github.com/2AMLogic/klayout-tools/issues/1424)
  (filed by issue #52; **closed `NOT_PLANNED` 2026-08-26, refuted** — see
  below) — a rejected (`routed: false`) leg's candidate route geometry is
  still drawn into the output GDS, mitered to a dead end rather than
  squared off, which then violates the deck's own min-width rule — the DRC
  regression in the table above. The maintainer's closure found no
  polygon-miter construction in `gen_compose.py` via direct source
  inspection, refuting the issue's claimed mechanism. **Not resolved,
  though**: issue #61's 2026-09-05 re-measurement re-ran the identical
  inputs against the exact commit that source inspection covered (verified
  code-identical for the relevant files, not assumed) and found the
  19/22/22 `metal1.width.1` violations reproduce byte-for-byte unchanged.
  The closure corrected the claimed mechanism, not the observed symptom —
  see `verification/records/analog-layout/records/20260905-200628-80cb14c.md`
  for the full comparison. Root-causing the discrepancy further (or
  refiling with the concrete repro the closing comment invited) is an open
  follow-up, not attempted by either issue.

The `dplus_pullup` blocker (`nf=10`) is unrelated to any of the above and
completely unmoved: identical error text on both the 2026-08-18 and
2026-08-26 runs. It is a deliberate, documented refusal in klt's subckt-call
conversion, whose own error text prescribes the fix — "flatten it in the
schematic netlist (one device per drawn gate)". Flattening a 10-finger
device in `design/dplus_pullup.sch` would change a design source to suit a
tool, and the simulation evidence under `sim/` was taken against the
current netlist, so it is not done here. Tracked for a maintainer/architect
decision at [gf180-usb2-phy#56](https://github.com/2AMLogic/gf180-usb2-phy/issues/56)
(`loom:operator-decision`) rather than left as unattributed prose.

### What would have to be true to deliver analog layout

The routing capability itself has, in large part, landed
(klayout-tools#1163/#1164/#1165 above). What remains is: (a) authoring
plans that actually spend `orientation` and the `metal2` bus role on real
per-block layout decisions — genuine analog layout design work, not a
mechanical re-run, and the reason this record does not attempt it in the
same pass that discovered the capability exists; (b) the mitered-dead-end
DRC regression (klayout-tools#1424, closed `NOT_PLANNED`/refuted
2026-08-26 but re-confirmed as of 2026-09-05 to still reproduce against
the exact inspected commit — see "Friction filed" above) actually going
away, so a partially-successful routing attempt doesn't manufacture
spurious violations; and (c) the
`differential_driver`/`dplus_pullup` ingestion blockers resolving via
either further klt device-class support (metal resistors, non-MOS
`device_map` entries) or the `dplus_pullup` decision above. None of this
is a bespoke block-specific layout generator in the shape of
[`gf180-bandgap`](https://github.com/2AMLogic/gf180-bandgap)'s
`generate.py`/`plan.py` — that remains explicitly out of scope; this record
exists so that as each piece above closes, re-measuring is one command
rather than a re-derivation.

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
cp flow/.klt/place-and-route/usb_utmi_phy.gds layout/digital/usb_utmi_phy.gds
cp flow/.klt/place-and-route/usb_utmi_phy.def layout/digital/usb_utmi_phy.def
cp flow/.klt/place-and-route/usb_utmi_phy.v   layout/digital/usb_utmi_phy_routed.v

# --- digital signoff: DRC, then gate-level LVS (+ its negative control)
PDK=gf180mcuD klt drc layout/digital/usb_utmi_phy.gds \
    --deck gf180mcu --top usb_utmi_phy --format json
PDK=gf180mcuD python3 scripts/digital_lvs.py
PDK=gf180mcuD python3 scripts/digital_lvs.py --negative-control

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

`scripts/digital_lvs.py` writes its extracted/reference netlists and reports
to `layout/digital/lvs/` (gitignored scratch — the frozen copies live under
`verification/records/digital-lvs/`). It exits 0 only on `status: "match"`;
with `--negative-control` it exits 0 only when the compare correctly *fails*
on a deliberately broken reference.

See `flow/README.md` for the digital flow's full detail and
`verification/README.md` for the evidence-record convention that
`verification/records/place-and-route/`, `verification/records/digital-drc/`,
`verification/records/digital-lvs/`, and
`verification/records/analog-layout/` all follow.
