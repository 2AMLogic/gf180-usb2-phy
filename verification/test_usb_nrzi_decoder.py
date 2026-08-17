"""cocotb testbench for `rtl/usb_nrzi_decoder.v`.

Checks the RX-side NRZI decoder bit-exactly against `usb_bit_model`'s
independent Python model, per `spec/usb2-device-phy.md` #11.

Sampling discipline follows `test_harness_counter.py`: drive on a
`FallingEdge`, read on the `FallingEdge` after the `RisingEdge` under test.

This file is *input* to `klt functional-verification` (see
`request-usb-nrzi-decoder.json`), not a pytest module.
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

from usb_bit_model import IDLE_J, nrzi_decode, nrzi_encode

# 12 MHz per spec/usb2-device-phy.md #3; see test_usb_nrzi_encoder.py for
# why 83334 ps rather than 83333 ps.
CLK_PERIOD_PS = 83334


async def _start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_PS, unit="ps").start())


async def _reset(dut):
    dut.rst_n.value = 0
    dut.init.value = 0
    dut.line_valid.value = 0
    dut.line_bit.value = IDLE_J
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)


async def _step(dut, valid, line=IDLE_J, init=0):
    """Present one sampled line state; return `(data_valid, data_bit)`."""
    dut.init.value = init
    dut.line_valid.value = valid
    dut.line_bit.value = line
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    return int(dut.data_valid.value), int(dut.data_bit.value)


async def _decode(dut, line_bits):
    """Push a line stream through the DUT; return the recovered data bits."""
    data = []
    for state in line_bits:
        valid, bit = await _step(dut, valid=1, line=state)
        assert valid == 1, "data_valid low while a bit was being decoded"
        data.append(bit)
    return data


@cocotb.test()
async def test_reset_is_quiet(dut):
    """Out of reset nothing is marked valid."""
    await _start_clock(dut)
    await _reset(dut)
    assert int(dut.data_valid.value) == 0, "data_valid asserted out of reset"


@cocotb.test()
async def test_no_transitions_decode_to_ones(dut):
    """A line held at J with no transitions decodes to a run of 1s.

    This is the "idle / hold" edge case from the issue's test plan: it is
    correct NRZI behavior, not an error. Detecting an over-long run of 1s
    is `usb_bit_destuffer`'s job, not this module's.
    """
    await _start_clock(dut)
    await _reset(dut)

    data = await _decode(dut, [IDLE_J] * 32)
    assert data == [1] * 32, f"a static J line did not decode to 1s: {data}"
    assert data == nrzi_decode([IDLE_J] * 32), "DUT disagrees with the model"


@cocotb.test()
async def test_transition_every_bit_decodes_to_zeros(dut):
    """A line that transitions on every bit decodes to a run of 0s."""
    await _start_clock(dut)
    await _reset(dut)

    line = [i % 2 for i in range(32)]  # K, J, K, ... away from idle J
    data = await _decode(dut, line)
    assert data == [0] * 32, f"an alternating line did not decode to 0s: {data}"
    assert data == nrzi_decode(line), "DUT disagrees with the model"


@cocotb.test()
async def test_random_stream_round_trips(dut):
    """512 random bits, model-encoded, must come back out unchanged."""
    await _start_clock(dut)
    await _reset(dut)

    rng = random.Random(20260817)
    bits = [rng.getrandbits(1) for _ in range(512)]
    line = nrzi_encode(bits)

    data = await _decode(dut, line)
    assert data == nrzi_decode(line), "DUT disagrees with the model"
    assert data == bits, "NRZI round trip did not recover the input"


@cocotb.test()
async def test_gap_is_ignored(dut):
    """A gap in line_valid emits nothing and does not disturb the reference."""
    await _start_clock(dut)
    await _reset(dut)

    # Two transitions -> two 0s; the reference is now K.
    assert await _decode(dut, [0, 1]) == [0, 0]

    for _ in range(5):
        # Wiggle line_bit during the gap: with line_valid low it must not
        # be latched as the transition reference.
        valid, _bit = await _step(dut, valid=0, line=0)
        assert valid == 0, "data_valid asserted during a gap"
        valid, _bit = await _step(dut, valid=0, line=1)
        assert valid == 0, "data_valid asserted during a gap"

    # Reference is still J (the last valid line state), so J decodes to 1.
    valid, bit = await _step(dut, valid=1, line=1)
    assert valid == 1 and bit == 1, "reference was disturbed by the gap"


@cocotb.test()
async def test_init_rearms_the_j_reference(dut):
    """`init` restores the packet-start J reference without a reset."""
    await _start_clock(dut)
    await _reset(dut)

    await _decode(dut, [0])  # reference is now K
    valid, _bit = await _step(dut, valid=0, init=1)
    assert valid == 0, "data_valid asserted while init was high"

    # With the reference back at J, a J line state decodes to 1.
    valid, bit = await _step(dut, valid=1, line=IDLE_J)
    assert valid == 1 and bit == 1, "init did not restore the J reference"
