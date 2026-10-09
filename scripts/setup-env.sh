#!/usr/bin/env bash
#
# scripts/setup-env.sh -- pin and provision this repo's digital verification
# environment.
#
#   1. Creates a local .venv (Python) and installs `klayout-tools` (`klt`)
#      into it at the pinned git revision below.
#   2. Fetches the pinned `gf180mcu` PDK version via `volare` into
#      `${PDK_ROOT:-$HOME/.volare}`.
#   3. Reports -- with an actionable message, never a Python traceback --
#      which of `iverilog`, `yosys`, `openroad` are missing from `$PATH`.
#
# Ported from `2AMLogic/sky130-modexp`'s `scripts/setup-env.sh` (the pattern
# named in this repo's CLAUDE.md "Harness bootstrap" section) and re-targeted
# from the sky130A PDK to gf180mcu -- see issue #7.
#
# Exit codes:
#   0  venv + klt + PDK provisioned. iverilog/yosys/openroad may still be
#      individually reported missing (see step 3's summary) -- this is not
#      itself a failure, since PDK-heavy legs (synthesis, P&R) are
#      documented as locally-run-and-recorded, not a CI/setup requirement.
#      P&R specifically needs `openroad`; see docs/environment-setup.md.
#   1  venv creation, klt install, or PDK fetch failed.
#
# --tool-light: a reduced mode for audit/lint hosts. Provisions the same
#   .venv with the pinned klt and cocotb==2.0.1 (matching CI), but performs
#   no volare install, no PDK directory creation and no PDK fetch, and does
#   not need yosys/openroad. It requires iverilog and vvp on $PATH (it never
#   installs system packages) and exits 1 with an install hint if absent.
#   Success means the prerequisites are usable; it is NOT verification
#   evidence -- run `npm run lint` / `npm run check:ci` separately.
#
# Usage:
#   ./scripts/setup-env.sh
#   ./scripts/setup-env.sh --pdk-root=/custom/path
#   ./scripts/setup-env.sh --tool-light
#
# The resolved versions this script pins are recorded in
# docs/environment-setup.md -- update both together if you re-pin.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}" || exit 1

# --- pinned versions -- keep in sync with docs/environment-setup.md -------
KLT_REPO="https://github.com/2AMLogic/klayout-tools"
KLT_REV="e8ca621a6961879cec1af60cc932c3b3d58ddcaa"
VOLARE_PDK_FAMILY="gf180mcu"
VOLARE_GF180MCU_VERSION="c6d73a35f524070e85faff4a6a9eef49553ebc2b"
# ----------------------------------------------------------------------------

PDK_ROOT="${PDK_ROOT:-${HOME}/.volare}"
VENV_DIR="${REPO_ROOT}/.venv"
COCOTB_PIN="2.0.1"
TOOL_LIGHT=0

for arg in "$@"; do
  case "${arg}" in
    --pdk-root)
      echo "error: --pdk-root requires a value, e.g. --pdk-root=/path" >&2
      exit 1
      ;;
    --pdk-root=*)
      PDK_ROOT="${arg#--pdk-root=}"
      ;;
    --tool-light)
      TOOL_LIGHT=1
      ;;
    -h|--help)
      sed -n '2,/^# The resolved/p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *)
      echo "unknown option: ${arg}" >&2
      exit 1
      ;;
  esac
done

status=0

if [ "${TOOL_LIGHT}" = "1" ]; then
  TOTAL=2
else
  TOTAL=3
fi

echo "== 1/${TOTAL} python venv =="
# cocotb 2.0.1 (pinned by klt) refuses to build on Python > 3.13 with a
# RuntimeError, not a graceful skip -- pick a compatible interpreter up
# front so that failure surfaces here, as an actionable message, rather
# than as a pip build-backend traceback in step 2.
PYTHON_BIN=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
  found="$(command -v "${candidate}" || true)"
  if [ -z "${found}" ]; then
    continue
  fi
  ver="$("${found}" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null)"
  major="${ver%%.*}"
  minor="${ver##*.}"
  if [ "${major}" = "3" ] && [ "${minor}" -le 13 ] 2>/dev/null; then
    PYTHON_BIN="${found}"
    break
  fi
done

