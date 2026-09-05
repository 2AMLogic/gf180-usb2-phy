# design

xschem schematics (gf180mcu PDK) for the analog sub-blocks of this PHY.
Each cell is one `.sch` source under `design/`, plus a netlist derived from
it under `design/netlist/`.

This file is additive: each schematic-adding issue gets its own `##`
section below, named after the issue and the cell(s) it adds, so concurrent
PRs touching this file don't clobber each other's content on rebase/merge.
Do not restructure or remove another issue's section from this file.

## Toolchain notes (applies to every cell in this directory)

- **Regenerating a netlist**: `python3 design/netlist.py` (writes
  `design/netlist/<cell>.spice` for every `design/*.sch`).
  `python3 design/netlist.py --check` verifies the committed netlists are
  current and reproduce byte-for-byte. Both need `source sim/env.sh` first
  (PDK discovery) and a real `xschem`/`ngspice` on `PATH`.
- **Headless xschem, no DISPLAY/X11 needed**: `xschem -x -q -n -s -r
  --rcfile design/xschemrc -o <outdir> <cell>.sch` runs and netlists
  correctly with no X server at all (`-x` disables the Tk GUI) -- confirmed
  working in this repo's CI-equivalent environment. `design/netlist.py`
  uses exactly this invocation, ported from the equivalent script in
  `gf180-temp-por`/`gf180-bandgap` (CLAUDE.md's harness-bootstrap
  instruction).
- **No cross-cell hierarchy yet.** Every cell currently in `design/` is a
  flat leaf block (no cell instantiates another). A future PHY-level
  wrapper issue that changes this should extend `design/netlist.py`
  accordingly rather than reinvent it -- see that script's module
  docstring.

## Differential driver + D+ pull-up (issue #30)

Two transmit-side analog blocks, per `spec/usb2-device-phy.md` Sec.5 (D+
pull-up) and Sec.6 (differential driver). **Schematic capture only** at
this stage: both cells target the spec thresholds below *by design*, but
neither has been through a PVT-corner simulation pass -- that is
`spec/usb2-device-phy.md` Sec.8's job, tracked as issue #26, which depends
on these schematics existing. Nothing in this section is a verified claim;
each is flagged as design intent, consistent with `sim/README.md`'s
append-only evidence-record convention (a *verified* claim lives in
`sim/`, not here).

### `differential_driver.sch`

