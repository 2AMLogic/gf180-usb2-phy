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

- **#246**: T1 item 3 (DRC clean, analog partition): klt drc on the committed analog GDS with coverage disclosed
- **#247**: T1 item 4 (LVS clean, analog partition): klt lvs of each analog block against its schematic netlist

## Ready

Human-approved issues ready for implementation (`loom:issue`).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#247**: T1 item 4 (LVS clean, analog partition): klt lvs of each analog block against its schematic netlist
- **#347**: Stop tabulating 8-element vectors against the time scale in sim/driver-jitter/testbench/tb.json: 98% of each corner log is blank rows (~89 MB per run)

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#356**: chore(sim): print driver-jitter dev/cons element-wise instead of tabulating them

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#354**: feat(signoff): cite the five analog LVS matches as T1 item 4.analog

## Proposed

Issues carrying `loom:curated`.

- **#51**: [Epic #542] 3A — gf180-usb2-phy maturation + Challenge #5 brief *(curated)*
- **#53**: Post-layout (extracted-parasitic) re-verification: digital STA now, analog PVT after #52 *(curated)*
- **#126**: Resolve DR-0003: transition-resynchronized RX oversampling for independent host clocks *(curated)*
- **#247**: T1 item 4 (LVS clean, analog partition): klt lvs of each analog block against its schematic netlist *(curated)*

## Proposed (Architect / Hermit)

- **#126**: Resolve DR-0003: transition-resynchronized RX oversampling for independent host clocks *(architect)*
- **#319**: Remove klt uri-scheme preflight probe from sim/harness/evidence_store.py: release pin makes it always pass *(hermit)*
- **#320**: Fold flow/request-usb-utmi-phy-par-sdf.json into request-usb-utmi-phy-par.json: 71-line unguarded duplicate *(hermit)*
- **#331**: Remove filtered-SDF workaround request from verification/: pinned klt 0.9.0 annotates the exported SDF (111/111) *(hermit)*
- **#339**: Merge se_receiver_dp and se_receiver_dm into one se_receiver cell: same circuit, byte-identical layout, identical PVT results *(hermit)*
- **#344**: Remove origin-snap workaround from scripts/gen_analog_layout.py: pinned klt 0.9.0 places group origins on-grid (0 instances snapped in every 0.9.0 run) *(hermit)*
- **#350**: Fold verification/test_usb_utmi_txoe.py into test_usb_utmi_phy.py: its stated reason (routed netlist has no txoe port) ended at #131 *(hermit)*

## Epics

- **#3**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers)

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 0 |
| Important | 2 |
| Ready (`loom:issue`) | 0 |
| In Progress (`loom:building`) | 2 |
| PRs awaiting review | 1 |
| Approved PRs awaiting merge | 1 |
| Curated | 4 |
| Architect / Hermit proposals | 7 |
| Active epics | 1 |
<!-- guide:plan-body:end -->
