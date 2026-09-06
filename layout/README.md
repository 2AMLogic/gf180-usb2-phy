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

`layout/analog/plans/*.json` are the resulting committed plans — four of the
five blocks now have one. The three receiver plans use one `device_groups[]`
entry per netlist device (`mos_array` with `rows`/`cols` 1 and `dummy` 0 for
each MOS, `res_array` with `num` 1 and `dummy` 0 for each poly resistor),
every group in a single `rows[]` row. `dplus_pullup.json` (issue #62) is the
first plan that groups rather than enumerates: 78 devices in 24 groups — the
six differently-sized `ppolyf_u` ladder segments as six distinct `res_array`
groups (one shared group would force a single `length_um` onto all six), each
switch bank's ten flattened fingers as one 10-wide `mos_array`, and the six
control inverters as per-device groups clustered in n/p pairs. It is also the
first plan to declare `routing` explicitly rather than take klt's default —
see "Route width" below. `scripts/gen_analog_layout.py` executes them and runs
`klt drc` on each result. Nothing here is hand-drawn: `klt draw` remains the
wrong tool for a layout claim (its own docs: "no PDK awareness and no rule
checking").

### What actually happened

Five runs exist. The first two ran against two `klt` pins over
byte-identical inputs (design netlists, plans, and the driver script never
changed between them — see `verification/records/analog-layout/` for the
content hashes that prove it); the pin moved specifically because the three
friction issues the first run filed (klayout-tools#1163, #1164, #1165) all
closed upstream within hours of that run, and the pin this repo carried
predated every one of the fixes (issue #52's investigation). The third
holds the `klt` pin fixed and changes exactly one design input —
`design/netlist/dplus_pullup.spice`, per the issue #56 flatten ruling
(`spec/decisions/0001-dplus-pullup-switch-device-flattening.md`) — so that
its effect is isolated. The fourth changes no design source at all: it adds
the committed `dplus_pullup` layout plan (issue #62) and drops that block
from the driver's `BLOCKED_BLOCKS`. The fifth (issue #65) changes no design
source and no `klt` pin either: it adds an explicit `routing` block (`metal`,
0.23 µm) to the three older plan documents themselves, in place of the
illegal 0.17 µm default they had taken by omission since the second run.

| Block | 2026-08-18, `klt` 0.2.0 @ `b3e284f` | 2026-08-26, `klt` 0.3.0 @ `07b1f04` | 2026-09-05, flattened `dplus_pullup` | 2026-09-05, + committed `dplus_pullup` plan | 2026-09-05, + legal `routing.width_um` (issue #65) |
|---|---|---|---|---|---|
| `differential_receiver` | 11 groups placed, **DRC-clean**, **0/8 nets routed** | 11 groups placed, **0/8 nets routed (unchanged)**, DRC **19 violations** (`metal1.width.1`) | unchanged — byte-identical GDS | unchanged — byte-identical GDS | **DRC-clean (0 violations)**, **0/8 nets routed (unchanged)** — `routing.width_um` corrected from klt's illegal 0.17 µm default to the deck's own 0.23 µm minimum |
| `se_receiver_dm` | 13 groups placed, **DRC-clean**, **0/9 nets routed** | 13 groups placed, **0/9 nets routed (unchanged)**, DRC **22 violations** | unchanged — byte-identical GDS | unchanged — byte-identical GDS | **DRC-clean (0 violations)**, **0/9 nets routed (unchanged)** — same fix |
| `se_receiver_dp` | 13 groups placed, **DRC-clean**, **0/9 nets routed** | 13 groups placed, **0/9 nets routed (unchanged)**, DRC **22 violations** | unchanged — byte-identical GDS | unchanged — byte-identical GDS | **DRC-clean (0 violations)**, **0/9 nets routed (unchanged)** — same fix |
| `differential_driver` | **cannot be ingested** — series-termination resistors are `rm1` (metal-1) devices, unknown to klt's curated `gf180mcu` deck | **cannot be ingested — identical error text, verbatim** | **still cannot be ingested** — unrelated blocker, unchanged | **still cannot be ingested** — unchanged | **still cannot be ingested** — unchanged, out of this fix's scope |
| `dplus_pullup` | **cannot be ingested** — pull-up switches carry `nf=10`, which klt's subckt-call → plain-element conversion refuses to represent | **cannot be ingested — identical error text, verbatim** | **ingests, and places** — 78 devices / 21 nets; blocker cleared by the flatten. Still **no committed plan**, so still no layout | **plan committed and executed** — 24 groups placed, **6/21 nets routed**, **DRC-clean (0 violations)**. Still not a layout: 15 nets unrouted | unchanged — byte-identical GDS (its plan already carried the legal `routing.width_um: 0.23`) |

**The `dplus_pullup` ingestion blocker is resolved; that block now has a
committed plan; it still does not have a layout.** Issue #56's operator
ruling (2026-09-05, FLATTEN — recorded as
`spec/decisions/0001-dplus-pullup-switch-device-flattening.md`) redrew each
of the six `nf=10` pull-up switch devices as ten one-finger devices in
parallel, one device per drawn gate, which is verbatim what klt's own error
text prescribed; that ruling did not make the change free — the flatten's
electrical equivalence is *measured*, in
`sim/dplus-pullup-tolerance/records/20260905-185112-6bfe679.md` (45/45 PVT
corners PASS, identical trim code at every corner, ≤ 0.01 Ω from the
superseded `nf=10` result), not assumed.

Issue #62 then authored `layout/analog/plans/dplus_pullup.json` — the real
plan, replacing the throwaway two-group probe #56's record used to prove the
ingestion path. Executing it places all 78 devices in 24 groups
(201.94 × 101.12 µm), routes **6 of 21 nets**, and produces a **DRC-clean**
GDS. Both of those are firsts for a committed analog plan in this repo, and
neither makes it a layout: the six routed nets are the inverter gate-input
nets, while every ladder node, both supplies, and all six switch gate-drive
nets are unrouted. The grouping decisions and the measured sweeps behind
them (grouping, `spacing_um`, `orientation`, `routing.layer_role`) are in
`verification/records/analog-layout/records/20260905-233520-2eca93d.md`.

**Route width: klt's default was illegal on this PDK, and that — not miter
geometry — is what the `metal1.width.1` counts above were measuring. All four
plans now set a legal width and all four are DRC-clean.** klt's documented
default routing width is 0.17 µm; the `gf180mcu` deck's own `metal1.width.1`
minimum is 0.23 µm (DRM 7.13 "Mn.1"), so every segment a default-width route
draws is below minimum. The `dplus_pullup` plan (issue #62) was the first
here to set `routing` explicitly (`metal`, 0.23 µm) and is DRC-clean; forcing
that same plan back to 0.17 µm yields 172 `metal1.width.1` violations with an
otherwise byte-for-byte identical placement and the same 6/21 routing.
Probing the three older plans the same way cleared **all** of their
violations (19 → 0, 22 → 0, 22 → 0) with unchanged 0/N routing, and issue #65
then committed that same `routing` block (`metal`, 0.23 µm) to
`differential_receiver.json`, `se_receiver_dm.json`, and `se_receiver_dp.json`
themselves — re-executing them confirms the identical result (0 violations,
routed-net counts unchanged) as the as-committed state, not just a probe. The
generic tool-side gap — klt never validates `routing.width_um` (nor its
hard-coded 0.22 µm via-drop square) against the resolved deck's own rules —
is filed upstream as
[klayout-tools#1501](https://github.com/2AMLogic/klayout-tools/issues/1501)
and remains open; this repo's own four plans no longer depend on it being
fixed.

A block of placed devices with none of its nets wired is not a layout, and
neither is one with 6 of 21 wired. None is committed as one, and no analog
GDS is committed under `layout/` — per `CLAUDE.md`'s rule against making a
claim the evidence does not support. Re-run `scripts/gen_analog_layout.py`
(below) to reproduce the artifacts under `layout/analog/out/` (gitignored)
for inspection; the same artifacts are frozen in the five evidence records.

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
*claimed mechanism*, not the observed symptom. See
`verification/records/analog-layout/records/20260905-200628-80cb14c.md`
for the full comparison and the independent re-verification that the
inspected and pinned commits are code-identical for the relevant files.
**That record's own explanation of the symptom is now superseded** — the
violating shapes are not the tapered quadrilaterals it (and #1424) described
but ordinary sub-minimum-width route segments; see "Route width" above and
record `20260905-233520-2eca93d`. The record stands unedited as the correct
account of *what reproduced*; only the mechanism it inferred is wrong.

**Why the routed-net count didn't move even though three friction issues
closed.** All three fixes are real and confirmed present in the newer
`klt` (checked directly against its own shipped docs, not assumed):
`netlist.device_map` now threads through a layout plan (#1163's fix), a
per-`device_groups[]` `orientation` field (`"mirror_x"`/`"mirror_y"`/
`"rotate_180"`) now exists to resolve same-facing ports (#1166, one of
#1164's five decomposed children), and a real two-layer
`routing.layer_role: "metal2"` bus role with via-drop now exists for
cross-block supply/bias nets (closing root-cause class 3 from the original
diagnosis below). **All three are opt-in fields that the three receiver
plans predate and do not use** — landing upstream does not retroactively
change what an already-written plan asks for.

**Update (2026-09-05, issue #62): two of those three were finally spent, on
`dplus_pullup`, and measured.** `orientation` was tried in all three
non-default values: `mirror_x` is neutral (6/21 routed, DRC clean),
`mirror_y` and `rotate_180` move the gate ports to the far edge and drop the
count to 0/21 — so the committed plan leaves it at `"none"` by measurement,
not by omission. `routing.layer_role: "metal2"` does remove the whole
same-drawing-layer rejection class, but does not raise the routed-net count
(the router still refuses to cross a block's bbox even on a layer that
cannot short to it) and adds 284 sub-minimum vias, so the committed plan
stays on metal1. The one capability that would plausibly carry the remaining
nets — `routing.cross_block_layer_role` — is unreachable from a plan
document at all (klayout-tools#1502). Using these fields for real is genuine
per-block analog layout design work, not a mechanical re-run, and remains
short of the line this repo does not cross into a bespoke block-specific
generator.

**A regression, found only because the same inputs were run twice — filed,
closed as refuted, re-confirmed to still reproduce, and finally root-caused
to this repo's own plans (2026-09-05, issue #62).** The story, in order,
because each step is recorded and none of them is deleted:

1. The three blocks went from DRC-clean to 19/22/22 `metal1.width.1`
   violations across a `klt` pin bump over byte-identical inputs. Per
   `gen-compose.md`, a partially-routable net's *accepted* legs are now kept
   in the output (klayout-tools#1169), where the pre-fix `klt` drew nothing
   for a rejected leg — so the new violations are drawn route geometry, and
   none of them come from device generation or placement. That much was, and
   remains, correct.
2. The mechanism this repo inferred for them — that a **rejected** leg
   leaves behind a mitered dead end tapering to zero width — was wrong. It
   was filed generically as
   [klayout-tools#1424](https://github.com/2AMLogic/klayout-tools/issues/1424)
   and **closed `NOT_PLANNED` on 2026-08-26**: the maintainer's direct source
   inspection found no `kdb.Polygon`/miter construction in `gen_compose.py`
   and every rejected leg's `points_um` `None` before the GDS writer runs.
   That refutation was right.
3. Issue #61's 2026-09-05 re-measurement then found the violations still
   reproduce byte-for-byte against the exact inspected commit — correctly
   recording that the refutation had settled the claimed mechanism without
   making the symptom go away
   (`verification/records/analog-layout/records/20260905-200628-80cb14c.md`).
4. Issue #62 root-caused it: the violating shapes are ordinary route
   segments drawn at klt's default `routing.width_um` of **0.17 µm**, below
   the `gf180mcu` deck's own **0.23 µm** `metal1.width.1` minimum. Setting a
   legal width on the identical plan documents clears every violation on all
   three blocks (19 → 0, 22 → 0, 22 → 0) with unchanged 0/N routed-net
   counts — see "Route width" above and record
   `20260905-233520-2eca93d`. The refuted miter theory and the real
   parameter bug were about different things, which is why both the
   maintainer's inspection and this repo's re-measurement were each right on
   their own terms.
5. Issue #65 committed the fix #62 had only probed: an explicit
   `routing: {"layer_role": "metal", "width_um": 0.23}` block added to
   `differential_receiver.json`, `se_receiver_dm.json`, and
   `se_receiver_dp.json` themselves. Re-executing the now-committed plans
   reproduces the probe exactly — 0 violations, 0/8, 0/9, 0/9 routed-net
   counts unchanged — see record `20260906-004835-90e442a`. The DRC-clean
   column of the table above is no longer a probe result; it is what the
   committed plans produce.

The remaining tool-side gap is that klt validates neither the requested
route width nor its hard-coded via-drop size against the resolved deck it
will later be judged by — filed generically as
[klayout-tools#1501](https://github.com/2AMLogic/klayout-tools/issues/1501)
and still open; this repo's committed plans no longer need it fixed to be
DRC-clean, they just needed a legal literal value.

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
  (filed by issue #52; **closed `NOT_PLANNED` 2026-08-26 — correctly
  refuted, and its claimed mechanism is now known to be wrong**) — it
  attributed the 19/22/22 `metal1.width.1` violations to a rejected
  (`routed: false`) leg leaving mitered dead-end geometry in the output GDS.
  The maintainer's direct source inspection found no such construction, and
  issue #62's 2026-09-05 root-cause confirms the refutation: the violations
  come from this repo's own plans requesting a 0.17 µm route width against a
  deck whose metal1 minimum is 0.23 µm. **Nothing about #1424 needs
  reopening**; the two real tool gaps behind the episode are filed fresh as
  #1501/#1502 below, and the plan-side correction — committing an explicit
  `routing.width_um: 0.23` to the three affected plans — is this repo's
  issue #65, **closed 2026-09-05**: all three blocks are now DRC-clean with
  their routed-net counts unchanged (record `20260906-004835-90e442a`).
- [klayout-tools#1501](https://github.com/2AMLogic/klayout-tools/issues/1501)
  (filed by issue #62, open) — neither `routing.width_um` nor the via-drop
  square is validated against the resolved PDK deck's own minimum-width
  rules, so `klt` silently draws geometry that `klt drc --deck <the same
  deck>` then rejects. Two instances measured: the documented default
  routing width (0.17 µm) is below `gf180mcu`'s `metal1.width.1` (0.23 µm),
  and the hard-coded 0.22 µm via-drop square is below its `via1.width.1`
  (0.26 µm), which makes `routing.layer_role: "metal2"` unable to produce a
  DRC-clean result on this family at all.
- [klayout-tools#1502](https://github.com/2AMLogic/klayout-tools/issues/1502)
  (filed by issue #62, open) — `layout_plan_execute` rebuilds
  `request.routing` from a two-field allow-list
  (`layer_role`/`width_um`), silently dropping every other field
  `gen_compose.compose()` accepts. `cross_block_layer_role` — the field the
  router's own rejection messages tell a plan author to configure when a
  net's backbone would short against a block's own ports — is therefore
  unreachable from a layout plan: adding it changes nothing, with no error
  and no warning. That is the single capability most of `dplus_pullup`'s 15
  unrouted nets are waiting on.

The `dplus_pullup` blocker (`nf=10`) was unrelated to any of the above and
was unmoved across the 2026-08-18 and 2026-08-26 runs: a deliberate,
documented refusal in klt's subckt-call conversion, whose own error text
prescribed the fix — "flatten it in the schematic netlist (one device per
drawn gate)". Doing that changes a design source to suit a tool, and the
`sim/` evidence for spec §5 had been taken against the un-flattened
netlist, so it was escalated rather than done unilaterally
([gf180-usb2-phy#56](https://github.com/2AMLogic/gf180-usb2-phy/issues/56)).

**Resolved 2026-09-05.** The operator ruled FLATTEN, conditional on proving
rather than assuming the equivalence — see
`spec/decisions/0001-dplus-pullup-switch-device-flattening.md` for the
ruling, the alternatives that were live, and the conditions attached. The
upstream tool gap is filed generically, per this repo's friction protocol,
as [klayout-tools#1487](https://github.com/2AMLogic/klayout-tools/issues/1487)
(native `nf` expansion, or an explicit conversion mode); if that lands, a
future decision record may restore the idiomatic `nf=10` form.

### What would have to be true to deliver analog layout

The routing capability itself has, in large part, landed
(klayout-tools#1163/#1164/#1165 above). What remains is: (a) plans that
spend the available capabilities on real per-block layout decisions —
genuine analog layout design work, not a mechanical re-run. `dplus_pullup`
(issue #62) is the first of these and shows both what that buys and where it
stops: measured grouping and spacing choices take it to 6/21 nets routed and
DRC-clean, and then it hits a wall that no plan can climb, because the
`metal2` bus role that would carry the remaining nets is unreachable from a
plan document (klayout-tools#1502) and, where it *is* reachable via
`layer_role`, draws sub-minimum vias (klayout-tools#1501). The three older
plans are now DRC-clean too (issue #65, committing the same legal
`routing.width_um: 0.23` those plans lacked), but that is an
attribution/DRC fix, not a routing improvement — `differential_receiver`
still routes 0 of 8 nets and both `se_receiver_dm`/`se_receiver_dp` still
route 0 of 9, so none of the three is any closer to a delivered layout than
before; (b) klt validating drawn geometry against the deck it will be judged
by — the still-open #1501 — so a routing attempt cannot manufacture
spurious violations the way the 0.17 µm default did for three blocks across
five runs before issue #65's fix; and (c) `differential_driver`'s remaining
ingestion blocker resolving via further klt device-class support (metal
resistors, non-MOS `device_map` entries) — `dplus_pullup`'s half of this item
is discharged by the 2026-09-05 flatten above. None of this
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

It also probes the one remaining block that has no committed plan
(`differential_driver`), so its ingestion error is re-measured live rather
than quoted from prose. If it ever ingests, the script says so explicitly
(`status: ingest-unexpectedly-succeeded`) and tells you to author its plan —
which is exactly how `dplus_pullup` left that list.

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
