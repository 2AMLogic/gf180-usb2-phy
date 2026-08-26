# Chipalooza Challenge #5 proposal — GF180MCU USB 2.0 full-speed device PHY

**Program:** Open Circuit Design Chipalooza Challenge #5 (GF180MCU /
Wafer.Space).
**Repository:** [`2AMLogic/gf180-usb2-phy`](https://github.com/2AMLogic/gf180-usb2-phy)
— public, Apache-2.0.

**Rules basis.** Challenge #5's own rules page had not published when this
document was written. It is written against the **Challenge #3 structure**,
which the organizers state Challenge #5 shares (same PDK, same
Wafer.Space platform): a template wrapper cell in a fixed slot; a harness
supplying a bandgap-referenced bias voltage, up to 2 bandgap-referenced
current sources, ≤ 24 digital control inputs, ≤ 12 digital test outputs, ≤ 4
shared (multiplexed) analog lines and ≤ 4 dedicated pads; 3.3 V digital and
5.0 V analog rails, with analog blocks expected to operate across
3.3–5.0 V. Every budget number in §2 should be re-checked against rules-5
when it publishes; §2.8 lists what would change if any of them moved.

**Status of this repository, stated up front.** The digital half of this
block is at the sign-off bar: synthesized, placed and routed, **DRC-clean**
and **LVS-matched**, with timing closed at every liberty corner of its cell
library including the 5.0 V ones. The analog half is **simulation-complete
but has no layout** — all five analog blocks have captured schematics,
exported netlists and full 45-corner PVT sweeps, and three of the five spec
rows they answer currently **fail** at some corners. Nothing has been
fabricated and nothing has been measured on silicon. §4 states every row's
verdict, met and unmet alike, and §6 says plainly what a shuttle seat
would and would not settle.

This document contains no personal or institutional identifiers; the
designer/CV and test-equipment attachments the program asks for separately
are supplied outside this repository.

---

## 1. Type of IP block

A **USB 2.0 full-speed (12 Mbps) device PHY**: the mixed-signal block that
sits between a USB connector's D+/D− pair and a chip's digital logic. It
contains a differential receiver, two single-ended receivers, a
series-terminated differential driver, a trimmed 1.5 kΩ D+ speed-signaling
pull-up, and the digital encode/decode logic (NRZI, bit stuffing, SYNC/EOP
framing, line-state decode) that turns wire-level signaling into a byte
stream at a **UTMI** interface.

Three scope boundaries are deliberate and load-bearing, not gaps:

- **Device only.** No host, no OTG, no role switching. This block is always
  the peripheral end of the cable.
- **Full-speed only, 12 Mbps.** High-speed (480 Mbps) is out of scope, not a
  stretch goal — it is a substantially harder analog problem (current-mode
  drivers, squelch, chirp handshake, elastic buffering) and nothing
  motivating this block needs it.
- **Up to the UTMI boundary, and no further** — see §3.1.

USB PHY is named explicitly in the sibling GF180 brief's own suggested block
list ("SERDES, LVPECL/LVDS drivers/receivers, PLLs, programmable filters,
USB PHY, etc." appears in the IHP brief; the GF180 brief's list is shorter
but not exclusive). It is also an unusually good shuttle candidate for the
reason §6 gives: its central claims — driver edge rate and crossover into a
real cable load, receiver behaviour at the top of the common-mode range —
are exactly the kind that a bench and a real host settle and a simulator
argues about.

---

## 2. I/O list

The block's native interface is the full UTMI port list of
[`rtl/usb_utmi_phy.v`](../../rtl/usb_utmi_phy.v) plus the analog front
end's own pins. That is 35 digital ports plus D+/D− plus the pull-up's
enable and 5 trim bits. It does not fit the slot budget unmodified, so this
section defines a **reduced test-chip pinout**: a thin wrapper around the
existing top level, not a change to it. Nothing below requires editing
`rtl/usb_utmi_phy.v` or any analog schematic; it requires one small piece of
new wrapper RTL, flagged in §2.7.

### 2.1 Budget summary

| Resource | Assumed budget | Requested | Headroom |
|---|---|---|---|
| Digital control inputs | ≤ 24 | **23** | 1 spare |
| Digital test outputs | ≤ 12 | **12** | 0 spare — at the ceiling |
| Shared (multiplexed) analog lines | ≤ 4 | **0** | 4 declined |
| Bandgap-referenced current sources | ≤ 2 | **0** | 2 declined |
| Bandgap-referenced bias voltage | offered | **declined** | not needed |
| Dedicated pads | ≤ 4 | **4** | 0 spare — at the ceiling |

### 2.2 Digital control inputs (23 of 24)

