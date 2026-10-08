# Work log

Merged PRs and closed issues from the Guide’s 30-day maintenance window.

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
