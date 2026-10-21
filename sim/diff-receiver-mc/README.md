# diff-receiver-mc — Monte Carlo for the differential receiver (T1 item 6, analog)

Classification and rationale: `spec/decisions/0007-analog-statistical-rows.md`.
The §4 differential input sensitivity is decided by MOS-pair mismatch, so the
45-corner matrix in `sim/diff-receiver-sensitivity/` cannot validate it alone.

`build_requests.py` writes two `klt sim` requests (one self-contained
`body.spice` each, DUT and testbench taken unmodified from
`sim/diff-receiver-sensitivity/`):

| variant | deck switch | purpose |
|---|---|---|
| `mismatch` | `sw_stat_mismatch = 1` | measurement: N samples at each of the 45 PVT points (5 MOS process corners × 3 temperatures × 3 supplies), `vary: "mismatch"`, recorded seed |
| `control` | `sw_stat_mismatch = 0` | deterministic negative control: same seeds, deck mismatch off; every sigma must be exactly 0 |

Limits on each measurement are copied from the ratified-spec `checks` in
`sim/diff-receiver-sensitivity/testbench/tb.json`; nothing is widened.

## Run (fleet only)

```bash
python3 sim/diff-receiver-mc/build_requests.py "$WORK" --n 100
klt sim --dry-run --backend batch "$WORK/mismatch/request.json"
klt sim --backend batch --format json -o "$WORK/mismatch/out" "$WORK/mismatch/request.json" > "$WORK/mismatch/report.json"
klt sim --backend batch --format json -o "$WORK/control/out"  "$WORK/control/request.json"  > "$WORK/control/report.json"
klt yield-samples "$WORK/mismatch/report.json" --negative-control "$WORK/control/report.json" > "$WORK/samples.json"
klt yield "$WORK/samples.json"
```

`klt yield` needs the native extension (`klayout-tools[yield]`). Do not install
it into the host tool; use a throwaway environment
(`uvx --from "klayout-tools[yield]" klt yield ...`).

## Status: no result recorded yet

**`6.analog` is not claimed.** No samples, `klt yield` report or evidence record
exist. No local fallback grid was run. Fleet attempts so far (N=100, 4500 units
per variant), newest first:

| date | submission | outcome |
|---|---|---|
| 2026-10-20 | `mismatch` + `control` at once, `--max-units-per-job 150 --max-concurrent-jobs 8`, `options.timeout_s` 20 (jobs `klt-sim-859a5a27c9fe` and `klt-sim-b0e86edf3f53` among 30 shards each) | `status: error`: 30 / 21 units passed. `timeout` (ngspice killed at 20 s on the fleet, although one unit takes 0.57 s locally), `measurement ... produced no value` (follows the timeouts), and `lost_shard`: the two concurrent client invocations each allowed 8 jobs and went over `BATCH_MAX_CONCURRENT_INSTANCES=8`, and some pools had no capacity. `options.timeout_s` was put back to 300. |
| 2026-10-20 | `mismatch` and `control` as one job each (`klt-sim-a6b680424799`, `klt-sim-c7bb42741f01`) | client `timeout` at 3412 s; submit warned the 4500-unit job exceeds the fleet's 3600 s whole-job ceiling. |
| 2026-10-17 | `mismatch`, n=2 (`klt-sim-7272c1a5d04f`) | `interrupted` (Spot reclaim) about 200 s in; the client was terminated while waiting. |

What the next attempt has to respect:

- `klt sim` refuses `--max-units-per-job` above `(3600 - 120) / options.timeout_s`
  (11 units at the 300 s in `build_requests.py`, so about 410 jobs per variant).
  Lowering `timeout_s` to fit more units per job needs a measured per-unit time
  on the fleet; the 20 s guess was too low.
- The fleet cap is 8 instances in total, so submit one variant at a time, not
  two concurrent `klt sim` invocations.

The campaign (N >= 100 per corner point, both variants, `klt yield`) remains the
work of issue #189.
