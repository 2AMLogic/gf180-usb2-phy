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

Byte-level TX driving follows the same "read `ready` before the edge it
governs" convention `test_usb_bit_codec_loopback.py` established for the
bit-level stuffer handshake, applied here one level up at the UTMI
`TxValid`/`TxReady` byte handshake `usb_utmi_phy.v` implements.

This file is *input* to `klt functional-verification` (see
`request-usb-utmi-phy.json`), not a pytest module.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

from usb_bit_model import bit_stuff, nrzi_encode

# spec/usb2-device-phy.md #3 ratifies a 12 MHz interface clock. See
# test_usb_nrzi_encoder.py for why 83334 ps rather than 83333 ps.
CLK_PERIOD_PS = 83334

SYNC_BYTE = 0x80


def _byte_to_bits(byte):
    """LSB-first bit list for one byte, matching USB's own transmission order."""
    return [(byte >> i) & 1 for i in range(8)]


def _bits_to_byte(bits):
    value = 0
    for i, bit in enumerate(bits):
        value |= (bit & 1) << i
    return value


def _line_to_dpdm(line_bit):
    """1 = J (dp=1,dm=0), 0 = K (dp=0,dm=1) -- usb_utmi_phy.v's own mapping."""
    return (1, 0) if line_bit else (0, 1)


def _expected_wire_dpdm(payload_bytes):
    """(dp,dm) sequence for SYNC + payload, NRZI-encoded -- no EOP tail."""
    pre_stuff = _byte_to_bits(SYNC_BYTE)
    for b in payload_bytes:
        pre_stuff += _byte_to_bits(b)
    stuffed, _flags = bit_stuff(pre_stuff)
    line = nrzi_encode(stuffed)
    return [_line_to_dpdm(b) for b in line]


async def _start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_PS, unit="ps").start())


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
    `TX_SHIFT` is currently sending (a one-byte-ahead skid buffer, so the
    PHY can request the next byte while still shifting the current one out
    -- this is why offering only `len(packet)` bytes correctly stops after
    exactly that many accepts, even though none of them may have finished
    being shifted onto the wire yet). Deciding "safe to start the next
    packet" therefore cannot use a bare `TxReady` pulse -- that fires
    throughout the tail of the *current* packet's shifting too. This
    driver reads `tx_state` (internal, whitebox) directly instead, since
    `TX_IDLE` is the only state where `TxReady` is asserted, and the only
    one that's safe to start a new packet from.
    """
    TX_IDLE_STATE = 0
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
        elif ended_current and int(dut.tx_state.value) == TX_IDLE_STATE:
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
    # last encoded bit immediately before it (the TX_FLUSHCHECK/DRAIN
    # states hold the line steady while the pipeline empties; see
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
async def test_loopback_trailing_run_of_six_ones_is_flushed(dut):
    """A packet whose pre-stuff bit stream ends on exactly six 1s (USB 2.0
    #7.1.9's mandatory trailing-stuff-bit case) still round-trips: the
    wrapper's TX_FLUSHCHECK state must emit the trailing stuffed 0 before
    EOP, exactly as `usb_bit_stuffer.v`'s own header documents."""
    await _start_clock(dut)
    await _reset(dut)

    # SYNC's own bits contribute a trailing single 1 (its last bit). Choose
    # a payload whose LSB-first bit stream, appended after that single 1,
    # ends on a run of exactly six more 1s: 0xFC's LSB-first bits are
    # 0,0,1,1,1,1,1,1 -- six trailing 1s, immediately after a payload byte
    # ending on a 0 boundary so the run does not start earlier.
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


