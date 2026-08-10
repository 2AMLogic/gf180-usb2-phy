// harness_counter.v -- throwaway smoke-test vehicle for the digital
// cocotb + klt verification/synthesis harness bootstrapped by issue #7.
//
// This module carries ZERO USB semantics: no NRZI encode/decode, no bit
// stuffing, no SYNC/EOP handling, nothing UTMI-boundary-shaped. It exists
// only to prove that the harness -- cocotb + Icarus for functional
// verification, `klt synthesize` for gf180mcu synthesis -- elaborates,
// simulates, and reports results end-to-end on a real (if trivial)
// design. Real PHY digital logic (NRZI/bit-stuffing/SYNC-EOP, per
// spec/usb2-device-phy.md #2) is future work and does not belong here --
// see CLAUDE.md's scope-discipline rule.
//
// Behavior: a plain WIDTH-bit up counter with a synchronous, active-low
// reset and a count-enable. Nothing more.

`default_nettype none

module harness_counter #(
    parameter integer WIDTH = 8
) (
    input  wire             clk,
    input  wire             rst_n,  // active-low, synchronous
    input  wire             en,     // count enable
    output reg  [WIDTH-1:0] count
);

  always @(posedge clk) begin
    if (!rst_n) begin
      count <= {WIDTH{1'b0}};
    end else if (en) begin
      count <= count + 1'b1;
    end
  end

endmodule

`default_nettype wire
