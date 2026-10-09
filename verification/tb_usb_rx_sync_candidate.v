// tb_usb_rx_sync_candidate.v -- TESTBENCH SCAFFOLDING, not PHY RTL.
//
// Verification-only experiment harness for issue #123. It wraps the
// UNCHANGED production top level `rtl/usb_utmi_phy.v` and puts a
// *candidate* RX input synchronizer -- two flops per input, one chain on
// `rxdp` and an independent chain on `rxdm` -- in front of it, so one
// Icarus elaboration can run the existing independent-host stimulus
// against both the baseline (no synchronizer) and the candidate.
//
// This file is NOT a production change and NOT a decision. It lives under
// `verification/`, not `rtl/`, on purpose: whether the block gets an RX
// synchronizer at all, where it lives, and whether it is two independent
// per-line chains or something that samples the pair coherently are open
// questions for DR-0003's operator ruling (#126). The harness exists to
// MEASURE the consequences of the simplest structural candidate --
// including the ones it is expected to get wrong (manufactured SE0/SE1
// when the two chains capture a J<->K transition on different clocks) --
// not to argue for it. It simulates no analog metastability: every flop
// here resolves cleanly in zero-delay RTL, so nothing below says anything
// about MTBF.
//
// Structure (`cand_en` = 1):
//
//   rxdp -> dp_s1 -> dp_s2 --+-----------> u_phy.rxdp
//                            \-> dp_s3 --/  (only when inj_dp = 1)
//   rxdm -> dm_s1 -> dm_s2 --+-----------> u_phy.rxdm
//                            \-> dm_s3 --/  (only when inj_dm = 1)
//
//   * Two stages per input (`*_s1`, `*_s2`); the PHY sees `*_s2`.
//   * `inj_dp` / `inj_dm` are deterministic FAULT INJECTION: they route
//     that line through one extra flop (`*_s3`), modelling one input
//     resolving/capturing one clock later than the other (or both, when
//     both are set). This is a digital stand-in for unequal capture, not a
//     model of a metastable flop's analog resolution.
//   * Every stage (s1, s2, s3) resets SYNCHRONOUSLY to J (DP=1, DM=0)
//     whenever `rst_n` = 0 OR the UTMI `Reset` input = 1 -- the same
//     reset term the production wrapper derives internally
//     (`int_rst_n = rst_n & ~Reset`), so the candidate never presents a
//     stale pre-reset level after the PHY leaves reset.
//
// Baseline (`cand_en` = 0): `u_phy.rxdp`/`u_phy.rxdm` are the raw
// `rxdp`/`rxdm` ports through a combinational mux with a static select --
// the production RX path with zero added flops. `inj_*` are ignored in
// this mode. (The mux adds only a zero-time evaluation; at a host edge
// exactly coincident with a clock edge the capture order is
// scheduler-dependent in either mode and is not claimed.)
//
// Latency, input edge -> production LineState register (clock edges,
// counting the first rising edge at/after which the new level is
// captured as edge 1), with the decoder register `usb_line_state_decode`
// itself included:
//
//   baseline:              edge 1 (LineState updates on the capture edge)
//   candidate:             s1 @ edge 1, s2 @ edge 2, LineState @ edge 3
//   candidate + injection: +1 on the injected line(s) (LineState @ edge 4)
//
// i.e. the candidate adds exactly two clocks to everything downstream of
// LineState (NRZI decode, SYNC detection, RxActive, RxValid, EOP), and
// single-line injection additionally skews the two lines by one clock.
// `test_usb_rx_sync_candidate.py` measures these numbers rather than
// trusting this comment.
//
// `cand_en`, `inj_dp`, `inj_dm` are static experiment controls; the test
// sets them while the design is held in reset and never changes them
// mid-case. Ports otherwise mirror `usb_utmi_phy` one-for-one so the
// shared stimulus/monitor code can drive either top level.

`default_nettype none

module tb_usb_rx_sync_candidate (
    input  wire clk,
    input  wire rst_n,

    input  wire        TxValid,
    output wire        TxReady,
    input  wire [7:0]  DataOut,

    output wire        RxValid,
    output wire        RxActive,
    output wire        RxError,
    output wire [7:0]  DataIn,

    output wire [1:0]  LineState,
    input  wire [1:0]  OpMode,
    input  wire        TermSelect,
    input  wire        XcvrSelect,
    input  wire        SuspendM,
    input  wire        Reset,

    output wire txdp,
    output wire txdm,

    input  wire rxdp,
    input  wire rxdm,

    // experiment controls (static per case)
    input  wire cand_en,
    input  wire inj_dp,
    input  wire inj_dm,

    // observation: what the production PHY's rxdp/rxdm actually see
    output wire phy_rxdp,
    output wire phy_rxdm
);

  // Same reset term the production wrapper builds internally.
  wire cand_rst_n = rst_n & ~Reset;

  reg dp_s1, dp_s2, dp_s3;
  reg dm_s1, dm_s2, dm_s3;

  always @(posedge clk) begin
    if (!cand_rst_n) begin
      // J: DP = 1, DM = 0 (matches usb_line_state_decode's reset-to-J).
      dp_s1 <= 1'b1;
      dp_s2 <= 1'b1;
      dp_s3 <= 1'b1;
      dm_s1 <= 1'b0;
      dm_s2 <= 1'b0;
      dm_s3 <= 1'b0;
    end else begin
      dp_s1 <= rxdp;
      dp_s2 <= dp_s1;
      dp_s3 <= dp_s2;
      dm_s1 <= rxdm;
      dm_s2 <= dm_s1;
      dm_s3 <= dm_s2;
    end
  end

  wire cand_dp = inj_dp ? dp_s3 : dp_s2;
  wire cand_dm = inj_dm ? dm_s3 : dm_s2;

  assign phy_rxdp = cand_en ? cand_dp : rxdp;
  assign phy_rxdm = cand_en ? cand_dm : rxdm;

  usb_utmi_phy u_phy (
      .clk        (clk),
      .rst_n      (rst_n),
      .TxValid    (TxValid),
      .TxReady    (TxReady),
      .DataOut    (DataOut),
      .RxValid    (RxValid),
      .RxActive   (RxActive),
      .RxError    (RxError),
      .DataIn     (DataIn),
      .LineState  (LineState),
      .OpMode     (OpMode),
      .TermSelect (TermSelect),
      .XcvrSelect (XcvrSelect),
      .SuspendM   (SuspendM),
      .Reset      (Reset),
      .txdp       (txdp),
      .txdm       (txdm),
      .rxdp       (phy_rxdp),
      .rxdm       (phy_rxdm)
  );

endmodule

`default_nettype wire
