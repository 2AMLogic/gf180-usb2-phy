"""cocotb testbench for `rtl/usb_utmi_phy.v`, the top-level UTMI wrapper.

This is the "top-level integration testbench exercising the assembled
wrapper end-to-end" this issue's test plan requires: TX byte(s) in ->
wire-level NRZI/stuffed/SYNC/EOP framed output, and wire-level input ->
`DataIn[7:0]`/`RxValid`/`RxActive` out. Rather than a separate structural
loopback harness (contrast `tb_usb_bit_codec_loopback.v`), the RX-side
claim is made by self-loopback *inside this Python driver*: each clock,
whatever the DUT's own `txdp`/`txdm` present is mirrored onto its own
`rxdp`/`rxdm` for the following clock (see `_drive_packets`'s tail). This
is a legitimate functional-verification technique for a half-duplex serial
line and needs no additional Verilog scaffolding -- the module under test
is the real top-level wrapper, not a second copy of it.

Since issue #84 the four protocol transforms inside the wrapper are the
vendored canonical modules under `rtl/common/`, and the wire-level
expectations follow the master's stuffing scope (sky130-usb2-phy DR-0002
Decision 3): SYNC is framing and is NEVER bit-stuffed; the stuffer's run
counter starts fresh at the first post-SYNC bit (`sof`). The
`_expected_wire_dpdm` model below encodes exactly that scope (the
pre-vendoring wrapper ran SYNC *through* the stuffer, which could differ
by one stuff position when a payload opens with a run of 1s).

Byte-level TX driving follows the same "read `ready` before the edge it
governs" convention `test_usb_bit_codec_loopback.py` established for the
bit-level stuffer handshake, applied here one level up at the UTMI
`TxValid`/`TxReady` byte handshake `usb_utmi_phy.v` implements.

This file is *input* to `klt functional-verification` (see
`request-usb-utmi-phy.json`), not a pytest module.
"""

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer

from usb_bit_model import bit_stuff, nrzi_decode, nrzi_encode

# spec/usb2-device-phy.md #3 ratifies a 12 MHz interface clock. See
# test_usb_nrzi_encoder.py for why 83334 ps rather than 83333 ps.
CLK_PERIOD_PS = 83334

# Negative-control hook (issue #93). The gate-level SDF regression's negative
# control replays this *same* suite with only the interface clock period
# shortened, to show the regression fails when timing is broken. This file
# starts its own clock (it does not use `cocotb_helpers.start_clock`), so the
# override has to live here. Unset (the default, and every committed RTL and
# nominal gate-level run) the period is the ratified 12 MHz one above.
CLK_PERIOD_PS_OVERRIDE_ENV = "USB_UTMI_PHY_TB_CLK_PERIOD_PS"

SYNC_BYTE = 0x80


def _byte_to_bits(byte):
    """LSB-first bit list for one byte, matching USB's own transmission order."""
    return [(byte >> i) & 1 for i in range(8)]


def _line_to_dpdm(line_bit):
    """1 = J (dp=1,dm=0), 0 = K (dp=0,dm=1) -- usb_utmi_phy.v's own mapping."""
    return (1, 0) if line_bit else (0, 1)


def _expected_wire_dpdm(payload_bytes):
    """(dp,dm) sequence for SYNC + payload -- no EOP tail, canonical scope.

    SYNC (8'h80, LSB-first) is NRZI-encoded unstuffed around the stuffer;
    the payload alone is bit-stuffed, its run counter starting fresh at
    the first post-SYNC bit (the canonical `sof` scope, see the module
    docstring); the two fields form one continuous NRZI stream from the
    idle-J reference.
    """
    sync_bits = _byte_to_bits(SYNC_BYTE)
    stuffed, _flags = bit_stuff(_byte_to_bits_list(payload_bytes))
    line = nrzi_encode(sync_bits + stuffed)
    return [_line_to_dpdm(b) for b in line]


def _byte_to_bits_list(payload_bytes):
    """LSB-first bit list for a whole payload."""
    bits = []
    for b in payload_bytes:
        bits += _byte_to_bits(b)
    return bits


def _clock_period_ps():
    override = os.environ.get(CLK_PERIOD_PS_OVERRIDE_ENV)
    return int(override) if override else CLK_PERIOD_PS


async def _start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, _clock_period_ps(), unit="ps").start())


async def _reset(dut):
    dut.rst_n.value = 0
    dut.Reset.value = 0
    dut.TxValid.value = 0
    dut.DataOut.value = 0
    dut.OpMode.value = 0
    dut.TermSelect.value = 1
    dut.XcvrSelect.value = 1
    dut.SuspendM.value = 1
    dut.rxdp.value = 1
    dut.rxdm.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)


async def _drive_packets(dut, packets, cycles, loopback=True):
    """Drive `packets` (a list of byte-lists) into TX, one packet after
    another with the minimum possible inter-packet gap (TxValid reasserted
    the very first clock TxReady is seen high again after the previous
    packet's EOP).

    When `loopback` is True, each clock's txdp/txdm is mirrored onto
    rxdp/rxdm for the following clock (self-loopback); when False, rxdp/rxdm
    are left alone so a caller can drive them directly (e.g. a malformed
    SYNC on the wire).

    Returns a dict: `dpdm` (per-clock (txdp,txdm) trace), `rx_bytes` (the
    DataIn value each time RxValid pulsed), `rx_active` (per-clock RxActive
    trace), `rx_error` (per-clock RxError trace).

    Note on `TxReady`: `usb_utmi_phy.v` pulses it not just in `TX_IDLE` but
    also, transiently, at the terminal-bit-consumed clock of whatever byte
    `TX_DATA` is currently sending (so the PHY can request the next byte
    while still shifting the current one out -- this is why offering only
    `len(packet)` bytes correctly stops after exactly that many accepts,
    even though none of them may have finished being shifted onto the wire
    yet). Deciding "safe to start the next packet" therefore cannot use a
    bare `TxReady` pulse -- that fires throughout the tail of the *current*
    packet's shifting too. Starting the next packet is safe only once the
    PHY is back in `TX_IDLE`, which this driver recognizes from the ports
    alone (issue #93: a synthesized/routed netlist has no `tx_state` of the
    RTL's encoding -- the flow re-encodes it one-hot): the previous packet's
    EOP tail (SE0, SE0, J) has been seen on `txdp`/`txdm`, and `TxReady` is
    high again. The EOPJ state itself holds `TxReady` low, so `TxReady`
    returning high after the tail is exactly the first `TX_IDLE` sample --
    the same sample the former whitebox `tx_state == TX_IDLE` read fired on.
    """
    EOP_TAIL = [(0, 0), (0, 0), (1, 0)]
    packets = [list(p) for p in packets]
    pkt_idx = 0
    byte_idx = 0
    ended_current = False

    dpdm = []
    rx_bytes = []
    rx_active = []
    rx_error = []

    for _ in range(cycles):
        have_bytes = (
            pkt_idx < len(packets)
            and not ended_current
            and byte_idx < len(packets[pkt_idx])
        )
        if have_bytes:
            dut.TxValid.value = 1
            dut.DataOut.value = packets[pkt_idx][byte_idx]
        else:
            dut.TxValid.value = 0
            dut.DataOut.value = 0
        ready = int(dut.TxReady.value)

        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)

        if have_bytes and ready:
            byte_idx += 1
            if byte_idx == len(packets[pkt_idx]):
                ended_current = True
        elif (
            ended_current
            and dpdm[-3:] == EOP_TAIL
            and int(dut.TxReady.value) == 1
        ):
            pkt_idx += 1
            byte_idx = 0
            ended_current = False

        dpdm.append((int(dut.txdp.value), int(dut.txdm.value)))
        rx_active.append(int(dut.RxActive.value))
        rx_error.append(int(dut.RxError.value))
        if int(dut.RxValid.value):
            rx_bytes.append(int(dut.DataIn.value))

        if loopback:
            dut.rxdp.value = int(dut.txdp.value)
            dut.rxdm.value = int(dut.txdm.value)

    return {
        "dpdm": dpdm,
        "rx_bytes": rx_bytes,
        "rx_active": rx_active,
        "rx_error": rx_error,
    }


