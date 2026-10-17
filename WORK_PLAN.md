# Work plan

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#154**: feat(analog): TXOE high-Z enable for differential_driver (#114)
- **#171**: ci: cancel in-progress runs only for pull_request events

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

_None._

## Important

`loom:important`; taken before unlabelled work.

- **#114**: Analog: add TXOE high-Z enable to differential_driver (pin contract, #109)
- **#166**: Re-check driver layout plan and regenerate netlist after #96 re-size
- **#167**: driver layout plan cannot ingest m=4 netlist: decide how output-stage multiplicity reaches layout

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#114**: Analog: add TXOE high-Z enable to differential_driver (pin contract, #109)

## In Progress

Issues currently being built (`loom:building`).

_None._

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#154**: feat(analog): TXOE high-Z enable for differential_driver (#114)
- **#171**: ci: cancel in-progress runs only for pull_request events

## Proposed

Issues carrying `loom:curated`.

- **#51**: [Epic #542] 3A — gf180-usb2-phy maturation + Challenge #5 brief *(curated)*
- **#53**: Post-layout (extracted-parasitic) re-verification: digital STA now, analog PVT after #52 *(curated)*
- **#114**: Analog: add TXOE high-Z enable to differential_driver (pin contract, #109) *(curated)*
- **#166**: Re-check driver layout plan and regenerate netlist after #96 re-size *(curated)*
- **#167**: driver layout plan cannot ingest m=4 netlist: decide how output-stage multiplicity reaches layout *(curated)*

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
| Important | 3 |
| Ready (`loom:issue`) | 1 |
| In Progress (`loom:building`) | 0 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 2 |
| Curated | 5 |
| Architect / Hermit proposals | 2 |
| Active epics | 1 |
<!-- guide:plan-body:end -->
