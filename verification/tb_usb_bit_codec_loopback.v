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
// generation/detection, EOP, and `LineState[1:0]` decode -- is
// `rtl/usb_utmi_phy.v`. This harness has no SYNC, no EOP, no line-state
// decode, no UTMI signals, and no serial-interface-engine semantics
// whatsoever (CLAUDE.md's scope-discipline rule).
//
// Since issue #84 the four protocol modules are the vendored canonical
// ones under `rtl/common/` (strobe/consume handshakes, `sof` run resets,
// `enable` gating -- no `init` ports), so this harness is their minimal
// canonical caller, in the 12 MHz one-bit-per-clock domain (`bit_stb`
// asserted on every active clock; see `rtl/usb_utmi_phy.v`'s header and
// `spec/decisions/0002` for the clocking-vocabulary note):
//
//   tx_bit -> usb_bit_stuffer -> usb_nrzi_encoder -+
//                                                  |  nrzi_level (J/K)
//   rx_bit <- usb_bit_destuffer <- usb_nrzi_decoder +
//
// A *session* is one burst of `tx_valid`: the first presented bit is
// strobed on the very IDLE->SEND transition edge (the canonical
// `entering_sync` pattern from the master's `usb_tx_framer.v`) with `sof`
// on both the stuffer (run counter starts fresh, matching a packet's
// stuffable field) and the encoder (transition reference re-derived from
// idle J). When `tx_valid` drops, the harness discharges the canonical
// flush duty itself: if the last consumed bit left `stuff_pending_after`
// high, it spends one extra strobed bit-time (SFLUSH) emitting the forced
// #7.1.9 trailing stuff bit before releasing the session -- the same
// decision `rtl/usb_utmi_phy.v`'s TX_FLUSH state makes at real packet
// ends.
//
// The RX side's `enable` (the canonical SOP..EOP gate) is derived by
// delaying the session's strobe by exactly the TX->RX pipeline depth
// (encoder register + decoder register = 2 clocks), so the destuffer is
// enabled precisely for the clocks its `data_strobe` inputs arrive and
// its run counter starts/ends at zero per session -- the canonical
// replacement for the former harness-wide `init` clear. The internal
// line is a direct wire, not a modelled analog channel: J/K to D+/D-
// mapping and the receivers themselves are analog work tracked
// elsewhere; `bit_is_jk` is tied high because this harness's line is
// always a genuine J or K level.

