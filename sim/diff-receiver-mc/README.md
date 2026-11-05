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
(`uvx --from "klayout-tools[yield]==0.9.0" klt yield ...`; resolved on 2026-11-05).
Pass `--format json` to `klt yield-samples` and `klt yield` when redirecting to a file.

## Status: campaign complete, graded `unmet` (issue #189; 2026-11-05, 4500 / 4500 units per variant)

**`6.analog` is not claimed.** The 2026-11-05 run produced the complete
N=100 x 45-point sample set for both variants and a `klt yield` report
(`results/20261105-n100/yield.json`), but `klt yield` reports the negative
control as `not_detected` on all 9 measurements (see the first row below), and
the item-6 grader renders that as `unmet` / `negative_control_not_detected`.
Pull-up and single-ended rows are not covered (DR-0007; #212). No local
fallback grid was run. Attempts, newest first (append-only; N=100, 4500 units
per variant unless noted):

| date | submission | outcome |
|---|---|---|
| 2026-11-05 | throwaway `uvx --from "klayout-tools[yield]==0.9.0" klt` (the `[yield]` extra resolved; `klt-yield-native` imports). `build_requests.py --n 100 --timeout-s 75`, `klt sim --dry-run --backend batch` first, then `mismatch` alone, waited to completion, then `control` alone, each with `--max-units-per-job 46 --max-concurrent-jobs 8 --wait-for-capacity 3000` (98 jobs per variant; `mismatch` first job `klt-sim-e1df254992d0`, `control` first job `klt-sim-d219f57f492e`; all 196 jobs `done`, no `--resume` needed, no `lost_shard`). Graded with `klt yield-samples ... --negative-control ... --format json` then `klt yield --format json`. Report sha256: `mismatch` `30e7309a...c422a438`, `control` `5d43e2a2...e18942f261`, derived `samples.json` `2d3dcb8b...c91e`, `yield.json` (as committed, before the `<work>` path scrub) `6730f824...ac4`. | **Campaign complete (4500 / 4500 passed per variant, 0 errored), grading `unmet`.** Seed 20261017, N=4500 per measurement, `sample_size.verdict` `sufficient` on all 9 measurements, empirical yield 1.0 (lower bound 99.918 % at 95 %). Within each of the 45 PVT points the `control` sigma is exactly 0 and the `mismatch` sigma is non-zero (e.g. `vth_cm080_mv` 0.0057 at `tt/2.970V/-40C`, against limits +/-200). `klt yield` nevertheless reports `negative_control.verdict = not_detected` (`degradation_detected: false`) on every measurement: its negative control must be a seeded *known-bad* variant whose yield degrades, and `sw_stat_mismatch = 0` is a better-than-nominal variant, so nominal and control yields are both 1.0 and statistically indistinguishable. Nothing here is a failure of the receiver: no sample left its limits. It is also not `6.analog` evidence: a degraded control (for example an injected input offset sized to push some samples out of limits) has to be designed and run, which changes the control variant in `build_requests.py` and is outside this PR. Normality is rejected (Anderson-Darling) and samples are pooled across 45 corners; the empirical estimate is the one to read. |
| 2026-11-02 | `mismatch` only, throwaway `uvx --from klayout-tools==0.8.0 klt sim --backend batch` (0.8.0 was uploaded 2026-10-24, after the #4019 merge of 2026-10-21), `--timeout-s 75 --max-units-per-job 46 --max-concurrent-jobs 8 --wait-for-capacity 3000`; 98 jobs. Run 1 first job `klt-sim-9c8ea782c148`; resume 1 and resume 2 (same flags plus `--resume`) re-submitted the lost shards (114 distinct job ids over the three invocations, e.g. `klt-sim-da89e3d33db5`, `klt-sim-ad6b0a47c058`, `klt-sim-3a2b1ad8bf5c`, `klt-sim-5b4d34950fb5`, `klt-sim-d5a97ec713ea`, `klt-sim-3537ad93dc0d`, `klt-sim-08f86a70c41b`) | **Outcome C, incomplete.** Run 1: 3404 / 4500 units passed, 1096 `lost_shard`. Resume 1: 4317 / 4500 passed, 183 not (`batch_job_interrupted` 137, `batch_poll_timeout` 46). Resume 2 refused: `--resume: shard map ... was written for a different request` (resume 1 had rewritten the shard map for the 183 remaining units; filed as klayout-tools#4821). Many jobs hit Spot `interrupted` after 676-1598 s. No unit failed a limit; the sample set is incomplete (4317 of 4500, so some PVT points have fewer than 100 draws) and is **not** evidence for `6.analog`. `control` was not submitted (it follows a finished `mismatch`); `klt yield` was not run. The `[yield]` extra still does not resolve (klt-yield-native not on the package index; tracked as klayout-tools#4671), so grading needs another route. No local grid was run. |
| 2026-10-21 | none submitted (issue #189 Revision 3 step 1) | Not run, outcome C. The klayout-tools#4018 fix landed as PR #4019 (merge commit `e345e690cab3`, 2026-10-21T01:51:46Z), but the latest release is v0.7.0 (PyPI upload 2026-10-08, 2396 commits behind that merge); no released `klayout-tools` carries it. Running the campaign on an unfixed tool would repeat the `lost_shard` / stalled-resume attempts above, so no fleet job was submitted and no local grid was run. Resubmit with a release that contains #4019. |
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
  when the fleet is quiet and with a released `klayout-tools` that contains the
  klayout-tools#4018 fix (PR #4019; not in v0.7.0).
- Do not lower N or drop PVT points to get a result; a reduced run is a pilot
  and is never cited as `6.analog`.

What remains for `6.analog` (issue #189): a deterministic negative control that
`klt yield` can detect as degraded, then regrade. The N >= 100 sample set and
the nominal `mismatch` campaign above need not be rerun for that.
