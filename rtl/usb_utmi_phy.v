// usb_utmi_phy.v -- top-level UTMI-facing wrapper.
//
// spec/usb2-device-phy.md #3 defines this block's digital interface as
// UTMI: an 8-bit parallel data bus at a 12 MHz interface clock (the raw
// full-speed bit rate -- one bit per clock, no oversampling, see #3's
// engineering note). This module assembles every digital submodule this
// repo owns -- `usb_line_state_decode`, `usb_sync_detector`,
// `usb_eop_detector`, plus this wrapper's own framing -- around the four
// USB-spec-defined protocol transforms, which since issue #84 are
// **vendored byte-exact** from the rule-9 master under `rtl/common/`
// (`usb_bit_stuffer`, `usb_nrzi_encoder`, `usb_nrzi_decoder`,
// `usb_bit_destuffer`; `reuse.lock.json` pins them to
// 2AMLogic/sky130-usb2-phy @ 4f3b2c72). The port set is unchanged from
// the pre-vendoring wrapper: `TxValid`/`TxReady`/`DataOut[7:0]`,
// `RxValid`/`RxActive`/`RxError`/`DataIn[7:0]`, `LineState[1:0]`,
// `OpMode[1:0]`, `TermSelect`, `XcvrSelect`, `SuspendM`, `Reset`.
//
// Interface adaptation (spec/decisions/0002) -- the whole point of this
// file. The vendored modules expose sky130-usb2-phy's canonical
// interfaces (its DR-0002 Decision 3): strobed bit-time handshakes
// (`bit_stb`/`bit_strobe`, `consume`, `stuff_pending_after`, `sof`,
// `bypass`, `bit_is_jk`, `enable`) rather than this repo's former
// valid/ready + `init` streaming shape. The vendored bytes never change,
// so every adaptation lives HERE, at the boundary:
//
//   * Clocking: the canonical port names say `clk_144`/`rst_144_n` --
//     the master's 144 MHz oversampling domain. This repo has no such
//     domain (spec #3: one bit per 12 MHz clock, no oversampling), so
//     the wrapper instantiates them on the interface clock and the
//     strobes (`bit_stb`/`bit_strobe`) are simply asserted on every
//     clock of an active bit stream -- one bit-time per clock. The
//     `_144` suffix is the master's domain vocabulary, not a frequency
//     requirement of the transforms (recorded in spec/decisions/0002 so
//     the next reader does not "fix" it).
//   * TX stuffing scope: the canonical architecture runs SYNC *around*
//     the stuffer (SYNC is framing, never stuffed; the stuffer's `sof`
//     marks the first post-SYNC bit and starts its run counter fresh),
//     where this repo's former local modules ran SYNC *through* the
//     stuffer. The wrapper's TX state machine follows the master's
//     `usb_tx_framer.v` shape (IDLE -> SYNC -> DATA -> FLUSH -> HOLD ->
//     EOP0/EOP1/EOPJ) accordingly, with one deliberate correction: the
//     entering edge encodes SYNC bit 0 from `sync_idx`'s pre-edge value,
//     so this wrapper re-arms `sync_idx` to 0 when SYNC exits -- the
//     master's own framer leaves it at 7, which encodes SYNC_BYTE[7] (a
//     1) as bit 0 of every packet after the first and corrupts the SYNC
//     pattern (its single-packet testbench never reaches the case;
//     pinned here by test_loopback_back_to_back_packets_minimal_gap,
//     and recorded in spec/decisions/0002).
//   * Flush duty: the former local stuffer's flush idiom (assert
//     `in_valid` for one clock while `in_ready` is low) is replaced by
//     the canonical lookahead: when the packet's last real bit is
//     consumed with `stuff_pending_after` high, the wrapper spends one
//     more bit-time in TX_FLUSH (the stuffer emits the USB 2.0 #7.1.9
//     forced stuff bit; `consume` reads 0), then frames EOP. TX_HOLD
//     gives the last encoded level (real or stuffed) its own visible
//     bit-time on the wire before the EOP override takes the pads --
//     without it, the edge that finalizes the last level would be the
//     same edge that switches the pads to SE0, silently dropping it.
//   * RX gating: the canonical destuffer has no `init`; its `enable`
//     (the master's SOP..EOP `rx_active` gating) replaces the former
//     per-packet `init` from `usb_sync_detector.sync_next`. This
//     wrapper arms `rx_receiving` from `sync_next` (one clock before
//     the first post-SYNC bit reaches the destuffer) and feeds that
//     same `rx_receiving` to `enable`, so the run counter starts at
//     zero exactly at the first PID bit and self-clears when EOP drops
//     `rx_receiving`. While `enable` is low the destuffer is
//     transparent (it must be: the canonical design searches for the
//     never-stuffed SYNC pattern on its output), so the wrapper's byte
//     assembly ignores its `bit_valid` until `rx_receiving` is high.
//   * `bit_is_jk` is load-bearing: NRZI is defined only over J/K, so
//     SE0/SE1 cells (EOP, bus reset) must not decode as data. The
//     wrapper derives it from the line-state decode -- the strobe
//     itself is asserted only on genuine J/K samples -- so EOP never
//     decodes as data bits.
//   * `OpMode` IS now consumed (a change from the former wrapper, which
//     left it unconnected): raw/transparent test mode `2'b10` drives
//     the vendored modules' `bypass` -- no bit stuffing, no NRZI
//     transform -- on the packet body only; SYNC is PHY-generated
//     framing and stays NRZI-encoded regardless (the master's own
//     `usb_tx_framer.v` convention, mirrored in spec/decisions/0002).
//
// Wire-level ports, matching the analog cells' own pin names (not a UTMI
// #3 concept -- #3 stops at the digital interface; these are what
// connects to `design/differential_driver.sch` (`TXDP`/`TXDM`,
// "TXDx=1 => Dx driven high") and `design/se_receiver_dp.sch` /
// `se_receiver_dm.sch` (`RXDP`/`RXDM`), lower-cased to match this
// directory's Verilog convention):
//
//   txdp, txdm  -- drive the differential driver's TXDP/TXDM inputs.
//   rxdp, rxdm  -- read from the two single-ended receivers' RXDP/RXDM
//                  outputs.
//
// J/K -> D+/D- mapping, matching the canonical encoder's "level_out 1 =
// J-equivalent (idle)" convention and `usb_line_state_decode`'s
// LineState encoding:
//
//     J: txdp=1, txdm=0      K: txdp=0, txdm=1      SE0 (EOP): txdp=0, txdm=0
//
// txdp/txdm are a combinational mux (the canonical framer's pad stage):
// forced SE0/SE0/J through the EOP tail, the encoder's registered
// `level_out` while sending (SYNC/DATA/FLUSH/HOLD -- the encoder
// registers the level on the strobe edge, so each bit gets exactly one
// full clock period on the wire), and idle J otherwise.
//
// SYNC's wire pattern, derived once here rather than repeated at each
// module: SYNC is the fixed pre-stuff byte 8'h80 (0000_0001), sent LSB
// first per USB's byte convention -- i.e. transmission order
// 0,0,0,0,0,0,0,1. NRZI-encoded from the idle-J reference (a data 0
// transitions, a data 1 holds -- `usb_nrzi_encoder.v`), bit by bit,
// starting at J:
//   bit0=0: transition J->K.  bit1=0: transition K->J.  bit2=0: J->K.
//   bit3=0: K->J.  bit4=0: J->K.  bit5=0: K->J.  bit6=0: J->K.
//   bit7=1: hold at K.
// Line states after each bit: K,J,K,J,K,J,K,K -- the textbook "KJKJKJKK"
// SYNC pattern. Verified directly in `test_usb_utmi_phy.py`
// (`test_tx_sync_pattern_is_kjkjkjkk`).
//
// TX state machine -- SYNC generation, byte serialization, stuff-flush,
// EOP generation, in the canonical framer's shape.
//
// SYNC is byte "-1" of the packet on the wire but NOT through the
// stuffer: the `entering_sync` term encodes SYNC bit 0 on the very
// IDLE->SYNC transition edge (the encoder's `sof` re-derives its
// transition reference from idle J on that edge), TX_SYNC encodes bits
// 1-7, and TX_DATA presents the first payload bit to the stuffer with
// ITS `sof` (first byte, bit 0) so the stuffable run counter starts
// fresh at the first post-SYNC bit -- the canonical stuffing scope
// (#7.1.9: stuffing covers PID..CRC, never SYNC).
//
// Byte serialization is a plain `byte_reg`/`byte_idx` shifter (no skid
// buffer): `TxReady` is asserted for the whole bit-time in which a
// byte's last real bit is being consumed (`byte_idx == 7 &&
// stuff_consume`), so a byte's request-to-request interval is 8 clocks
// normally and stretches to exactly 9 when a stuff bit falls inside it
// (the stuffer spends one clock not consuming -- `consume` reads 0 --
// and the same bit is re-presented the next clock). When the link stops
// asserting `TxValid` at a terminal bit, the wrapper checks the
// canonical `stuff_pending_after` lookahead: high means USB 2.0 #7.1.9's
// forced trailing stuff bit is owed, so TX_FLUSH spends that one
// bit-time before TX_HOLD and the EOP tail.
//
// RX pipeline -- free-running NRZI decode, SYNC-searched, enable-gated
// destuffing.
//
// `usb_nrzi_decoder` is fed continuously and never re-initialized after
// the block's own reset (the canonical module has no `init` port at
// all): `bit_strobe`/`bit_is_jk` are asserted whenever `line_state` is
// a genuine J or K sample (never during SE0/SE1), so the decoder simply
// holds across EOP/idle gaps and SE0 cells never decode as data. This
// is deliberate, not an oversight: a mid-packet re-reference would be
// WRONG immediately after a SYNC field, because the actual line
// reference at that point is K (SYNC's last bit), not J. Free-running
// avoids the problem: the decoder's transition tracking self-corrects
// to the true line state within one real J/K sample of any gap.
//
// `usb_sync_detector` (local, architecture-bound per the master's
// DR-0002 Decision 4) matches on the DECODED bit stream: it watches the
// decoder's output for the fixed byte value 8'h80. Its `sync_next`
// (combinational, high on the same clock the decoder emits SYNC's own
// final bit) arms `rx_receiving` one clock later -- exactly the clock
// the decoder emits the first post-SYNC bit -- so the destuffer's
// `enable` is high for that bit's `data_strobe` and its run counter
// starts from zero on the first PID bit (see the adaptation notes
// above).
//
// `usb_eop_detector` runs unconditionally off `LineState`, independent
// of RX framing state (see its own header) -- `eop` (RX_ACTIVE ends
// normally) and the internal-only `bus_reset` (RX_ACTIVE aborts) both
// simply clear `rx_receiving`.
//
// Scope choices, stated explicitly (per CLAUDE.md's honesty convention,
// same pattern rtl/README.md uses for the bit-level codec):
//
// - `OpMode` raw mode (`2'b10`) is consumed as the vendored modules'
//   `bypass`; every other encoding is ignored -- this FS-only,
//   device-only block has no HS chirp mode, no host/OTG role, no LS
//   support (spec #3's own "UTMI, not UTMI+" decision).
// - `TermSelect`, `XcvrSelect` are present as ports (spec #3's table
//   requires them) but not consumed by any logic in this file.
//   `TermSelect`'s real analog effect (D+ pull-up enable) is explicitly
//   deferred to "a PHY-level wrapper" by `design/README.md`'s own
//   differential-driver section; this is that wrapper, but wiring an
//   enable signal to an analog pad is a separate, not-yet-filed
//   integration issue, not this one's digital framing scope.
// - `SuspendM` is likewise present but unconsumed; this block does not
//   model low-power state retention (nothing here is stateful enough to
//   need it, and "how much current does an unclocked flop draw" is not
//   a cocotb-testable claim).
// - `Reset` IS consumed: folded into an internal reset
//   (`int_rst_n = rst_n & ~Reset`) alongside the block's own `rst_n`,
//   matching standard UTMI usage where `Reset` is the link/SIE
//   commanding the PHY to reset after it has itself decided (via
//   `LineState`) that a bus reset is underway -- that decision is
//   SIE-layer policy (out of scope), consuming the resulting command is
//   not.
//
// Rate: one bit per clock throughout, at the spec #3 interface clock of
// 12 MHz -- no oversampling, no dual-rate mode, high speed out of scope
// per spec #1 and CLAUDE.md.

