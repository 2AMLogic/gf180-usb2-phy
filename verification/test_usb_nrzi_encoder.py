"""cocotb testbench for `rtl/common/usb_nrzi_encoder.v` (vendored, issue #84).

Checks the TX-side NRZI encoder bit-exactly against `usb_bit_model`'s
independent Python model -- the floor `spec/usb2-device-phy.md` #11 sets
for this block's digital logic ("verified by a cocotb testbench, bit-exact
against NRZI/bit-stuffing/... behavior").

The DUT is the rule-9 master's canonical interface (`bit_stb`/`bypass`/
`sof`/`bit_in` -> registered `level_out`; see sky130-usb2-phy DR-0002
Decision 3): one bit-time strobe consumes `bit_in`, and `level_out` shows
the freshly encoded level for the whole clock after that edge. There is no
valid output -- the level is always meaningful -- so the model comparison
is level-per-strobed-bit.

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
    dut.bit_stb.value = 0
    dut.bypass.value = 0
    dut.sof.value = 0
    dut.bit_in.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)


async def _step(dut, bit=0, stb=1, sof=0, bypass=0):
    """Drive one bit time; return `level_out` afterwards."""
    dut.bypass.value = bypass
    dut.sof.value = sof
    dut.bit_stb.value = stb
    dut.bit_in.value = bit
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    return int(dut.level_out.value)


async def _encode(dut, bits):
    """Push `bits` through the DUT, `sof` on the first; return the levels."""
    line = []
    for i, bit in enumerate(bits):
        # `sof` re-derives the transition reference from idle J -- the
        # canonical packet-start behaviour (matched to nrzi_encode's
        # default initial=IDLE_J). Asserted only on the first bit.
        line.append(await _step(dut, bit=bit, sof=1 if i == 0 else 0))
    return line


@cocotb.test()
async def test_reset_idles_j(dut):
    """Out of reset, and un-strobed, the line sits at J."""
    await _start_clock(dut)
    await _reset(dut)
    assert int(dut.level_out.value) == IDLE_J, "line did not reset to J"
    # A clock with no strobe must not move the level either.
    level = await _step(dut, bit=0, stb=0)
    assert level == IDLE_J, "un-strobed clock moved the line"


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
    assert nrzi_decode(line) == bits, "DUT line stream is not NRZI-decodable"


@cocotb.test()
async def test_sof_rederives_reference_from_j(dut):
    """`sof` re-derives this bit's transition from idle J mid-stream: after
    the line has been driven to K, a `sof` bit re-anchors the reference, so
    a data 1 holds at J (not at the stale K level)."""
    await _start_clock(dut)
    await _reset(dut)

    # A single 0 flips the line J -> K.
    level = await _step(dut, bit=0)
    assert level == 0, "first 0 did not land the line on K"

    # sof + data 1: reference is J again, and 1 holds -> the line RETURNS
    # to J on this very bit, where without sof it would have held at K.
    level = await _step(dut, bit=1, sof=1)
    assert level == IDLE_J, "sof did not re-derive the reference from J"


@cocotb.test()
async def test_bypass_passes_the_bit_through_raw(dut):
    """Raw/transparent mode (OpMode 2'b10's `bypass`): `bit_in` reaches
    `level_out` un-transformed and the transition state is not consumed."""
    await _start_clock(dut)
    await _reset(dut)

    bits = [0, 1, 1, 0, 1, 0, 0, 1]
    line = []
    for bit in bits:
        line.append(await _step(dut, bit=bit, bypass=1))
    assert line == bits, f"bypass did not pass bits through raw: {line}"

    # Leaving bypass, the encoder's reference is whatever bypass last put
    # on the wire (bypass persists no transition state of its own): the
    # next encoded 0 transitions from that raw level.
    last_raw = bits[-1]
    level = await _step(dut, bit=0)
    assert level == (0 if last_raw == 1 else 1), (
        "post-bypass transition did not start from the bypassed level"
    )
