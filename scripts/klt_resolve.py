#!/usr/bin/env python3
"""Resolve -- and version-gate -- the klt invocation every harness uses.

Why this module exists (issue #431): the harnesses used to default their
``--klt`` to a bare ``klt`` on ``$PATH``, so a run outside the pinned venv
silently graded with whatever klt came first on the path and nothing
cross-checked the result against the pin -- PR #430 froze an ERC record
claiming the pinned 0.9.0 while its artifacts came from 0.9.3.dev. Two
halves, shared here so they cannot drift per script:

* **resolution** -- :func:`klt_argv` prefers the *interpreter's own* klt
  (``python -m klayout_tools.cli``), so a venv run can never pick up a
  different klt from ``$PATH``; a plain ``klt`` is the fallback only when
  ``klayout_tools`` is not importable. An explicit ``--klt PATH`` from the
  caller still overrides the default.
* **gating** -- :func:`pinned_klt_version` reads the repo's single source
  of truth (``KLT_VERSION=`` in ``scripts/setup-env.sh``; never a second
  hard-coded copy), and :func:`require_pinned_klt_version` refuses a
  report rendered by any other klt, loudly, naming both versions.

Zero dependencies beyond the Python 3 standard library.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SETUP_ENV = SCRIPTS_DIR / "setup-env.sh"

#: ``KLT_VERSION="0.9.0"`` in scripts/setup-env.sh -- the pin every harness
#: gates its reports against.
_PIN_LINE = re.compile(r'^\s*KLT_VERSION="([^"]+)"', re.MULTILINE)


class KltVersionError(Exception):
    """A report's klt version does not match the repo pin (or is absent)."""


def klt_argv() -> list[str]:
    """Prefer the interpreter's own klt (so a venv run never picks up a
    different klt from $PATH), falling back to a plain `klt`."""
    try:
        import klayout_tools.cli  # noqa: F401
    except ImportError:
        return ["klt"]
    return [sys.executable, "-m", "klayout_tools.cli"]


def normalize_version(version: str) -> str:
    """Drop the PEP 440 local segment: ``0.9.0+gabc`` is the pin ``0.9.0``.

    Everything else is compared exactly -- ``0.9.3.dev1`` is *not* the pin
    ``0.9.0``, which is precisely the PR #430 failure this module exists
    to catch.
    """
    return version.split("+", 1)[0].strip()


def pinned_klt_version(setup_env: Path = SETUP_ENV,
                       klt: list[str] | None = None) -> str:
    """The repo's pinned klt version, parsed from ``KLT_VERSION=`` in
    ``scripts/setup-env.sh`` (one source of truth).

    Falls back to asking the resolved klt itself (``<klt> --version``)
    only if the pin cannot be parsed from the file; raises
    :class:`KltVersionError` if both routes fail.
    """
    try:
        text = setup_env.read_text(encoding="utf-8")
    except OSError:
        text = ""
    match = _PIN_LINE.search(text)
    if match:
        return match.group(1)

    argv = (klt if klt is not None else klt_argv()) + ["--version"]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True)
    except OSError as exc:
        raise KltVersionError(
            f"cannot determine the pinned klt version: no KLT_VERSION in "
            f"{setup_env} and `{' '.join(argv)}` did not run: {exc}"
        ) from exc
    tokens = (proc.stdout or "").strip().split()
    if proc.returncode != 0 or not tokens:
        raise KltVersionError(
            "cannot determine the pinned klt version: no KLT_VERSION in "
            f"{setup_env} and `{' '.join(argv)}` failed (exit "
            f"{proc.returncode}): {(proc.stderr or proc.stdout or '').strip()[:200]}"
        )
    return tokens[-1]


def report_klt_version(report: dict) -> str | None:
    """The klt version a harness report claims, wherever its shape keeps it:
    ``provenance.klt_version`` (erc / lvs / extract / drc reports) or
    ``build.version`` (signoff reports). None when the report carries none."""
    provenance = report.get("provenance")
    if isinstance(provenance, dict) and provenance.get("klt_version"):
        return str(provenance["klt_version"])
    build = report.get("build")
    if isinstance(build, dict):
        for key in ("version", "package_version"):
            if build.get(key):
                return str(build[key])
    return None


def require_pinned_klt_version(report: dict, pinned: str, context: str) -> str:
    """Gate a freshly rendered report against the pin.

    Raises :class:`KltVersionError` -- naming both versions, or the missing
    field plus the pin -- when the report was rendered by any other klt or
    carries no version at all. Returns the report's normalized version so
    the caller can stamp it into a summary.
    """
    found = report_klt_version(report)
    if not found:
        raise KltVersionError(
            f"{context}: report carries no klt version (expected the pin "
            f"{pinned}); refusing to trust it"
        )
    if normalize_version(found) != normalize_version(pinned):
        raise KltVersionError(
            f"{context}: report was rendered by klt {found}, but this repo "
            f"pins klt {pinned} (KLT_VERSION in scripts/setup-env.sh); "
            "re-run inside the pinned environment (./scripts/setup-env.sh)"
        )
    return normalize_version(found)
