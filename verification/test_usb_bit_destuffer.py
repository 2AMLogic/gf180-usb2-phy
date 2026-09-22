"""cocotb testbench for `rtl/common/usb_bit_destuffer.v` (vendored, issue #84).

Checks the RX-side bit destuffer bit-exactly against `usb_bit_model`'s
independent Python model -- the floor `spec/usb2-device-phy.md` #11 sets for
this block's digital logic.

The DUT is the rule-9 master's canonical interface (`enable`/`data_strobe`/
`data_bit` -> registered `bit_valid`/`out_bit`/`stuff_err`, on the
`clk_144`/`rst_144_n` port names that are the master's 144 MHz
oversampling-domain vocabulary -- driven here at this repo's 12 MHz
interface clock; see `rtl/usb_utmi_phy.v`'s header and `spec/decisions/0002`).

`enable` is the canonical SOP..EOP gate (the master's `rx_active`), and it
replaces this repo's former per-packet `init` packet-start clear. While
`enable` is low the module is a transparent pass-through (it holds its run
counter at zero and forwards every strobed bit) -- the property its caller
relies on to search for the never-stuffed SYNC pattern on its output, and
the property that makes indefinitely long idle (continuous decoded 1s,
since NRZI of "no transitions" is all ones) incapable of ever accumulating
into a false bit-stuff violation.

Sampling discipline follows `test_harness_counter.py`: inputs are driven on
a `FallingEdge` and outputs are read on the `FallingEdge` after the
`RisingEdge` under test (the outputs are registered, one clock behind
`data_strobe`).

This file is *input* to `klt functional-verification` (see
`request-usb-bit-destuffer.json`), not a pytest module.
"""

import random

import cocotb
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

from cocotb_helpers import start_clock as _start_clock
from usb_bit_model import bit_stuff

CLK = "clk_144"
RST_N = "rst_144_n"


async def _reset(dut):
    getattr(dut, RST_N).value = 0
    dut.enable.value = 0
    dut.data_strobe.value = 0
    dut.data_bit.value = 0
    await ClockCycles(getattr(dut, CLK), 3)
    getattr(dut, RST_N).value = 1
    await FallingEdge(getattr(dut, CLK))


async def _cell(dut, bit=0, strobe=1, enable=1):
    """Present one decoded bit cell; return (bit_valid, out_bit, stuff_err)
    on the clock after it (the module's registered output stage)."""
    dut.enable.value = enable
    dut.data_strobe.value = strobe
    dut.data_bit.value = bit
    await RisingEdge(getattr(dut, CLK))
    await FallingEdge(getattr(dut, CLK))
    return (
        int(dut.bit_valid.value),
        int(dut.out_bit.value),
        int(dut.stuff_err.value),
    )


async def _destuff(dut, bits):
    """Feed `bits` as one enable-gated packet; return (data, errors)."""
    data = []
    errors = 0
    for bit in bits:
        valid, out, err = await _cell(dut, bit=bit)
        if err:
            errors += 1
        if valid:
            data.append(out)
    return data, errors


@cocotb.test()
async def test_reset_is_quiescent(dut):
    """Out of reset: no bit_valid, no stuff_err."""
    await _start_clock(dut, clock_name=CLK)
    await _reset(dut)
    assert int(dut.bit_valid.value) == 0, "bit_valid asserted out of reset"
    assert int(dut.stuff_err.value) == 0, "stuff_err asserted out of reset"


@cocotb.test()
async def test_enabled_destuffing_matches_model(dut):
    """Random packets (stuffed by the model) destuff back to the model's
    data bits with zero stuff errors -- the round trip of the transform."""
    await _start_clock(dut, clock_name=CLK)
    await _reset(dut)

    rng = random.Random(20260821)
    for _ in range(4):
        raw = [1 if rng.random() < 0.8 else 0 for _ in range(128)]
        stuffed, _flags = bit_stuff(raw)

        data, errors = await _destuff(dut, stuffed)
        assert data == raw, "destuffed stream differs from the model"
        assert errors == 0, "a conformant stuffed stream raised stuff_err"

        # Inter-packet gap: EOP drops `enable` (SOP..EOP gating), which
        # zeroes the run counter -- the model treats each packet fresh
        # (its `bit_stuff` starts ones=0), so the DUT must too.
        for _ in range(3):
            await _cell(dut, bit=0, strobe=0, enable=0)


