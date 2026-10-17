# Work log

Merged PRs and closed issues from the Guide’s 30-day maintenance window.

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

### 2026-09-17

- **Issue #76** (closed): Same protocol logic, two incompatible implementations: usb_nrzi_encoder.v diverged across PDKs

### 2026-09-14

- **PR #75**: fix(layout): set params.flavor:1k on 3 receiver plans' res_array groups
- **Issue #73** (closed): Fix silent PPOLYF_U_1K/generic-flavor mismatch on 3 committed analog layout plans' res_array groups

### 2026-09-13

- **PR #74**: feat(env): re-pin klt past klayout-tools#1731 (res_array rm1 support)
- **Issue #72** (closed): Re-pin klt past klayout-tools#1731 fix so a differential_driver plan can be authored

### 2026-09-12

- **PR #71**: feat(env): re-pin klt past klayout-tools#1662 (rm1/rm2/rm3 metal resistors)
- **Issue #70** (closed): Re-pin klt past klayout-tools#1662 (rm1/rm2/rm3 metal-resistor support): retry differential_driver ingestion

### 2026-09-09

- **PR #69**: Re-pin klt past #1501/#1502 and spend cross_block_layer_role on dplus_pullup
- **Issue #68** (closed): Re-pin klt past klayout-tools#1501/#1502 and spend `routing.cross_block_layer_role` on `dplus_pullup`: route the 15 unrouted nets, or record what still blocks them
- **Issue #58** (closed): loom-daemon: noop cooldown (#6670) did not prevent issue #51 from being re-dispatched twice within minutes
