# T1 signoff manifest — the machine-graded verdict of record

`manifests/gf180-usb2-phy.json` is this block's **`klt signoff --manifest`
block manifest** (issue [#78]), and `manifests/t1-signoff-report.json` is
what `klt signoff` renders from it — frozen verbatim at the repo's pinned
`klt` and re-graded on every CI run. **As of this directory landing, these
two files are the verdict of record for this block's gap to T1
(design-evidence tiers), replacing the hand-maintained checkbox list in
tracking issue [#3].** Nothing else in this repo should be treated as the
finder's-answer to "what is this block's T1 state" — per-instrument
narratives (`sim/spec-coverage.md`, `layout/README.md`,
`docs/characterization-report.md`, the records under
`verification/records/`) remain the *engineering* accounts; the manifest
and its rendered report are the *graded* ones.

The fleet-side counterpart is the `--fleet` roll-up
([2AMLogic/2am#956](https://github.com/2AMLogic/2am/issues/956)); a fleet
manifest that lists this repo points at `manifests/gf180-usb2-phy.json`
from this block's repo root (`klt signoff`'s file-backed evidence paths
resolve against the invoking process's working directory — run from this
repo's root, not this subdirectory).

## Why this exists

Every prior "gap to T1" read in this repo (and the fleet) was hand-written
prose against whatever the checklist said that day. The checklist grew an
eleventh item on 2026-09-17 (klayout-tools#2025 — **Power delivery
(structural)**; its supply-spec half landed here via companion issue
[#77], closed by PR #80 while this manifest was being built), invalidating every
prior hand-read the moment it merged — and the `klt` pin this repo carried
predated it, so no mechanical re-read was even possible. This manifest is
the fix: an unmet item renders `unmet` with a stated `reason`, a cited
item renders `met` only when its evidence is a *passing* `klt` envelope
whose input content-hash matches the pin in the manifest — and when the
checklist moves again, re-rendering moves with it mechanically.

**An unmet row is not an accusation.** Per the tiers doc and
`klt signoff`'s own contract, an all-`unmet` manifest is an honest,
machine-readable statement of a gap. Which rows are deliberately cited
versus deliberately uncited, and why, is the rest of this document.

## The manifest

| Field | Value | Basis in this repo |
|---|---|---|
| `block` | `gf180-usb2-phy` | identifies this block's row in the fleet roll-up (2AMLogic/2am#956) |
| `kind` | `mixed-signal` | the block partitions into an analog front end (differential driver, differential + 2× single-ended receivers, D+ pull-up — `design/*.sch`) and a digital UTMI-side logic slice (`rtl/*.v`, synthesized, placed-and-routed in `layout/digital/`). A mixed-signal manifest is graded once per partition against each column's items; the kind-independent items cite the same evidence in both rows, per the tiers doc's own mixed-signal guidance |

**Partition boundary (claim, per the tiers doc's requirement that a
mixed-signal block state it explicitly):** the **analog partition** is the
five front-end blocks over the D+/D−/RPU pins — `differential_driver`,
`differential_receiver`, `se_receiver_dp`, `se_receiver_dm`,
`dplus_pullup` (schematics in `design/`, netlists in `design/netlist/`,
PVT evidence in `sim/`). The **digital partition** is the UTMI-side logic
instantiated as `usb_utmi_phy` — NRZI encode/decode, bit stuff/destuff,
SYNC/EOP detect, line-state decode and the UTMI wrapper (`rtl/*.v`) —
whose layout (`layout/digital/usb_utmi_phy.gds`) is the only committed
routed GDS. The boundary is the UTMI pin interface plus the two pins the
analog slice drives D+/D− and the receiver outputs it consumes; spec §2
draws it exactly.

## Citations — what is cited, and why

Four items carry citations, each pinned to the cited envelope's
recorded input revision (`content_hash`); the three single-envelope ones
were verified fresh by the grader at freeze time (`input_verified: true`
in the frozen report), and the fourth (item 11.digital) is the compound
citing set the item's own text requires:

- **Item 3, DRC clean** — cites the digital routed GDS's `klt drc`
  envelope (`verification/records/digital-drc/artifacts/20260825-224815-6a83263/drc-report.json`),
  pinned to the committed GDS
  (`layout/digital/usb_utmi_phy.gds`,
  `sha256:341ccb…`). **Coverage disclosure, quoted from the cited
  envelope's own `coverage` block as the item's text demands** (the
  report carries it verbatim; it is claimant-enforced, not graded):
  `layers_in_stream_without_rules`: `0/0`, `21/10`, `31/0`, `32/0`,
  `34/10`, `36/10`, `63/63`, `81/10`, `112/1`, `204/0`, `204/10`;
  `rules_skipped`: `bjt.separation.comp.1`, `metaltop.space.1`,
  `metaltop.width.1`, `mim.enclosing.fusetop.1`, `mim.enclosing.via4.1`,
  `mim.space.1`, `pad.enclosing.metal5.1`; `deck_scope`: chapters
  `7.4`–`7.15`, `9.1`, `10.4.2`, `10.7` of the foundry DRM. A "clean"
  measured inside those disclosed gaps is what "clean" means here — the
  analog partition has no full layout to run DRC on at all (its per-block
  plan-execution DRC probes live under `verification/records/analog-layout/`,
  incomplete by the routed-net gaps those records state).
- **Item 4, LVS clean** — cites the gate-level LVS envelope minted against
  the `gate-level-verilog` reference form
  (`verification/records/digital-lvs/artifacts/20260921-145814-5bee855/lvs-report.json`,
  `status: "match"` **and** `power_connectivity.status: "match"`,
  negative control correctly rejecting), pinned to the frozen extracted
  layout-side netlist (`role: netlist`,
  `sha256:89f86b1…`) — this is the first envelope whose power/ground half
  is computed rather than `"unchecked"` (issue #79; the Sep-21
  plain-element envelope it supersedes, like the superseded Aug-25 one,
  carries a hand-transcribed SPICE reference, and that form's power half
  reads `"unchecked"` by construction — see record
  `20260921-145814-5bee855.md`).
- **Item 11.digital, power delivery (structural) — cited, honestly
  `unmet`** — the first T1 item no single artifact proves, so its
  manifest entry is a **list**: the digital partition's `klt erc` supply
  report
  (`verification/records/digital-erc/artifacts/20260921-125459-223bae5/erc-supply-report.json`,
  issue [#77] / PR #80 — `erc_status` clean, zero `erc.unconnected_net` /
  `erc.supply_short` naming `VDD`/`VSS`) pinned to the routed GDS it
  graded, **plus** item 4's own gate-level LVS envelope, pinned as for
  item 4 (so including its `power_connectivity` verdict since issue #79's
  re-mint). The grader renders the row `unmet` with reason
  **`supply_spec_incomplete`** — the *correct* current state, not a gap
  in the citation: the committed spec
  (`layout/digital/erc-supply-spec.json`) deliberately declares **no
  `ties[]`**, because klayout-tools#2169's tie-graph collapse
  false-`supply_short` makes one unusable on a routed standard-cell
  design (reproduced four ways in `gf180-drone-fc`'s FRICTION F-034;
  [#77]'s record states it explicitly: `erc.missing_tie` *not computed*,
  an absence of evidence, not evidence of absence, with the well-tie
  stand-ins — `power.tapcell_master`, the standard cells' 64+64 PG pin
  labels, and the LVS compare's VDD/VSS pairing — named as what stands
  in). The row flips to `met` the day a usable `ties[]` model (or an
  equivalent graded path) lands upstream and the spec's `ties[]` +
  re-run are minted — mechanically, by re-rendering this report, never
  by re-reading a checklist.
- **Item 8, characterization report** — the one item the grader binds to
  a purpose-built **generic envelope**
  (`manifests/item8-characterization.json`), wrapping
  `docs/characterization-report.md` and pinned to that file's content
  hash (`sha256:8e8fc4…`). The envelope's `status: "pass"` asserts the
  *report's* existence, currency, and complete per-row coverage — it is
  **not** an assertion that every spec row passes; the wrapped report
  records 4 of 9 electrical rows as FAIL at some corners and says so, and
  the envelope's `summary` states this explicitly.

### What is deliberately uncited, and why

Per `klt signoff`'s own guidance ("items 1, 2, 9, 10 have no `klt` verb
behind them… the safest default is to leave them uncited"), and per this
repo's rule that an envelope must actually support the item to be cited:

- **Items 1, 2, 9, 10** (design sources, layout, testbenches shipped,
  repo hygiene) — the artifacts are *present in the repo* (the graded
  evidence the tracker narrative maps to them lives in issue #3's
  2026-09-18 re-survey), but the grader accepts *any* passing envelope
  for these four regardless of topical relevance, so citing a
  coincidentally-passing envelope at them would be exactly the
  "borrow a pass" the tiers doc warns about. They render `unmet` /
  `no_evidence` — the grader's honest statement that no *check* backs
  the claim — not a statement that the repo lacks sources, layout,
  testbenches, or hygiene.
- **Items 5 + 5.digital / 5.analog** (corner verification vs ratified
  spec) — the analog evidence (`sim/`, all 45 corners, per-row verdicts)
  exists as this repo's *own* Markdown evidence-record convention, which
  no `klt sim` envelope represents; and the digital evidence exists as
  three per-corner OpenSTA envelopes that predate `klt sta`'s
  `geometry_source`/`corner` response shape and are therefore not
  gradeable either — plus `klt functional-verification` envelopes that
  record no `provenance` and so cannot be freshness-pinned. Re-minting
  either leg at the current pin is real work with its own scope
  (post-layout STA is tracked by issue #53), not a manifest edit.
- **Item 6** (Monte Carlo) — the ratified §8.2 spec table contains no
  statistical (accuracy/offset/matching-distribution) row: every receiver
  threshold and the pull-up tolerance row are corner-matrix claims.
  Stated here explicitly per the item's own requirement that a spec with
  no statistical row must say so rather than silently omit the item.
- **Items 7.analog / 7.digital** (post-layout verification) — no analog
  layout exists to extract; the digital flow has SPEF-annotated STA
  (item-5-shaped evidence, deliberately not this item's) but no
  SDF-annotated `klt functional-verification` run. Tracked by #53 and
  the analog `layout/README.md` narrative.
- **Item 11.analog** (power delivery, structural, analog partition) — no
  analog layout exists, so no `klt erc` supply run has anything to grade:
  `unmet`/`no_evidence`. The digital partition's cite-and-document state
  is the bullet above; the frozen report carries both rows, which is what
  this manifest guarantees: the row exists the day the checklist does.

## Regeneration and freshness

```bash
./scripts/setup-env.sh          # provisions .venv at the pinned klt (see docs/environment-setup.md)
source .venv/bin/activate
klt signoff --manifest manifests/gf180-usb2-phy.json --format json > /tmp/fresh.json
klt signoff --manifest manifests/gf180-usb2-phy.json --format text
diff /tmp/fresh.json manifests/t1-signoff-report.json   # regeneration = update the frozen report in the same change
```

Exit `0` means every T1 item met (this repo is **not** there:
exit `3`, `tier: null`, `6/22` item-rows met at the time of freezing —
items 3, 4, and 8, each in both partitions). Exit codes `0` and `3` are
both "clean runs"; exit `1` is an error and must be fixed, not committed
around.

**The freshness contract is the pin, and CI re-checks it**
(`scripts/check_signoff_report.py`, wired into `npm run check:ci` and
hence `.github/workflows/ci.yml`):

1. Every citation's `content_hash` pins the input revision the cited
   envelope was produced against. If a cited artifact's input changes
   (e.g. the GDS is re-run) without re-minting the envelope *and*
   updating the manifest, the grader renders that item
   `unmet/stale_evidence`.
2. The committed `t1-signoff-report.json` must equal a fresh render,
   byte-semantics compared, on every CI run. A manifest citing an
   artifact that has since changed *fails CI* rather than rotting —
   and so does a report frozen against an older `klt` pin or a moved
   checklist: regeneration and the manifest move in the same change,
   visibly.

Re-verification of the LVS citation's freshness also rides the repo's
append-only evidence-record linter (`verification/check_records.py` pins
the record's `provenance.inputs[]` — GDS, gate-level netlist, driver
script, P&R request — to the working tree on every run).

## Files

| File | What it is |
|---|---|
| `gf180-usb2-phy.json` | the block manifest — `block`, `kind`, per-item pinned evidence citations. **The stable path a fleet roll-up points at.** |
| `t1-signoff-report.json` | `klt signoff --manifest gf180-usb2-phy.json --format json` output, frozen at the pinned `klt`; CI diff-checks a fresh render against it |
| `item8-characterization.json` | the T1-item-8 `generic` evidence envelope wrapping `docs/characterization-report.md`, pinned to its content hash |
| `README.md` | this claim document — kind/partition basis, citation rationale, disclosure of the uncited rows, the regeneration contract |

[#78]: https://github.com/2AMLogic/gf180-usb2-phy/issues/78
[#3]: https://github.com/2AMLogic/gf180-usb2-phy/issues/3
[#77]: https://github.com/2AMLogic/gf180-usb2-phy/issues/77
[#53]: https://github.com/2AMLogic/gf180-usb2-phy/issues/53
