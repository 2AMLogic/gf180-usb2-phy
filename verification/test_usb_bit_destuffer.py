"""cocotb testbench for `rtl/usb_bit_destuffer.v`.

Checks the RX-side bit destuffer bit-exactly against
`usb_bit_model.bit_destuff`, including the bit-stuff error case
(`spec/usb2-device-phy.md` #2: at most six consecutive 1s may legally
appear, so a seventh is a malformed stream).

Sampling discipline follows `test_harness_counter.py`: drive on a
`FallingEdge`, read on the `FallingEdge` after the `RisingEdge` under test.

This file is *input* to `klt functional-verification` (see
`request-usb-bit-destuffer.json`), not a pytest module.
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

from usb_bit_model import bit_destuff, bit_stuff

# 12 MHz per spec/usb2-device-phy.md #3; see test_usb_nrzi_encoder.py for
# why 83334 ps rather than 83333 ps.
CLK_PERIOD_PS = 83334


async def _start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_PS, unit="ps").start())


async def _reset(dut):
    dut.rst_n.value = 0
    dut.init.value = 0
    dut.in_valid.value = 0
    dut.in_bit.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)


async def _step(dut, valid, bit=0, init=0):
    """Drive one clock; return `(out_valid, out_bit, stuff_err)`."""
    dut.init.value = init
    dut.in_valid.value = valid
    dut.in_bit.value = bit
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    return (
        int(dut.out_valid.value),
        int(dut.out_bit.value),
        int(dut.stuff_err.value),
    )


async def _destuff(dut, bits):
    """Feed `bits`; return `(data_bits, error_positions)`.

    `error_positions` indexes into `bits`, matching what
    `usb_bit_model.bit_destuff` reports: the destuffer has one clock of
    latency and consumes exactly one bit per clock, so the pulse observed
    after driving bit `i` belongs to bit `i`.
    """
    data = []
    errors = []
    for index, bit in enumerate(bits):
        valid, out_bit, err = await _step(dut, valid=1, bit=bit)
        if valid:
            data.append(out_bit)
        if err:
            errors.append(index)
        assert not (valid and err), "a removed bit was also emitted"
    return data, errors


@cocotb.test()
async def test_all_zeros_pass_through(dut):
    """A run of 0s is never a stuff position (edge case: no destuffing)."""
    await _start_clock(dut)
    await _reset(dut)

    bits = [0] * 32
    data, errors = await _destuff(dut, bits)
    assert data == bits, f"0s were altered: {data}"
    assert errors == [], "a 0 run raised a stuff error"
    assert (data, errors) == bit_destuff(bits), "DUT disagrees with the model"


@cocotb.test()
async def test_removes_the_stuffed_zero(dut):
    """A stuffed stream comes back out as the original data."""
    await _start_clock(dut)
    await _reset(dut)

    original = [1] * 6 + [0, 1, 1]
    stuffed, _flags = bit_stuff(original)
    assert len(stuffed) == len(original) + 1, "fixture did not exercise stuffing"

    data, errors = await _destuff(dut, stuffed)
    assert data == original, f"destuffing did not recover the input: {data}"
    assert errors == [], "a well-formed stream raised a stuff error"


@cocotb.test()
async def test_seven_ones_raise_a_stuff_error(dut):
    """Seven consecutive 1s is a bit-stuff error (edge case: injection)."""
    await _start_clock(dut)
    await _reset(dut)

    bits = [1] * 7
    data, errors = await _destuff(dut, bits)
    assert errors == [6], f"seven 1s did not flag exactly one error: {errors}"
    assert data == [1] * 6, f"the offending bit was not removed: {data}"
    assert (data, errors) == bit_destuff(bits), "DUT disagrees with the model"


@cocotb.test()
async def test_stuff_error_is_a_single_clock_pulse(dut):
    """`stuff_err` pulses for one clock and then clears itself."""
    await _start_clock(dut)
    await _reset(dut)

    for _ in range(6):
        _valid, _bit, err = await _step(dut, valid=1, bit=1)
        assert err == 0, "stuff_err asserted before the seventh 1"

    _valid, _bit, err = await _step(dut, valid=1, bit=1)
    assert err == 1, "stuff_err did not assert on the seventh consecutive 1"

    for _ in range(4):
        _valid, _bit, err = await _step(dut, valid=1, bit=0)
        assert err == 0, "stuff_err stayed high past its clock"


@cocotb.test()
async def test_long_run_of_ones_errors_every_seventh_bit(dut):
    """An unbroken 1 run keeps flagging, once per stuff position."""
    await _start_clock(dut)
    await _reset(dut)

    bits = [1] * 21
    data, errors = await _destuff(dut, bits)
    assert (data, errors) == bit_destuff(bits), "DUT disagrees with the model"
    assert errors == [6, 13, 20], f"unexpected error positions: {errors}"


@cocotb.test()
async def test_random_stream_round_trips(dut):
    """512 random bits, model-stuffed, must come back out unchanged."""
    await _start_clock(dut)
    await _reset(dut)

    rng = random.Random(20260819)
    # Biased toward 1s so the stream actually contains stuffed bits.
    original = [1 if rng.random() < 0.8 else 0 for _ in range(512)]
    stuffed, flags = bit_stuff(original)
    assert any(flags), "the biased stream produced no stuffing at all"

    data, errors = await _destuff(dut, stuffed)
    assert (data, errors) == bit_destuff(stuffed), "DUT disagrees with the model"
    assert data == original, "destuffing did not recover the input"
    assert errors == [], "a well-formed stream raised a stuff error"


@cocotb.test()
async def test_gap_preserves_the_run(dut):
    """A gap in in_valid holds the run count instead of clearing it."""
    await _start_clock(dut)
    await _reset(dut)

    data, errors = await _destuff(dut, [1] * 3)
    for _ in range(5):
        valid, _bit, err = await _step(dut, valid=0, bit=1)
        assert valid == 0, "out_valid asserted during a gap"
        assert err == 0, "stuff_err asserted during a gap"

    more, more_errors = await _destuff(dut, [1] * 4)
    data += more
    errors += [index + 3 for index in more_errors]

    # Six 1s spanning the gap; the seventh is a stuff position and is a 1.
    assert data == [1] * 6, f"run count did not survive the gap: {data}"
    assert errors == [6], f"unexpected error positions: {errors}"


@cocotb.test()
async def test_init_clears_the_run(dut):
    """`init` clears the run count at a packet boundary."""
    await _start_clock(dut)
    await _reset(dut)

    await _destuff(dut, [1] * 6)
    valid, _bit, err = await _step(dut, valid=0, init=1)
    assert valid == 0, "out_valid asserted while init was high"
    assert err == 0, "stuff_err asserted while init was high"

    # With the run cleared, six more 1s are accepted without an error.
    data, errors = await _destuff(dut, [1] * 6)
    assert data == [1] * 6, f"init did not clear the run: {data}"
    assert errors == [], "init did not clear the run"
