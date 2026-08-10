# USB 2.0 device PHY — target specification

**Status: Ratified 2026-08-10** (issue #1). This document is the
authoritative spec for this repo. `README.md` points here instead of
duplicating values; the DRAFT table that previously lived in `README.md`
under "Target specification (DRAFT — engineering to ratify, see issue #1)"
is superseded by this document.

Source of truth for every hard number below is the USB Implementers Forum's
*Universal Serial Bus Specification, Revision 2.0* (frozen since April 2000),
Chapter 7 ("Electrical"). Section citations follow the numbering the issue
itself specified for driver characteristics (**§7.3.2**) and, elsewhere, the
numbering this repo's own reading of the standard Chapter 7 structure
produces. **This ratification was performed from well-established,
widely-documented USB 2.0 full-speed electrical/timing knowledge, not from a
live read of the physical specification PDF** — every section/table citation
below should be spot-checked against the physical specification text before
a verification record is allowed to quote pass/fail against it as a legal
citation rather than an engineering target. Numeric values that carry real
uncertainty are flagged inline rather than stated as if confirmed; see
§9 (References) for the honesty note this implies for the whole document.

## 1. Scope

This spec covers the **entire PHY block** built in this repo: the
differential and single-ended receivers, the differential driver and D+
pull-up, and the digital encode/decode logic that turns wire-level
signaling into a byte stream at a UTMI interface. Unlike `sky130-usb2-phy`
(a sibling that splits UTMI-side digital logic and analog sub-blocks across
separate canary repos), this repo is **one self-contained block** — see
§2 for exactly where its boundary is drawn and CLAUDE.md for why that
boundary is not inherited from the sibling.

**Explicitly out of scope for this ratification** (per issue #1's own "Out
of scope for ratification" section — a scope change to include any of these
requires its own decision record, not a spec row here):

- **High-speed (480 Mbps) operation.** Full-speed (12 Mbps) is the only
  signaling rate this block targets. HS is not a stretch goal — it is a
  substantially harder analog problem (current-mode drivers, HS squelch,
  chirp handshake, elastic buffering) that nothing motivating this block
  needs.
- **Host or OTG capability.** This block is a device (peripheral) PHY only.
  No role switching, no session-request/host-negotiation protocol (SRP/HNP),
  no VBUS session valid comparators used only by a host/OTG A-device.
- **The serial interface engine (SIE) above UTMI.** Endpoints, CRC-5/CRC-16,
  enumeration, and packet handling belong to whatever digital design
  integrates this PHY, not to this repo.

## 2. Where the UTMI boundary falls

**Decision: NRZI encode/decode, bit stuffing/destuffing, and SYNC/EOP
handling are INSIDE this block.**

UTMI (as defined by the UTMI/UTMI+ specification from the USB-IF, not the
Chapter-7 USB 2.0 spec itself) places the PHY/link boundary *above* NRZI
encoding and bit stuffing — a UTMI-compliant PHY hands the link layer
already-decoded `DataIn[7:0]` bytes with `RxActive`/`RxValid`/`RxError`
status, not raw NRZI bits. This is the conventional and, for a device
targeting an off-the-shelf digital link/SIE integration, the only sensible
place to draw the line: NRZI/bit-stuffing/SYNC-EOP handling has zero
protocol-layer meaning (no endpoints, no CRC, no enumeration state) and is
identical for every USB full-speed device regardless of what SIE sits above
it. Putting it in this block, rather than pushing it into the integrator's
SIE, is exactly what "digital interface: UTMI" in the README's draft table
already implied — this section makes that implication explicit and binding,
per issue #1's own instruction to "say so explicitly, so the integrator
knows what they are getting."

Concretely, **inside this block**:

- Differential and single-ended receiver front ends (§4)
- Differential driver and D+ pull-up (§3, §5)
- NRZI encode (TX) / decode (RX)
- Bit stuffing (TX, after every six consecutive 1s) / bit destuffing (RX)
- SYNC field generation (TX) / SYNC detection and bit-lock (RX)
- EOP (Single-Ended Zero, SE0) generation (TX) and detection (RX)
- Line-state reporting (`LineState[1:0]`: J/K/SE0/SE1) for reset, suspend,
  resume, and disconnect detection at the UTMI boundary

**Outside this block** (the SIE, per CLAUDE.md's scope-discipline rule and
issue #1's "Out of scope" section):

- PID (packet ID) interpretation
- CRC5 (token) / CRC16 (data) generation and checking
- Endpoint/address matching, enumeration state machine
- Any USB protocol semantics above raw byte-stream + line-state signaling

## 3. Digital interface: UTMI

| Parameter | Ratified value |
|---|---|
| Interface | **UTMI** |
| Data bus width | 8 bits, parallel |
| Interface clock | 12 MHz (native FS bit rate; see engineering note below) |
| Core TX signals | `TxValid`, `TxReady`, `DataOut[7:0]` |
| Core RX signals | `RxValid`, `RxActive`, `RxError`, `DataIn[7:0]` |
| Status/control signals | `LineState[1:0]`, `OpMode[1:0]`, `TermSelect`, `XcvrSelect`, `SuspendM`, `Reset` |

**Decision: UTMI, not UTMI+ — the README draft's "UTMI+ subset" Stretch
entry is dropped, not carried forward.** UTMI+'s incremental signaling over
UTMI exists to support two things this block explicitly excludes: HS chirp
handshake / link power-state management, and OTG session-request signaling.
Neither applies to a device-only, full-speed-only PHY. Carrying a "UTMI+
subset" stretch goal forward would misstate the block's own scope discipline
(§1) as still-open, so it is removed rather than merely left unimplemented.

**Engineering note on interface clock, flagged as needing a follow-on
decision, not silently assumed:** a canonical full-speed-only UTMI PHY can
run its parallel interface at the raw 12 MHz bit rate (byte-wide, one byte
per ~8 bit periods) rather than the 30 MHz a dual FS/HS-capable UTMI
interface conventionally uses (which exists to serve HS's higher internal
sample rate, not FS). Because this block is FS-only, 30 MHz is not required
by anything in this spec; 12 MHz is stated here as the ratified target
because it is what an FS-only implementation needs and nothing forces a
higher rate. If the integrating SIE's own clocking constraints later require
a different rate, that is a follow-on decision for the integration, not a
re-opening of this ratification.

## 4. Receiver set

**Decision: confirmed as drafted — a differential receiver plus two
single-ended receivers, needed for SE0/idle and reset detection.** This is
the standard USB 2.0 device-side receiver complement; nothing about this
block's scope changes it.

| Receiver | Function | Threshold | Basis |
|---|---|---|---|
| Differential receiver | Recovers D+/D− differential data (J/K states) | Differential input sensitivity \|(D+) − (D−)\| > 200 mV, over a common-mode input range of 0.8–2.5 V | USB 2.0 Table 7-2 / §7.1 receiver electrical characteristics (**flagged: verify exact section number against physical text**) |
| Single-ended receiver on D+ | Detects D+ high/low independent of D− | VIH > 2.0 V, VIL < 0.8 V | Standard TTL-compatible single-ended threshold used for SE0/idle/reset detection |
| Single-ended receiver on D− | Detects D− high/low independent of D+ | VIH > 2.0 V, VIL < 0.8 V | Same as above |

The two single-ended receivers, combined, give the line-state decode
(`LineState[1:0]` in §3) that the digital logic uses to detect: **idle** (D+
high / D− low for an FS device, i.e. J state, given the 1.5 kΩ D+ pull-up of
§5), **SE0** (both low — reset if held ≥ 2.5 µs per USB 2.0 §7.1.7.5, EOP if
held for 2 bit times), and **disconnect** (this repo does not build the
host-side envelope/squelch disconnect detector — disconnect detection is a
host/OTG A-device responsibility per §1's scope exclusion, not a device-side
one).

Squelch/envelope detection (the HS-style differential-envelope comparator)
is **not** part of this receiver set: it exists in USB 2.0 primarily to
serve high-speed signal-loss and host-side disconnect detection, both
excluded by §1.

## 5. D+ pull-up

**Decision: 1.5 kΩ, integrated, enable-controlled — confirmed, with an
explicit PVT-tolerance caveat flagged for the analog design phase.**

| Parameter | Ratified value | Basis |
|---|---|---|
| Nominal resistance | 1.5 kΩ | USB 2.0 speed-signaling pull-up, standard FS device value |
| Tolerance | ±5% (1.425–1.575 kΩ) across the full PVT envelope of §7 | USB 2.0 pull-up tolerance requirement (**flagged: verify exact tolerance figure against physical Table 7-2 text — this repo's draft carried ±5% from memory and it is not independently re-derived here**) |
| Pull-up rail | Internally regulated, 3.0–3.6 V | USB 2.0 speed-signaling requirement — the pull-up must present a valid VOH at the connector, not simply tie to the raw 3.3 V supply rail without regard to its tolerance |
| Integration | **Integrated** (not external) | See rationale below |
| Enable control | **Enable-controlled**, digital input from the UTMI-side logic (soft-connect) | Lets an integrator force a re-enumeration by toggling the pull-up, and is required for standard soft-disconnect/reset sequencing |

**Rationale for integrated vs. external:** an external 1.5 kΩ resistor
avoids any PVT-tolerance risk entirely, at the cost of a mandatory external
component and a dedicated pad the integrator cannot omit. Integrated is the
better block for this repo's purpose (a canary block should minimize what
the integrator must additionally provide) — the tolerance question is real,
but it is a solvable analog design problem, not a reason to punt the pull-up
external. gf180mcu poly and diffusion resistors are not inherently ±5%
across process on their own (unassisted process spread on unsalicided poly
in comparable open PDKs commonly runs well outside ±5%, before trim) — so
**meeting the ±5% (or whatever the physical spec text confirms) tolerance
requires either a trimmed/calibrated resistor (e.g., a binary-weighted
trim ladder set at test) or an active regulation scheme (a resistor value
combined with a servo/reference that holds the effective pull-up impedance
in range across corners), not a bare untrimmed resistor.** This spec does
not choose between those two circuit-level approaches — that is
implementation work for whichever design pass builds the pull-up — but it
records the requirement explicitly so that design pass does not discover
the PVT problem late: **the ±5% pull-up tolerance is a verified claim this
block must earn with PVT-corner simulation evidence (§7), not an assumption
carried from the README draft unexamined.**

**Enable control, decision:** enable-controlled, confirmed. This lets an
integrator drive a soft-disconnect (pull-up disabled, forcing the host to
see a device removal) followed by a soft-connect (pull-up re-enabled),
which is the standard mechanism for forcing re-enumeration without a
physical cable cycle — useful for firmware update flows and is effectively
free to add (one digital enable input) relative to the value it provides.

## 6. Driver characteristics

**Decision: confirmed as drafted, citing USB 2.0 §7.3.2 as directed by
issue #1** ("§7.3.2 for driver characteristics is the section that matters
most here" — this repo defers to that citation as given rather than
re-deriving a different section number from memory).

| Parameter | Ratified value | Basis |
|---|---|---|
| Rise time (10%–90%) | 4–20 ns | USB 2.0 §7.3.2, into the specified test load below |
| Fall time (10%–90%) | 4–20 ns | USB 2.0 §7.3.2, into the specified test load below |
| Rise/fall time matching | Within 10% of each other | USB 2.0 §7.3.2 driver characteristics — timing symmetry requirement (**flagged: confirm the exact matching percentage against physical text**) |
| Test load | 50 pF, into which rise/fall times above are measured | USB 2.0 Table 7-2 driver test-load capacitance (**flagged: confirm exact load value/tolerance against physical text — carried unchanged from the README draft**) |
| Output signal crossover voltage | 1.3–2.0 V | USB 2.0 §7.3.2 |
| Driver output resistance | 28–44 Ω (series termination, sets differential line impedance with cable) | Standard FS driver output impedance range consistent with USB 2.0 Chapter 7 driver electrical characteristics (**flagged: not itself in the README draft table — stated here as context for §7's verification method, not as a new ratified row**) |

No change from the README draft's numbers. This section exists to attach
the §7.3.2 citation explicitly (per issue #1) and to state the test load
condition as part of the ratified value rather than an implicit assumption.

## 7. Reference clock

**Decision: 12 MHz external crystal/resonator at ±0.25% tolerance,
confirmed. Crystal-less operation (SOF-trimmed) is explicitly OUT of
scope — not a stretch goal, dropped entirely.**

| Parameter | Ratified value | Basis |
|---|---|---|
| Reference input | 12 MHz external crystal/resonator | Standard FS device reference clock |
| Frequency tolerance | ±0.25% (2500 ppm), unsynchronized to host SOF | USB 2.0 full-speed data-rate tolerance (**flagged: standard, widely-cited figure — confirm exact section number, commonly cited as §7.1.11, against physical text; not independently verified from the primary source in this pass**) |

**Rationale for dropping crystal-less/SOF-trimmed operation, rather than
carrying it as a stretch:** issue #1 was explicit that this needs an
in-or-out call now, "because designing for it later is much harder than
designing for it now." Crystal-less operation trims an internal oscillator
against the host's periodic SOF packets — which means it requires SOF
*packet* recognition (PID decode, not just SYNC/line-state), a trim/DCO
control loop, and typically a wider internal timebase tolerance budget that
propagates into every other timing-derived spec in this document (bit
sampling window, jitter budget, EOP timing). Every one of those either
crosses the §1 SIE boundary (PID decode is explicitly out of scope for this
block) or would force every other section of this ratified spec to be
re-derived against a *variable* input clock tolerance instead of a fixed
±0.25% one. Given that this repo's whole premise is a deliberately narrow,
finishable block (CLAUDE.md), and crystal-less operation is a genuine
scope-*expanding* feature (more logic, a new control loop, a dependency the
integrator's SIE would need to expose SOF timing across the UTMI boundary
back into this block, which breaks the boundary just drawn in §2) rather
than a refinement of the existing scope, it is dropped rather than kept as
an aspirational row. A future scope change to add it would need its own
decision record, per issue #1's own instruction, not a spec row here.

## 8. What "verified" means at the block boundary

**Decision: the corner list is fixed below; the verified quantities are
rise/fall time into the specified load, crossover voltage, driver-output
jitter budget, and full-speed signal-quality (in place of a formal
USB-IF-style eye-pattern compliance mask, per the rationale below).**

### 8.1 PVT corner list (fixed)

| Axis | Points | Count |
|---|---|---|
| Temperature | −40 °C, 27 °C, 125 °C | 3 |
| Supply | 3.3 V − 10% (2.97 V), 3.3 V nominal, 3.3 V + 10% (3.63 V) | 3 |
| Process corner | `tt`, `ss`, `ff`, `fs`, `sf` (standard 5-corner gf180mcu process set, applied consistently to both the digital standard-cell timing corners and analog device corners) | 5 |
| **Total** | | **45 corners** |

This matches the fleet-wide PVT convention used by this repo's siblings
(gf180-bandgap, gf180-pll: "−40/27/125 °C, ±10% supply, process corners"),
adapted here to name the process-corner set explicitly since this repo's own
`CLAUDE.md` does not yet state it. Every electrical claim recorded against
this spec must carry this full 45-corner matrix, or explicitly state and
justify why a subset was used instead — the same append-only,
justify-a-subset convention `sim/README.md` will document once simulation
work begins.

### 8.2 What gets measured, and against which section

| Quantity | Verified against | Method |
|---|---|---|
| Rise/fall time | §6 (4–20 ns, into 50 pF) | Transient simulation at each of the 45 corners, driver output into the specified load |
| Crossover voltage | §6 (1.3–2.0 V) | Transient simulation, same runs as above |
| Driver-output timing jitter | Derived budget, see note below | Transient simulation, edge-to-edge timing variation across the corner set |
| Full-speed signal quality | §6 driver characteristics, checked as a set (rise/fall + crossover + monotonic single-zero-crossing transition) into the 50 pF load | Simulated waveform capture at each corner, checked against the numeric limits directly — **not** a formal USB-IF compliance eye-pattern mask overlay |
| D+ pull-up tolerance | §5 (±5% target) | DC/parametric analysis across the 45 corners |
| Receiver thresholds | §4 | DC/parametric analysis across the 45 corners |
| DRC / LVS | N/A — layout hygiene, not an electrical spec row | `klt drc` / `klt lvs`, clean required before signoff regardless of PVT |

**Decision, and the reasoning behind it: no formal eye-pattern compliance
mask.** The README draft's "eye diagram" entry is interpreted here as "the
driver's output signal quality, verified by simulation" rather than a
literal USB-IF Full-Speed Electrical Test Procedure eye-mask overlay. Two
reasons: first, the formal graphical eye-mask template with defined
geometry is, as best as this repo can determine without the physical
compliance document in hand, a USB-IF *compliance-testing* artifact rather
than a Chapter 7 numeric spec value, and this repo's own top-level README
already states "USB-IF compliance certification is out of scope... meeting
the electrical requirements in simulation is in scope; a certificate is a
different kind of artifact and this repo does not claim one." Second, the
numeric limits in §6 (rise/fall, crossover voltage, load) are themselves
sufficient to bound the same waveform shape an eye-mask would check, for
the purposes of a simulation-only signoff. If a later verification pass
finds the numeric-limits method insufficient (e.g., a corner passes every
individual numeric limit but the waveform is visibly non-conformant in a
way none of those limits catch), that is a trigger to revisit this
decision with its own record — not a reason to invent an unverified mask
geometry now.

**Jitter budget, stated honestly as a derived — not literally
spec-quoted — number, same honesty convention `sky130-usb2-phy` used for
its own PLL jitter budget:** USB 2.0 full-speed does define paired- and
consecutive-transition source-jitter limits somewhere in Chapter 7 (commonly
cited around §7.1.13–§7.1.15, covering "differential data-to-SE0" and
in-band transition jitter) — **this repo does not have confirmed exact
numeric values for those limits from the physical text**, and rather than
inventing plausible-sounding nanosecond figures, this document flags them
as an open item: the jitter budget verified against this spec must be
**pulled verbatim from the physical USB 2.0 specification text** (Chapter 7,
source-jitter tables) before any `sim/` record is allowed to claim a
pass/fail against a specific number. Until that pull happens, `sim/` may
record measured jitter as engineering data without a spec citation attached.

## 9. Supply

**Decision: confirmed, single 3.3 V supply, unchanged from the README
draft.**

| Rail | Voltage | Basis |
|---|---|---|
| Supply (single rail, both digital UTMI-side logic and analog front end) | 3.3 V | gf180mcu 3.3 V-class device flavor; matches USB FS driver/receiver voltage range (VOH 2.8–3.6 V with a pull-up regulated to 3.0–3.6 V, receiver common-mode 0.8–2.5 V) with margin |

**Rationale for a single rail (no split digital-core / analog-I/O rail, as
`sky130-usb2-phy` uses):** this block's digital logic (§2 — NRZI, bit
stuffing, line-state decode) is small relative to a full SIE, and gf180mcu
offers a 3.3 V-class standard-cell library suitable for that amount of
logic without requiring a separate lower-voltage core rail or the
level-shifters a split rail would need at the digital/analog seam. A single
3.3 V rail keeps the block self-contained (no second regulator/LDO
dependency handed to the integrator) and is the simpler, FS-optimal choice
per CLAUDE.md's general rule ("take the full-speed-optimal choice"). If the
digital logic later grows enough that a lower-voltage core rail becomes
worth its area/power savings, that is a follow-on decision, not a
retroactive change to this ratification.

## 10. Role and signaling rate

**Decision: both confirmed unchanged from the README draft.**

| Parameter | Ratified value |
|---|---|
| Role | Device (peripheral) only — no host, no OTG, no role switching |
| Signaling rate | Full-speed, 12 Mbps only — high-speed (480 Mbps) is explicitly out of scope (§1), not a stretch goal |

## 11. Signoff

**Decision: confirmed, restated precisely against §8.**

Signoff for this block requires:

- DRC and LVS clean (`klt drc` / `klt lvs`)
- §6's driver characteristics (rise/fall, crossover voltage) verified by
  simulation across the full 45-corner PVT matrix of §8.1, into the 50 pF
  test load
- §5's D+ pull-up tolerance verified by simulation across the same matrix
- §4's receiver thresholds verified by simulation across the same matrix
- A recorded jitter budget once the §8.2 open item (exact USB 2.0 §7.1.13–15
  numeric limits) is resolved against the physical specification text
- Digital UTMI-side logic (§2) verified by a cocotb testbench, bit-exact
  against NRZI/bit-stuffing/SYNC/EOP/line-state behavior — the same
  bit-exact-UTMI-level floor `sky130-usb2-phy` set for its own digital half

## 12. Decision log summary

Every README draft row, resolved:

| Row | Outcome | Section |
|---|---|---|
| Role | Confirmed unchanged | §10 |
| Signaling rate | Confirmed unchanged | §10 |
| Digital interface | **Changed**: UTMI+ subset stretch dropped; UTMI confirmed; interface clock set to 12 MHz (was unstated in draft) with a flagged follow-on note | §3 |
| Supply | Confirmed unchanged, rationale for single-rail choice now recorded | §9 |
| D+ pull-up | Confirmed integrated + enable-controlled; **PVT-tolerance mechanism flagged as an open circuit-level decision**, not silently assumed achievable | §5 |
| Driver rise/fall | Confirmed unchanged, §7.3.2 citation attached per issue #1 | §6 |
| Crossover voltage | Confirmed unchanged, §7.3.2 citation attached | §6 |
| Reference clock | Confirmed 12 MHz ±0.25%; **crystal-less/SOF-trimmed stretch explicitly dropped** (not carried forward) | §7 |
| Receiver | Confirmed unchanged, thresholds now stated explicitly | §4 |
| Signoff | Confirmed, PVT corner list now fixed (was unstated in draft) | §8, §11 |

## 13. References

- USB Implementers Forum, *Universal Serial Bus Specification, Revision
  2.0*, April 2000 — Chapter 7 ("Electrical"). §7.3.2 (driver
  characteristics) is cited as directed by issue #1's own text; other
  section numbers in this document (§7.1.7.5 reset timing, §7.1.11 frequency
  tolerance, §7.1.13–§7.1.15 source jitter, Table 7-2 DC electrical
  characteristics) follow this repo's best current understanding of the
  standard Chapter 7 structure and are **explicitly flagged throughout this
  document as needing a spot-check against the physical specification text**
  — this ratification was performed without direct access to that text in
  this session (see the note under the document title). Every numeric value
  carried unresolved (the driver rise/fall matching percentage, the pull-up
  tolerance percentage, the source-jitter budget) is stated as an open item
  rather than an invented number, per this repo's own instruction not to
  transcribe from memory as if it were authority.
- [`sky130-usb2-phy`](https://github.com/2AMLogic/sky130-usb2-phy)'s
  [`spec/usb2-phy.md`](https://github.com/2AMLogic/sky130-usb2-phy/blob/main/spec/usb2-phy.md) —
  sibling repo's ratified spec, read for harness/reasoning patterns (jitter
  budget honesty convention, decision-log structure) per CLAUDE.md's
  instruction to copy patterns, not scope. Its numbers are **not** copied
  into this document except where independently confirmed appropriate for
  this repo's narrower (device-only, FS-only, single self-contained block)
  scope.
- `gf180-bandgap` and `gf180-pll` (sibling gf180mcu canary repos) — source
  of the fleet-wide PVT corner convention adapted in §8.1.
