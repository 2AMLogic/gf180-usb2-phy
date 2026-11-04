# TXOE cell: rise/fall-matching fix, 45-corner re-measurement (issue #277)

Dated note, 2026-11-04. Not a record; it tabulates differences between append-only
records and edits none of them. Spec limits and checks are unchanged (the 1.1
`trf_ratio` limit is **not** relaxed).

| Experiment | New record | Superseded record | Batch job (`environment.remote.job_id`) | Result |
|---|---|---|---|---|
| `driver-signal-quality` | `20261104-204550-2d31f87` | `20261104-194138-bccb09f` (FAIL, 1 row at 1 corner) | `klt-sim-d00fa2c1dd21` | 45/45 completed, **PASS** every §6 row |
| `driver-jitter` | `20261104-204926-2d31f87` | `20261104-194449-bccb09f` | `klt-sim-061f4df7bb73` | 45/45, PASS (no spec limit) |
| `driver-disabled-leakage` | `20261104-205341-2d31f87` | `20261104-193759-bccb09f` | `klt-sim-7dc8ba0aa75c` | 45/45, PASS (harness check only) |

All three grids ran on the Spot batch fleet through `--backend klt`. The single-corner
probes used to choose the value ran locally (`--no-write`, one point each, not records).

## The change

`design/differential_driver.sch`: `RSLEWNDP` and `RSLEWNDM` (the poly slew resistor
between the gated NOR predriver and the output NMOS gate) `ppolyf_u` 1u × 2u →
1u × 10u. Nothing else changed: predriver devices, output stage (4 × 80u / 4 × 30u),
`rm1` series resistor and the PMOS-path `RSLEWP*` are as in `20261104-194138-bccb09f`.
`design/netlist/differential_driver.spice` was regenerated with `design/netlist.py`
(`klt netlist`).

Why this lever: at `fs_-40c_2.97v` the fall edge (fast NMOS) is the short one, so
the ratio is fixed by slowing only the NMOS gate edge. Lengthening the PMOS-path
resistor or shortening the NMOS-path one was ruled out by single-corner probes (rise
time fell below the 4 ns floor at `ff_-40c_3.63v`: 3.996 ns). The `fs_-40c_2.97v`
probe sweep (NMOS-path `r_length`): 2u → 1.1058 (baseline), 6u → 1.0896,
10u → 1.0682, 14u → 1.0508; 14u was rejected because crossover reached 1.990 V at
`sf_-40c_3.63v` (2.0 V ceiling). Narrowing the NOR PMOS series stack (16u → 12u)
barely moved the ratio (1.1051) and was dropped. These probe numbers are
exploratory; the 45-corner records are the evidence.

## `driver-signal-quality`: before → after

| measurement | `20261104-194138-bccb09f` | `20261104-204550-2d31f87` | limit |
|---|---|---|---|
| `trf_ratio` at `fs_-40c_2.97v` | 1.10582 (FAIL) | 1.06821 | 0.9–1.1 |
| `trf_ratio` range | 0.946–1.106 | 0.930–1.068 | 0.9–1.1 |
| `trise_ns` range | 4.030–8.664 | 4.037–8.647 | 4–20 |
| `tfall_ns` range | 4.046–8.591 | 4.117–8.766 | 4–20 |
| `vcross_rise` range (V) | 1.340–1.834 | 1.420–1.941 | 1.3–2.0 |
| `vcross_fall` range (V) | 1.339–1.834 | 1.419–1.941 | 1.3–2.0 |

Margins after the change: fastest rise 4.0366 ns (0.9 % above the floor, was 0.8 %);
highest crossover 1.941 V at `sf_-40c_3.63v` (3 % below the ceiling, was 8 %); lowest
ratio 0.930 at `sf_-40c_2.97v` (3 % above 0.9, was 5 %); highest ratio 1.068 (3 % below
1.1). The crossover ceiling and the sf ratio floor are now the tighter rows.

## `driver-disabled-leakage` (TXOE=0 path)

The change sits on the enabled gate-edge path only; the re-run confirms the disabled
state is unaffected: worst settled disabled current is 50 459.4 nA at `ff_125c_2.97v`
(unchanged to the figure in `20261104-193759-bccb09f`), and the worst figures at
3.30 V / 3.63 V supply are 283 nA / 273 nA as before.

## Layout

`layout/analog/plans/differential_driver.json` is not updated: it already predates the
TXOE cell (it names `SLEWDP`/`SLEWDM`, not `RSLEWNDP`/`RSLEWNDM`), so the resistor
length is picked up when the plan is brought up to the TXOE schematic. Not done here.
