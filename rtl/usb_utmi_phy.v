// usb_utmi_phy.v -- top-level UTMI-facing wrapper.
//
// spec/usb2-device-phy.md #3 defines this block's digital interface as
// UTMI: an 8-bit parallel data bus at a 12 MHz interface clock (the raw
// full-speed bit rate -- one bit per clock, no oversampling, see #3's
// engineering note). This module assembles every digital submodule in
// this directory -- `usb_bit_stuffer`, `usb_nrzi_encoder`,
// `usb_nrzi_decoder`, `usb_bit_destuffer` (issue #31), plus
// `usb_line_state_decode`, `usb_sync_detector`, and `usb_eop_detector`
// (this issue, #32) -- into the exact port set #3's table names:
// `TxValid`/`TxReady`/`DataOut[7:0]`,
// `RxValid`/`RxActive`/`RxError`/`DataIn[7:0]`, `LineState[1:0]`,
// `OpMode[1:0]`, `TermSelect`, `XcvrSelect`, `SuspendM`, `Reset`.
//
// SYNC field generation (TX) and EOP (SE0) generation (TX) -- the two
// pieces of spec #2 this issue's dedicated modules do not cover -- are
// implemented directly in this file's TX state machine below, because
// both are inseparable from the byte-serialization sequencing this
// wrapper already owns; see the TX section header for the derivation.
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
// J/K -> D+/D- mapping, matching every other module's "1 = J, 0 = K"
// convention and `usb_line_state_decode`'s LineState encoding:
//
//     J: txdp=1, txdm=0      K: txdp=0, txdm=1      SE0 (EOP): txdp=0, txdm=0
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
// EOP generation.
//
// SYNC is not special-cased as its own phase: it is simply byte "-1" of
// the packet, pushed through the exact same
// stuffer -> encoder byte-shift pipeline every other byte uses (it never
// actually triggers stuffing, since 8'h80 contains at most one run of a
// single 1, but running it through the same counter is exactly what real
// USB bit stuffing does -- the run count carries continuously from SYNC
// into the PID field). Concretely: `TX_IDLE` captures the first byte the
// link offers into a one-entry skid buffer (`next_byte`/`next_valid`) and
// immediately begins shifting `cur_byte = 8'h80` (SYNC); every subsequent
// terminal (8th, stuffer-consumed) bit of `cur_byte` promotes
// `next_byte` into `cur_byte` and pulls a further byte from the link if
// still offered, so payload bytes stream back-to-back with the same
// one-byte-ahead pipelining `TxReady` implies. When the link stops
// asserting `TxValid` (declares the packet done, ordinary UTMI TX
// framing, not SIE-layer semantics), the wrapper checks whether a bit
// stuff is pending (`usb_bit_stuffer.v`'s own documented flush idiom:
// assert `in_valid` for exactly one clock while `in_ready` is low, only
// if `in_ready` is currently low) then, after enough clocks for that bit
// to drain through the 2-stage stuffer->encoder pipeline, switches from
// NRZI-muxed output to two clocks of directly-driven SE0 and one of J --
// EOP, spec #2/#4.
//
// `init` (to both `usb_bit_stuffer` and `usb_nrzi_encoder`) is pulsed for
// exactly one dedicated clock (`TX_INIT`) at the start of every packet,
// never again mid-packet: TX always starts from a known idle-J reference,
// so the encoder's `init` (which unconditionally sets the line reference
// to J) is always correct here -- unlike the RX side, see below.
//
// RX pipeline -- free-running NRZI decode, SYNC-gated destuff forwarding.
//
// `usb_nrzi_decoder` is fed continuously and never re-initialized after
// the block's own reset: `line_valid` is asserted whenever `line_state` is
// a genuine J or K sample (never during SE0/SE1), so the decoder simply
// holds across EOP/idle gaps. This is deliberate, not an oversight of the
// "packet start" case `usb_bit_stuffer`'s own `init` idiom exists for: a
// fresh `init` pulse (which `usb_nrzi_decoder.v` hardcodes to a J
// reference) would be WRONG immediately after a SYNC field, because the
// actual line reference at that point is K (SYNC's last bit), not J.
// Free-running avoids the problem rather than working around it: the
// decoder's own transition-tracking (`prev_line <= line_bit` every valid
// clock) self-corrects to the true line state within one real J/K sample
// of any gap, and idle-J is stable for far longer than one clock before
// the next SYNC begins, so by the time a new SYNC is transmitted the
// decoder's reference is already correct. Only `usb_bit_destuffer` needs a
// per-packet `init`, because a stale bit-stuffing run count genuinely
// would misalign the very next packet's stuff positions -- and
// `usb_sync_detector` provides exactly the signal needed to place it
// correctly, one clock ahead of the first real bit: `sync_next`
// (combinational, high on the same clock the decoder emits SYNC's own
// final bit) drives `usb_bit_destuffer.init`, so the reset lands the clock
// BEFORE RX forwarding begins -- not on top of the first real bit, which
// would otherwise be silently dropped (`init` masks `in_valid` on the same
// clock it is asserted, matching every other module's `init` convention;
// see `usb_sync_detector.v`'s own header for why its registered
// `sync_valid` -- used to gate forwarding itself -- is one clock too late
// for this).
//
// `usb_sync_detector` matches on the DECODED bit stream (not raw line
// state) for exactly the same free-running reason: it needs no separate
// re-arming logic keyed to line transitions, it just watches the decoder's
// already-continuous output for the fixed byte value 8'h80.
//
// `usb_eop_detector` runs unconditionally off `LineState`, independent of
// RX framing state (see its own header) -- `eop` (RX_ACTIVE ends
// normally) and the internal-only `bus_reset` (RX_ACTIVE aborts) both
// simply clear `rx_receiving`.
//
// Scope choices, stated explicitly (per CLAUDE.md's honesty convention,
// same pattern rtl/README.md already uses for the bit-level codec):
//
// - `OpMode`, `TermSelect`, `XcvrSelect` are present as ports (spec #3's
//   table requires them) but not consumed by any logic in this file. This
//   FS-only, device-only block has exactly one meaningful operating point
//   -- there is no HS chirp mode, no host/OTG role, no LS support -- so
//   the UTMI+ semantics these signals exist to select do not apply here
//   (spec #3's own "UTMI, not UTMI+" decision). `TermSelect`'s real analog
//   effect (D+ pull-up enable) is explicitly deferred to "a PHY-level
//   wrapper" by `design/README.md`'s own differential-driver section;
//   this is that wrapper, but wiring an enable signal to an analog pad is
//   a separate, not-yet-filed integration issue, not this one's digital
//   framing scope.
// - `SuspendM` is likewise present but unconsumed; this block does not
//   model low-power state retention (nothing here is stateful enough to
//   need it, and "how much current does an unclocked flop draw" is not a
//   cocotb-testable claim).
// - `Reset` IS consumed: folded into an internal synchronous reset
//   (`int_rst_n = rst_n & ~Reset`) alongside the block's own `rst_n`,
//   matching standard UTMI usage where `Reset` is the link/SIE commanding
//   the PHY to reset after it has itself decided (via `LineState`) that a
//   bus reset is underway -- that decision is SIE-layer policy (out of
//   scope), consuming the resulting command is not.
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
    input  wire [1:0]  OpMode,      // present per spec #3; not consumed, see header
    input  wire        TermSelect,  // present per spec #3; not consumed, see header
    input  wire        XcvrSelect,  // present per spec #3; not consumed, see header
    input  wire        SuspendM,    // present per spec #3; not consumed, see header
    input  wire        Reset,       // active-high UTMI reset command; consumed, see header

    // Wire-level TX -- drives design/differential_driver.sch's TXDP/TXDM
    output reg  txdp,
    output reg  txdm,

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
  // TX path: usb_bit_stuffer -> usb_nrzi_encoder, plus framing state
  // machine (SYNC generation, byte serialization, flush, EOP generation).
  // ---------------------------------------------------------------------

  localparam [7:0] SYNC_BYTE = 8'h80;

  localparam [3:0] TX_IDLE       = 4'd0;
  localparam [3:0] TX_INIT       = 4'd1;
  localparam [3:0] TX_SHIFT      = 4'd2;
  localparam [3:0] TX_FLUSHCHECK = 4'd3;
  localparam [3:0] TX_DRAIN0     = 4'd4;
  localparam [3:0] TX_DRAIN1     = 4'd5;
  localparam [3:0] TX_EOP0       = 4'd6;
  localparam [3:0] TX_EOP1       = 4'd7;
  localparam [3:0] TX_EOPJ       = 4'd8;

  reg [3:0] tx_state;
  reg [2:0] tx_bitidx;
  reg [7:0] cur_byte;
  reg [7:0] next_byte;
  reg       next_valid;

  wire       stuff_in_ready;
  wire       stuff_out_valid;
  wire       stuff_out_bit;
  wire       tx_init = (tx_state == TX_INIT);

  wire stuffer_in_valid = (tx_state == TX_SHIFT)      ? 1'b1 :
                           (tx_state == TX_FLUSHCHECK) ? ~stuff_in_ready :
                                                          1'b0;
  wire stuffer_in_bit   = (tx_state == TX_SHIFT) ? cur_byte[tx_bitidx] : 1'b0;

  usb_bit_stuffer u_stuffer (
      .clk        (clk),
      .rst_n      (int_rst_n),
      .init       (tx_init),
      .in_valid   (stuffer_in_valid),
      .in_bit     (stuffer_in_bit),
      .in_ready   (stuff_in_ready),
      .out_valid  (stuff_out_valid),
      .out_bit    (stuff_out_bit),
      .out_stuffed()
  );

  wire enc_line_valid;
  wire enc_line_bit;

  usb_nrzi_encoder u_encoder (
      .clk        (clk),
      .rst_n      (int_rst_n),
      .init       (tx_init),
      .data_valid (stuff_out_valid),
      .data_bit   (stuff_out_bit),
      .line_valid (enc_line_valid),
      .line_bit   (enc_line_bit)
  );

  assign TxReady = (tx_state == TX_IDLE) ||
                    (tx_state == TX_SHIFT && tx_bitidx == 3'd7 && stuff_in_ready);

  always @(posedge clk) begin
    if (!int_rst_n) begin
      tx_state   <= TX_IDLE;
      tx_bitidx  <= 3'd0;
      cur_byte   <= 8'd0;
      next_byte  <= 8'd0;
      next_valid <= 1'b0;
    end else begin
      case (tx_state)
        TX_IDLE: begin
          if (TxValid) begin
            next_byte  <= DataOut;
            next_valid <= 1'b1;
            cur_byte   <= SYNC_BYTE;
            tx_bitidx  <= 3'd0;
            tx_state   <= TX_INIT;
          end
        end

        TX_INIT: begin
          tx_state <= TX_SHIFT;
        end

        TX_SHIFT: begin
          if (stuff_in_ready) begin
            if (tx_bitidx == 3'd7) begin
              tx_bitidx <= 3'd0;
              if (next_valid) begin
                cur_byte <= next_byte;
                tx_state <= TX_SHIFT;
              end else begin
                tx_state <= TX_FLUSHCHECK;
              end
              if (TxValid) begin
                next_byte  <= DataOut;
                next_valid <= 1'b1;
              end else begin
                next_valid <= 1'b0;
              end
            end else begin
              tx_bitidx <= tx_bitidx + 3'd1;
            end
          end
        end

        TX_FLUSHCHECK: tx_state <= TX_DRAIN0;
        TX_DRAIN0:     tx_state <= TX_DRAIN1;
        TX_DRAIN1:     tx_state <= TX_EOP0;
        TX_EOP0:       tx_state <= TX_EOP1;
        TX_EOP1:       tx_state <= TX_EOPJ;
        TX_EOPJ:       tx_state <= TX_IDLE;
        default:       tx_state <= TX_IDLE;
      endcase
    end
  end

  // txdp/txdm mux: explicit SE0/J during the EOP tail, otherwise NRZI
  // output when fresh (line_valid), else hold -- exactly mirroring
  // usb_nrzi_encoder's own "hold the line when line_valid is low"
  // contract.
  always @(posedge clk) begin
    if (!int_rst_n) begin
      txdp <= 1'b1;  // idle J
      txdm <= 1'b0;
    end else begin
      case (tx_state)
        TX_EOP0, TX_EOP1: begin
          txdp <= 1'b0;
          txdm <= 1'b0;
        end
        TX_EOPJ: begin
          txdp <= 1'b1;
          txdm <= 1'b0;
        end
        default: begin
          if (enc_line_valid) begin
            txdp <= enc_line_bit;
            txdm <= ~enc_line_bit;
          end
        end
      endcase
    end
  end

  // ---------------------------------------------------------------------
  // RX path: usb_nrzi_decoder -> usb_sync_detector / usb_bit_destuffer,
  // plus usb_eop_detector and byte assembly.
  // ---------------------------------------------------------------------

  wire dec_line_valid = (line_state == LS_J) || (line_state == LS_K);
  wire dec_line_bit   = (line_state == LS_J);

  wire dec_data_valid;
  wire dec_data_bit;

  usb_nrzi_decoder u_decoder (
      .clk        (clk),
      .rst_n      (int_rst_n),
      .init       (1'b0),  // free-running; see header for why
      .line_valid (dec_line_valid),
      .line_bit   (dec_line_bit),
      .data_valid (dec_data_valid),
      .data_bit   (dec_data_bit)
  );

  reg rx_receiving;

  // `sync_valid` (registered, "SYNC just completed") is not consumed here
  // -- this wrapper only needs the earlier `sync_next`, see the RX section
  // header below -- so it is left unconnected rather than wired to a dead
  // signal.
  wire sync_next;

  usb_sync_detector u_sync_detector (
      .clk        (clk),
      .rst_n      (int_rst_n),
      .enable     (!rx_receiving),
      .data_valid (dec_data_valid),
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

  wire destuff_in_valid = dec_data_valid && rx_receiving;
  wire destuff_out_valid;
  wire destuff_out_bit;
  wire destuff_stuff_err;

  usb_bit_destuffer u_destuffer (
      .clk        (clk),
      .rst_n      (int_rst_n),
      .init       (sync_next),
      .in_valid   (destuff_in_valid),
      .in_bit     (dec_data_bit),
      .out_valid  (destuff_out_valid),
      .out_bit    (destuff_out_bit),
      .stuff_err  (destuff_stuff_err)
  );

  // `rx_receiving` (and therefore RX forwarding/RxActive) is armed from
  // `sync_next`, not `sync_valid`: `sync_next` is concurrent with SYNC's
  // final bit (see usb_sync_detector.v), so `rx_receiving` becomes 1
  // starting the very next clock -- exactly the clock the decoder emits
  // the first post-SYNC bit. Arming from `sync_valid` instead (one clock
  // later) would miss that first bit entirely, since the decoder is
  // free-running and does not wait to be forwarded.
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
  // and mirroring the TX side's tx_bitidx==0 -> DataOut[0] first ordering.
  reg [7:0] rx_shift;
  reg [2:0] rx_bitcnt;

  wire [7:0] rx_shift_next = {destuff_out_bit, rx_shift[7:1]};

  always @(posedge clk) begin
    if (!int_rst_n || !rx_receiving) begin
      rx_shift  <= 8'd0;
      rx_bitcnt <= 3'd0;
      RxValid   <= 1'b0;
    end else begin
      RxValid <= 1'b0;
      if (destuff_out_valid) begin
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
      RxError <= destuff_stuff_err && rx_receiving;
    end
  end

endmodule

`default_nettype wire