def _find_wire_start(dpdm):
    """Index of the first sample that departs idle J (1, 0)."""
    for i, sample in enumerate(dpdm):
        if sample != (1, 0):
            return i
    raise AssertionError(f"line never left idle J: {dpdm}")


@cocotb.test()
async def test_reset_state(dut):
    """Out of reset: TxReady high (idle, ready for a packet), RX quiescent,
    LineState reads the driven idle-J receivers."""
    await _start_clock(dut)
    await _reset(dut)

    assert int(dut.TxReady.value) == 1, "TxReady not asserted in TX_IDLE"
    assert int(dut.RxActive.value) == 0, "RxActive asserted out of reset"
    assert int(dut.RxValid.value) == 0, "RxValid asserted out of reset"
    assert int(dut.LineState.value) == 0b01, "LineState did not read idle J"
    assert (int(dut.txdp.value), int(dut.txdm.value)) == (1, 0), (
        "txdp/txdm did not default to idle J"
    )


@cocotb.test()
async def test_tx_sync_pattern_is_kjkjkjkk(dut):
    """The first 8 wire samples of any packet are exactly J/K's SYNC shape:
    K,J,K,J,K,J,K,K (spec #2; see usb_utmi_phy.v's header derivation)."""
    await _start_clock(dut)
    await _reset(dut)

    result = await _drive_packets(dut, [[0x00]], cycles=40, loopback=False)
    start = _find_wire_start(result["dpdm"])
    sync_wire = result["dpdm"][start:start + 8]

    expected = [(0, 1), (1, 0), (0, 1), (1, 0), (0, 1), (1, 0), (0, 1), (0, 1)]
    assert sync_wire == expected, f"SYNC wire pattern mismatch: {sync_wire}"


@cocotb.test()
async def test_tx_eop_tail_is_se0_se0_j(dut):
    """A packet's tail is exactly two SE0 clocks then one J clock (spec #2/#4)."""
    await _start_clock(dut)
    await _reset(dut)

    result = await _drive_packets(dut, [[0x00, 0xA5]], cycles=60, loopback=False)
    dpdm = result["dpdm"]
    start = _find_wire_start(dpdm)

    # Search forward, after the encoded region begins, for the exact
    # SE0,SE0,J shape -- there may be one or more repeated samples of the
    # last encoded bit immediately before it (the TX_FLUSH/TX_HOLD states
    # hold the line steady while the last level gets its wire clock; see
    # usb_utmi_phy.v's TX section header), which this search tolerates.
    eop_index = None
    for i in range(start, len(dpdm) - 2):
        if dpdm[i:i + 3] == [(0, 0), (0, 0), (1, 0)]:
            eop_index = i
            break
    assert eop_index is not None, f"no SE0,SE0,J EOP tail found in trace: {dpdm}"

    # And the line stays at idle J afterward (TX_IDLE).
    assert all(s == (1, 0) for s in dpdm[eop_index + 3:eop_index + 6]), (
        "line did not settle at idle J after the EOP tail"
    )


@cocotb.test()
async def test_loopback_single_byte(dut):
    """One TX byte, self-looped back, is received bit-exactly as one RX byte."""
    await _start_clock(dut)
    await _reset(dut)

    payload = [0x55]
    result = await _drive_packets(dut, [payload], cycles=60)

    assert result["rx_bytes"] == payload, f"round trip mismatch: {result['rx_bytes']}"
    assert not any(result["rx_error"]), "RxError asserted on a clean packet"
    # RxActive must have gone high during reception and returned low by the end.
    assert any(result["rx_active"]), "RxActive never asserted"
    assert result["rx_active"][-1] == 0, "RxActive still asserted after EOP"


@cocotb.test()
async def test_loopback_multi_byte_with_stuffing(dut):
    """Several bytes, including runs long enough to force bit stuffing,
    round-trip exactly through TX -> wire -> RX."""
    await _start_clock(dut)
    await _reset(dut)

    # 0xFF bytes guarantee long runs of 1s in the LSB-first bit stream,
    # forcing usb_bit_stuffer to fire multiple times.
    payload = [0x00, 0xFF, 0xFF, 0x3C, 0x01]
    result = await _drive_packets(dut, [payload], cycles=140)

    assert result["rx_bytes"] == payload, f"round trip mismatch: {result['rx_bytes']}"
    assert not any(result["rx_error"]), "RxError asserted on a clean packet"

    # Cross-check the wire itself against the independent bit_stuff/nrzi_encode
    # model, from the first departure from idle through the end of the
    # encoded (pre-EOP) stream.
    expected_wire = _expected_wire_dpdm(payload)
    start = _find_wire_start(result["dpdm"])
    actual_wire = result["dpdm"][start:start + len(expected_wire)]
    assert actual_wire == expected_wire, "wire trace disagrees with the bit-level model"


@cocotb.test()
async def test_loopback_leading_ones_payload_canonical_stuff_scope(dut):
    """The canonical stuffing scope, exercised where it is observable: a
    payload opening with a run of 1s must stuff after the SIXTH payload one
    (the stuffer's `sof` run reset at the first post-SYNC bit), not after
    five (which is what a SYNC run carry-through would produce). A 0xFF
    first byte opens with eight 1s, so the stuff position lands inside it."""
    await _start_clock(dut)
    await _reset(dut)

    payload = [0xFF, 0x00]
    result = await _drive_packets(dut, [payload], cycles=80)

    assert result["rx_bytes"] == payload, f"round trip mismatch: {result['rx_bytes']}"
    assert not any(result["rx_error"]), "RxError asserted on a clean packet"

    expected_wire = _expected_wire_dpdm(payload)
    start = _find_wire_start(result["dpdm"])
    actual_wire = result["dpdm"][start:start + len(expected_wire)]
    assert actual_wire == expected_wire, (
        "wire trace disagrees with the canonical (fresh-at-PID) stuffing scope"
    )


@cocotb.test()
async def test_loopback_trailing_run_of_six_ones_is_flushed(dut):
    """A packet whose payload bit stream ends on exactly six 1s (USB 2.0
    #7.1.9's mandatory trailing-stuff-bit case) still round-trips: the
    wrapper's TX_FLUSH state must emit the trailing stuffed 0 before EOP,
    decided by the canonical `stuff_pending_after` lookahead (see
    usb_utmi_phy.v's TX section header)."""
    await _start_clock(dut)
    await _reset(dut)

    # 0xFC's LSB-first bits are 0,0,1,1,1,1,1,1 -- six trailing 1s, behind
    # a leading 0x00 byte so the run starts at the 0xFC boundary. The
    # canonical stuffer counts this run fresh (SYNC never reaches it).
    payload = [0x00, 0xFC]
    result = await _drive_packets(dut, [payload], cycles=80)

    assert result["rx_bytes"] == payload, f"round trip mismatch: {result['rx_bytes']}"
    assert not any(result["rx_error"]), (
        "RxError asserted -- the trailing stuff bit was likely not flushed"
    )

    expected_wire = _expected_wire_dpdm(payload)
    start = _find_wire_start(result["dpdm"])
    actual_wire = result["dpdm"][start:start + len(expected_wire)]
    assert actual_wire == expected_wire, "wire trace disagrees with the bit-level model"


