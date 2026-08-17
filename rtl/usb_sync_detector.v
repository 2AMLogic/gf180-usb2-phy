// usb_sync_detector.v -- SYNC field detection and bit-lock for the receive
// path.
//
// spec/usb2-device-phy.md #2 puts "SYNC detection and bit-lock (RX)" inside
// this block's UTMI boundary. USB full-speed's SYNC field is the fixed
// pre-NRZI byte 8'h80 (0000_0001, sent LSB first per USB's own byte
// convention -- see `usb_utmi_phy.v`'s header for the KJKJKJKK derivation),
// transmitted through the *same* NRZI encode path as every other packet
// byte. Consequently its NRZI-DECODED form is architecture-independent of
// line polarity or drift: it is always exactly the fixed bit sequence
// 0,0,0,0,0,0,0,1, in transmission order.
//
// This module therefore does its pattern matching on the ALREADY
// NRZI-DECODED bit stream (`data_valid`/`data_bit`, matching
// `usb_nrzi_decoder`'s output ports), not on raw line state. This is a
// deliberate design choice, not an oversight: matching on decoded bits
// means `usb_utmi_phy.v` can feed `usb_nrzi_decoder` continuously and in
// free-running fashion (see that file's header for why re-issuing `init`
// mid-packet would require a non-J transition reference this module's
// sibling does not support), and this detector needs no special knowledge
// of the analog line encoding at all -- it just watches for its own fixed
// byte value.
//
// "Bit-lock" in this purely-digital, one-sample-per-bit-period block (no
// oversampling -- spec #3's engineering note; CLAUDE.md's scope-discipline
// rule keeps clock/data recovery hardware itself out of scope) reduces to:
// once the fixed SYNC pattern has been recognized, the receive pipeline
// downstream (`usb_bit_destuffer` in the top-level wrapper) is known to be
// bit-aligned with the transmitter, because the decoder that produced this
// exact byte value must itself have been correctly tracking every
// preceding transition.
//
// Two completion outputs, one clock apart, for two different consumers:
//
//   `sync_next`  -- combinational, high during the SAME clock `data_bit`
//                   carries SYNC's final '1'. By the FOLLOWING clock the
//                   free-running `usb_nrzi_decoder` this module watches has
//                   already moved on to the first post-SYNC bit -- so a
//                   consumer that needs to prepare something (reset a
//                   downstream run counter, etc.) *before* that first real
//                   bit arrives must act on `sync_next`, not `sync_valid`.
//   `sync_valid` -- registered, one clock LATER than `sync_next` (i.e. high
//                   during the clock that carries the first post-SYNC bit).
//                   The natural signal for a consumer that wants to *use*
//                   that first real bit, e.g. "start forwarding now".
//
// `usb_utmi_phy.v` uses exactly this split: `sync_next` pulses
// `usb_bit_destuffer.init` (which -- matching every other module's `init`
// convention -- masks `in_valid` on the clock it is asserted, so it must
// land one clock before the first real bit, not on top of it), while
// `sync_valid` gates when RX forwarding and `RxActive` actually begin.
//
// `enable`: gates whether the pattern matcher is armed at all. The
// top-level wrapper drives this low while already mid-packet (RX_ACTIVE),
// so a SYNC-shaped byte value appearing inside payload/CRC data (a false
// positive is not actually possible against a strict 8-bit match starting
// from a clean idle run, but `enable` also gives a well-defined "not
// currently searching" state for `line_state`-adjacent reasoning in the
// wrapper). While `enable` is low the match state is held at zero, so
// re-enabling always starts a fresh search rather than resuming a stale
// partial match.
//
// A byte value that does not match SYNC (malformed/missing SYNC, or line
// noise) simply never produces `sync_valid` -- there is deliberately no
// separate "bad sync" error output. The match state restarts from the
// first sample that could itself begin a fresh match (this pattern's first
// bit is 0, so any 0 sample restarts a 1-bit-deep match), which is the
// standard behavior for a fixed-pattern correlator and is enough for this
// receiver: a byte that never matches simply never asserts `RxActive`
// downstream, which is the correct, safe outcome (spec #2 does not ask for
// a distinct "malformed SYNC" status signal -- see
// `spec/usb2-device-phy.md` #3's port table).
//
// Rate: one sample per clock at the spec #3 interface clock of 12 MHz.

`default_nettype none

module usb_sync_detector (
    input  wire clk,
    input  wire rst_n,       // active-low, synchronous
    input  wire enable,      // arm the search; low holds the match state at 0
    input  wire data_valid,  // `data_bit` carries an NRZI-decoded bit this clock
    input  wire data_bit,    // NRZI-decoded bit (usb_nrzi_decoder's `data_bit`)
    output reg  sync_valid,  // one-clock pulse: SYNC fully matched this clock
    output wire sync_next    // combinational: this clock's data_bit is the
                              // eighth (final) match -- one clock earlier
                              // than `sync_valid`, see below
);

  // SYNC field, pre-NRZI, transmission order (LSB of 8'h80 first):
  // 0,0,0,0,0,0,0,1.
  localparam [7:0] SYNC_BYTE = 8'h80;

  function automatic expected_bit;
    input [2:0] idx;
    begin
      expected_bit = SYNC_BYTE[idx];
    end
  endfunction

  // Number of consecutive matching samples seen so far, 0..7. Widened to
  // 4 bits so `match == 7` and "restart at 1" are unambiguous during the
  // same always-block evaluation.
  reg [3:0] match;

  // Combinational: high during the SAME clock the eighth (final) bit is
  // presented, one clock EARLIER than the registered `sync_valid` pulse
  // above (which reflects that same event only after it has been
  // registered). Consumers that need to act on "the next clock's data
  // starts a fresh sequence" -- `usb_utmi_phy.v` pulses
  // `usb_bit_destuffer.init` on this signal, not on `sync_valid`, because
  // by the time `sync_valid` itself is visible the decoder has already
  // moved on to the first post-SYNC bit, and `usb_bit_destuffer.init`
  // masks `in_valid` on the same clock it is asserted (matching every
  // other module's `init` convention) -- asserting it a clock too late
  // would silently drop that first real bit.
  assign sync_next = enable && data_valid && (match == 4'd7) &&
                      (data_bit == expected_bit(3'd7));

  always @(posedge clk) begin
    if (!rst_n || !enable) begin
      match      <= 4'd0;
      sync_valid <= 1'b0;
    end else begin
      sync_valid <= 1'b0;
      if (data_valid) begin
        if (data_bit == expected_bit(match[2:0])) begin
          if (match == 4'd7) begin
            // Eighth (final) bit matched: SYNC fully recognized this clock.
            sync_valid <= 1'b1;
            match      <= 4'd0;
          end else begin
            match <= match + 4'd1;
          end
        end else begin
          // Mismatch: restart. If this sample itself equals SYNC's first
          // bit (0) it can begin a fresh match immediately; otherwise back
          // to a clean search.
          match <= (data_bit == expected_bit(3'd0)) ? 4'd1 : 4'd0;
        end
      end
      // data_valid low: hold match state across the gap (mirrors
      // usb_bit_stuffer/usb_bit_destuffer's own "idle holds the run count"
      // convention).
    end
  end

endmodule

`default_nettype wire
