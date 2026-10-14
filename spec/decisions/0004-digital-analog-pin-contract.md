# DR-0004 — Digital <-> analog pin contract

- **Status**: Proposed -- the pin table is a structural contract checked by
  `scripts/check_pin_contract.py`; the items under "Flagged for operator
  ruling" are NOT decided. Nothing here relaxes a ratified spec row.
- **Date**: 2026-10-08
- **Raised by**: Builder agent, issue #109
- **Affects**: nothing in this PR (docs + lint only). Implied changes are
  follow-ups: #112 (`pu_en`), #113 (`txoe` RTL), #114 (`TXOE` analog pin),
  #115 (`trim[4:0]` port).
- **Does not change**: the ratified spec, the RTL, or the netlists;
  full-speed-only, device-only, UTMI-boundary-only scope.

## Context

`rtl/usb_utmi_phy.v` exposes only `txdp/txdm/rxdp/rxdm` toward the analog
cells. The analog cells expose `PU_EN`, `TRIM0..4`, and `RXD` with no
digital counterpart, and the driver has no enable although `DP`/`DM` are
shared with the receivers (`design/README.md`). Spec §5 ratifies the pull-up
as "enable-controlled, digital input from the UTMI-side logic
(soft-connect)", so that connection is a ratified requirement that had no
owner. This record fixes every seam pin, picks the full-speed-minimal
option for each, and records alternatives.

## Decisions

1. **`PU_EN` <- `TermSelect` (gated by `rst_n`).** `pu_en = TermSelect &
   rst_n`. In full-speed UTMI, `TermSelect=1` means "present the FS
   termination", i.e. the D+ pull-up -- exactly the §5 soft-connect.
   `rst_n` low forces the pull-up off so a powering-up block does not
   advertise a device before its digital side is alive.
   - `SuspendM` does **not** gate `PU_EN`: a USB device keeps its pull-up
     through suspend (dropping it reads as disconnect). `SuspendM` stays
     unconsumed, as `rtl/usb_utmi_phy.v:178-184` already states.
   - UTMI `Reset` does **not** gate `PU_EN`: it is a link command to the
     PHY's framing logic, not a disconnect request.
   - Alternatives rejected: `TermSelect & SuspendM` (breaks suspend);
     a registered/synchronised `pu_en` (extra flop, no spec need; the
     pull-up is a slow analog load); a dedicated `soft_connect` port
     (duplicates `TermSelect`, new non-UTMI port).
2. **Driver output-enable `TXOE`: yes, needed.** `DP`/`DM` are shared with
   the receivers and the host drives the bus while the device receives; a
   driver with no high-Z state fights the host. Add `TXOE` (active-high,
   `TXOE=0` => `DP`/`DM` outputs high-Z) to `differential_driver`, driven
   by RTL `txoe`, high exactly while the wrapper drives the line (SYNC
   through the final EOP/J bit, `tx_state != TX_IDLE`), low otherwise.
   - Alternatives rejected: gating via `TXDP=TXDM=0` (that is SE0, an
     actively driven state, not high-Z); an external tri-state at the pad
     ring (pushes a mandatory component on the integrator, against §5's
     "minimise what the integrator must additionally provide" rationale).
3. **`TRIM[4:0]` source: integrator-supplied static input**, a
   `trim[4:0]` pass-through port on the digital top (no RTL logic, no
   register, no in-block default). It is a test-time code (`design/README.md`
   already places it in the integrator's OTP/fuse/scan mechanism, and
   `sim/tests/test_fixed_trim.py` assumes one fixed code); all-zero is the
   unprogrammed default. Bit order: `trim[i]` <-> `TRIMi`.
   - Alternatives rejected: an RTL constant (cannot be corrected per die,
     defeating the trim ladder); a register loaded over a side bus (adds a
     configuration interface -- scope creep towards a controller); on-chip
     OTP (macro the open PDK flow does not provide).
4. **`RXD` (differential receiver output): deliberately unused by the
   digital side.** `LineState` and RX framing derive J/K/SE0 from the two
   single-ended receivers (`RXDP`/`RXDM`) alone, matching the current RTL
   and its verification. `RXD` therefore has no digital port; the cell stays
   in the analog set because spec §4 ratifies it. It is listed in the table
   with digital port `-` so the omission is explicit and checked.
   - Alternative: feed `RXD` to the data path for better noise margin on
     differential data. Not chosen: larger RTL/verification change, and the
     SE decode already satisfies the ratified receive tests.
5. **Supplies/regulated rail** (`VDD`, `VSS`, `VPU_REG`) are not digital
   ports; they are in the table as analog-only rows so a renamed supply
   pin is also caught.

## Flagged for operator ruling (not decided here)

