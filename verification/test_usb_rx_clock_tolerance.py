"""cocotb characterization of `rtl/usb_utmi_phy.v`'s RX path against a host
whose bit clock is NOT the device clock (issue #108; spec §7 +/-2500 ppm).

Every other RX test in this directory drives the RX from the PHY's own TX
or from a stimulus that changes once per DUT clock edge, so none of them can
see a rate mismatch. The RX here is one sample per 12 MHz clock with no
oversampling and no clock/data recovery (`rtl/usb_sync_detector.v` header),
so the question this file *measures* is how much host/device frequency
offset, over how long a packet, it tolerates.

Stimulus is an independent host model: timed cocotb events at absolute
simulator times, never derived from DUT edges. The DUT is observed by a
separate per-clock monitor sampling on the falling edge (signals settled).

Conventions (stated once, used everywhere):

* Relative offset: `ppm = 1e6 * (f_host / f_dev - 1)`; the host bit period
  is `T_dev / (1 + ppm/1e6)`. Positive = host faster than the device.
* Two assumed +/-2500 ppm clocks give the opposing endpoint ratios
  `1.0025/0.9975` (+5012.531 ppm) and `0.9975/1.0025` (-4987.531 ppm).
  This is arithmetic on the assumed spec §7 figure, not a verification of
  the USB standard's host tolerance.
* Timing uses absolute deadlines: transition k of a case is scheduled at
  `t0 + round(k * T_dev / ratio)` computed in exact rational arithmetic, so
  per-bit rounding never accumulates into a frequency error (<= 0.5 ps
  absolute error at the 1 ps simulator precision).
* Phase: host bit boundaries sit at `phase * T_dev` after a DUT rising
  clock edge. Phase 0 puts the first host edge coincident with a DUT edge
  (cocotb applies the host write in the same time step; the DUT sampling
  order is then scheduler-dependent and is NOT claimed). Since the offset
  walks the host edges across the DUT sampling instant, later edges in a
  nonzero-ppm case pass through every effective phase anyway.
* Frame per case: idle J, unstuffed SYNC (KJKJKJKK), payload-only bit
  stuffing (incl. the §7.1.9 trailing stuff bit), two host bit periods of
  SE0, one host bit period of J. The PHY treats payload bytes as opaque.
* Pass = DataIn bytes exactly equal the payload (no missing, extra, or
  altered byte), RxActive rose and returned low, RxError never asserted.
  Anything else is a measured failure; RxError low does NOT imply pass.

`npm test` asserts only the harness (stimulus correctness, scoreboard
sensitivity, finite termination, the zero-offset control at a noncoincident
phase, result completeness). The tolerance matrix itself is *recorded*, not
asserted: measured failures are kept as failures in the output artifact.

Environment:
  USB_RXTOL_GRID=full   run the whole issue grid (lengths 1,8,64,1024);
                        default is the reduced regression grid (1,8,64)
  USB_RXTOL_OUT=<path>  write the complete result matrix as JSON
"""

import json
import os
import random
from fractions import Fraction

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, Timer
from cocotb.utils import get_sim_time

from cocotb_helpers import CLK_PERIOD_PS
from usb_bit_model import bit_destuff, bit_stuff, nrzi_decode, nrzi_encode

SYNC_BYTE = 0x80
J, K, SE0 = (1, 0), (0, 1), (0, 0)

IDLE_BITS = 8          # host idle-J bit periods before SYNC
DRAIN_CLOCKS = 40      # DUT clocks observed after the host frame ends
SEED = 1

# Offsets: (label, ratio f_host/f_dev as an exact Fraction).
_PPM_GRID = [0, 1000, -1000, 2500, -2500, 5000, -5000]
OFFSETS = [(f"{p:+d}", 1 + Fraction(p, 10**6)) for p in _PPM_GRID] + [
    ("+endpoint(1.0025/0.9975)", Fraction(10025, 9975)),
    ("-endpoint(0.9975/1.0025)", Fraction(9975, 10025)),
]
PHASES = [Fraction(i, 8) for i in range(8)]
PATTERNS = ["ones", "zeros", "mixed"]
LENGTHS_REDUCED = [1, 8, 64]
LENGTHS_FULL = [1, 8, 64, 1024]