@cocotb.test()
async def test_loopback_back_to_back_packets_minimal_gap(dut):
    """Two packets sent back to back, TxValid reasserted the instant
    TxReady returns after the first packet's EOP -- the minimal possible
    inter-packet gap -- both round-trip correctly and independently."""
    await _start_clock(dut)
    await _reset(dut)

    packets = [[0x01, 0x02], [0xAA, 0xBB, 0xCC]]
    result = await _drive_packets(dut, packets, cycles=160)

    assert result["rx_bytes"] == packets[0] + packets[1], (
        f"back-to-back round trip mismatch: {result['rx_bytes']}"
    )
    assert not any(result["rx_error"]), "RxError asserted across back-to-back packets"

    # RxActive must have dropped low between the two packets (proving the
    # first packet's EOP was recognized) rather than staying high through
    # both as if they were one packet.
    active = result["rx_active"]
    first_high = active.index(1)
    first_low_after = next(i for i in range(first_high, len(active)) if active[i] == 0)
    second_high = next(
        (i for i in range(first_low_after, len(active)) if active[i] == 1), None
    )
    assert second_high is not None, "RxActive never reasserted for the second packet"


@cocotb.test()
async def test_raw_mode_puts_payload_on_the_wire_unencoded(dut):
    """OpMode 2'b10 (raw/transparent test mode) drives the vendored modules'
    `bypass`: the payload reaches the wire with NO bit stuffing and NO
    NRZI transform (bit 1 = J, bit 0 = K, one clock each). SYNC is
    PHY-generated framing and stays NRZI-encoded KJKJKJKK regardless (the
    canonical convention usb_utmi_phy.v's header documents)."""
    await _start_clock(dut)
    await _reset(dut)
    dut.OpMode.value = 0b10

    payload = [0b1010_0110]
    result = await _drive_packets(dut, [payload], cycles=60, loopback=False)

    start = _find_wire_start(result["dpdm"])
    sync_wire = result["dpdm"][start:start + 8]
    expected_sync = [(0, 1), (1, 0), (0, 1), (1, 0), (0, 1), (1, 0), (0, 1), (0, 1)]
    assert sync_wire == expected_sync, f"SYNC must stay NRZI-encoded: {sync_wire}"

    # The payload, LSB first, raw: 0,1,1,0,0,1,0,1 -> K,J,J,K,K,J,K,J.
    raw_wire = result["dpdm"][start + 8:start + 16]
    expected_raw = [_line_to_dpdm(b) for b in
                    [(0b1010_0110 >> i) & 1 for i in range(8)]]
    assert raw_wire == expected_raw, f"raw-mode payload was not raw: {raw_wire}"


@cocotb.test()
async def test_malformed_sync_never_activates_rx(dut):
    """A line pattern that starts like SYNC but breaks partway through never
    produces RxActive/RxValid -- bit-lock failure must fail safe."""
    await _start_clock(dut)
    await _reset(dut)

    # K,J,K,J then J again (should be K): breaks the SYNC match at bit 4.
    broken_line = [0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1]  # 1=J,0=K per _line_to_dpdm
    for line_bit in broken_line:
        dp, dm = _line_to_dpdm(line_bit)
        dut.rxdp.value = dp
        dut.rxdm.value = dm
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)
        assert int(dut.RxActive.value) == 0, "RxActive asserted against a malformed SYNC"
        assert int(dut.RxValid.value) == 0, "RxValid asserted against a malformed SYNC"

    # Idle out for a few more clocks: still nothing.
    dut.rxdp.value = 1
    dut.rxdm.value = 0
    for _ in range(10):
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)
        assert int(dut.RxActive.value) == 0
        assert int(dut.RxValid.value) == 0


# ---------------------------------------------------------------------------
# RX stuffing-error propagation and recovery (issue #118)
#
# Independent wire stimulus: the receive pins are driven directly from the
# bit-level model (`usb_bit_model`), not looped back from the DUT's own TX
# path, because TX can only ever emit correctly stuffed frames. No new error
# semantics are invented: the wrapper's contract under test is the existing
# one -- `RxError` is the destuffer's `stuff_err` (a seventh consecutive 1 in
# the decoded stream) registered and gated by `rx_receiving`; `RxActive`
# falls on EOP; byte assembly is cleared whenever reception ends.
# ---------------------------------------------------------------------------

SE0_CELL = (0, 0)
J_CELL = (1, 0)
IDLE_LEAD = 6          # idle J clocks before a frame
IDLE_TAIL = 14         # idle J clocks after EOP (EOP detector + pipeline drain)
# Upper bound, in clocks after the first SE0 cell is presented, by which
# RxActive must have fallen (2 SE0 cells to qualify the EOP + registered
# pulse + `rx_receiving` clear). Finite and small; not a timing claim beyond
# "terminates promptly".
RX_ACTIVE_FALL_BOUND = 6


def _rx_frame_cells(body_bits, eop=True):
    """Wire cells for SYNC + `body_bits` (already stuffed/violated as the
    caller wants) NRZI-encoded from idle J, then SE0,SE0,J if `eop`."""
    line = nrzi_encode(_byte_to_bits(SYNC_BYTE) + list(body_bits))
    cells = [_line_to_dpdm(b) for b in line]
    if eop:
        cells += [SE0_CELL, SE0_CELL, J_CELL]
    return cells


def _good_body(payload):
    stuffed, _flags = bit_stuff(_byte_to_bits_list(payload))
    return stuffed


async def _drive_rx_cells(dut, cells, trace=None):
    """Present `cells` on rxdp/rxdm, one per clock, sampling the UTMI RX
    outputs after each edge. Appends to `trace` (a dict of lists) and
    returns it."""
    if trace is None:
        trace = {"active": [], "error": [], "valid": [], "bytes": [], "cells": []}
    for dp, dm in cells:
        dut.rxdp.value = dp
        dut.rxdm.value = dm
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)
        trace["cells"].append((dp, dm))
        trace["active"].append(int(dut.RxActive.value))
        trace["error"].append(int(dut.RxError.value))
        v = int(dut.RxValid.value)
        trace["valid"].append(v)
        if v:
            trace["bytes"].append(int(dut.DataIn.value))
    return trace


async def _drive_rx_frame(dut, body_bits, trace=None):
    cells = ([J_CELL] * IDLE_LEAD + _rx_frame_cells(body_bits)
             + [J_CELL] * IDLE_TAIL)
    return await _drive_rx_cells(dut, cells, trace)


def _assert_rx_terminated(trace, what):
    """RxActive is low at the end of the trace and fell within the bound
    after the first SE0 cell of the EOP."""
    assert trace["active"][-1] == 0, f"{what}: RxActive still high after EOP"
    first_se0 = trace["cells"].index(SE0_CELL)
    window = trace["active"][first_se0:first_se0 + RX_ACTIVE_FALL_BOUND + 1]
    assert 0 in window, (
        f"{what}: RxActive did not fall within {RX_ACTIVE_FALL_BOUND} clocks "
        f"of EOP: {window}"
    )


async def _assert_clean_packet(dut, payload, what):
    trace = await _drive_rx_frame(dut, _good_body(payload))
    assert trace["bytes"] == payload, f"{what}: bytes {trace['bytes']} != {payload}"
    assert not any(trace["error"]), f"{what}: RxError inherited / spurious"
    assert any(trace["active"]), f"{what}: RxActive never asserted"
    _assert_rx_terminated(trace, what)
    return trace