`default_nettype none

module usb_utmi_phy (
    input  wire clk,
    input  wire rst_n,       // active-low, synchronous power-on reset

    // UTMI TX (spec #3)
    input  wire        TxValid,
    output wire        TxReady,
    input  wire [7:0]  DataOut,

    // UTMI RX (spec #3)
    output reg          RxValid,
    output wire         RxActive,
    output reg          RxError,
    output reg  [7:0]   DataIn,

    // UTMI status/control (spec #3)
    output wire [1:0]  LineState,
    input  wire [1:0]  OpMode,      // 2'b10 = raw mode, consumed as bypass; see header
    input  wire        TermSelect,  // present per spec #3; not consumed, see header
    input  wire        XcvrSelect,  // present per spec #3; not consumed, see header
    input  wire        SuspendM,    // present per spec #3; not consumed, see header
    input  wire        Reset,       // active-high UTMI reset command; consumed, see header

    // Wire-level TX -- drives design/differential_driver.sch's TXDP/TXDM
    output wire txdp,
    output wire txdm,

    // Wire-level RX -- from design/se_receiver_dp.sch / se_receiver_dm.sch
    input  wire rxdp,
    input  wire rxdm
);

  localparam [1:0] LS_SE0 = 2'b00;
  localparam [1:0] LS_J   = 2'b01;
  localparam [1:0] LS_K   = 2'b10;

  wire int_rst_n = rst_n & ~Reset;

  // ---------------------------------------------------------------------
  // LineState
  // ---------------------------------------------------------------------

  wire [1:0] line_state;

  usb_line_state_decode u_line_state (
      .clk        (clk),
      .rst_n      (int_rst_n),
      .rxdp       (rxdp),
      .rxdm       (rxdm),
      .line_state (line_state)
  );

  assign LineState = line_state;

  // ---------------------------------------------------------------------
  // TX path: this wrapper is the framer (the canonical usb_tx_framer.v
  // role) around the vendored usb_bit_stuffer -> usb_nrzi_encoder, in
  // the 12 MHz one-bit-per-clock domain (bit_stb asserted every clock
  // of an active stream -- see the header's clocking note).
  // ---------------------------------------------------------------------

  localparam [7:0] SYNC_BYTE = 8'h80;

  localparam [2:0] TX_IDLE  = 3'd0;
  localparam [2:0] TX_SYNC  = 3'd1;
  localparam [2:0] TX_DATA  = 3'd2;
  localparam [2:0] TX_FLUSH = 3'd3;
  localparam [2:0] TX_HOLD  = 3'd4;
  localparam [2:0] TX_EOP0  = 3'd5;
  localparam [2:0] TX_EOP1  = 3'd6;
  localparam [2:0] TX_EOPJ  = 3'd7;

  reg [2:0] tx_state;
  reg [2:0] sync_idx;
  reg [7:0] byte_reg;
  reg [2:0] byte_idx;
  reg       first_byte;

  wire raw_mode = (OpMode == 2'b10);

  wire sync_bit      = SYNC_BYTE[sync_idx];
  wire entering_sync = (tx_state == TX_IDLE) && TxValid;

  wire stuff_bit_out;
  wire stuff_consume;
  wire stuff_pending_after;

  // One bit-time per clock while a body bit is being presented -- the
  // canonical bit_stb, unsuppressed: TX_DATA presents payload (a
  // stuff-insertion clock inside TX_DATA simply re-presents the same
  // bit), TX_FLUSH presents the forced trailing stuff bit.
  wire tx_body_active = (tx_state == TX_DATA) || (tx_state == TX_FLUSH);

  usb_bit_stuffer u_stuffer (
      .clk                 (clk),
      .rst_n               (int_rst_n),
      .bit_stb             (tx_body_active),
      .bypass              (raw_mode),
      .sof                 (tx_body_active && (tx_state == TX_DATA) &&
                            first_byte && (byte_idx == 3'd0)),
      .bit_in              ((tx_state == TX_FLUSH) ? 1'b0 : byte_reg[byte_idx]),
      .bit_out             (stuff_bit_out),
      .consume             (stuff_consume),
      .stuff_pending_after (stuff_pending_after)
  );

  wire nrzi_level;

  usb_nrzi_encoder u_encoder (
      .clk       (clk),
      .rst_n     (int_rst_n),
      // SYNC bypasses the stuffer: the encoder is strobed through
      // TX_SYNC (and on the entering edge itself) with the SYNC bit,
      // and through the body states with the stuffer's output.
      .bit_stb   (tx_body_active || (tx_state == TX_SYNC) || entering_sync),
      .bypass    (raw_mode && tx_body_active),
      .sof       (entering_sync),
      .bit_in    ((tx_state == TX_SYNC || entering_sync) ? sync_bit
                                                          : stuff_bit_out),
      .level_out (nrzi_level)
  );

  // Combinational (not clock-gated) so the requesting window is the
  // full clock leading up to the edge that consumes the byte's last
  // real bit -- the canonical TxReady back-pressure contract.
  assign TxReady = (tx_state == TX_IDLE) ||
                    ((tx_state == TX_DATA) && (byte_idx == 3'd7) &&
                     stuff_consume);

  always @(posedge clk) begin
    if (!int_rst_n) begin
      tx_state   <= TX_IDLE;
      sync_idx   <= 3'd0;
      byte_reg   <= 8'd0;
      byte_idx   <= 3'd0;
      first_byte <= 1'b0;
    end else begin
      case (tx_state)
        TX_IDLE: begin
          if (TxValid) begin
            byte_reg   <= DataOut;
            tx_state   <= TX_SYNC;
            // `entering_sync` above already encoded SYNC bit 0 on this
            // very edge (using sync_idx's pre-edge value, 0) -- advance
            // to 1 so TX_SYNC starts at bit 1, not bit 0 twice.
            sync_idx   <= 3'd1;
            first_byte <= 1'b1;
          end
        end

        TX_SYNC: begin
          if (sync_idx == 3'd7) begin
            tx_state <= TX_DATA;
            byte_idx <= 3'd0;
            // Re-arm for the next packet: the entering edge of every
            // packet encodes SYNC bit 0 from sync_idx's PRE-edge value,
            // which must therefore be 0 whenever the FSM sits in TX_IDLE
            // -- after reset and after every previous packet alike
            // (leaving it at 7 would encode SYNC_BYTE[7] (a 1) as the
            // next packet's bit 0 and corrupt the SYNC pattern).
            sync_idx <= 3'd0;
          end else begin
            sync_idx <= sync_idx + 3'd1;
          end
        end

        TX_DATA: begin
          if (stuff_consume) begin
            if (byte_idx == 3'd7) begin
              if (TxValid) begin
                byte_reg   <= DataOut;
                byte_idx   <= 3'd0;
                first_byte <= 1'b0;
              end else begin
                // Last real bit consumed. Neither branch frames EOP
                // directly: the strobe on this same edge just finalized
                // this bit's `nrzi_level`, and TX_HOLD owes it one
                // visible clock on the wire first.
                tx_state <= stuff_pending_after ? TX_FLUSH : TX_HOLD;
              end
            end else begin
              byte_idx <= byte_idx + 3'd1;
            end
          end
          // else: this clock inserted a stuff bit (consume == 0) --
          // byte_idx and byte_reg hold; the same bit is re-presented.
        end

        TX_FLUSH: begin
          // The forced #7.1.9 trailing stuff bit went out on this
          // edge; its level needs its wire clock too.
          tx_state <= TX_HOLD;
        end

        TX_HOLD:  tx_state <= TX_EOP0;
        TX_EOP0:  tx_state <= TX_EOP1;
        TX_EOP1:  tx_state <= TX_EOPJ;
        TX_EOPJ:  tx_state <= TX_IDLE;
        default:  tx_state <= TX_IDLE;
      endcase
    end
  end

  // txdp/txdm pad mux (combinational, the canonical framer's pad
  // stage): forced SE0/SE0/J through the EOP tail, the encoder's
  // registered level while sending (the level for the bit consumed at
  // edge N is on the wire for the whole clock after N -- hence TX_HOLD
  // before the EOP override), idle J otherwise.
  wire tx_line_phase = (tx_state == TX_SYNC) || (tx_state == TX_DATA) ||
                       (tx_state == TX_FLUSH) || (tx_state == TX_HOLD);

  assign txdp = (tx_state == TX_EOP0 || tx_state == TX_EOP1) ? 1'b0 :
                (tx_state == TX_EOPJ)                       ? 1'b1 :
                tx_line_phase                                ? nrzi_level :
                                                                1'b1;  // idle J
  assign txdm = (tx_state == TX_EOP0 || tx_state == TX_EOP1) ? 1'b0 :
                (tx_state == TX_EOPJ)                       ? 1'b0 :
                tx_line_phase                                ? ~nrzi_level :
                                                                1'b0;  // idle J

  // ---------------------------------------------------------------------
  // RX path: vendored usb_nrzi_decoder (free-running, strobed only on
  // genuine J/K samples) -> local usb_sync_detector / vendored
  // usb_bit_destuffer (enable-gated by rx_receiving), local
  // usb_eop_detector, byte assembly.
  // ---------------------------------------------------------------------

  wire dec_bit_strobe = (line_state == LS_J) || (line_state == LS_K);
  wire dec_bit_level  = (line_state == LS_J);

  wire dec_data_strobe;
  wire dec_data_bit;

  usb_nrzi_decoder u_decoder (
      .clk_144     (clk),
      .rst_144_n   (int_rst_n),
      .bit_strobe  (dec_bit_strobe),
      .bit_level   (dec_bit_level),
      // `bit_is_jk` from the line-state decode: the strobe itself is
      // only asserted on genuine J/K samples, so SE0/SE1 cells (EOP,
      // bus reset) are never decoded as data -- see the header.
      .bit_is_jk   (dec_bit_strobe),
      .data_strobe (dec_data_strobe),
      .data_bit    (dec_data_bit)
  );

  reg rx_receiving;

  // `sync_valid` (registered, "SYNC just completed") is not consumed
  // here -- this wrapper only needs the earlier `sync_next`, see the RX
  // section header -- so it is left unconnected rather than wired to a
  // dead signal.
  wire sync_next;

  usb_sync_detector u_sync_detector (
      .clk        (clk),
      .rst_n      (int_rst_n),
      .enable     (!rx_receiving),
      .data_valid (dec_data_strobe),
      .data_bit   (dec_data_bit),
      .sync_valid (),
      .sync_next  (sync_next)
  );

  wire eop_pulse;
  wire bus_reset;

  usb_eop_detector u_eop_detector (
      .clk        (clk),
      .rst_n      (int_rst_n),
      .line_state (line_state),
      .eop        (eop_pulse),
      .bus_reset  (bus_reset)
  );

  wire rx_bit_valid;
  wire rx_out_bit;
  wire rx_stuff_err;

  usb_bit_destuffer u_destuffer (
      .clk_144     (clk),
      .rst_144_n   (int_rst_n),
      // SOP..EOP gating -- the canonical `enable`, replacing the former
      // per-packet `init`: armed by `sync_next` one clock before the
      // first post-SYNC bit arrives here, dropped by EOP/bus-reset,
      // which also resets the run counter for the next packet.
      .enable      (rx_receiving),
      .data_strobe (dec_data_strobe),
      .data_bit    (dec_data_bit),
      .bit_valid   (rx_bit_valid),
      .out_bit     (rx_out_bit),
      .stuff_err   (rx_stuff_err)
  );

  // `rx_receiving` (and therefore RX forwarding/RxActive) is armed from
  // `sync_next`, not `sync_valid`: `sync_next` is concurrent with
  // SYNC's final bit, so `rx_receiving` becomes 1 starting the very
  // next clock -- exactly the clock the decoder emits the first
  // post-SYNC bit, which is also the clock the destuffer's `enable`
  // must already be high so its run counter counts that bit from zero.
  always @(posedge clk) begin
    if (!int_rst_n) begin
      rx_receiving <= 1'b0;
    end else if (sync_next) begin
      rx_receiving <= 1'b1;
    end else if (eop_pulse || bus_reset) begin
      rx_receiving <= 1'b0;
    end
  end

  assign RxActive = rx_receiving;

  // Byte assembly: LSB-first shift, matching USB's own byte convention
  // and mirroring the TX side's byte_idx==0 -> DataOut[0] first ordering.
  //
  // Gated on a one-clock-delayed `rx_receiving` (`rx_assembly_en`), not on
  // `rx_receiving` itself: the destuffer is transparent while enable is
  // low, so the SYNC field's bits -- its final bit included -- pulse
  // `bit_valid` one clock after they pass through. `rx_receiving` rises
  // exactly when the first post-SYNC bit is at the destuffer's input, so
  // SYNC's own final forwarded bit would pulse `bit_valid` on that same
  // first clock of reception; the extra register stage skips exactly that
  // pulse while still assembling the first post-SYNC bit (whose
  // `bit_valid` lands one clock later). The canonical master arms its
  // deserializer from a sync match on the destuffer's OUTPUT stream and
  // gets this separation for free; this wrapper arms one clock earlier
  // (on the decoder stream, via `sync_next`) so the destuffer's run
  // counter starts AT the first post-SYNC bit -- one bit earlier than the
  // master's framer, self-consistent with this wrapper's TX-side `sof`
  // (which also counts that bit) and recorded in spec/decisions/0002.
  reg rx_assembly_en;

  always @(posedge clk) begin
    if (!int_rst_n) begin
      rx_assembly_en <= 1'b0;
    end else begin
      rx_assembly_en <= rx_receiving;
    end
  end

  reg [7:0] rx_shift;
  reg [2:0] rx_bitcnt;

  wire [7:0] rx_shift_next = {rx_out_bit, rx_shift[7:1]};

  always @(posedge clk) begin
    if (!int_rst_n || !rx_receiving) begin
      rx_shift  <= 8'd0;
      rx_bitcnt <= 3'd0;
      RxValid   <= 1'b0;
    end else begin
      RxValid <= 1'b0;
      if (rx_bit_valid && rx_assembly_en) begin
        rx_shift <= rx_shift_next;
        if (rx_bitcnt == 3'd7) begin
          rx_bitcnt <= 3'd0;
          DataIn    <= rx_shift_next;
          RxValid   <= 1'b1;
        end else begin
          rx_bitcnt <= rx_bitcnt + 3'd1;
        end
      end
    end
  end

  always @(posedge clk) begin
    if (!int_rst_n) begin
      RxError <= 1'b0;
    end else begin
      RxError <= rx_stuff_err && rx_receiving;
    end
  end

endmodule

`default_nettype wire
