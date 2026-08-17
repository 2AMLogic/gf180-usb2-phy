"""cocotb testbench for `rtl/usb_nrzi_encoder.v`.

Checks the TX-side NRZI encoder bit-exactly against `usb_bit_model`'s
independent Python model -- the floor `spec/usb2-device-phy.md` #11 sets
for this block's digital logic ("verified by a cocotb testbench, bit-exact
against NRZI/bit-stuffing/... behavior").

Sampling discipline follows `test_harness_counter.py`: inputs are driven on
a `FallingEdge` and outputs are read on the `FallingEdge` after the
`RisingEdge` under test, so a cocotb callback never races the DUT's own
non-blocking update at the same simulation event.

This file is *input* to `klt functional-verification` (see
`request-usb-nrzi-encoder.json`), not a pytest module.
"""

import random

import cocotb
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

from cocotb_helpers import start_clock as _start_clock
from usb_bit_model import IDLE_J, nrzi_decode, nrzi_encode


async def _reset(dut):
    dut.rst_n.value = 0
    dut.init.value = 0
    dut.data_valid.value = 0
    dut.data_bit.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)


async def _step(dut, valid, bit=0, init=0):
    """Drive one bit time; return `(line_valid, line_bit)` afterwards."""
    dut.init.value = init
    dut.data_valid.value = valid
    dut.data_bit.value = bit
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    return int(dut.line_valid.value), int(dut.line_bit.value)


async def _encode(dut, bits):
    """Push `bits` through the DUT; return the line states it emitted."""
    line = []
    for bit in bits:
        valid, state = await _step(dut, valid=1, bit=bit)
        assert valid == 1, "line_valid low while a bit was being encoded"
        line.append(state)
    return line


@cocotb.test()
async def test_reset_idles_j(dut):
    """Out of reset the line sits at J with nothing marked valid."""
    await _start_clock(dut)
    await _reset(dut)
    assert int(dut.line_bit.value) == IDLE_J, "line did not reset to J"
    assert int(dut.line_valid.value) == 0, "line_valid asserted out of reset"


@cocotb.test()
async def test_all_ones_hold_the_line(dut):
    """A run of 1s produces no transitions at all (edge case: static line)."""
    await _start_clock(dut)
    await _reset(dut)

    line = await _encode(dut, [1] * 32)
    assert line == [IDLE_J] * 32, f"1s transitioned the line: {line}"
    assert line == nrzi_encode([1] * 32), "DUT disagrees with the model"


@cocotb.test()
async def test_all_zeros_transition_every_bit(dut):
    """A run of 0s transitions on every bit (edge case: maximal density)."""
    await _start_clock(dut)
    await _reset(dut)

    bits = [0] * 32
    line = await _encode(dut, bits)
    assert line == nrzi_encode(bits), f"DUT disagrees with the model: {line}"
    # Independently of the model: strictly alternating away from idle J,
    # so the first 0 lands the line on K.
    assert line == [i % 2 for i in range(32)], f"line did not alternate: {line}"


@cocotb.test()
async def test_random_stream_matches_model(dut):
    """512 random bits, bit-exact against the model, and NRZI-decodable."""
    await _start_clock(dut)
    await _reset(dut)

    rng = random.Random(20260816)
    bits = [rng.getrandbits(1) for _ in range(512)]

    line = await _encode(dut, bits)
    assert line == nrzi_encode(bits), "DUT line stream differs from the model"
    # Round trip: decoding the DUT's own output recovers the input exactly.
    assert nrzi_decode(line) == bits, "NRZI round trip did not recover the input"


@cocotb.test()
async def test_gap_holds_the_line(dut):
    """With data_valid low the line holds and nothing is marked valid."""
    await _start_clock(dut)
    await _reset(dut)

    await _encode(dut, [0, 1, 0])  # leaves the line somewhere non-trivial
    held = int(dut.line_bit.value)

    for _ in range(5):
        valid, state = await _step(dut, valid=0)
        assert valid == 0, "line_valid asserted during a gap"
        assert state == held, "line moved during a gap"

    # The run resumes from exactly where it left off.
    valid, state = await _step(dut, valid=1, bit=0)
    assert valid == 1 and state == held ^ 1, "line did not transition after the gap"


@cocotb.test()
async def test_init_returns_to_j(dut):
    """`init` re-establishes the packet-start J reference without a reset."""
    await _start_clock(dut)
    await _reset(dut)

    await _encode(dut, [0])  # drive the line to K
    assert int(dut.line_bit.value) == 0, "a single 0 did not drive the line to K"

    valid, state = await _step(dut, valid=0, init=1)
    assert valid == 0, "line_valid asserted while init was high"
    assert state == IDLE_J, "init did not return the line to J"

    # A following 1 holds J, proving the reference really was re-armed.
    valid, state = await _step(dut, valid=1, bit=1)
    assert valid == 1 and state == IDLE_J, "line moved off J after init"
