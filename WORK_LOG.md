# Work log

Merged PRs and closed issues from the Guide’s 30-day maintenance window.

## Archives

- [2026-09](work_log/WORK_LOG_2026-09.md)

### 2026-11-19

- **PR #475**: fix(env): pin the klayout engine wheel (0.30.12) for the analog flow
- **Issue #472** (closed): gen_analog_layout --check does not reproduce committed gds_sha256 pins
- **Issue #372** (closed): Split scripts/gen_analog_layout.py: extract the scripted-routing layer
- **PR #473**: refactor(analog): extract scripted-routing layer into gen_analog_routing.py, drop dead BULK_TERMINAL
- **Issue #474** (closed): Repair the mid-sentence docstring split left by the gen_analog_routing extraction
- **PR #468**: refactor(sim): remove the klt uri-scheme preflight probe
- **Issue #319** (closed): Remove klt uri-scheme preflight probe from sim/harness/evidence_store.py: release pin makes it always pass

### 2026-11-18

- **PR #466**: evidence: move driver-jitter 20260817 raw logs to artifact store (DR-0008 A1)
- **PR #465**: layout: check array repetitions in origin on-grid assertion; add rotated/mirrored/array tests
- **PR #460**: docs: renumber analog-statistical-rows record to DR-0011 and drop the DR-0007 exemption
- **Issue #458** (closed): Origin on-grid check: no coverage for mirrored/rotated or array instances
- **Issue #381** (closed): Operator ruling: resolve the duplicate DR-0007 allocation in spec/decisions/ (renumber the analog record to DR-0011, or keep the documented exemption)
- **Issue #364** (closed): Migrate the 84.7 MB pre-#347 driver-jitter corner logs out of git: 95% blank table rows, 45% of the repo
- **PR #459**: verification: retire filtered slow-corner SDF, cite as-exported SDF for item 7.digital
- **PR #454**: refactor: replace analog-layout origin snap with a fail-on-off-grid check
- **Issue #344** (closed): Remove origin-snap workaround from scripts/gen_analog_layout.py: pinned klt 0.9.0 places group origins on-grid (0 instances snapped in every 0.9.0 run)
- **Issue #331** (closed): Remove filtered-SDF workaround request from verification/: pinned klt 0.9.0 annotates the exported SDF (111/111)
- **PR #456**: test: pin full key set of the analog-LVS request
- **PR #455**: fix: bind-mount out-of-tree PDK symlink target in openroad-docker.sh
- **Issue #453** (closed): Prove the analog-LVS anti-relaxation guard goes red on a relaxing option
- **Issue #385** (closed): Wire scripts/test_analog_lvs.py into npm run lint: the only self-test in the repo CI never runs
- **Issue #360** (closed): Repair the ciel-symlink mount block in scripts/openroad-docker.sh: mount REAL_TARGET and fix the comment
- **PR #450**: refactor: share the analog harness helpers in scripts/analog_common.py
- **Issue #380** (closed): Deduplicate the byte-identical sh/sha256/discover_blocks helpers shared by scripts/analog_erc.py and scripts/analog_lvs.py
- **Issue #392** (closed): Frozen digital-lvs record no longer reproduces on main under repo-pin klt 0.9.0 (power_connectivity VNW/VPW well-pin derivation)

### 2026-11-17

- **PR #445**: fix: partition signoff-report divergences by build stamp vs graded content
- **Issue #419** (closed): check_signoff_report.py's 5-diff cap hides graded-content divergences behind klt build-stamp drift
- **PR #443**: fix(signoff): bind item 8's envelope to the report by path and live hash
- **Issue #420** (closed): T1 item 8's envelope pins a content hash that matches no revision of docs/characterization-report.md, and nothing checks it
- **PR #440**: fix: version-gate lvs/extract reports and the npm klt path
- **Issue #438** (closed): Close the rest of the klt-pin class: version-gate analog_lvs/digital_lvs reports and the bare-klt npm scripts
- **PR #433**: fix(harness): resolve klt from the interpreter and gate report versions against the pin
- **Issue #431** (closed): Harden harnesses that resolve klt from $PATH: pin the interpreter's klt and gate the report's embedded version
- **PR #436**: fix: correct rise-crossover failing-corner count in spec-coverage provenance summary
- **Issue #434** (closed): sim/spec-coverage.md: rise-crossover failing-corner count is 16 in the provenance summary, 15 in the row and the record
- **PR #432**: feat(analog): extracted-netlist 45-corner PVT re-verification of all five analog blocks
- **PR #430**: fix(layout): measure bbox_um from the stream gds_path names
- **Issue #427** (closed): analog-layout-report.json bbox_um does not describe the committed stream it is paired with (y-extent only; x matches)

