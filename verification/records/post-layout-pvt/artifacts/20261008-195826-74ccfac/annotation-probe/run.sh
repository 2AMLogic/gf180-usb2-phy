#!/usr/bin/env bash
#
# SPEF annotation probe for record 20261008-195826-74ccfac (PR #104
# review of record 20261008-200000-8139bb6). Run from the repo root:
#
#   OPENROAD_DOCKER_CMD='sudo -n docker' \
#     verification/records/post-layout-pvt/artifacts/20261008-195826-74ccfac/annotation-probe/run.sh
#
# Needs the pinned openroad/orfs image (scripts/openroad-docker.sh) and the
# gf180mcuD PDK under $PDK_ROOT (default ~/.volare). For each of the three
# liberty corners it runs probe.tcl once per SPEF:
#   *-as-extracted.txt  record 20261008-200000-8139bb6's SPEF, unchanged
#                       (extracted without --def-pins)
#   *-hub-repaired.txt  that same SPEF after repair_spef_hub_nodes.py
#                       (diagnostic only; written to flow/.klt/probe/,
#                       which is git-ignored, and not committed)
#   *-def-pins.txt      this record's SPEF (re-extracted with --def-pins)
# The logs are overwritten in place. Runs are sequential.
set -euo pipefail
here="verification/records/post-layout-pvt/artifacts/20261008-195826-74ccfac/annotation-probe"
old_spef="verification/records/post-layout-pvt/artifacts/20261008-200000-8139bb6/usb_utmi_phy_route.spef"
new_spef="verification/records/post-layout-pvt/artifacts/20261008-195826-74ccfac/usb_utmi_phy_route.spef"
repaired="flow/.klt/probe/repaired.spef"
pdk_root="${PDK_ROOT:-$HOME/.volare}"

mkdir -p "$(dirname "$repaired")"
python3 -I "${here}/repair_spef_hub_nodes.py" "$old_spef" layout/digital/usb_utmi_phy.def "$repaired"
sha256sum "$old_spef" "$repaired" "$new_spef"

run_one() {  # <corner> <spef> <log>
  local wrapper
  wrapper="$(mktemp -p . .probe-XXXXXX.tcl)"
  printf 'set pdk_root {%s}\nset corner {%s}\nset spef {%s}\nsource %s/probe.tcl\n' \
    "$pdk_root" "$1" "$2" "$here" > "$wrapper"
  PDK_ROOT="$pdk_root" ./scripts/openroad-docker.sh -no_init -exit "$wrapper" > "$3" 2>&1 \
    || { rm -f "$wrapper"; echo "probe failed: $1 $2 (see $3)" >&2; return 1; }
  rm -f "$wrapper"
}

for corner in tt_025C_1v80 ss_125C_1v62 ff_n40C_5v50; do
  run_one "$corner" "$old_spef" "${here}/probe-${corner}-as-extracted.txt"
  run_one "$corner" "$repaired" "${here}/probe-${corner}-hub-repaired.txt"
  run_one "$corner" "$new_spef" "${here}/probe-${corner}-def-pins.txt"
  for kind in as-extracted hub-repaired def-pins; do
    log="${here}/probe-${corner}-${kind}.txt"
    pre="$(sed -n '/^===PROBE_PRE_BEGIN===$/,/^===PROBE_PRE_END===$/p' "$log" | sed '1d;$d')"
    post="$(sed -n '/^===PROBE_POST_BEGIN===$/,/^===PROBE_POST_END===$/p' "$log" | sed '1d;$d')"
    if [ "$pre" = "$post" ]; then same="paths-identical-before/after-read_spef"; else same="paths-changed-by-read_spef"; fi
    printf '%s %-12s %s ' "$corner" "$kind" "$same"
    grep -E '^worst slack (max|min)|^Found [0-9]+ (unannotated|partially)| Wire capacitance' "$log" | tr -s ' ' | tr '\n' ' '
    echo
  done
done
