"""Shared cocotb helpers for the `verification/test_usb_*.py` testbenches.

Every per-module testbench in this directory drives its DUT off the same
12 MHz interface clock and starts it the same way; this module is the single
place that pattern is defined so the testbenches that need it
(`test_usb_bit_stuffer.py`, `test_usb_bit_destuffer.py`,
`test_usb_nrzi_encoder.py`, `test_usb_nrzi_decoder.py`,
`test_usb_bit_codec_loopback.py`) import it rather than redefine it. Mirrors
the consolidations in `sim/` (#37, shared `_fmt`/`_repo_relative`) and
`verification/check_records.py` (#39, shared `_git`).

Since issue #84 the four USB-protocol modules under `rtl/common/` are
vendored byte-exact from sky130-usb2-phy, and two of them name their clock
ports `clk_144`/`rst_144_n` -- the master's 144 MHz oversampling-domain
vocabulary. This repo instantiates them on its own 12 MHz interface clock
(one bit per clock, no oversampling; see `rtl/usb_utmi_phy.v`'s header and
`spec/decisions/0002`), so `start_clock` takes the clock signal's name and
those two testbenches pass ``"clk_144"``. The name is vocabulary, not a
frequency: the period below is the same 12 MHz one every other DUT uses.

`_reset(dut)` is deliberately *not* consolidated here: it differs in which
DUT signal names it drives across those testbenches (`bit_stb`/`bit_in` vs.
`bit_strobe`/`bit_level` vs. `enable`/`data_strobe`), and parameterizing it
is not worth the indirection.
"""

import cocotb
from cocotb.clock import Clock

# spec/usb2-device-phy.md #3 ratifies a 12 MHz interface clock -- the raw
# full-speed bit rate, one bit per clock. 83334 ps is 12 MHz to within
# 0.001%, chosen over 83333 ps only so the half period is a whole number of
# picoseconds at this request's 1 ps precision.
CLK_PERIOD_PS = 83334


async def start_clock(dut, clock_name="clk"):
    """Start the 12 MHz interface clock on `dut.<clock_name>`.

    `clock_name` exists for the vendored modules whose clock port is named
    `clk_144` (see the module docstring) -- same clock, different pin name.
    """
    cocotb.start_soon(
        Clock(getattr(dut, clock_name), CLK_PERIOD_PS, unit="ps").start()
    )
