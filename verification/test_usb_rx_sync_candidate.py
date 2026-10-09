"""Verification-only structural RX synchronization experiment (issue #123).

Drives `verification/tb_usb_rx_sync_candidate.v` -- the UNCHANGED
production `usb_utmi_phy` behind an optional candidate synchronizer (two
independent flops per input, `rxdp` and `rxdm`) -- with the existing
independent-host stimulus and exact-byte scoreboard of
`test_usb_rx_clock_tolerance.py` (imported, not copied, so the two cannot
drift), and compares:

* **baseline**  (`cand_en`=0): the production RX path, no added flops;
* **candidate** (`cand_en`=1): two stages per input, both resetting
  synchronously to J on `rst_n`=0 or UTMI `Reset`=1;
* **candidate + injection** (`inj_dp`/`inj_dm`): one additional capture
  clock on DP, DM, or both -- deterministic digital fault injection that
  stands in for unequal capture of the two lines. It is NOT an analog
  metastability model; nothing here measures MTBF or resolution time.

This is an experiment, not a fix and not a decision. DR-0003 (Proposed)
establishes that the one-sample-per-bit RX has no sampling margin against
an independent host clock; a synchronizer adds latency and does not add
margin, so the candidate is NOT expected to improve the clock-offset grid
and is not presented as a frequency-slip fix. Ownership, clock domain, and
paired/coherent sampling remain questions for the DR-0003 ruling (#126).

What is ASSERTED (harness validity + structural/latency/reset controls):

* skewed-stimulus model polarity (which line leads -> SE0 vs SE1);
* scoreboard negative controls: altered/missing/extra bytes fail even when
  the real DUT run had `RxError` low;
* every candidate stage resets synchronously to J from both reset sources,
  whatever level the line holds;
* measured latency: input -> LineState is 1 edge (baseline), 3 (candidate),
  4 on an injected line; packet status (`RxActive` rise, every `RxValid`,
  `RxActive` fall) is exactly baseline + 2 clocks for the candidate;
* zero-skew, zero-offset, no-injection controls decode the exact bytes on
  both designs; a +5% host fails on both (the harness can see failure);
* real 2-bit SE0 EOP pulses `eop` once with no `bus_reset`; sustained SE0
  raises `bus_reset`; UTMI Reset / rst_n in idle and mid-packet, and bus
  reset mid-packet, all recover to an exact next packet;
* injection self-check: single-line injection manufactures non-J/K
  samples, both-line injection does not;
* every sweep/grid produces a result for every case.

What is RECORDED, never asserted (characterization -- failures stay
failures): the clock-offset/phase/length/pattern grid per design, and the
J->K / K->J skew x injection sweep, including manufactured SE0/SE1 sample
counts, EOP/bus-reset indications, and packet results.

Phases: the existing eight k/8-period phases (0 = coincident with a DUT
rising edge, scheduler-dependent, NOT claimed) plus one simulator tick
(1 ps) after and before a rising edge.

Environment:
  USB_RXTOL_GRID=full        grid lengths 1,8,64,1024 (default 1,8,64)
  USB_RXSYNC_DESIGNS=a,b     grid designs, subset of baseline,candidate
                             (default both; run them as separate klt
                             invocations for the full grid)
  USB_RXSYNC_OUT_DIR=<dir>   write <design>-grid-matrix.json,
                             skew-injection-sweep.json, controls.json
"""

import json
import os
from fractions import Fraction

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer
from cocotb.utils import get_sim_time

from cocotb_helpers import CLK_PERIOD_PS
from test_usb_rx_clock_tolerance import (
    IDLE_BITS,
    J,
    K,
    LENGTHS_FULL,
    LENGTHS_REDUCED,
    OFFSETS,
    PATTERNS,
    SE0,
    SEED,
    host_states,
    make_payload,
    ppm_of,
    schedule,
    score,
)

T = CLK_PERIOD_PS
SE1 = (1, 1)
DRAIN_CLOCKS = 40

# (label, ps after the reference rising edge). k/8 values are computed
# exactly as the baseline harness does (round(Fraction(k, 8) * T)).
PHASES = (
    [("0/8(coincident)", 0), ("+1tick", 1)]
    + [(f"{k}/8", round(Fraction(k, 8) * T)) for k in range(1, 8)]
    + [("-1tick", T - 1)]
)
CONTROL_PHASE = round(Fraction(1, 2) * T)

# (label, cand_en, inj_dp, inj_dm)
BASELINE = ("baseline", 0, 0, 0)
CANDIDATE = ("candidate", 1, 0, 0)
INJ_DP = ("candidate+inj_dp", 1, 1, 0)
INJ_DM = ("candidate+inj_dm", 1, 0, 1)
INJ_BOTH = ("candidate+inj_both", 1, 1, 1)
VARIANTS = [BASELINE, CANDIDATE, INJ_DP, INJ_DM, INJ_BOTH]
GRID_DESIGNS = {"baseline": BASELINE, "candidate": CANDIDATE}

