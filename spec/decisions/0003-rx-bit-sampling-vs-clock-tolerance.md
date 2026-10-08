# DR-0003 — RX bit sampling vs. the §7 reference-clock tolerance

- **Status**: Proposed -- awaiting operator ruling. Nothing here is
  decided, and the ratified spec and the RTL are unchanged by this record.
- **Date**: 2026-10-08
- **Raised by**: Builder agent, issue #108
- **Evidence**: `verification/records/utmi-framing-functional/records/20261008-210900-2875d57.md`
  (full matrix: `.../artifacts/20261008-210900-2875d57/usb-rx-clock-tolerance-matrix.json`)
- **Affects (if any option other than D is chosen)**: `spec/usb2-device-phy.md`
  §3 (single 12 MHz clock) and/or §7 (reference clock), `rtl/usb_utmi_phy.v`,
  `rtl/usb_sync_detector.v` (header comment's bit-lock argument),
  `verification/`
- **Does not change**: the ratified spec, the RTL, or the full-speed-only /
  UTMI-boundary-only scope.

## Context

Spec §7 ratifies a 12 MHz reference at +/-2500 ppm, unsynchronized to host
SOF. The RX samples once per 12 MHz clock = once per full-speed bit, with
no oversampling and no clock/data recovery (`rtl/usb_sync_detector.v`
header: bit-lock "reduces to" SYNC recognition because the decoder "must
itself have been tracking"). That argument assumes the host bit clock and
the device sample clock are the same clock. The host transmits on its own
clock, so they are not.

Issue #108 added the first testbench with an independent host rate and
phase. Result (sampled grid, 864 cases, not a continuous envelope): zero
offset passes everywhere; **every nonzero offset tested (+/-1000 ppm and
beyond) fails at 1024 post-SYNC bytes; every offset of magnitude >= 2500
ppm fails at 64 bytes in every start phase; the +/-5000 ppm class (the
~0.5 % worst relative offset of two +/-2500 ppm clocks, exact ratios
1.0025/0.9975 and 0.9975/1.0025) fails some phases even at 8 bytes.**
Failures are mostly silent corruption (398 of 408 include a wrong byte;
295 of the 408 never raised `RxError`). Pass/fail did not depend on
payload pattern. +/-2500 ppm against a *nominal* device clock already
fails at 64 bytes, so this is not only a worst-case-pair effect.

Consistent mechanism: with bit period equal to the sample period there is
no sampling margin, so about one bit is dropped (host fast) or repeated
(host slow) per `1e6/|ppm|` bits from the starting phase. Full-speed data
packets are far longer than the tens of bits that survive.

The §7 tolerance row is itself flagged as an unverified standard citation;
that is not litigated here. Whatever the correct host tolerance is, any
nonzero value implies a finite tolerated packet length for this sampler.

## Options (for operator ruling; none implemented)

- **A. Resync-on-transition with a sample clock above the bit rate.**
  Oversample the line (e.g. 4x or higher, clocked by an internal faster
  clock or PLL derived from the 12 MHz reference), and re-center the bit
  sampling phase on every J/K transition; NRZI plus bit stuffing guarantee
  a transition at least every 7 bit times, which bounds the free-running
  interval between resyncs, so the slip budget no longer scales with
  packet length. This is the standard full-speed approach and is
  full-speed-motivated (not HS). Cost: a clock above 12 MHz inside the
  block, which contradicts the §3 "single 12 MHz clock" architecture and
  needs a spec amendment; a new timing/area/power budget; a decision on
  where the faster clock comes from. Verification: this issue's matrix is
  the acceptance test and should pass at the endpoint ratios and 1024
  bytes.
- **B. Bound the supported packet length.** Declare the PHY correct only up
  to some maximum wire length at the §7 tolerance. The measured grid
  suggests the usable bound is below ~74 wire bits at +/-5000 ppm, i.e.
  roughly token/handshake-sized packets only, which excludes data packets
  and so does not make a USB device PHY. Listed for completeness; the
  evidence argues against it.
- **C. Tighten the device reference tolerance.** Does not help: the
  dominant term is the host's own offset, which the device cannot choose;
  the +/-2500 ppm-vs-nominal row already fails at 64 bytes.
- **D. Accept the limitation as-is and record it.** Leave RTL and spec
  unchanged and keep the failing record as the known-limitation evidence;
  the block then cannot claim §7 compliance and is not a functional
  receiver for real asynchronous hosts. Not recommended for a block whose
  point is to be finished and verified.

Recommendation (non-binding): **A**, because it is the only option that
makes the §7 claim true at packet lengths that matter; it is
full-speed-optimal in the sense that it adds only what 12 Mbps with
asynchronous clocks needs and nothing for high speed. The minimum
oversampling ratio and the clock source are the operator's call and should
be argued from this matrix.

## Constraints on any follow-up

- A separate issue, gated on this record's ruling, does any RTL or spec
  change. No agent relaxes §7 to make the result pass.
- The existing record is not edited; a fix produces a new record that
  re-runs `verification/request-usb-rx-clock-tolerance.json` and says why
  it supersedes or sits beside this one.