if [ -z "${PYTHON_BIN}" ]; then
  echo "FATAL: no Python <= 3.13 interpreter found on \$PATH."
  echo "  cocotb 2.0.1 (the version klt pins) refuses to build on Python 3.14+."
  echo "  -> install a compatible interpreter, e.g.:"
  echo "       brew install python@3.13   (macOS/Homebrew)"
  echo "       uv python install 3.13     (if 'uv' is available)"
  echo "       apt-get install python3.13 (Debian/Ubuntu with deadsnakes/backports)"
  echo "     then re-run this script; it prefers python3.13 > 3.12 > 3.11 >"
  echo "     3.10 > plain python3 automatically once one exists on \$PATH."
  exit 1
fi
echo "python3: $(${PYTHON_BIN} --version 2>&1) (${PYTHON_BIN})"

if [ ! -d "${VENV_DIR}" ]; then
  if ! "${PYTHON_BIN}" -m venv "${VENV_DIR}"; then
    echo "FATAL: 'python3 -m venv ${VENV_DIR}' failed."
    echo "  -> on Debian/Ubuntu this usually means the venv module is"
    echo "     missing: 'apt-get install python3-venv'."
    exit 1
  fi
  echo "created ${VENV_DIR}"
else
  echo "reusing existing ${VENV_DIR}"
fi

VENV_PY="${VENV_DIR}/bin/python3"
VENV_PIP="${VENV_DIR}/bin/pip"
if [ ! -x "${VENV_PY}" ]; then
  echo "FATAL: ${VENV_PY} not found after venv creation -- venv looks corrupt."
  echo "  -> remove ${VENV_DIR} and re-run this script."
  exit 1
fi

echo
echo "== 2/${TOTAL} klayout-tools (klt) @ ${KLT_REV:0:12} =="
if ! "${VENV_PY}" -m pip --version >/dev/null 2>&1; then
  echo "FATAL: pip is not available inside ${VENV_DIR}."
  echo "  -> remove ${VENV_DIR} and re-run this script (venv bootstrap likely"
  echo "     failed partway through)."
  exit 1
fi

if ! "${VENV_PIP}" install --quiet --upgrade pip; then
  echo "WARNING: could not upgrade pip in ${VENV_DIR}; continuing with the"
  echo "  version venv bundled."
fi

if [ "${TOOL_LIGHT}" = "1" ]; then
  PKGS=("klayout-tools @ git+${KLT_REPO}@${KLT_REV}" "cocotb==${COCOTB_PIN}")
else
  PKGS=("klayout-tools @ git+${KLT_REPO}@${KLT_REV}" cocotb volare)
fi
if ! "${VENV_PIP}" install --quiet "${PKGS[@]}"; then
  echo "FATAL: failed to install ${PKGS[*]} into ${VENV_DIR}."
  echo "  -> common causes: no network access to ${KLT_REPO}, or no C/C++"
  echo "     toolchain for a dependency's native build (install Xcode CLI"
  echo "     tools on macOS: 'xcode-select --install'; build-essential on"
  echo "     Debian/Ubuntu)."
  echo "  -> re-run with the venv's own pip for a full traceback:"
  echo "       ${VENV_PIP} install ${PKGS[*]}"
  exit 1
fi
INSTALLED_KLT_VERSION="$("${VENV_PY}" -m klayout_tools.cli --version 2>/dev/null || true)"
INSTALLED_KLT_VERSION="${INSTALLED_KLT_VERSION#klt }"
echo "installed: klt ${INSTALLED_KLT_VERSION:-(version unknown)} from ${KLT_REPO}@${KLT_REV:0:12}"
echo "activate with: source ${VENV_DIR}/bin/activate"

if [ "${TOOL_LIGHT}" = "1" ]; then
  echo
  echo "== tool-light prerequisite check =="
  fail=0
  if [ ! -x "${VENV_DIR}/bin/klt" ]; then
    echo "FATAL: ${VENV_DIR}/bin/klt not found after install."
    fail=1
  else
    echo "  klt:      $("${VENV_DIR}/bin/klt" --version 2>&1 | head -1)"
  fi
  COCOTB_VER="$("${VENV_PY}" -c 'import importlib.metadata as m; print(m.version("cocotb"))' 2>/dev/null || true)"
  if [ "${COCOTB_VER}" != "${COCOTB_PIN}" ]; then
    echo "FATAL: cocotb ${COCOTB_VER:-(missing)} in ${VENV_DIR}, expected ${COCOTB_PIN}."
    echo "  -> remove ${VENV_DIR} and re-run this script."
    fail=1
  else
    echo "  cocotb:   ${COCOTB_VER}"
  fi
  echo "  python:   $("${VENV_PY}" --version 2>&1)"
  for tool in iverilog vvp; do
    if command -v "${tool}" >/dev/null 2>&1; then
      echo "  ${tool}: $(${tool} -V 2>&1 | head -1)"
    else
      echo "FATAL: ${tool} not found on \$PATH (Icarus Verilog)."
      echo "  -> install it as the host administrator: 'apt-get install iverilog'"
      echo "     (Debian/Ubuntu) or 'brew install icarus-verilog' (macOS). This"
      echo "     script never installs system packages."
      fail=1
    fi
  done
  echo
  if [ "${fail}" -ne 0 ]; then
    echo "RESULT: tool-light prerequisites NOT satisfied -- see FATAL messages above."
    exit 1
  fi
  echo "RESULT: tool-light environment ready (venv + klt + cocotb ${COCOTB_PIN} + iverilog/vvp)."
  echo "  No PDK was fetched. Next, as separate verification steps:"
  echo "    source ${VENV_DIR}/bin/activate && npm run lint && npm run check:ci"
  exit 0