@cocotb.test()
async def test_rx_clean_wire_packet_has_no_error(dut):
    """Control: the independent wire driver, with correct stuffing (including
    a mid-byte stuffed 0 and the #7.1.9 trailing stuffed 0), yields exact
    bytes and no RxError -- so a pulse in the tests below is caused by the
    injected violation, not by the stimulus."""
    await _start_clock(dut)
    await _reset(dut)

    await _assert_clean_packet(dut, [0x00, 0xFF, 0xA5], "mid-byte stuff control")
    await _assert_clean_packet(dut, [0x00, 0xFC], "trailing stuff control")


@cocotb.test()
async def test_rx_missing_stuff_bit_mid_byte_reaches_rxerror(dut):
    """Delete the stuffed 0 from inside a byte (0xFF: six 1s, [0], 1, 1): the
    decoded stream carries a seventh consecutive 1 while RxActive is high.
    RxError must pulse (exactly once, during active reception), RxActive must
    terminate, and the next clean packet must receive exact bytes with no
    inherited error."""
    await _start_clock(dut)
    await _reset(dut)

    payload = [0x00, 0xFF, 0xA5]
    stuffed, flags = bit_stuff(_byte_to_bits_list(payload))
    stuff_pos = flags.index(True)
    bad = stuffed[:stuff_pos] + stuffed[stuff_pos + 1:]
    assert bad != stuffed

    trace = await _drive_rx_frame(dut, bad)
    pulses = [i for i, e in enumerate(trace["error"]) if e]
    assert len(pulses) == 1, f"expected exactly one RxError pulse, got {pulses}"
    assert trace["active"][pulses[0]] == 1, "RxError pulsed outside active reception"
    first_se0 = trace["cells"].index(SE0_CELL)
    assert pulses[0] < first_se0, "RxError arrived after EOP began, not mid-packet"

    # Timing derived from the interface: the violating bit is the 7th 1 of
    # the run, i.e. bad[stuff_pos] at wire cell (IDLE_LEAD + 8 + stuff_pos),
    # the first body cell after SYNC being IDLE_LEAD + 8. The error is a
    # registered chain (decoder -> destuffer -> RxError), so it must follow
    # that cell by a small, fixed number of clocks.
    violating_cell = IDLE_LEAD + 8 + stuff_pos
    latency = pulses[0] - violating_cell
    assert 0 <= latency <= 4, f"RxError latency {latency} from the violating cell"
    dut._log.info(f"RxError latency from violating wire cell: {latency} clocks")

    _assert_rx_terminated(trace, "mid-byte violation packet")

    # Recovery: nothing leaks into the following clean packet.
    await _assert_clean_packet(dut, [0x3C, 0xFF, 0x01], "post-violation recovery")


@cocotb.test()
async def test_rx_missing_trailing_stuff_bit_near_eop_reaches_rxerror(dut):
    """The packet ends on six 1s, and the mandatory trailing stuffed 0 is
    replaced by a 1 immediately before EOP (violation adjacent to EOP). The
    error must still reach RxError before RxActive falls; termination is
    finite; the next clean packet is exact."""
    await _start_clock(dut)
    await _reset(dut)

    payload = [0x00, 0xFC]
    stuffed, flags = bit_stuff(_byte_to_bits_list(payload))
    assert flags[-1] and stuffed[-1] == 0, "model should end with a trailing stuff 0"
    bad = stuffed[:-1] + [1]

    trace = await _drive_rx_frame(dut, bad)
    pulses = [i for i, e in enumerate(trace["error"]) if e]
    assert len(pulses) == 1, f"expected exactly one RxError pulse, got {pulses}"
    assert trace["active"][pulses[0]] == 1, "RxError pulsed outside active reception"
    # The violating 1 is the last body bit, directly before the SE0 cells.
    violating_cell = IDLE_LEAD + 8 + len(bad) - 1
    latency = pulses[0] - violating_cell
    assert 0 <= latency <= 4, f"RxError latency {latency} from the violating cell"
    _assert_rx_terminated(trace, "near-EOP violation packet")

    await _assert_clean_packet(dut, [0xC3, 0x00, 0xFF], "post-near-EOP recovery")


@cocotb.test()
async def test_rx_error_not_raised_after_reception_ends(dut):
    """A run of 1s on the wire while no packet is active (no SYNC) must not
    raise RxError (the destuffer is enable-gated by rx_receiving, and the
    wrapper additionally gates its error with it)."""
    await _start_clock(dut)
    await _reset(dut)

    # Idle J is a stream of NRZI 1s -- far more than seven of them.
    trace = await _drive_rx_cells(dut, [J_CELL] * 40)
    assert not any(trace["error"]), "RxError raised with no packet active"
    assert not any(trace["active"]), "RxActive raised on idle"


@cocotb.test()
async def test_rx_utmi_reset_mid_packet_clears_pipeline(dut):
    """Assert UTMI Reset while a packet is partway through reception (a
    partial byte already shifted in). RxActive must drop, no RxValid/DataIn
    leaks from the half-assembled byte, no RxError; the rest of the aborted
    packet (no SYNC for it to lock onto) is ignored, and the next clean
    packet is received exactly."""
    await _start_clock(dut)
    await _reset(dut)

    payload = [0x11, 0x22, 0x33, 0x44]
    body = _good_body(payload)
    cells = [J_CELL] * IDLE_LEAD + _rx_frame_cells(body)
    # Reset lands 8 (SYNC) + 8 + 8 + 3 bits in: two bytes delivered, three
    # bits of the third shifted in.
    cut = IDLE_LEAD + 8 + 19

    trace = await _drive_rx_cells(dut, cells[:cut])
    assert trace["bytes"] == payload[:2], f"pre-reset bytes: {trace['bytes']}"
    assert trace["active"][-1] == 1, "packet not active at the reset point"

    # Reset for two clocks while the rest of the packet keeps arriving.
    dut.Reset.value = 1
    post = await _drive_rx_cells(dut, cells[cut:cut + 2])
    dut.Reset.value = 0
    assert post["active"][-1] == 0, "RxActive not cleared by Reset"
    assert not any(post["valid"]), "RxValid pulsed during Reset"

    rest = await _drive_rx_cells(dut, cells[cut + 2:] + [J_CELL] * IDLE_TAIL)
    assert not any(rest["valid"]), f"bytes leaked after Reset: {rest['bytes']}"
    assert not any(rest["error"]), "RxError after Reset"
    assert not any(rest["active"]), "aborted packet's tail re-activated RxActive"

    await _assert_clean_packet(dut, [0x5A, 0xFF, 0x00, 0x81], "post-Reset reception")


@cocotb.test()
async def test_rx_utmi_reset_after_stuffing_error_mid_packet(dut):
    """Reset arriving after a stuffing error, still inside the active packet,
    leaves no error or byte state behind: the following clean packet is
    exact and error-free."""
    await _start_clock(dut)
    await _reset(dut)

    payload = [0x00, 0xFF, 0xA5, 0x0F]
    stuffed, flags = bit_stuff(_byte_to_bits_list(payload))
    stuff_pos = flags.index(True)
    bad = stuffed[:stuff_pos] + stuffed[stuff_pos + 1:]
    cells = [J_CELL] * IDLE_LEAD + _rx_frame_cells(bad)

    cut = IDLE_LEAD + 8 + stuff_pos + 6   # a few clocks past the violation
    trace = await _drive_rx_cells(dut, cells[:cut])
    assert any(trace["error"]), "violation did not reach RxError before Reset"
    assert trace["active"][-1] == 1

    dut.Reset.value = 1
    await _drive_rx_cells(dut, [cells[cut]])
    dut.Reset.value = 0
    assert int(dut.RxActive.value) == 0
    assert int(dut.RxError.value) == 0

    rest = await _drive_rx_cells(dut, [J_CELL] * 20)
    assert not any(rest["error"]) and not any(rest["valid"])

    await _assert_clean_packet(dut, [0x7E, 0xFF, 0x12], "post-error-Reset reception")


