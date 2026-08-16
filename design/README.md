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
  wreck trim resolution. Re-sized to `W=1000u` in `nf=10` fingers of 100u
  (near this PDK's observed ~100-150u-per-finger / `nf<=64` modelling
  limits), which measured `Ron ~4.4ohm` -- ~15% of one LSB, a much better
  (though still not PVT-verified) margin. All six pass switches (`MEN` +
  five `MSW*`) in the committed schematic use the corrected sizing.
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
