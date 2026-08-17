"""cocotb testbench for `rtl/usb_eop_detector.v`.

Checks the SE0 hold-duration disambiguation `spec/usb2-device-phy.md` #4
requires: SE0 held for 2 bit times is EOP, SE0 held >= 2.5us (30 clocks at
the ratified 12.000 MHz interface clock, spec #3) is a reset condition.
Both boundaries are exercised exactly at the edge, per this issue's own
test plan.

Sampling discipline follows `test_harness_counter.py`: inputs are driven on
a `FallingEdge` and outputs are read on the `FallingEdge` after the
`RisingEdge` under test.

This file is *input* to `klt functional-verification` (see
`request-usb-eop-detector.json`), not a pytest module.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

# spec/usb2-device-phy.md #3 ratifies a 12 MHz interface clock. See
# test_usb_nrzi_encoder.py for why 83334 ps rather than 83333 ps.
CLK_PERIOD_PS = 83334

LS_SE0 = 0b00
LS_J = 0b01

EOP_CYCLES = 2
RESET_CYCLES = 30


async def _start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_PS, unit="ps").start())


async def _reset(dut):
    dut.rst_n.value = 0
    dut.line_state.value = LS_J
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)


async def _drive(dut, line_state):
    dut.line_state.value = line_state
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    return int(dut.eop.value), int(dut.bus_reset.value)


async def _hold_se0(dut, cycles):
    """Drive SE0 for `cycles` clocks; return the list of (eop, bus_reset)."""
    return [await _drive(dut, LS_SE0) for _ in range(cycles)]


@cocotb.test()
async def test_reset_defaults(dut):
    await _start_clock(dut)
    await _reset(dut)
    assert int(dut.eop.value) == 0
    assert int(dut.bus_reset.value) == 0


@cocotb.test()
async def test_one_bit_time_of_se0_is_not_eop(dut):
    """SE0 for 1 clock, then back to J: below the 2-bit-time threshold."""
    await _start_clock(dut)
    await _reset(dut)

    samples = await _hold_se0(dut, 1)
    assert samples == [(0, 0)], f"unexpected assertion on a single SE0 clock: {samples}"

    eop, bus_reset = await _drive(dut, LS_J)
    assert (eop, bus_reset) == (0, 0), "eop/bus_reset fired for a 1-clock SE0 glitch"


@cocotb.test()
async def test_exactly_two_bit_times_of_se0_is_eop(dut):
    """SE0 held for exactly EOP_CYCLES clocks pulses `eop` once, on the last one."""
    await _start_clock(dut)
    await _reset(dut)

    samples = await _hold_se0(dut, EOP_CYCLES)
    eops = [s[0] for s in samples]
    assert eops == [0, 1], f"eop did not pulse on the {EOP_CYCLES}th SE0 clock: {eops}"
    assert all(s[1] == 0 for s in samples), "bus_reset fired well before threshold"

    # The pulse is exactly one clock wide, and does not re-fire while SE0
    # continues beyond the boundary.
    eop, _ = await _drive(dut, LS_SE0)
    assert eop == 0, "eop re-fired on a later SE0 clock"


@cocotb.test()
async def test_twenty_nine_clocks_of_se0_never_asserts_bus_reset(dut):
    """One clock short of the reset threshold: bus_reset must not fire."""
    await _start_clock(dut)
    await _reset(dut)

    samples = await _hold_se0(dut, RESET_CYCLES - 1)
    assert all(s[1] == 0 for s in samples), (
        f"bus_reset fired before the {RESET_CYCLES}-clock threshold: {samples}"
    )

    # Returning to J now (a legitimately long EOP hold, still not a reset)
    # must not leave bus_reset stuck.
    _, bus_reset = await _drive(dut, LS_J)
    assert bus_reset == 0, "bus_reset asserted despite never reaching threshold"


@cocotb.test()
async def test_exactly_thirty_clocks_of_se0_asserts_bus_reset(dut):
    """SE0 held for exactly RESET_CYCLES (2.5us) clocks asserts bus_reset."""
    await _start_clock(dut)
    await _reset(dut)

    samples = await _hold_se0(dut, RESET_CYCLES)
    bus_resets = [s[1] for s in samples]
    assert bus_resets == [0] * (RESET_CYCLES - 1) + [1], (
        f"bus_reset did not assert exactly on the {RESET_CYCLES}th SE0 clock: "
        f"{bus_resets}"
    )

    # Level, not a pulse: stays asserted while SE0 continues.
    for _ in range(5):
        _, bus_reset = await _drive(dut, LS_SE0)
        assert bus_reset == 1, "bus_reset dropped while SE0 was still held"

    # Clears the clock after the line leaves SE0.
    _, bus_reset = await _drive(dut, LS_J)
    assert bus_reset == 0, "bus_reset did not clear when SE0 ended"


@cocotb.test()
async def test_eop_and_bus_reset_both_derive_from_one_hold(dut):
    """A long SE0 hold fires eop early (2 clocks) and bus_reset later (30)."""
    await _start_clock(dut)
    await _reset(dut)

    samples = await _hold_se0(dut, RESET_CYCLES)
    eop_cycles = [i + 1 for i, s in enumerate(samples) if s[0]]
    reset_cycles = [i + 1 for i, s in enumerate(samples) if s[1]]
    assert eop_cycles == [EOP_CYCLES], f"eop fired on the wrong clock(s): {eop_cycles}"
    assert reset_cycles == list(range(RESET_CYCLES, RESET_CYCLES + 1)), (
        f"bus_reset fired on the wrong clock(s): {reset_cycles}"
    )