# ---------------------------------------------------------------------------
# RX reset assertion / release, edge-timed (issue #132)
#
# Contract under test (spec/decisions/0006): UTMI `Reset` is synchronous to
# the interface clock on the receive side too.
#
#   * Nothing at the RX ports (`RxActive`, `RxValid`, `RxError`, `DataIn`)
#     changes between clock edges when `Reset` rises or falls: checked 1 ns
#     after the change and again shortly before the next rising edge.
#   * The edge that samples `Reset` high aborts reception: `RxActive`,
#     `RxValid` and `RxError` are low after it and stay low on every reset
#     clock, whatever the wire carries. A byte or error the pipeline was about
#     to deliver on that edge is suppressed. `DataIn` is not cleared (it is
#     only meaningful with `RxValid`); it simply does not change.
#   * After release the receiver restarts from the idle-J NRZI reference with
#     an empty SYNC search and a zero stuffing run. The aborted packet's tail
#     (no SYNC for it to lock onto) is ignored, whether the wire sampled by the
#     release edge is J or K, and the next SYNC/payload/EOP is received
#     exactly -- including a SYNC whose first K is the cell the release edge
#     itself samples, so no first payload bit is dropped.
#
# Injection points are named from the frame model, not from the RTL. A cell
# presented before edge t reaches `LineState` at t, the NRZI decoder's output
# at t+1, the destuffer's output at t+2 and `RxValid`/`RxError` at t+3 (the
# fixed registered chain the #118 tests above already measure). `cut` is the
# index of the cell whose edge is the first to sample `Reset` high, so the
# destuffer would have been processing body cell `cut - 2` on that edge.
# When the simulated netlist exposes the RTL's destuffer run counter it is
# read only to confirm the stuffing boundary was hit, never to form an
# expectation.
# ---------------------------------------------------------------------------

# Aborted packet: an ordinary first byte, a 0xFF whose six leading 1s force a
# mid-byte stuffed 0, then two more bytes (no SYNC pattern anywhere in the
# decoded tail). Fresh packet: sixteen leading 1s (two stuffed 0s; an
# inherited run would move the first one) and a trailing #7.1.9 stuff bit.
RX_RESET_ABORTED = [0x5A, 0xFF, 0x3C, 0xFC]
RX_RESET_FRESH = [0xFF, 0xFF, 0x00, 0xFC]

RX_RESET_PHASES = [
    "sync",           # mid-SYNC, reception not yet active
    "sync_final",     # SYNC's final bit at the destuffer: arming edge preempted
    "first_bit",      # first PID bit at the destuffer
    "partial_byte",   # byte 2, three bits already shifted in
    "byte_complete",  # the edge that would deliver byte 1 on RxValid
    "six_ones",       # sixth consecutive 1 at the destuffer (run 5 -> 6)
    "stuff_bit",      # the stuffed 0 at the destuffer (run == 6)
    "error",          # violating seventh 1 at the destuffer (stuff_err edge)
    "error_out",      # stuff_err registered, the RxError edge preempted
    "eop",            # first SE0 cell of the EOP
]

K_CELL = (0, 1)

PORTS_ONLY_ENV = "USB_UTMI_PHY_TB_PORTS_ONLY"


def _stuffed_index(flags, data_index):
    """Index into the stuffed stream of the `data_index`-th real data bit."""
    seen = -1
    for i, is_stuff in enumerate(flags):
        if not is_stuff:
            seen += 1
            if seen == data_index:
                return i
    raise ValueError(data_index)


def _rx_reset_plan(phase):
    """(cells, cut, run_expected, delivered) for `phase`.

    `cells` is the aborted frame (idle lead, SYNC, body, EOP); `cut` as in
    the section header; `run_expected` is the destuffer run count the RTL
    should hold just before the reset edge (whitebox confirmation only, None
    when not meaningful); `delivered` is how many aborted bytes RxValid must
    have delivered before the reset edge."""
    payload = RX_RESET_ABORTED
    stuffed, flags = bit_stuff(_byte_to_bits_list(payload))
    stuff_pos = flags.index(True)
    body0 = IDLE_LEAD + 8
    body = stuffed
    if phase in ("error", "error_out"):
        body = stuffed[:stuff_pos] + stuffed[stuff_pos + 1:]
    cells = [J_CELL] * IDLE_LEAD + _rx_frame_cells(body)
    run = None
    if phase == "sync":
        cut = IDLE_LEAD + 4
    elif phase == "sync_final":
        cut = IDLE_LEAD + 7 + 2
    elif phase == "first_bit":
        cut = body0 + 2
    elif phase == "partial_byte":
        cut = body0 + _stuffed_index(flags, 19) + 2
    elif phase == "byte_complete":
        cut = body0 + _stuffed_index(flags, 15) + 3
    elif phase == "six_ones":
        cut = body0 + stuff_pos - 1 + 2
        run = 5
    elif phase in ("stuff_bit", "error"):
        cut = body0 + stuff_pos + 2
        run = 6
    elif phase == "error_out":
        cut = body0 + stuff_pos + 3
    elif phase == "eop":
        cut = cells.index(SE0_CELL)
    else:
        raise ValueError(phase)
    # A byte reaches RxValid three edges after its last cell's edge.
    delivered = 0
    for b in range(len(payload)):
        last = body0 + _stuffed_index(flags, 8 * b + 7)
        if phase in ("error", "error_out") and _stuffed_index(flags, 8 * b + 7) > stuff_pos:
            last -= 1
        if last + 3 < cut:
            delivered += 1
    return cells, cut, run, delivered


def _rx_ports(dut):
    """RX port snapshot (binary strings: DataIn is legitimately X until the
    first byte, since it is never reset)."""
    return (str(dut.RxActive.value), str(dut.RxValid.value),
            str(dut.RxError.value), str(dut.DataIn.value))


