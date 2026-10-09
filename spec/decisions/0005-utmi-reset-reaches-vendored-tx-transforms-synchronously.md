# DR-0005 — UTMI `Reset` reaches the vendored TX transforms synchronously

- **Status**: Accepted (wrapper-internal implementation decision; no spec
  row changes)
- **Date**: 2026-10-09
- **Raised by**: Builder agent, issue #130
- **Amends**: DR-0002 Decision 5's last sentence ("the wrapper feeds all of
  them the same `int_rst_n`"), for the two TX transforms only. DR-0002 is
  left unedited as history; this record is the current statement.
- **Does not change**: the ratified spec, the UTMI port set, the vendored
  bytes under `rtl/common/` (`reuse.lock.json` stamps unchanged), any RX
  behaviour, or the full-speed-only, device-only, UTMI-boundary-only scope.

## Context

`rtl/usb_utmi_phy.v` folds the UTMI `Reset` input into
`int_rst_n = rst_n & ~Reset`. The wrapper's own registers use it as a
synchronous reset. The four vendored transforms (DR-0002) take an
asynchronous active-low reset, and DR-0002 Decision 5 fed them the same
`int_rst_n`.

UTMI signals are synchronous to the interface clock: the link raises
`Reset` after one clock edge and the PHY acts on the next. Issue #130's
TX reset-and-recovery regression (`verification/test_usb_utmi_phy.py`,
`test_tx_utmi_reset_aborts_and_recovers`) found that the TX side did not
behave that way. When `Reset` rose mid-clock, the asynchronous port
cleared the NRZI encoder's registered level straight away, while the TX
state machine (synchronous) was still in `TX_SYNC`/`TX_DATA`/`TX_HOLD`
and still passing that level to `txdp`/`txdm`. An in-flight K cell
therefore turned into J before the sampling edge, a combinational path
from the `Reset` input to the wire. 16 of the 36 new cases failed this
way, every case where the in-flight cell was K (the last SYNC bit, an
ordinary data bit, an inserted stuff bit, the last level's hold clock).
The stuffer's run counter was cleared the same way. It feeds `consume`
and so `TxReady`, which is the same hazard on the handshake (not
separately observed in the failing cases). The post-edge behaviour and
the next packet were already correct. Only the timing of the reset was
wrong. Evidence:
`verification/records/utmi-framing-functional/records/20261009-140000-5e89df9.md`.

## Decision

1. **The vendored TX transforms' asynchronous reset port takes `rst_n`
   only.** `usb_bit_stuffer` and `usb_nrzi_encoder` are still
   asynchronously reset by the block's power-on `rst_n`, as before.
2. **UTMI `Reset` reaches them through their canonical inputs, on the
   sampling edge.** While `int_rst_n` is low (`tx_clear`), the wrapper
   strobes:
   - the stuffer with `bit_in` = 0. That zeroes its run counter in every
     branch (bypass, sof, stuff, data).
   - the encoder with `sof` = 1 and `bit_in` = 1. That loads idle J,
     with or without bypass.

   Every TX register is therefore still cleared by `Reset`, on the edge
   that samples it. Neither override reaches `consume` (a function of
   the run register, `bypass` and `sof`), so `TxReady` stays a function
   of registered state. The stuffer outputs that do follow `bit_in`
   (`bit_out`, `stuff_pending_after`) feed only the overridden encoder
   input and the TX state machine, which is itself in reset.
3. **RX is unchanged.** `usb_nrzi_decoder` and `usb_bit_destuffer` keep
   `int_rst_n` on their asynchronous port. No UTMI output is a
   combinational function of their state: `RxValid`, `RxError`,
   `DataIn`, `RxActive` and `LineState` are all wrapper registers.
   Whether to make the RX resets synchronous too is outside #130's
   transmit scope, and is not decided here (#132).

## Consequences

- The TX reset contract is now as #130 specified. On the edge that
  samples `Reset` high, `txdp`/`txdm` go to idle J and `TxReady` goes to
  its idle value (high). Nothing changes before that edge. While `Reset`
  is high nothing is accepted. The first edge that samples `Reset` low
  with `TxValid` and `TxReady` high accepts `DataOut`, which is the
  release edge itself when `TxValid` is held.
- Coverage limit, recorded honestly: removing the encoder or stuffer
  clear (leaving only the `rst_n` port) is **not** observable at the
  ports. Each packet's `sof` re-derives the encoder's idle-J reference
  and restarts the stuffer's run count, and the pad mux forces J in
  `TX_IDLE`. The clears keep "every TX register resets on `Reset`" true
  internally. They are not what makes the wire correct.
- Synthesis: +8 cells, +39.5 µm², same flop count (11 `dffrnq`). See
  `verification/records/synthesis-smoke/`.
- **The committed routed netlist and layout (`layout/digital/`) predate
  this change** and still contain the asynchronous TX path. The
  zero-delay gate-level replay records the failures on that netlist.
  Re-running synthesis, place-and-route, signoff and the post-layout
  records for the fixed RTL is a follow-up (#131). It is not part of
  #130.

## Alternatives considered

- **Register `Reset` once and feed the registered copy to the
  asynchronous ports.** Rejected. It makes assertion glitch-free but
  holds the vendored modules in reset across the release edge, so with
  `TxValid` held high the release edge would accept a byte while the
  encoder ignored SYNC bit 0. Fixing that would need `TxReady` held low
  for an extra clock after release, a new handshake rule.
- **Feed `rst_n` only, with no synchronous clear.** Rejected. It is
  port-equivalent (see the coverage limit above) but leaves stale
  internal state after `Reset`, against the "Reset clears the TX framer,
  stuffer and encoder together" contract #130 verifies.
- **Edit the vendored modules to take a synchronous clear port.**
  Rejected. The vendored bytes are stamped (DR-0002, `reuse.lock.json`),
  and the canonical inputs already reach the needed state.
