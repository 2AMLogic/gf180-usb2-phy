# DR-0007 — Which analog spec rows are statistical (T1 item 6)

- **Status**: Accepted (classification only; no spec row, bound or tolerance changes)
- **Date**: 2026-10-17
- **Raised by**: Builder agent, issue #189
- **Corrects**: `manifests/README.md`, which said the whole block has no
  statistical row. That is true only of the digital partition.
- **Does not change**: the ratified spec, any bound (including the ±5 %
  pull-up tolerance), the full-speed-only, device-only, UTMI-boundary scope.

## Context

T1 item 6 asks for Monte Carlo evidence for every accuracy, offset or
matching row, and for a block with none to say so. `manifests/README.md`
claimed the §8.2 table has "no statistical row". §8.2 lists the pull-up
tolerance and the receiver thresholds as "DC/parametric across the 45
corners", which describes the method used so far, not whether the quantity is
decided by random device variation. A corner matrix moves every device of a
type together; it cannot show what happens when two nominally matched devices
differ.

## Classification

| §8.2 row | Statistical? | Reason |
|---|---|---|
| Rise/fall time, crossover voltage, driver jitter, signal quality | No (not classified here) | Edge timing of a large driver into a 50 pF load; the margin is set by the corner spread. No matching-dependent mechanism has been identified. Revisit if a record shows the margin is thinner than the corner-to-corner step. |
| Receiver thresholds, differential (§4: \|D+ − D−\| > 200 mV, CM 0.8–2.5 V) | **Yes** | The input-referred threshold is the offset of a MOS input pair; that offset is a matching quantity. |
| Receiver thresholds, single-ended D+ / D− (§4: VIL < 0.8 V, VIH > 2.0 V) | **Yes, lower risk** | The switching point is set by device ratios and shifts with mismatch; the window (0.8–2.0 V) is wide, so margin is expected to be large but has not been measured. |
| D+ pull-up tolerance (§5: ±5 %) | **Yes in principle, not measurable with this PDK** | The pull-up is a polysilicon resistor ladder plus trim; segment-to-segment mismatch moves the best trim code. The gf180mcuD resistor model carries the mismatch hook but ships it disabled (`mis_r=0` in every `*_u` resistor subcircuit of `sm141064.ngspice`, verified 2026-10-17), so `sw_stat_mismatch=1` samples MOS devices only. Global resistor spread (`sw_stat_global`, `mc_rsh_*`) is modelled and is a process variation, not mismatch. |
| DRC / LVS | N/A | Not an electrical row. |
| Digital partition | No | See `verification/statistical-claims-na.md`. |

## Decisions

1. The manifest claim is narrowed: "no statistical row" holds for the digital
   partition only. The analog partition has the statistical rows above.
2. The differential-receiver row is the first campaign
   (`sim/diff-receiver-mc/`): `klt sim` `monte_carlo` requests with
   `vary: "mismatch"`, per-corner N and a recorded seed, run on all 45 PVT
   points so the MC is combined with, not instead of, the process corners; the
   deterministic negative control is the same request with
   `sw_stat_mismatch=0`, where every sigma must be exactly 0 (the control klt
   documents for decks that draw mismatch from ngspice's own RNG).
3. The pull-up row is **not** given a fabricated mismatch model. Injecting
   `mis_r` from the instance line would rely on a coefficient the PDK does not
   stand behind. The gap is recorded here; the tool side (the resistor family
   reports `family_mismatch.active: false`) is already tracked upstream as
   klayout-tools#355, so no new tool issue is filed. The pull-up row stays
   without Monte Carlo evidence until the PDK or a ratified injected-mismatch
   model supplies one.
4. Spec bounds are not widened to make a yield figure pass.

## Alternatives rejected

- A custom MC loop in `sim/run_corners.py`: duplicates `klt sim monte_carlo`
  and would run on the dispatch host.
- Reporting the pull-up row as covered by the process corners alone: a corner
  matrix cannot validate a matching quantity, which is the point of item 6.