`default_nettype none

module tb_usb_bit_codec_loopback (
    input  wire clk,
    input  wire rst_n,

    // TX side: strobed presentation. `tx_ready` is high on exactly the
    // bit-times whose presented bit was consumed (a stuff-insertion
    // bit-time reads 0 -- hold `tx_bit` and re-present it).
    input  wire tx_valid,
    input  wire tx_bit,
    output wire tx_ready,

    // The encoded line between the two paths, exposed for observation.
    // `line_valid` is high for the clock after each strobed bit-time
    // (the encoder's registered `level_out`).
    output wire line_valid,
    output wire line_bit,

    // RX side: registered, one clock behind the decoder's data_strobe.
    output wire rx_valid,
    output wire rx_bit,
    output wire rx_stuff_err,

    // The stuffer emitted a stuffed 0 this bit-time (not a data bit).
    output wire tx_stuffed
);

  localparam [1:0] S_IDLE  = 2'd0;
  localparam [1:0] S_SEND  = 2'd1;
  localparam [1:0] S_FLUSH = 2'd2;

  reg [1:0] state;
  reg       flush_due;

  wire entering_send = (state == S_IDLE) && tx_valid;

  wire session_strobe = entering_send ||
                        (state == S_SEND && tx_valid) ||
                        (state == S_FLUSH);

  // ---- usb_bit_stuffer (vendored, canonical caller side) ---------------
  wire stuff_bit_out;
  wire stuff_consume;
  wire stuff_pending_after;

  usb_bit_stuffer u_stuffer (
      .clk                 (clk),
      .rst_n               (rst_n),
      .bit_stb             (session_strobe),
      .bypass              (1'b0),
      .sof                 (entering_send),
      .bit_in              ((state == S_FLUSH) ? 1'b0 : tx_bit),
      .bit_out             (stuff_bit_out),
      .consume             (stuff_consume),
      .stuff_pending_after (stuff_pending_after)
  );

  // ---- usb_nrzi_encoder (vendored, canonical caller side) --------------
  wire nrzi_level;

  usb_nrzi_encoder u_encoder (
      .clk       (clk),
      .rst_n     (rst_n),
      .bit_stb   (session_strobe),
      .bypass    (1'b0),
      .sof       (entering_send),
      .bit_in    (stuff_bit_out),
      .level_out (nrzi_level)
  );

  assign tx_ready = ((state == S_SEND) || entering_send) && tx_valid &&
                    stuff_consume;
  assign tx_stuffed = session_strobe && !stuff_consume;

  // ---- the line: encoder output -> decoder input -----------------------
  // Bit-time N is strobed at edge N; its level is on the wire for the
  // whole clock after (d1); the decoder's data_strobe follows one clock
  // later still (N+2, d2-shaped) -- which is also exactly when the
  // destuffer must be enabled for that bit.
  //
  // The decoder is strobed on every genuine line sample, mirroring how
  // `usb_utmi_phy.v` free-runs its decoder: each real bit's period (d1)
  // plus idle-J samples once the line has been quiet for two clocks --
  // the debounce skips the one-clock strobe hole the session FSM leaves
  // at a session tail (the caller-deasserts-tx_valid clock before
  // SFLUSH), which is a hold, not a bus turnaround. Between sessions the
  // line idles at J (a real USB bus idles at J between packets, and the
  // wrapper's own pad mux drives J in TX_IDLE), so the decoder's
  // transition reference self-corrects to J during the gap. This is the
  // canonical replacement for the former harness-wide `init` clear: the
  // canonical decoder has no re-reference port, and without idle-J
  // samples a stale reference from the previous session would corrupt
  // the next session's first bit. The idle samples' decoded bits are
  // harmless by construction: the destuffer is transparent then (enable
  // low, run counter held at zero) and `rx_valid`'s window mask (d3)
  // excludes them.
  reg d1, d2, d3;
  reg [1:0] idle_cnt;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      d1 <= 1'b0;
      d2 <= 1'b0;
      d3 <= 1'b0;
      idle_cnt <= 2'd0;
    end else begin
      d1 <= session_strobe;
      d2 <= d1;
      d3 <= d2;
      if (d1) begin
        idle_cnt <= 2'd0;
      end else if (idle_cnt != 2'd3) begin
        idle_cnt <= idle_cnt + 2'd1;
      end
    end
  end

  wire idle_sample = !d1 && (idle_cnt >= 2'd2);
  wire line_level = d1 ? nrzi_level : 1'b1;  // idle J between sessions

  // The destuffer's enable must span the session's data_strobe clocks
  // CONTINUOUSLY: the canonical module zeroes its run counter whenever
  // `enable` reads low -- even on a clock with no data_strobe -- and the
  // raw d2 window has a one-clock hole at a session tail (d1 mirrors the
  // strobe, whose tx_valid-gated S_SEND leg drops for the single clock
  // between the caller's last accept and SFLUSH). The sticky term bridges
  // exactly that hole and clears only on genuine idle (the same
  // idle_cnt >= 2 debounce), so a trailing stuff bit still meets a live
  // run count and the counter still zeroes between sessions.
  reg en_sticky;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      en_sticky <= 1'b0;
    end else if (d2) begin
      en_sticky <= 1'b1;
    end else if (idle_cnt >= 2'd2) begin
      en_sticky <= 1'b0;
    end
  end
  wire destuff_en = d2 || en_sticky;

  assign line_valid = d1;
  assign line_bit   = line_level;

  wire dec_data_strobe;
  wire dec_data_bit;

  usb_nrzi_decoder u_decoder (
      .clk_144     (clk),
      .rst_144_n   (rst_n),
      .bit_strobe  (d1 || idle_sample),
      .bit_level   (line_level),
      .bit_is_jk   (1'b1),  // this harness's line is always J or K
      .data_strobe (dec_data_strobe),
      .data_bit    (dec_data_bit)
  );

  wire dst_bit_valid;
  wire dst_out_bit;
  wire dst_stuff_err;

  usb_bit_destuffer u_destuffer (
      .clk_144     (clk),
      .rst_144_n   (rst_n),
      .enable      (destuff_en),
      .data_strobe (dec_data_strobe),
      .data_bit    (dec_data_bit),
      .bit_valid   (dst_bit_valid),
      .out_bit     (dst_out_bit),
      .stuff_err   (dst_stuff_err)
  );

  // `rx_valid` is the destuffer's output masked to the session's
  // forwarding window: while the enable is low the destuffer is
  // transparent by design (its caller searches for the never-stuffed SYNC
  // pattern on its output), so its raw `bit_valid` also pulses for
  // between-session idle samples -- noise to a round-trip observer. The
  // mask (d3, d1 delayed by the decoder and destuffer output registers,
  // i.e. exactly two clocks) opens precisely for the clocks whose
  // data_strobe was a real in-session line bit.
  assign rx_valid     = dst_bit_valid && d3;
  assign rx_bit       = dst_out_bit;
  assign rx_stuff_err = dst_stuff_err;

  // ---- session FSM -----------------------------------------------------
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state     <= S_IDLE;
      flush_due <= 1'b0;
    end else begin
      // Latch the flush decision on every consumed bit-time so the
      // session-end transition below never depends on a stale `tx_bit`.
      if (session_strobe && stuff_consume) begin
        flush_due <= stuff_pending_after;
      end

      case (state)
        S_IDLE: begin
          if (tx_valid) begin
            state <= S_SEND;
          end
        end

        S_SEND: begin
          if (!tx_valid) begin
            // The caller declared the stream done. If the last consumed
            // bit left a stuff pending, USB 2.0 #7.1.9's trailing stuff
            // bit is owed first (same decision as usb_utmi_phy.v's
            // TX_FLUSH).
            state <= flush_due ? S_FLUSH : S_IDLE;
          end
        end

        S_FLUSH: state <= S_IDLE;

        default: state <= S_IDLE;
      endcase
    end
  end

endmodule

`default_nettype wire
