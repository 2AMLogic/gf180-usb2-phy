"""cocotb testbench for `rtl/usb_sync_detector.v`.

Checks SYNC-field pattern matching against the NRZI-decoded bit stream
(`data_valid`/`data_bit`, matching `usb_nrzi_decoder`'s output ports),
per `spec/usb2-device-phy.md` #2/#11: SYNC is the fixed pre-stuff byte
8'h80, transmission order 0,0,0,0,0,0,0,1 (see `usb_sync_detector.v`'s own
header for the derivation).

Sampling discipline follows `test_harness_counter.py`: inputs are driven on
a `FallingEdge` and outputs are read on the `FallingEdge` after the
`RisingEdge` under test.

This file is *input* to `klt functional-verification` (see
`request-usb-sync-detector.json`), not a pytest module.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

# spec/usb2-device-phy.md #3 ratifies a 12 MHz interface clock. See
# test_usb_nrzi_encoder.py for why 83334 ps rather than 83333 ps.
CLK_PERIOD_PS = 83334

SYNC_BITS = [0, 0, 0, 0, 0, 0, 0, 1]


async def _start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_PS, unit="ps").start())


async def _reset(dut):
    dut.rst_n.value = 0
    dut.enable.value = 1
    dut.data_valid.value = 0
    dut.data_bit.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)


async def _step(dut, valid, bit=0, enable=1):
    dut.enable.value = enable
    dut.data_valid.value = valid
    dut.data_bit.value = bit
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    return int(dut.sync_valid.value)


async def _feed(dut, bits, enable=1):
    """Drive `bits` (each with data_valid=1); return the sync_valid samples."""
    return [await _step(dut, valid=1, bit=b, enable=enable) for b in bits]


@cocotb.test()
async def test_reset_holds_no_pulse(dut):
    await _start_clock(dut)
    await _reset(dut)
    assert int(dut.sync_valid.value) == 0, "sync_valid asserted out of reset"


@cocotb.test()
async def test_exact_sync_pattern_pulses_on_eighth_bit(dut):
    """SYNC_BITS fed back-to-back pulses sync_valid on exactly the 8th clock."""
    await _start_clock(dut)
    await _reset(dut)

    pulses = await _feed(dut, SYNC_BITS)
    assert pulses == [0, 0, 0, 0, 0, 0, 0, 1], f"unexpected pulse pattern: {pulses}"


@cocotb.test()
async def test_all_ones_never_matches(dut):
    """A run of 1s (idle-J's own decoded shape) never looks like SYNC."""
    await _start_clock(dut)
    await _reset(dut)

    pulses = await _feed(dut, [1] * 64)
    assert not any(pulses), "sync_valid fired against a stream of all 1s"


@cocotb.test()
async def test_corrupted_bit_never_matches(dut):
    """A single flipped bit inside an otherwise-correct SYNC breaks the match."""
    await _start_clock(dut)
    await _reset(dut)

    corrupted = list(SYNC_BITS)
    corrupted[5] = 1 - corrupted[5]  # flip a bit that would otherwise be a 0
    pulses = await _feed(dut, corrupted)
    assert not any(pulses), f"sync_valid fired against a corrupted pattern: {pulses}"


@cocotb.test()
async def test_disabled_never_matches(dut):
    """`enable` low holds the match state at 0 even against a perfect pattern."""
    await _start_clock(dut)
    await _reset(dut)

    pulses = await _feed(dut, SYNC_BITS, enable=0)
    assert not any(pulses), "sync_valid fired while disabled"

    # Re-enabling starts a fresh search rather than resuming a stale partial
    # match: this second, correctly-enabled attempt still matches cleanly.
    pulses = await _feed(dut, SYNC_BITS, enable=1)
    assert pulses == [0, 0, 0, 0, 0, 0, 0, 1], f"unexpected pulse pattern: {pulses}"


@cocotb.test()
async def test_data_valid_gap_holds_match_state(dut):
    """A gap in `data_valid` mid-pattern does not reset the partial match."""
    await _start_clock(dut)
    await _reset(dut)

    pulses = await _feed(dut, SYNC_BITS[:4])
    assert not any(pulses), "premature sync_valid before the pattern completed"

    for _ in range(5):
        pulse = await _step(dut, valid=0)
        assert pulse == 0, "sync_valid asserted during a data_valid gap"

    pulses = await _feed(dut, SYNC_BITS[4:])
    assert pulses == [0, 0, 0, 1], f"match did not resume correctly: {pulses}"


@cocotb.test()
async def test_mismatch_then_restart_matches_on_second_attempt(dut):
    """A broken first attempt does not prevent a clean second attempt."""
    await _start_clock(dut)
    await _reset(dut)

    # Three correct bits (0,0,0), then a bad one (1 instead of 0) that
    # itself is not SYNC's first bit (0), so the search must restart clean.
    broken = [0, 0, 0, 1]
    pulses = await _feed(dut, broken)
    assert not any(pulses), f"unexpected pulse during broken attempt: {pulses}"

    pulses = await _feed(dut, SYNC_BITS)
    assert pulses == [0, 0, 0, 0, 0, 0, 0, 1], (
        f"second, clean attempt did not match: {pulses}"
    )