| Pin | Width | Maps to | Purpose |
|---|---|---|---|
| `clk` | 1 | `usb_utmi_phy.clk` | 12 MHz UTMI interface clock (spec §3). Sourced externally — this block has no oscillator and no PLL; the reference-clock row of the spec (§7) is a *requirement on the source*, not a circuit in this block. |
| `rst_n` | 1 | `rst_n` | Active-low power-on reset. |
| `TxValid` | 1 | `TxValid` | UTMI transmit handshake. |
| `DataOut[7:0]` | 8 | `DataOut[7:0]` | UTMI transmit byte. |
| `OpMode[1:0]` | 2 | `OpMode[1:0]` | UTMI operational mode. Present per spec §3; the RTL does not consume it (documented in the module header), so it is brought out for interface conformance and future use, not because it changes behaviour today. |
| `TermSelect` | 1 | `TermSelect` | Same — present, unconsumed. |
| `XcvrSelect` | 1 | `XcvrSelect` | Same — present, unconsumed. Fixed-function on an FS-only PHY. |
| `SuspendM` | 1 | `SuspendM` | Same — present, unconsumed. |
| `Reset` | 1 | `Reset` | Active-high UTMI reset command; **is** consumed by the RTL. |
| `pu_en` | 1 | `dplus_pullup.PU_EN` | D+ pull-up enable (soft-connect / soft-disconnect). Driving this low then high forces a host-visible detach/attach cycle — the single most useful bench control this block has, and the entry point for the §6 enumeration test. |
| `pu_trim[4:0]` | 5 | `dplus_pullup.TRIM0..TRIM4` | Pull-up trim code. The 1.5 kΩ ±5 % row of §4 is **only** met with this ladder set per part; §4 Row F reports both the untrimmed spread and the trimmed error. This is the block's one calibration input and it is exposed deliberately rather than strapped, because measuring the untrimmed spread on silicon is itself a result worth having. |

23 of 24 used; one spare deliberately left for whatever a schematic review adds.

### 2.3 Digital test outputs (12 of 12 — at the ceiling)

| Pin | Width | Maps to | Purpose |
|---|---|---|---|
| `TxReady` | 1 | `TxReady` | UTMI transmit handshake. |
| `RxValid` | 1 | `RxValid` | UTMI receive strobe. |
| `RxActive` | 1 | `RxActive` | Packet in progress (SYNC locked, no EOP yet). |
| `RxError` | 1 | `RxError` | Bit-stuff error on the receive path. |
| `DataIn[7:0]` | 8 | `DataIn[7:0]` | UTMI receive byte. |

**`LineState[1:0]` is deliberately dropped from the pinout, and costs
nothing.** It is a purely combinational decode of the two single-ended
receiver outputs, i.e. of the D+/D− pads themselves — and D+/D− are
dedicated pads (§2.5), directly observable on the bench with a scope. A
logic analyzer capturing the two pads recovers `LineState` exactly, so
spending 2 of 12 scarce test outputs on a function the bench can already see
would buy nothing. This is the one place where the pad decision in §2.5
pays for itself twice.

### 2.4 Shared (multiplexed) analog lines: 0 of 4 — declined, and why D+/D− cannot use them

**Full-speed USB signaling cannot ride a shared, multiplexed analog line.**
This is the load-bearing I/O statement in this proposal, so it is spelled
out rather than assumed:

1. **The line is switched, and USB attachment signaling is not.** A device's
   1.5 kΩ D+ pull-up must be *continuously* presented to the host from the
   moment of attach; that is how the host learns a full-speed device exists
   at all. A multiplexer that connects the pad only while this slot is
   selected makes the device invisible to enumeration whenever another
   design owns the mux.
2. **The switch destroys the source impedance.** The driver's ratified
   output resistance is 28–44 Ω of series termination, chosen to match a
   90 Ω differential cable. An analog mux switch adds tens of ohms of
   on-resistance in series and its own charge injection — the termination
   is no longer the termination.
3. **The switch destroys the edge rate.** Rise/fall must land in 4–20 ns
   into a 50 pF test load (§4 Rows A/B). A shared line carries the pad
   capacitance of every design on it plus the mux, which both slows the edge
   and moves the crossover voltage (§4 Row D) — the two rows that are
   already the tightest in this design.
4. **The pair is differential and must stay matched.** D+ and D− have to see
   the same parasitics for the crossover and matching rows to mean anything.
   Two independent mux paths do not guarantee that.
5. **The far end is a physical connector.** These two nets terminate in a USB
   receptacle on the test board, not in a measurement instrument.

The remaining shared analog lines are declined outright: this block has no
other internal node worth spending shared-analog budget on. Every internal
analog node worth probing is already observable through the digital test
outputs of §2.3 or the pads of §2.5.

### 2.5 Dedicated pads (4 of 4 — at the ceiling)

