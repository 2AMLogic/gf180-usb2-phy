#!/usr/bin/env bash
#
# scripts/test_setup_env.sh -- shell regression test for scripts/setup-env.sh
# mode selection and failure behaviour. Uses stub executables on an isolated
# PATH: no network, no real pip/volare/PDK, nothing outside a temp dir.
#
#   ./scripts/test_setup_env.sh
#
# Exits 0 when all cases pass. This does NOT exercise a real bootstrap.

set -uo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/setup-env.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
fails=0

# new_case NAME -> sets CASE (fake repo copy), BIN (stub dir), LOG, HOME
new_case() {
  CASE="${TMP}/$1"; BIN="${CASE}/bin"; LOG="${CASE}/calls.log"
  mkdir -p "${CASE}/repo/scripts" "${BIN}" "${CASE}/home"
  cp "${SRC}" "${CASE}/repo/scripts/setup-env.sh"
  : > "${LOG}"
  for t in dirname sed head mkdir cat cp chmod; do ln -s "$(command -v "$t")" "${BIN}/$t"; done
  export HOME="${CASE}/home" PDK_ROOT="${CASE}/pdk" STUB_LOG="${LOG}"
  unset STUB_PIP_FAIL STUB_COCOTB STUB_PYVER
  # Stub interpreter (system and venv): handles the calls setup-env.sh makes.
  cat > "${BIN}/python3.13" <<'PY'
#!/bin/bash
case "$*" in
  *"sys.version_info"*) echo "${STUB_PYVER:-3.13}" ;;
  "-m venv "*) d="${*:3}"; mkdir -p "$d/bin"
     cp "$0" "$d/bin/python3"; printf '#!/bin/sh\necho "pip $*" >>"$STUB_LOG"\n[ -n "$STUB_PIP_FAIL" ] && exit 1\nexit 0\n' >"$d/bin/pip"
     printf '#!/bin/sh\necho "volare $*" >>"$STUB_LOG"\n' >"$d/bin/volare"
     printf '#!/bin/sh\necho "klt 0.0-stub"\n' >"$d/bin/klt"
     chmod +x "$d/bin/pip" "$d/bin/volare" "$d/bin/klt" ;;
  "-m pip --version") echo pip-stub ;;
  *"klayout_tools.cli"*) echo "klt 0.0-stub" ;;
  *"m.version"*) echo "${STUB_COCOTB:-2.0.1}" ;;
  "--version") echo "Python ${STUB_PYVER:-3.13}.0" ;;
esac
PY
  chmod +x "${BIN}/python3.13"
}
add_icarus() { for t in iverilog vvp; do printf '#!/bin/sh\necho "%s stub 1.0"\n' "$t" >"${BIN}/$t"; chmod +x "${BIN}/$t"; done; }
run() { OUT="$(cd "${CASE}/repo" && PATH="${BIN}" /bin/bash scripts/setup-env.sh "$@" 2>&1)"; RC=$?; }
check() { # desc, condition-exit
  if [ "$2" -eq 0 ]; then echo "ok   - $1"; else echo "FAIL - $1"; echo "$OUT" | sed 's/^/       | /'; fails=$((fails+1)); fi
}
has() { grep -q -- "$1" <<<"$OUT"; }
logged() { grep -q -- "$1" "${LOG}"; }

bash -n "${SRC}"; check "bash -n" $?
OUT="$(/bin/bash "${SRC}" --help)"; has -- '--tool-light'; check "--help lists --tool-light" $?

new_case light_ok; add_icarus; run --tool-light
[ $RC -eq 0 ]; check "tool-light succeeds with stubs" $?
has "cocotb:   2.0.1"; check "tool-light reports cocotb version" $?
logged 'cocotb==2.0.1'; check "tool-light pins cocotb==2.0.1" $?
! logged volare; check "tool-light never invokes volare" $?
[ ! -e "${PDK_ROOT}" ]; check "tool-light creates no PDK dir" $?
run --tool-light
[ $RC -eq 0 ] && has "reusing existing"; check "tool-light rerun with existing venv" $?

new_case light_noicarus; run --tool-light
[ $RC -ne 0 ] && has "iverilog not found" && has "vvp not found"; check "tool-light fails without iverilog/vvp" $?

new_case light_pipfail; add_icarus; export STUB_PIP_FAIL=1; run --tool-light
[ $RC -ne 0 ] && has FATAL; check "tool-light propagates pip failure" $?

new_case light_cocotb; add_icarus; export STUB_COCOTB=1.9.0; run --tool-light
[ $RC -ne 0 ] && has "expected 2.0.1"; check "tool-light rejects wrong cocotb" $?

new_case nopy; add_icarus; rm "${BIN}/python3.13"; run --tool-light
[ $RC -ne 0 ] && has "no Python <= 3.13"; check "tool-light fails with no Python" $?

new_case badpy; add_icarus; export STUB_PYVER=3.14; run --tool-light
[ $RC -ne 0 ] && has "no Python <= 3.13"; check "tool-light rejects Python 3.14" $?

new_case full; add_icarus; run
[ $RC -eq 0 ]; check "full mode succeeds with stubs" $?
logged 'volare enable'; check "full mode fetches PDK via volare" $?
[ -d "${PDK_ROOT}" ]; check "full mode creates PDK dir" $?
has "MISSING TOOLS: yosys openroad"; check "full mode keeps optional-tool reporting" $?

echo
if [ "${fails}" -eq 0 ]; then echo "all setup-env tests passed"; else echo "${fails} failure(s)"; exit 1; fi
