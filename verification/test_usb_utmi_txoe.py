"""cocotb testbench for the `txoe` driver-enable output of
`rtl/usb_utmi_phy.v` (spec/decisions/0004, issue #113).

Kept in its own module, separate from `test_usb_utmi_phy.py`, on purpose:
that file is also replayed against the committed routed gate-level netlist
(`request-usb-utmi-phy-gate-*.json`), which predates `txoe` and has no such
port. These tests are RTL-only until the layout is regenerated with the
port; the shared driver and RX helpers are imported, not copied.

This file is *input* to `klt functional-verification` (see
`request-usb-utmi-txoe.json`), not a pytest module.
"""

import cocotb
from cocotb.triggers import FallingEdge, RisingEdge

import test_usb_utmi_phy as base
from test_usb_utmi_phy import (
    IDLE_LEAD,
    IDLE_TAIL,
    J_CELL,
    _good_body,
    _reset,
    _rx_frame_cells,
    _start_clock,
)


async def _drive_packets(dut, packets, cycles, loopback=True):
    """`base._drive_packets` plus a per-clock `txoe` trace, sampled at the
    same falling edge as the matching `dpdm` entry."""
    txoe = []

    async def monitor():
        for _ in range(cycles):
            await FallingEdge(dut.clk)
            txoe.append(int(dut.txoe.value))

    mon = cocotb.start_soon(monitor())
    result = await base._drive_packets(dut, packets, cycles, loopback=loopback)
    await mon
    assert len(txoe) == len(result["dpdm"])
    result["txoe"] = txoe
    return result

def _txoe_runs(txoe):
    """(start, end_exclusive) index pairs of each contiguous high run."""
    runs = []
    start = None
    for i, v in enumerate(txoe):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(txoe)))
    return runs


def _assert_txoe_covers_one_packet(dpdm, txoe, run, what):
    """txoe's high run `run` spans exactly from the first non-idle wire
    sample through the final J of the SE0,SE0,J tail."""
    s, e = run
    # Rises with the first SYNC bit: the first K is on the wire in the
    # very sample txoe first reads high.
    assert dpdm[s] == (0, 1), f"{what}: first txoe sample is not SYNC bit 0 (K): {dpdm[s]}"
    assert s == 0 or dpdm[s - 1] == (1, 0), f"{what}: wire not idle J before txoe"
    # High through the whole EOP tail, falling after the J bit.
    assert dpdm[e - 3:e] == [(0, 0), (0, 0), (1, 0)], (
        f"{what}: txoe did not stay high through SE0,SE0,J: {dpdm[e - 3:e]}"
    )
    assert e == len(txoe) or dpdm[e] == (1, 0), f"{what}: wire not idle J after txoe falls"


@cocotb.test()
async def test_txoe_idle_and_rx_low(dut):
    """txoe is low in idle and throughout an RX frame (driver stays high-Z
    while receiving)."""
    await _start_clock(dut)
    await _reset(dut)
    assert int(dut.txoe.value) == 0, "txoe high after reset"
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    assert int(dut.txoe.value) == 0, "txoe high in idle"

    cells = ([J_CELL] * IDLE_LEAD + _rx_frame_cells(_good_body([0xA5, 0xFC]))
             + [J_CELL] * IDLE_TAIL)
    seen = []
    for dp, dm in cells:
        dut.rxdp.value = dp
        dut.rxdm.value = dm
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)
        seen.append((int(dut.RxActive.value), int(dut.txoe.value)))
    assert any(a for a, _ in seen), "RX frame never became active"
    assert not any(t for _, t in seen), "txoe asserted during RX"


@cocotb.test()
async def test_txoe_spans_packet_sync_through_final_j(dut):
    """txoe rises with the first SYNC bit, stays high across data and the
    SE0,SE0,J tail, and falls right after the J bit."""
    await _start_clock(dut)
    await _reset(dut)

    result = await _drive_packets(dut, [[0x01, 0xA5]], cycles=80)
    runs = _txoe_runs(result["txoe"])
    assert len(runs) == 1, f"expected one txoe pulse, got {runs}"
    _assert_txoe_covers_one_packet(result["dpdm"], result["txoe"], runs[0], "data packet")
    # Length: 8 SYNC + 16 data bits (+ stuffing, flush, hold) + 3 EOP.
    assert runs[0][1] - runs[0][0] >= 8 + 16 + 3
    assert result["txoe"][-1] == 0, "txoe still high after the packet"


@cocotb.test()
async def test_txoe_high_through_flush_path(dut):
    """Trailing run of six 1s takes the TX_FLUSH path; txoe is continuous
    (one pulse) across it and still ends right after the EOP J."""
    await _start_clock(dut)
    await _reset(dut)

    result = await _drive_packets(dut, [[0x00, 0xFC]], cycles=80)
    runs = _txoe_runs(result["txoe"])
    assert len(runs) == 1, f"txoe glitched low mid-packet: {runs}"
    _assert_txoe_covers_one_packet(result["dpdm"], result["txoe"], runs[0], "flush packet")
    # The flush adds one stuffed bit: 8 SYNC + 16 data + 1 stuff + 3 EOP at
    # minimum (plus the wrapper's HOLD bit-time).
    assert runs[0][1] - runs[0][0] >= 8 + 16 + 1 + 3


@cocotb.test()
async def test_txoe_raw_mode(dut):
    """Raw/transparent mode (OpMode 2'b10) frames txoe identically."""
    await _start_clock(dut)
    await _reset(dut)
    dut.OpMode.value = 0b10

    result = await _drive_packets(dut, [[0b1010_0110]], cycles=60, loopback=False)
    runs = _txoe_runs(result["txoe"])
    assert len(runs) == 1, f"expected one txoe pulse in raw mode, got {runs}"
    _assert_txoe_covers_one_packet(result["dpdm"], result["txoe"], runs[0], "raw packet")
    assert runs[0][1] - runs[0][0] >= 8 + 8 + 3


@cocotb.test()
async def test_txoe_back_to_back_packets(dut):
    """Back to back packets: the driver releases for at least one clock
    between packets (the second packet starts only from TX_IDLE, which
    this test's driver waits for), so txoe pulses once per packet."""
    await _start_clock(dut)
    await _reset(dut)

    result = await _drive_packets(dut, [[0x01, 0x02], [0xAA, 0xBB, 0xCC]], cycles=160)
    runs = _txoe_runs(result["txoe"])
    assert len(runs) == 2, f"expected one txoe pulse per packet, got {runs}"
    for n, run in enumerate(runs):
        _assert_txoe_covers_one_packet(result["dpdm"], result["txoe"], run, f"packet {n}")
    assert runs[1][0] > runs[0][1], "txoe pulses not separated by a low gap"