Two symmetric single-ended output stages (`DP` half, `DM` half), each:
small CMOS predriver -> poly gate-slew resistor -> large complementary
output stage -> `rm1` (metal1) series/termination resistor to the pad.
`TXDP`/`TXDM` are opaque digital inputs from the (out-of-scope, per
CLAUDE.md's "do not build the serial interface engine" rule) NRZI/encode
logic; this cell defines `TXDx=1` => `Dx` driven high.

Targets (spec Sec.6), by design intent:

| Parameter | Target | This cell's approach |
|---|---|---|
| Rise/fall time (10-90%) into 50pF | 4-20ns | `R_series` (36ohm nominal) x 50pF alone gives a ~4ns floor; `R_slew` (poly, ~4kohm) into the big output FET's gate cap adds a second RC stage so the edge lands mid-window instead of at the floor |
| Rise/fall matching | within 10% | Output stage `Wp:Wn = 2:1` (gf180mcu 3.3V mobility ratio), both edges driven from the *same* shared gate node so they see correlated RC delay |
| Crossover voltage | 1.3-2.0V | Balanced `Wp:Wn` centers the crossover near VDD/2 = 1.65V |
| Output resistance | 28-44ohm | `RSER*` = `rm1`, W=2u L=800u -> 36ohm nominal (L/W=400, rsh_rm1=0.09ohm/sq) |

No output-enable/tri-state in this cell. `DP`/`DM` are physically shared
with the (separate, sibling-issue) receiver front end, so a real
integration needs *some* disable path -- deliberately deferred to a
PHY-level wrapper (not yet filed) rather than added here, since the issue's
acceptance criteria scope this cell to the four Sec.6 electrical
parameters above, not to bus arbitration.

**Sizing rationale, `R_series` needs no trim (contrast with the pull-up
below):** `rm1`'s sheet-rho process spread is only ~+/-13%
(`rsh_rm1=0.09 +/-0.012 ohm/sq`, `libs.tech/ngspice/sm141064.ngspice`),
comfortably inside the spec's +/-22%-wide 28-44ohm band around a 36ohm
center -- so a plain untrimmed metal resistor is sufficient here, unlike
the pull-up's much tighter +/-5% target.

**Spot-check (informal, not a `sim/` evidence record -- #26 owns
verification):** `ngspice -b`, tt corner, 27 degC, ideal 3.3V rail,
`TXDP`/`TXDM` driven by a matched pulse pair into two 50pF loads, measured
via `.meas`:
- rise (10-90%) ~15.1ns, fall (10-90%) ~13.0ns -- both inside [4,20]ns.
- rise/fall matching in this one point: ~14% (2.1ns / ~14.6ns average) --
  slightly *over* the 10% target. Flagged as a concrete tuning item for
  #26 (e.g. re-balance `Wp:Wn` or make `R_slew` polarity-asymmetric), not
  fixed here since this issue is schematic capture only.
- crossover voltage ~1.605V -- inside [1.3,2.0]V, close to the VDD/2
  prediction.

### `dplus_pullup.sch`

Integrated D+ speed-signaling pull-up: 1.5kohm nominal, target +/-5%
(1.425-1.575kohm) across the full PVT envelope (spec Sec.7/Sec.8.1),
enable-controlled for soft-connect/soft-disconnect.

**Design choice: a binary-weighted TRIM LADDER, not active regulation.**
gf180mcu poly resistors are not inherently +/-5% across process on their
own -- `ppolyf_u` alone spans `rsh=350 +/-20%`
(`libs.tech/ngspice/sm141064.ngspice`'s `ss`/`ff` `.lib` sections) -- so a
bare untrimmed resistor cannot meet the target (this is spec Sec.5's own
flag, not a new finding). Two circuit-level ways to close that gap were
open (spec Sec.5): a trimmed/calibrated resistor, or an active
(servo/reference) regulation scheme. This cell uses the trim ladder,
because:

- it needs no on-chip voltage/current reference of its own -- this repo
  has no bandgap block in scope (CLAUDE.md's scope discipline explicitly
  keeps this block narrow; adding a reference generator here would be
  scope creep the block doesn't need for anything else);
- it has no feedback-loop stability concern (a servo scheme would need
  its own compensation, adding a second thing #26 has to verify);
- the correction is a one-time, test-time operation. The trim code itself
  is assumed held in whatever OTP/fuse/scan mechanism the integrator's
  test flow uses -- **out of scope for this schematic**, given the exact
  same boundary treatment as the enable input: `TRIM<4:0>` are presented
  here purely as digital control inputs, the same way `PU_EN` is.

`VPU_REG` (the "internally regulated 3.0-3.6V" rail of spec Sec.5) is an
**input** to this cell, assumed supplied by an upstream regulator block --
not built here. If that regulator does not already exist elsewhere in this
repo, it is a natural follow-up issue; this cell's `VPU_REG` pin is where
it would connect.

**Topology**: `PU_EN`/`TRIM<4:0>` are active-high digital inputs, each
driving a small CMOS inverter (supplied from `VPU_REG`/`VSS`) whose output
gates a PMOS pass switch referenced to `VPU_REG` (source/well tied to
`VPU_REG`, so no body-diode forward-bias risk while D+ sits near its
pulled-up level). `MEN` gates the whole ladder off `VPU_REG` for
enable/disable. `TRIM<i>=1` => bypass switch `i` ON => segment `i`
shorted out (removed from the series path); `TRIM<i>=0` => segment `i`
included. **The untrimmed/unprogrammed default (all-0, the typical
OTP/fuse power-up state) therefore yields MAXIMUM series resistance --
the weakest, safest pull-up state -- rather than minimum.** This is a
deliberate fail-safe choice, not an accident of bit-ordering.

**Trim math (first-order, sheet-rho-only argument -- design intent, not a
PVT-verified claim; #26 owns verification):** all ladder resistors are
`ppolyf_u`, W=4u, nominal `rsh=350ohm/sq` (L sized per `R = rsh*L/W`).

| Segment | R (nominal) | L |
|---|---|---|
| `RBASE` | 1000ohm | 11.43u |
| `R0` (LSB) | 30ohm | 0.343u |
| `R1` | 60ohm | 0.686u |
| `R2` | 120ohm | 1.371u |
| `R3` | 240ohm | 2.743u |
| `R4` (MSB) | 480ohm | 5.486u |

5-bit binary ladder (31 codes), additive range 0-930ohm, ~2% of nominal
per LSB. Let `f` = process sheet-rho factor relative to typical (observed
spread ~0.8-1.2 from the `ss`/`ff` `.lib` corners above; `RBASE` and every
trim segment are the same poly flavour, so they all scale by the same
`f`). Achievable range at a given corner is `[RBASE*f, (RBASE+930)*f]`:

- `f=1.2` (slow/high-R corner): `[1200, 2316]` -- contains `[1425,1575]`
- `f=1.0` (typical): `[1000, 1930]` -- contains `[1425,1575]`
- `f=0.8` (fast/low-R corner): `[800, 1544]` -- contains `[1425,1575]`

So a trim code exists at every corner that lands inside the +/-5% band by
this first-order argument. This covers sheet-rho spread only, not
temperature/voltage/mismatch -- #26's PVT sweep is what turns this from
design intent into a verified claim.

**Spot-check findings (informal `ngspice -b` runs, tt corner, 27 degC --
not a `sim/` evidence record):**

- **Bypass-switch sizing was corrected during authoring, not shipped
  blind.** A first-cut `W=20u/nf=1` PMOS bypass switch measured
  `Ron ~223ohm` -- comparable to a full LSB step (30ohm) and enough to
  wreck trim resolution. Re-sized to a total `W=1000u` in ten 100u fingers
  (near this PDK's observed ~100-150u-per-finger / `nf<=64` modelling
  limits), which measured `Ron ~4.4ohm` -- ~15% of one LSB, a much better
  (though still not PVT-verified) margin. All six pass switches (`MEN` +
  five `MSW*`) in the committed schematic use the corrected sizing.
  **How those ten fingers are drawn changed on 2026-09-05** (issue #56,
  `spec/decisions/0001-dplus-pullup-switch-device-flattening.md`): each
  switch was one `nf=10` instance and is now ten one-finger `W=100u`
  instances in parallel -- one device per drawn gate -- because `klt`'s
  subckt-call -> plain-element ingestion, the path `klt layout-plan` and
  `klt lvs` share, refuses to represent a multi-finger device
  (klayout-tools#1487). Total drawn gate width and every terminal net are
  unchanged, and the electrical equivalence is measured rather than assumed
  in `sim/dplus-pullup-tolerance/records/20260905-185112-6bfe679.md`.
- With that fix, injecting 100uA out of `DP` (`VPU_REG=3.3V`, enabled)
  measured effective resistance of ~2141ohm at trim code 0 (all
  segments in-circuit) and ~1070ohm at trim code 31 (all segments
  bypassed) -- monotonic and in the expected direction, confirming the
  trim mechanism's *topology* works. Both absolute values run ~100-200ohm
  **above** the L/W-only hand calculation above, most likely from
  `ppolyf_u`'s contact/end-resistance terms (not modelled in the simple
  `R=rsh*L/W` estimate). This is a real, open gap between this cell's
  first-cut sizing and its 1.5kohm target -- flagged here rather than
  silently absorbed, and left for #26 to close (either by re-deriving `L`
  from the full compact model instead of the sheet-rho approximation, or
  by relying on the trim algorithm to characterize-and-select at test
  regardless of the hand-calc's absolute accuracy, which is exactly what
  a trim ladder is for).
- Disabling (`PU_EN=0`, all trim bits 0) correctly removes `DP` from the
  `VPU_REG` path (no finite operating point exists for the synthetic
  100uA test load -- the expected signature of a true high-impedance
  disconnect).

None of the above is a substitute for #26's PVT-corner simulation pass;
it is the level of diligence reasonable to expect from schematic capture
(catching an obviously-wrong component value before it ships), not a
claim that the +/-5% target is met.

## Differential + single-ended receivers (issue #29)

Three receive-side analog blocks, per `spec/usb2-device-phy.md` Sec.4: a
differential receiver and one single-ended receiver per line (D+, D-).
**Schematic capture only** at this stage, same boundary as issue #30's
cells above -- each targets its spec Sec.4 threshold(s) *by design*, but
none has been through a PVT-corner simulation pass (#26, which depends on
these schematics existing). Nothing below is a verified claim; each is
flagged as design intent, per `sim/README.md`'s append-only
evidence-record convention (a *verified* claim lives in `sim/`, not
here). All three cells are flat leaves (no cell instantiates another),
consistent with `design/netlist.py`'s module docstring.

### Shared building block: a self-biased 5T OTA + 2-inverter buffer

All three cells reduce to the same core: a differential-to-digital
converter built from an NMOS 5-transistor OTA (operational
transconductance amplifier) followed by a 2-stage CMOS inverter buffer
that squares the OTA's small analog output swing to a rail-to-rail
digital bit. No on-chip voltage/current reference is used anywhere in
this section -- consistent with CLAUDE.md's scope discipline (no
bandgap block in scope): bias current is generated locally in each cell
by a resistor (`RBIAS`, `ppolyf_u_1k`, ~200kohm nominal) into a
diode-connected NMOS (`MNBIAS`), mirrored 2x into the OTA's tail
transistor (`MTAIL`).

**5T-OTA polarity rule (load-bearing, and easy to get backwards --
flagged here because an earlier draft of this schematic had it
inverted until an ngspice spot-check caught it):** in a diff pair with
diode-connected PMOS load on one branch and a mirrored PMOS load on the
other, the single-ended output node (the mirrored branch) is
**non-inverting with respect to the diode-connected branch's own gate**,
and inverting with respect to the output branch's own gate. Each cell
below places its "the output should track this signal" input on the
diode-connected branch (`MN_INA`) for exactly this reason, so that the
two buffer-stage inversions cancel and the final digital output tracks
that input non-invertingly.

### `differential_receiver.sch`

Recovers D+/D- differential data (J/K states): the OTA compares `DP`
(diode branch, `MN_INA`) against `DM` (mirror/output branch, `MN_INB`),
so `RXD` tracks `DP` non-inverting: `RXD=1` when `DP` is the
more-positive line (J), `RXD=0` when `DM` is (K). NRZI/bit decode of
`RXD` is out of scope here (the out-of-scope serial interface engine per
CLAUDE.md) -- this cell stops at the recovered raw bit.

Target (spec Sec.4), by design intent: differential input sensitivity
`|DP-DM| > 200mV`, over a `0.8-2.5V` common-mode range.

**Sizing rationale (first-order, hand calc):** input pair `MN_INA`/
`MN_INB` sized `W=20u/L=0.28u` (min-L for gm, wide for low Vov --
headroom toward the 0.8V common-mode floor). Load `MP_LOADA`/
`MP_LOADB` sized 2:1 P:N (`W=40u` vs the input pair's `W=20u`, gf180mcu
3.3V mobility ratio -- same convention as `differential_driver.sch`'s
output stage). Buffer inv1 (`MP_B1`/`MN_B1`, `W=8u`/`4u`) and inv2
(`MP_B2`/`MN_B2`, `W=16u`/`8u`) follow the same 2:1 P:N ratio and
roughly double per stage (fanout scaling) to square `AMPOUT`'s
small-signal swing to rail-to-rail `RXD`.

**Spot-check (informal, `ngspice -b`, tt corner, 27 degC, ideal 3.3V
rail -- not a `sim/` evidence record):** DC operating-point sweep with
DP/DM driven +/-150mV around a common-mode point (300mV differential,
above the 200mV sensitivity target), swept across the full 0.8-2.5V
common-mode range (0.8, 1.0, 1.4, 1.65, 2.0, 2.5V):
- At every common-mode point, `AMPOUT` and `RXD` saturate to VDD (3.3V)
  -- correct polarity (`DP>DM` -> `RXD` high) and full rail-to-rail
  output across the entire spec'd common-mode range at this one
  operating point (tt/27degC/ideal-VDD only; PVT sweep is #26's job).
- Reverse polarity check (`DP=1.5V`, `DM=1.8V`, CM=1.65V, 300mV the
  other way): `AMPOUT` = 0.83V, `RXD` ~ 0V -- correctly low.
- Differential just above the spec minimum (`DP=1.775V`, `DM=1.525V`,
  250mV differential, CM=1.65V): `RXD` still saturates fully high --
  consistent with, but not a substitute for, a real offset/mismatch
  sweep at exactly 200mV (#26's job).

Open PVT items (not covered by the spot-check above; #26 owns
verification): common-mode headroom margins at the tail current source
(0.8V floor) and the PMOS load (2.5V ceiling) were not swept beyond the
six single points above; input-referred offset from device mismatch is
not modelled by a DC operating-point check at all.

### `se_receiver_dp.sch` / `se_receiver_dm.sch`

One single-ended receiver per line, identical topology, mirrored only in
which line/output pin they use (`DP`/`RXDP` vs `DM`/`RXDM`). Each
compares its line against a locally-generated reference `VREF` (mirror
branch is the internal `VREF` node, diode branch is the line input, so
the output tracks the *line*, not `VREF`, non-inverting -- same 5T-OTA
polarity rule as above).

Target (spec Sec.4), by design intent, per line: `VIH > 2.0V`,
`VIL < 0.8V`.

**Design choice: `VREF` at the VIH/VIL midpoint, not an absolute
reference.** `VREF` is set by an on-chip resistor divider (`R1`/`R2`,
both `ppolyf_u_1k`) off `VDD`: `R1=1900ohm` (`W=2u,L=3.8u`),
`R2=1400ohm` (`W=2u,L=2.8u`), `R1+R2=3300ohm`, so
`VREF = VDD*R2/(R1+R2) = 3.3V*1400/3300 = 1.4V` at nominal `VDD` --
exactly `(VIH+VIL)/2 = (2.0+0.8)/2 = 1.4V` by construction, giving a
zero-offset comparator 0.6V of margin on each side. This is a
supply-referenced (ratiometric) threshold, not an absolute one: it
tracks `VDD` along with the thresholds it is trying to straddle, which
is appropriate for this cell's purpose (recognizing rail-referenced
J/K/SE0 levels) but is a design choice worth flagging, not a claim that
it is immune to `VDD` variation -- #26's job. OTA/bias/buffer sizing is
identical to `differential_receiver.sch`'s (see above); not repeated
per-cell to avoid drift between independently-editable copies (some
duplication across the three cells in this section is expected, per
`design/netlist.py`'s "flat leaf, no hierarchy yet" module docstring).

**Spot-check (informal, `ngspice -b`, tt corner, 27 degC, ideal 3.3V
rail -- not a `sim/` evidence record, `se_receiver_dp.sch` shown, `_dm`
confirmed to match at the two boundary points):**
- `VREF` measured 1.412V -- close to the 1.4V hand calc; the small gap
  is the real `ppolyf_u_1k` compact model's non-ideal (contact/end
  resistance) terms versus the sheet-rho-only estimate, the same class
  of gap flagged for the pull-up's trim resistors above.
- `DP=2.0V` (the VIH boundary): `RXDP` = 3.3V (high) -- correct.
- `DP=0.8V` (the VIL boundary): `RXDP` ~ 0V (low) -- correct.
- Coarse trip-point sweep (`DP` = 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0V):
  low through 1.2V, high from 1.4V onward -- the actual switching point
  falls between 1.2V and 1.4V, consistent with the ~1.412V `VREF`
  measurement and comfortably inside both margins.
- `se_receiver_dm.sch`: `DM=2.0V` -> `RXDM` high, `DM=0.8V` -> `RXDM`
  low -- same boundary behavior confirmed on the D- copy.

Open PVT item (not covered by the spot-check above; #26 owns
verification): comparator input-referred offset from device mismatch
eats directly into the 0.6V margin on each side and is not modelled by
a DC operating-point check -- #26's PVT/mismatch sweep is what turns
this margin argument into a verified claim.

None of the above is a substitute for #26's PVT-corner simulation pass;
it is the level of diligence reasonable to expect from schematic capture
(catching an obviously-wrong polarity or component value before it
ships -- the polarity bug above is a concrete example of exactly that),
not a claim that the Sec.4 thresholds are met.
