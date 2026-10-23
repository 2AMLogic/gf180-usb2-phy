# se-receiver-mc — Monte Carlo for the single-ended D+/D− receivers (T1 item 6, analog)

Classification and rationale: `spec/decisions/0007-analog-statistical-rows.md`
§4 (VIL < 0.8 V, VIH > 2.0 V; statistical, lower risk). The 45-corner matrices
in `sim/se-receiver-dp-thresholds/` and `sim/se-receiver-dm-thresholds/` cannot
validate a mismatch-driven row alone.

`build_requests.py` writes, for each receiver (`dp`, `dm`), two `klt sim`
requests (one self-contained `body.spice` each, DUT and testbench taken
unmodified from the corner-run benches). Same shape as
`sim/diff-receiver-mc/`, whose builder it reuses:

| variant | deck switch | purpose |
|---|---|---|
| `mismatch` | `sw_stat_mismatch = 1` | measurement: N samples at each of the 45 PVT points, `vary: "mismatch"`, recorded seed |
| `control` | `sw_stat_mismatch = 0` | deterministic negative control: same seeds, mismatch off; every sigma must be exactly 0 |

The measurements come from the `klt_measure` hooks in each bench's `tb.json`;
limits are copied from that bench's `checks`. Nothing is widened.

## Run (fleet only)

```bash
python3 sim/se-receiver-mc/build_requests.py "$WORK" --n 100
for side in dp dm; do
  klt sim --dry-run --backend batch "$WORK/$side/mismatch/request.json"
  klt sim --backend batch --format json -o "$WORK/$side/mismatch/out" "$WORK/$side/mismatch/request.json" > "$WORK/$side/mismatch/report.json"
  klt sim --backend batch --format json -o "$WORK/$side/control/out"  "$WORK/$side/control/request.json"  > "$WORK/$side/control/report.json"
  klt yield-samples "$WORK/$side/mismatch/report.json" --negative-control "$WORK/$side/control/report.json" > "$WORK/$side/samples.json"
  klt yield "$WORK/$side/samples.json"
done
```

`klt yield` needs the native extension; use a throwaway environment
(`uvx --from "klayout-tools[yield]" klt yield ...`), not the host tool. If a
batch submit fails, report the error — do not run a local grid.

## Status: no result recorded yet

Both receivers' requests pass `klt sim --dry-run --backend batch` (n=100). The
fleet campaign and `klt yield` are deliberately **not** run yet: they wait for
the differential-receiver campaign of issue #189 to produce a result (they share
the fleet path and the install route). Until then no samples, yield report or
record exist, so **`6.analog` is not claimed** for the single-ended rows.