- **Spec §4 vs. `RXD` unused**: §4 ratifies a differential receiver that
  "recovers D+/D- differential data". Decision 4 leaves its output
  unconsumed. If the operator reads §4 as requiring the digital side to use
  it, decision 4's alternative applies and `rxd` becomes a digital input.
- **Spec §5 "digital input from the UTMI-side logic"**: decision 1 maps this
  to `TermSelect` (reset-gated). Confirm that is the intended source.
- **Spec §6 / driver high-Z**: §6 lists no high-Z/leakage parameter. Decision
  2 adds one pin and implies a leakage claim for #114's evidence; the
  operator may want a spec row for it. No row is added or relaxed here.

## Pin table (machine-checked)

`scripts/check_pin_contract.py` parses the block between the markers. For
analog rows the pin must exist in the named `.subckt` with the stated
direction (from `*.PININFO`: I input, O output, B bidirectional); for
digital rows the port must exist in `usb_utmi_phy` with the stated
direction. Rows with status `planned-dig #N` / `planned-ana #N` / `planned #N`
(both sides) must be **absent** on the planned side until the follow-up
lands (`PU_EN`/`TRIM` already exist in the netlist; `TXOE` was `planned-ana #114` until the
analog pin landed, after the digital `txoe` port of #113);
landing the analog side requires flipping the row to `current`. Every `.subckt` pin and every module port must appear. `-` means
no counterpart on that side. Analog direction is what the generated
`*.PININFO` line says: the receiver output pins are marked `B` there
(not `O`), and the table records that as-is rather than the intent
(output); it is a schematic-annotation imprecision, not a contract choice.

<!-- pin-contract:begin -->
| Contract pin | Digital port | Dig dir | Analog cell.pin | Ana dir | Status | Owner | Source of truth |
|---|---|---|---|---|---|---|---|
| TXDP | txdp | output | differential_driver.TXDP | I | current | RTL | `tx_state` pad mux |
| TXDM | txdm | output | differential_driver.TXDM | I | current | RTL | `tx_state` pad mux |
| TXOE | txoe | output | differential_driver.TXOE | I | current | RTL | `tx_state != TX_IDLE`  |
| RXDP | rxdp | input | se_receiver_dp.RXDP | B | current | analog | SE receiver on D+ |
| RXDM | rxdm | input | se_receiver_dm.RXDM | B | current | analog | SE receiver on D- |
| RXD | - | - | differential_receiver.RXD | B | current | analog | deliberately unused by digital (decision 4) |
| PU_EN | pu_en | output | dplus_pullup.PU_EN | I | current | RTL | `TermSelect & rst_n` |
| TRIM0 | trim[0] | input | dplus_pullup.TRIM0 | I | planned-dig #115 | integrator | test-time code |
| TRIM1 | trim[1] | input | dplus_pullup.TRIM1 | I | planned-dig #115 | integrator | test-time code |
| TRIM2 | trim[2] | input | dplus_pullup.TRIM2 | I | planned-dig #115 | integrator | test-time code |
| TRIM3 | trim[3] | input | dplus_pullup.TRIM3 | I | planned-dig #115 | integrator | test-time code |
| TRIM4 | trim[4] | input | dplus_pullup.TRIM4 | I | planned-dig #115 | integrator | test-time code |
| DP.driver | - | - | differential_driver.DP | B | current | analog | pad net |
| DM.driver | - | - | differential_driver.DM | B | current | analog | pad net |
| DP.rx_se | - | - | se_receiver_dp.DP | I | current | analog | pad net |
| DM.rx_se | - | - | se_receiver_dm.DM | I | current | analog | pad net |
| DP.rx_diff | - | - | differential_receiver.DP | I | current | analog | pad net |
| DM.rx_diff | - | - | differential_receiver.DM | I | current | analog | pad net |
| DP.pullup | - | - | dplus_pullup.DP | B | current | analog | pad net |
| VPU_REG | - | - | dplus_pullup.VPU_REG | I | current | analog | upstream regulator (not built) |
| VDD.driver | - | - | differential_driver.VDD | B | current | analog | supply |
| VSS.driver | - | - | differential_driver.VSS | B | current | analog | supply |
| VDD.rx_diff | - | - | differential_receiver.VDD | B | current | analog | supply |
| VSS.rx_diff | - | - | differential_receiver.VSS | B | current | analog | supply |
| VDD.rx_dp | - | - | se_receiver_dp.VDD | B | current | analog | supply |
| VSS.rx_dp | - | - | se_receiver_dp.VSS | B | current | analog | supply |
| VDD.rx_dm | - | - | se_receiver_dm.VDD | B | current | analog | supply |
| VSS.rx_dm | - | - | se_receiver_dm.VSS | B | current | analog | supply |
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