# Skew: (label, magnitude_ps, transition kind, leading line, scope). Zero
# skew is direction-independent, so it appears once. Scope "all" skews every
# matching transition including SYNC's; scope "payload" only those after
# SYNC, so payload consequences are visible rather than masked by a SYNC
# that was never recognized.
SKEW_MAGS = [("1tick", 1), ("T/8", round(Fraction(T, 8))), ("T/2", round(Fraction(T, 2)))]
SKEWS = [("none", 0, None, None, "all")] + [
    (f"{scope}:{kind}:{lead}-leads:{mlabel}", mag, kind, lead, scope)
    for scope in ("all", "payload")
    for kind in ("J->K", "K->J")
    for lead in ("dp", "dm")
    for mlabel, mag in SKEW_MAGS
]
SYNC_BITS = 8
SKEW_BYTES = 8

LS_NAME = {1: "J", 2: "K", 0: "SE0", 3: "SE1"}  # LineState = {rxdm, rxdp}


# ------------------------------------------------------------- stimulus


def kind_of(prev, new):
    if prev == J and new == K:
        return "J->K"
    if prev == K and new == J:
        return "K->J"
    return None


def line_events(trans, skew_ps=0, kind=None, lead=None, from_ps=None):
    """Per-line event list [(time_ps, line, value)] from `schedule()`
    transitions. For a J<->K transition of type `kind` (at or after
    `from_ps`, if given), the `lead` line switches at the scheduled time and
    the other line `skew_ps` later; every other transition switches both
    lines together."""
    ev = []
    prev = None
    for t, st in trans:
        lag = skew_ps if (skew_ps and kind_of(prev, st) == kind
                          and (from_ps is None or t >= from_ps)) else 0
        for line, val in (("dp", st[0]), ("dm", st[1])):
            ev.append((t + (0 if line == lead else lag), line, val))
        prev = st
    ev.sort(key=lambda e: e[0])
    return ev


async def _drive(dut, events):
    """Independent host: per-line writes at absolute times, no DUT waits."""
    for t, line, val in events:
        now = get_sim_time("ps")
        if t > now:
            await Timer(t - now, unit="ps")
        (dut.rxdp if line == "dp" else dut.rxdm).value = val


# --------------------------------------------------------------- DUT ops


# Simulation time of the current test's clock start. cocotb cancels a
# test's clock at test end and each test starts its own at the CURRENT sim
# time, so rising edges are at _CLK0 + k*T -- not at absolute multiples of
# T. Every phase, edge index and coincidence check below is computed
# relative to _CLK0 so the phase labels mean what they say regardless of
# how long earlier tests ran.
_CLK0 = 0


async def _start_clock(dut):
    global _CLK0
    _CLK0 = int(get_sim_time("ps"))
    cocotb.start_soon(Clock(dut.clk, T, unit="ps").start(start_high=True))


def _next_edge(now, k):
    """Rising-edge time k periods after the last rising edge <= now."""
    return _CLK0 + ((now - _CLK0) // T + k) * T


async def _reset(dut, variant):
    _label, cand, idp, idm = variant
    dut.rst_n.value = 0
    dut.Reset.value = 0
    dut.TxValid.value = 0
    dut.DataOut.value = 0
    dut.OpMode.value = 0
    dut.TermSelect.value = 1
    dut.XcvrSelect.value = 1
    dut.SuspendM.value = 1
    dut.rxdp.value = 1
    dut.rxdm.value = 0
    dut.cand_en.value = cand
    dut.inj_dp.value = idp
    dut.inj_dm.value = idm
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)
    await ClockCycles(dut.clk, 4)


def _sample(dut):
    rxv = int(dut.RxValid.value)
    return {
        "ls": int(dut.LineState.value),
        "rxv": rxv,
        # DataIn is uninitialized (X) until the first byte; read it only
        # when RxValid qualifies it (the baseline harness does the same).
        "data": int(dut.DataIn.value) if rxv else None,
        "act": int(dut.RxActive.value),
        "err": int(dut.RxError.value),
        "eop": int(dut.u_phy.u_eop_detector.eop.value),
        "brst": int(dut.u_phy.u_eop_detector.bus_reset.value),
    }


async def _observe(dut, cycles, ref_edge):
    """Falling-edge monitor. `edge` is the index of the rising edge whose
    register updates the sample shows, relative to `ref_edge` (index 0)."""
    obs = []
    for _ in range(cycles):
        await FallingEdge(dut.clk)
        s = _sample(dut)
        rising = int(get_sim_time("ps")) - T // 2
        # phase-reference guard: falling edges must sit at _CLK0 + T/2 + kT
        assert (rising - _CLK0) % T == 0, (rising, _CLK0)
        s["edge"] = (rising - ref_edge) // T
        obs.append(s)
    return obs


