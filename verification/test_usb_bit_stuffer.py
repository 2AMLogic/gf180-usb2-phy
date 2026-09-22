"""cocotb testbench for `rtl/common/usb_bit_stuffer.v` (vendored, issue #84).

Checks the TX-side bit stuffer bit-exactly against `usb_bit_model`'s
independent Python model -- the floor `spec/usb2-device-phy.md` #11 sets for
this block's digital logic.

The DUT is the rule-9 master's canonical interface (`bit_stb`/`bypass`/
`sof`/`bit_in` -> combinational `bit_out`/`consume`/`stuff_pending_after`;
sky130-usb2-phy DR-0002 Decision 3). Back-pressure inverts relative to this
repo's former ready/valid stuffer: `consume == 0` on a strobed bit-time
means "a stuff bit was emitted instead; hold `bit_in` and re-present it on
the next strobe". `stuff_pending_after` is a same-cycle lookahead valid
while `consume == 1`: the very next bit-time is mandatorily a forced stuff
bit -- the signal the TX framer uses to discharge USB 2.0 #7.1.9's
stuff-bit-immediately-before-EOP duty.

Because the outputs are combinational, the sampling discipline differs from
the registered-output testbenches: inputs are driven on a `FallingEdge`,
`await ReadWrite()` lets the combinational logic settle, the outputs are
read for the bit-time being presented, and only then does the `RisingEdge`
commit the run-counter update.

This file is *input* to `klt functional-verification` (see
`request-usb-bit-stuffer.json`), not a pytest module.
"""

import random

import cocotb
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer

from cocotb_helpers import start_clock as _start_clock
from usb_bit_model import bit_stuff


async def _reset(dut):
    dut.rst_n.value = 0
    dut.bit_stb.value = 0
    dut.bypass.value = 0
    dut.sof.value = 0
    dut.bit_in.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)


async def _bit_time(dut, bit=0, stb=1, sof=0, bypass=0):
    """Present one bit-time; return (bit_out, consume, pending) for it.

    The outputs are combinational on the just-driven inputs, so a 1 ps
    settle (still safely inside the low half of the clock period) is
    awaited before reading them -- a bare `ReadWrite()` resume can race
    the write flush and read the pre-drive value.
    """
    dut.bypass.value = bypass
    dut.sof.value = sof
    dut.bit_in.value = bit
    dut.bit_stb.value = stb
    await Timer(1, unit="ps")
    out = (
        int(dut.bit_out.value),
        int(dut.consume.value),
        int(dut.stuff_pending_after.value),
    )
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    return out


async def _send(dut, bits, sof_first=True):
    """Send `bits` as one packet's stuffable field (`sof` on the first bit,
    the canonical packet-start run reset); return the emitted stream and the
    count of stuffed bit-times."""
    emitted = []
    stuffed = 0
    for i, bit in enumerate(bits):
        # Hold `bit_in` across consume==0 cycles: the canonical protocol.
        # Each such cycle emitted a forced stuff bit (bit_out == 0); the
        # held data bit is accepted on the first consume==1 cycle.
        while True:
            result = await _bit_time(
                dut, bit=bit, sof=1 if (sof_first and i == 0) else 0
            )
            emitted.append(result[0])
            if result[1] == 1:
                break
            stuffed += 1
    return emitted, stuffed


@cocotb.test()
async def test_reset_state_is_unstuffed(dut):
    """Out of reset the run counter is zero: the first strobed bit is
    consumed normally and nothing is pending."""
    await _start_clock(dut)
    await _reset(dut)

    out, consume, pending = await _bit_time(dut, bit=0)
    assert (out, consume, pending) == (0, 1, 0), (
        f"reset state not clean: {(out, consume, pending)}"
    )


@cocotb.test()
async def test_all_zeros_never_stuff(dut):
    """A run of 0s never inserts anything (edge case: zero density)."""
    await _start_clock(dut)
    await _reset(dut)

    bits = [0] * 64
    emitted, stuffed = await _send(dut, bits)
    assert emitted == bits, "a 0 was altered in flight"
    assert stuffed == 0, "a 0 run stuffed"


