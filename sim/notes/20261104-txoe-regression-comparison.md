# TXOE cell: 45-corner re-measurement vs the pre-TXOE predecessors (issue #114)

Dated note, 2026-11-04. Not a record; it tabulates differences between append-only
records and edits none of them. Spec limits and checks are unchanged.

| Experiment | New record | Predecessor | Batch job (`environment.remote.job_id`) | Result |
|---|---|---|---|---|
| `driver-disabled-leakage` | `20261104-193759-bccb09f` | `20261021-014209-b685001` (ERROR, job `klt-sim-e642f9b58251` exited 87; no data) | `klt-sim-5fce0783636a` | 45/45, PASS (harness check only) |
| `driver-signal-quality` | `20261104-194138-bccb09f` | `20261015-104027-d109790` | `klt-sim-94773e0c253e` | 45/45 completed, **FAIL** 1 row at 1 corner |
| `driver-jitter` | `20261104-194449-bccb09f` | `20261015-104027-d109790` | `klt-sim-45c3f47e5606` | 45/45, PASS (no spec limit) |

All three ran on the Spot batch fleet through `--backend klt`; nothing ran locally.
The records note "dirty" git state only because the new records and manifests were
untracked at run time. The DUT (`design/netlist/differential_driver.spice`, sha256
`50dcbc20…8a9b8930`) is the merged cell from #154; no schematic, netlist or
testbench was touched.

## Newly failing §6 row (regression, not a known #96 failure)

`driver-signal-quality`, `fs_-40c_2.97v`: `trf_ratio` = **1.10582** against max 1.1
(predecessor 1.08626, +0.01956). Rise 5.05189 ns (was 5.13035), fall 4.56846 ns
(was 4.72295). Fall time dropped 0.154 ns but rise time only 0.078 ns, so the
ratio grew. The predecessor passed this row with a 1.4 % margin; the TXOE cell lost
it. Every other row passes at all 45 corners.

Cause, to the extent the evidence supports it: the TXOE cell re-gates the
predrivers (#154), which changes the predriver loading and delay on the pull-down
path more than on the pull-up path in the `fs` corner (fast NMOS, slow PMOS). This
note does not claim a root cause beyond that; the sizing fix is a separate issue
(out of scope for #114).

## `driver-signal-quality`: per-corner change vs `20261015-104027-d109790` (new − old, over 45 corners)

| measurement | mean | smallest change | largest change |
|---|---|---|---|
| `trise_ns` | −0.081 | −0.116 (`ss_-40c_2.97v`) | −0.062 (`ff_-40c_3.30v`) |
| `tfall_ns` | −0.123 | −0.213 (`ss_-40c_2.97v`) | −0.061 (`ff_125c_3.63v`) |
| `trf_ratio` | +0.0079 | −0.0021 (`ff_125c_3.63v`) | **+0.0196** (`fs_-40c_2.97v`) |
| `vcross_rise` (V) | −0.038 | −0.070 (`ss_-40c_2.97v`) | −0.013 (`ff_125c_3.63v`) |
| `vcross_fall` (V) | −0.038 | −0.070 (`ss_-40c_2.97v`) | −0.013 (`ff_125c_3.63v`) |
| `dp_over_mv` | −0.646 | −0.913 (`ss_-40c_2.97v`) | −0.376 (`ff_125c_3.63v`) |
| `dp_under_mv` | +0.046 | −0.012 (`fs_125c_2.97v`) | +0.096 (`sf_-40c_3.63v`) |

Margins that shrank: fastest rise 4.03035 ns (`ff_-40c_3.63v`) is 0.8 % above the
4 ns floor (was 2.3 %); lowest crossover 1.339 V (`fs_-40c_2.97v`) is 3 % above the
1.3 V floor (was 1.405 V).

## `driver-jitter`: per-corner change vs `20261015-104027-d109790`

| measurement | mean | smallest change | largest change |
|---|---|---|---|
| `tprop_ns` | −0.688 | −0.945 (`ss_125c_2.97v`) | −0.508 (`ff_-40c_3.63v`) |
| `jit_grid_pp_ps` | +0.439 | +0.195 (`tt_-40c_3.63v`) | +1.015 (`ss_125c_2.97v`) |
| `jit_cons_pp_ps` | +0.557 | +0.139 (`sf_-40c_2.97v`) | +0.985 (`ff_27c_3.63v`) |
| `xings_extra_ps` | 0 | 0 | 0 |

Propagation delay fell at every corner; peak-to-peak jitter rose by sub-picosecond
to ~1 ps. No spec limit applies, so no pass/fail is claimed.

## `driver-disabled-leakage`: worst corner

No compliance limit is established or invented. The 1 mA contention floor is a
harness-integrity check only (the enabled control fought the opposing source at
35.5–92.1 mA on DP and 34.9–78.6 mA on DM, so the meter was capable of seeing a fight).

- **Worst settled disabled current: 50 459 nA (50.5 µA) at `ff_125c_2.97v`**
  (`leak_j_dp`, `leak_k_dm`, `leak_se1_*` all ≈ 50.46 µA: host pad driven to
  3.3 V while the cell runs from 2.97 V, i.e. an over-rail pad).
- Worst per supply: 2.97 V → 50 459 nA (`ff_125c_2.97v`); 3.30 V → 283 nA
  (`ff_125c_3.30v`); 3.63 V → 273 nA (`ff_125c_3.63v`).
- Best: 0.083 nA (`ss_-40c_3.30v`).
- PR #154's single-point figure (~272 nA at `ss`/125 °C/2.97 V, not a record) is
  **not** the grid's worst: the grid shows ~185× higher current at `ff_125c_2.97v`
  and the over-rail 3.3 V host case at the 2.97 V supply corner dominates.
- `toggle_peak_*` (peak current while inputs toggle with TXOE=0) reaches 50.5 µA
  (DP) / 59.8 µA (DM) at `ff_125c_2.97v`.