async def run_states(dut, variant, states, ratio, phase_ps, skew=None, side=None):
    """Reset, play `states` (per-host-bit (dp, dm) list) from the reference
    edge + phase, observe through drain. `side` is an optional coroutine
    factory `f(ref_edge)` started alongside (reset injection)."""
    await _reset(dut, variant)
    now = int(get_sim_time("ps"))
    ref_edge = _next_edge(now, 3)
    t0 = ref_edge + phase_ps
    trans = schedule(states, ratio, t0)
    _sl, mag, kind, lead, scope = skew or ("none", 0, None, None, "all")
    # first post-SYNC host bit boundary (idle J, then the 8 SYNC bits)
    from_ps = (t0 + round(Fraction((IDLE_BITS + SYNC_BITS) * T) / ratio)
               if scope == "payload" else None)
    events = line_events(trans, mag, kind, lead, from_ps)
    frame_end = t0 + round(Fraction(len(states) * T) / ratio)
    cycles = (frame_end - now) // T + DRAIN_CLOCKS
    cocotb.start_soon(_drive(dut, events))
    if side is not None:
        cocotb.start_soon(side(ref_edge))
    obs = await _observe(dut, cycles, ref_edge)
    return obs, {"ref_edge_ps": ref_edge, "first_edge_ps": t0, "trans": trans, "events": events}


# -------------------------------------------------------------- analysis


def rle_text(runs):
    """Per-sample LineState as 'STATE*count' runs, e.g. 'J*11 K*1 SE0*2'."""
    return " ".join(f"{c}*{n}" for c, n in runs)


def rle(chars):
    out = []
    for c in chars:
        if out and out[-1][0] == c:
            out[-1][1] += 1
        else:
            out.append([c, 1])
    return out


def line_stats(obs):
    """LineState run statistics. In a single-frame case the host's only
    SE0 is its EOP, so the LAST SE0 run is the genuine EOP (possibly
    lengthened/shortened by skew/injection) and every earlier SE0 run --
    and every SE1 run -- is manufactured by unequal capture."""
    runs = rle(LS_NAME[s["ls"]] for s in obs)
    se0 = [n for c, n in runs if c == "SE0"]
    se1 = [n for c, n in runs if c == "SE1"]
    manu0 = se0[:-1]
    return {
        "linestate_rle": rle_text(runs),
        "genuine_eop_se0_samples": se0[-1] if se0 else 0,
        "manufactured_se0_runs": len(manu0),
        "manufactured_se0_samples": sum(manu0),
        "manufactured_se0_max_run": max(manu0, default=0),
        "manufactured_se1_runs": len(se1),
        "manufactured_se1_samples": sum(se1),
        "manufactured_se1_max_run": max(se1, default=0),
        "eop_pulses": sum(s["eop"] for s in obs),
        "bus_reset_samples": sum(s["brst"] for s in obs),
    }


def episodes(obs):
    """Split by RxActive rises; RxValid bytes belong to the latest rise."""
    eps = []
    prev = 0
    for s in obs:
        if s["act"] and not prev:
            eps.append({"bytes": [], "err": False, "rise_edge": s["edge"], "fall_edge": None,
                        "valid_edges": []})
        if eps:
            e = eps[-1]
            if s["rxv"]:
                e["bytes"].append(s["data"])
                e["valid_edges"].append(s["edge"])
            e["err"] = e["err"] or bool(s["err"])
            if prev and not s["act"] and e["fall_edge"] is None:
                e["fall_edge"] = s["edge"]
        prev = s["act"]
    return eps


def packet_result(obs, payload):
    rx = [s["data"] for s in obs if s["rxv"]]
    active_seen = any(s["act"] for s in obs)
    err_seen = any(s["err"] for s in obs)
    end_low = not obs[-1]["act"]
    ok, reason, first = score(payload, rx, active_seen, end_low, err_seen)
    eps = episodes(obs)
    return {
        "pass": ok,
        "reason": reason,
        "first_mismatch_index": first,
        "expected_bytes": len(payload),
        "received_bytes": len(rx),
        "rx_active_seen": active_seen,
        "rx_active_ended": end_low,
        "rx_error_seen": err_seen,
        "rx_active_episodes": len(eps),
        "rx_active_rise_edge": eps[0]["rise_edge"] if eps else None,
        "first_rx_valid_edge": eps[0]["valid_edges"][0] if eps and eps[0]["valid_edges"] else None,
        "rx_active_fall_edge": eps[-1]["fall_edge"] if eps else None,
    }, rx


