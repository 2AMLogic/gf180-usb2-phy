# DR-0001 — Flatten `dplus_pullup`'s multi-finger pull-up switch devices

- **Status**: Accepted (binding operator ruling)
- **Date**: 2026-09-05
- **Decided by**: repository operator, in-session, on
  [issue #56](https://github.com/2AMLogic/gf180-usb2-phy/issues/56)
- **Affects**: `design/dplus_pullup.sch`,
  `design/netlist/dplus_pullup.spice`; the spec §5 / §8.2 "D+ pull-up
  tolerance" evidence trail under `sim/dplus-pullup-tolerance/`
- **Does not change**: the ratified spec. `spec/usb2-device-phy.md` §5's
  1.5 kΩ nominal, ±5 % tolerance, integrated, enable-controlled pull-up is
  untouched. This record documents a **design-source representation**
  change, not a relaxation of any ratified value.

## Context

`design/dplus_pullup.sch` drew each of its six W = 1000 µm pull-up switch
devices — the enable switch `MEN` and the five trim-ladder bypass switches
`MSW0`..`MSW4` — as a single `nf=10` (ten-finger) instance. That is the
idiomatic way to draw a wide MOS device, and it is what the schematic
carried from the day the cell was created.

`klt`'s subckt-call → plain-element netlist conversion — the ingestion path
that `klt layout-plan` and `klt lvs` both go through, and that
`scripts/gen_analog_layout.py` drives — refuses to represent a multi-finger
device in its curated plain-element form. Its own error text prescribes the
remedy: *flatten it in the schematic netlist (one device per drawn gate)
before comparing.* The block was therefore un-ingestable, and no analog
layout for it was reachable. This was confirmed live, not quoted from a
stale finding, in
`verification/records/analog-layout/records/20260826-003645-4644a26.md`
against the repo's pinned `klt` revision `07b1f04f`.

Issue #56 was raised precisely because working around this in the design
source is *not* a Builder's unilateral call. Every `sim/` PVT record for
spec §5 had been taken against the `nf=10` netlist. Editing the design
source to satisfy a layout tool, without re-running that evidence, would
silently invalidate it — which `CLAUDE.md`'s "verification is the product"
and append-only-evidence rules forbid.

## The alternatives that were live

1. **Keep `nf=10`.** Preserves exact continuity with every existing spec §5
   record. Cost: `dplus_pullup` stays un-ingestable by `klt`'s layout-plan
   path indefinitely — the analog layout path for this block is forfeited
   until upstream grows multi-finger support, with no scheduled date.
2. **Flatten to one device per drawn gate.** Unblocks ingestion now. Cost:
   a spec-level decision record (this file); re-running every `sim/` record
   that depends on `design/netlist/dplus_pullup.spice` against the new
   netlist and *proving* rather than assuming equivalence; and accepting a
   schematic whose device decomposition is shaped by tooling convenience
   rather than purely by design intent.

Neither was factually superior. The trade-off axis is design-fidelity /
evidence-continuity against layout-tooling compatibility — a preference
call, which is why it was reserved for a decision record.

## Decision

**FLATTEN.** Each `nf=10` pull-up switch device is redrawn as ten
one-finger W = 100 µm devices in parallel — one device per drawn gate,
exactly the transformation `klt`'s error text specifies — with total drawn
gate width per switch unchanged at 1000 µm and every terminal connection
identical. No other design change rides along with it.

The operator's stated rationale, verbatim from the ruling:

> Rationale: layout work is now the program's stated priority, and the two
> representations are electrically equivalent in principle — the honest way
> to preserve evidence continuity is to *prove* that equivalence by
> re-running the affected records, not to freeze the schematic and forfeit
> the layout path indefinitely. The upstream tool gap is now tracked as
> klayout-tools#1487 (native nf expansion or an explicit conversion mode);
> if that lands, a future decision record may restore the idiomatic nf=10
> form.

## Conditions attached to the decision (all discharged)

The ruling was conditional on the evidence discipline, not a licence to
edit the schematic and move on. Each condition and where it is discharged:

1. **Re-run every `sim/` record depending on
   `design/netlist/dplus_pullup.spice`, with the equivalence comparison
   committed.** `sim/dplus-pullup-tolerance` was re-verified to be the
   complete such set (it is the only experiment whose `tb.json` names that
   DUT). New append-only record
   `sim/dplus-pullup-tolerance/records/20260905-185112-6bfe679.md`
   supersedes `20260817-203609-a408cb6` and carries the full comparison:
   45/45 PVT corners PASS (unchanged), the selected trim code identical at
   every one of the 45 corners, and a maximum absolute deviation of 0.01 Ω
   on measurements of 862–2572 Ω — one unit in the last printed digit.
   A control run of the *pre-flatten* netlist through the same harness on
   the same host reproduced the superseded record's 45-corner table
   bit-for-bit at all 270 printed values, so the residual deltas are
   attributable to the flatten and to nothing in the toolchain.
2. **Prove the flatten actually clears the tool blocker, rather than
   assuming the ruling settles it.**
   `verification/records/analog-layout/records/20260905-190024-525c67c.md`
   records the re-attempt against the same pinned `klt` revision: `klt` now
   ingests `dplus_pullup` (78 devices, 21 nets), and a throwaway probe plan
   places the flattened block for the first time. The other four blocks'
   results are unchanged, including `differential_driver`'s separate and
   still-open `rm1` blocker.
3. **File the tool gap upstream, generically.** Already tracked as
   [klayout-tools#1487](https://github.com/2AMLogic/klayout-tools/issues/1487)
   ("layout-plan/lvs ingestion refuses multi-finger (nf>1) MOS devices —
   support expansion natively or via an explicit conversion mode"),
   confirmed open at the time this record was written. Per `CLAUDE.md`'s
   friction protocol, this repo's design content stays out of that tracker.

## Consequences

- `design/dplus_pullup.spice` grows from 24 to 78 `X`-instances. This is
  netlist verbosity, not circuit change.
- The netlist is now **less faithful to the intended physical layout in one
  respect**, and this is stated rather than hidden: the PDK symbol derives
  drain/source junction area and perimeter from the finger count, so ten
  isolated one-finger devices claim roughly 2× the drain area and 1.7× the
  source area that a shared-diffusion ten-finger array would. That
  difference is purely capacitive. It cannot affect the DC sweep that
  substantiates spec §5, and the DC-relevant parameters are unchanged in
  aggregate (`nrd`/`nrs` combine in parallel to the same value; BSIM4's
  per-finger effective width `W/NF` is 100 µm in both forms). **A future
  transient or AC record for this cell, or an interdigitated layout, must
  re-derive that question rather than inherit this conclusion.**
- The schematic carries an on-canvas annotation stating why the array is
  drawn flat, so the next reader does not "tidy" it back to `nf=10`.
- **Reversal condition.** If klayout-tools#1487 lands native `nf` expansion
  or an explicit conversion mode, restoring the idiomatic `nf=10` form is a
  legitimate follow-up — but it is itself a design-source change and needs
  its own decision record plus its own re-run of the same `sim/` evidence,
  by the same reasoning that produced this one.
