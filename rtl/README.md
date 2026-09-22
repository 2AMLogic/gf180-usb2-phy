# rtl

Verilog sources.

## Bit-level codec (`spec/usb2-device-phy.md` §2)

The four modules below are the core bit-level encode/decode path that
spec §2 places **inside** this block's UTMI boundary. They are real PHY
logic, unlike `harness_counter.v` further down.

**Vendored from the rule-9 master (issue #84).** The four files live under
`rtl/common/` as byte-exact stamped copies of
[`2AMLogic/sky130-usb2-phy`](https://github.com/2AMLogic/sky130-usb2-phy)
— the reconciliation master for shared PDK-independent USB protocol RTL
per `2AMLogic/2am`'s `REUSE.md` cross-cutting rule 9 and the master's
DR-0002 (master by *precedence*: its copies were committed first). The
root `reuse.lock.json` pins the upstream commit and per-file SHA-256s,
`scripts/reuse-check.py` (a per-repo CI copy from 2am) enforces the
stamps, and `spec/decisions/0002` records the interface adaptation and
the local dispositions. **Never hand-edit anything under `rtl/common/`**:
an edit breaks the byte-stamp and, absent a `diverged:` entry pointing at
a decision record, defeats the one-master rule this layout exists to
enforce. Fix bugs upstream (master side) and re-vendor.

All four are single-clock, one bit per strobe, instantiated here at the
spec §3 interface clock of **12 MHz** — the raw full-speed bit rate, no
oversampling. There is deliberately no dual-rate mode: high speed is out
of scope per spec §1 and `CLAUDE.md`'s scope-discipline rule. Two of the
files name their clock/reset ports `clk_144`/`rst_144_n` — that is the
**master's 144 MHz oversampling-domain vocabulary, not a frequency
requirement of the transforms**: the master instantiates them behind a
12×-oversampling recovery clock, this repo instantiates them on its own
interface clock with the strobes (`bit_stb`/`bit_strobe`) asserted on
every active clock (`spec/decisions/0002`; do not "fix" the names). The
vendored modules take an **asynchronous** active-low `rst_n` (the
master's style); the local modules in this directory keep synchronous
resets. Shared control conventions:

- Strobed bit-times: `bit_stb`/`bit_strobe` mark the clocks on which a
  bit is consumed/presented — the canonical handshake discipline.
- `sof` (stuffer/encoder) — packet-start: re-establish the idle-J
  transition reference (encoder) / reset the consecutive-1s run counter
  (stuffer) at the first bit of a packet's stuffable field.
- `bypass` (stuffer/encoder) — raw/transparent mode (UTMI `OpMode`
  `2'b10`): no stuffing, no NRZI transform.
- Line-state encoding, wherever a J/K bit appears: `1` = **J**, `0` = **K**.
  Mapping J/K onto the D+/D− pads, and the SE0 states that are neither, is
  line-state/EOP work that lives above these modules.

| Module | Direction | Function |
|---|---|---|
| `common/usb_nrzi_encoder.v` | TX | NRZI line encoding: a data 0 transitions the line, a data 1 holds it. Strobe-consumed (`bit_stb`), registered `level_out` — the level for the bit consumed at edge N is on the wire for the clock after N. `sof` re-derives the transition reference from idle J on a packet's first bit. |
| `common/usb_nrzi_decoder.v` | RX | NRZI line decoding, the exact inverse: a transition recovers a 0, no transition recovers a 1. A line held static (no transitions) decodes to a run of 1s, which is correct behavior, not an error. `bit_is_jk` is load-bearing: NRZI is defined only over J/K, so SE0/SE1 cells (EOP, bus reset) must not be strobed as data — the wrapper derives it from its line-state decode. |
| `common/usb_bit_stuffer.v` | TX | Inserts a 0 after every six consecutive 1s, so an all-1s payload cannot leave the line static and starve the receiver's clock recovery. Back-pressure is inverted relative to a ready/valid stream: `consume` reads 0 on the bit-time where the stuffed bit is emitted instead — hold `bit_in`, re-present it on the next strobe. `stuff_pending_after` is a same-cycle lookahead ("the very next bit-time is mandatorily a forced stuff") that a caller uses to discharge the flush duty below. `sof` resets the run counter at the first post-SYNC bit. |
| `common/usb_bit_destuffer.v` | RX | Removes the stuffed 0 at each stuff position, and pulses `stuff_err` for one clock when that position holds a 1 instead — seven consecutive 1s, i.e. a malformed stream. Gated by `enable` (SOP..EOP): while low it is a transparent pass-through with its run counter held at zero (so indefinitely long idle — continuous decoded 1s — can never accumulate into a false stuff error), which is also what lets a caller search for the never-stuffed SYNC pattern on its output. Latching `stuff_err` into the UTMI `RxError` status signal (spec §3) belongs to the framing/UTMI wrapper, not here. |

Ordering matters and is fixed by spec §2: stuffing sits **below** NRZI on
the way out and **above** it on the way in. Per the canonical
architecture, SYNC framing goes **around** the stuffer (SYNC is never
stuffed; the stuffer's `sof` starts its run counter fresh at the first
post-SYNC bit), not through it.

```
TX:  data -> usb_bit_stuffer   -> usb_nrzi_encoder -> line (J/K)
         (SYNC bypasses the stuffer, into the encoder)
RX:  data <- usb_bit_destuffer <- usb_nrzi_decoder <- line (J/K)
```

Boundary detail you must handle before wiring these up: **USB 2.0 §7.1.9
enforces bit stuffing without exception** — "a zero bit will be inserted
even if it is the last bit before the end-of-packet (EOP) signal". A
packet whose last six payload bits are 1s (an ordinary CRC16 residue can
end that way) must therefore put a stuffed 0 on the wire before EOP.

The stuffer is a *streaming* module with no concept of a packet boundary:
it emits a stuffed bit only on a strobed bit-time. The framing/UTMI
wrapper owns the boundary and discharges the flush duty through the
canonical lookahead: when the packet's last real bit is consumed with
`stuff_pending_after` high, the caller spends **one more strobed
bit-time** presenting any `bit_in` (the stuffer emits the forced 0,
`consume` reads 0) before framing EOP — `usb_utmi_phy.v`'s `TX_FLUSH`
state. (The pre-vendoring local stuffer expressed the same duty as a
valid/ready flush idiom — assert `in_valid` one clock while `in_ready` is
low — that idiom is gone with the module.)

`usb_bit_destuffer.v` needs no matching special case: the stuff position
is fixed by the run count, so the trailing 0 is removed like any other,
and the pair is lossless *and* conformant across a packet end. Both
directions are covered by directed tests, and end to end by the loopback
harness.

Verification: each module has its own cocotb testbench under
`verification/`, checked bit-exactly against an independent Python model,
plus an RTL-to-RTL round-trip harness that drives the whole TX path into
the whole RX path. See `verification/README.md`.

## SYNC/EOP framing, line-state decode, and the top-level UTMI wrapper (issue #32)

The four modules below complete spec §2's digital logic and assemble it,
with the bit-level codec above, into the UTMI-facing block spec §3
defines. Same conventions as the local half of the bit-level codec: fully
synchronous, single-clock, 12 MHz, `rst_n` active-low synchronous reset,
`1` = J / `0` = K wherever a bare J/K bit appears.

| Module | Direction | Function |
|---|---|---|
| `usb_line_state_decode.v` | RX | `LineState[1:0]` from the two single-ended receiver outputs (`rxdp`/`rxdm`, matching `design/se_receiver_dp.sch`/`se_receiver_dm.sch`'s own pin names): `2'b01`=J, `2'b10`=K, `2'b00`=SE0, `2'b11`=SE1 (illegal, not produced in normal operation). |
| `usb_sync_detector.v` | RX | Matches the fixed SYNC byte (`8'h80`, transmission order `0,0,0,0,0,0,0,1`) against the NRZI-**decoded** bit stream, not raw line state — see the module's own header for why. Two completion outputs one clock apart: combinational `sync_next` (concurrent with SYNC's own final bit) and registered `sync_valid` (one clock later, concurrent with the first post-SYNC bit). Architecture-bound, not vendored — the master's counterpart is its 12×-oversampling `usb_bit_sync.v`; per its DR-0002 Decision 4 the two are the same USB-visible function at different layers, deliberately not shared files. |
| `usb_eop_detector.v` | RX | One SE0-duration counter feeding two outputs: `eop` (one-clock pulse at exactly 2 bit times of SE0 — spec §4's EOP threshold) and `bus_reset` (level, asserted from exactly 30 clocks of SE0 onward — 2.5 µs at the ratified 12.000 MHz interface clock, spec §4's reset threshold — cleared the clock SE0 ends). Architecture-bound, not vendored (master-side EOP detection is embedded in its `usb_rx_framer.v`). |
| `usb_utmi_phy.v` | both | The top-level wrapper: presents the full UTMI port set (spec §3) plus wire-level `txdp`/`txdm`/`rxdp`/`rxdm` (matching `design/differential_driver.sch`'s `TXDP`/`TXDM` and the single-ended receivers' `RXDP`/`RXDM`), and instantiates the four vendored codec modules (issue #84) plus the three RX modules in this section. Since the vendoring it is the **canonical-interface adapter** (`spec/decisions/0002`): its TX state machine follows the master's `usb_tx_framer.v` shape (SYNC around the stuffer, `sof` run resets, the `stuff_pending_after` flush duty, a HOLD bit-time so the last encoded level gets its wire clock before EOP), and its RX side derives the canonical `bit_is_jk`/`enable` gating signals. SYNC and EOP *generation* (TX) live directly in this file's TX state machine, since both are inseparable from the byte-serialization sequencing the wrapper already owns — see its own header for the full derivation, including why the RX side free-runs `usb_nrzi_decoder` (the canonical module has no re-reference port at all), and the `sync_next`/`sync_valid` split's role in arming the destuffer's `enable` exactly at the first post-SYNC bit. |

**Scope choices, stated explicitly** (see `usb_utmi_phy.v`'s header for
the full reasoning): `OpMode` raw mode (`2'b10`) **is** consumed — it
drives the vendored modules' `bypass` (no stuffing, no NRZI, body bits
only; SYNC stays framed). Every other `OpMode` encoding, plus
`TermSelect`, `XcvrSelect`, `SuspendM`, is present as a port (spec §3
requires them) but not consumed by any logic in this wrapper — this
FS-only, device-only block has exactly one meaningful operating point, and
the pull-up/receiver-mode effects those signals would otherwise drive are
analog integration work tracked separately (see `design/README.md`'s own
note that pull-up enable wiring is deferred to a PHY-level wrapper).
`Reset` **is** consumed, folded into an internal reset alongside `rst_n`.
Bus-reset detection (`usb_eop_detector`'s `bus_reset`) is used internally
only, to abort an in-progress RX reception — it is not exposed as a port,
since spec §3's UTMI table defines no such output; asserting the `Reset`
*input* in response to a sustained SE0 on `LineState` is SIE-layer
policy, out of scope per CLAUDE.md.

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
the canonical fresh-at-PID stuffing scope, raw-mode (`OpMode 2'b10`) wire
output, back-to-back packets with a minimal inter-packet gap, and a
malformed SYNC never activating `RxActive`. See `verification/README.md`.

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
  belong in this one; see `CLAUDE.md`'s scope-discipline rule. Dispositioned
  as harness mechanics (not PHY logic, not vendorable) in
  `spec/decisions/0002`.