| Pad | Purpose |
|---|---|
| `DP` | USB D+. Carries the differential driver's D+ output, both single-ended and differential receiver inputs, and the 1.5 kΩ pull-up. Routes to a USB receptacle on the test board. |
| `DM` | USB D−. Same, less the pull-up. |
| `VDDA` | Analog supply for the whole PHY front end (driver, both single-ended receivers, differential receiver) **and** the pull-up rail `VPU_REG`. **Requested at 3.3 V, not 5.0 V — see the rail note below.** |
| `VSSA` | Analog ground. |

The digital section (`usb_utmi_phy`) is asked to sit on the harness's own
**3.3 V digital rail**, not on a dedicated pad — it is ordinary standard-cell
logic and needs no supply isolation. Its DRC-clean, LVS-matched layout
(§5) is timed at that rail and at 5.0 V (§4 Row I), so either works for the
digital half.

#### The rail note (the single largest gap in this proposal)

**Every analog device in this design is from gf180mcu's 3.3 V-rated family.**
`design/netlist/*.spice` instantiates `nfet_03v3` / `pfet_03v3` throughout,
plus `ppolyf_u` poly resistors and two `rm1` metal-1 series-termination
resistors. `sim/harness/corners.py` generates supply points at ±10 % of a
3.3 V nominal (2.97 / 3.30 / 3.63 V) and nothing wider; **no record under
`sim/*/records/` exercises any analog device above 3.63 V.** Running the
front end continuously at a 5.0 V analog rail would put every device above
both the range this repository has simulated and the range its device family
is rated for. That is an engineering risk, not a documentation gap, and this
proposal does not wave it away.

There is also a specification reason the pull-up rail cannot simply follow a
wide supply: spec §5 ratifies `VPU_REG` at **3.0–3.6 V**, because the D+ VOH
the host sees is a speed-signaling requirement, not a convenience. Tying
`VPU_REG` to `VDDA` satisfies that at 3.30 V and 3.63 V but **violates it at
the 2.97 V corner** (2.97 V < 3.00 V). That is recorded here as an unmet row
(§4 Row G), not rounded away.

**Request:** route `VDDA` from the 3.3 V digital rail rather than the 5.0 V
analog rail. If the program requires every seat to sit on the 5.0 V rail,
the options before schematic review are (a) migrate the front end to
gf180mcu's 5 V-rated device family (`nfet_06v0`/`pfet_06v0` — the same
family the digital standard cells already use) and re-run the whole
characterization suite from scratch, or (b) add a compact series regulation
element ahead of `VDDA` so the block's local supply stays in the 3.0–3.6 V
window while occupying only the 5.0 V pads. Neither option has any evidence
in `sim/` today.

### 2.6 Bandgap bias voltage / current sources: declined

This design needs neither. Its only bias-like element is the pull-up trim
ladder of §2.2, which is a digitally-selected resistor network referenced to
`VPU_REG`, not to an external bandgap; no net in `design/netlist/*.spice` is
a bias or bandgap input. We ask that the shared bandgap/current-source
budget be allocated to another entry.

### 2.7 Open items for schematic review

- **The wrapper RTL does not exist yet.** §2.2–§2.3's pinout is a reduction
  of `usb_utmi_phy`'s port list plus the pull-up's controls; it needs one
  small wrapper module (tie-offs for the dropped ports, `LineState`
  left unbrought-out, pull-up controls threaded through) written and checked
  against `verification/`'s existing suite before the pinout is real.
- **`VPU_REG`'s 3.0 V floor** (§2.5) is unresolved and is §4 Row G's unmet
  status.
- **Three §4 rows fail in simulation today** (Rows C, D-partial, E) and are
  *design* work, not documentation work — see §4's own notes.

### 2.8 What changes if the published Challenge #5 rules differ

- **Fewer than 4 dedicated pads:** `DP`/`DM` are non-negotiable (§2.4). The
  first thing dropped would be `VSSA`, sharing the harness ground; then
  `VDDA`, which forces the rail decision in §2.5 to (a) or (b).
- **Fewer than 12 test outputs:** `DataIn[7:0]` collapses to a 1-bit
  serialized stream plus its strobe, costing 6 outputs, at the price of new
  wrapper RTL and a slower bench capture.
- **Fewer than 24 control inputs:** `OpMode`/`TermSelect`/`XcvrSelect`/
  `SuspendM` are unconsumed by the RTL (§2.2) and can be strapped on-die,
  freeing 5 immediately.

---

## 3. Functional description

### 3.1 Where the UTMI boundary falls

