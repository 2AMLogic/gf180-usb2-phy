// usb_bit_destuffer.v -- USB bit destuffing for the receive path.
//
// spec/usb2-device-phy.md #2 puts "bit destuffing (RX)" inside this block's
// UTMI boundary. The exact inverse of `usb_bit_stuffer`: after six
// consecutive 1s in the received (already NRZI-decoded) stream, the next
// bit is the transmitter's inserted 0 and is removed rather than passed on.
//
// The RX bit path is
//
//     line -> usb_nrzi_decoder -> usb_bit_destuffer -> data
//
// the mirror image of the TX path in `usb_bit_stuffer`'s header.
//
// Error detection: the removed bit MUST be a 0. If it is a 1 -- i.e. seven
// consecutive 1s arrived where the protocol allows at most six -- the
// stream is malformed and `stuff_err` pulses high for one clock. Common
// causes are a bit-level sampling slip or line noise. This module only
// reports the event; latching it into the UTMI `RxError` status signal is
// the framing/UTMI wrapper's job, not this module's (spec #3 lists
// `RxError` among the core RX signals, and CLAUDE.md's scope-discipline
// rule keeps everything above the bit level out of here).
//
// The offending bit is dropped either way: the stuff position is fixed by
// the bit count, so the receiver stays bit-aligned with the transmitter and
// the packet is discarded by the layer that consumes `stuff_err`.
//
// Removing a bit means this module *emits fewer* bits than it consumes, so
// it never needs to stall its source -- there is no ready signal, unlike
// `usb_bit_stuffer`.
//
// Rate: one input bit per clock at the spec #3 interface clock of 12 MHz.

`default_nettype none

module usb_bit_destuffer (
    input  wire clk,
    input  wire rst_n,      // active-low, synchronous
    input  wire init,       // synchronous packet-start clear: run count -> 0
    input  wire in_valid,   // `in_bit` carries a received bit this clock
    input  wire in_bit,     // NRZI-decoded, still-stuffed data bit
    output reg  out_valid,  // `out_bit` is a destuffed data bit
    output reg  out_bit,    // destuffed data bit
    output reg  stuff_err   // one-clock pulse: seven consecutive 1s
);

  localparam [2:0] STUFF_AFTER = 3'd6;

  // Number of consecutive 1s already accepted into the output stream.
  reg [2:0] ones;

  // Six 1s have been accepted -> the bit arriving now is the stuffed one.
  wire at_stuff = (ones == STUFF_AFTER);

  always @(posedge clk) begin
    if (!rst_n || init) begin
      ones      <= 3'd0;
      out_valid <= 1'b0;
      out_bit   <= 1'b0;
      stuff_err <= 1'b0;
    end else if (in_valid) begin
      if (at_stuff) begin
        // Remove the stuffed bit. It must be a 0; a 1 is a stuff error.
        ones      <= 3'd0;
        out_valid <= 1'b0;
        stuff_err <= in_bit;
      end else begin
        ones      <= in_bit ? (ones + 3'd1) : 3'd0;
        out_valid <= 1'b1;
        out_bit   <= in_bit;
        stuff_err <= 1'b0;
      end
    end else begin
      // Idle: hold the run count across a gap in the source stream; a
      // packet boundary uses `init` to clear it.
      out_valid <= 1'b0;
      stuff_err <= 1'b0;
    end
  end

endmodule

`default_nettype wire
