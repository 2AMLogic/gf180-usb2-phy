# DR-0007 — Retire the bootstrap `harness_counter` smoke vehicle

- **Status**: Proposed (prepared under the operator's 2026-10-19 ruling on
  issue #207, option 1: prepare a *conditional* retirement. Normal
  decision-record review and merge gates apply; this PR does not
  self-ratify.)
- **Date**: 2026-10-20
- **Raised by**: Builder agent, issue #207
- **Amends**: DR-0002 Decision 4's disposition of `rtl/harness_counter.v`
  ("kept, in-tree, as harness mechanics"). DR-0002 is left unedited as
  history. This record is the current statement for the counter.
- **Does not change**: the ratified spec, the UTMI port set, any PHY RTL,
  the vendored bytes under `rtl/common/` or `reuse.lock.json`, the shared
  RTL and reuse contract, or the full-speed-only, device-only,
  UTMI-boundary-only scope. No physical-design campaign is authorized or
  run.

## Context

`rtl/harness_counter.v` was a parameterized up-counter with zero USB
semantics, added in issue #7 to prove the cocotb + Icarus + `klt` harness
and the `klt synthesize` flow end-to-end before any PHY logic existed. DR-0002
kept it as harness mechanics. Since then twelve real-PHY
`klt functional-verification` requests (`package.json` `test`) and the PHY
synthesis recipe `flow/request-usb-utmi-phy-synth.json` have run the same
tool paths on real designs, and the counter is the only RTL in the tree that
is not PHY logic.

The counter is also pinned by two live evidence records (the unsuperseded
`functional-smoke` and `synthesis-smoke` records of 2026-08-10), so removing
it without a supersession would fail `verification/check_records.py`. The
records are append-only evidence and are not edited or deleted.

## Decision

Retire the counter, conditionally on replacement coverage and evidence
continuity both being established in the same PR. Both were.

1. **Removed**: `rtl/harness_counter.v`, `verification/test_harness_counter.py`,
   `verification/request-harness-counter.json`,
   `flow/request-harness-counter-synth.json`, and their wiring and docs.
   `package.json` `test` drops the counter request; `check:all` now runs
   `klt synthesize flow/request-usb-utmi-phy-synth.json`.
2. **Evidence continuity** (no history touched; every pre-existing path under
   `verification/records/` is byte-identical to `origin/main`):
   - `functional-smoke`: new record `20261020-033000-4be8f5b` supersedes
     `20260810-205021-c819c95`. It **is a measured run**: the twelve
     surviving requests were run once each with the pinned klt, 12/12 PASS,
     178 tests, envelopes archived. It claims the harness works on real
     designs. It does not claim the counter still passes.
   - `synthesis-smoke`: new record `20261020-033001-4be8f5b` supersedes
     `20260810-205021-c819c95`. It **is bookkeeping only, with no new
     measured run**: results are carried by the existing real-PHY record
     `20261015-011500-32db02a` (330 instances, 12782.6496 um2).
   - The superseded records stay in the tree with their artifacts. Their
     provenance hashes can no longer be recomputed because their inputs are
     removed; the checker exempts superseded records by design.
3. **Sampling guidance preserved**: the "drive on `FallingEdge`, read
   registered outputs on the following `FallingEdge`" discipline, which the
   counter's testbench introduced and other testbenches cite, now lives in
   `verification/README.md`. Four testbench docstrings were reworded to state
   it directly. Three (`test_usb_sync_detector.py`, `test_usb_eop_detector.py`,
   `test_usb_line_state_decode.py`) are deliberately left with the stale
   cross-reference because live records pin their content hashes; the README
   paragraph explains this.

## Coverage mapping (an argument, not a measurement)

| Counter test | What it checked | Surviving coverage |
|---|---|---|
| `test_reset_holds_zero` | reset drives a known state | `test_reset_state` and `test_reset_is_quiescent`, and the `test_rx_utmi_reset_*` / `test_tx_utmi_reset_*` families in `test_usb_utmi_phy.py` |
| `test_disabled_holds_value` | state holds while not enabled | `test_disabled_is_transparent_and_never_errors` (`usb_bit_destuffer`), `test_disabled_never_matches` and `test_data_valid_gap_holds_match_state` (`usb_sync_detector`) |
| `test_counts_and_wraps` | 500-case seeded random check against a Python model | `test_random_stream_matches_model` (`usb_bit_stuffer`), `test_enabled_destuffing_matches_model` (`usb_bit_destuffer`), `test_usb_bit_codec_loopback.py`, `test_tolerance_matrix` |
| (synthesis) | Yosys + abc map a design to gf180mcu | `flow/request-usb-utmi-phy-synth.json`, record `20261015-011500-32db02a` |

## What this does not claim

- **No diagnostic equivalence.** A 3-test counter localised a broken
  *harness* in seconds; a 111-test PHY suite localises it less sharply. The
  counter's value as a minimal bring-up canary is given up deliberately, not
  shown to be unneeded. A future harness break is diagnosed from the PHY
  suites plus the toolchain version, as every post-bootstrap break was.
- **No measured runtime improvement.** One short invocation is removed from
  `npm run test` and `check:all`. No before/after timing was taken.
- **No spec relaxation.** Nothing ratified changed.

## Alternatives considered

- **Keep the counter** (DR-0002's disposition): costs a non-PHY RTL file, two
  requests and a testbench in a block whose scope discipline is "finished and
  verified, not general". Remains the right call if this PR's review finds the
  coverage argument unconvincing; reverting this PR restores it.
- **Retire with a WORK_LOG note only**: rejected. The checker would fail on
  the live 2026-08-10 records, and the history requires an explicit
  supersession rather than a note.
- **Re-mint the three `utmi-framing-functional` heads to allow docstring edits
  in their pinned testbenches**: rejected as churn for zero behaviour change.
