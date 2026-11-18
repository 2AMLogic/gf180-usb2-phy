# Work plan

<!-- guide:plan-body:start -->
_Generated: 2026-11-18T22:15:38Z (snapshot; compare against live labels)_
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

_None._

## Important

`loom:important`; taken before unlabelled work.

- **#53**: Post-layout (extracted-parasitic) re-verification: digital STA now, analog PVT after #52 *(held)*
- **#246**: T1 item 3 (DRC clean, analog partition): klt drc on the committed analog GDS with coverage disclosed *(held)*
- **#249**: T1 item 5 (Full corner verification): propose a spec 8.2 driver-jitter decision record so 5.analog's declared gap can close *(held)*

## Ready

Human-approved issues (`loom:issue`) ready for implementation — excluding held (`loom:blocked`/`loom:operator`/`loom:frozen`), `loom:building`, and issues closed by an open `loom:pr` PR (listed under Approved).

- **#51**: [Epic #542] 3A — gf180-usb2-phy maturation + Challenge #5 brief
- **#319**: Remove klt uri-scheme preflight probe from sim/harness/evidence_store.py: release pin makes it always pass

## In Progress

Issues currently being built (`loom:building`).

- **#339**: Merge se_receiver_dp and se_receiver_dm into one se_receiver cell: same circuit, byte-identical layout, identical PVT results
- **#364**: Migrate the 84.7 MB pre-#347 driver-jitter corner logs out of git: 95% blank table rows, 45% of the repo
- **#372**: Split scripts/gen_analog_layout.py: extract the 335-LOC scripted-routing layer, delete the dead BULK_TERMINAL constant
- **#381**: Operator ruling: resolve the duplicate DR-0007 allocation in spec/decisions/ (renumber the analog record to DR-0011, or keep the documented exemption)
- **#458**: Origin on-grid check: no coverage for mirrored/rotated or array instances

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#51**: [Epic #542] 3A — gf180-usb2-phy maturation + Challenge #5 brief *(curated)*
- **#53**: Post-layout (extracted-parasitic) re-verification: digital STA now, analog PVT after #52 *(curated)* *(held)*
- **#126**: Resolve DR-0003: transition-resynchronized RX oversampling for independent host clocks *(curated)* *(held)*
- **#319**: Remove klt uri-scheme preflight probe from sim/harness/evidence_store.py: release pin makes it always pass *(curated)*
- **#339**: Merge se_receiver_dp and se_receiver_dm into one se_receiver cell: same circuit, byte-identical layout, identical PVT results *(curated)*
- **#364**: Migrate the 84.7 MB pre-#347 driver-jitter corner logs out of git: 95% blank table rows, 45% of the repo *(curated)*
- **#372**: Split scripts/gen_analog_layout.py: extract the 335-LOC scripted-routing layer, delete the dead BULK_TERMINAL constant *(curated)*
- **#381**: Operator ruling: resolve the duplicate DR-0007 allocation in spec/decisions/ (renumber the analog record to DR-0011, or keep the documented exemption) *(curated)*
- **#458**: Origin on-grid check: no coverage for mirrored/rotated or array instances *(curated)*

## Proposed (Architect / Hermit)

- **#126**: Resolve DR-0003: transition-resynchronized RX oversampling for independent host clocks *(architect)* *(held)*
- **#320**: Fold flow/request-usb-utmi-phy-par-sdf.json into request-usb-utmi-phy-par.json: 71-line unguarded duplicate *(hermit)* *(held)*
- **#339**: Merge se_receiver_dp and se_receiver_dm into one se_receiver cell: same circuit, byte-identical layout, identical PVT results *(hermit)*
- **#350**: Fold verification/test_usb_utmi_txoe.py into test_usb_utmi_phy.py: its stated reason (routed netlist has no txoe port) ended at #131 *(hermit)* *(held)*

## Epics

- **#3**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers) *(held)*

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 0 |
| Important | 3 |
| Ready (`loom:issue`, net of holds/building/merge-pending) | 2 |
| In Progress (`loom:building`) | 5 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 0 |
| Curated | 9 |
| Architect / Hermit proposals | 4 |
| Active epics | 1 |
<!-- guide:plan-body:end -->
