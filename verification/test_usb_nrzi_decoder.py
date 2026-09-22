"""cocotb testbench for `rtl/common/usb_nrzi_decoder.v` (vendored, issue #84).

Checks the RX-side NRZI decoder bit-exactly against `usb_bit_model`'s
independent Python model -- the floor `spec/usb2-device-phy.md` #11 sets for
this block's digital logic.

The DUT is the rule-9 master's canonical interface (`bit_strobe`/
`bit_level`/`bit_is_jk` -> `data_strobe`/`data_bit`; sky130-usb2-phy
DR-0002 Decision 3), on the `clk_144`/`rst_144_n` port names that are the
master's domain vocabulary -- driven here at this repo's 12 MHz interface
clock, one bit per strobe (see `rtl/usb_utmi_phy.v`'s header and
`spec/decisions/0002`).

`bit_is_jk` is load-bearing and gets its own tests: NRZI is defined only
over the two valid differential states, so a bit cell flagged not-J/K (EOP's
SE0 bit times, a bus reset, illegal SE1) must produce no `data_strobe`, no
`data_bit` update, and no `prev_level` update -- the decode resumes
correctly from the true reference on the next genuine J/K cell.

Sampling discipline follows `test_harness_counter.py`: inputs are driven on
a `FallingEdge` and outputs are read on the `FallingEdge` after the
`RisingEdge` under test.

This file is *input* to `klt functional-verification` (see
`request-usb-nrzi-decoder.json`), not a pytest module.
"""

import random

import cocotb
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

from cocotb_helpers import start_clock as _start_clock
from usb_bit_model import IDLE_J, nrzi_encode

# The vendored module's clock/reset port names (the master's 144 MHz
# oversampling-domain vocabulary, instantiated here on the 12 MHz
# interface clock -- see this file's docstring).
CLK = "clk_144"
RST_N = "rst_144_n"


async def _reset(dut):
    getattr(dut, RST_N).value = 0
    dut.bit_strobe.value = 0
    dut.bit_level.value = IDLE_J
    dut.bit_is_jk.value = 0
    await ClockCycles(getattr(dut, CLK), 3)
    getattr(dut, RST_N).value = 1
    await FallingEdge(getattr(dut, CLK))


async def _sample(dut, level, is_jk=1, strobe=1):
    """Present one recovered bit cell; return `(data_strobe, data_bit)`."""
    dut.bit_is_jk.value = is_jk
    dut.bit_strobe.value = strobe
    dut.bit_level.value = level
    await RisingEdge(getattr(dut, CLK))
    await FallingEdge(getattr(dut, CLK))
    return int(dut.data_strobe.value), int(dut.data_bit.value)


async def _decode(dut, line_bits):
    """Feed `line_bits` as J/K cells; return the decoded data bits."""
    out = []
    for level in line_bits:
        strobe, bit = await _sample(dut, level)
        assert strobe == 1, "data_strobe low for a genuine J/K cell"
        out.append(bit)
    return out


@cocotb.test()
async def test_reset_is_quiescent(dut):
    """Out of reset: no data_strobe until a J/K cell is strobed in."""
    await _start_clock(dut, clock_name=CLK)
    await _reset(dut)
    assert int(dut.data_strobe.value) == 0, "data_strobe asserted out of reset"

    strobe, _bit = await _sample(dut, IDLE_J, strobe=0)
    assert strobe == 0, "an un-strobed clock produced data_strobe"


@cocotb.test()
async def test_idle_line_decodes_to_ones(dut):
    """A line with no transitions at all (idle J) decodes to a run of 1s --
    correct NRZI behaviour, not an error (the destuffer judges runs)."""
    await _start_clock(dut, clock_name=CLK)
    await _reset(dut)

    bits = await _decode(dut, [IDLE_J] * 32)
    assert bits == [1] * 32, f"idle J did not decode to 1s: {bits}"


@cocotb.test()
async def test_alternating_line_decodes_to_zeros(dut):
    """A transition on every cell recovers all 0s (edge case: max density)."""
    await _start_clock(dut, clock_name=CLK)
    await _reset(dut)

    line = [i % 2 for i in range(32)]
    bits = await _decode(dut, line)
    assert bits == [0] * 32, f"alternating line did not decode to 0s: {bits}"


@cocotb.test()
async def test_random_stream_matches_model(dut):
    """512 random bits round-trip through the model's own encoder first,
    then decode bit-exactly back."""
    await _start_clock(dut, clock_name=CLK)
    await _reset(dut)

    rng = random.Random(20260817)
    bits = [rng.getrandbits(1) for _ in range(512)]
    line = nrzi_encode(bits)

    got = await _decode(dut, line)
    assert got == bits, "DUT decode differs from the model"


@cocotb.test()
async def test_se0_cells_never_decode_as_data(dut):
    """`bit_is_jk` low (SE0/SE1 cells: EOP, bus reset) produces no
    data_strobe and leaves the reference untouched -- the decode after the
    gap continues from the pre-gap line level, not from a phantom update.

    This is the property EOP correctness rests on: an EOP's two SE0 bit
    times must not decode as data bits appended to the packet."""
    await _start_clock(dut, clock_name=CLK)
    await _reset(dut)

    # Pre-gap: drive the line to K (a 0 from idle J).
    strobe, bit = await _sample(dut, 0)
    assert (strobe, bit) == (1, 0), "pre-gap transition did not decode to 0"

    # The gap: two not-J/K cells (EOP's SE0 pair), strobed but flagged.
    for _ in range(2):
        strobe, _bit = await _sample(dut, 0, is_jk=0)
        assert strobe == 0, "a not-J/K cell produced data_strobe"

    # Post-gap: line still at K. A 1 (hold) must decode as 1 -- proof the
    # SE0 cells did not corrupt `prev_level` (a phantom update to the SE0
    # level would make this a transition -> a spurious 0).
    strobe, bit = await _sample(dut, 0)
    assert (strobe, bit) == (1, 1), (
        "SE0 cells corrupted the transition reference"
    )

    # And a genuine transition right after the gap still decodes to 0.
    strobe, bit = await _sample(dut, 1)
    assert (strobe, bit) == (1, 0), "post-gap transition lost"
