# rtl

Verilog sources.

## Bit-level codec (`spec/usb2-device-phy.md` §2)

The four modules below are the core bit-level encode/decode path that
spec §2 places **inside** this block's UTMI boundary. They are real PHY
logic, unlike `harness_counter.v` further down.

All four are fully synchronous, single-clock, one bit per clock at the
spec §3 interface clock of **12 MHz** — the raw full-speed bit rate.
There is deliberately no dual-rate or oversampled mode: high speed is out
of scope per spec §1 and `CLAUDE.md`'s scope-discipline rule. All four
share the same control convention:

- `rst_n` — active-low, **synchronous** reset.
- `init` — synchronous packet-start clear; re-establishes the idle-J
  reference / clears the consecutive-1s run count without a block reset,
  which is what a framing layer needs at every packet boundary.
- Line-state encoding, wherever a J/K bit appears: `1` = **J**, `0` = **K**.
  Mapping J/K onto the D+/D− pads, and the SE0 states that are neither, is
  line-state/EOP work that lives above these modules.

| Module | Direction | Function |
|---|---|---|
| `usb_nrzi_encoder.v` | TX | NRZI line encoding: a data 0 transitions the line, a data 1 holds it. Bare valid strobe, no backpressure — the encoder consumes one bit per clock and can never stall. |
| `usb_nrzi_decoder.v` | RX | NRZI line decoding, the exact inverse: a transition recovers a 0, no transition recovers a 1. A line held static (no transitions) decodes to a run of 1s, which is correct behavior, not an error. |
| `usb_bit_stuffer.v` | TX | Inserts a 0 after every six consecutive 1s, so an all-1s payload cannot leave the line static and starve the receiver's clock recovery. Because it *adds* bits it must stall its source: `in_ready` drops for the single clock on which the stuffed bit is emitted (an ordinary valid/ready handshake — `in_ready` is combinational from internal state only, so there is no ready/valid loop). `out_stuffed` marks inserted bits. |
| `usb_bit_destuffer.v` | RX | Removes the stuffed 0 at each stuff position, and pulses `stuff_err` for one clock when that position holds a 1 instead — seven consecutive 1s, i.e. a malformed stream. It removes bits rather than adding them, so it never stalls its source and has no ready signal. Latching `stuff_err` into the UTMI `RxError` status signal (spec §3) belongs to the framing/UTMI wrapper, not here. |

Ordering matters and is fixed by spec §2: stuffing sits **below** NRZI on
the way out and **above** it on the way in.

```
TX:  data -> usb_bit_stuffer   -> usb_nrzi_encoder -> line (J/K)
RX:  data <- usb_bit_destuffer <- usb_nrzi_decoder <- line (J/K)
```

Boundary detail you must handle before wiring these up: **USB 2.0 §7.1.9
enforces bit stuffing without exception** — "a zero bit will be inserted
even if it is the last bit before the end-of-packet (EOP) signal". A
packet whose last six pre-NRZI bits are 1s (an ordinary CRC16 residue can
end that way) must therefore put a stuffed 0 on the wire before EOP.

`usb_bit_stuffer.v` is a *streaming* module with no concept of a packet
boundary: its insert arm is gated on `in_valid`, so merely dropping
`in_valid` after the sixth 1 emits nothing more. The framing/UTMI wrapper
owns the boundary and must **flush** the stuffer before asserting EOP —
assert `in_valid` for exactly one clock while `in_ready` is low, then
deassert. That clock emits the stuffed 0 (`out_stuffed` high) and consumes
no input bit, because no transfer happens while `in_ready` is low; when
`in_ready` is high there is no pending stuff position and the flush must be
skipped. This is the one sanctioned exception to the "hold `in_valid` until
`in_ready`" rule the handshake otherwise follows.

`usb_bit_destuffer.v` needs no matching special case: the stuff position is
fixed by the run count, so the trailing 0 is removed like any other, and the
pair is lossless *and* conformant across a packet end. Both directions are
covered by directed tests, and end to end by the loopback harness.

Verification: each module has its own cocotb testbench under
`verification/`, checked bit-exactly against an independent Python model,
plus an RTL-to-RTL round-trip harness that drives the whole TX path into
the whole RX path. See `verification/README.md`.

## SYNC/EOP framing, line-state decode, and the top-level UTMI wrapper (issue #32)

The four modules below complete spec §2's digital logic and assemble it,
with the bit-level codec above, into the UTMI-facing block spec §3
defines. Same conventions as the bit-level codec: fully synchronous,
single-clock, 12 MHz, `rst_n` active-low synchronous reset, `1` = J / `0` =
K wherever a bare J/K bit appears.

