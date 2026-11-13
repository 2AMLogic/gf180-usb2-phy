# `klt` pin-move history

Dated history: how this repo's `klayout-tools` (`klt`) pin got to where it is,
one numbered entry per move. The **current** pin is the table in
[`environment-setup.md`](environment-setup.md) § "Pinned versions" — read that
first; nothing here is an install instruction. Moves 1-8 describe a
git-revision pin scheme that move 9 superseded, so do not install a
`git+...@<sha>` revision named below. Move numbers are cited by records under
`verification/records/` and by `manifests/README.md`, so they are stable: a
future bump appends the next move here and changes the table there.

1. `af5791b5` → `b3e284fff4243cdc5ab59a684d9c0582444b485d` by issue #25,
   specifically to pick up the netlist-driven layout-plan compiler/executor
   (klayout-tools PR #1158 "Phase C", `klayout_tools.layout_plan_execute`,
   plus its follow-up fix #1161) that `scripts/gen_analog_layout.py` calls
   — see `layout/README.md`.
2. `b3e284f` → `07b1f04f29f21b3f8551d3937183b206a57a5e3a` by issue #52.
   `b3e284f` was authored 2026-08-18T08:48:51Z; the friction issues that
   same exercise filed (klayout-tools#1163/#1164/#1165) all closed
   `COMPLETED` between 12:19Z and 14:33Z **that same day**, so the pin this
   repo carried predated every fix by hours despite never having been
   re-pinned since. `07b1f04f` is klayout-tools' `main` tip as of this
   move (2026-08-26T00:25:45Z) — confirmed (`gh api
   repos/2AMLogic/klayout-tools/compare/<fix-commit>...main`) to have every
   relevant fix commit as a strict ancestor. See
   `verification/records/analog-layout/records/20260826-003645-4644a26.md`
   for what re-measuring against it did and did not change.
3. `07b1f04f` → `8bd3f0b09a87641b093d655a7282b8f730db19e8` by issue #68,
   specifically to pick up two fixes this repo's committed analog plans were
   waiting on, both closed `COMPLETED` 2026-09-06 — klayout-tools#1502
   (merge [`815d8abadf4182bd1b2543c1dee2f7d04a5ee904`](https://github.com/2AMLogic/klayout-tools/commit/815d8abadf4182bd1b2543c1dee2f7d04a5ee904),
   PR #1509: `layout_plan_execute._resolve_routing_spec()` forwards
   `routing.cross_block_layer_role` instead of silently dropping it, and
   hard-fails on unknown `routing` keys) and klayout-tools#1501 (merge
   [`8d094b70628aae2d4cdba7544989c415c1f877a4`](https://github.com/2AMLogic/klayout-tools/commit/8d094b70628aae2d4cdba7544989c415c1f877a4),
   PR #1507: routing width and the via-drop square are floored at the
   resolved deck's own DRC minimums). Both are **strict ancestors** of the
   new pin — verified with the doc's own rule, `gh api
   repos/2AMLogic/klayout-tools/compare/<fix-commit>...8bd3f0b09a87641b093d655a7282b8f730db19e8`
   returning `status: "ahead"` with `behind_by: 0` for each (`ahead_by` 83
   and 84 respectively); the old pin `07b1f04f` is likewise `behind_by: 0`,
   `ahead_by: 189`. `8bd3f0b0` was klayout-tools' `main` tip at the time of
   this move (2026-09-09T20:48:26Z). The `klt` self-reported version crosses
   a minor boundary with this move (`0.3.0+g07b1f04f29f2` →
   `0.4.0+g8bd3f0b09a87`). See
   `verification/records/analog-layout/records/20260909-213500-29c5780.md`
   for what the pin bump alone changed with byte-identical plans, and
   `…/20260909-215500-29c5780.md` for what spending
   `routing.cross_block_layer_role` on `dplus_pullup` then bought.
4. `8bd3f0b0` → `bf90e1d5e3a624ea2e098efdfe76596081508751` by issue #70,
   specifically to pick up klayout-tools#1640's fix (merge
   [`df36f4fce8c63e367c132a3335369a877acc4ebb`](https://github.com/2AMLogic/klayout-tools/commit/df36f4fce8c63e367c132a3335369a877acc4ebb),
   PR #1662: `rm1`/`rm2`/`rm3` — plus `tm6k`/`tm9k`/`tm11k`/`tm30k` —
   gf180mcu metal-resistor device classes now recognised by
   `netlist_digest`), the ingestion blocker behind `differential_driver`
   being the only one of the five analog blocks klt could not ingest at
   all. The fix commit is a **strict ancestor** of the new pin —
   `gh api repos/2AMLogic/klayout-tools/compare/df36f4fce8c63e367c132a3335369a877acc4ebb...bf90e1d5e3a624ea2e098efdfe76596081508751`
   returns `status: "ahead"`, `behind_by: 0`, `ahead_by: 39`. `bf90e1d5e3a6`
   is not klayout-tools' bare `main` tip at the time of this move (`main`
   was one commit ahead, `160073f34f74e1796b903586a2f278a0438a6462`, whose
   sole parent *is* `bf90e1d5e3a6`, with several CI legs still `queued` —
   `gh api
   repos/2AMLogic/klayout-tools/compare/bf90e1d5e3a624ea2e098efdfe76596081508751...160073f34f74e1796b903586a2f278a0438a6462`
   returns `status: "ahead"`, `behind_by: 0`, `ahead_by: 1`); it is the
   newest commit whose own CI had fully completed with every check-run
   `conclusion: "success"` at check time. The pin move itself is much larger
   than that one-commit gap to `main`: `gh api
   repos/2AMLogic/klayout-tools/compare/8bd3f0b09a87641b093d655a7282b8f730db19e8...bf90e1d5e3a624ea2e098efdfe76596081508751`
   returns `status: "ahead"`, `behind_by: 0`, `ahead_by: 70` — 70 commits
   spanning 2026-09-09T20:48:26Z → 2026-09-12T18:19:29Z (just under three
   days), with the fix commit `df36f4f` 31 commits past the old pin and 39
   short of the new one (31 + 39 = 70). `behind_by: 0` means the old pin
   is a strict ancestor, so the move is still purely forward — a
   fast-forward, but not a one-commit one. The `klt` self-reported version does
   not cross a minor boundary this time (`0.4.0+g8bd3f0b09a87` →
   `0.4.0+gbf90e1d5e3a6`). **What the move bought, and what it didn't**:
   `differential_driver`'s netlist now ingests cleanly (confirmed live), but
   a committed plan still isn't possible — `klt gen`'s `res_array` generator
   has no drawn-geometry support for a gf180mcu metal resistor at all, and
   silently draws the wrong device (a poly resistor) instead of failing
   when a plan leaves `flavor`/`metal_level` at their defaults for an `rm1`
   device, a distinct, narrower gap filed generically as
   [klayout-tools#1731](https://github.com/2AMLogic/klayout-tools/issues/1731).
   See
   `verification/records/analog-layout/records/20260912-191922-5953e89.md`
   for the full reproduction, the byte-identical re-confirmation for the
   four already-committed plans, and a throwaway probe's initial (unrouted)
   placement/DRC reading for `differential_driver`.
5. `bf90e1d5e3a6` → `61e743088f4722854d18b0cc48bd98c3dee58cf6` by issue #72,
   specifically to pick up klayout-tools#1731's fix (merge
   [`1641fa5f9617e57931debbfc2bc58fab62799348`](https://github.com/2AMLogic/klayout-tools/commit/1641fa5f9617e57931debbfc2bc58fab62799348),
   PR #1774: `res_array`'s `metal_level` mechanism gains real drawn-geometry
   support for gf180mcu's `rm1`/`rm2`/`rm3` metal-resistor device classes,
   and a new `device_groups[]`-declared-class-vs-resolved-generator-output
   mismatch check appends a `warnings[]` entry instead of silently
   substituting the wrong device), the last blocker standing between
   `differential_driver` and a committed layout plan. The fix commit is a
   **strict ancestor** of the new pin — `gh api
   repos/2AMLogic/klayout-tools/compare/1641fa5f9617e57931debbfc2bc58fab62799348...61e743088f4722854d18b0cc48bd98c3dee58cf6`
   returns `status: "ahead"`, `behind_by: 0`, `ahead_by: 1`; the old pin
   (`bf90e1d5e3a6`) is 32 commits **behind** the fix (`compare/1641fa5f...
   bf90e1d5e3a6` → `status: "behind"`, `behind_by: 32`), confirming it did
   not contain it. **The new pin is klayout-tools' bare `main` tip**
   (`61e743088f4722854d18b0cc48bd98c3dee58cf6`, 2026-09-13T18:59:37Z) — a
   deliberate deviation from the "confirm CI, don't just take `main`" habit
   the fourth move set, made because checking both candidates' CI directly
   (not assumed from either commit's filing-time snapshot) showed `main`
   tip was the *more* complete one: the fix commit itself has two
   `cancelled` check-runs alongside eleven `success` ones, while `main`
   tip's fourteen check-runs are all `conclusion: "success"`. The `klt`
   self-reported version does not cross a minor boundary
   (`0.4.0+gbf90e1d5e3a6` → `0.4.0+g61e743088f47`). **What the move bought,
   and what it didn't**: `differential_driver` now has a committed,
   correctly-drawn plan (`layout/analog/plans/differential_driver.json`) —
   its two `RM1` series-termination resistors draw real `Metal1`/`Via1`/
   `Metal2` geometry with an explicit `params.metal_level: 1`, confirmed by
   direct GDS layer inspection and a zero-length `warnings[]` array, not
   assumed. The four already-committed plans are unaffected at the
   drawn-geometry level — verified by per-layer Boolean XOR against the
   superseded record's frozen artifacts (zero area difference on every layer
   of all four blocks), **not** by byte comparison: the GDS files are
   geometrically identical but not byte-identical, differing only in the
   order the same elements are emitted. **The new mismatch-warning
   check itself found something this move did not set out to look for**:
   three of those four plans (`differential_receiver`, `se_receiver_dm`,
   `se_receiver_dp`) have their own declared-class-vs-drawn-device mismatch
   — a `PPOLYF_U_1K`-declared bias/reference resistor drawn as the
   default-flavor `ppolyf_u` body instead, present since before this pin
   moved and only now visible. That is a real finding this record does not
   fix (see the record and the follow-up issue it links) — this repo's own
   plan documents disagreeing with the netlist they were written against,
   not a further `klt` gap. See
   `verification/records/analog-layout/records/20260913-192744-b653c71.md`
   for the full reproduction, the geometric re-confirmation (per-layer XOR)
   for the four already-committed plans' drawn geometry, the layer-level
   confirmation that `differential_driver`'s `RM1` groups now draw correctly,
   the newly-surfaced `PPOLYF_U_1K` mismatch finding, and the characterization
   of the GDS byte-level ordering difference.

6. `61e743088f4722854d18b0cc48bd98c3dee58cf6` →
   `e8ca621a6961879cec1af60cc932c3b3d58ddcaa` by issue #78, driven by the
   T1 signoff block manifest rather than by one upstream fix: grading T1
   state with `klt signoff --manifest` requires (a) the **eleventh checklist
   item** "Power delivery (structural)" (klayout-tools#2025/#2057, merged
   2026-09-19 — every earlier `klt` renders a ten-item report, and by this
   repo's own recorded re-survey reads that item's absence made prior
   gap-to-T1 tables stale the day it landed), and (b) `klt lvs`'s
   `provenance.input.content_hash` recording (klayout-tools#1969) so an
   "LVS clean" citation can be freshness-pinned at all. The item-11 merge
   `428951e036935d37161732adb55915049c598cc4` is a strict ancestor of the
   new pin — `gh api repos/2AMLogic/klayout-tools/compare/428951e036935d37161732adb55915049c598cc4...e8ca621a6961879cec1af60cc932c3b3d58ddcaa`
   returns `status: "ahead"`, `behind_by: 0`, `ahead_by: 58` — and the old
   pin is likewise purely behind it (`behind_by: 0`, `ahead_by: 263`).
   `e8ca621a` is klayout-tools' `main` tip (2026-09-21T12:10:33Z) at the
   time of this move, with its own CI complete: all 18 check-runs
   `conclusion: "success"` at the time of this move. **The same move also
   repairs a drifted second pin**: `.github/workflows/ci.yml` still
   installed the *first* pin `b3e284f` (it was never moved by re-pin
   moves 2-5, and at `b3e284f` the CI could not have rendered item 11 or
   re-run the manifest at all); it now installs the same revision as
   `scripts/setup-env.sh`, restoring the "keep in sync with
   docs/environment-setup.md" invariant both files declare. The `klt`
   self-reported version crosses a minor boundary (`0.4.0+g61e743088f47` →
   `0.5.0+ge8ca621a6961`). **What the move bought, and what it didn't**:
   the digital LVS verdict reproduces (`status: "match"`, negative control
   still correctly rejected) at the new pin — and the re-run's envelope
   now records `provenance.input.content_hash`, which the superseded Aug-25
   envelope could not; re-minted as
   `verification/records/digital-lvs/records/20260921-132813-1376d98.md`.
   The five committed analog plans re-execute with no status change
   (DRC-clean everywhere, `0 warnings[]` everywhere, routed tally
   unchanged per block), but `dplus_pullup`'s drawn Metal-1 routing
   genuinely changed shape — 63,504,000 dbu² less on layer `34/0` vs the
   superseded run, produced by the upstream routing-semantics commits
   (#1931/#1936/#1945/#2098/#2144) between the pins — minted as
   `verification/records/analog-layout/records/20260921-130120-223bae5.md`
   rather than assumed identical. The four other blocks' GDS are
   `cmp`-identical to the superseded record's. **Engine note**: this venv
   explicitly holds `klayout==0.30.10` — the `klayout_version_expected`
   this pin reports as tested — so fresh envelopes carry
   `klayout_version_mismatch: false` (a venv left to resolve the newest
   `klayout` shows the flag `true`; the first extraction attempt here did,
   and was discarded, not committed).

7. `e8ca621a6961879cec1af60cc932c3b3d58ddcaa` →
   `7ee09483b74867a47a05eb353015c2cf5ca33ef3` by issue #188, to grade item
   5.analog. The move was needed for two reasons: `measurements[].expr`
   (klayout-tools#2533) and list-form item-5 evidence with `spec_rows`
   coverage (klayout-tools#2959, which lets several `klt sim` envelopes
   jointly cover one item). **`v0.7.0` (`0e2362bd`) has #2533 but not #2959**:
   `klayout_tools.signoff` there has no `_grade_multi_citation`. So the pin is
   the commit the fleet-dispatch host's `klt` was built from (`klt
   0.7.1.dev1743+g7ee09483b748`), which contains both, not a release tag.
   Re-pin to a release once one carries #2959.
   For this move only the lint half of `npm run check:ci` was run locally
   (`npm run lint`'s chain plus `scripts/check_signoff_report.py`); the cocotb
   half (`npm run test`) was left to CI. The re-pin made two live
   `analog-layout` records' `setup-env.sh` provenance hash stale; they are
   superseded by source-only records, not re-run.

8. #187 (artifact-anchored generic envelopes for T1 items 1, 2, 9 and 10,
   klayout-tools#2843, first released in 0.7.0) needs no further pin move: the
   `7ee09483` pin above descends from 0.7.0, so it already carries that grader.
   The old `e8ca621a` revision predates it and renders those items
   `unmet`/`no_evidence` whatever is cited. The unreleased `klt signoff --attest`
   (klayout-tools#2844) is not used. No evidence record was re-minted.

9. `7ee09483b74867a47a05eb353015c2cf5ca33ef3` (`0.7.1.dev1743+g7ee09483b748`) →
   release `0.8.0` by issue #257, on the operator's approval to move chip repos to
   the current klayout-tools release. It supersedes the "re-pin to a release once
   one carries #2959" note in move 7: 0.8.0 contains #2959, #3768 and #3769.

   Issue #260 (2026-10-28) then used #3768: `manifests/gf180-usb2-phy.json`
   declares its item-5 rows under `spec_rows."5.analog"`, so 5.digital is no
   longer charged with the analog rows (no `5.digital` rows are declared;
   spec §8.2 ratifies none). It then rendered `unmet`: klt 0.8.0 wants a
   `functional-verification` citation beside the `sta` one. Issue #295 added
   those citations (record `20261020-033000-4be8f5b`) and 5.digital is `met`.

10. Release `0.8.0` → release `0.9.0` by issue #263, once 0.9.0 (on PyPI; 0.9.1 is
   also out) carried klayout-tools#4666: `klt gen res_array` snaps `length_um`
   to the manufacturing grid and refuses a length below the deck's `sab.width.1`
   floor unless `params.short_length` is `lengthen`, reporting the realised
   length in `drc_hints.length_snap`. `dplus_pullup` is now regenerated from the
   netlist lengths with no `length_um` override (only `short_length: "lengthen"`
   on `r_seg0`), and the realised lengths equal those hand-set by DR-0010. The
   other three child-A blocks are geometrically identical to their 0.8.0 GDS
   (per-layer XOR, zero area difference) but not byte-identical, so their
   `gds_sha256` values in `layout/analog/provenance.json` moved. See
   `verification/records/analog-layout/` for the record.

`npm run check:ci` was re-run against each new pin before it was committed.
