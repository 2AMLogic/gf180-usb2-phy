"""cocotb testbench for `rtl/usb_bit_stuffer.v`.

Checks the TX-side bit stuffer bit-exactly against `usb_bit_model.bit_stuff`
-- an independent Python model written from the prose rule in
`spec/usb2-device-phy.md` #2 ("after every six consecutive 1s") -- per the
bit-exact signoff bar in spec #11.

Sampling discipline follows `test_harness_counter.py`: drive on a
`FallingEdge`, read on the `FallingEdge` after the `RisingEdge` under test.
`in_ready` is combinational from internal state only, so it is stable at the
falling edge and is sampled there, before the transfer it governs.

This file is *input* to `klt functional-verification` (see
`request-usb-bit-stuffer.json`), not a pytest module.
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

from usb_bit_model import STUFF_AFTER, bit_stuff

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
    """Drive one clock; return `(in_ready, out_valid, out_bit, out_stuffed)`.

    `in_ready` is the value seen *before* the rising edge -- i.e. whether
    the bit being presented was accepted on that edge.
    """
    dut.init.value = init
    dut.in_valid.value = valid
    dut.in_bit.value = bit
    ready = int(dut.in_ready.value)
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    return (
        ready,
        int(dut.out_valid.value),
        int(dut.out_bit.value),
        int(dut.out_stuffed.value),
    )


async def _stuff(dut, bits, drain=4):
    """Feed `bits` honoring `in_ready`; return `(out_bits, stuffed_flags)`."""
    out_bits = []
    flags = []
    index = 0
    # Guard against a livelock in the handshake rather than hanging the sim.
    budget = 4 * len(bits) + 16
    while index < len(bits):
        budget -= 1
        assert budget > 0, "in_ready never came back high -- handshake stalled"
        ready, valid, bit, stuffed = await _step(dut, valid=1, bit=bits[index])
        if valid:
            out_bits.append(bit)
            flags.append(bool(stuffed))
        if ready:
            index += 1
    for _ in range(drain):
        _ready, valid, bit, stuffed = await _step(dut, valid=0)
        if valid:
            out_bits.append(bit)
            flags.append(bool(stuffed))
    return out_bits, flags


@cocotb.test()
async def test_all_zeros_are_never_stuffed(dut):
    """A run of 0s passes through untouched (edge case: no stuffing)."""
    await _start_clock(dut)
    await _reset(dut)

    bits = [0] * 32
    out, flags = await _stuff(dut, bits)
    assert out == bits, f"0s were altered: {out}"
    assert not any(flags), "a 0 run should never insert a bit"
    assert (out, flags) == bit_stuff(bits), "DUT disagrees with the model"


@cocotb.test()
async def test_all_ones_stuff_maximally(dut):
    """A run of 1s stuffs a 0 after every six (edge case: max density)."""
    await _start_clock(dut)
    await _reset(dut)

    bits = [1] * 49
    out, flags = await _stuff(dut, bits)
    assert (out, flags) == bit_stuff(bits), f"DUT disagrees with the model: {out}"

    # Independently of the model: never more than six 1s in a row on the
    # wire, which is the whole point of the rule.
    run = 0
    longest = 0
    for bit in out:
        run = run + 1 if bit == 1 else 0
        longest = max(longest, run)
    assert longest == STUFF_AFTER, f"longest run of 1s emitted was {longest}"


@cocotb.test()
async def test_six_ones_then_zero_still_stuffs(dut):
    """The inserted 0 is positional: it goes in even before a data 0."""
    await _start_clock(dut)
    await _reset(dut)

    out, flags = await _stuff(dut, [1] * 6 + [0])
    assert out == [1, 1, 1, 1, 1, 1, 0, 0], f"unexpected stuffed stream: {out}"
    assert flags == [False] * 6 + [True, False], f"unexpected stuff flags: {flags}"


@cocotb.test()
async def test_trailing_run_of_six_is_not_stuffed(dut):
    """A stream ending on exactly six 1s gets no trailing stuffed bit.

    The stuffed 0 precedes the seventh bit; with no seventh bit there is
    nothing to precede. `usb_bit_destuffer` mirrors the same boundary, so
    the pair stays lossless.
    """
    await _start_clock(dut)
    await _reset(dut)

    out, flags = await _stuff(dut, [1] * 6)
    assert out == [1] * 6, f"a trailing six-1 run was altered: {out}"
    assert not any(flags), "a trailing six-1 run should not stuff"


@cocotb.test()
async def test_random_stream_matches_model(dut):
    """512 random bits, bit-exact against the model, flags included."""
    await _start_clock(dut)
    await _reset(dut)

    rng = random.Random(20260818)
    # Bias toward 1s so stuffing fires often -- a uniform stream almost
    # never produces a six-long run of 1s.
    bits = [1 if rng.random() < 0.8 else 0 for _ in range(512)]

    out, flags = await _stuff(dut, bits)
    assert (out, flags) == bit_stuff(bits), "DUT disagrees with the model"
    assert any(flags), "the biased stream produced no stuffing at all"


@cocotb.test()
async def test_in_ready_falls_only_for_the_stuffed_bit(dut):
    """`in_ready` deasserts for exactly one clock, per inserted bit."""
    await _start_clock(dut)
    await _reset(dut)

    stalls = 0
    stuffs = 0
    previous_ready = 1
    for _ in range(40):
        ready, valid, _bit, stuffed = await _step(dut, valid=1, bit=1)
        if not ready:
            stalls += 1
            assert previous_ready == 1, "in_ready stayed low for two clocks"
        if valid and stuffed:
            stuffs += 1
        previous_ready = ready

    assert stalls > 0, "a 40-bit run of 1s never stalled the source"
    assert stalls == stuffs, f"{stalls} stalls but {stuffs} stuffed bits"


@cocotb.test()
async def test_gap_preserves_the_run(dut):
    """A gap in in_valid holds the run count instead of clearing it."""
    await _start_clock(dut)
    await _reset(dut)

    out, flags = await _stuff(dut, [1] * 3, drain=0)
    for _ in range(5):
        _ready, valid, _bit, _stuffed = await _step(dut, valid=0)
        assert valid == 0, "out_valid asserted during a gap"

    more, more_flags = await _stuff(dut, [1] * 4)
    out += more
    flags += more_flags

    # Six 1s spanning the gap, then the seventh bit forces a stuffed 0.
    assert out == [1] * 6 + [0, 1], f"run count did not survive the gap: {out}"
    assert flags == [False] * 6 + [True, False], f"unexpected stuff flags: {flags}"


@cocotb.test()
async def test_init_clears_the_run(dut):
    """`init` clears the run count at a packet boundary."""
    await _start_clock(dut)
    await _reset(dut)

    await _stuff(dut, [1] * 6, drain=0)
    _ready, valid, _bit, _stuffed = await _step(dut, valid=0, init=1)
    assert valid == 0, "out_valid asserted while init was high"

    # With the run cleared, six more 1s pass through unstuffed.
    out, flags = await _stuff(dut, [1] * 6)
    assert out == [1] * 6, f"init did not clear the run: {out}"
    assert not any(flags), "init did not clear the run"
