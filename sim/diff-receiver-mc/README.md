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

The `--dry-run` of both requests validates (n=2: 90 units). The first fleet
submission (n=2, `mismatch` variant, job `klt-sim-7272c1a5d04f`) was **not
completed**: the job went `interrupted` (Spot reclaim) about 200 s in and
stayed there for over 25 min; the client was then terminated while waiting
(`batch_client_interrupted`). No local fallback grid was run. No samples,
`klt yield` report or record exist, so **`6.analog` is not claimed**. The
campaign (N ≥ 100 per corner point, both variants, `klt yield`) is the
remaining work of issue #189.
