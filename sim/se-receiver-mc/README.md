# se-receiver-mc — Monte Carlo for the single-ended D+/D− receivers (T1 item 6, analog)

Classification and rationale: `spec/decisions/0007-analog-statistical-rows.md`
§4 (VIL < 0.8 V, VIH > 2.0 V; statistical, lower risk). The 45-corner matrices
in `sim/se-receiver-dp-thresholds/` and `sim/se-receiver-dm-thresholds/` cannot
validate a mismatch-driven row alone.

`build_requests.py` writes, for each receiver (`dp`, `dm`), four `klt sim`
requests (one self-contained `body.spice` each, DUT and testbench taken
unmodified from the corner-run benches). Same shape as
`sim/diff-receiver-mc/`, whose builder it reuses:

| variant | deck switch | purpose |
|---|---|---|
| `mismatch` | `sw_stat_mismatch = 1` | measurement: N samples at each of the 45 PVT points, `vary: "mismatch"`, recorded seed |
| `control` | `sw_stat_mismatch = 0` | deterministic negative control: same seeds, mismatch off; every sigma must be exactly 0 (not part of the graded campaign, see Status) |
| `degraded` | `sw_stat_mismatch = 1`, +0.9 V series offset on the input | seeded known-bad variant for `klt yield-samples --negative-control`: pulls the threshold below VIL, breaks `vth_v` and `out_at_vil` |
| `degraded_neg` | `sw_stat_mismatch = 1`, -0.9 V series offset on the input | the same for `out_at_vih` (and `vth_v`), which the +offset variant leaves in limits |

The measurements come from the `klt_measure` hooks in each bench's `tb.json`;
limits are copied from that bench's `checks`. Nothing is widened.

## Run (fleet only)

```bash
python3 sim/se-receiver-mc/build_requests.py "$WORK" --n 100 --timeout-s 75
for side in dp dm; do
  for v in mismatch degraded degraded_neg; do   # one variant at a time
    klt sim --dry-run --backend batch "$WORK/$side/$v/request.json"
    klt sim --backend batch --max-units-per-job 46 --max-concurrent-jobs 8 --wait-for-capacity 3000 \
      --format json -o "$WORK/$side/$v/out" "$WORK/$side/$v/request.json" > "$WORK/$side/$v/report.json"
  done
  klt yield-samples "$WORK/$side/mismatch/report.json" --negative-control "$WORK/$side/degraded/report.json" \
    --measurement vth_v --measurement out_at_vil --format json > "$WORK/$side/samples-pos.json"
  klt yield-samples "$WORK/$side/mismatch/report.json" --negative-control "$WORK/$side/degraded_neg/report.json" \
    --measurement out_at_vih --format json > "$WORK/$side/samples-neg.json"
  klt yield --format json "$WORK/$side/samples-pos.json" > "$WORK/$side/yield-degraded-pos.json"
  klt yield --format json "$WORK/$side/samples-neg.json" > "$WORK/$side/yield-degraded-neg.json"
done
```

`klt yield` needs the native extension; use a throwaway environment
(`uvx --from "klayout-tools[yield]==0.9.0" klt ...`), not the host tool. If a
batch submit fails, report the error; do not run a local grid. The two reports
per receiver each cover a subset of rows because `klt signoff` requires every
measurement in a cited report to detect its control.

## Status: `6.analog` met for the single-ended receivers (issue #212; 2026-11-05, 4500 units per variant)

| date | submission | outcome |
|---|---|---|
| 2026-11-05 | throwaway `uvx --from "klayout-tools[yield]==0.9.0" klt`, `build_requests.py --n 100 --timeout-s 75`, `klt sim --dry-run --backend batch` first, then each of `dp`/`dm` x `mismatch`/`degraded`/`degraded_neg` alone with `--max-units-per-job 46 --max-concurrent-jobs 8 --wait-for-capacity 3000` (98 jobs per variant, no `--resume`, no `lost_shard`; `dp` `mismatch` first job `klt-sim-3cec53dae673`). Report sha256 (first 12): `dp` `mismatch` `aad894784917`, `degraded` `6c96b1c28032`, `degraded_neg` `9b134fe9def3`; `dm` `mismatch` `f079faa9e35b`, `degraded` `003ff93c4cfa`, `degraded_neg` `f6f4a7d3da30`. Committed yield reports in `results/20261105-n100/{dp,dm}/`. | **Campaign complete and graded `met`.** Seed 20261017, N=4500 per measurement. `mismatch`: 4500 / 4500 pass for both receivers. `degraded` and `degraded_neg`: 4500 / 4500 fail, 0 errored (the known-bad offset pushes every sample out of limits, as designed). `sample_size.verdict` `sufficient`, empirical yield 1.0 (95 % lower bound 99.918 %) on all 3 measurements per receiver; negative control `detected` on all 3 (`vth_v`, `out_at_vil` against +offset; `out_at_vih` against -offset). `klt signoff --manifest` (klt 0.8.0, the CI pin) keeps `6.analog` `met` with the four new citations. Caveats: the `control` variant (`sw_stat_mismatch = 0`) was not run, as in the differential campaign's regrade; the controls are known-bad by construction and prove the detector, not receiver margin; the 0.9 V offset was chosen from the 1.2-1.5 V measured threshold spread so every sample leaves its limits, and was probed on one local single-unit run before the fleet submit. Ratified limits are unchanged. No local grid. |

Remaining after this record: the D+ pull-up row (PDK-blocked, DR-0007).