### 2026-11-16

- **PR #418**: docs: re-point superseded analog-erc/analog-lvs record citations to the live head records
- **Issue #415** (closed): docs: six passages still cite the superseded analog-erc record 20261114-003000-db05b5e as current (item 11.analog + four files)
- **PR #426**: docs: correct differential_driver stream extent and ERC wording
- **Issue #422** (closed): docs: layout/README.md states an unsupported differential_driver bbox height (83.88 vs 103.205 measured); one residual "no ERC" clause in challenge-5-proposal.md
- **PR #424**: fix: drop dead __main__ block left by unittest conversion and rebind evidence
- **Issue #407** (closed): verification/test_check_records.py carries a dead `if __name__ == "__main__": sys.exit(main())` block after the unittest conversion
- **PR #421**: docs: re-point analog-layout citations to the 8dff986 head and retire the stale no-ERC clauses
- **Issue #417** (closed): docs: analog-layout prose cites the superseded 162700 record; adjacent prose still says "no ERC result"
- **PR #416**: docs: settle the stored-evidence signoff deferral with the measured klt signoff determination
- **PR #414**: docs: re-point analog LVS/extraction prose and item 4.analog citation to the superseding records
- **PR #413**: check: assert GDS marker-cell count equals measured resistor count
- **Issue #412** (closed): Establish at runtime whether klt signoff can re-hash a manifest-backed (artifact:) citation, and file the gap upstream
- **Issue #411** (closed): docs: five more files still cite the pre-#361 analog-lvs record as current state (layout/README, README, characterization-report, spec-coverage, challenge-5 proposal)
- **PR #410**: fix: measure the analog body strap's inputs instead of asserting them
- **PR #409**: docs: state the live 7.analog gap; date the klt-only analog-layout claims
- **Issue #408** (closed): docs: analog-lvs / analog-extraction entries and item 4.analog citation still describe the pre-#361 records
- **Issue #406** (closed): Analog body strap: the collision model is a per-block snapshot and the pad size is a hand-measured constant
- **Issue #402** (closed): check_analog_resistor_dims: assert GDS marker-cell count equals the measured device count, so a resistor outside the plan/netlist join cannot go unmeasured
- **PR #400**: fix: replace unusable layout/digital evidence recipe, parameterise stored-evidence citation
- **PR #398**: test: convert hand-rolled case-table self-test runners to unittest
- **Issue #395** (closed): sim/README.md's manual klt artifact put recipe is unusable for the one tree it now addresses
- **Issue #382** (closed): Make a zero-test scripts/test_*.py module loud: unittest discover hides a hand-rolled runner it collects nothing from
- **Issue #371** (closed): docs: manifests/README.md and verification/README.md still say no analog layout exists

### 2026-11-15

- **PR #404**: feat(analog): strap every drawn body-tie pad to its body net; ERC partition to pad granularity
- **PR #403**: fix(lvs): resolve the digital abstraction from in-cell labels only, restore the full-pass LVS verdict
- **PR #367**: docs: roadmap as of 2026-11-13
- **Issue #361** (closed): Analog body-tie pads: only one pad per device group is wired to the rail; the rest are tied through the substrate alone
- **PR #399**: check: compare drawn analog resistor L/W against the netlists outside LVS
- **Issue #370** (closed): Check drawn poly-resistor dimensions in the five analog streams against design/netlist, since LVS compares none
- **PR #383**: refactor: drop unused klt_version() probe and two unused imports in sim/harness
- **Issue #373** (closed): Remove three dead symbols in sim/harness: klt_version() and two unused imports
- **Issue #397** (closed): digital_lvs.py picks the abstract-cell LEF by filesystem walk order, not by the declared PDK variant
- **PR #393**: refactor: drop the unused instance-parsing half of digital_lvs parse_verilog
- **Issue #389** (closed): Remove the unused instance-parsing half of digital_lvs.py's parse_verilog()
- **PR #377**: ci: drop two workflow steps that repeat commands check:ci already ran
- **Issue #359** (closed): Remove two CI steps that re-run commands npm run check:ci already ran: neither can ever fail
- **PR #394**: refactor: one record per T1 item in signoff/inventories.py
- **Issue #384** (closed): Collapse the five parallel T1-item tables in signoff/inventories.py into one record per item: a missing ITEM_ENVELOPES entry is written but never verified
- **PR #391**: evidence: standalone klt drc records for the five analog streams, coverage quoted verbatim
- **Issue #368** (closed): Record standalone klt drc reports for the five committed analog streams, with the coverage block quoted
- **PR #388**: feat: store verification-record artifacts by manifest instead of in git
- **Issue #366** (closed): Stop committing verification/records artifact bytes: 629 blobs, 40% of the repo, DR-0008's own named follow-up
- **PR #387**: feat: check spec §12.1's decision-record index against spec/decisions/
- **Issue #378** (closed): Remove the hand-maintained DR index in spec §12.1: drifted to 3 of 11 and let DR-0007 be allocated twice