def ppm_of(ratio):
    return float((ratio - 1) * 10**6)


def make_payload(pattern, nbytes):
    if pattern == "ones":
        return [0xFF] * nbytes
    if pattern == "zeros":
        return [0x00] * nbytes
    rng = random.Random(SEED * 100003 + nbytes)
    return [rng.randrange(256) for _ in range(nbytes)]


def byte_bits(byte):
    return [(byte >> i) & 1 for i in range(8)]


def payload_bits(payload):
    bits = []
    for b in payload:
        bits += byte_bits(b)
    return bits


def host_states(payload):
    """Per-host-bit-period (dp, dm) list: idle, SYNC, payload, SE0 x2, J."""
    stuffed, _flags = bit_stuff(payload_bits(payload))
    line = nrzi_encode(byte_bits(SYNC_BYTE) + stuffed)
    to_dpdm = lambda b: J if b else K
    return (
        [J] * IDLE_BITS
        + [to_dpdm(b) for b in line]
        + [SE0, SE0, J]
    ), len(stuffed)


def schedule(states, ratio, t0_ps, period_ps=CLK_PERIOD_PS):
    """Absolute-deadline transition list [(time_ps, state)] for `states`.

    Bit k starts at t0 + round(k * period / ratio), exact rational math.
    Only level changes are emitted (the first period always is).
    """
    out = []
    prev = None
    for k, st in enumerate(states):
        if st != prev:
            t = t0_ps + round(Fraction(k * period_ps) / ratio)
            out.append((t, st))
            prev = st
    return out


def score(expected, got_bytes, rx_active_seen, rx_active_end_low, rx_error_seen):
    """Scoreboard: returns (passed, reason, first_mismatch_index)."""
    first = None
    for i, (e, g) in enumerate(zip(expected, got_bytes)):
        if e != g:
            first = i
            break
    if not rx_active_seen:
        return False, "no_rx_active(sync_not_recognized)", first
    if first is None and len(got_bytes) < len(expected):
        first = len(got_bytes)
        return False, "truncated", first
    if first is None and len(got_bytes) > len(expected):
        return False, "extra_bytes", len(expected)
    if first is not None:
        return False, "corrupt_byte", first
    if not rx_active_end_low:
        return False, "rx_active_stuck_high", None
    if rx_error_seen:
        return False, "rx_error_asserted", None
    return True, "ok", None


async def _start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_PS, unit="ps").start())


async def _reset(dut):
    dut.rst_n.value = 0
    # trim[4:0] (DR-0004 decision 3, #115): the direct production top must
    # expose it and gets the unprogrammed default. Other tops reusing this
    # helper (e.g. tb_usb_rx_sync_candidate, which ties its instance's
    # trim to 5'b00000 itself) are not required to have the port.
    if dut._name == "usb_utmi_phy":
        assert len(dut.trim) == 5, f"trim is {len(dut.trim)} bits wide, want 5"
        dut.trim.value = 0
    elif hasattr(dut, "trim"):
        dut.trim.value = 0
    dut.Reset.value = 0
    dut.TxValid.value = 0
    dut.DataOut.value = 0
    dut.OpMode.value = 0
    dut.TermSelect.value = 1
    dut.XcvrSelect.value = 1
    dut.SuspendM.value = 1
    dut.rxdp.value = 1
    dut.rxdm.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)
    await ClockCycles(dut.clk, 4)


async def _host(dut, transitions):
    """Independent host: drives rxdp/rxdm at absolute times; no DUT waits."""
    for t, (dp, dm) in transitions:
        now = get_sim_time("ps")
        if t > now:
            await Timer(t - now, unit="ps")
        dut.rxdp.value = dp
        dut.rxdm.value = dm


