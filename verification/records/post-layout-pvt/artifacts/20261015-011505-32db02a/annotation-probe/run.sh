#!/usr/bin/env bash
#
# SPEF annotation probe for the #131 post-layout-pvt record. Adapted from
# 20261008-195826-74ccfac/annotation-probe/run.sh: same probe.tcl, but only
# the record's own SPEF is probed (the as-extracted / hub-repaired variants
# were diagnostics for the old SPEF and are not repeated). Run from the
# repo root with a native `openroad` on $PATH:
#
#   verification/records/post-layout-pvt/artifacts/20261015-011505-32db02a/annotation-probe/run.sh
set -euo pipefail
here="verification/records/post-layout-pvt/artifacts/20261015-011505-32db02a/annotation-probe"
new_spef="verification/records/post-layout-pvt/artifacts/20261015-011505-32db02a/usb_utmi_phy_route.spef"
pdk_root="${PDK_ROOT:-$HOME/.volare}"
mkdir -p flow/.klt/probe
wrapper="flow/.klt/probe/wrapper.tcl"   # git-ignored scratch, overwritten per corner
for corner in tt_025C_1v80 ss_125C_1v62 ff_n40C_5v50; do
  printf 'set pdk_root {%s}\nset corner {%s}\nset spef {%s}\nsource %s/probe.tcl\n' \
    "$pdk_root" "$corner" "$new_spef" "$here" > "$wrapper"
  log="${here}/probe-${corner}-def-pins.txt"
  openroad -no_init -exit "$wrapper" > "$log" 2>&1 || { echo "probe failed: $corner" >&2; exit 1; }
  pre="$(sed -n '/^===PROBE_PRE_BEGIN===$/,/^===PROBE_PRE_END===$/p' "$log" | sed '1d;$d')"
  post="$(sed -n '/^===PROBE_POST_BEGIN===$/,/^===PROBE_POST_END===$/p' "$log" | sed '1d;$d')"
  if [ "$pre" = "$post" ]; then same="paths-identical-before/after-read_spef"; else same="paths-changed-by-read_spef"; fi
  printf '%s def-pins %s ' "$corner" "$same"
  grep -E '^worst slack (max|min)|^Found [0-9]+ (unannotated|partially)| Wire capacitance' "$log" | tr -s ' ' | tr '\n' ' '
  echo
done