### 2026-11-14

- **PR #390**: evidence: probe klt --parasitics extraction of differential_receiver.gds for an ngspice re-run
- **Issue #369** (closed): Probe parasitic extraction of differential_receiver.gds for an ngspice re-run and record what the pinned klt can do
- **PR #379**: refactor: move the shared Monte Carlo request code into sim/harness/mc_requests.py
- **Issue #376** (closed): Remove the importlib path-load between the two Monte Carlo builders: move the shared request code into sim/harness/
- **PR #374**: build: discover scripts/ unittest modules in lint instead of listing them
- **Issue #365** (closed): Collapse four hand-enumerated scripts/ test steps in npm run lint into one unittest discover (scripts/test_analog_lvs.py has been silently never-run)
- **PR #363**: feat(analog): add per-stream klt erc supply specs and cite 11.analog
- **Issue #248** (closed): T1 item 11 (Power delivery, analog partition): analog klt erc supply spec plus LVS supply pairing
- **PR #358**: docs: state the five analog LVS matches and the committed driver layout
- **Issue #355** (closed): docs: challenge-5 proposal still says no analog block has an LVS match or a committed driver layout
- **PR #356**: chore(sim): print driver-jitter dev/cons element-wise instead of tabulating them
- **Issue #347** (closed): Stop tabulating 8-element vectors against the time scale in sim/driver-jitter/testbench/tb.json: 98% of each corner log is blank rows (~89 MB per run)

### 2026-11-13

