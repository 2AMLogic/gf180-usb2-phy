// usb_nrzi_decoder.v -- NRZI line decoding for the receive path.
//
// spec/usb2-device-phy.md #2 puts "NRZI decode (RX)" inside this block's
// UTMI boundary. The exact inverse of `usb_nrzi_encoder`: a transition on
// the line recovers a data 0, no transition recovers a data 1.
//
// Line encoding convention (identical to the encoder's):
//
//     line_bit == 1'b1  =>  J state
//     line_bit == 1'b0  =>  K state
//
// `line_bit` is expected to be the already-sampled line state for one bit
// time -- bit-level clock/data recovery (sampling the recovered line at the
// right instant, and the SYNC-field bit-lock that establishes it) lives
// above this module, not here.
//
// Rate: one bit per clock at the spec #3 interface clock of 12 MHz. No
// oversampling, no dual-rate mode -- high speed is out of scope per spec #1.
//
// A stream with no transitions at all (an idle line held at J) decodes to a
// run of 1s. That is correct NRZI behavior and not an error on its own; it
// is `usb_bit_destuffer` that turns an over-long run of 1s into a
// bit-stuff error.

`default_nettype none

module usb_nrzi_decoder (
    input  wire clk,
    input  wire rst_n,       // active-low, synchronous
    input  wire init,        // synchronous packet-start clear: reference -> J
    input  wire line_valid,  // `line_bit` carries a sampled bit this clock
    input  wire line_bit,    // 1 = J, 0 = K
    output reg  data_valid,  // `data_bit` is a freshly decoded bit
    output reg  data_bit     // recovered pre-NRZI data bit
);

  // Line state of the previous bit time -- the transition reference.
  reg prev_line;

  always @(posedge clk) begin
    if (!rst_n || init) begin
      // Idle / packet start is J, matching the encoder's reset state.
      prev_line  <= 1'b1;
      data_valid <= 1'b0;
      data_bit   <= 1'b0;
    end else begin
      data_valid <= line_valid;
      if (line_valid) begin
        // no transition -> 1; transition -> 0.
        data_bit  <= ~(line_bit ^ prev_line);
        prev_line <= line_bit;
      end
    end
  end

endmodule

`default_nettype wire
