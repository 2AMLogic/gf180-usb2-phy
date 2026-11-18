# DR-0011 — One `se_receiver` cell, instantiated for D+ and D-

- **Status**: Proposed -- awaiting ratification through the usual path. The
  operator ruling that sets the direction is recorded on issue #339
  (rjwalters, 2026-11-18, attended `/fleet:decide` round 20261118-r16, q99,
  option `merge-now`); this record is not itself ratified by that comment.
- **Date**: 2026-11-18
- **Raised by**: Builder agent, issue #339
- **Supersedes**: the rows of DR-0004's pin table that name `se_receiver_dp`
  and `se_receiver_dm` (`RXDP`, `RXDM`, `DP.rx_se`, `DM.rx_se`,
  `VDD/VSS.rx_dp`, `VDD/VSS.rx_dm`). DR-0004 is otherwise unchanged and stays
  in force; its table is not edited in place.
- **Does not change**: the ratified spec, any device, size, connection or
  threshold, the RTL ports, or any existing evidence record. No spec limit is
  relaxed. Full-speed-only, device-only, UTMI-boundary-only scope.

## Context

`se_receiver_dp` and `se_receiver_dm` were the same circuit committed under two
names: the schematics, netlists, layout plans and benches differed only in the
`DP`/`DM` and `RXDP`/`RXDM` spelling, and the two GDS streams are identical
modulo those names (checked structurally per layer for #339: no geometry
differs; the only differences are the pin-label texts). Every verification step
was therefore run, recorded and cited twice for one circuit, and two editable
copies could drift apart unnoticed.

## Decision

There is one single-ended receiver cell, `se_receiver`, with ports
`VDD VSS IN OUT`. The integration level instantiates it twice:
`Xrxp VDD 0 DP RXDP se_receiver` and `Xrxm VDD 0 DM RXDM se_receiver`.
The digital-facing contract pins `RXDP` and `RXDM` are unchanged; only the
analog side of the pin map is re-keyed. The pin table below is the complete
current table; `scripts/check_pin_contract.py` reads it from this record.

Alternatives considered: keep both cells and add a parity lint (the operator
declined it: a parity check between two copies is the pattern 2AMLogic/2am#7561
says not to repeat); one cell with per-line parameters (no circuit differs, so
there is nothing to parameterise).

## Consequences

- Existing records under `sim/se-receiver-dp-thresholds/`,
  `sim/se-receiver-dm-thresholds/` and `sim/se-receiver-mc/results/` are
  append-only evidence and stay as they are. They describe the pre-merge cells;
  new records for `se_receiver` supersede them and say why.
- Evidence for the already-closed LVS (#247) and power-delivery (#248) items
  needs superseding records for the merged cell. #246 (DRC) and #53
  (post-layout PVT) run on the merged cell, so on four analog blocks, not five.

## Pin table

<!-- pin-contract:begin -->
| Contract pin | Digital port | Dig dir | Analog cell.pin | Ana dir | Status | Owner | Source of truth |
|---|---|---|---|---|---|---|---|
| TXDP | txdp | output | differential_driver.TXDP | I | current | RTL | `tx_state` pad mux |
| TXDM | txdm | output | differential_driver.TXDM | I | current | RTL | `tx_state` pad mux |
| TXOE | txoe | output | differential_driver.TXOE | I | current | RTL | `tx_state != TX_IDLE`  |
| RXDP | rxdp | input | se_receiver.OUT | B | current | analog | `Xrxp` instance of `se_receiver` on D+ |
| RXDM | rxdm | input | se_receiver.OUT | B | current | analog | `Xrxm` instance of `se_receiver` on D- |
| RXD | - | - | differential_receiver.RXD | B | current | analog | deliberately unused by digital (decision 4) |
| PU_EN | pu_en | output | dplus_pullup.PU_EN | I | current | RTL | `TermSelect & rst_n` |
| TRIM0 | trim[0] | input | dplus_pullup.TRIM0 | I | current | integrator | test-time code |
| TRIM1 | trim[1] | input | dplus_pullup.TRIM1 | I | current | integrator | test-time code |
| TRIM2 | trim[2] | input | dplus_pullup.TRIM2 | I | current | integrator | test-time code |
| TRIM3 | trim[3] | input | dplus_pullup.TRIM3 | I | current | integrator | test-time code |
| TRIM4 | trim[4] | input | dplus_pullup.TRIM4 | I | current | integrator | test-time code |
| DP.driver | - | - | differential_driver.DP | B | current | analog | pad net |
| DM.driver | - | - | differential_driver.DM | B | current | analog | pad net |
| DP.rx_se | - | - | se_receiver.IN | I | current | analog | pad net |
| DM.rx_se | - | - | se_receiver.IN | I | current | analog | pad net |
| DP.rx_diff | - | - | differential_receiver.DP | I | current | analog | pad net |
| DM.rx_diff | - | - | differential_receiver.DM | I | current | analog | pad net |
| DP.pullup | - | - | dplus_pullup.DP | B | current | analog | pad net |
| VPU_REG | - | - | dplus_pullup.VPU_REG | I | current | analog | upstream regulator (not built) |
| VDD.driver | - | - | differential_driver.VDD | B | current | analog | supply |
| VSS.driver | - | - | differential_driver.VSS | B | current | analog | supply |
| VDD.rx_diff | - | - | differential_receiver.VDD | B | current | analog | supply |
| VSS.rx_diff | - | - | differential_receiver.VSS | B | current | analog | supply |
| VDD.rx_se | - | - | se_receiver.VDD | B | current | analog | supply (both instances) |
| VSS.rx_se | - | - | se_receiver.VSS | B | current | analog | supply (both instances) |
| VSS.pullup | - | - | dplus_pullup.VSS | B | current | analog | supply |
| clk | clk | input | - | - | current | integrator | 12 MHz clock (spec §7) |
| rst_n | rst_n | input | - | - | current | integrator | power-on reset |
| TxValid | TxValid | input | - | - | current | SIE/integrator | UTMI |
| TxReady | TxReady | output | - | - | current | RTL | UTMI |
| DataOut | DataOut[7:0] | input | - | - | current | SIE/integrator | UTMI |
| RxValid | RxValid | output | - | - | current | RTL | UTMI |
| RxActive | RxActive | output | - | - | current | RTL | UTMI |
| RxError | RxError | output | - | - | current | RTL | UTMI |
| DataIn | DataIn[7:0] | output | - | - | current | RTL | UTMI |
| LineState | LineState[1:0] | output | - | - | current | RTL | UTMI |
| OpMode | OpMode[1:0] | input | - | - | current | SIE/integrator | UTMI |
| TermSelect | TermSelect | input | - | - | current | SIE/integrator | UTMI; source of PU_EN |
| XcvrSelect | XcvrSelect | input | - | - | current | SIE/integrator | UTMI, unconsumed |
| SuspendM | SuspendM | input | - | - | current | SIE/integrator | UTMI, unconsumed |
| Reset | Reset | input | - | - | current | SIE/integrator | UTMI |
<!-- pin-contract:end -->
