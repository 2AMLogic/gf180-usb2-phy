// usb_nrzi_encoder.v -- NRZI line encoding for the transmit path.
//
// spec/usb2-device-phy.md #2 puts "NRZI encode (TX)" inside this block's
// UTMI boundary. USB NRZI is inverted-sense NRZI: a data 0 forces a
// transition on the line, a data 1 forces no transition (the line holds).
//
// Line encoding convention used throughout this repo's digital sources:
//
//     line_bit == 1'b1  =>  J state
//     line_bit == 1'b0  =>  K state
//
// For a full-speed device (spec #4/#5: 1.5 kohm pull-up on D+), J is
// D+ high / D- low and K is the complement -- but this module deals only
// in the abstract J/K bit. Mapping J/K onto the D+/D- pads, and the SE0
// states that are neither J nor K, belongs to the line-state/EOP logic
// above this module, not here.
//
// Rate: one bit per clock at the spec #3 interface clock of 12 MHz -- the
// raw full-speed bit rate. There is deliberately no dual-rate / oversampled
// mode: high speed is out of scope per spec #1 and CLAUDE.md.
//
// Interface: a bare valid strobe, no backpressure. The encoder consumes one
// bit per asserted `data_valid` and can never stall, so it needs no ready
// signal -- unlike `usb_bit_stuffer`, which inserts bits and therefore must
// stall its upstream. `line_valid` is `data_valid` delayed by one clock
// (the registered output). When `line_valid` is low the line holds its
// last state, which is what the driver must do between bits anyway.

`default_nettype none

module usb_nrzi_encoder (
    input  wire clk,
    input  wire rst_n,       // active-low, synchronous
    input  wire init,        // synchronous packet-start clear: line -> J
    input  wire data_valid,  // `data_bit` carries a bit this clock
    input  wire data_bit,    // pre-NRZI data bit
    output reg  line_valid,  // `line_bit` is a freshly encoded bit
    output reg  line_bit     // 1 = J, 0 = K
);

  always @(posedge clk) begin
    if (!rst_n || init) begin
      // Idle / packet start is J. Every USB packet's SYNC field is encoded
      // starting from the idle J state, so `init` gives the framing logic
      // above a way to re-establish that reference without a block reset.
      line_bit   <= 1'b1;
      line_valid <= 1'b0;
    end else begin
      line_valid <= data_valid;
      // data 0 -> transition; data 1 -> hold.
      if (data_valid && !data_bit) begin
        line_bit <= ~line_bit;
      end
    end
  end

endmodule

`default_nettype wire
