// usb_eop_detector.v -- EOP detection and reset-condition timing for the
// receive path.
//
// spec/usb2-device-phy.md #2 puts "EOP (Single-Ended Zero, SE0) ...
// detection (RX)" inside this block's UTMI boundary, and #4 states the
// disambiguation rule this module exists to implement: SE0 held for 2 bit
// times is EOP, SE0 held >= 2.5 microseconds is a reset condition. Both
// are measured from the same underlying signal (`line_state == SE0`) and
// differ only in hold duration, so one counter drives both outputs.
//
// At the spec #3 interface clock of exactly 12.000 MHz, 2.5us is exactly
// 30 clock periods (2.5e-6 s / (1 / 12e6 Hz) = 30) -- no rounding, no
// fractional-cycle ambiguity, which is why RESET_CYCLES below is an exact
// integer rather than an approximation.
//
// `eop`: a single-clock pulse asserted on the clock where `line_state` has
// now been SE0 for exactly EOP_BITS (2) consecutive clocks. It fires
// exactly once per contiguous SE0 run (it does not re-fire if SE0
// continues beyond 2 clocks, e.g. into a reset condition) -- a real EOP is
// always exactly this long before the line returns to J
// (`usb_utmi_phy.v`'s TX EOP generation produces exactly this shape), so
// this is the correct point to end an in-progress RX reception. It is the
// caller's (the top-level wrapper's) job to only *act* on `eop` while a
// packet is actually being received; this module makes no claim about
// packet framing state, only about the line.
//
// `bus_reset`: a level, not a pulse. Asserted starting the clock where
// `line_state` has been SE0 for RESET_CYCLES (30) consecutive clocks, and
// held asserted for as long as the SE0 condition continues; deasserted the
// clock after `line_state` first leaves SE0. Consistent with spec #4's
// framing of reset as a *duration-qualified* condition of the line itself,
// not an edge event.
//
// Deliberately NOT implemented here: this module does not drive (or even
// define) the UTMI `Reset` port. Per spec #3's port table and standard
// UTMI usage, `Reset` is an INPUT to the PHY, asserted by the link/SIE
// once *it* has observed a sustained SE0 via `LineState` and decided to
// command a reset -- that decision is SIE-layer policy, out of scope per
// CLAUDE.md. `bus_reset` here is purely an internal signal `usb_utmi_phy.v`
// uses to abort an in-progress RX reception if the line goes silent for
// that long mid-packet; it is not exposed as a top-level port because
// spec #3 defines no such output.
//
// Rate: one sample per clock at 12 MHz, matching every module in this
// directory.

`default_nettype none

module usb_eop_detector (
    input  wire clk,
    input  wire rst_n,          // active-low, synchronous
    input  wire [1:0] line_state,  // usb_line_state_decode's output
    output reg  eop,             // one-clock pulse: SE0 held for 2 bit times
    output reg  bus_reset        // level: SE0 held for >= 2.5us (30 clocks)
);

  localparam [1:0] LS_SE0 = 2'b00;

  // 2 bit times (spec #4's EOP threshold).
  localparam [5:0] EOP_CYCLES = 6'd2;
  // 2.5us at exactly 12.000 MHz (see header).
  localparam [5:0] RESET_CYCLES = 6'd30;

  wire is_se0 = (line_state == LS_SE0);

  // Consecutive SE0 samples so far, saturating at RESET_CYCLES so a long
  // reset hold cannot wrap the counter.
  reg [5:0] se0_count;

  always @(posedge clk) begin
    if (!rst_n) begin
      se0_count <= 6'd0;
      eop       <= 1'b0;
      bus_reset <= 1'b0;
    end else begin
      eop <= 1'b0;  // default: pulse, re-armed every clock
      if (is_se0) begin
        // Threshold checks use the pre-update count: on the clock where
        // se0_count is about to become EOP_CYCLES (i.e. this is the
        // EOP_CYCLES-th consecutive SE0 sample), fire `eop` now.
        if (se0_count == (EOP_CYCLES - 6'd1)) eop <= 1'b1;
        if (se0_count == (RESET_CYCLES - 6'd1)) bus_reset <= 1'b1;
        if (se0_count < RESET_CYCLES) se0_count <= se0_count + 6'd1;
      end else begin
        se0_count <= 6'd0;
        bus_reset <= 1'b0;
      end
    end
  end

endmodule

`default_nettype wire