- **PR #354**: feat(signoff): cite the five analog LVS matches as T1 item 4.analog
- **Issue #247** (closed): T1 item 4 (LVS clean, analog partition): klt lvs of each analog block against its schematic netlist
- **PR #351**: fix(layout): tie every device body and label the schematic's ports
- **Issue #346** (closed): Analog LVS: all five committed streams mismatch — untied n-wells, untied substrate, and a wrong labelled port set
- **PR #348**: feat(verification): add analog LVS harness and record the five-block mismatch
- **Issue #345** (closed): Analog LVS harness and first record: scripts/analog_lvs.py over the five committed streams (all five mismatch today)
- **PR #340**: refactor(sim): build Monte Carlo measurements with the harness's own mapper
- **Issue #333** (closed): Reuse harness klt_measure limits logic in sim/diff-receiver-mc/build_requests.py: second copy already drifted once
- **PR #342**: docs(verification): replace per-test case lists in README Contents with file/DUT/caveat entries
- **Issue #334** (closed): Trim per-test prose in verification/README.md Contents: restates testbench docstrings, omits 9 of 23 usb_utmi_phy tests
- **PR #341**: chore(sim): drop the hand-written klt sim decks from both driver benches
- **Issue #337** (closed): Remove hand-written klt sim decks from the two driver benches: superseded by the harness decks transport, no live consumer
- **PR #338**: fix(layout): run each analog layout plan in its own process
- **Issue #335** (closed): bug(layout): dplus_pullup.gds does not reproduce from its recorded regeneration command (geometrically identical, byte order differs)
- **PR #336**: feat(layout): route and commit differential_driver GDS, cite T1 item 2.analog
- **Issue #252** (closed): T1 item 2 (analog) B: route differential_driver GDS and attest 2.analog
- **Issue #245** (closed): T1 item 2 (Layout, analog partition): route the five analog front-end blocks and commit their GDS
- **PR #330**: docs(env): move the klt pin-move history to docs/klt-pin-history.md
- **Issue #327** (closed): Split docs/environment-setup.md: move 220 lines of klt pin-move history into a sibling history file
- **PR #329**: docs(verification): replace per-request command list with one example
- **Issue #328** (closed): Remove hand-copied request list from verification/README.md: drifted from package.json test script (10 of 12)
- **PR #325**: docs(layout): move the dated klt-only analog narrative to analog/HISTORY.md
- **Issue #323** (closed): Split layout/README.md: move 615 lines of dated analog-routing history into a sibling history file
- **PR #326**: refactor(sim): share one deck assembler between both receiver MC builders
- **Issue #322** (closed): Remove copied build_deck() and dead DEGRADED_OFFSET_V from sim/se-receiver-mc/build_requests.py
- **PR #316**: refactor(sim): drop unused write_record, test append-only on the live writer
- **Issue #312** (closed): Remove dead write_record() from sim/harness/report.py: superseded by evidence_store.store_files
- **PR #324**: docs(layout): date the klt pin in the two pin-relative README sentences
- **Issue #321** (closed): docs(layout): README line 125 says the repo pins klt 0.8.0; the pin is 0.9.0
- **PR #318**: docs(layout): state the committed analog streams in the current-state paragraph
- **Issue #315** (closed): layout/README.md "Current state in one paragraph" contradicts the committed analog layout
- **PR #317**: chore(lint): discover sim/tests self-tests instead of listing them by name
- **Issue #313** (closed): Replace hand-listed sim/tests entries in npm run lint with unittest discovery
- **PR #314**: docs(chipalooza): correct analog layout status in the Challenge #5 proposal
- **PR #311**: fix(layout): regenerate driver layout plan against current netlist
- **Issue #166** (closed): Re-check driver layout plan and regenerate netlist after #96 re-size
- **Issue #167** (closed): driver layout plan cannot ingest m=4 netlist: decide how output-stage multiplicity reaches layout

### 2026-11-12

- **PR #308**: Bump Repo Skills 0.25.10 -> 0.26.1

### 2026-11-07

- **PR #306**: ci: check analog provenance sidecar hashes offline
- **Issue #305** (closed): CI: check layout/analog/provenance.json hashes against committed GDS, netlists and plans
- **PR #301**: Bump Repo Skills 0.25.1 -> 0.25.10

### 2026-11-06

- **PR #297**: feat(sim): shared-pad-bus experiment for host/device ownership on shared DP/DM
- **Issue #119** (closed): Verify shared-pad analog bus ownership and receiver transients
- **PR #298**: docs: require claim replay before freezing evidence records
- **Issue #101** (closed): Auditor proposal: pre-verify factual claims in append-only evidence records
- **PR #296**: feat(signoff): cite functional-verification suites for T1 item 5.digital
- **Issue #295** (closed): T1 item 5.digital: cite the RTL klt functional-verification suite beside the STA envelope
- **PR #293**: feat(layout): draw dplus_pullup resistors from netlist lengths via klt 0.9.0
- **Issue #263** (closed): Revisit dplus_pullup resistor lengths when klt res_array snaps to grid (klayout-tools#4666)

### 2026-11-05

- **PR #291**: feat(sim): single-ended receiver MC campaign graded on the fleet, cited in 6.analog
- **Issue #212** (closed): T1 item 6: single-ended receiver Monte Carlo request (klt_measure hooks + MC builder)
- **PR #289**: feat(manifests): cite 6.digital not-applicable outcome under klt 0.8.0
- **Issue #189** (closed): T1 item 6: the analog partition needs Monte Carlo evidence; record "not applicable" only for the digital partition
- **PR #288**: feat(sim): regrade differential-receiver MC with known-bad controls, cite 6.analog
- **PR #286**: docs(sim): record complete N=100 diff-receiver MC campaign, graded unmet

### 2026-11-04

- **PR #282**: ci: run port_lint self-test in the lint script
- **Issue #279** (closed): Wire orphaned sim/tests/test_port_lint.py into npm run lint
- **PR #281**: design: lengthen TXOE NMOS-path slew resistor to fix fs rise/fall matching
- **Issue #277** (closed): Analog: driver rise/fall matching fails 1.1 limit at fs/-40C/2.97V with TXOE cell
- **PR #278**: sim: mint 45-corner TXOE leakage, signal-quality and jitter records
- **Issue #114** (closed): Analog: add TXOE high-Z enable to differential_driver (pin contract, #109)

