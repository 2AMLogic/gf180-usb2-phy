"""Shared cocotb helpers for the `verification/test_usb_*.py` testbenches.

Every per-module testbench in this directory drives its DUT off the same
12 MHz interface clock and starts it the same way; this module is the single
place that pattern is defined so the five testbenches that need it
(`test_usb_bit_stuffer.py`, `test_usb_bit_destuffer.py`,
`test_usb_nrzi_encoder.py`, `test_usb_nrzi_decoder.py`,
`test_usb_bit_codec_loopback.py`) import it rather than redefine it. Mirrors
the consolidations in `sim/` (#37, shared `_fmt`/`_repo_relative`) and
`verification/check_records.py` (#39, shared `_git`).

`_reset(dut)` is deliberately *not* consolidated here: it differs in which
DUT signal names it drives across those testbenches (`in_valid`/`in_bit` vs.
`line_valid`/`line_bit` vs. `data_valid`/`data_bit` vs. `tx_valid`/`tx_bit`),
and parameterizing it is not worth the indirection.
"""

import cocotb
from cocotb.clock import Clock

# spec/usb2-device-phy.md #3 ratifies a 12 MHz interface clock -- the raw
# full-speed bit rate, one bit per clock. 83334 ps is 12 MHz to within
# 0.001%, chosen over 83333 ps only so the half period is a whole number of
# picoseconds at this request's 1 ps precision.
CLK_PERIOD_PS = 83334


async def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_PS, unit="ps").start())
