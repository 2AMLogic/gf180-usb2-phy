// usb_line_state_decode.v -- LineState[1:0] decode from the two single-ended
// receivers.
//
// spec/usb2-device-phy.md #4 defines the receiver set: a differential
// receiver plus one single-ended receiver each on D+ and D-. This module
// implements the digital half of that section's own sentence -- "the two
// single-ended receivers, combined, give the line-state decode
// (LineState[1:0] in #3)". The differential receiver's recovered bit
// (`RXD` in design/differential_receiver.sch) is NRZI/framing input, not a
// LineState input; it is consumed by `usb_nrzi_decoder`, not here.
//
// Port names deliberately match the analog single-ended receiver cells'
// own pin names, `RXDP`/`RXDM` (design/README.md, issue #29:
// "se_receiver_dp.sch / se_receiver_dm.sch ... DP/RXDP vs DM/RXDM"),
// lower-cased to match this repo's Verilog port-naming convention
// elsewhere (`rst_n`, `line_bit`, ...): `rxdp` is the digital output of
// the single-ended receiver on D+, `rxdm` the same for D-.
//
// Encoding (this module's own choice; spec #3/#4 name the four states but
// not a numeric encoding). Full-speed device idle is D+ high / D- low
// (spec #4, #5's 1.5 kohm D+ pull-up), i.e. J. SE1 (both high) is the
// illegal/undefined line condition USB 2.0 never produces in normal
// operation; it is decoded distinctly rather than aliased to J or K so a
// downstream consumer can tell the two apart, but no submodule in this
// repo treats SE1 as anything other than "not a valid J/K sample" -- see
// `usb_sync_detector.v` and this wrapper's line-valid gating in
// `usb_utmi_phy.v`.
//
//     LineState[1:0] = {rxdm, rxdp}
//
//     rxdp rxdm | LineState | Meaning (FS device)
//     ---- ---- | --------- | -------------------
//       1    0  |    2'b01  | J (idle)
//       0    1  |    2'b10  | K
//       0    0  |    2'b00  | SE0 (EOP / reset candidate, spec #4)
//       1    1  |    2'b11  | SE1 (illegal, not produced in normal operation)
//
// Rate: registered every clock at the spec #3 interface clock of 12 MHz,
// matching every other module in this directory. No metastability
// synchronizer is instantiated here -- `rxdp`/`rxdm` are assumed already
// stable with respect to this domain's setup/hold by the time they reach
// this purely digital block; a synchronizer, if the analog/digital
// integration needs one, belongs at that boundary, not inside this
// digital-only module.

`default_nettype none

module usb_line_state_decode (
    input  wire clk,
    input  wire rst_n,       // active-low, synchronous
    input  wire rxdp,        // single-ended receiver output, D+
    input  wire rxdm,        // single-ended receiver output, D-
    output reg  [1:0] line_state
);

  always @(posedge clk) begin
    if (!rst_n) begin
      // Reset defaults to J, matching the idle state every other module's
      // `init`/reset already assumes (see e.g. usb_nrzi_encoder.v).
      line_state <= 2'b01;
    end else begin
      line_state <= {rxdm, rxdp};
    end
  end

endmodule

`default_nettype wire