### 2026-11-02

- **PR #274**: docs(sim): record incomplete 2026-11-02 differential-receiver MC fleet attempt

### 2026-11-01

- **PR #269**: Bump Repo Skills 0.24.7 -> 0.25.1

### 2026-10-31

- **PR #268**: fix: tie TXOE in klt driver testbenches and lint subckt port counts
- **Issue #267** (closed): Reconcile drifted klt sim driver testbenches (missing TXOE port after #114)

### 2026-10-30

- **PR #264**: feat(layout): grid-snap dplus_pullup trim resistors for a DRC-clean stream
- **Issue #251** (closed): T1 item 2 (analog) A: route and commit GDS for dplus_pullup, se_receiver_dp/dm, differential_receiver

### 2026-10-28

- **PR #261**: fix(signoff): key item-5 spec_rows to 5.analog so 5.digital is not charged analog rows
- **Issue #260** (closed): T1 item 5 (corner verification, digital): re-key spec_rows to "5.analog" so 5.digital stops being charged with analog rows

### 2026-10-27

- **PR #258**: build: pin klayout-tools to release 0.8.0 and re-render signoff evidence
- **Issue #257** (closed): Bump klayout-tools pin 7ee09483b748 → 0.8.0
- **PR #254**: feat: route and commit analog GDS for four blocks with scripted completion
- **PR #253**: docs(spec): propose DR-0009 numeric limit for driver-output jitter row

### 2026-10-24

- **PR #242**: test(sim): record first stored-evidence campaign and live-verify manifest
- **Issue #241** (closed): Confirm sim evidence store against a live broker: run klt artifact verify on first recorded campaign
- **PR #238**: feat(sim): store corner-run evidence in the artifact store, commit manifests only
- **Issue #237** (closed): Adopt the common artifact store for sim evidence (manifests in git, bytes via klt artifact)
- **PR #210**: chore: retire the bootstrap harness counter with explicit record supersession
- **Issue #207** (closed): Remove harness_counter.v smoke vehicle: redundant with real PHY tests
- **PR #190**: feat(signoff): cite artifact-anchored evidence for T1 items 1, 2.digital, 9, 10
- **Issue #187** (closed): T1 items 1, 2 (digital), 9 and 10: cite artifact-anchored evidence now that klt signoff binds it

### 2026-10-21

- **PR #230**: docs: correct envelope-agreement note on dplus-pullup measure spelling
- **Issue #194** (closed): analog-envelope-agreement: pull-up findings text says the local measure still uses '>' after #188 changed it to 'gt'
- **PR #231**: chore: add source-only analog-layout records superseding stale-hash chain heads
- **Issue #229** (closed): main CI red: analog-layout records have stale provenance hashes after #193
- **PR #193**: feat(analog): cite five 45-corner klt sim envelopes as item 5.analog
- **Issue #188** (closed): T1 item 5.analog: re-emit the 45-corner analog PVT suite as klt sim envelopes
- **PR #226**: Bump Repo Skills 0.24.3 -> 0.24.7
- **PR #224**: sim: record diff-receiver-mc campaign not run; no klt release has the capacity-wait fix
- **PR #222**: sim: record failed batch attempt for driver-disabled-leakage grid (#114)
- **PR #154**: feat(analog): TXOE high-Z enable for differential_driver (#114)
- **PR #219**: sim: add --timeout-s to diff-receiver-mc builder; record fleet pilot and failed campaign attempts

### 2026-10-20

- **PR #217**: docs(sim): point run_corners --help examples at real bench and spec anchor
- **Issue #216** (closed): Fix run_corners.py --help: examples cite smoke-bias and a bandgap spec left over from the harness port
- **PR #215**: docs: record failed fleet attempts and limits for diff-receiver MC campaign
- **PR #213**: feat(sim): klt_measure hooks and MC request builder for single-ended receivers
- **PR #192**: docs: classify analog statistical rows and state digital item-6 N/A
- **PR #206**: test: fail instead of skipping when DUT lacks trim[4:0]
- **Issue #204** (closed): Remove dead legacy no-trim fallback from test_usb_utmi_phy.py (can silently skip the trim test)
- **PR #208**: feat(sim): klt deck-list transport for all benches; refuse implicit local grid fan-out

