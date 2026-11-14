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

Several manifest entries carry citations, each pinned to the cited
envelope's recorded input revision (`content_hash`). Of the
single-envelope ones below, 3.digital and 4.digital were verified fresh
by the grader at freeze time (`input_verified: true` in the frozen
report), while 7.digital and item 8 read `null`: 7.digital carries no
`content_hash` for the grader to re-hash, and item 8's pin is a `role:
"document"` hash with no path it can resolve. The list-form ones (items
4.analog, 5.analog, 5.digital, 6.analog, 11.analog and 11.digital) are
the compound citing sets those items' own text requires. Items 3 and 7 are
keyed to the **digital partition only** (`"3.digital"`, `"7.digital"`),
and item 5 is keyed in both; item 4 became partition-complete when
`"4.analog"` was added (issue #247) and item 11 when `"11.analog"` was
added (issue #248), so the T1 rows still graded from digital evidence
alone are 3 and 7. Only item 8 uses a bare key and so grades in both
partitions:

- **Item 3.digital, DRC clean** — cites the digital routed GDS's `klt drc`
  envelope (`verification/records/digital-drc/artifacts/20261015-011502-32db02a/drc-report.json`),
  pinned to the committed GDS
  (`layout/digital/usb_utmi_phy.gds`,
  `sha256:4491a548…`, regenerated by issue #131). **Coverage disclosure, quoted from the cited
  envelope's own `coverage` block as the item's text demands** (the
  report carries it verbatim; it is claimant-enforced, not graded):
  `layers_in_stream_without_rules`: `0/0`, `21/10`, `31/0`, `32/0`,
  `34/10`, `36/10`, `63/63`, `81/10`, `112/1`, `204/0`, `204/10`;
  `rules_skipped`: `bjt.separation.comp.1`, `metaltop.space.1`,
  `metaltop.width.1`, `mim.enclosing.fusetop.1`, `mim.enclosing.via4.1`,
  `mim.space.1`, `pad.enclosing.metal5.1`; `deck_scope`: chapters
  `7.4`–`7.15`, `9.1`, `10.4.2`, `10.7` of the foundry DRM. A "clean"
  measured inside those disclosed gaps is what "clean" means here — and it is
  a *digital*-partition result. The analog partition has no assembled
  top-level layout to run DRC on; its five blocks are individually routed and
  individually DRC-clean at the same deck (`layout/analog/`, cited by
  2.analog), which is a per-block probe and not a partition-level DRC
  signoff. Analog LVS is now cited per block (item 4.analog, below);
  analog DRC and ERC remain issues #246 and #248.
- **Item 4.digital, LVS clean** — cites the gate-level LVS envelope minted against
  the `gate-level-verilog` reference form
  (`verification/records/digital-lvs/artifacts/20261015-011503-32db02a/lvs-report.json`,
  `status: "match"` **and** `power_connectivity.status: "match"`,
  negative control correctly rejecting), pinned to the frozen extracted
  layout-side netlist (`role: netlist`,
  `sha256:0c965022…`; record `20261015-011503-32db02a`, regenerated by issue #131) — this is the first envelope whose power/ground half
  is computed rather than `"unchecked"` (issue #79; the Sep-21
  plain-element envelope it supersedes, like the superseded Aug-25 one,
  carries a hand-transcribed SPICE reference, and that form's power half
  reads `"unchecked"` by construction — see record
  `20260921-145814-5bee855.md`).

  **Item 3.analog is still `unmet`/`no_evidence`** (item 4.analog is
  cited, below). Until issue #95 these two citations sat under the bare
  keys `"3"` and `"4"`. On a `mixed-signal` manifest `klt signoff` looks
  up the partition-qualified key first and falls back to the bare key. So
  the analog rows also graded `met` from the *digital* DRC and LVS
  reports, although no analog layout existed to run DRC or LVS on.
  Re-keying the citations to the digital partition dropped the frozen
  count from `8/22` to `6/22`. That is a correction of an overstated
  count, not a regression — and 4.analog has since been earned on its own
  analog evidence rather than restored by un-keying.
- **Item 4.analog, LVS clean — cited, `met` since #247** — cites a list of
  five `klt lvs` envelopes, one per committed analog block, from record
  `verification/records/analog-lvs/artifacts/20261113-163000-35e9b6e5ab87/`
  (`<block>-lvs-report.json`). All five read `status: "match"` with
  `error_count: 0`, against the schematic netlist
  (`design/netlist/<block>.spice`, `reference.form: "subckt-call"`,
  `reference_top` upper-cased) that item 1.analog cites — the reference is
  a byte copy of the committed netlist, not a hand-edited one. Each
  citation is pinned to the GDS revision its envelope was minted against
  (`provenance.input`, `role: "layout"`). Minted at the repo pin
  (`klt 0.9.0`, KLayout `0.30.13`, deck `gf180mcu`
  `sha256:cf44de63…`, `released: true`).

  | block | GDS (`content_hash`) | reference netlist | devices | nets | pins | `device.geometry_not_compared` | `device.placeholder_value` | `topology` |
  |---|---|---|---|---|---|---|---|---|
  | `differential_driver` | `4a1c1ddf…` | `b5dda530…` | 40 | 22 | 7 | 2 | 2 | 1 |
  | `differential_receiver` | `8546baa5…` | `76a1e6f9…` | 11 | 10 | 5 | 1 | 1 | 1 |
  | `dplus_pullup` | `61811cc5…` | `9c645ecf…` | 78 | 21 | 9 | 1 | 1 | 1 |
  | `se_receiver_dm` | `31601e63…` | `ebfc91ac…` | 13 | 10 | 4 | 1 | 1 | 1 |
  | `se_receiver_dp` | `10131291…` | `1f854210…` | 13 | 10 | 4 | 1 | 1 | 1 |

  Device, net and pin columns are *matched* counts, and layout equals
  reference equals matched on every block. **What this claim does not
  cover**, in the envelopes' own words:

  - **`power_connectivity.status` reads `"unchecked"` on all five**, which
    satisfies the checklist (it requires "not `mismatch`") but verifies
    nothing about the supplies. The envelopes give the reason: the
    `subckt-call` reference form carries its own power/ground pins and
    nets, so they take part in the ordinary compare and the separate
    power check — which exists to cover the signal-only
    `gate-level-verilog` form — does not apply. The supplies' own check is
    item 11.analog, which issue #248 landed: these same five envelopes are
    its LVS half (the supply-pairing read of their `net_correspondence`),
    beside the five `klt erc` supply runs in
    `verification/records/analog-erc/`.
  - **No resistor dimension is compared.** The `ppolyf_u` / `ppolyf_u_1k`
    / `rm1` devices pair on topology alone: `R` is `not_compared`
    (`placeholder_value`) and `L`/`W`/`A`/`P` are `not_compared`
    (`secondary`) — that is what the `device.geometry_not_compared` and
    `device.placeholder_value` categories above count. A resistor of the
    wrong size would still read `match`. Trim-resistor *values* are a
    simulation claim (item 5.analog), not an LVS one.
  - **`body_verification.status` reads `"verified"` on all five** (it read
    `"unverified"` before issue #346 tied every device body), so the
    bodies are a checked part of this match rather than a disclosure.
  - **`input_verified` reads `null`, not `true`, for all five citations**
    — unlike 4.digital. The grader cannot re-hash the input itself because
    each envelope's `layout.path` names the harness's scratch copy
    (`layout/analog/lvs/<block>/<block>.gds`, gitignored), not
    `layout/analog/<block>.gds`. The pins above are still the GDS hashes:
    each `content_hash` was confirmed by hand to equal the sha256 of the
    committed `layout/analog/<block>.gds` at the commit that added this
    citation. Note the consequence for the freshness contract below: a
    re-run GDS does **not** automatically flip 4.analog to
    `unmet`/`stale_evidence` the way it would for 4.digital; what catches
    it instead is `signoff/check.py`, which refuses when a committed GDS
    stops hashing to the `gds_sha256` in `layout/analog/provenance.json`.
    Re-mint these envelopes through `scripts/analog_lvs.py` whenever an
    analog GDS or netlist moves.
- **Item 5.digital, corner verification (digital STA + functional verification): cited, `met` since #295 (was `unmet`/`partial_coverage` from #260 to #295 for want of a `functional-verification` citation; `met` before #188)**.
  Cites a list: one multi-corner `klt sta` envelope (below) followed by the
  12 `klt functional-verification` responses of record
  `verification/records/functional-smoke/artifacts/20261020-033000-4be8f5b/`
  (`utmi-phy-output.json`, the full top-level `usb_utmi_phy` suite, 111/111,
  first; then the 11 block-level suites). All 12 are `status: pass` with 0
  failures and grade `met`; the shape is that of `7.digital` (`file` only, no
  `content_hash`). Issue #295 checked that no `rtl/usb_*` file or exercised
  `verification/test_*.py` assertion changed after that record (only
  `harness_counter`, which none of the 12 suites exercise, was removed, plus
  docstring edits); the record was not re-run or edited.
  The STA part cites one multi-corner `klt sta` envelope,
  `verification/records/post-layout-pvt/artifacts/20261015-011505-32db02a/sta-corners.json`
  (record `20261015-011505-32db02a`, issue #131; the method is that of
  `20261008-195826-74ccfac`, issue #92, which measured the previous layout). It was run once with
  `pdk.corners` over the routed `layout/digital/usb_utmi_phy.def` and an
  SPEF extracted with `--def-pins`, which OpenSTA does attach:
  `delay_changed: true` at every corner. `content_hash` is the DEF hash
  the envelope records in `provenance.input` (`sha256:2bccf4bd…`,
  `input_verified: true`). The cited file is the emitted response (kept
  beside it as `sta-corners.emitted.json`) with only the producing
  checkout's root prefix stripped, so `def_path` is repo-relative and can
  be re-hashed from the repo root (klayout-tools#2879). The grader passes
  it because every declared corner is `timing_status: "constrained"` with
  non-negative setup and hold slack. Worst setup / hold slack:
  59.87 / 2.45 ns at tt, 25.70 / 5.90 ns at ss, 79.51 / 0.41 ns at ff.

  **What `met` here does and does not establish.** The grader checks the
  slack signs. It does not check whether parasitics were attached. A
  first version of this citation pointed at record
  `20261008-200000-8139bb6`. That envelope also graded `met`, but its SPEF
  had not attached at all (`delay_changed: false`, 307 partially
  unannotated drivers, wire capacitance 0). It was wire-parasitic-free
  timing presented as post-layout, and so was the earlier single-corner
  record `20260922-042422-9ec2304`. The PR #104 review caught this. The
  cited envelope still has two disclosed limits, measured in its record:
  - 7 unannotated drivers: the floating outputs of the CTS dummy-load
    cells.
  - 3 partially unannotated drivers: the `RxActive` / `LineState[1:0]`
    nets, whose DEF PIN name differs from their NET name. On the previous
    layout, attaching their parasitics by another route left worst slack
    unchanged; that cross-check was not repeated for the regenerated layout.

  The timing is also a lumped-capacitance model. The extractor's wire
  resistance never sits between two pins, so no wire RC delay is included.
  The clock is ideal (klayout-tools#2739). Lateral coupling is modelled
  only for `--critical-net` nets, and none were declared. Read the row as
  "three-corner STA with extracted wire and vertical-coupling capacitance
  attached". It is not full RC signoff.

  **Corner scope: three corners, and only three**: `tt_025C_1v80`,
  `ss_125C_1v62`, `ff_n40C_5v50`, the liberty corners of the
  `gf180mcu_fd_sc_mcu9t5v0` library. This does **not** cover spec §8.1's
  45-corner matrix (3 T x 3 V x 5 process including `fs`/`sf`), and the
  grader does not widen it. The digital timing row is a three-corner
  claim; the §8.1 difference is disclosed, not closed. The item's text
  also names a bit-exact functional suite. The grader's `sta` rule does
  not require one, and this citation does not claim it:
  `klt functional-verification` envelopes record no `provenance` and
  cannot be freshness-pinned, and SDF gate-level verification is tracked
  separately by #93 (cited as item 7.digital, see item 7 below). **Item 5.analog is cited, and renders `unmet`/`partial_coverage`** (see
  the 5.analog bullet below). **Item 5.digital rendered `met` at the previous
  pin and renders `unmet`/`partial_coverage` since issue #188**; since issue
  #260 the reason is no longer the analog rows but a missing
  `functional-verification` citation (see the 5.analog bullet's update note).
- **Item 11.digital, power delivery (structural) — cited, `met`** — the
  first T1 item no single artifact proves, so its manifest entry is a
  **list**: the digital partition's `klt erc` supply report
  (`verification/records/digital-erc/artifacts/20261015-011504-32db02a/erc-supply-report.json`,
  issue [#83] — `erc_status` clean, zero `erc.unconnected_net` /
  `erc.supply_short` / `erc.missing_tie`, with **both `ties[]` entries
  reported in `erc_coverage.checked`** — the spec now declares its
  well/substrate ties as `Comp ∩ Nplus` in Nwell → VDD and
  `Comp ∩ Pplus` in LVPWELL → VSS, which the klayout-tools#2169 fix
  inside the pinned klt makes gradeable), **plus** item 4's own
  gate-level LVS envelope, pinned as for item 4 (so including its
  `power_connectivity` verdict since issue #79's re-mint), **plus** the
  committed `klt place-and-route` envelope
  (`verification/records/place-and-route/artifacts/20261015-011501-32db02a/place-and-route-output.json`,
  unpinned-hash entry — that envelope records no input content hash to
  pin) whose `power.pdn: true` with
  `power.tapcell_master: gf180mcu_fd_sc_mcu9t5v0__filltie` the item's
  own text requires of an RTL-flow block. History: this row rendered
  `unmet`/`supply_spec_incomplete` from its first freeze (issue [#78])
  until [#83], because the spec deliberately declared no `ties[]` while
  klayout-tools#2169's tie-graph collapse made one unusable — the row
  flipped to `met` mechanically, by re-declaring the ties, re-running
  `klt erc`, and re-rendering this report, never by re-reading a
  checklist.
- **Item 8, characterization report** — the one item the grader binds to
  a purpose-built **generic envelope**
  (`manifests/item8-characterization.json`), wrapping
  `docs/characterization-report.md` and pinned to that file's content
  hash (`sha256:b2502c53…`). The envelope's `status: "pass"` asserts the
  *report's* existence, currency, and complete per-row coverage — it is
  **not** an assertion that every spec row passes; the wrapped report
  records 4 of 9 electrical rows as FAIL at some corners and says so, and
  the envelope's `summary` states this explicitly.

### Items 1, 2, 9 and 10 — artifact-anchored citations (issue #187)

These items have no `klt` verb behind them. Until `klt` 0.7.0 the
grader accepted *any* passing envelope for them, so citing one would have
been "borrowing a pass" and they were left uncited. klayout-tools#2843
(released in 0.7.0) closed that gap: the envelope must declare `"t1_item"`
and bind the audited artifact by path and content hash, and the row is
`met` only while the artifact still re-hashes to the pinned value
(`input_verified: true`). The repo pin (a git revision descending from 0.7.0, so it carries that
grader; `docs/klt-pin-history.md`, moves 7 and 8) serves this. The unreleased
`klt signoff --attest` (klayout-tools#2844) is **not** used: the envelopes
are written by `signoff/inventories.py`.

| Row | Envelope (`signoff/evidence/`) | Bound artifact | Members |
|---|---|---|---|
| 1.analog | `t1-item-1-analog-design-sources.json` | `inventory-design-sources-analog.json` | `design/*.sch` (5), derived `design/netlist/*.spice` (5), `design/netlist.py`, `design/xschemrc` |
| 1.digital | `t1-item-1-digital-design-sources.json` | `inventory-design-sources-digital.json` | `rtl/*.v`, vendored `rtl/common/*.v`, `reuse.lock.json`, the synthesis request, the routed gate-level netlist `layout/digital/usb_utmi_phy_routed.v` that item 4.digital LVS compares against |
| 2.analog | `t1-item-2-analog-layout.json` | `inventory-analog-layout.json` | the 5 routed analog GDS under `layout/analog/`, each with the layout plan and SPICE netlist it was built from, plus the generator sidecar `layout/analog/provenance.json` (issue #252) |
| 2.digital | `t1-item-2-digital-layout.json` | `layout/digital/usb_utmi_phy.gds` (bound directly; the same GDS items 3.digital and 11.digital pin) | — |
| 9 (both partitions) | `t1-item-9-testbenches.json` | `inventory-testbenches.json` | every cocotb test and `verification/request-*.json`, the `sim/*/testbench/` files of the 7 analog experiments, `sim/harness/`, the cold-start commands and the klt / cocotb / PDK pins |
| 10 (both partitions) | `t1-item-10-repo-hygiene.json` | `inventory-repo-hygiene.json` | `README.md`, `LICENSE`, `spec/usb2-device-phy.md`, `docs/environment-setup.md`, `.github/workflows/ci.yml`, `package.json` |

Each inventory lists every member with its sha256. `signoff/check.py`
(wired into `npm run check:ci`) rebuilds each inventory from the live tree and
fails on any changed, missing or newly added member, so editing an
inventoried file without running `python3 signoff/check.py --regen` fails CI.
`--regen` also refuses to write when an audit fails (a schematic without a
derived netlist, a cocotb test no request runs, a `sim/` experiment
`sim/spec-coverage.md` does not index, differing klt/cocotb pins between
`ci.yml` and `scripts/setup-env.sh`, or — for 2.analog — a **partial** analog
set: any plan under `layout/analog/plans/` with no delivered GDS, a GDS that
is missing or no longer hashes to the sidecar, or a block the sidecar does
not record as fully routed and DRC-clean. `signoff/test_inventories.py`
covers each of those refusals, including that a failed audit writes nothing).

**Limits — read before relying on these rows.** A `met` here says the
audited files exist, are listed, and have not moved since the audit. It does
not say they are correct:

- Gates that need xschem, the gf180mcu PDK, yosys or OpenROAD are **not**
  run by `signoff/check.py` or by the PDK-free CI job: `python3
  design/netlist.py --check` (1.analog), `klt synthesize` and
  `klt place-and-route` (1.digital, 2.digital), and every ngspice testbench
  (9). They are named in the inventories and in each envelope's `summary`,
  not claimed as run.
- The pinned grader binds a single `provenance.input.path`, so for 2.digital
  only the routed GDS is hash-bound. The P&R request
  (`flow/request-usb-utmi-phy-par.json`) is named in the envelope `summary`;
  the committed `klt place-and-route` envelope cited under 11.digital
  records the run.
- Item 9 maps the analog experiments to `sim/spec-coverage.md`, but the
  inventory does not assert that any measurement *passes*; the per-row
  verdicts (including the 4 of 9 electrical rows that fail at some corners)
  are in the characterization report (item 8).
- Items 9 and 10 render `met` for the analog and the digital partition
  alike, because one inventory covers the whole repo.
- For 2.analog the bound artifact is the *inventory*, not a stream: it
  asserts the five routed GDS exist and still hash to
  `layout/analog/provenance.json`, and that each was fully routed and
  DRC-clean at delivery. It does **not** assert that regenerating a stream
  reproduces its bytes — that gate is `scripts/gen_analog_layout.py --check`,
  which needs klt and the PDK and is run neither by `signoff/check.py` nor in
  CI. As of 2026-11-13 it reproduces all five: the one block that did not
  (`dplus_pullup`, which regenerated to a geometrically identical but
  byte-different stream) was fixed and re-delivered under issue #335, whose
  cause was that the generator ran every plan in one process. It claims no
  LVS, ERC or extracted re-simulation.

### What is deliberately uncited, and why

Per `klt signoff`'s own guidance ("items 1, 2, 9, 10 have no `klt` verb
behind them… the safest default is to leave them uncited"), and per this
repo's rule that an envelope must actually support the item to be cited:

- **Item 5.analog** (corner verification vs ratified spec, analog
  partition) — **cited (issue #188), renders `unmet`/`partial_coverage`**.
  Five `klt sim` envelopes, one per row-grading bench, each over the full
  45-corner grid (`sim/<bench>/corners/<record-id>/klt-sim-report.json`,
  run on the Spot batch fleet), each measurement carrying the spec bound as
  `limits` so a corner's `pass` means "inside the bound":
  `diff-receiver-sensitivity`, `se-receiver-dp-thresholds`,
  `se-receiver-dm-thresholds` (row `receiver-thresholds`),
  `driver-signal-quality` (rows `rise-fall-time`, `crossover-voltage`,
  `full-speed-signal-quality`) and `dplus-pullup-tolerance` (row
  `dplus-pullup-tolerance`). All five pass at all 45 corners, and the
  grader lists no failed and no uncovered row. **The one reason the item is
  not `met`** is the declared gap `driver-output-timing-jitter`: spec §8.2
  ratifies no jitter limit and mandates that the row be recorded as
  engineering data with no pass/fail (`sim/driver-jitter`, record
  `20261015-104027-d109790`), so no envelope can grade it. Its `klt sim`
  envelope is committed but deliberately **not** cited: it has no limited
  measurement, and an envelope with none grades `pass` vacuously
  (klayout-tools#3769). The rows are the §8.2 table's, in the manifest's
  `spec_rows` block. The per-row agreement between the envelopes and the
  older Markdown records is `docs/analog-envelope-agreement.md` (every
  comparison in the `.csv` beside it).
  **Side effect on 5.digital.** `spec_rows` is keyed by item id, not by
  partition (klayout-tools#3768), so declaring the analog rows also asks
  the digital partition's item 5 to cover them, and `5.digital` (one passing
  `klt sta` envelope, unchanged) drops from `met` to `unmet`/`partial_coverage`
  with every analog row listed as uncovered. Nothing about the digital
  evidence changed; the alternative was to omit `spec_rows` and let 5.analog
  render `met` with the jitter gap recorded nowhere the grader reads. Removing
  the `spec_rows` block restores `5.digital: met` at the price of that
  overclaim; the tool fix is #3768.
  **Update, issue #260 (2026-10-28, klt 0.8.0).** The side effect above is
  retired. klayout-tools#3768 shipped partition-qualified `spec_rows` keys
  in 0.8.0, and the manifest now declares the rows under `"5.analog"`
  (rows and the `driver-output-timing-jitter` gap unchanged). **No
  `5.digital` rows are declared**: spec §8.2 lists only analog quantities,
  so a digital row set would be invented. `5.digital` is therefore no longer
  charged with analog rows (`uncovered_rows` is gone). It then rendered
  `unmet`/`partial_coverage`, for a digital-partition reason that the
  analog rows had been masking: klt 0.8.0 grades item 5 digital as `sta`
  *and* `functional-verification`, and only the `sta` envelope was cited
  (`detail.missing_kinds: ["functional-verification"]`).
  **Update, issue #295 (2026-11-06).** The functional-verification
  responses are now cited beside the STA envelope and `5.digital` is `met`
  with no `missing_kinds` (frozen report `t1_met_count` 14 → 15 of 22).
  History: this item was recorded here as waiting on klayout-tools#1962
  (tracked in #53). That was a mis-attribution: #1962 is a `gen-compose`
  routing gap and #53 is post-layout re-verification, and item 5 is a
  schematic-level claim that needs no layout. (5.digital is cited above.)
- **Item 6** (Monte Carlo) — **digital partition: no statistical row,
  stated explicitly** in `verification/statistical-claims-na.md`, pinned to
  the SHA-256 of the ratified spec and re-checked by
  `verification/check_statistical_na.py`. `6.digital` is cited from
  `verification/statistical-na/*.json` and `klt` 0.8.0 (the CI pin) renders it
  `not_applicable` (cite block in `verification/statistical-claims-na.md`;
  it was held `unmet` / `no_evidence` while the pin predated that form).
  **Analog partition: statistical rows exist.** An earlier version of this
  paragraph said the whole block has none; that was wrong for the analog
  partition. `spec/decisions/0007-analog-statistical-rows.md` classifies them:
  the differential and single-ended receiver thresholds (input-referred
  offset is a MOS matching quantity) and the D+ pull-up tolerance (resistor
  ladder matching; not measurable with the gf180mcuD resistor model, whose
  mismatch hook ships disabled). A corner matrix cannot validate those, so
  `6.analog` is cited and renders `met` from `klt yield` reports of the
  differential-receiver Monte Carlo campaign
  (`sim/diff-receiver-mc/results/20261105-n100-regrade/`) and of the
  single-ended D+/D- receiver campaigns
  (`sim/se-receiver-mc/results/20261105-n100/{dp,dm}/`); seed, N=4500 and the
  known-bad controls are in each campaign's README. The D+ pull-up row has no
  Monte Carlo evidence yet (PDK-blocked), so `6.analog` is not a claim about it.
- **Item 7.digital, post-layout verification — cited, `met`** — the
  gate-level `test_usb_utmi_phy.py` suite (all 111 tests, none skipped)
  replayed through `klt functional-verification` against the routed netlist,
  the PDK cell models and the post-route SDF at the slow corner
  `ss_125C_1v62` (`options.sdf`, `environment.sdf.annotated: true`):
  `verification/records/post-layout-functional/artifacts/20261015-040000-963c79c/response-gate-sdf-ss_125C_1v62-filtered-klt-0.7.1.dev472.json`,
  111/111 pass (record `post-layout-functional/20261015-040000-963c79c`,
  issue #93). A `klt functional-verification` response carries no
  `provenance` block, so the entry has **no `content_hash`** (a pinned one
  would render `unverifiable_provenance`); the layout, SDF, test and request
  hashes are pinned in the record, where `verification/check_records.py`
  checks them for freshness. **Read the limits before relying on this row:**
  the grader accepts the run as annotated, but klt reports it as
  `partial` (52 IOPATH entries on XOR/XNOR/MUX-select arcs dropped because
  Icarus cannot elaborate their `ifnone` edge-only paths, and every
  TIMINGCHECK section dropped because Icarus implements none), so it is a
  functional check against annotated cell delays, not a setup/hold signoff;
  and one zero-delay `INTERCONNECT` entry was deleted from the SDF before the
  replay to pass klt's annotation gate (klayout-tools#2984, open; the raw
  SDF and the refused run are archived next to it). The negative control
  (same suite, 30 ns clock) fails 48/111 on functional assertions while the
  zero-delay replay at 30 ns passes. The replay needs klt at or after
  klayout-tools `bc386fb` (the #2885 fix); the pin
  at the time (`e8ca621a`) rendered the signoff report correctly but could not
  replay the SDF (53 diagnostics). Issue #188 moved the pin to `7ee09483`,
  which is past `bc386fb`; the replay was not re-run against it.
  The slow-corner SDF was produced outside klt from klt's generated
  OpenSTA script (klayout-tools#2886, open). **Item 7.analog stays
  `unmet`/`no_evidence`** (no analog layout; parked on klayout-tools#1962,
  tracked by #53 and the analog `layout/README.md` narrative).
- **Item 11.analog, power delivery (structural), analog partition — cited,
  `met`** (issue #248; it read `unmet`/`no_evidence` until this change,
  because no analog layout existed when the row was first frozen). Its
  manifest entry is a **two-part list**, the shape item 11 requires: the
  `differential_driver` `klt erc` supply report
  (`verification/records/analog-erc/artifacts/20261114-003000-db05b5e/differential_driver-erc-supply-report.json`,
  pinned to that stream's GDS hash `sha256:4a1c1ddf…`), **plus** that same
  block's `analog-lvs` envelope — the identical artifact item 4.analog cites,
  at the identical pin. No `klt place-and-route` part: that is the Digital
  column's PDN branch, and these are full-custom streams with no P&R
  response to cite.

  **Why this row cites one stream when the partition has five.** `klt
  signoff` resolves item 11's compound citation into exactly one
  `(erc, lvs)` pair — "a later part of the same kind replaces an earlier
  one", in its own docstring's words — so unlike item 4, which accepts a
  per-block citation **list** and renders a `citations_graded` entry per
  block, item 11 has no multi-member form for a partition built from five
  separately signed-off streams. A ten-entry list would be reduced to one
  pair while the rendered report still showed only two `parts`, i.e. the
  drop would be invisible to a reader of `t1-signoff-report.json`. So this
  row cites one visible pair, and `differential_driver` is the one: the
  largest analog stream (17 n-wells, 84 drawn body-tie pads, 17 asserted
  substrate polygons) and the block that drives the bus. **The tool gap is
  filed upstream as
  [klayout-tools#5597](https://github.com/2AMLogic/klayout-tools/issues/5597)**;
  when item 11 grows the list form item 4 already has, this entry becomes the
  five-pair set and the row is re-rendered in that change.

  The other four streams are *not* unevidenced. Their identical `klt erc`
  runs are frozen in the same record
  (`verification/records/analog-erc/records/20261114-003000-db05b5e.md`),
  every stream and every spec is pinned by hash in that record's
  `provenance.inputs[]` — so `verification/check_records.py` fails CI if any
  of them moves without a fresh record — and `scripts/analog_erc.py` re-runs
  and re-gates all five (plus five negative controls, plus the LVS supply
  pairing) on demand, with its shape-and-gating self-test
  (`scripts/test_analog_erc.py`) in `npm run lint`.

  **Coverage disclosures, quoted from the cited envelope**, since item 11
  asks a claimant to state them rather than leaving them to the tool:
  `erc_coverage.layers_in_stream_without_declaration` is **empty** (the
  spec's model is as wide as what the stream draws);
  `erc_coverage.skipped` is **empty** and both ties are in `checked`;
  `power_delivery.ties_checked_by_well_assertion` names
  `erc.missing_tie:["substrate_neg_tap"]`, because gf180mcu draws no tub
  layer for a native-substrate block and the substrate region is therefore
  caller-asserted (`well_boxes`, klayout-tools#2255) — derived from the
  stream by `scripts/analog_erc.py` and re-gated on every run, not
  hand-typed; `power_delivery.supply_unlabelled_islands` is `{}`, klt's
  honest "not measured", because no role is owned by a supply in these
  streams and `nets[].roles` is deliberately not declared; and
  `erc.supply_short` is `inapplicable` /`substrate_continuity_not_modelled`
  on every analog run, so the no-short claim rests on the LVS compare
  pairing the two supplies as distinct nets. The record's "What is NOT
  established" section carries these in full, including the measured fact
  that only 17 of `differential_driver`'s 84 drawn body-tie pads reach
  ground through metal.

## Regeneration and freshness

```bash
# the grader pin is the klayout-tools release in .github/workflows/ci.yml
# (`scripts/setup-env.sh` uses the same one, see docs/environment-setup.md), e.g.:
python3 -m venv /tmp/klt-pin && /tmp/klt-pin/bin/pip install "klayout-tools==0.9.0" cocotb==2.0.1
export PATH=/tmp/klt-pin/bin:$PATH
python3 signoff/check.py --regen   # only if an inventoried file changed on purpose
klt signoff --manifest manifests/gf180-usb2-phy.json --format json > /tmp/fresh.json
klt signoff --manifest manifests/gf180-usb2-phy.json --format text
diff /tmp/fresh.json manifests/t1-signoff-report.json   # regeneration = update the frozen report in the same change
```

Exit `0` means every T1 item met (this repo is **not** there:
exit `3`, `tier: null`, `18/22` item-rows met at the time of freezing —
3.digital, 4.analog, 4.digital, 5.digital, 6.analog, 7.digital, 11.analog
and 11.digital, plus item 8 in both partitions and the artifact-anchored
rows 1.analog, 1.digital, 2.analog, 2.digital and items 9 and 10 in both
partitions. The three still unmet are 3.analog (`no_evidence`), 5.analog
(`partial_coverage`) and 7.analog (`no_evidence`); the twenty-second row,
6.digital, grades
`not_applicable` rather than unmet (`t1_not_applicable_count: 1`, as the
item 6 bullet above records), so the rows are 18 `met` + 1
`not_applicable` + 3 `unmet`. The count was
`17/22` before issue #248 added the 11.analog citation,
`16/22` before issue #247 added the 4.analog citation, `6/22` before issue
#187, `7/22` before issue #188 (when 5.digital was also met, see the
5.analog bullet), and `8/22` before issue #95 stopped items 3 and 4 from
grading the analog partition off digital evidence. Exit codes `0` and `3` are
both "clean runs"; exit `1` is an error and must be fixed, not committed
around.

**The freshness contract is the pin, and CI re-checks it**
(`scripts/check_signoff_report.py` and `signoff/check.py`, both wired into
`npm run check:ci` and hence `.github/workflows/ci.yml`):

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
| `artifacts/` | stored-evidence manifests for new corner-run records — bytes in the artifact store, hashes here; see `artifacts/README.md` (not part of the signoff manifest) |
| `../signoff/` | `inventories.py` (the only writer of the items 1/2.digital/9/10 inventories and envelopes), `check.py` (the drift gate), `evidence/` (inventories and envelopes) |
| `README.md` | this claim document — kind/partition basis, citation rationale, disclosure of the uncited rows, the regeneration contract |

## Stored-evidence manifests are a different thing

`manifests/artifacts/` (issue #237) holds `klt artifact` manifests naming
simulation evidence kept in the artifact store. They are unrelated to the
`klt signoff` block manifest above, and adding one never changes
`t1-signoff-report.json`. The artifact client is a separate `klt` install from
the signoff pin in `.github/workflows/ci.yml` (the pin may predate
`klt artifact put`; bumping it would re-freeze the signoff report), so the
writer checks for the verb and fails closed rather than moving the pin.

[#78]: https://github.com/2AMLogic/gf180-usb2-phy/issues/78
[#3]: https://github.com/2AMLogic/gf180-usb2-phy/issues/3
[#77]: https://github.com/2AMLogic/gf180-usb2-phy/issues/77
[#83]: https://github.com/2AMLogic/gf180-usb2-phy/issues/83
[#53]: https://github.com/2AMLogic/gf180-usb2-phy/issues/53