**NRZI encode/decode, bit stuffing/destuffing, and SYNC/EOP handling are
INSIDE this block. Everything above them is not.** Concretely, inside:
the differential and single-ended receiver front ends, the differential
driver and D+ pull-up, NRZI encode (TX) and decode (RX), bit stuffing after
every six consecutive 1s (TX) and destuffing (RX), SYNC generation and
SYNC detection/bit-lock, EOP (SE0) generation and detection, and
`LineState[1:0]` reporting.

Outside, and belonging to whatever digital design integrates this PHY: PID
interpretation, CRC-5 and CRC-16, endpoint/address matching, the
enumeration state machine, and every other USB protocol semantic above a
raw byte stream plus line state. A bench host still exercises all of that —
it just exercises it against the integrator's SIE, not against this block.

This is the conventional UTMI split and it is the reason the pinout in §2 is
byte-oriented rather than bit-oriented: a UTMI-compliant PHY hands its link
layer decoded bytes with `RxActive`/`RxValid`/`RxError` status, not raw
NRZI bits.

### 3.2 Transmit path

`DataOut[7:0]`/`TxValid` are serialized LSB-first, prefixed with the fixed
SYNC field (pre-stuff byte `8'h80`, sent LSB-first, i.e. the KJKJKJKK wire
pattern), bit-stuffed, NRZI-encoded, and driven onto `txdp`/`txdm` with the
convention 1 = J, 0 = K. The packet is terminated by the EOP tail: two bit
times of SE0 followed by one bit time of J. If the pre-stuff bit stream ends
on exactly six consecutive 1s, the mandatory trailing stuff bit is emitted
before the EOP — a case the testbench exercises explicitly.

The analog driver (`design/differential_driver.sch`) is a 60 µm PMOS /
30 µm NMOS output pair per leg into a fixed `rm1` series termination of
~36 Ω, nominally centred in the ratified 28–44 Ω window.

### 3.3 Receive path

`rxdp`/`rxdm` come from the analog front end: a differential receiver
(a 5T OTA followed by a CMOS buffer) recovering J/K, and two single-ended
receivers giving D+ and D− high/low independently. The digital side decodes
`LineState[1:0]` (J/K/SE0/SE1) combinationally, searches for the SYNC
pattern to acquire bit lock, then NRZI-decodes, destuffs (flagging seven
consecutive 1s as `RxError`), and deserializes into `DataIn[7:0]`/`RxValid`,
with `RxActive` asserted between SYNC lock and EOP. SE0 held for two bit
times is EOP; SE0 held for ≥ 2.5 µs is a bus reset.

### 3.4 D+ pull-up

A trimmed 1.5 kΩ pull-up from `VPU_REG` to D+, enabled by `pu_en`. The trim
is a 5-bit ladder (`pu_trim[4:0]`, ~3.2 % per step). Untrimmed, the resistor
spans 1722–2572 Ω across the 45-corner grid — nowhere near ±5 %. With **one
code chosen per die at 27 °C / 3.30 V and then held fixed** across that
die's whole temperature and supply range, every process corner lands within
1472–1530 Ω, inside the ratified 1425–1575 Ω window, worst-case error 2.01 %.
That is the mechanism spec §5 anticipated when it recorded that a bare
untrimmed resistor would not make the tolerance, and the fixed-code
requirement is checked by its own analysis script
(`sim/dplus-pullup-tolerance/analyze_fixed_trim.py`) rather than inferred
from the per-corner best codes — because a per-corner re-trim is not
something a shipped part can do.

---

## 4. Target specification

**Every row below is re-derived directly from this repository's own
`sim/` and `verification/` records, cited per row.** The analog rows come
from the 45-corner PVT matrix of spec §8.1 (5 process corners `tt`/`ff`/
`ss`/`fs`/`sf` × 3 temperatures −40/27/125 °C × 3 supplies 2.97/3.30/
3.63 V) — no row below is a subset of that matrix. **No spec limit was
relaxed to make any row pass**; four rows fail and are reported as failures
with their offending corners.

`sim/spec-coverage.md` is the index from spec §8.2's rows to these records
and is the authority if this table and it ever disagree.