async def run_packet(dut, variant, payload, ratio, phase_ps, skew=None):
    states, stuffed = host_states(payload)
    obs, meta = await run_states(dut, variant, states, ratio, phase_ps, skew)
    res, rx = packet_result(obs, payload)
    res.update(line_stats(obs))
    res.update(
        stuffed_wire_bits=stuffed,
        host_bit_periods=len(states),
        requested_ratio=float(ratio),
        requested_ppm=ppm_of(ratio),
        first_edge_ps=meta["first_edge_ps"],
        ref_edge_ps=meta["ref_edge_ps"],
        # host line events landing exactly on a DUT rising edge (the clock
        # starts at t=0, rising edges at multiples of T): their capture
        # order is scheduler-dependent, so such cases are NOT claimed
        coincident_host_edges=sum(1 for t, _l, _v in meta["events"] if (t - _CLK0) % T == 0),
        # host SE0 (EOP) start, as an edge index: the first rising edge at
        # or after the host drives SE0
        host_eop_start_edge=-(-(meta["trans"][-2][0] - meta["ref_edge_ps"]) // T),
    )
    return res, rx, obs


def _out_dir():
    d = os.environ.get("USB_RXSYNC_OUT_DIR")
    if d:
        os.makedirs(d, exist_ok=True)
    return d


def _dump(path, header, cases):
    """Columnar JSON: `columns` names the fields once, each `rows` entry is
    one case (one per line -- diff-friendly and compact). Rebuild case
    dicts with dict(zip(columns, row)); `rx_sync_candidate_summary.py`
    does exactly that."""
    cols = sorted({k for c in cases for k in c})
    with open(path, "w") as f:
        f.write("{\n")
        for k, v in header.items():
            f.write(f" {json.dumps(k)}: {json.dumps(v)},\n")
        f.write(f' "columns": {json.dumps(cols)},\n')
        f.write(' "rows": [\n')
        for i, c in enumerate(cases):
            row = json.dumps([c.get(k) for k in cols], separators=(",", ":"))
            f.write("  " + row + (",\n" if i + 1 < len(cases) else "\n"))
        f.write(" ]\n}\n")


_CONTROLS = {}


def _record_control(key, value):
    _CONTROLS[key] = value
    d = _out_dir()
    if d:
        with open(os.path.join(d, "controls.json"), "w") as f:
            json.dump({"schema": "usb-rx-sync-candidate-controls/1",
                       "device_period_ps": T, "controls": _CONTROLS}, f, indent=1, sort_keys=True)


# ---------------------------------------------------------------- tests


@cocotb.test()
async def test_skew_stimulus_model(dut):
    """Pure model: zero skew equals the baseline schedule; skew delays only
    the lagging line of the selected transition type by exactly the skew;
    and lead polarity yields the expected intermediate line state."""
    payload = make_payload("mixed", 8)
    states, _ = host_states(payload)
    trans = schedule(states, Fraction(1), 1_000_000)
    zero = line_events(trans)
    assert len(zero) == 2 * len(trans)
    for (t, st), (e0, e1) in zip(trans, zip(zero[0::2], zero[1::2])):
        assert e0[0] == e1[0] == t
    # replay a skewed event list into a level timeline and check the
    # transient states between lead and lag edges
    expect = {("J->K", "dp"): SE0, ("J->K", "dm"): SE1,
              ("K->J", "dp"): SE1, ("K->J", "dm"): SE0}
    for (kind, lead), mid in expect.items():
        for _ml, mag in SKEW_MAGS:
            ev = line_events(trans, mag, kind, lead)
            assert len(ev) == 2 * len(trans)
            level = {"dp": 1, "dm": 0}
            seen = set()
            n_kind = sum(1 for (a, b) in zip(states, states[1:]) if kind_of(a, b) == kind)
            for i, (t, line, val) in enumerate(ev):
                level[line] = val
                nxt = ev[i + 1][0] if i + 1 < len(ev) else None
                st = (level["dp"], level["dm"])
                # intervals before the host's own EOP SE0 (trans[-2])
                if nxt is not None and nxt > t and t < trans[-2][0] and st not in (J, K):
                    seen.add((st, nxt - t))
            assert seen == {(mid, mag)}, (kind, lead, mag, seen)
            assert n_kind > 0
    # SE0/J transitions (EOP) change one line only and are never skewed.
    ev = line_events(trans, SKEW_MAGS[-1][1], "K->J", "dm")
    assert ev[-1][0] == trans[-1][0]
    # Payload scope: no SYNC (or idle) transition is skewed, and at least
    # one post-SYNC transition is.
    from_ps = 1_000_000 + (IDLE_BITS + SYNC_BITS) * T
    for kind in ("J->K", "K->J"):
        ev = line_events(trans, SKEW_MAGS[-1][1], kind, "dp", from_ps)
        sync_times = {t for t, _st in trans if t < from_ps}
        assert {t for t, _l, _v in ev if t < from_ps} == sync_times
        assert len({t for t, _l, _v in ev} - {t for t, _st in trans}) > 0


@cocotb.test()
async def test_scoreboard_negative_controls(dut):
    """Altered, missing and extra bytes must fail even with RxError low --
    pure-scoreboard checks and on a real (passing, RxError-low) DUT run."""
    exp = [1, 2, 3, 4]
    assert score(exp, exp, True, True, False)[0]
    assert score(exp, [1, 2, 9, 4], True, True, False) == (False, "corrupt_byte", 2)
    assert score(exp, [1, 2, 3], True, True, False) == (False, "truncated", 3)
    assert score(exp, [1, 2, 3, 4, 5], True, True, False) == (False, "extra_bytes", 4)
    await _start_clock(dut)
    out = {}
    for variant in (BASELINE, CANDIDATE):
        payload = make_payload("mixed", 8)
        res, rx, _ = await run_packet(dut, variant, payload, Fraction(1), CONTROL_PHASE)
        assert res["pass"] and not res["rx_error_seen"], res
        a, e = res["rx_active_seen"], res["rx_active_ended"]
        altered = list(rx)
        altered[3] ^= 0x10
        checks = {
            "unmodified": score(payload, rx, a, e, False),
            "altered_byte": score(payload, altered, a, e, False),
            "missing_byte": score(payload, rx[:-1], a, e, False),
            "extra_byte": score(payload, rx + [0x5A], a, e, False),
        }
        assert checks["unmodified"][0]
        assert checks["altered_byte"] == (False, "corrupt_byte", 3)
        assert checks["missing_byte"] == (False, "truncated", len(payload) - 1)
        assert checks["extra_byte"] == (False, "extra_bytes", len(payload))
        out[variant[0]] = {k: list(v) for k, v in checks.items()}
    _record_control("scoreboard_negative_controls", out)


@cocotb.test()
async def test_candidate_reset_to_j(dut):
    """Both candidate stages (and the injection stage) reset synchronously
    to J on rst_n=0 and on UTMI Reset=1, whatever the line holds; LineState
    is J during reset; after release the chain refills in 3 edges."""
    await _start_clock(dut)
    rec = []
    for source in ("rst_n", "Reset"):
        for line in (K, SE0, SE1):
            await _reset(dut, INJ_BOTH)
            dut.rxdp.value, dut.rxdm.value = line
            await ClockCycles(dut.clk, 5)
            await FallingEdge(dut.clk)
            pre = (int(dut.dp_s2.value), int(dut.dm_s2.value))
            assert pre == line, (source, line, pre)
            if source == "rst_n":
                dut.rst_n.value = 0
            else:
                dut.Reset.value = 1
            # synchronous: unchanged before the edge, J after it
            await Timer(1, unit="ps")
            assert (int(dut.dp_s1.value), int(dut.dm_s1.value)) == line
            await RisingEdge(dut.clk)
            await FallingEdge(dut.clk)
            for st in ("s1", "s2", "s3"):
                got = (int(getattr(dut, f"dp_{st}").value), int(getattr(dut, f"dm_{st}").value))
                assert got == J, (source, line, st, got)
            assert int(dut.LineState.value) == 0b01, (source, line)
            await ClockCycles(dut.clk, 3)
            await FallingEdge(dut.clk)
            assert int(dut.LineState.value) == 0b01
            dut.rst_n.value = 1
            dut.Reset.value = 0
            refill = None
            for n in range(1, 8):
                await FallingEdge(dut.clk)
                if (int(dut.phy_rxdp.value), int(dut.phy_rxdm.value)) == line and refill is None:
                    refill = n
            # inj_both: s3 is the 3rd stage => line reaches phy after 3 edges
            assert refill == 3, (source, line, refill)
            rec.append({"source": source, "line": list(line), "stages_after_reset": "J",
                        "linestate_during_reset": "J", "edges_to_refill_inj_both": refill})
    _record_control("candidate_reset_to_j", rec)


@cocotb.test()
async def test_latency(dut):
    """Measure input->stage->LineState latency per variant, and packet
    status latency (RxActive rise, each RxValid, RxActive fall) baseline
    vs candidate. Asserted: LineState edge 1 / 3 / 4(injected line); packet
    status exactly +2 clocks for the candidate."""
    await _start_clock(dut)
    step = {}
    for variant in VARIANTS:
        await _reset(dut, variant)
        now = int(get_sim_time("ps"))
        ref = _next_edge(now, 2)
        await Timer(ref + CONTROL_PHASE - now, unit="ps")  # mid-cycle J->K
        dut.rxdp.value, dut.rxdm.value = K
        first = {}
        for n in range(1, 7):
            await RisingEdge(dut.clk)
            await Timer(1, unit="ps")
            vals = {
                "dp_s1": int(dut.dp_s1.value) == 0, "dm_s1": int(dut.dm_s1.value) == 1,
                "dp_s2": int(dut.dp_s2.value) == 0, "dm_s2": int(dut.dm_s2.value) == 1,
                "phy_rxdp": int(dut.phy_rxdp.value) == 0, "phy_rxdm": int(dut.phy_rxdm.value) == 1,
                "LineState_dp_bit": (int(dut.LineState.value) & 1) == 0,
                "LineState_dm_bit": (int(dut.LineState.value) >> 1) == 1,
            }
            for k, v in vals.items():
                if v and k not in first:
                    first[k] = n
        step[variant[0]] = first
    want = {"baseline": (1, 1), "candidate": (3, 3), "candidate+inj_dp": (4, 3),
            "candidate+inj_dm": (3, 4), "candidate+inj_both": (4, 4)}
    for name, (dp_e, dm_e) in want.items():
        got = (step[name]["LineState_dp_bit"], step[name]["LineState_dm_bit"])
        assert got == (dp_e, dm_e), (name, got, step[name])
    assert step["candidate"]["dp_s1"] == 1 and step["candidate"]["dp_s2"] == 2

    pkt = {}
    for variant in (BASELINE, CANDIDATE):
        per = {}
        for pattern in PATTERNS:
            payload = make_payload(pattern, 8)
            res, _rx, obs = await run_packet(dut, variant, payload, Fraction(1), CONTROL_PHASE)
            assert res["pass"], (variant, pattern, res)
            ep = episodes(obs)[0]
            per[pattern] = {
                "rx_active_rise_edge": ep["rise_edge"],
                "rx_valid_edges": ep["valid_edges"],
                "rx_active_fall_edge": ep["fall_edge"],
                "host_eop_start_edge": res["host_eop_start_edge"],
            }
        pkt[variant[0]] = per
    for pattern in PATTERNS:
        b, c = pkt["baseline"][pattern], pkt["candidate"][pattern]
        assert c["rx_active_rise_edge"] == b["rx_active_rise_edge"] + 2, (pattern, b, c)
        assert c["rx_active_fall_edge"] == b["rx_active_fall_edge"] + 2, (pattern, b, c)
        assert c["rx_valid_edges"] == [e + 2 for e in b["rx_valid_edges"]], (pattern, b, c)
    _record_control("latency", {
        "note": "edge n = n-th rising edge after a mid-cycle (T/2) input change; "
                "packet edges are relative to the reference edge preceding the first host edge "
                "at phase 1/2, zero offset",
        "input_step_J_to_K_first_edge": step,
        "packet_status_edges": pkt,
    })


@cocotb.test()
async def test_zero_offset_controls(dut):
    """Zero skew, zero offset, no injection: exact bytes on both designs
    (all patterns, regression lengths, phase 1/2). A +5% host must fail on
    both -- a control that the harness can see failure. Failure of this
    test means the EXPERIMENT is invalid, not that the RX is."""
    await _start_clock(dut)
    rec = {}
    for variant in (BASELINE, CANDIDATE):
        for pattern in PATTERNS:
            for nbytes in LENGTHS_REDUCED:
                res, _rx, _ = await run_packet(
                    dut, variant, make_payload(pattern, nbytes), Fraction(1), CONTROL_PHASE)
                assert res["pass"], (variant, pattern, nbytes, res)
                assert res["manufactured_se0_samples"] == 0 and res["manufactured_se1_samples"] == 0
                assert res["eop_pulses"] == 1 and res["bus_reset_samples"] == 0
                rec[f"{variant[0]}:{pattern}:{nbytes}"] = res["reason"]
        res, _rx, _ = await run_packet(
            dut, variant, make_payload("mixed", 64), Fraction(105, 100), CONTROL_PHASE)
        assert not res["pass"], (variant, res)
        rec[f"{variant[0]}:+5%:mixed:64(must fail)"] = res["reason"]
    _record_control("zero_offset_controls", rec)


def _reset_pulse(dut, signal, start_edge_offset, n_clocks):
    """Side coroutine factory: assert `signal` (Reset=1 or rst_n=0) at the
    falling edge `start_edge_offset` clocks after the reference edge, for
    `n_clocks` clocks (synchronous to clk)."""

    async def side(ref_edge):
        when = ref_edge + start_edge_offset * T + T // 2
        now = int(get_sim_time("ps"))
        await Timer(when - now, unit="ps")
        if signal == "Reset":
            dut.Reset.value = 1
        else:
            dut.rst_n.value = 0
        await ClockCycles(dut.clk, n_clocks)
        await FallingEdge(dut.clk)
        dut.Reset.value = 0
        dut.rst_n.value = 1

    return side


@cocotb.test()
async def test_eop_and_reset_controls(dut):
    """Real 2-bit SE0 EOP; sustained bus reset (after a packet and
    mid-packet); UTMI Reset and rst_n during idle and mid-packet. Asserted:
    EOP pulses once without bus_reset; sustained SE0 raises bus_reset; the
    NEXT packet after every interruption decodes exactly. The interrupted
    packet's own outcome is recorded, not asserted."""
    await _start_clock(dut)
    p1 = make_payload("mixed", 8)
    p2 = make_payload("zeros", 8)
    s1, _ = host_states(p1)
    s2, _ = host_states(p2)
    body_start = 8 + 8  # idle + SYNC host bits
    mid = body_start + 30
    scenarios = {
        "real_eop_then_next_packet": (s1 + [J] * 8 + s2, None),
        "sustained_bus_reset_after_packet": (s1 + [SE0] * 40 + [J] * 8 + s2, None),
        "bus_reset_mid_packet": (s1[:mid] + [SE0] * 40 + [J] * 8 + s2, None),
        "utmi_reset_idle": (s1 + [J] * 24 + s2, ("Reset", len(s1) + 6, 5)),
        "rst_n_idle": (s1 + [J] * 24 + s2, ("rst_n", len(s1) + 6, 5)),
        "utmi_reset_mid_packet": (s1 + [J] * 24 + s2, ("Reset", mid, 5)),
        "rst_n_mid_packet": (s1 + [J] * 24 + s2, ("rst_n", mid, 5)),
    }
    rec = {}
    for variant in (BASELINE, CANDIDATE):
        for name, (states, rst) in scenarios.items():
            side = _reset_pulse(dut, *rst) if rst else None
            obs, _meta = await run_states(dut, variant, states, Fraction(1), CONTROL_PHASE,
                                          side=side)
            eps = episodes(obs)
            last = eps[-1]
            nxt = score(p2, last["bytes"], True, last["fall_edge"] is not None, last["err"])
            first = eps[0] if len(eps) > 1 else None
            r = {
                "rx_active_episodes": len(eps),
                "first_packet": (
                    {"bytes": len(first["bytes"]), "exact": first["bytes"] == p1,
                     "rx_error": first["err"]} if first else None),
                "next_packet": list(nxt),
                "eop_pulses": sum(s["eop"] for s in obs),
                "bus_reset_samples": sum(s["brst"] for s in obs),
                "linestate_rle": rle_text(rle(LS_NAME[s["ls"]] for s in obs)),
            }
            rec[f"{variant[0]}:{name}"] = r
            assert nxt[0], (variant, name, r)
            if name == "real_eop_then_next_packet":
                assert len(eps) == 2 and first["bytes"] == p1 and not first["err"], r
                assert r["eop_pulses"] == 2 and r["bus_reset_samples"] == 0, r
            if name == "sustained_bus_reset_after_packet":
                assert first["bytes"] == p1, r
                # SE0 held 40 clocks: bus_reset level from the 30th sample on
                assert r["bus_reset_samples"] == 40 - 30 + 1, r
                assert r["eop_pulses"] == 3, r  # packet 1 EOP, reset's own 2-bit point, packet 2 EOP
            if name == "bus_reset_mid_packet":
                assert r["bus_reset_samples"] == 40 - 30 + 1, r
            if name.endswith("_idle"):
                assert first["bytes"] == p1, r
    _record_control("eop_and_reset", rec)


@cocotb.test()
async def test_injection_self_check(dut):
    """The injection model does what it claims at zero skew, phase 1/2:
    single-line injection manufactures non-J/K LineState samples;
    both-line injection and no injection do not."""
    await _start_clock(dut)
    rec = {}
    for variant in (CANDIDATE, INJ_DP, INJ_DM, INJ_BOTH):
        res, _rx, _ = await run_packet(dut, variant, make_payload("mixed", 8), Fraction(1),
                                       CONTROL_PHASE)
        manu = res["manufactured_se0_samples"] + res["manufactured_se1_samples"]
        if variant in (INJ_DP, INJ_DM):
            assert manu > 0, (variant, res)
        else:
            assert manu == 0, (variant, res)
        if variant is INJ_BOTH:
            assert res["pass"], res
        rec[variant[0]] = {k: res[k] for k in ("pass", "reason", "manufactured_se0_samples",
                                               "manufactured_se1_samples", "eop_pulses")}
    _record_control("injection_self_check", rec)


@cocotb.test()
async def test_skew_injection_sweep(dut):
    """Characterization: J->K / K->J skew (each line leading) x magnitude
    {0, 1 tick, T/8, T/2} x phase x pattern, for baseline and candidate
    with no/DP/DM/both injection, zero offset, 8 bytes. Recorded, not
    asserted, except completeness and that the zero-skew no-injection
    phase-1/2 points (the controls) pass."""
    await _start_clock(dut)
    results = []
    for variant in VARIANTS:
        for skew in SKEWS:
            for plabel, pps in PHASES:
                for pattern in PATTERNS:
                    res, _rx, _ = await run_packet(dut, variant, make_payload(pattern, SKEW_BYTES),
                                                   Fraction(1), pps, skew)
                    res.update(design=variant[0], skew=skew[0], skew_ps=skew[1],
                               skew_kind=skew[2], skew_lead=skew[3], skew_scope=skew[4],
                               phase=plabel,
                               phase_ps=pps, pattern=pattern, post_sync_bytes=SKEW_BYTES,
                               seed=SEED)
                    results.append(res)
    assert len(results) == len(VARIANTS) * len(SKEWS) * len(PHASES) * len(PATTERNS)
    for r in results:
        if r["skew"] == "none" and r["phase_ps"] == CONTROL_PHASE and r["design"] in (
                "baseline", "candidate"):
            assert r["pass"], r
    summary = {}
    for r in results:
        s = summary.setdefault((r["design"], r["skew"]), [0, 0, 0, 0, 0])
        s[0] += r["pass"]
        s[1] += 1
        s[2] += r["manufactured_se0_samples"] > 0
        s[3] += r["manufactured_se1_samples"] > 0
        s[4] += r["coincident_host_edges"] > 0
    lines = ["design / skew : passed/total, cases with manufactured SE0, SE1, "
             "cases with a coincident (unclaimed) host edge"]
    for (d, sk), (p, t, m0, m1, co) in summary.items():
        lines.append(f"{d:>20s} {sk:>24s} : {p}/{t}  se0:{m0} se1:{m1} coincident:{co}")
    dut._log.info("skew x injection sweep\n" + "\n".join(lines))
    d = _out_dir()
    if d:
        _dump(os.path.join(d, "skew-injection-sweep.json"), {
            "schema": "usb-rx-sync-candidate-skew/1",
            "device_period_ps": T,
            "simulator_precision": "1 ps",
            "offset_ppm": 0,
            "skew_model": "lead line switches at the scheduled host time, other line skew_ps later, "
                          "only on transitions of skew_kind; SE0/J (EOP) transitions never skewed",
            "injection_model": "one extra clean capture flop on the named line(s); digital, "
                               "deterministic; not analog metastability",
            "phases": PHASES,
        }, results)


@cocotb.test()
async def test_grid(dut):
    """Characterization: the existing independent-host offset x phase x
    pattern x length grid, per design, plus the +/-1-tick phases. Records
    every case; asserts only completeness."""
    await _start_clock(dut)
    full = os.environ.get("USB_RXTOL_GRID") == "full"
    lengths = LENGTHS_FULL if full else LENGTHS_REDUCED
    names = [n.strip() for n in os.environ.get("USB_RXSYNC_DESIGNS", "baseline,candidate").split(",")
             if n.strip()]
    for name in names:
        variant = GRID_DESIGNS[name]
        results = []
        for olabel, ratio in OFFSETS:
            for plabel, pps in PHASES:
                for pattern in PATTERNS:
                    for nbytes in lengths:
                        res, _rx, _ = await run_packet(dut, variant, make_payload(pattern, nbytes),
                                                       ratio, pps)
                        # counts are kept; the per-sample RLE is not (1024-byte
                        # cases would make it megabytes per case)
                        res.pop("linestate_rle")
                        res.update(design=name, offset=olabel, phase=plabel, phase_ps=pps,
                                   pattern=pattern, post_sync_bytes=nbytes, seed=SEED)
                        results.append(res)
        assert len(results) == len(OFFSETS) * len(PHASES) * len(PATTERNS) * len(lengths)
        npass = sum(r["pass"] for r in results)
        nsilent = sum((not r["pass"]) and (not r["rx_error_seen"]) for r in results)
        dut._log.info(f"grid {name}: {npass}/{len(results)} receive-pass, "
                      f"{len(results) - npass} measured failures ({nsilent} with RxError never high)")
        d = _out_dir()
        if d:
            _dump(os.path.join(d, f"{name}-grid-matrix.json"), {
                "schema": "usb-rx-sync-candidate-grid/1",
                "design": name,
                "convention": "ppm = 1e6*(f_host/f_dev - 1); host period = T_dev/(1+ppm/1e6)",
                "device_period_ps": T,
                "simulator_precision": "1 ps",
                "grid": "full" if full else "reduced",
                "lengths": lengths,
                "phases": PHASES,
                "offsets": [[label, str(ratio)] for label, ratio in OFFSETS],
            }, results)
