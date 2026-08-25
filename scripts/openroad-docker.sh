#!/usr/bin/env bash
#
# scripts/openroad-docker.sh -- invoke the pinned openroad/orfs Docker
# image's `openroad` binary as if it were a native `openroad` on $PATH.
#
# Why a container, not a native install: `openroad` has no Homebrew formula
# and no common Linux-distro package as of this writing (see
# docs/environment-setup.md's "OpenROAD" section). OpenROAD-flow-scripts
# (ORFS) publishes an official Docker image with a matched, pinned
# OpenROAD + Yosys + KLayout toolchain. Ported, near-verbatim, from
# `sky130-modexp`'s `scripts/openroad-docker.sh` (the digital half of
# issue #2's harness bootstrap, per `CLAUDE.md`) -- same mechanism, no
# sky130-specific content (the pinned image is PDK-agnostic; `klt
# place-and-route` resolves the gf180mcu LEF/liberty deck itself, per
# `flow/request-usb-utmi-phy-par.json`).
#
# Usage (identical to a native `openroad` binary):
#   ./scripts/openroad-docker.sh -version
#   ./scripts/openroad-docker.sh -no_init -exit script.tcl
#
# The current working directory is bind-mounted into the container at the
# *same absolute path* it has on the host (not at a fixed /workspace) --
# both the mount source and target are ${MOUNT_DIR}, and the container's
# working directory is set to that same path. This matters beyond relative
# paths: `klt place-and-route` (klayout-tools) generates its per-stage Tcl
# scripts with **absolute host paths** baked in throughout -- the netlist,
# LEF/liberty deck, and every `-metrics`/`write_db`/`write_def` output path
# are all `os.path.abspath()`-resolved before being written into the script
# or passed as an `openroad` CLI argument. Mounting source==target for both
# the repo tree and the resolved PDK root (below) is what makes those
# absolute paths resolve identically on both sides of the container
# boundary. Set OPENROAD_DOCKER_MOUNT to bind-mount a different host
# directory instead of $(pwd).
#
# -- pinned version -- keep in sync with docs/environment-setup.md ----------
# `openroad -version` inside this image reports 26Q3-1260-g06a5a02279.
OPENROAD_DOCKER_IMAGE="${OPENROAD_DOCKER_IMAGE:-openroad/orfs:26Q3-296-gda37dce1c}"
OPENROAD_DOCKER_DIGEST="${OPENROAD_DOCKER_DIGEST:-sha256:ebc8142da6d65d1a1e9a528aa2cedcde356243465dd859af8d3ade51075f8cb2}"
# -----------------------------------------------------------------------------

set -euo pipefail

DOCKER_BIN="${OPENROAD_DOCKER_CMD:-docker}"

# `OPENROAD_DOCKER_CMD` is documented (below, and in
# docs/environment-setup.md) as accepting a *wrapper* -- e.g. `sudo -n
# docker` on a host where the invoking user is not in the `docker` group.
# A multi-word wrapper is not an executable name, so `command -v` must be
# given only its first word, and the daemon-reachability probe and the
# final `docker run` must expand the whole string as argv (word-split on
# purpose -- hence the deliberate lack of quotes at those two call sites).
DOCKER_PROG="${DOCKER_BIN%% *}"

if ! command -v "${DOCKER_PROG}" >/dev/null 2>&1; then
  echo "FATAL: '${DOCKER_PROG}' not found on \$PATH." >&2
  echo "  openroad is provisioned on this host only via the pinned" >&2
  echo "  ${OPENROAD_DOCKER_IMAGE} Docker image -- install Docker and" >&2
  echo "  re-run. See docs/environment-setup.md's 'OpenROAD' section." >&2
  echo "  Set OPENROAD_DOCKER_CMD if docker needs a wrapper (e.g. 'sudo" >&2
  echo "  docker') to reach the daemon on this host." >&2
  exit 1
fi

# shellcheck disable=SC2086  # deliberate word-split: see DOCKER_PROG above
if ! ${DOCKER_BIN} info >/dev/null 2>&1; then
  echo "FATAL: docker daemon is not reachable." >&2
  exit 1
fi

MOUNT_DIR="${OPENROAD_DOCKER_MOUNT:-$(pwd)}"

# Resolve the PDK root the same way klayout-tools' `find_pdk()` does
# ($PDK_ROOT env var, then ~/.ciel, then ~/.volare) so it can be bind-
# mounted too -- `klt place-and-route`/`klt synthesize` resolve
# liberty/LEF paths under there, and those absolute host paths need to
# exist inside the container at the identical path (see comment block
# above). Best-effort: if none of these exist, no extra mount is added and
# a downstream `openroad` "cannot read file" error will point at the same
# gap this comment describes.
PDK_MOUNT_DIR=""
if [ -n "${PDK_ROOT:-}" ] && [ -d "${PDK_ROOT}" ]; then
  PDK_MOUNT_DIR="${PDK_ROOT}"
elif [ -d "${HOME}/.ciel" ]; then
  PDK_MOUNT_DIR="${HOME}/.ciel"
elif [ -d "${HOME}/.volare" ]; then
  PDK_MOUNT_DIR="${HOME}/.volare"
fi

VOLUME_ARGS=(-v "${MOUNT_DIR}:${MOUNT_DIR}")
if [ -n "${PDK_MOUNT_DIR}" ] && [ "${PDK_MOUNT_DIR}" != "${MOUNT_DIR}" ]; then
  VOLUME_ARGS+=(-v "${PDK_MOUNT_DIR}:${PDK_MOUNT_DIR}")
fi

# `~/.ciel`'s PDK install stores its real content under a versioned
# `ciel/gf180mcu/versions/<sha>/...` tree with the per-variant directories
# (`gf180mcuA`/`B`/`C`/`D`) symlinked into it -- if those symlinks are
# absolute (as ciel's own layout uses), the container needs that target
# path bind-mounted too, at the identical host path, or the symlink
# resolves to nothing inside the container. Resolve it defensively rather
# than assuming a relative symlink.
if [ -n "${PDK_MOUNT_DIR}" ] && [ -L "${PDK_MOUNT_DIR}/gf180mcuD" ]; then
  REAL_TARGET="$(readlink -f "${PDK_MOUNT_DIR}/gf180mcuD" 2>/dev/null || true)"
  if [ -n "${REAL_TARGET}" ] && [ "${REAL_TARGET#${PDK_MOUNT_DIR}}" = "${REAL_TARGET}" ]; then
    CIEL_ROOT="${PDK_MOUNT_DIR}/ciel"
    if [ -d "${CIEL_ROOT}" ]; then
      VOLUME_ARGS+=(-v "${CIEL_ROOT}:${CIEL_ROOT}")
    fi
  fi
fi

# Forward a small allowlist of ORFS/OpenROAD-relevant env vars from the host
# shell into the container, if set there. `docker run -e VAR` with VAR
# unset in the calling shell is a harmless no-op, not an error.
ENV_ARGS=(-e PLATFORM_DIR -e PDK_ROOT)

# shellcheck disable=SC2086  # deliberate word-split: see DOCKER_PROG above
exec ${DOCKER_BIN} run --rm --platform linux/amd64 \
  "${VOLUME_ARGS[@]}" \
  -w "${MOUNT_DIR}" \
  "${ENV_ARGS[@]}" \
  "${OPENROAD_DOCKER_IMAGE}@${OPENROAD_DOCKER_DIGEST}" \
  bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1 && exec openroad "$@"' bash "$@"