async def run_case(dut, payload, ratio, phase):
    """One frame. Returns the measured-result dict (never asserts)."""
    await _reset(dut)
    states, stuffed_len = host_states(payload)
    now = int(get_sim_time("ps"))
    # First host edge at the next DUT rising edge (multiples of the clock
    # period; the clock starts at t=0) plus the phase offset, after margin.
    next_edge = ((now // CLK_PERIOD_PS) + 3) * CLK_PERIOD_PS
    t0 = next_edge + round(phase * CLK_PERIOD_PS)
    trans = schedule(states, ratio, t0)
    frame_end = t0 + round(Fraction(len(states) * CLK_PERIOD_PS) / ratio)
    cycles = (frame_end - now) // CLK_PERIOD_PS + DRAIN_CLOCKS

    cocotb.start_soon(_host(dut, trans))

    rx_bytes = []
    active_seen = False
    err_seen = False
    last_active = 0
    for _ in range(cycles):
        await FallingEdge(dut.clk)
        if int(dut.RxValid.value):
            rx_bytes.append(int(dut.DataIn.value))
        last_active = int(dut.RxActive.value)
        active_seen = active_seen or bool(last_active)
        err_seen = err_seen or bool(int(dut.RxError.value))

    ok, reason, first = score(payload, rx_bytes, active_seen, not last_active, err_seen)
    return {
        "pass": ok,
        "reason": reason,
        "first_mismatch_index": first,
        "expected_bytes": len(payload),
        "received_bytes": len(rx_bytes),
        "rx_active_seen": active_seen,
        "rx_active_ended": not last_active,
        "rx_error_seen": err_seen,
        "stuffed_wire_bits": stuffed_len,
        "host_bit_periods": len(states),
        "achieved_host_period_ps": float(Fraction(CLK_PERIOD_PS) / ratio),
        "requested_ratio": float(ratio),
        "requested_ppm": ppm_of(ratio),
        "first_edge_ps": t0,
        "last_edge_ps": trans[-1][0],
        "achieved_ratio": (len(states) - 1) * CLK_PERIOD_PS / (trans[-1][0] - trans[0][0]),
    }


# ---------------------------------------------------------------- harness


@cocotb.test()
async def test_stimulus_model(dut):
    """Pure-model checks that need no DUT: the host waveform decodes back to
    the payload at ideal bit centers, its edges lie on the requested
    (ratio-scaled) grid within rounding, and rounding does not accumulate."""
    for pattern in PATTERNS:
        for nbytes in (1, 8, 64):
            payload = make_payload(pattern, nbytes)
            states, stuffed_len = host_states(payload)
            # Ideal-center decode: strip idle, SE0 tail; SYNC; destuff.
            body = states[IDLE_BITS:-3]
            assert all(s in (J, K) for s in body)
            line = [1 if s == J else 0 for s in body]
            decoded = nrzi_decode(line)
            assert decoded[:8] == byte_bits(SYNC_BYTE)
            data, errs = bit_destuff(decoded[8:])
            assert not errs
            assert data == payload_bits(payload), (pattern, nbytes)
            assert len(decoded) - 8 == stuffed_len
            assert states[-3:] == [SE0, SE0, J]
    # Timing: absolute deadlines, no drift. Check on the longest frame at an
    # extreme ratio.
    payload = make_payload("zeros", 1024)
    states, _ = host_states(payload)
    for _label, ratio in OFFSETS:
        trans = schedule(states, ratio, 1_000_000)
        starts = {}
        k = 0
        prev = None
        for i, st in enumerate(states):
            if st != prev:
                starts[i] = st
                prev = st
        for (t, _st), (i, _s2) in zip(trans, starts.items()):
            ideal = 1_000_000 + Fraction(i * CLK_PERIOD_PS) / ratio
            assert abs(t - ideal) <= Fraction(1, 2), (ratio, i, t, float(ideal))
    # Sign convention: positive ppm means host faster => shorter period.
    fast = schedule([J, K], 1 + Fraction(5000, 10**6), 0)
    slow = schedule([J, K], 1 - Fraction(5000, 10**6), 0)
    assert fast[1][0] < CLK_PERIOD_PS < slow[1][0]
    # Endpoint ratios quoted in the docstring.
    assert abs(ppm_of(Fraction(10025, 9975)) - 5012.531) < 1e-3
    assert abs(ppm_of(Fraction(9975, 10025)) + 4987.531) < 1e-3


@cocotb.test()
async def test_scoreboard_detects_faults(dut):
    """The scoreboard must fail corrupt/missing/extra bytes even with RxError
    low and RxActive well-behaved, and a never-recognized SYNC."""
    exp = [1, 2, 3, 4]
    assert score(exp, [1, 2, 3, 4], True, True, False)[0]
    assert score(exp, [1, 2, 9, 4], True, True, False) == (False, "corrupt_byte", 2)
    assert score(exp, [1, 2, 3], True, True, False) == (False, "truncated", 3)
    assert score(exp, [1, 2, 3, 4, 5], True, True, False) == (False, "extra_bytes", 4)
    assert not score(exp, [], False, True, False)[0]
    assert not score(exp, exp, True, False, False)[0]
    assert not score(exp, exp, True, True, True)[0]


@cocotb.test()
async def test_missing_sync_terminates(dut):
    """Idle J only (no SYNC): the case terminates in finite time and is
    reported as a failure, not a hang or a pass."""
    await _start_clock(dut)
    await _reset(dut)
    # The line stays at idle J (set by _reset): no SYNC ever appears.
    cycles = 120
    rx_bytes, active = [], False
    for _ in range(cycles):
        await FallingEdge(dut.clk)
        if int(dut.RxValid.value):
            rx_bytes.append(int(dut.DataIn.value))
        active = active or bool(int(dut.RxActive.value))
    res = score([0xA5], rx_bytes, active, True, False)
    assert res == (False, "no_rx_active(sync_not_recognized)", None), res


@cocotb.test()
async def test_zero_offset_control(dut):
    """Control: zero offset at a noncoincident phase must match every byte.
    A failure here means the harness (not the tolerance) is broken."""
    await _start_clock(dut)
    for pattern in PATTERNS:
        for nbytes in LENGTHS_REDUCED:
            res = await run_case(
                dut, make_payload(pattern, nbytes), Fraction(1), Fraction(1, 2)
            )
            assert res["pass"], (pattern, nbytes, res)
    # Control for the control: the harness must also be able to see a
    # failure -- a +5% host over 64 bytes cannot pass.
    res = await run_case(
        dut, make_payload("mixed", 64), Fraction(105, 100), Fraction(1, 2)
    )
    assert not res["pass"], res


@cocotb.test()
async def test_tolerance_matrix(dut):
    """Characterization sweep. Records every case; asserts only that the
    sweep completed with a result for every grid point. Measured failures
    are data, not test failures."""
    await _start_clock(dut)
    lengths = LENGTHS_FULL if os.environ.get("USB_RXTOL_GRID") == "full" else LENGTHS_REDUCED
    results = []
    for label, ratio in OFFSETS:
        for phase in PHASES:
            for pattern in PATTERNS:
                for nbytes in lengths:
                    res = await run_case(dut, make_payload(pattern, nbytes), ratio, phase)
                    res.update(
                        offset=label,
                        phase_eighths=int(phase * 8),
                        pattern=pattern,
                        post_sync_bytes=nbytes,
                        seed=SEED,
                    )
                    results.append(res)
    expected_cases = len(OFFSETS) * len(PHASES) * len(PATTERNS) * len(lengths)
    assert len(results) == expected_cases

    summary = {}
    for r in results:
        key = (r["offset"], r["post_sync_bytes"])
        s = summary.setdefault(key, [0, 0])
        s[0] += r["pass"]
        s[1] += 1
    lines = ["offset  bytes  passed/total(over phases x patterns)"]
    for (off, n), (p, t) in sorted(summary.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        lines.append(f"{off:>26s} {n:5d}  {p}/{t}")
    dut._log.info("RX clock-tolerance matrix summary\n" + "\n".join(lines))

    out = os.environ.get("USB_RXTOL_OUT")
    if out:
        doc = {
            "schema": "usb-rx-clock-tolerance-matrix/1",
            "convention": "ppm = 1e6*(f_host/f_dev - 1); host period = T_dev/(1+ppm/1e6)",
            "device_period_ps": CLK_PERIOD_PS,
            "simulator_precision": "1 ps",
            "grid": "full" if lengths == LENGTHS_FULL else "reduced",
            "cases": results,
        }
        with open(out, "w") as f:
            json.dump(doc, f, indent=1)