async def _assert_rx_ports_hold(dut, expect, what):
    """Called right after a falling edge, having just changed `Reset`: the RX
    ports must not move before the next rising edge."""
    await Timer(1, unit="ns")
    assert _rx_ports(dut) == expect, f"{what}: RX ports changed 1 ns after Reset moved"
    await Timer(max(_clock_period_ps() // 2 - 3000, 1), unit="ps")
    assert _rx_ports(dut) == expect, (
        f"{what}: RX ports changed before the sampling edge")


def _probe_path(dut, path, width):
    """Like `_probe`, for a hierarchical path (RTL only; None when the
    netlist does not expose it with the RTL's width, or when the
    `USB_UTMI_PHY_TB_PORTS_ONLY` environment variable is set -- a ports-only
    replay of the RTL, used to establish which checks are port-observable)."""
    if os.environ.get(PORTS_ONLY_ENV):
        return None
    try:
        handle = dut
        for part in path.split("."):
            handle = getattr(handle, part)
        if len(handle) != width:
            return None
        return int(handle.value)
    except (AttributeError, TypeError, ValueError):
        return None


def _assert_rx_internal_cleared(dut, what, released=False):
    """RTL-only whitebox check (skipped when the netlist does not expose the
    RTL names): after an edge that sampled `Reset` high, the vendored
    decoder holds the idle-J reference and the destuffer has a zero run, no
    forwarded bit and no error -- the state its asynchronous reset used to
    produce. After the release edge additionally nothing has reached the
    SYNC search or the destuffer (`released`): the reset-edge strobe the
    decoder emits is masked. Port-level tests cannot see all of this (see
    spec/decisions/0006's coverage limit), so it is checked here."""
    expect = {
        "u_decoder.prev_level": (1, 1),
        "u_destuffer.ones_run": (3, 0),
        "u_destuffer.bit_valid": (1, 0),
        "u_destuffer.stuff_err": (1, 0),
    }
    if released:
        expect["u_sync_detector.match"] = (4, 0)
    for path, (width, want) in expect.items():
        got = _probe_path(dut, path, width)
        if got is not None:
            assert got == want, f"{what}: {path} = {got}, expected {want}"


def _decoded_tail_has_sync(cells):
    """Would the receiver find SYNC in `cells`, starting right after a
    release edge? The release edge decodes the line-state register's reset
    value (J) against the idle-J reference, then each J/K cell in turn (SE0
    cells are not NRZI data). Precondition for the stimulus, not a claim."""
    levels = [1] + [1 if c == J_CELL else 0 for c in cells if c in (J_CELL, K_CELL)]
    bits = nrzi_decode(levels)
    pattern = _byte_to_bits(SYNC_BYTE)
    return any(bits[i:i + 8] == pattern for i in range(len(bits) - 7))


@cocotb.test()
@cocotb.parametrize(phase=RX_RESET_PHASES, hold=[1, 3], release=["J", "K"])
async def test_rx_utmi_reset_edge_timed_abort_and_release(dut, phase, hold, release):
    """UTMI Reset raised between edges during reception (SYNC, the arming
    edge, the first PID bit, a partial byte, a byte-delivery edge, a six-1
    run, the stuffed 0, a stuffing violation and its RxError edge, EOP):
    ports hold until the sampling edge, the edge aborts with no byte or error
    delivered, every reset clock keeps RX quiet, release with J or K on the
    wire ignores the aborted tail, and a fresh packet is received exactly."""
    await _start_clock(dut)
    await _reset(dut)

    cells, cut, run_expected, delivered = _rx_reset_plan(phase)
    release_cell = J_CELL if release == "J" else K_CELL
    tail = [release_cell] + cells[cut + hold + 1:] + [J_CELL] * IDLE_TAIL
    assert not _decoded_tail_has_sync(tail), f"{phase}: stimulus tail contains SYNC"

    # --- 1. Receive the aborted frame up to the injection point. ---
    pre = await _drive_rx_cells(dut, cells[:cut])
    assert pre["bytes"] == RX_RESET_ABORTED[:delivered], (
        f"{phase}: bytes before reset {pre['bytes']}, expected "
        f"{RX_RESET_ABORTED[:delivered]}")
    assert not any(pre["error"]), f"{phase}: RxError before the reset edge"
    if phase not in ("sync", "sync_final"):
        assert pre["active"][-1] == 1, f"{phase}: reception not active at injection"
    run = _probe_path(dut, "u_destuffer.ones_run", 3)
    if run_expected is not None and run is not None:
        assert run == run_expected, (
            f"{phase}: injection coverage -- destuffer run {run}, expected {run_expected}")
    dut._log.info(
        f"phase={phase} hold={hold} release={release}: reset edge at cell {cut} "
        f"of {len(cells)}; {delivered} byte(s) delivered; destuffer run "
        f"{run if run is not None else 'n/a (not exposed)'}")

    # --- 2. Raise Reset mid-clock: ports hold until the sampling edge. ---
    before = _rx_ports(dut)
    data_in = before[3]
    dut.Reset.value = 1
    dut.rxdp.value, dut.rxdm.value = cells[cut]
    await _assert_rx_ports_hold(dut, before, f"{phase} assert")

    # --- 3. Every reset clock: RX quiet, DataIn unchanged. ---
    for n in range(hold):
        during = await _drive_rx_cells(dut, [cells[cut + n]])
        assert (during["active"][0], during["valid"][0], during["error"][0]) == (0, 0, 0), (
            f"{phase}: reset clock {n}: RxActive/RxValid/RxError = "
            f"{during['active'][0]}/{during['valid'][0]}/{during['error'][0]}")
        _assert_rx_internal_cleared(dut, f"{phase}: reset clock {n}")
    assert str(dut.DataIn.value) == data_in, f"{phase}: DataIn changed under Reset"

    # --- 4. Release mid-clock with J or K on the wire; ports hold. ---
    quiet = _rx_ports(dut)
    dut.Reset.value = 0
    dut.rxdp.value, dut.rxdm.value = release_cell
    await _assert_rx_ports_hold(dut, quiet, f"{phase} release")

    # --- 5. The aborted tail is ignored. ---
    rest = await _drive_rx_cells(dut, tail[:1])
    _assert_rx_internal_cleared(dut, f"{phase}: release edge", released=True)
    rest = await _drive_rx_cells(dut, tail[1:], rest)
    assert not any(rest["active"]), f"{phase}: aborted tail re-activated RxActive"
    assert not any(rest["valid"]), f"{phase}: bytes leaked after release: {rest['bytes']}"
    assert not any(rest["error"]), f"{phase}: RxError after release"
    assert str(dut.DataIn.value) == data_in, f"{phase}: DataIn changed after release"

    # --- 6. A fresh packet is exact. ---
    await _assert_clean_packet(dut, RX_RESET_FRESH, f"{phase} fresh packet")


@cocotb.test()
@cocotb.parametrize(before=["J", "K"], hold=[1, 3], gap=[0, 1])
async def test_rx_utmi_reset_release_straight_into_sync(dut, before, hold, gap):
    """Reset raised with J or K as the last cell before it (so the first
    reset edge sees that level in the line-state register), then a fresh
    frame starting `gap` cells after the release clock -- with `gap` 0 the
    release edge itself samples SYNC's first K. The NRZI reference after
    release must be idle J whatever the line was, and the stuffing run zero,
    so SYNC locks and the first PID bit is neither dropped nor mis-decoded
    (both payloads open with the bit that a wrong reference or a one-bit
    slip would flip). `before`=K, `hold`=1, `gap`=0 is the one case where a
    decoder left holding the pre-reset level (K) would emit a decoded 0
    just ahead of SYNC and lose the packet."""
    await _start_clock(dut)
    await _reset(dut)

    lead = [J_CELL] * IDLE_LEAD + ([K_CELL] if before == "K" else [])
    for payload in ([0xFF, 0xFF, 0x00, 0xFC], [0x2D, 0x00, 0x10]):
        await _drive_rx_cells(dut, lead)
        dut.Reset.value = 1
        await _drive_rx_cells(dut, [J_CELL] * hold)
        dut.Reset.value = 0
        frame = [J_CELL] * gap + _rx_frame_cells(_good_body(payload))
        trace = await _drive_rx_cells(dut, frame + [J_CELL] * IDLE_TAIL)
        assert trace["bytes"] == payload, (
            f"before={before} hold={hold} gap={gap}: bytes {trace['bytes']} != {payload}")
        assert not any(trace["error"]), f"before={before} hold={hold} gap={gap}: RxError"
        _assert_rx_terminated(trace, f"before={before} hold={hold} gap={gap}")


RX_RESET_UNSAMPLED_PHASES = ["sync", "partial_byte", "six_ones", "stuff_bit"]


@cocotb.test()
@cocotb.parametrize(phase=RX_RESET_UNSAMPLED_PHASES)
async def test_rx_utmi_reset_pulse_between_edges_is_not_sampled(dut, phase):
    """Structural probe, not a UTMI-legal stimulus: a `Reset` pulse that rises
    and falls between two clock edges is sampled by no edge, so a receiver
    that consumes `Reset` only synchronously must ignore it completely -- the
    packet in flight is received exactly, with no error. Any asynchronous
    path from `Reset` into RX state (the former `int_rst_n` on the vendored
    decoder's and destuffer's reset port, spec/decisions/0002 Decision 5)
    clears the NRZI reference, the decoded bit in flight and the stuffing
    run, which this test sees at the ports."""
    await _start_clock(dut)
    await _reset(dut)

    payload = RX_RESET_ABORTED
    cells, cut, run_expected, _delivered = _rx_reset_plan(phase)
    cells = cells + [J_CELL] * IDLE_TAIL

    trace = await _drive_rx_cells(dut, cells[:cut])
    run = _probe_path(dut, "u_destuffer.ones_run", 3)
    if run_expected is not None and run is not None:
        assert run == run_expected, (
            f"{phase}: injection coverage -- destuffer run {run}, expected {run_expected}")
    before = _rx_ports(dut)
    await Timer(5, unit="ns")
    dut.Reset.value = 1
    await Timer(5, unit="ns")
    dut.Reset.value = 0
    await Timer(1, unit="ns")
    assert _rx_ports(dut) == before, f"{phase}: RX ports moved during the pulse"

    trace = await _drive_rx_cells(dut, cells[cut:], trace)
    assert trace["bytes"] == payload, (
        f"{phase}: unsampled Reset pulse corrupted reception: "
        f"{trace['bytes']} != {payload}")
    assert not any(trace["error"]), f"{phase}: unsampled Reset pulse raised RxError"
    _assert_rx_terminated(trace, phase)


# ---------------------------------------------------------------------------
# TX reset-and-recovery (issue #130)
#
# UTMI `Reset` is folded into the internal reset (`int_rst_n = rst_n &
# ~Reset`) that clears the TX framer, the vendored stuffer and the vendored
# NRZI encoder together. The RX-side tests above interrupt reception; these
# interrupt *transmission* at selected wire phases and then require the first
# packet after release to be bit-exact against the independent model.
#
# Contract under test (issue #130's statement of the UTMI reset semantics;
# spec/decisions/0005 records the RTL change this regression forced -- the
# vendored transforms' asynchronous reset port had let `Reset` change the
# wire mid-clock, before the sampling edge):
#
#   * Reset is synchronous: the edge that samples `Reset` high is the edge on
#     which the wire returns to idle J and `TxReady` returns to its idle value
#     (high, as in `test_reset_state`). Before that edge the in-flight cell is
#     still on the wire (checked 1 ns after `Reset` is raised).
#   * While `Reset` is high nothing is accepted, whatever `TxValid` and
#     `TxReady` read: the wire stays at idle J on every reset clock.
#   * Acceptance at release follows the ordinary UTMI handshake: the first
#     rising edge that samples `Reset` low with `TxValid` and `TxReady` both
#     high accepts `DataOut`. With `TxValid` held high through reset that is
#     the release edge itself, so SYNC's first cell (K) is on the wire right
#     after it; with `TxValid` low the link starts the packet whenever it
#     chooses (here two idle clocks later).
#
# Phase selection is port-only and model-derived: the injection point is
# named by the index `c` (into the model's SYNC + stuffed payload + SE0,SE0,J
# wire sequence) of the cell the reset edge preempts, and the test first
# checks that cells 0..c-1 appeared on the wire exactly as the model predicts
# -- so the phase of cell `c` is known from the model, not from the RTL. When
# the simulated netlist exposes the RTL's `tx_state` / `stuff_consume` with
# the RTL's width (the RTL run; a routed gate-level netlist re-encodes
# `tx_state` one-hot), they are read only to *confirm* injection coverage,
# never to form an expectation.
# ---------------------------------------------------------------------------

TX_EOP_TAIL = [SE0_CELL, SE0_CELL, J_CELL]

# Aborted packet: an ordinary first byte (0x5A), a 0xFF whose eight 1s force a
# mid-byte stuffed 0, and a trailing 0xFC whose six final 1s owe the #7.1.9
# trailing stuff bit (TX_FLUSH) before EOP.
TX_RESET_ABORTED = [0x5A, 0xFF, 0x3C, 0xFC]
# Fresh packet after release: opens with sixteen 1s (two stuffed 0s; an
# inherited stuffer run would move the first one early) and ends with the
# trailing-stuff case. Distinct from every aborted byte, so a stale byte,
# duplicate or leaked run shows up as a wire mismatch.
TX_RESET_FRESH = [0xFF, 0xFF, 0x00, 0xFC]

# RTL `tx_state` encodings, for the optional whitebox coverage confirmation.
_TX_STATE_NAMES = {1: "TX_SYNC", 2: "TX_DATA", 3: "TX_FLUSH", 4: "TX_HOLD",
                   5: "TX_EOP0", 6: "TX_EOP1", 7: "TX_EOPJ"}

TX_RESET_PHASES = ["sync", "sync_last", "payload", "stuff", "flush", "hold",
                   "eop_se0", "eop_j", "eop_idle"]


def _tx_full_wire(payload):
    """Model wire sequence for one packet: SYNC + stuffed payload + EOP tail."""
    return _expected_wire_dpdm(payload) + TX_EOP_TAIL


def _tx_reset_cell(phase, payload):
    """(c, rtl_state) for `phase`: `c` is the index into `_tx_full_wire` of
    the cell the reset edge preempts (cells 0..c-1 are on the wire first);
    `rtl_state` is the RTL state expected to be in flight then (whitebox
    confirmation only). Asserts that `payload` actually has the phase."""
    stuffed, flags = bit_stuff(_byte_to_bits_list(payload))
    body = 8
    end = body + len(stuffed)  # index of the first EOP SE0 cell
    if phase == "sync":
        return 4, "TX_SYNC"           # SYNC bit 4 in flight
    if phase == "sync_last":
        # SYNC's final bit (the only 1 in 8'h80) in flight: the SYNC bit
        # index is at its last value, so a reset that failed to re-arm it
        # would open the next packet with a 1 (J) instead of K.
        return 7, "TX_SYNC"
    if phase == "payload":
        assert not any(flags[:4])
        return body + 3, "TX_DATA"    # byte 0 bit 3, an ordinary data bit
    if phase == "stuff":
        pos = flags.index(True)
        assert pos < len(stuffed) - 1, "need a mid-packet stuff bit"
        return body + pos, "TX_DATA"  # the inserted 0 itself (run count 6)
    if phase == "flush":
        assert flags[-1], "payload must owe a trailing stuff bit"
        return end - 1, "TX_FLUSH"    # the #7.1.9 trailing stuffed 0
    if phase == "hold":
        return end, "TX_HOLD"         # last level's own wire clock -> SE0
    if phase == "eop_se0":
        return end + 1, "TX_EOP0"     # first SE0 on the wire, second pending
    if phase == "eop_j":
        return end + 2, "TX_EOP1"     # second SE0 on the wire, EOP J pending
    if phase == "eop_idle":
        return end + 3, "TX_EOPJ"     # EOP J on the wire, idle pending
    raise ValueError(phase)


def _probe(dut, name, width):
    """Internal signal value if the netlist exposes it with the RTL's width,
    else None. A synthesized/routed netlist may keep the name but re-encode
    the register (yosys turns the 3-bit `tx_state` into a one-hot vector),
    so a width mismatch means "not the RTL encoding" and is not read."""
    try:
        handle = getattr(dut, name)
        if len(handle) != width:
            return None
        return int(handle.value)
    except (AttributeError, TypeError, ValueError):
        return None


async def _tx_cycle(dut, trace, loopback=True):
    """One clock: edge, then sample the wire and UTMI outputs after it."""
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    sample = (int(dut.txdp.value), int(dut.txdm.value))
    trace["wire"].append(sample)
    trace["ready"].append(int(dut.TxReady.value))
    trace["error"].append(int(dut.RxError.value))
    if int(dut.RxValid.value):
        trace["rx_bytes"].append(int(dut.DataIn.value))
    if loopback:
        dut.rxdp.value = sample[0]
        dut.rxdm.value = sample[1]
    return sample


def _new_trace():
    return {"wire": [], "ready": [], "error": [], "rx_bytes": []}


@cocotb.test()
@cocotb.parametrize(
    phase=TX_RESET_PHASES,
    hold=[1, 3],
    txvalid_held=[False, True],
)
async def test_tx_utmi_reset_aborts_and_recovers(dut, phase, hold, txvalid_held):
    """UTMI Reset during transmission (SYNC, ordinary payload bit, inserted
    stuff bit, trailing-stuff flush, last-level hold, each EOP tail cell)
    aborts the packet on the sampling edge, holds idle J / TxReady-idle for
    every reset clock (TxValid low or held high), and the first packet after
    release is bit-exact -- SYNC, stuffed payload including a trailing stuff
    bit, EOP -- with no stale byte, NRZI reference or stuffing run. The
    looped-back RX path receives exactly the fresh packet's bytes."""
    await _start_clock(dut)
    await _reset(dut)

    aborted, fresh = TX_RESET_ABORTED, TX_RESET_FRESH
    full_aborted = _tx_full_wire(aborted)
    full_fresh = _tx_full_wire(fresh)
    c, rtl_state = _tx_reset_cell(phase, aborted)
    assert 1 <= c <= len(full_aborted)

    # --- 1. Send the aborted packet until cells 0..c-1 are on the wire. ---
    trace = _new_trace()
    pre = []
    idx = 0
    started = False
    for _ in range(4 * len(full_aborted)):
        if len(pre) == c:
            break
        have = idx < len(aborted)
        dut.TxValid.value = 1 if have else 0
        dut.DataOut.value = aborted[idx] if have else 0
        ready = int(dut.TxReady.value)
        sample = await _tx_cycle(dut, trace)
        if have and ready:
            idx += 1
            started = True
        if started:
            pre.append(sample)
    assert pre == full_aborted[:c], (
        f"{phase}: wire before injection disagrees with the model: "
        f"{pre} != {full_aborted[:c]}"
    )

    # --- 2. Raise Reset. Synchronous: the in-flight cell stays until the edge.
    dut.Reset.value = 1
    dut.TxValid.value = 1 if txvalid_held else 0
    dut.DataOut.value = fresh[0] if txvalid_held else 0
    await Timer(1, unit="ns")
    in_flight = (int(dut.txdp.value), int(dut.txdm.value))
    assert in_flight == full_aborted[c - 1], (
        f"{phase}: wire changed before the reset edge (not synchronous): "
        f"{in_flight} != {full_aborted[c - 1]}"
    )
    assert int(dut.TxReady.value) == trace["ready"][-1], (
        f"{phase}: TxReady changed before the reset edge (not synchronous)"
    )
    state = _probe(dut, "tx_state", 3)
    if state is not None:
        assert _TX_STATE_NAMES.get(state) == rtl_state, (
            f"{phase}: injection coverage -- RTL in {state}, expected {rtl_state}"
        )
        consume = _probe(dut, "stuff_consume", 1)
        if phase == "stuff":
            assert consume == 0, "stuff phase: stuffer not inserting at injection"
        elif phase == "payload":
            assert consume == 1, "payload phase: stuffer not consuming data"
    dut._log.info(
        f"phase={phase} hold={hold} txvalid_held={txvalid_held}: reset preempts "
        f"model cell {c} of {len(full_aborted)}; in-flight RTL state "
        f"{_TX_STATE_NAMES.get(state, state) if state is not None else 'n/a (not exposed)'}"
    )

    rx_mark = len(trace["rx_bytes"])
    err_mark = len(trace["error"])
    for n in range(hold):
        sample = await _tx_cycle(dut, trace)
        assert sample == J_CELL, (
            f"{phase}: reset clock {n}: wire {sample} is not idle J"
        )
        assert trace["ready"][-1] == 1, (
            f"{phase}: reset clock {n}: TxReady not at its idle value"
        )

    # --- 3. Release and send the fresh packet through the normal handshake.
    dut.Reset.value = 0
    post_start = len(trace["wire"])
    if not txvalid_held:
        dut.TxValid.value = 0
        dut.DataOut.value = 0
        for _ in range(2):
            await _tx_cycle(dut, trace)
    accepts = []
    idx = 0
    for _ in range(len(full_fresh) + 16):
        have = idx < len(fresh)
        dut.TxValid.value = 1 if have else 0
        dut.DataOut.value = fresh[idx] if have else 0
        ready = int(dut.TxReady.value)
        await _tx_cycle(dut, trace)
        if have and ready:
            accepts.append(len(trace["wire"]) - 1 - post_start)
            idx += 1
    post = trace["wire"][post_start:]

    assert len(accepts) == len(fresh), f"{phase}: accepted {len(accepts)} bytes"
    first = accepts[0]
    assert first == (0 if txvalid_held else 2), (
        f"{phase}: first fresh byte accepted at release+{first}, not per handshake"
    )
    expected = ([J_CELL] * first + full_fresh
                + [J_CELL] * (len(post) - first - len(full_fresh)))
    assert post == expected, (
        f"{phase}: post-release wire disagrees with the model\n"
        f"  got      {post}\n  expected {expected}"
    )

    rx_after = trace["rx_bytes"][rx_mark:]
    assert rx_after == fresh, (
        f"{phase}: loopback RX after reset got {rx_after}, expected {fresh}"
    )
    assert not any(trace["error"][err_mark:]), f"{phase}: RxError after reset"


@cocotb.test()
async def test_pu_en_follows_termselect_gated_by_rst_n(dut):
    """pu_en == TermSelect & rst_n for every rst_n/TermSelect/Reset/SuspendM
    combination, combinationally (DR-0004 decision 1)."""
    await _start_clock(dut)
    await _reset(dut)

    for rst_n in (0, 1):
        for term in (0, 1):
            for reset in (0, 1):
                for susp in (0, 1):
                    dut.rst_n.value = rst_n
                    dut.TermSelect.value = term
                    dut.Reset.value = reset
                    dut.SuspendM.value = susp
                    await Timer(1, unit="ns")
                    got = int(dut.pu_en.value)
                    assert got == (term & rst_n), (
                        f"rst_n={rst_n} TermSelect={term} Reset={reset} "
                        f"SuspendM={susp}: pu_en={got}"
                    )

    # Reset / SuspendM, alone and together, never drop pu_en.
    dut.rst_n.value = 1
    dut.TermSelect.value = 1
    for reset, susp in ((1, 1), (0, 0), (1, 0), (0, 1), (0, 1)):
        dut.Reset.value = reset
        dut.SuspendM.value = susp
        await Timer(1, unit="ns")
        assert int(dut.pu_en.value) == 1, f"Reset={reset} SuspendM={susp} dropped pu_en"

    # Not registered: changes take effect between clock edges, no edge needed.
    await FallingEdge(dut.clk)
    dut.Reset.value = 0
    dut.SuspendM.value = 1
    dut.TermSelect.value = 0
    await Timer(1, unit="ns")
    assert int(dut.pu_en.value) == 0, "pu_en did not fall with TermSelect before an edge"
    dut.TermSelect.value = 1
    await Timer(1, unit="ns")
    assert int(dut.pu_en.value) == 1, "pu_en did not rise with TermSelect before an edge"
    dut.rst_n.value = 0
    await Timer(1, unit="ns")
    assert int(dut.pu_en.value) == 0, "rst_n low did not force pu_en low (TermSelect high)"
    dut.rst_n.value = 1
    await Timer(1, unit="ns")
    assert int(dut.pu_en.value) == 1, "rst_n release did not restore pu_en"

    # Restore testbench inputs.
    await _reset(dut)