| # | Parameter | Min | Typ (`tt`/27 °C/3.30 V) | Max | Ratified limit | Binding corner | Citation | Verdict at 3.3 V | Verdict at 5.0 V analog rail |
|---|---|---|---|---|---|---|---|---|---|
| A | Driver rise time, 10–90 % into 50 pF | 10.82 ns | 15.13 ns | 22.33 ns | 4–20 ns (spec §6) | max: `ss`/125 °C/2.97 V; min: `ff`/−40 °C/3.63 V | `sim/driver-signal-quality/`, record `20260817-203552-a408cb6` | **Unmet** — 3 of 45 corners exceed 20 ns (`ss_125c_2.97v` 22.33, `fs_125c_2.97v` 20.92, `ss_125c_3.30v` 20.79). Nominal has 25 % margin; the slow/hot/low corner loses it. The 4 ns floor is never approached. | **Unmet/TBD — no analog record above 3.63 V** (§2.5) |
| B | Driver fall time, 10–90 % into 50 pF | 9.59 ns | 12.98 ns | 19.27 ns | 4–20 ns (spec §6) | same as Row A | same | **Met** 45/45 | **Unmet/TBD — no record above 3.63 V** |
| C | Rise/fall matching, `t_rise`/`t_fall` | 0.979 | 1.165 | 1.402 | within 10 % of each other, i.e. 0.90–1.10 (spec §6) | min: `sf`/125 °C/3.63 V; max: `fs`/−40 °C/2.97 V | same | **Unmet — 36 of 45 corners outside the window.** The dominant failure. The output stage's 60 µm PMOS / 30 µm NMOS pair makes pull-up systematically weaker than pull-down once mobility is accounted for; `fs` (fast NMOS / slow PMOS) is worst and `sf` is the only family inside the window. A device-sizing result, not a measurement artifact. | **Unmet/TBD — no record above 3.63 V**; a supply change does not fix a mobility-ratio asymmetry |
| D | Output crossover voltage | 1.293 V | 1.602 V | 1.941 V | 1.3–2.0 V (spec §6) | min: `fs`/27 °C/2.97 V; max: `sf`/−40 °C/3.63 V | same | **Unmet — 2 of 45 corners below 1.3 V** (`fs_27c_2.97v` 1.2935 V, `fs_-40c_2.97v` 1.2968 V), both a few millivolts under, both on the same fast-NMOS/slow-PMOS/low-supply corner as Row C. Every other corner is comfortably inside. | **Unmet/TBD — no record above 3.63 V** |
| E | Differential receiver input-referred threshold, common mode 0.8 V / 1.65 V / 2.5 V | −79 / −89 / −500 mV | −52 / −59 / −355 mV | −32 / −36 / −60 mV | \|D+ − D−\| > 200 mV over 0.8–2.5 V common mode (spec §4) | worst: 2.5 V common-mode point | `sim/diff-receiver-sensitivity/`, record `20260817-203852-5a963e7` | **Partly unmet.** At 0.8 V and 1.65 V common mode the threshold stays within −89…−32 mV, comfortably inside ±200 mV: **45/45 pass**. At 2.5 V it degrades to −60…−500 mV and **30 of 45 corners** read a K state (−200 mV) as a J. Mechanism: the 5T OTA's output common mode sits near VDD − \|V_GS,p\|, above the following buffer's trip point, and the loop gain available to overcome that collapses as the input common mode approaches the rail. (−500 mV entries are the sweep's saturating floor: "at least this bad".) The 0.8–2.5 V range is ratified, so this is a real receiver gap. | **Unmet/TBD** — and note a higher rail *raises* the buffer trip point this row is already losing to |
| F | D+ pull-up resistance, trimmed | 1472.4 Ω | 1486.6 Ω | 1530.1 Ω | 1.5 kΩ ±5 % = 1425–1575 Ω (spec §5) | worst: `ss`, code 26 (2.01 %) | `sim/dplus-pullup-tolerance/`, record `20260817-203609-a408cb6`, plus `sim/dplus-pullup-tolerance/analyze_fixed_trim.py` over the same recorded logs | **Met**, and met under the *realistic* calibration model: **one trim code chosen per die at 27 °C / 3.30 V, then held fixed** across that die's whole temperature and supply grid, stays inside ±5 % for every process corner — worst 2.01 % (`ss`, code 26), best 1.38 % (`ff`, code 7). That is a stronger claim than a per-corner re-trim, which no production part could do. **Untrimmed** the same resistor spans 1722–2572 Ω across the grid, i.e. misses badly — so the trim ladder is a requirement, not a refinement, and it is exposed as `pu_trim[4:0]` (§2.2) for exactly that reason. | **Unmet/TBD — no record above 3.63 V** |
| G | Pull-up rail `VPU_REG` | 2.97 V | 3.30 V | 3.63 V | 3.0–3.6 V regulated (spec §5) | min: any 2.97 V corner | spec §5; §2.5 of this document | **Unmet at the low supply corner** if `VPU_REG` is tied to a 3.3 V ±10 % `VDDA`, as §2.5 proposes: 2.97 V is below the ratified 3.00 V floor, and 3.63 V is above the 3.60 V ceiling. A regulation element, or a tighter supply spec from the harness, is required. Stated rather than rounded. | **Unmet** — a 5.0 V rail is further outside the window, not closer to it |
| H | Single-ended receiver threshold (D+ and D−, identical circuits) | 1.203 V | 1.355 V | 1.506 V | VIH > 2.0 V, VIL < 0.8 V (spec §4) — i.e. the trip point must lie between them | min: `ff`/125 °C/2.97 V; max: `ss`/−40 °C/3.63 V | `sim/se-receiver-dp-thresholds/` record `20260817-203631-a408cb6`; `sim/se-receiver-dm-thresholds/` record `20260817-203654-a408cb6` | **Met 45/45** on both receivers. Output is a hard rail at both VIL and VIH at every corner. | **Unmet/TBD — no record above 3.63 V** |
| I | Digital section maximum clock frequency (`fmax`) | — | 68.53 MHz @ `tt_025C_1v80` | — | must exceed the 12 MHz UTMI interface clock (spec §3) | worst setup slack 47.29 ns @ `ss_125C_1v62`; worst hold 0.383 ns @ `ff_n40C_5v50` | `verification/records/place-and-route/records/20260825-224709-6a83263.md` | **Met** — 5.7× the required rate, 0 setup / 0 hold / 0 antenna / 0 router-DRC violations. | **Met.** Uniquely among these rows: the standard-cell library `gf180mcu_fd_sc_mcu9t5v0` is a 5 V-capable library and the P&R run's own multi-corner STA covers `4v50`/`5v00`/`5v50` as well as `3v00`/`3v30`/`3v60`. Every one of the 15 corners is positive on setup and hold. At `tt_025C_3v30`: 77.73 ns setup / 0.886 ns hold. At `tt_025C_5v00`: 79.36 ns setup / 0.613 ns hold. |
| J | Driver propagation delay and data-dependent jitter | 5.36 ns | 7.05 ns | 10.10 ns | **none** — spec §8.2 records that this repo has no confirmed numeric USB 2.0 source-jitter limits from the physical specification text and forbids inventing them | min: `ff`/−40 °C/3.63 V; max: `ss`/125 °C/2.97 V | `sim/driver-jitter/`, record `20260817-203915-5a963e7` | **No pass/fail claimed, by design.** Corner-to-corner propagation-delay spread is 4.74 ns. Data-dependent jitter within one corner, over an 18-bit 12 Mbps pattern with run lengths 1,1,2,1,3,1,6,1,2, is ≤ 2.53 ps peak-to-peak consecutive-transition and ≤ 1.33 ps against the ideal bit grid — ~3 × 10⁻⁵ UI at an 83.33 ns bit time, i.e. at the transient solver's own resolution floor. Read as "below the noise of this measurement". | **Unmet/TBD — no record above 3.63 V** |
| K | Digital UTMI logic functional correctness | — | — | — | spec §11: bit-exact against NRZI / bit-stuffing / SYNC / EOP / line-state behaviour, by cocotb testbench | n/a | `verification/records/bit-codec-functional/` (record `20260817-212707-6c7f7ff`), `verification/records/utmi-framing-functional/` (record `20260818-025302-ea10f21`) | **Met.** Bit-exact against an independently-written Python golden model, plus TX→wire→RX loopback including the trailing-stuff-bit case, back-to-back packets at minimum gap, and a malformed-SYNC case that must never assert `RxActive`/`RxValid`. | Rail-independent (a functional claim, not an electrical one) |
| L | DRC | — | 0 violations | — | spec §11: clean before signoff | n/a | `verification/records/digital-drc/records/20260825-224815-6a83263.md` | **Met for the digital half** — `klt drc --deck gf180mcu` reports `status: "clean"`, `violation_count: 0` against `layout/digital/usb_utmi_phy.gds`. **Unmet for the analog half: no analog GDS exists** (§5). | Rail-independent |
| M | LVS | — | match, 0 mismatches | — | spec §11: clean before signoff | n/a | `verification/records/digital-lvs/records/20260825-224930-6a83263.md` | **Met for the digital half** — gate-level LVS of the routed GDS against the as-built netlist is a match, with a passing negative control. **Unmet for the analog half: no analog GDS exists.** | Rail-independent |
| N | Post-layout (extracted-parasitic) PVT simulation | — | — | — | spec §11 (implied by "verified by simulation" once a layout exists) | n/a | `verification/records/post-layout-pvt/records/20260825-233200-1c84648.md` (digital half only) | **Unmet.** Every electrical row above is still measured against the **schematic** netlist under `design/netlist/`, not an extracted one — there is no analog layout to extract (re-measured, still blocked, under
issue #52; tracked onward at klayout-tools#1424 and gf180-usb2-phy#56).
Row I now has a first post-layout attempt: a SPEF-annotated `klt sta` re-run at three corners against the committed digital layout, moving worst setup slack by +0.22 to +2.96 ns versus the liberty/estimated-RC numbers Row I cites. That attempt's own parasitic annotation is incomplete (186 of 366 design nets), root-caused to a `klt sta` net-name-correlation defect (klayout-tools#1422) rather than to the extraction itself — so it does not change Row I's verdict and does not make this row **Met**. | Same |

### Summary of verdicts

**Met:** Rows B, F (conditional on per-part trim), H, I (at both 3.3 V and
5.0 V), K, L and M (digital half).
**Unmet:** Rows A, C, D, E, G, N, and the analog half of L and M.
**Deliberately unjudged:** Row J.

Rows C and E are the two that would change the design rather than the
document: C is a driver output-stage sizing problem and E is a differential
receiver topology problem at the top of the common-mode range. Neither is
fixed by anything in this proposal, and neither is hidden by it.

---

## 5. Physical status

**Digital — at the sign-off bar.** `layout/digital/usb_utmi_phy.gds` is the
real PHY digital logic (`rtl/usb_utmi_phy.v` and all seven submodules),
synthesized with Yosys and placed-and-routed with OpenROAD against
`gf180mcu_fd_sc_mcu9t5v0`, both driven through committed request files
(`flow/`) rather than ad-hoc commands. 342 mapped cells become 1206 placed
instances after tapcell, PDN and filler insertion, in a 37 937 µm²
(~195 µm × 195 µm) core-only die at 44 % utilization. It is DRC-clean (Row
L) and LVS-matched (Row M).

**Analog — no layout.** No GDS is committed for
`differential_driver`, `differential_receiver`, `dplus_pullup`,
`se_receiver_dm` or `se_receiver_dp`. This is a measured result, not an
untried assumption: the attempt is committed, re-runnable
(`scripts/gen_analog_layout.py`) and its raw output frozen under
`verification/records/analog-layout/`. Issue #52 re-measured it against a
newer `klt` pin advanced to consume three friction fixes this repo had
filed (all closed upstream): the routing capability those fixes add
(block orientation, a two-layer bus role) exists but is opt-in and unused
by the committed plans, so the same three blocks still place but route
**0 of their nets** — and are now DRC-**violating** rather than clean, a
regression in the tool's own partial-route geometry filed as
klayout-tools#1424. The other two blocks still cannot be ingested by the
layout-plan compiler at all, one of which (`dplus_pullup`) now has its
path forward tracked as an explicit maintainer decision at
gf180-usb2-phy#56. `layout/README.md` § "Analog" gives the full per-block
outcome. A block of placed devices with none of its nets wired is not a
layout and is not committed as one.

**What that means for this proposal.** A Chipalooza submission is expected
to reach DRC/LVS-clean GDS with post-layout PVT simulation. This block is
there for its digital half and is not there for its analog half. That is
stated here as the current status, with the work it implies named in §7,
rather than presented as a formality remaining.

---

## 6. Test-plan outline

### 6.1 Bench setup

The packaged part is measured on a daughterboard mated to the
Chipalooza/Wafer.Space test board, with a **USB receptacle wired to the
`DP`/`DM` dedicated pads** through a controlled-impedance differential pair
as short as the board allows — that connector is what makes the interesting
half of this plan possible. Minimum instrumentation: a programmable supply
for `VDDA` (independently of the digital rail, per §2.5); a 12 MHz clock
source for `clk`; a logic analyzer or FPGA capture fabric wide enough for
the 12 digital test outputs and the 23 control inputs; a ≥ 500 MHz
differential-capable oscilloscope on `DP`/`DM` with a defined 50 pF load
fixture for Rows A–D; a real USB host; and a thermal chamber or hot/cold
plate for any point beyond bench ambient, since every simulated row spans
−40…+125 °C.

### 6.2 Per-row bring-up and closure plan

1. **Power-on / reset smoke test.** Assert then release `rst_n` with
   `pu_en` low and confirm every test output takes its documented reset
   value and `DP`/`DM` sit at SE0. First go/no-go gate.
2. **Pull-up trim sweep (Rows F, G).** With `pu_en` high and no host
   attached, sweep `pu_trim[4:0]` across all 32 codes and measure the D+
   pull-up resistance at each, across `VDDA` and temperature. This
   measures the *untrimmed* spread (1722–2572 Ω in simulation) separately
   from the *fixed-code-per-die* result (1472–1530 Ω), which is exactly the
   distinction Row F depends on: pick the code once at 27 °C / 3.30 V, then
   hold it while temperature and supply move, and check it never leaves
   ±5 %. It also directly checks the `VPU_REG` window of Row G on a real
   rail.
3. **Driver signal quality (Rows A, B, C, D).** Drive a known pattern
   through `DataOut`/`TxValid`, capture `DP`/`DM` into the 50 pF fixture,
   and measure rise time, fall time, their ratio, and crossover voltage
   against the per-corner tables in the `sim/driver-signal-quality/`
   record. **This is the step that settles Rows A/C/D** — all three fail in
   simulation, all three are sizing/topology-sensitive, and all three are
   exactly the kind of claim a scope on a real load resolves better than a
   corner model does.
4. **Differential receiver common-mode sweep (Row E).** Drive `DP`/`DM`
   externally with a controlled differential amplitude on a swept common
   mode from 0.8 V to 2.5 V and find the amplitude at which `DataIn`/
   `RxValid` stop tracking. Row E predicts clean behaviour up to ~1.65 V
   and failure approaching 2.5 V; measuring where the real part gives up is
   the single most useful number this block can bring back from silicon.
5. **Real enumeration against a real host (Rows K, and the system-level
   claim no simulation makes).** Attach the receptacle to a USB host with a
   minimal SIE driving the UTMI pins (an FPGA on the daughterboard), toggle
   `pu_en` to force detach/attach, and confirm the host detects a
   full-speed device and completes a `GET_DESCRIPTOR` exchange. The SIE is
   deliberately outside this block (§3.1); the point of this step is that
   the *PHY* survives contact with a real host's timing, cable and
   terminations.
6. **Bus-reset and line-state behaviour (Row K, second half).** Have the
   host issue a bus reset (SE0 ≥ 2.5 µs) and confirm the block's reset
   detection fires; observe `LineState` on the scope at `DP`/`DM` per §2.3.
7. **Jitter and propagation delay (Row J).** Measure edge-to-edge timing on
   `DP` over a long pseudorandom pattern and compare against the 4.74 ns
   corner spread and the sub-picosecond data-dependent jitter in the
   `sim/driver-jitter/` record. Recorded as engineering data — Row J has no
   spec limit attached and will not acquire one on the bench.

### 6.3 What silicon cannot close

Rows L, M and N are pre-tapeout obligations, not bench measurements: a part
cannot be fabricated to *discover* whether its analog layout is DRC-clean.
They are named in §7.

---

## 7. Work remaining before this block meets the brief

Listed honestly, in the order it gates:

1. **Analog layout for all five blocks**, then DRC and LVS on each. Blocked
   today on real tool limitations documented in
   `verification/records/analog-layout/` and filed upstream, not on design
   intent.
2. **Post-layout (extracted-parasitic) PVT re-verification** of every Row
   A–H measurement (blocked on item 1). The digital section's timing (Row
   N) has a first attempt —
   `verification/records/post-layout-pvt/records/20260825-233200-1c84648.md`
   — but its parasitic annotation is incomplete (a `klt sta` correlation
   defect, klayout-tools#1422, not a design gap), so completing it is a
   remaining item, not a closed one: either wait on the upstream fix, or
   root-cause a workaround.
3. **Row C — driver rise/fall matching.** A device-sizing pass on the output
   stage; 36 of 45 corners currently fail.
4. **Row E — differential receiver at high common mode.** A topology change
   (the output common mode of the OTA versus the following buffer's trip
   point), not a sizing tweak; 30 of 45 corners currently fail.
5. **Rows A and D** are the same asymmetry as Row C seen at the slow/hot and
   the `fs` corners respectively; a Row C fix is expected to move both, but
   that expectation is not evidence and would be re-measured.
6. **Row G — `VPU_REG` regulation**, or a narrower supply guarantee.
7. **The test-chip wrapper RTL** of §2.7.
8. **A 5.0 V answer for the analog front end** (§2.5), if the program
   requires that rail.

---

## Program compliance notes

- **License.** This repository is [Apache-2.0](../../LICENSE), one of the
  program's named acceptable licenses, with every modifiable source —
  schematics, netlists, RTL, testbenches, evidence records, layout — public
  in this same repository.
- **Open-source EDA flow, end to end.** Schematics: xschem. Analog
  simulation: ngspice (≥ 46) against the gf180mcu open PDK, installable via
  [volare](https://github.com/efabless/volare) or
  [ciel](https://github.com/fossi-foundation/ciel), driven by
  `sim/run_corners.py`. Digital functional verification: cocotb + Icarus via
  `klt functional-verification`. Synthesis: Yosys via `klt synthesize`.
  Place and route: OpenROAD via `klt place-and-route` (the pinned
  `openroad/orfs` image). DRC / extraction / LVS: KLayout via `klt drc` /
  `klt extract` / `klt lvs`. Everything above runs from this repository's own
  committed scripts and request files, with no proprietary tool anywhere in
  the loop.
- **Reproducibility.** Every number in §4 traces to an append-only evidence
  record under `sim/*/records/` or `verification/records/`, each carrying the
  tool versions, the resolved PDK version, and content hashes of every input
  the claim depends on. `verification/check_records.py` fails the build if a
  record's inputs have changed since it was minted.
- **Disclosure.** This repository is public. Nothing in this document
  discloses anything beyond what is already committed to it, and no wording
  about the organization that maintains this repository appears here or
  belongs here.
