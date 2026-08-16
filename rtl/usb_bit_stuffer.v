// usb_bit_stuffer.v -- USB bit stuffing for the transmit path.
//
// spec/usb2-device-phy.md #2 puts "Bit stuffing (TX, after every six
// consecutive 1s)" inside this block's UTMI boundary. USB guarantees a
// minimum transition density on the wire by inserting a 0 into the data
// stream after every six consecutive 1s; because a 1 is encoded as "no
// transition" (see `usb_nrzi_encoder`), an unbounded run of 1s would leave
// the line static and starve the receiver's clock recovery.
//
// Ordering: stuffing happens *before* NRZI encoding on the way out. The TX
// bit path is therefore
//
//     data -> usb_bit_stuffer -> usb_nrzi_encoder -> line
//
// and the RX path is its mirror image (`usb_nrzi_decoder` then
// `usb_bit_destuffer`).
//
// The stuffed 0 is inserted unconditionally after six 1s, even when the
// next data bit is itself a 0 -- the receiver removes a bit at exactly the
// same position, so the rule has to be positional, not data-dependent.
//
// Backpressure: this module *adds* bits, so it cannot accept an input bit
// on the clock where it emits a stuffed one. `in_ready` goes low for that
// single clock and the upstream source must hold `in_valid` / `in_bit`
// until it is high again -- an ordinary valid/ready handshake, with the
// transfer taking place on the rising edge where both are asserted.
// `in_ready` is combinational from internal state only (it does not depend
// on `in_valid`), so there is no ready/valid combinational loop.
//
// Rate: one output bit per clock at the spec #3 interface clock of 12 MHz.

`default_nettype none

module usb_bit_stuffer (
    input  wire clk,
    input  wire rst_n,        // active-low, synchronous
    input  wire init,         // synchronous packet-start clear: run count -> 0
    input  wire in_valid,     // `in_bit` carries a bit this clock
    input  wire in_bit,       // unstuffed data bit
    output wire in_ready,     // low for the clock on which a bit is stuffed
    output reg  out_valid,    // `out_bit` is a bit of the stuffed stream
    output reg  out_bit,      // stuffed data bit
    output reg  out_stuffed   // this `out_bit` is an inserted 0, not data
);

  // Number of consecutive 1s already emitted, saturating at the stuff
  // threshold: 0..6 needs 3 bits.
  localparam [2:0] STUFF_AFTER = 3'd6;

  reg [2:0] ones;

  // Six 1s are already on the wire -> this clock belongs to the stuffed 0.
  wire stuffing = (ones == STUFF_AFTER);

  assign in_ready = ~stuffing;

  always @(posedge clk) begin
    if (!rst_n || init) begin
      ones        <= 3'd0;
      out_valid   <= 1'b0;
      out_bit     <= 1'b0;
      out_stuffed <= 1'b0;
    end else if (in_valid) begin
      if (stuffing) begin
        // Insert the 0. `in_ready` is low this clock, so whatever the
        // source is presenting is held and consumed on the next one.
        //
        // Note this arm is gated on `in_valid`: the stuffed bit precedes
        // the seventh bit, so it is only emitted once a seventh bit
        // actually shows up. A stream that simply ends on a run of six 1s
        // gets no trailing stuffed bit -- the same boundary
        // `usb_bit_model.bit_stuff` implements, and the same one
        // `usb_bit_destuffer` expects on the way back in.
        ones        <= 3'd0;
        out_valid   <= 1'b1;
        out_bit     <= 1'b0;
        out_stuffed <= 1'b1;
      end else begin
        ones        <= in_bit ? (ones + 3'd1) : 3'd0;
        out_valid   <= 1'b1;
        out_bit     <= in_bit;
        out_stuffed <= 1'b0;
      end
    end else begin
      // Idle: hold the run count so a gap in the source stream does not
      // silently reset it. A packet boundary uses `init` for that.
      out_valid   <= 1'b0;
      out_stuffed <= 1'b0;
    end
  end

endmodule

`default_nettype wire
