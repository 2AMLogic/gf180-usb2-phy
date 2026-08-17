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

**Not here, on purpose.** SYNC generation/detection, EOP (SE0)
generation/detection, `LineState[1:0]` decode, and the top-level
UTMI-facing wrapper that assembles these submodules are separate work and
will arrive as their own files. Everything above the bit level — PID
interpretation, CRC5/CRC16, endpoint/enumeration state — is the
integrator's serial interface engine and is out of scope for this repo
entirely (spec §1/§2, `CLAUDE.md`).

Verification: each module has its own cocotb testbench under
`verification/`, checked bit-exactly against an independent Python model,
plus an RTL-to-RTL round-trip harness that drives the whole TX path into
the whole RX path. See `verification/README.md`.

## Harness smoke-test vehicle

- `harness_counter.v` — a plain, parameterized (`WIDTH`, default 8) up
  counter with a synchronous active-low reset and a count-enable. **This is
  a throwaway smoke-test vehicle for the digital cocotb + `klt` harness
  bootstrapped by issue #7 — it has zero USB semantics** (no NRZI, no bit
  stuffing, no SYNC/EOP, nothing UTMI-boundary-shaped) and is not part of
  the PHY. It exists only to prove that `verification/` (cocotb + Icarus)
  and `flow/` (`klt synthesize` against gf180mcu) elaborate, simulate, and
  synthesize a real design end-to-end. Real PHY digital logic — NRZI
  encode/decode and bit stuffing/destuffing (now above), SYNC/EOP handling
  and line-state decode (still to come), per `spec/usb2-device-phy.md`
  §2 — lives in its own files and does not belong in this one; see
  `CLAUDE.md`'s scope-discipline rule.
