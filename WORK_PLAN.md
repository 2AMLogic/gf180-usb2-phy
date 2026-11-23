# Work plan

<!-- guide:plan-body:start -->
_Generated: 2026-11-21T05:39:51Z (snapshot; compare against live labels)_
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#484**: differential_driver fails spec section 6 timing post-layout: cut the output-path Metal1 series resistance in the committed routing *(held)*

## Important

`loom:important`; taken before unlabelled work.

- **#53**: Post-layout (extracted-parasitic) re-verification: digital STA now, analog PVT after #52 *(held)*
- **#246**: T1 item 3 (DRC clean, analog partition): klt drc on the committed analog GDS with coverage disclosed *(held)*
- **#249**: T1 item 5 (Full corner verification): propose a spec 8.2 driver-jitter decision record so 5.analog's declared gap can close *(held)*

## Ready

Human-approved issues (`loom:issue`) ready for implementation — excluding held (`loom:blocked`/`loom:operator`/`loom:frozen`), `loom:building`, and issues closed by an open `loom:pr` PR (listed under Approved).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#339**: Merge se_receiver_dp and se_receiver_dm into one se_receiver cell: same circuit, byte-identical layout, identical PVT results
- **#483**: Move the klayout-tools pin 0.9.0 -> 0.9.2 and re-render the signoff report (pin precondition of #246, T1 item 3.analog)

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#490**: chore: pin klayout-tools 0.9.2 and re-measure analog evidence at the new pin

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#51**: [Epic #542] 3A — gf180-usb2-phy maturation + Challenge #5 brief *(curated)* *(held)*
- **#53**: Post-layout (extracted-parasitic) re-verification: digital STA now, analog PVT after #52 *(curated)* *(held)*
- **#126**: Resolve DR-0003: transition-resynchronized RX oversampling for independent host clocks *(curated)* *(held)*
- **#339**: Merge se_receiver_dp and se_receiver_dm into one se_receiver cell: same circuit, byte-identical layout, identical PVT results *(curated)*
- **#483**: Move the klayout-tools pin 0.9.0 -> 0.9.2 and re-render the signoff report (pin precondition of #246, T1 item 3.analog) *(curated)*
- **#484**: differential_driver fails spec section 6 timing post-layout: cut the output-path Metal1 series resistance in the committed routing *(curated)* *(held)*

## Proposed (Architect / Hermit)

- **#126**: Resolve DR-0003: transition-resynchronized RX oversampling for independent host clocks *(architect)* *(held)*
- **#320**: Fold flow/request-usb-utmi-phy-par-sdf.json into request-usb-utmi-phy-par.json: 71-line unguarded duplicate *(hermit)* *(held)*
- **#339**: Merge se_receiver_dp and se_receiver_dm into one se_receiver cell: same circuit, byte-identical layout, identical PVT results *(hermit)*
- **#350**: Fold verification/test_usb_utmi_txoe.py into test_usb_utmi_phy.py: its stated reason (routed netlist has no txoe port) ended at #131 *(hermit)* *(held)*
- **#486**: Remove the executable fallback when the repository klt version pin is missing *(hermit)* *(held)*
- **#488**: Keep routing-method counts for single-method analog layouts *(hermit)* *(held)*

## Epics

- **#3**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers) *(held)*

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 1 |
| Important | 3 |
| Ready (`loom:issue`, net of holds/building/merge-pending) | 0 |
| In Progress (`loom:building`) | 2 |
| PRs awaiting review | 1 |
| Approved PRs awaiting merge | 0 |
| Curated | 6 |
| Architect / Hermit proposals | 6 |
| Active epics | 1 |
<!-- guide:plan-body:end -->
