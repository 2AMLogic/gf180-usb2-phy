"""Run a PVT grid through ``klt sim`` instead of hand-launching ngspice.

``run_corners.py --backend klt`` (or ``klt:local`` / ``klt:batch``) builds one
``klt sim`` corners request for the whole grid, runs it, and maps the
per-corner results back onto the harness's ``PointResult`` objects so the
usual evidence record is minted unchanged. On a shared host the full grid
must go this way: with ``KLT_SIM_BACKEND=batch`` the request is submitted to
the Spot batch fleet instead of occupying local cores.

A testbench opts in by declaring ``klt_measure`` in ``tb.json``: a map of
measurement name -> either ``{"spice": ".meas ...", "scale": k}`` (a ``.meas``
card, result multiplied by ``k`` -- the form the fleet's older runner image
accepts) or a bare *self-contained* ngspice expression string
(``measurements[].expr``, needs a newer runner). It cannot use ``derive``'s
helper vectors, because the request has no equivalent of the local deck's
free-form ``.control`` statements; put any needed reference nodes in the
testbench netlist instead. The names must equal
``measure``'s, so the same ``checks`` apply.

The supply is driven through the voltage source named by ``klt_supply_source``
(default ``vsup``), which ``klt sim`` re-targets per corner with ``alter``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .corners import PvtPoint
from .pdk import Pdk
from .runner import DeckRefs, PointResult, classify_output, compose_deck
from .testbench import Testbench

KLT = "klt"
DEFAULT_SUPPLY_SOURCE = "vsup"

#: Transports: ``request`` re-expresses the bench as a `klt sim` corners
#: request (needs ``klt_measure``); ``decks`` ships the harness's own composed
#: per-point decks verbatim as a deck-list request, so ``.control`` / derived
#: vector measurements and the output parser are unchanged.
TRANSPORTS = ("auto", "request", "decks")

#: ``$KLT_SIM_BACKEND`` values that mean "this host must not run SPICE grids
#: itself" (the shared dispatch workers); also the only backends a multi-unit
#: klt grid may resolve to.
FLEET_BACKENDS = ("batch", "remote")
BACKEND_ENV = "KLT_SIM_BACKEND"

#: The executing host resolves its own PDK; the deck names it by this literal.
PDK_ROOT_LITERAL = "$PDK_ROOT"

_INCLUDE_RE = re.compile(r"^\s*\.(include|inc|lib|read)\b", re.IGNORECASE | re.MULTILINE)


class KltError(RuntimeError):
    pass


def fleet_env_backend() -> str | None:
    """The host's ``$KLT_SIM_BACKEND`` when it marks a no-local-grid host."""
    value = os.environ.get(BACKEND_ENV, "").strip()
    return value if value in FLEET_BACKENDS else None


def check_local_fanout(n_points: int) -> None:
    """Refuse an in-process multi-point ngspice grid on a no-local-grid host.

    ``run_point``-style single-point probes stay allowed; there is no exception
    for a grid -- express it as a klt request instead.
    """
    if n_points > 1 and fleet_env_backend():
        raise KltError(
            f"refusing to run {n_points} points in-process: ${BACKEND_ENV}="
            f"{fleet_env_backend()} marks this host as one that must not run SPICE "
            "grids itself. Use --backend klt (or klt:batch); a single point "
            "(--corners X --temps T --supply-tol 0) may still run locally."
        )


def effective_klt_backend(backend: str | None, n_points: int) -> str | None:
    """Pin the backend a klt run will use, refusing implicit/local multi-unit fan-out.

    ``backend`` is the explicit ``klt:<name>`` part (or ``None``). Precedence
    mirrors klt (flag > ``$KLT_SIM_BACKEND``); the result is always passed to
    ``klt sim --backend`` so nothing is decided later by a default. For more
    than one unit it must be a fleet backend: an unset environment (klt would
    silently pick ``local``) or an explicit local backend is an error here, not
    a quiet local grid.
    """
    name = backend or os.environ.get(BACKEND_ENV, "").strip() or None
    if n_points > 1 and name not in FLEET_BACKENDS:
        raise KltError(
            f"refusing to run {n_points} units on klt backend {name or 'local (default)'!r}: "
            f"a multi-unit grid must go to the fleet. Name it explicitly (--backend "
            f"klt:batch) or export {BACKEND_ENV}=batch."
        )
    return name


