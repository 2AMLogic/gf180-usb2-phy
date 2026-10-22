# Work plan

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#190**: feat(signoff): cite artifact-anchored evidence for T1 items 1, 2.digital, 9, 10
- **#210**: chore: retire the bootstrap harness counter with explicit record supersession

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

_None._

## Important

`loom:important`; taken before unlabelled work.

- **#114**: Analog: add TXOE high-Z enable to differential_driver (pin contract, #109)
- **#166**: Re-check driver layout plan and regenerate netlist after #96 re-size
- **#167**: driver layout plan cannot ingest m=4 netlist: decide how output-stage multiplicity reaches layout
- **#187**: T1 items 1, 2 (digital), 9 and 10: cite artifact-anchored evidence now that klt signoff binds it

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#51**: [Epic #542] 3A — gf180-usb2-phy maturation + Challenge #5 brief

## In Progress

Issues currently being built (`loom:building`).

- **#207**: Remove harness_counter.v smoke vehicle: redundant with real PHY tests

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#190**: feat(signoff): cite artifact-anchored evidence for T1 items 1, 2.digital, 9, 10
- **#210**: chore: retire the bootstrap harness counter with explicit record supersession

## Proposed

Issues carrying `loom:curated`.

- **#51**: [Epic #542] 3A — gf180-usb2-phy maturation + Challenge #5 brief *(curated)*
- **#53**: Post-layout (extracted-parasitic) re-verification: digital STA now, analog PVT after #52 *(curated)*
- **#114**: Analog: add TXOE high-Z enable to differential_driver (pin contract, #109) *(curated)*
- **#166**: Re-check driver layout plan and regenerate netlist after #96 re-size *(curated)*
- **#167**: driver layout plan cannot ingest m=4 netlist: decide how output-stage multiplicity reaches layout *(curated)*
- **#187**: T1 items 1, 2 (digital), 9 and 10: cite artifact-anchored evidence now that klt signoff binds it *(curated)*
- **#189**: T1 item 6: the analog partition needs Monte Carlo evidence; record "not applicable" only for the digital partition *(curated)*
- **#212**: T1 item 6: single-ended receiver Monte Carlo request (klt_measure hooks + MC builder) *(curated)*

## Proposed (Architect / Hermit)

- **#119**: Verify shared-pad analog bus ownership and receiver transients *(architect)*
- **#126**: Resolve DR-0003: transition-resynchronized RX oversampling for independent host clocks *(architect)*

## Epics

- **#3**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers)

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 2 |
| Very important | 0 |
| Important | 4 |
| Ready (`loom:issue`) | 1 |
| In Progress (`loom:building`) | 1 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 2 |
| Curated | 8 |
| Architect / Hermit proposals | 2 |
| Active epics | 1 |
<!-- guide:plan-body:end -->