@cocotb.test()
async def test_all_ones_enabled_stuffs_and_errors(dut):
    """All-1s with `enable` high: every 7th bit-time is a stuff position,
    and a 1 there is a violation -- `stuff_err` pulses and the offending
    bit is dropped, exactly as the model's error positions say."""
    await _start_clock(dut, clock_name=CLK)
    await _reset(dut)

    bits = [1] * 32
    data, errors = await _destuff(dut, bits)

    # Model the same input: every position after six 1s is an error.
    expected_errors = 0
    ones = 0
    for bit in bits:
        if ones == 6:
            expected_errors += 1
            ones = 0
            continue
        ones = ones + 1 if bit == 1 else 0
    assert errors == expected_errors > 0, (
        f"expected {expected_errors} stuff errors, saw {errors}"
    )
    assert all(b == 1 for b in data), "non-1 leaked through an all-1s stream"


@cocotb.test()
async def test_trailing_stuffed_bit_at_packet_end_is_removed(dut):
    """A packet ending on exactly six 1s ends with its #7.1.9 trailing
    stuff bit; that bit is removed like any other (the receiver stays
    bit-aligned), with no error."""
    await _start_clock(dut, clock_name=CLK)
    await _reset(dut)

    raw = [0, 1, 0] + [1] * 6
    stuffed, flags = bit_stuff(raw)
    assert flags[-1] is True, "fixture does not end on a stuff position"

    data, errors = await _destuff(dut, stuffed)
    assert data == raw, "trailing stuff bit was not removed cleanly"
    assert errors == 0, "conformant trailing stuff bit raised stuff_err"


@cocotb.test()
async def test_disabled_is_transparent_and_never_errors(dut):
    """`enable` low (not SOP-locked): every strobed bit passes through
    untouched, the run counter does not accumulate, and not even an
    unbounded run of 1s can raise a false stuff_err -- the idle
    false-positive the canonical enable gating exists to remove."""
    await _start_clock(dut, clock_name=CLK)
    await _reset(dut)

    bits = [1] * 64  # far past the six-1 threshold
    data = []
    errors = 0
    for bit in bits:
        valid, out, err = await _cell(dut, bit=bit, enable=0)
        assert valid == 1, "transparent mode dropped a bit"
        assert out == bit, "transparent mode altered a bit"
        errors += err
    assert data == []
    assert errors == 0, "transparent mode raised a stuff error on idle 1s"


@cocotb.test()
async def test_enable_drop_resets_the_run_counter(dut):
    """Dropping `enable` (EOP) zeroes the run counter, so a following
    packet destuffs with no carry-over misalignment -- the canonical
    replacement for the former `init` packet-start clear."""
    await _start_clock(dut, clock_name=CLK)
    await _reset(dut)

    # First packet: leaves the run counter at 5 (five trailing 1s).
    first = [0] + [1] * 5
    data, errors = await _destuff(dut, first)
    assert data == first and errors == 0, "first packet did not pass cleanly"

    # The gap: enable low for a few clocks (EOP/idle).
    for _ in range(4):
        await _cell(dut, bit=1, enable=0)

    # Second packet: starts with a 1. If the run counter carried over at
    # 5, this 1 would reach 6 and the NEXT bit would be treated as a
    # stuff position -- mis-eating the packet's second bit.
    second = [1, 0, 1, 1, 0, 0, 1]
    data, errors = await _destuff(dut, second)
    assert data == second, "run counter carried across the enable gap"
    assert errors == 0, "enable gap produced a spurious stuff error"