def klt_version() -> str:
    exe = shutil.which(KLT)
    if not exe:
        raise KltError("klt not found on PATH")
    out = subprocess.run([exe, "--version"], capture_output=True, text=True, check=False)
    return (out.stdout or out.stderr).strip()


def _measurement(name: str, entry) -> dict:
    """A ``klt_measure`` entry: a ``.meas`` card dict, or a bare expression string."""
    if isinstance(entry, str):
        return {"name": name, "expr": entry}
    if not isinstance(entry, dict) or not isinstance(entry.get("spice"), str):
        raise KltError(
            f"klt_measure[{name!r}] must be an expression string or "
            "{'spice': '.meas ...', 'scale': k}"
        )
    return {"name": name, "spice": entry["spice"]}


def _scale(manifest: dict, name: str) -> float:
    entry = manifest["klt_measure"][name]
    return float(entry.get("scale", 1.0)) if isinstance(entry, dict) else 1.0


def build_request(
    tb: Testbench,
    pdk: Pdk,
    points: list[PvtPoint],
    workdir: Path,
    timeout_s: int,
    backend: str | None,
    manifest: dict,
    runner_version_check: str | None = None,
) -> Path:
    """Write ``body.spice`` + ``request.json`` into ``workdir``; return the request path."""
    klt_measure = manifest.get("klt_measure")
    if not klt_measure:
        raise KltError(
            f"{tb.name}: tb.json has no 'klt_measure'; add self-contained "
            "expressions to use the klt backend"
        )
    if set(klt_measure) != set(tb.measure):
        raise KltError(
            f"{tb.name}: klt_measure keys {sorted(klt_measure)} differ from "
            f"measure keys {sorted(tb.measure)}"
        )
    if len(tb.analyses) != 1:
        raise KltError(f"{tb.name}: klt backend supports exactly one analysis")
    source = manifest.get("klt_supply_source", DEFAULT_SUPPLY_SOURCE)

    workdir.mkdir(parents=True, exist_ok=True)
    body = [
        f"* {tb.name} -- circuit body for klt sim (GENERATED by sim/harness)",
        f".param vdd_nom={tb.nominal_supply_v!r}",
        f".param vdd_val={tb.nominal_supply_v!r}",
        f".param temp_c=27.0",
    ]
    for key, value in tb.params.items():
        body.append(f".param {key}={value}")
    body.append(f'.include "{pdk.design_include}"')
    if tb.dut is not None:
        body.append(f'.include "{tb.dut}"')
    body.append(f'.include "{tb.netlist}"')
    (workdir / "body.spice").write_text("\n".join(body) + "\n")

    # Process axis keeps the grid's own corner order; supply/temperature are
    # the distinct values present in the grid (full factorial by construction).
    process, seen = [], set()
    for p in points:
        if p.corner.name not in seen:
            seen.add(p.corner.name)
            process.append({"name": p.corner.name, "sections": list(p.corner.sections)})
    supplies = sorted({p.vdd for p in points})
    temps = []
    for p in points:
        if p.temp_c not in temps:
            temps.append(p.temp_c)
    # Compare the actual point set against the full product, not just counts:
    # a duplicated point can otherwise hide a missing one.
    keys = [_key(p.corner.name, p.temp_c, p.vdd) for p in points]
    full = {_key(c["name"], t, v) for c in process for t in temps for v in supplies}
    if len(set(keys)) != len(keys) or set(keys) != full:
        raise KltError("grid is not a full factorial; klt backend cannot express it")

    analysis = tb.analyses[0].split(None, 1)
    request = {
        "netlist": "body.spice",
        "engine": "ngspice",
        "models": {"pdk": pdk.variant, "lib": "libs.tech/ngspice/sm141064.ngspice"},
        "corners": {
            "process": process,
            "supply_v": {source: supplies},
            "temperature_c": temps,
        },
        "analysis": {"kind": analysis[0], "args": analysis[1] if len(analysis) > 1 else ""},
        "measurements": [_measurement(n, klt_measure[n]) for n in tb.measure],
        "options": {"timeout_s": timeout_s, "keep_artifacts": True},
    }
    if backend:
        request["backend"] = backend
    if runner_version_check:
        request["batch"] = {"runner_version_check": runner_version_check}
    path = workdir / "request.json"
    path.write_text(json.dumps(request, indent=2) + "\n")
    return path


