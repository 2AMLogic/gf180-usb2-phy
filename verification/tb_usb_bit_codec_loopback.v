// tb_usb_bit_codec_loopback.v -- TESTBENCH SCAFFOLDING, not PHY RTL.
//
// This file lives under `verification/` rather than `rtl/` on purpose: it
// is a structural harness that exists only so one Icarus elaboration can
// contain the whole TX bit path *and* the whole RX bit path, letting
// `test_usb_bit_codec_loopback.py` make an RTL-to-RTL round-trip claim
// (bits in == bits out) instead of an RTL-against-Python-model one.
//
// It is deliberately NOT the top-level digital wrapper. The UTMI-facing
// wrapper that assembles the digital submodules -- together with SYNC
// generation/detection, EOP, and `LineState[1:0]` decode -- is a separate
// piece of work (issue #32) and belongs under `rtl/` when it lands. This
// harness has no SYNC, no EOP, no line-state decode, no UTMI signals, and
// no serial-interface-engine semantics whatsoever (CLAUDE.md's
// scope-discipline rule).
//
// Wiring, per spec/usb2-device-phy.md #2 (stuffing sits below NRZI on TX,
// above it on RX):
//
//   tx_bit -> usb_bit_stuffer -> usb_nrzi_encoder -+
//                                                  |  line_bit (J/K)
//   rx_bit <- usb_bit_destuffer <- usb_nrzi_decoder +
//
// The internal line is a direct wire, not a modelled analog channel: J/K to
// D+/D- mapping and the receivers themselves are analog work tracked
// elsewhere.

`default_nettype none

module tb_usb_bit_codec_loopback (
    input  wire clk,
    input  wire rst_n,
    input  wire init,

    // TX side: valid/ready, because the stuffer stalls when it inserts.
    input  wire tx_valid,
    input  wire tx_bit,
    output wire tx_ready,

    // The encoded line between the two paths, exposed for observation.
    output wire line_valid,
    output wire line_bit,

    // RX side: valid only -- destuffing removes bits, never adds them.
    output wire rx_valid,
    output wire rx_bit,
    output wire rx_stuff_err,

    // Stuffer's own "this bit was inserted" marker, exposed for observation.
    output wire tx_stuffed
);

  wire stuffed_valid;
  wire stuffed_bit;

  usb_bit_stuffer u_stuffer (
      .clk        (clk),
      .rst_n      (rst_n),
      .init       (init),
      .in_valid   (tx_valid),
      .in_bit     (tx_bit),
      .in_ready   (tx_ready),
      .out_valid  (stuffed_valid),
      .out_bit    (stuffed_bit),
      .out_stuffed(tx_stuffed)
  );

  usb_nrzi_encoder u_encoder (
      .clk       (clk),
      .rst_n     (rst_n),
      .init      (init),
      .data_valid(stuffed_valid),
      .data_bit  (stuffed_bit),
      .line_valid(line_valid),
      .line_bit  (line_bit)
  );

  wire decoded_valid;
  wire decoded_bit;

  usb_nrzi_decoder u_decoder (
      .clk       (clk),
      .rst_n     (rst_n),
      .init      (init),
      .line_valid(line_valid),
      .line_bit  (line_bit),
      .data_valid(decoded_valid),
      .data_bit  (decoded_bit)
  );

  usb_bit_destuffer u_destuffer (
      .clk      (clk),
      .rst_n    (rst_n),
      .init     (init),
      .in_valid (decoded_valid),
      .in_bit   (decoded_bit),
      .out_valid(rx_valid),
      .out_bit  (rx_bit),
      .stuff_err(rx_stuff_err)
  );

endmodule

`default_nettype wire