@cocotb.test()
async def test_all_ones_stuff_every_seventh(dut):
    """All-1s: a forced 0 every seventh bit-time, matching the model."""
    await _start_clock(dut)
    await _reset(dut)

    bits = [1] * 64
    emitted, _stuffed = await _send(dut, bits)

    expected, flags = bit_stuff(bits)
    assert emitted == expected, "stuffed stream differs from the model"
    assert sum(flags) > 0, "model says stuffing must fire"


@cocotb.test()
async def test_random_stream_matches_model(dut):
    """512 random bits (biased toward 1s so stuffing fires), bit-exact
    against the model, with the hold-and-represent protocol exercised by
    every inserted bit."""
    await _start_clock(dut)
    await _reset(dut)

    rng = random.Random(20260819)
    bits = [1 if rng.random() < 0.8 else 0 for _ in range(512)]

    emitted, _stuffed = await _send(dut, bits)
    expected, flags = bit_stuff(bits)
    assert emitted == expected, "stuffed stream differs from the model"
    assert sum(flags) > 0, "fixture did not exercise stuffing"

    # Every accepted data bit appears exactly once (the hold protocol
    # neither loses nor duplicates): consumed == len(bits), and the
    # emission count is data + stuff bits.
    assert len(emitted) == len(expected)


@cocotb.test()
async def test_stuff_pending_after_lookahead(dut):
    """`stuff_pending_after` reads high exactly on the consumed cycle of
    the sixth consecutive 1, and the very next strobed bit-time is the
    forced stuff bit (consume == 0, bit_out == 0)."""
    await _start_clock(dut)
    await _reset(dut)

    for i in range(6):
        out, consume, pending = await _bit_time(dut, bit=1, sof=1 if i == 0 else 0)
        assert consume == 1, f"bit {i} was not consumed"
        if i < 5:
            assert pending == 0, f"pending fired early at bit {i}"
        else:
            assert pending == 1, "pending did not fire on the sixth 1"

    out, consume, pending = await _bit_time(dut, bit=1)
    assert (out, consume, pending) == (0, 0, 0), (
        "the bit-time after the sixth 1 was not a forced stuff bit"
    )


@cocotb.test()
async def test_sof_resets_a_carried_run(dut):
    """`sof` on a packet's first bit resets the consecutive-1s run even
    when the previous stream left it maxed: no phantom stuff bit is
    inserted, and the new stream's stuffing matches the model exactly."""
    await _start_clock(dut)
    await _reset(dut)

    # First segment: six 1s, run left maxed -- deliberately NOT flushed.
    for i in range(6):
        _out, consume, _pending = await _bit_time(
            dut, bit=1, sof=1 if i == 0 else 0
        )
        assert consume == 1

    # Second packet starts here: first bit presented WITH sof. If sof
    # failed to reset the run, this strobe would emit a phantom stuff bit
    # (consume == 0) instead of consuming the bit.
    second = [0, 1, 1, 1, 1, 1, 1, 1, 0, 1]
    emitted, _stuffed = await _send(dut, second)
    expected, _flags = bit_stuff(second)
    assert emitted == expected, (
        "sof did not reset the carried run: second stream mis-stuffed"
    )


@cocotb.test()
async def test_bypass_disables_stuffing_entirely(dut):
    """Raw/transparent mode (OpMode 2'b10's `bypass`): every bit passes
    straight through, always consumed, never pending -- even a 64-long
    run of 1s."""
    await _start_clock(dut)
    await _reset(dut)

    bits = [1] * 64
    emitted = []
    for bit in bits:
        out, consume, pending = await _bit_time(dut, bit=bit, bypass=1)
        assert consume == 1, "bypass stalled on a stuff position"
        assert pending == 0, "bypass reported a pending stuff bit"
        emitted.append(out)
    assert emitted == bits, "bypass altered the bit stream"