def _key(process: str, temp_c: float, vdd: float) -> tuple:
    return (process, round(float(temp_c), 6), round(float(vdd), 6))


def _invoke_klt(
    request: Path, outdir: Path, backend: str | None, workdir: Path, list_key: str
) -> tuple[subprocess.CompletedProcess, dict, float]:
    """Run ``klt sim`` on ``request``; return (process, parsed report, wall seconds)."""
    cmd = [KLT, "sim", str(request), "--format", "json", "-o", str(outdir)]
    if backend:
        cmd += ["--backend", backend]
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise KltError(f"{KLT} not found on PATH; cannot run `klt sim`") from exc
    wall = time.monotonic() - started
    (workdir / "klt-stderr.txt").write_text(proc.stderr or "")
    try:
        report = json.loads(proc.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        (workdir / "klt-stdout.txt").write_text(proc.stdout or "")
        raise KltError(
            f"klt sim produced no JSON report (exit {proc.returncode}); "
            f"stderr tail:\n{(proc.stderr or '')[-2000:]}"
        ) from exc
    if not isinstance(report, dict) or not isinstance(report.get(list_key, []), list):
        (workdir / "klt-stdout.txt").write_text(proc.stdout)
        raise KltError(
            f"klt sim report is not a report object (exit {proc.returncode}); "
            f"got {type(report).__name__}"
        )
    (workdir / "klt-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return proc, report, wall


def run_grid_klt(
    tb: Testbench,
    pdk: Pdk,
    points: list[PvtPoint],
    workdir: Path,
    manifest: dict,
    backend: str | None = None,
    runner_version_check: str | None = None,
    timeout_s: int = 300,
    on_result=None,
    log_dir: Path | None = None,
) -> tuple[list[PointResult], dict]:
    """Run the grid via ``klt sim``; return (results in grid order, backend info)."""
    backend = effective_klt_backend(backend, len(points))
    request = build_request(
        tb, pdk, points, workdir, timeout_s, backend, manifest, runner_version_check
    )
    outdir = workdir / "klt-out"
    proc, report, wall = _invoke_klt(request, outdir, backend, workdir, "corners")

    by_key = {}
    for c in report.get("corners", []):
        if not isinstance(c, dict):
            continue
        supply = c.get("supply_v")
        vdd = next(iter(supply.values()), None) if isinstance(supply, dict) else None
        try:
            by_key[_key(c.get("process"), c.get("temperature_c"), vdd)] = c
        except (TypeError, ValueError):
            continue  # malformed corner: its grid point is reported missing

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
    results: list[PointResult] = []
    for point in points:
        c = by_key.get(_key(point.corner.name, point.temp_c, point.vdd))
        if c is None:
            res = PointResult(
                point=point, status="error", missing=list(tb.measure),
                message=f"corner missing from klt report (klt status {report.get('status')})",
            )
        else:
            meas = {}
            for m in c.get("measurements") or []:
                name = m.get("name") if isinstance(m, dict) else None
                if name not in tb.measure:
                    continue
                try:
                    meas[name] = float(m["value"]) * _scale(manifest, name)
                except (KeyError, TypeError, ValueError):
                    continue  # absent / null / non-numeric: reported missing
            missing = [n for n in tb.measure if n not in meas]
            diags = "; ".join(f"{d.get('code')}: {d.get('message')}"
                              for d in c.get("diagnostics") or [] if isinstance(d, dict))
            if c.get("status") == "error" or missing:
                res = PointResult(
                    point=point, status="failed" if meas else "error", measurements=meas,
                    missing=missing, seconds=c.get("runtime_s", 0.0),
                    message=diags or f"klt corner status {c.get('status')}",
                )
            else:
                # klt's own pass/fail grading is ignored: the harness's
                # `checks` decide, exactly as for the local backend.
                res = PointResult(point=point, status="ok", measurements=meas,
                                  seconds=c.get("runtime_s", 0.0))
            if log_dir is not None:
                log_name = f"{point.corner_id}.log"
                art = (c.get("artifacts") or {}).get("log")
                dest = log_dir / log_name
                if art and Path(art).is_file():
                    shutil.copyfile(art, dest)
                else:
                    dest.write_text(
                        f"klt sim corner {c.get('corner_id')} status={c.get('status')}\n"
                        + json.dumps(c, indent=2) + "\n"
                    )
                res.log = log_name
        results.append(res)
        if on_result is not None:
            on_result(res)

    info = {
        "backend": backend or "request-default",
        "klt_exit_code": proc.returncode,
        "klt_status": report.get("status"),
        "klt_version": (report.get("provenance") or {}).get("klt_version"),
        "engine_version": (report.get("environment") or {}).get("engine_version"),
        "remote": (report.get("environment") or {}).get("remote"),
        "wall_seconds": round(wall, 2),
    }
    return results, info


# --------------------------------------------------------------------------
# Deck-list transport: ship the harness's own composed decks, unchanged.
# --------------------------------------------------------------------------

DECK_NETLIST_NAME = "tb_netlist.spice"
DECK_DUT_NAME = "dut.spice"


def select_transport(requested: str, manifest: dict) -> str:
    """``auto`` -> ``request`` when the bench declares ``klt_measure``, else ``decks``."""
    if requested not in TRANSPORTS:
        raise KltError(f"unknown klt transport {requested!r} (expected one of {TRANSPORTS})")
    if requested == "auto":
        return "request" if manifest.get("klt_measure") else "decks"
    return requested


def _pdk_root_ref(pdk: Pdk, path: Path, pdk_root: str | None = None) -> str:
    """The deck's reference to a PDK file, resolved by the *executing* host.

    Default: the literal ``$PDK_ROOT/<rel>`` (klt's convention; the executor
    must expand it -- local ngspice 42 does not, so this is a named executor
    prerequisite). With ``pdk_root`` (the executor's own PDK root): the
    absolute ``<pdk_root>/<rel>``, which needs no environment expansion.
    """
    try:
        rel = Path(path).relative_to(pdk.path.parent)
    except ValueError as exc:
        raise KltError(
            f"{path} is not under the PDK root {pdk.path.parent}; the deck-list "
            "transport cannot reference it portably"
        ) from exc
    return f"{pdk_root.rstrip('/')}/{rel.as_posix()}" if pdk_root else f"{PDK_ROOT_LITERAL}/{rel.as_posix()}"


def _check_fragment(label: str, path: Path) -> None:
    if _INCLUDE_RE.search(path.read_text()):
        raise KltError(
            f"{label} {path} has .include/.lib/.read directives; the deck-list "
            "transport stages only the deck's two netlist fragments by name and "
            "cannot ship a nested include closure -- unsupported, not dropped"
        )


def build_deck_request(
    tb: Testbench,
    pdk: Pdk,
    points: list[PvtPoint],
    workdir: Path,
    timeout_s: int,
    backend: str | None,
    runner_version_check: str | None = None,
    pdk_root: str | None = None,
) -> Path:
    """Write one composed deck per point + ``request.json``; return the request path.

    Each deck is :func:`compose_deck`'s output with only the file references
    changed (staged relative names; ``$PDK_ROOT/...`` for the PDK). Analyses,
    ``derive``, ``measure``, ``.control`` and ``.temp`` are byte-identical to
    the local deck, so the printed ``m_<name>`` vectors parse the same way.
    """
    ids = [p.corner_id for p in points]
    if len(set(ids)) != len(ids):
        raise KltError(f"{tb.name}: duplicate corner ids in the grid; deck ids must be unique")
    workdir.mkdir(parents=True, exist_ok=True)
    _check_fragment("testbench netlist", tb.netlist)
    shutil.copyfile(tb.netlist, workdir / DECK_NETLIST_NAME)
    refs = DeckRefs(
        design_include=_pdk_root_ref(pdk, pdk.design_include, pdk_root),
        model_lib=_pdk_root_ref(pdk, pdk.model_lib, pdk_root),
        netlist=DECK_NETLIST_NAME,
    )
    if tb.dut is not None:
        _check_fragment("DUT netlist", tb.dut)
        shutil.copyfile(tb.dut, workdir / DECK_DUT_NAME)
        refs = DeckRefs(refs.design_include, refs.model_lib, DECK_DUT_NAME, DECK_NETLIST_NAME)

    decks = []
    for point in points:
        name = f"{point.corner_id}.spice"
        (workdir / name).write_text(compose_deck(tb, pdk, point, refs))
        decks.append({"id": point.corner_id, "deck": name})
    request = {
        "engine": "ngspice",
        "models": {"pdk": pdk.variant, **({"pdk_root": pdk_root} if pdk_root else {})},
        "decks": decks,
        "options": {"timeout_s": timeout_s},
    }
    if backend:
        request["backend"] = backend
    if runner_version_check:
        request["batch"] = {"runner_version_check": runner_version_check}
    path = workdir / "request.json"
    path.write_text(json.dumps(request, indent=2) + "\n")
    return path


def _read_stream(outdir: Path, unit: dict, key: str) -> str | None:
    rel = unit.get(key)
    if not isinstance(rel, str):
        return None
    try:
        return (outdir / rel).read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return None


def run_decks_klt(
    tb: Testbench,
    pdk: Pdk,
    points: list[PvtPoint],
    workdir: Path,
    backend: str | None = None,
    runner_version_check: str | None = None,
    timeout_s: int = 300,
    on_result=None,
    log_dir: Path | None = None,
    pdk_root: str | None = None,
) -> tuple[list[PointResult], dict]:
    """Run the grid as a `klt sim` deck-list request; classify output like the local runner.

    klt only transports: grading is :func:`classify_output` on the unit's raw
    stdout+stderr, exactly what ``run_point`` applies to a local ngspice run.
    A unit that is missing, timed out, or has no captured stream is an
    explicit ``error`` result -- never dropped, never retried locally.
    """
    backend = effective_klt_backend(backend, len(points))
    request = build_deck_request(
        tb, pdk, points, workdir, timeout_s, backend, runner_version_check, pdk_root
    )
    outdir = workdir / "klt-out"
    proc, report, wall = _invoke_klt(request, outdir, backend, workdir, "units")
    if report.get("mode") != "decks":
        raise KltError(
            "klt sim did not return a deck-list report (mode "
            f"{report.get('mode')!r}); is the installed klt/runner image new enough "
            "for deck-list requests?"
        )

    by_id = {u.get("id"): u for u in report.get("units", []) if isinstance(u, dict)}
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
    results: list[PointResult] = []
    for point in points:
        unit = by_id.get(point.corner_id)
        deck_name = f"{point.corner_id}.spice"
        log_name = f"{point.corner_id}.log"
        if unit is None:
            res = PointResult(
                point=point, status="error", missing=list(tb.measure), deck=deck_name,
                message=f"unit missing from klt deck report (klt status {report.get('status')})",
            )
            text = f"unit {point.corner_id} missing from klt deck report\n"
        elif unit.get("timed_out") or unit.get("status") == "timeout":
            text = f"TIMEOUT after {timeout_s}s\n"
            res = PointResult(
                point=point, status="error", missing=list(tb.measure), deck=deck_name,
                seconds=unit.get("duration_s") or 0.0,
                message=f"ngspice timed out after {timeout_s}s",
            )
        else:
            out = _read_stream(outdir, unit, "stdout")
            err = _read_stream(outdir, unit, "stderr")
            if out is None and err is None:
                text = f"no captured streams for unit {point.corner_id}\n"
                diags = "; ".join(str(d.get("message")) for d in unit.get("diagnostics") or []
                                  if isinstance(d, dict))
                res = PointResult(
                    point=point, status="error", missing=list(tb.measure), deck=deck_name,
                    seconds=unit.get("duration_s") or 0.0,
                    message=diags or "klt deck unit produced no captured streams",
                )
            else:
                # Same composition as run_point's log: stdout, newline, stderr.
                text = (out or "") + "\n" + (err or "")
                res = classify_output(
                    tb, point, text, unit.get("exit_code"),
                    unit.get("duration_s") or 0.0, deck=deck_name, log=log_name,
                )
        if log_dir is not None:
            (log_dir / log_name).write_text(text)
            res.log = log_name
        results.append(res)
        if on_result is not None:
            on_result(res)

    digest = hashlib.sha256()
    for u in sorted(by_id.values(), key=lambda x: str(x.get("id"))):
        digest.update(f"{u.get('id')} {u.get('deck_sha256')}\n".encode())
    info = {
        "backend": backend or "request-default",
        "transport": "decks",
        "klt_exit_code": proc.returncode,
        "klt_status": report.get("status"),
        "klt_version": (report.get("environment") or {}).get("klt_version"),
        "engine_version": (report.get("environment") or {}).get("engine_version"),
        "remote": (report.get("environment") or {}).get("remote"),
        "pdk_ref": pdk_root or PDK_ROOT_LITERAL,
        "units": len(by_id),
        "decks_sha256": digest.hexdigest(),
        "wall_seconds": round(wall, 2),
    }
    return results, info
