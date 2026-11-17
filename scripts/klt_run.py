#!/usr/bin/env python3
"""The npm scripts' klt invocation: resolution + version gate (issue #438).

`npm run test` and `npm run check:all` used to invoke a bare ``klt`` from
``$PATH`` -- no resolution, no pin check -- the same shape of hole PR #430
opened for the Python harnesses and issue #431 closed for them. This
wrapper gives the npm scripts the same two halves every harness gets from
``scripts/klt_resolve.py``, so the invocation and its defense cannot
drift:

* **resolution** -- ``klt_argv()`` prefers the *interpreter's own* klt
  (``python -m klayout_tools.cli``), so a venv run can never pick up a
  different klt from ``$PATH``; a plain ``klt`` is the fallback only when
  ``klayout_tools`` is not importable.
* **gating** -- the resolved klt's own ``--version`` must report the
  repo's pin (``KLT_VERSION=`` in ``scripts/setup-env.sh``, the single
  source of truth), so the fallback branch cannot silently run an
  unpinned build. The gate runs *before* the requested command, and a
  mismatch fails loudly naming both versions.

The requested arguments are passed to klt verbatim, stdout/stderr are not
captured, and klt's exit status is the wrapper's -- so ``npm``'s ``&&``
chains keep their meaning and CI log output is unchanged.

Usage (in package.json; arguments after the wrapper go to klt):
    python3 scripts/klt_run.py functional-verification verification/request-usb-nrzi-encoder.json --format json
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from klt_resolve import (  # noqa: E402
    KltVersionError,
    klt_argv,
    normalize_version,
    pinned_klt_version,
)


def resolve_gated_klt() -> list[str]:
    """The klt argv the requested command may run under, after the gate.

    Resolution is ``klt_resolve.klt_argv()``; the gate refuses anything
    whose ``--version`` does not report the repo pin. Returns the argv,
    or raises ``SystemExit`` with an actionable message.
    """
    klt = klt_argv()
    try:
        pinned = pinned_klt_version(klt=klt)
    except KltVersionError as exc:
        raise SystemExit(f"error: {exc}") from exc
    try:
        proc = subprocess.run(klt + ["--version"], capture_output=True, text=True)
    except OSError as exc:
        raise SystemExit(
            f"error: `{' '.join(klt)} --version` did not run: {exc}; "
            "re-run inside the pinned environment (./scripts/setup-env.sh)"
        ) from exc
    tokens = (proc.stdout or "").strip().split()
    found = tokens[-1] if proc.returncode == 0 and tokens else ""
    if not found:
        raise SystemExit(
            f"error: `{' '.join(klt)} --version` reported no version "
            f"(exit {proc.returncode}): "
            f"{(proc.stderr or proc.stdout or '').strip()[:200]}"
        )
    if normalize_version(found) != normalize_version(pinned):
        raise SystemExit(
            f"error: this klt reports {found}, but this repo pins klt "
            f"{pinned} (KLT_VERSION in scripts/setup-env.sh); re-run "
            "inside the pinned environment (./scripts/setup-env.sh)"
        )
    return klt


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: klt_run.py <klt arguments...>", file=sys.stderr)
        return 2
    klt = resolve_gated_klt()
    return subprocess.run(klt + argv).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
