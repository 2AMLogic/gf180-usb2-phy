"""cocotb testbench for `rtl/usb_line_state_decode.v`.

Directed checks of the four `LineState[1:0]` encodings this module defines
from the two single-ended receiver outputs (`rxdp`/`rxdm`), per
`spec/usb2-device-phy.md` #3/#4 -- the floor #11 sets for this block's
digital logic.

Sampling discipline follows `test_harness_counter.py`: inputs are driven on
a `FallingEdge` and outputs are read on the `FallingEdge` after the
`RisingEdge` under test.

This file is *input* to `klt functional-verification` (see
`request-usb-line-state-decode.json`), not a pytest module.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

# spec/usb2-device-phy.md #3 ratifies a 12 MHz interface clock. See
# test_usb_nrzi_encoder.py for why 83334 ps rather than 83333 ps.
CLK_PERIOD_PS = 83334

LS_SE0 = 0b00
LS_J = 0b01
LS_K = 0b10
LS_SE1 = 0b11


async def _start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_PS, unit="ps").start())


async def _reset(dut, rxdp=1, rxdm=0):
    dut.rst_n.value = 0
    dut.rxdp.value = rxdp
    dut.rxdm.value = rxdm
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)


async def _drive(dut, rxdp, rxdm):
    dut.rxdp.value = rxdp
    dut.rxdm.value = rxdm
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    return int(dut.line_state.value)


@cocotb.test()
async def test_reset_defaults_to_j(dut):
    """Out of reset LineState reads J, matching every other module's idle."""
    await _start_clock(dut)
    await _reset(dut)
    assert int(dut.line_state.value) == LS_J, "reset default was not J"


@cocotb.test()
async def test_j_state(dut):
    """D+ high, D- low -> J (idle, FS device)."""
    await _start_clock(dut)
    await _reset(dut, rxdp=0, rxdm=0)
    state = await _drive(dut, rxdp=1, rxdm=0)
    assert state == LS_J, f"expected J (0b01), got {state:#04b}"


@cocotb.test()
async def test_k_state(dut):
    """D+ low, D- high -> K."""
    await _start_clock(dut)
    await _reset(dut)
    state = await _drive(dut, rxdp=0, rxdm=1)
    assert state == LS_K, f"expected K (0b10), got {state:#04b}"


@cocotb.test()
async def test_se0_state(dut):
    """Both low -> SE0 (EOP / reset candidate, spec #4)."""
    await _start_clock(dut)
    await _reset(dut)
    state = await _drive(dut, rxdp=0, rxdm=0)
    assert state == LS_SE0, f"expected SE0 (0b00), got {state:#04b}"


@cocotb.test()
async def test_se1_state(dut):
    """Both high -> SE1 (illegal, never produced in normal operation)."""
    await _start_clock(dut)
    await _reset(dut)
    state = await _drive(dut, rxdp=1, rxdm=1)
    assert state == LS_SE1, f"expected SE1 (0b11), got {state:#04b}"


@cocotb.test()
async def test_tracks_toggling_inputs(dut):
    """A sequence of all four states is decoded correctly, one clock late."""
    await _start_clock(dut)
    await _reset(dut)

    sequence = [(1, 0, LS_J), (0, 1, LS_K), (0, 0, LS_SE0), (1, 1, LS_SE1),
                (1, 0, LS_J), (0, 1, LS_K)]
    for rxdp, rxdm, expected in sequence:
        state = await _drive(dut, rxdp, rxdm)
        assert state == expected, (
            f"rxdp={rxdp} rxdm={rxdm}: expected {expected:#04b}, got {state:#04b}"
        )
