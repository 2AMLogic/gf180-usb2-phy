"""cocotb testbench for `harness_counter.v` -- the throwaway smoke-test
vehicle that proves the cocotb + Icarus + klt digital harness bootstrapped
by issue #7 elaborates, simulates, and reports a real result end-to-end.

`harness_counter` has zero USB semantics -- no NRZI, no bit stuffing, no
SYNC/EOP -- see CLAUDE.md's scope-discipline rule and
spec/usb2-device-phy.md. It is a plain N-bit up counter with a synchronous,
active-low reset and a count-enable, nothing more.

Inputs are driven on `FallingEdge` and outputs are sampled on the
`FallingEdge` that follows the `RisingEdge` under test (i.e. half a clock
period after the edge whose effect is being checked). This is a
deliberate choice, not a style preference: `posedge clk` in the DUT's
`always` block and cocotb's own `RisingEdge` callback are two independent
processes sensitive to the same simulation event, and the Verilog LRM does
not guarantee their relative execution order -- reading a signal
immediately after `await RisingEdge(dut.clk)` returns can race the DUT's
own non-blocking update and observe the *pre*-edge value. Waiting out the
remaining half period before driving or sampling sidesteps that race
entirely, at the cost of the extra `FallingEdge` bookkeeping below.

This file is *input* to `klt functional-verification` (the testbench module
named by `request.testbench.module`, see `request-harness-counter.json`),
not a pytest module -- pytest never collects it, since it takes a
cocotb-injected `dut` argument and only runs inside a simulator process.
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge


def _width(dut):
    """Operand width of this elaboration, read from the count port."""
    return len(dut.count)


async def _start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())


async def _reset(dut):
    """Hold reset for a few cycles, release it, and settle on a
    FallingEdge so the caller can safely drive/sample from there."""
    dut.rst_n.value = 0
    dut.en.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)


async def _step(dut, en):
    """Drive `en` for the next RisingEdge and return `count` sampled at
    the following FallingEdge, once the synchronous update has settled."""
    dut.en.value = en
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    return int(dut.count.value)


@cocotb.test()
async def test_reset_holds_zero(dut):
    """Asserting rst_n low drives count to 0, even with en held high."""
    await _start_clock(dut)
    dut.rst_n.value = 0
    dut.en.value = 1
    await ClockCycles(dut.clk, 5)
    await FallingEdge(dut.clk)
    assert int(dut.count.value) == 0, "count did not reset to 0"


@cocotb.test()
async def test_disabled_holds_value(dut):
    """en=0 holds the current count steady across clock edges."""
    await _start_clock(dut)
    await _reset(dut)
    assert int(dut.count.value) == 0, "count did not settle to 0 after reset"

    held = None
    for _ in range(4):
        held = await _step(dut, en=1)
    assert held == 4, f"count after 4 enabled cycles: got {held}, want 4"

    for _ in range(5):
        got = await _step(dut, en=0)
        assert got == held, "count changed while en was low"


@cocotb.test()
async def test_counts_and_wraps(dut):
    """Randomized cross-check against a plain Python model, including
    wraparound at 2**WIDTH -- fixed seed for reproducibility."""
    await _start_clock(dut)
    width = _width(dut)
    modulus = 1 << width

    await _reset(dut)

    expected = 0
    rng = random.Random(0)
    for _ in range(500):
        enable = rng.choice([0, 1])
        got = await _step(dut, en=enable)
        if enable:
            expected = (expected + 1) % modulus
        assert got == expected, f"count mismatch: got {got}, want {expected}"
