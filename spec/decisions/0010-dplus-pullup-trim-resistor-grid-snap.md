# DR-0010 — Grid-snapped drawn lengths for the `dplus_pullup` trim resistors XR0..XR4

- **Status**: Accepted — operator ruling (rjwalters, 2026-10-30, attended
  fleet:decide round 20261030-r4, question r4-q16, option 1), recorded on
  issue #251.
- **Date**: 2026-10-30
- **Raised by**: Builder agent, issue #251
- **Does not change**: the ratified spec text, §5's 1.5 kΩ ±5 % row, the
  schematic `design/dplus_pullup.sch`, `design/netlist/dplus_pullup.spice`, or
  any existing evidence record. It changes only the *drawn* length of five
  resistors in `layout/analog/plans/dplus_pullup.json`. The no-re-sizing rule
  of issue #251 is set aside by the ruling for these five resistors only; no
  device in any of the other three blocks, and no MOS device, is touched.

## Context

`layout/analog/dplus_pullup.gds` was routed 21/21 but carried 75 DRC
violations, all inside the five `ppolyf_u` cells for the trim-ladder segments
XR0..XR4. The netlist lengths (0.343, 0.686, 1.371, 2.743, 5.486 µm) are not
multiples of the 0.005 µm manufacturing grid, and `res_array` draws exactly
what the netlist says (klayout-tools#4203 only warns). Upstream tracking:
klayout-tools#4666 (`res_array` should snap and enforce a minimum drawable
length). Repo-side follow-up: #263, which regenerates from the netlist once the
generator snaps, and reconciles with this record.

## Decision

Draw XR0..XR4 at the lengths below, set as `params.length_um` on the
`r_seg0`..`r_seg4` groups of the plan. klt reports each as a divergence from
the netlist-derived value in `warnings[]`; that is intended and is the
mechanism, not an error.

| Resistor | Plan group | Netlist L (µm) | Drawn L (µm) | ΔL (µm) | ΔR at tt/27 °C (Ω) | ΔR / own R |
|---|---|---|---|---|---|---|
| XR0 | `r_seg0` | 0.343 | **0.420** | +0.077 | +6.83 | +22.4 % |
| XR1 | `r_seg1` | 0.686 | 0.685 | −0.001 | −0.09 | −0.15 % |
| XR2 | `r_seg2` | 1.371 | 1.370 | −0.001 | −0.09 | −0.07 % |
| XR3 | `r_seg3` | 2.743 | 2.745 | +0.002 | +0.18 | +0.07 % |
| XR4 | `r_seg4` | 5.486 | 5.485 | −0.001 | −0.09 | −0.02 % |

XR1..XR4 take the nearest 0.005 µm multiple. XR0's nearest multiple (0.345) is
not drawable: a probe of the plan at klt 0.8.0 (deck `gf180mcu`) gave

| XR0 drawn L (µm) | `klt drc` result |
|---|---|
| 0.345 | `pplus.width.1` and `sab.width.1` |
| 0.400 | `sab.width.1` |
| 0.415 | `sab.width.1` |
| 0.420 | clean |

so XR0 is lengthened to 0.420 µm, the shortest on-grid length that clears
`sab.width.1` (0.42 µm) and `pplus.width.1` (0.40 µm). The ΔR column uses
88.7 Ω/µm, the slope measured between the two `tt_27c_3.30v` points of the
netlist run and the snapped run (+6.74 Ω for ΔL_total = +0.076 µm).

## Consequences

- **Ladder weights are no longer 1:2:4:8:16.** The weights are
  0.420 / 0.685 / 1.370 / 2.745 / 5.485 µm. The code-to-resistance map stays
  strictly monotonic (checked on all 32 codes), but the per-code step ranges
  0.265–0.420 µm (about 23.5–37 Ω) instead of a uniform 0.343 µm (30.4 Ω).
- **Absolute resistance** rises by 5.4–8.2 Ω (about +0.3 %) at every code and
  corner, almost all of it XR0; the trim range absorbs this.
- **Tolerance band.** The band the snapped ladder must stay inside is §5's
  1.425–1.575 kΩ across the §8.1 matrix. Re-simulated on the 45-corner matrix
  (`sim/dplus-pullup-tolerance/`, DUT
  `sim/dplus-pullup-tolerance/dut/dplus_pullup_grid_snapped.spice`, which is
  `design/netlist/dplus_pullup.spice` with only the five `r_length` values
  changed):

  | Reading | Netlist lengths (record `20261017-195431-49d005c`) | Snapped lengths (records `20261030-212701-7134cc0`, `20261030-212919-7134cc0`) | Limit |
  |---|---|---|---|
  | Per-corner best code, worst error | 2.01 % | 2.44 % | 5 % |
  | Per-corner best code, R range | 1482.9–1530.1 Ω | 1464.8–1536.6 Ω | 1425–1575 Ω |
  | Fixed trim code, worst error (`analyze_fixed_trim.py`) | 2.01 % (record `20260817-203609-a408cb6`) | 2.55 % | 5 % |

  45/45 corners pass on both readings. The two new records are the same
  simulation over two `klt sim` transports (`request`, `decks`); the
  per-corner values agree, and only the `decks` record carries the 32-code
  table the fixed-trim analysis needs.
- **LVS (#247) will see a parameter difference** on XR0..XR4 between the
  layout and `design/netlist/dplus_pullup.spice`. That difference is this
  decision, not a layout error; the LVS record must cite DR-0010 until #263
  retires it.
- The re-simulation is schematic-level on a modified netlist. It is not an
  extracted post-layout result (#53).

## Alternatives not taken

- **Leave the five resistors off-grid and record the 75 violations** (option a
  of the decision block): keeps the no-re-sizing rule, gives up a clean
  `dplus_pullup` stream.
- **Wait for klayout-tools#4666 / #4203** (option c): no date.
- **Edit `design/dplus_pullup.sch`** so the netlist carries on-grid lengths:
  would restate the ratified design source for a layout-tool limitation; #263
  keeps the netlist as the source of truth and removes the override once klt
  snaps.
