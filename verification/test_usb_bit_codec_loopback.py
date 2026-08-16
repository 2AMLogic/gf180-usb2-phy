"""cocotb testbench for `verification/tb_usb_bit_codec_loopback.v`.

Where the four per-module testbenches check each block against a Python
model, this one closes the loop in RTL: the TX path (`usb_bit_stuffer` ->
`usb_nrzi_encoder`) drives the RX path (`usb_nrzi_decoder` ->
`usb_bit_destuffer`) through a wire, and the claim is that the bit stream
comes back out unchanged. That is the round-trip half of this issue's test
plan, made against real hardware on both ends rather than a model on one.

The harness is testbench scaffolding, not PHY RTL, and deliberately has no
SYNC, no EOP, no line-state decode and no UTMI ports -- see its own header.

Sampling discipline follows `test_harness_counter.py`: drive on a
`FallingEdge`, read on the `FallingEdge` after the `RisingEdge` under test.

This file is *input* to `klt functional-verification` (see
`request-usb-bit-codec-loopback.json`), not a pytest module.
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

from usb_bit_model import bit_stuff, nrzi_encode

# 12 MHz per spec/usb2-device-phy.md #3; see test_usb_nrzi_encoder.py for
# why 83334 ps rather than 83333 ps.
CLK_PERIOD_PS = 83334

# Stuffer -> encoder -> decoder -> destuffer, one registered stage each.
PIPELINE_DEPTH = 4


async def _start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_PS, unit="ps").start())


async def _reset(dut):
    dut.rst_n.value = 0
    dut.init.value = 0
    dut.tx_valid.value = 0
    dut.tx_bit.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)


async def _step(dut, valid, bit=0, init=0):
    dut.init.value = init
    dut.tx_valid.value = valid
    dut.tx_bit.value = bit
    ready = int(dut.tx_ready.value)
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    return {
        "ready": ready,
        "line_valid": int(dut.line_valid.value),
        "line_bit": int(dut.line_bit.value),
        "tx_stuffed": int(dut.tx_stuffed.value),
        "rx_valid": int(dut.rx_valid.value),
        "rx_bit": int(dut.rx_bit.value),
        "rx_stuff_err": int(dut.rx_stuff_err.value),
    }


async def _loopback(dut, bits):
    """Send `bits` through the whole path; return what came back.

    Returns `(line_bits, stuffed_count, rx_bits, error_count)`.
    """
    line = []
    stuffed = 0
    rx_bits = []
    errors = 0

    def observe(sample):
        nonlocal stuffed, errors
        if sample["line_valid"]:
            line.append(sample["line_bit"])
        if sample["tx_stuffed"]:
            stuffed += 1
        if sample["rx_valid"]:
            rx_bits.append(sample["rx_bit"])
        if sample["rx_stuff_err"]:
            errors += 1

    index = 0
    budget = 4 * len(bits) + 32
    while index < len(bits):
        budget -= 1
        assert budget > 0, "tx_ready never came back high -- handshake stalled"
        sample = await _step(dut, valid=1, bit=bits[index])
        observe(sample)
        if sample["ready"]:
            index += 1

    for _ in range(PIPELINE_DEPTH + 2):
        observe(await _step(dut, valid=0))

    return line, stuffed, rx_bits, errors


def _longest_run(values):
    longest = 0
    run = 0
    previous = None
    for value in values:
        run = run + 1 if value == previous else 1
        previous = value
        longest = max(longest, run)
    return longest


@cocotb.test()
async def test_round_trip_random_stream(dut):
    """512 random bits survive stuff -> NRZI -> NRZI -> destuff intact."""
    await _start_clock(dut)
    await _reset(dut)

    rng = random.Random(20260820)
    # Biased toward 1s so the round trip actually exercises stuffing.
    bits = [1 if rng.random() < 0.8 else 0 for _ in range(512)]

    line, stuffed, rx_bits, errors = await _loopback(dut, bits)

    expected_stuffed, flags = bit_stuff(bits)
    assert stuffed == sum(flags) > 0, "stuffing did not fire as the model expects"
    assert line == nrzi_encode(expected_stuffed), "line stream differs from the model"
    assert rx_bits == bits, "the round trip did not recover the transmitted bits"
    assert errors == 0, "a well-formed round trip raised a stuff error"


@cocotb.test()
async def test_round_trip_all_ones(dut):
    """All-1s: maximal stuffing density, still lossless end to end."""
    await _start_clock(dut)
    await _reset(dut)

    bits = [1] * 64
    line, stuffed, rx_bits, errors = await _loopback(dut, bits)

    _expected, flags = bit_stuff(bits)
    assert stuffed == sum(flags) > 0, f"unexpected stuffed-bit count: {stuffed}"
    assert rx_bits == bits, "the round trip did not recover the transmitted bits"
    assert errors == 0, "a legally stuffed 1 run raised a stuff error"

    # The point of the whole exercise: without stuffing an all-1s payload
    # would leave the line static forever. With it, the line cannot hold
    # the same state for more than seven bit times.
    assert _longest_run(line) == 7, f"line held for {_longest_run(line)} bit times"


@cocotb.test()
async def test_round_trip_all_zeros(dut):
    """All-0s: no stuffing at all, a transition on every bit."""
    await _start_clock(dut)
    await _reset(dut)

    bits = [0] * 64
    line, stuffed, rx_bits, errors = await _loopback(dut, bits)

    assert stuffed == 0, "a 0 run should never stuff"
    assert rx_bits == bits, "the round trip did not recover the transmitted bits"
    assert errors == 0, "a 0 run raised a stuff error"
    assert _longest_run(line) == 1, "a 0 run should transition every bit"


@cocotb.test()
async def test_round_trip_after_init(dut):
    """`init` re-arms the whole path for a second, independent stream."""
    await _start_clock(dut)
    await _reset(dut)

    first = [1] * 6 + [0, 1, 0]
    _line, _stuffed, rx_first, errors = await _loopback(dut, first)
    assert rx_first == first, "first stream did not round trip"
    assert errors == 0, "first stream raised a stuff error"

    await _step(dut, valid=0, init=1)

    second = [1] * 9
    line, stuffed, rx_second, errors = await _loopback(dut, second)
    assert rx_second == second, "second stream did not round trip after init"
    assert errors == 0, "second stream raised a stuff error"
    assert stuffed == 1, f"unexpected stuffed-bit count after init: {stuffed}"
    # `init` put the line back at J, so the second stream's encoding starts
    # from the packet-start reference rather than wherever the first ended.
    expected_stuffed, _flags = bit_stuff(second)
    assert line == nrzi_encode(expected_stuffed), "init did not re-arm the line"
