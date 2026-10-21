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

## Status: no result recorded yet (issue #189 outcome C)

**`6.analog` is not claimed.** No complete sample set, `klt yield` report or
evidence record exists, and the differential-receiver row is not covered by
Monte Carlo. No local fallback grid was run. Fleet attempts, newest first
(append-only; N=100, 4500 units per variant unless noted):

| date | submission | outcome |
|---|---|---|
| 2026-10-20/21 | `mismatch`, `--resume --wait-for-capacity 3000 --max-units-per-job 46 --max-concurrent-jobs 8`, re-attaching to the attempt below | Stalled: shards sat at `no status.json yet` for over an hour with no further shard completing; killed by hand, so no report was written. Filed as klayout-tools#4018. `control` was not submitted. |
| 2026-10-20 | `mismatch`, `options.timeout_s` 75, `--max-units-per-job 46 --max-concurrent-jobs 8` (98 jobs) | `status: error`: 1971 / 4500 units passed, 2529 `lost_shard`. Refusals: `8 or 9 instance(s) already running + 1 requested exceeds BATCH_MAX_CONCURRENT_INSTANCES=8` (1425 units) and `224 vCPU already running ... exceeds BATCH_MAX_VCPU=224` (1104 units). The caps are fleet-wide and shared with other clients. Not usable as evidence (incomplete per point). Passing units took 16-44 s each on the fleet. |
| 2026-10-20 | **pilot**: `mismatch`, `--n 2` (90 units), `--max-units-per-job 11`, `options.timeout_s` 300; 9 jobs including `klt-sim-e3b87a8cfb4b`, `klt-sim-a62ee60389af`, `klt-sim-776f33a63c73`, `klt-sim-c0afa192932d`, `klt-sim-05ff85faed98`, `klt-sim-b12b8bdbc411`, `klt-sim-afd11d6bfc84`, `klt-sim-aa114b0ebc35`, `klt-sim-85ad9dc677aa` | 80 / 90 units passed (per-unit fleet time 16.4-23.2 s, median 21.0 s; 2 units per instance in parallel); the 9th job was `lost_shard` (9 jobs exceeded the 8-instance cap, `--max-concurrent-jobs` was not passed). A measurement, not evidence for `6.analog`. |
| 2026-10-20 | `mismatch` + `control` at once, `--max-units-per-job 150 --max-concurrent-jobs 8`, `options.timeout_s` 20 (jobs `klt-sim-859a5a27c9fe` and `klt-sim-b0e86edf3f53` among 30 shards each) | `status: error`: 30 / 21 units passed. `timeout` (ngspice killed at 20 s on the fleet; the pilot above shows a unit needs 16-23 s there, not the 0.57 s seen locally), `measurement ... produced no value` (follows the timeouts), and `lost_shard` (two concurrent client invocations went over `BATCH_MAX_CONCURRENT_INSTANCES=8`). |
| 2026-10-20 | `mismatch` and `control` as one job each (`klt-sim-a6b680424799`, `klt-sim-c7bb42741f01`) | client `timeout` at 3412 s; submit warned the 4500-unit job exceeds the fleet's 3600 s whole-job ceiling. |
| 2026-10-17 | `mismatch`, n=2 (`klt-sim-7272c1a5d04f`) | `interrupted` (Spot reclaim) about 200 s in; the client was terminated while waiting. |

Sizing taken from the pilot (use when the fleet has capacity):

- Slowest pilot unit 23.2 s; `--timeout-s 75` is about 3.2x that (the 4500-unit
  run saw units up to 43.8 s under load, still inside 75 s).
- `--max-units-per-job <= (3600 - 120) / 75 = 46` (98 jobs per variant).
  Pass `--timeout-s 75` to `build_requests.py`; the default stays 300.

What the next attempt has to respect:

- Submit one variant at a time (`mismatch`, wait, then `control`).
- Pass `--max-concurrent-jobs 8` and `--wait-for-capacity`, and expect the
  shared fleet to refuse launches while other clients hold instances; run it
  when the fleet is quiet or after klayout-tools#4018 is addressed.
- Do not lower N or drop PVT points to get a result; a reduced run is a pilot
  and is never cited as `6.analog`.

The campaign (N >= 100 per corner point, both variants, `klt yield`) remains the
work of issue #189.
