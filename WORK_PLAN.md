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

- **#53**: Post-layout (extracted-parasitic) re-verification: digital STA now, analog PVT after #52
- **#246**: T1 item 3 (DRC clean, analog partition): klt drc on the committed analog GDS with coverage disclosed
- **#249**: T1 item 5 (Full corner verification): propose a spec 8.2 driver-jitter decision record so 5.analog's declared gap can close
- **#392**: Frozen digital-lvs record no longer reproduces on main under repo-pin klt 0.9.0 (power_connectivity VNW/VPW well-pin derivation)

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#419**: check_signoff_report.py's 5-diff cap hides graded-content divergences behind klt build-stamp drift
- **#420**: T1 item 8's envelope pins a content hash that matches no revision of docs/characterization-report.md, and nothing checks it
- **#422**: docs: layout/README.md states an unsupported differential_driver bbox height (83.88 vs 103.205 measured); one residual "no ERC" clause in challenge-5-proposal.md

## In Progress

Issues currently being built (`loom:building`).

- **#415**: docs: six passages still cite the superseded analog-erc record 20261114-003000-db05b5e as current (item 11.analog + four files)

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
- **#392**: Frozen digital-lvs record no longer reproduces on main under repo-pin klt 0.9.0 (power_connectivity VNW/VPW well-pin derivation) *(curated)*
- **#415**: docs: six passages still cite the superseded analog-erc record 20261114-003000-db05b5e as current (item 11.analog + four files) *(curated)*
- **#419**: check_signoff_report.py's 5-diff cap hides graded-content divergences behind klt build-stamp drift *(curated)*
- **#420**: T1 item 8's envelope pins a content hash that matches no revision of docs/characterization-report.md, and nothing checks it *(curated)*
- **#422**: docs: layout/README.md states an unsupported differential_driver bbox height (83.88 vs 103.205 measured); one residual "no ERC" clause in challenge-5-proposal.md *(curated)*

## Proposed (Architect / Hermit)

- **#126**: Resolve DR-0003: transition-resynchronized RX oversampling for independent host clocks *(architect)*
- **#319**: Remove klt uri-scheme preflight probe from sim/harness/evidence_store.py: release pin makes it always pass *(hermit)*
- **#320**: Fold flow/request-usb-utmi-phy-par-sdf.json into request-usb-utmi-phy-par.json: 71-line unguarded duplicate *(hermit)*
- **#331**: Remove filtered-SDF workaround request from verification/: pinned klt 0.9.0 annotates the exported SDF (111/111) *(hermit)*
- **#339**: Merge se_receiver_dp and se_receiver_dm into one se_receiver cell: same circuit, byte-identical layout, identical PVT results *(hermit)*
- **#344**: Remove origin-snap workaround from scripts/gen_analog_layout.py: pinned klt 0.9.0 places group origins on-grid (0 instances snapped in every 0.9.0 run) *(hermit)*
- **#350**: Fold verification/test_usb_utmi_txoe.py into test_usb_utmi_phy.py: its stated reason (routed netlist has no txoe port) ended at #131 *(hermit)*
- **#360**: Remove the inert ciel-symlink mount block from scripts/openroad-docker.sh: the guard never fires, and the mount it adds is the wrong path *(hermit)*
- **#364**: Migrate the 84.7 MB pre-#347 driver-jitter corner logs out of git: 95% blank table rows, 45% of the repo *(hermit)*
- **#372**: Split scripts/gen_analog_layout.py: extract the 335-LOC scripted-routing layer, delete the dead BULK_TERMINAL constant *(hermit)*
- **#380**: Deduplicate the byte-identical sh/sha256/discover_blocks helpers shared by scripts/analog_erc.py and scripts/analog_lvs.py *(hermit)*
- **#385**: Wire scripts/test_analog_lvs.py into npm run lint: the only self-test in the repo CI never runs *(hermit)*

## Epics

- **#3**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers)

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 0 |
| Important | 4 |
| Ready (`loom:issue`) | 3 |
| In Progress (`loom:building`) | 1 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 0 |
| Curated | 8 |
| Architect / Hermit proposals | 12 |
| Active epics | 1 |
<!-- guide:plan-body:end -->