### 2026-10-18

- **PR #171**: ci: cancel in-progress runs only for pull_request events
- **Issue #138** (closed): CI: preserve started main verification runs with event-aware concurrency

### 2026-10-17

- **PR #198**: chore(verification): remove superseded gate-sdf request
- **Issue #196** (closed): Remove verification/request-usb-utmi-phy-gate-sdf.json: request for a superseded layout that README says must not be run
- **PR #184**: refactor(layout): remove inert BLOCKED_BLOCKS path from gen_analog_layout.py
- **PR #178**: test: use shared start_clock in four remaining cocotb testbenches
- **PR #181**: refactor: route design netlisting through klt netlist
- **Issue #179** (closed): Simplify design/netlist.py: replace raw xschem call with klt netlist
- **Issue #177** (closed): Remove inert BLOCKED_BLOCKS path from gen_analog_layout.py: empty since #72
- **Issue #176** (closed): Finish #44: four cocotb testbenches still redefine the shared 12 MHz clock helper

### 2026-10-16

- **PR #173**: chore(sim): remove unused mk_dut.py and fix stale DUT references
- **PR #172**: Bump Repo Skills 0.24.1 -> 0.24.3
- **Issue #107** (closed): Remove sim/tools/mk_dut.py: unused, superseded by design/netlist.py

### 2026-10-15

- **PR #170**: docs(records): equivalence-sim attempts on flattened driver incomplete; raise signal-quality timeout
- **PR #169**: feat(analog): flatten driver output m=4 into parallel m=1 devices
- **PR #168**: docs(records): driver layout-plan re-run on post-resize netlist fails on m=4
- **PR #165**: feat(analog): re-size differential driver to meet §6 rise/fall, matching and crossover at 45/45
- **PR #163**: Bump Repo Skills 0.19.5 -> 0.24.1
- **PR #164**: feat(digital): SDF-annotated gate-level regression for T1 item 7.digital (#93)
- **PR #162**: Regenerate digital physical/evidence chain from current RTL (#131)
- **PR #149**: feat(rtl): add trim[4:0] integration input to usb_utmi_phy (#115)
- **Issue #96** (closed): Analog: re-size differential_driver output stage to meet spec §6 rise/fall, matching, and crossover rows
- **Issue #93** (closed): T1 item 7 (digital): run the gate-level regression with SDF back-annotation and cite it
- **Issue #131** (closed): Re-run synthesis, P&R, signoff and post-layout records for the #130 synchronous TX reset RTL
- **Issue #115** (closed): RTL: add trim[4:0] pass-through input port (pin contract, #109)

### 2026-10-14

- **Issue #90** (closed): README: embed the fleet burndown chart (one line)

### 2026-10-12

- **Issue #161** (closed): Auditor guard decision: keep untracked-file deletion confirmation

### 2026-10-11

- **PR #158**: test(utmi): pin inertness of XcvrSelect, SuspendM and non-raw OpMode
- **PR #157**: Lint: run scripts/test_setup_env.sh from npm run lint
- **PR #151**: docs(spec): fix evidence link in decision 0005
- **Issue #160** (closed): Auditor guard decision: keep literal-at API body protection
- **Issue #159** (closed): Auditor guard decision: keep detached force-push guard
- **Issue #155** (closed): Pin the documented inertness of XcvrSelect, SuspendM and non-raw OpMode with a UTMI testbench
- **Issue #156** (closed): Lint: run scripts/test_setup_env.sh from npm run lint so setup-env.sh regressions reach CI
- **Issue #135** (closed): Fix broken evidence link in DR-0005

### 2026-10-10

- **PR #150**: feat(rtl): UTMI Reset reaches the vendored RX transforms synchronously (#132)
- **PR #153**: fix(verification): current-source records superseding stale #112/#113 carry-forwards (#147)
- **Issue #132** (closed): Decide whether UTMI Reset should reach the vendored RX transforms synchronously
- **Issue #152** (closed): Build failure on main: pin-contract planned TXOE test is stale
- **Issue #147** (closed): Build failure on main: nine stale provenance errors block check:ci
- **PR #146**: RTL: add txoe driver-enable output (pin contract, #109)
- **PR #145**: RTL: add pu_en output derived from TermSelect (#112)
- **Issue #113** (closed): RTL: add txoe driver-enable output (pin contract, #109)
- **Issue #112** (closed): RTL: add pu_en output derived from TermSelect (pin contract, #109)

