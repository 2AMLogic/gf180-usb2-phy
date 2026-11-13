# Work plan

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

_None._

## Important

`loom:important`; taken before unlabelled work.

- **#245**: T1 item 2 (Layout, analog partition): route the five analog front-end blocks and commit their GDS
- **#252**: T1 item 2 (analog) B: route differential_driver GDS and attest 2.analog

## Ready

Human-approved issues ready for implementation (`loom:issue`).

_None._

## In Progress

Issues currently being built (`loom:building`).

_None._

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#51**: [Epic #542] 3A — gf180-usb2-phy maturation + Challenge #5 brief *(curated)*
- **#53**: Post-layout (extracted-parasitic) re-verification: digital STA now, analog PVT after #52 *(curated)*
- **#126**: Resolve DR-0003: transition-resynchronized RX oversampling for independent host clocks *(curated)*

## Proposed (Architect / Hermit)

- **#126**: Resolve DR-0003: transition-resynchronized RX oversampling for independent host clocks *(architect)*
- **#319**: Remove klt uri-scheme preflight probe from sim/harness/evidence_store.py: release pin makes it always pass *(hermit)*
- **#320**: Fold flow/request-usb-utmi-phy-par-sdf.json into request-usb-utmi-phy-par.json: 71-line unguarded duplicate *(hermit)*
- **#331**: Remove filtered-SDF workaround request from verification/: pinned klt 0.9.0 annotates the exported SDF (111/111) *(hermit)*

## Epics

- **#3**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers)

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 0 |
| Important | 2 |
| Ready (`loom:issue`) | 0 |
| In Progress (`loom:building`) | 0 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 0 |
| Curated | 3 |
| Architect / Hermit proposals | 4 |
| Active epics | 1 |
<!-- guide:plan-body:end -->