fi

echo
echo "== 3/${TOTAL} gf180mcu PDK (volare ${VOLARE_GF180MCU_VERSION:0:12}) =="
mkdir -p "${PDK_ROOT}"
if "${VENV_DIR}/bin/volare" enable \
    --pdk-root "${PDK_ROOT}" --pdk "${VOLARE_PDK_FAMILY}" \
    "${VOLARE_GF180MCU_VERSION}"; then
  echo "gf180mcu ready under ${PDK_ROOT}"
else
  echo "FATAL: 'volare enable' failed to fetch gf180mcu ${VOLARE_GF180MCU_VERSION:0:12}."
  echo "  -> common causes: no network access to GitHub releases, or a rate"
  echo "     limit on unauthenticated GitHub API requests -- set GITHUB_TOKEN"
  echo "     and re-run, or run manually:"
  echo "       ${VENV_DIR}/bin/volare enable --pdk-root ${PDK_ROOT} --pdk ${VOLARE_PDK_FAMILY} ${VOLARE_GF180MCU_VERSION}"
  status=1
fi

echo
echo "== toolchain check (iverilog / yosys / openroad) =="
missing=()
for tool in iverilog yosys openroad; do
  if command -v "${tool}" >/dev/null 2>&1; then
    case "${tool}" in
      iverilog) echo "  iverilog: $(iverilog -V 2>&1 | head -1)" ;;
      yosys)    echo "  yosys:    $(yosys -V 2>&1 | head -1)" ;;
      openroad) echo "  openroad: $(openroad -version 2>&1 | head -1)" ;;
    esac
  else
    missing+=("${tool}")
  fi
done

if [ "${#missing[@]}" -gt 0 ]; then
  echo
  echo "MISSING TOOLS: ${missing[*]}"
  for tool in "${missing[@]}"; do
    case "${tool}" in
      iverilog)
        echo "  - iverilog (Icarus Verilog): 'brew install icarus-verilog' (macOS)"
        echo "    or 'apt-get install iverilog' (Debian/Ubuntu). Required for"
        echo "    'klt functional-verification'."
        ;;
      yosys)
        echo "  - yosys: 'brew install yosys' (macOS) or 'apt-get install yosys'"
        echo "    (Debian/Ubuntu). Required for 'klt synthesize'."
        ;;
      openroad)
        echo "  - openroad: no package-manager formula on macOS or common Linux"
        echo "    distros as of this writing. Options:"
        echo "      * precompiled binaries / docker image:"
        echo "        https://github.com/The-OpenROAD-Project/OpenROAD#install"
        echo "        (e.g. 'docker pull openroad/orfs' for the flow-scripts image)"
        echo "      * build from source via OpenROAD-flow-scripts:"
        echo "        https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts"
        echo "        ('./build_openroad.sh --local')"
        echo "    Required for 'klt place-and-route' (not yet exercised in this"
        echo "    repo -- see flow/README.md)."
        ;;
    esac
  done
  echo
  echo "This is expected and non-fatal for this script: the functional-"
  echo "verification suite and record linter need only iverilog and"
  echo "python3+git. synthesis needs yosys; place-and-route additionally"
  echo "needs openroad -- see verification/README.md and flow/README.md."
else
  echo "all of iverilog/yosys/openroad found on \$PATH."
fi

echo
if [ "${status}" -eq 0 ]; then
  echo "RESULT: environment provisioned (venv + klt + gf180mcu)."
else
  echo "RESULT: environment provisioning incomplete -- see FATAL messages above."
fi
exit "${status}"