| Module | Direction | Function |
|---|---|---|
| `usb_line_state_decode.v` | RX | `LineState[1:0]` from the two single-ended receiver outputs (`rxdp`/`rxdm`, matching `design/se_receiver_dp.sch`/`se_receiver_dm.sch`'s own pin names): `2'b01`=J, `2'b10`=K, `2'b00`=SE0, `2'b11`=SE1 (illegal, not produced in normal operation). |
| `usb_sync_detector.v` | RX | Matches the fixed SYNC byte (`8'h80`, transmission order `0,0,0,0,0,0,0,1`) against the NRZI-**decoded** bit stream, not raw line state — see the module's own header for why. Two completion outputs one clock apart: combinational `sync_next` (concurrent with SYNC's own final bit) and registered `sync_valid` (one clock later, concurrent with the first post-SYNC bit). |
| `usb_eop_detector.v` | RX | One SE0-duration counter feeding two outputs: `eop` (one-clock pulse at exactly 2 bit times of SE0 — spec §4's EOP threshold) and `bus_reset` (level, asserted from exactly 30 clocks of SE0 onward — 2.5 µs at the ratified 12.000 MHz interface clock, spec §4's reset threshold — cleared the clock SE0 ends). |
| `usb_utmi_phy.v` | both | The top-level wrapper: presents the full UTMI port set (spec §3) plus wire-level `txdp`/`txdm`/`rxdp`/`rxdm` (matching `design/differential_driver.sch`'s `TXDP`/`TXDM` and the single-ended receivers' `RXDP`/`RXDM`), and instantiates every module above — `usb_bit_stuffer`, `usb_nrzi_encoder`, `usb_nrzi_decoder`, `usb_bit_destuffer` (issue #31) and the three RX modules in this section. SYNC and EOP *generation* (TX) live directly in this file's TX state machine, since both are inseparable from the byte-serialization sequencing the wrapper already owns — see its own header for the full derivation, including why the RX side free-runs `usb_nrzi_decoder` rather than re-issuing `init` mid-packet, and the `sync_next`/`sync_valid` split's role in that. |

**Scope choices, stated explicitly** (see `usb_utmi_phy.v`'s header for
the full reasoning): `OpMode`, `TermSelect`, `XcvrSelect`, `SuspendM` are
present as ports (spec §3 requires them) but not consumed by any logic in
this wrapper — this FS-only, device-only block has exactly one meaningful
operating point, and the pull-up/receiver-mode effects those signals would
otherwise drive are analog integration work tracked separately (see
`design/README.md`'s own note that pull-up enable wiring is deferred to a
PHY-level wrapper). `Reset` **is** consumed, folded into an internal
synchronous reset alongside `rst_n`. Bus-reset detection
(`usb_eop_detector`'s `bus_reset`) is used internally only, to abort an
in-progress RX reception — it is not exposed as a port, since spec §3's
UTMI table defines no such output; asserting the `Reset` *input* in
response to a sustained SE0 on `LineState` is SIE-layer policy, out of
scope per CLAUDE.md.

**Not here, on purpose.** Everything above the bit/framing level — PID
interpretation, CRC5/CRC16, endpoint/enumeration state — is the
integrator's serial interface engine and is out of scope for this repo
entirely (spec §1/§2, `CLAUDE.md`).

Verification: each of the three RX modules has its own cocotb testbench
under `verification/`, and `usb_utmi_phy.v` has a top-level integration
testbench exercising the assembled wrapper end to end (TX byte(s) in →
wire-level SYNC/NRZI/stuffed/EOP output, checked against
`usb_bit_model.py`'s bit-level model; wire-level input → `DataIn`/`RxValid`/
`RxActive` out, via self-loopback) — including bit-stuff-flush-before-EOP,
back-to-back packets with a minimal inter-packet gap, and a malformed SYNC
never activating `RxActive`. See `verification/README.md`.

## Harness smoke-test vehicle

- `harness_counter.v` — a plain, parameterized (`WIDTH`, default 8) up
  counter with a synchronous active-low reset and a count-enable. **This is
  a throwaway smoke-test vehicle for the digital cocotb + `klt` harness
  bootstrapped by issue #7 — it has zero USB semantics** (no NRZI, no bit
  stuffing, no SYNC/EOP, nothing UTMI-boundary-shaped) and is not part of
  the PHY. It exists only to prove that `verification/` (cocotb + Icarus)
  and `flow/` (`klt synthesize` against gf180mcu) elaborate, simulate, and
  synthesize a real design end-to-end. Real PHY digital logic — NRZI
  encode/decode and bit stuffing/destuffing, SYNC/EOP handling, line-state
  decode, and the top-level UTMI wrapper (all above), per
  `spec/usb2-device-phy.md` §2/§3 — lives in its own files and does not
  belong in this one; see `CLAUDE.md`'s scope-discipline rule.