### 2026-10-09

- **Issue #106** (closed): Post-layout STA: SPEF parasitics not applied despite 342/342 net-name annotation (follow-up to #92)
- **Issue #129** (closed): Auditor Capability Request: pinned klt digital validation environment
- **PR #141**: docs(layout): re-measure resized differential_receiver (DRC clean, LVS mismatch)
- **Issue #103** (closed): Re-run differential_receiver layout/DRC/LVS after MP_B1/MN_B1 resize (PR #102)
- **PR #139**: fix(signoff): key DRC/LVS citations to the digital partition (#95)
- **PR #137**: fix: require full 45-corner evidence before fixed-trim PASS
- **PR #134**: fix(rtl): synchronous UTMI Reset on the TX path, with TX reset-and-recovery regression
- **Issue #95** (closed): signoff: bare evidence keys 3 and 4 grade the analog partition met with no analog layout
- **Issue #136** (closed): Require complete PVT evidence before fixed-trim analysis can report PASS
- **Issue #130** (closed): Verify UTMI Reset aborts transmission through stuffing and EOP states
- **PR #128**: verification: structural RX synchronization experiment (#123)
- **Issue #123** (closed): Characterize RX boundary synchronization with paired-input skew and reset injection
- **PR #125**: Add --tool-light mode to setup-env.sh (#117)
- **Issue #117** (closed): Audit setup: add a tool-light mode to the existing environment bootstrap

### 2026-10-08

- **PR #122**: Add top-level RX stuffing-error propagation and recovery tests (#118)
- **PR #121**: Reconcile status docs with superseding verification evidence
- **PR #116**: Define and lint the digital-analog pin contract (DR-0004)
- **PR #111**: Attempt SDF-annotated gate-level regression for T1 item 7.digital (blocked; negative result recorded) (#93)
- **PR #110**: Characterize RX bit sampling vs host/device clock offset (#108)
- **PR #104**: T1 item 5 (digital): cite multi-corner klt sta envelope (#92)
- **Issue #118** (closed): Verify top-level RX stuffing-error propagation and packet recovery
- **Issue #120** (closed): Reconcile current PHY status documents with superseding verification evidence
- **Issue #109** (closed): Define and lint the digital-to-analog pin contract (PU_EN/TermSelect, TRIM, driver enable, unused RXD)
- **Issue #108** (closed): Verify RX bit sampling against spec §7 ±0.25% clock tolerance (no test covers host/device rate offset)
- **Issue #92** (closed): T1 item 5 (digital): mint one multi-corner klt sta envelope on the routed layout and cite it
- **PR #102**: Analog: differential_receiver resolves 200 mV over 0.8-2.5 V common mode (spec §4)
- **Issue #97** (closed): Analog: re-size differential_receiver to meet spec §4 sensitivity across full common-mode range

### 2026-09-22

- **PR #89**: feat: re-run usb_utmi_phy P&R and post-layout PVT against vendored sources
- **PR #88**: feat: vendor shared USB protocol RTL and adapt the UTMI wrapper
- **Issue #87** (closed): Re-run usb_utmi_phy place-and-route and post-layout PVT against the vendored rtl/common sources (post-#84)
- **Issue #84** (closed): 2am: reuse rule 9 — reconcile the shared USB protocol RTL with sky130-usb2-phy — vendor the master's modules under rtl/common with reuse.lock.json

### 2026-09-21

- **PR #85**: feat(erc): declare well/substrate ties, re-grade item 11.digital
- **PR #82**: feat: check power/ground connectivity in the digital LVS harness
- **PR #81**: feat(signoff): machine-grade the block's T1 state via a klt block manifest
- **PR #80**: feat: add klt erc supply spec and evidence record for T1 item 11
- **Issue #83** (closed): T1 item 11 (digital): declare well/substrate ties[] in layout/digital/erc-supply-spec.json and re-run klt erc — upstream klayout-tools#2169 fix is already in the pinned klt
- **Issue #79** (closed): T1 item 11 digital leg: committed LVS report predates power_connectivity - re-run digital LVS on a klt that computes it
- **Issue #78** (closed): Commit a klt signoff block manifest so this block's T1 state is graded, not hand-read
- **Issue #77** (closed): T1 item 11 (power delivery, structural): no klt erc supply spec or report in this repo

