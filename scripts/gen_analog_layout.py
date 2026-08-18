#!/usr/bin/env python3
"""Generate analog-block layout from committed klt layout plans (issue #25).

Drives klayout-tools' netlist-driven layout-plan executor (Phase C,
``klayout_tools.layout_plan_execute``) over every plan under
``layout/analog/plans/``, then runs ``klt drc`` on whatever GDS each plan
produced, and prints one honest per-block verdict.

**This is a measurement harness, not a "produce the shipping layout"
button.** Its current, recorded outcome is *not* a usable analog layout --
see ``layout/README.md`` and
``verification/records/analog-layout/`` for the full finding. Two of the
five analog blocks cannot even be ingested by klt's netlist reader, and the
three that can place their devices but route **none** of their nets. The
script exists so that finding is reproducible with one command, and so the
day klayout-tools closes those gaps the same command re-measures instead of
someone re-deriving the setup from prose.

Exit codes (about *the run*, never about the quality of the layout -- read
the report for that):

  0  every plan was executed and every blocked block was probed; a report
     was written.
  1  the run itself failed (missing klt, unresolvable PDK, an unexpected
     exception).
  2  CLI usage error (argparse).

Usage:

    PDK_ROOT=$HOME/.volare python3 scripts/gen_analog_layout.py
    PDK_ROOT=$HOME/.volare python3 scripts/gen_analog_layout.py --format json
    PDK_ROOT=$HOME/.volare python3 scripts/gen_analog_layout.py --out-dir /tmp/o
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN_DIR = os.path.join(REPO_ROOT, "layout", "analog", "plans")
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "layout", "analog", "out")

# Blocks with no committed plan, because klt's own netlist ingestion rejects
# their SPICE before a plan could be validated at all. Probed live on every
# run (rather than described in prose only) so the report states the current
# error text, not a stale quotation of it.
BLOCKED_BLOCKS = {
    "differential_driver": (
        "series-termination resistors are rm1 (metal-1) devices, which the "
        "curated gf180mcu deck does not know, and no klt gen generator draws "
        "a metal resistor"
    ),
    "dplus_pullup": (
        "the pull-up switch devices carry nf=10 (multi-finger), which klt's "
        "subckt-call -> plain-element conversion refuses to represent"
    ),
}


def _fail(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    raise SystemExit(1)


def _klt_argv() -> list[str]:
    """Prefer the interpreter's own klt (so a venv run never picks up a
    different klt from $PATH), falling back to a plain `klt`."""
    try:
        import klayout_tools.cli  # noqa: F401
    except ImportError:
        return ["klt"]
    return [sys.executable, "-m", "klayout_tools.cli"]


def _run_drc(gds_path: str) -> dict:
    argv = _klt_argv() + [
        "drc",
        gds_path,
        "--deck",
        "gf180mcu",
        "--format",
        "json",
    ]
    proc = subprocess.run(argv, capture_output=True, text=True)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": (proc.stderr or proc.stdout or "no output").strip()[:400],
        }
    if "error" in payload:
        return {"status": "error", "message": payload["error"].get("message", "")}
    violations = payload.get("violations") or []
    by_rule: dict[str, int] = {}
    for violation in violations:
        rule = violation.get("rule") or violation.get("check") or "?"
        by_rule[rule] = by_rule.get(rule, 0) + 1
    return {
        "status": "clean" if not violations else "violations",
        "violation_count": len(violations),
        "by_rule": dict(sorted(by_rule.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def _execute_plan(plan_path: str, out_dir: str, keep_work: bool) -> dict:
    from klayout_tools.layout_plan import LayoutPlanError
    from klayout_tools.layout_plan_execute import (
        LayoutPlanExecuteError,
        execute_layout_plan_document,
        exit_code_for,
    )

    block = os.path.splitext(os.path.basename(plan_path))[0]
    with open(plan_path, encoding="utf-8") as handle:
        request = json.load(handle)

    gds_path = os.path.join(out_dir, f"{block}.gds")
    # The committed plan's own options.output is a bare filename (it documents
    # intent); the runner decides where artifacts actually land.
    request.setdefault("options", {})["output"] = gds_path
    work_dir = os.path.join(out_dir, f"{block}.work") if keep_work else None
    if work_dir:
        os.makedirs(work_dir, exist_ok=True)

    result: dict = {"block": block, "plan": os.path.relpath(plan_path, REPO_ROOT)}
    try:
        response = execute_layout_plan_document(
            request, request_dir=os.path.dirname(plan_path), work_dir=work_dir
        )
    except (LayoutPlanError, LayoutPlanExecuteError) as exc:
        result.update(status="execute-failed", message=str(exc))
        return result
    except Exception as exc:  # noqa: BLE001 -- ingestion errors are klt-internal
        result.update(status="ingest-failed", message=str(exc))
        return result

    with open(os.path.join(out_dir, f"{block}-layout-plan.json"), "w") as handle:
        json.dump(response, handle, indent=2)
        handle.write("\n")

    nets = response.get("nets") or []
    routed = [net for net in nets if net.get("routed")]
    result.update(
        status="executed",
        klt_exit_code=exit_code_for(response),
        gds_path=os.path.relpath(gds_path, REPO_ROOT),
        device_group_count=len(response.get("device_groups") or []),
        net_count=len(nets),
        routed_net_count=len(routed),
        unrouted_nets=sorted(response.get("unrouted_nets") or []),
        unmapped_netlist_nets=sorted(response.get("unmapped_netlist_nets") or []),
        bbox_um=response.get("bbox_um"),
        warning_count=len(response.get("warnings") or []),
        drc=_run_drc(gds_path),
    )
    return result


def _probe_blocked(block: str, reason: str) -> dict:
    from klayout_tools.netlist_digest import build_netlist_digest

    netlist = os.path.join(REPO_ROOT, "design", "netlist", f"{block}.spice")
    entry = {"block": block, "plan": None, "expected_reason": reason}
    try:
        build_netlist_digest(netlist, top=block, form="subckt-call", deck="gf180mcu")
    except Exception as exc:  # noqa: BLE001 -- klt raises its own LvsError here
        entry.update(status="ingest-failed", message=str(exc))
        return entry
    entry.update(
        status="ingest-unexpectedly-succeeded",
        message=(
            "klt now ingests this netlist -- the blocker this entry records is "
            "gone; author a plan under layout/analog/plans/ and drop this block "
            "from BLOCKED_BLOCKS"
        ),
    )
    return entry


def _print_text(report: dict) -> None:
    print(f"klt: {report['klt_version']}   plans: {report['plan_dir']}")
    print(f"out: {report['out_dir']}")
    print()
    for entry in report["blocks"]:
        print(f"== {entry['block']}")
        if entry["status"] != "executed":
            print(f"   status: {entry['status']}")
            print(f"   {entry['message']}")
            print()
            continue
        drc = entry["drc"]
        drc_text = (
            f"{drc['status']} ({drc.get('violation_count', 0)} violations)"
            if drc["status"] != "error"
            else f"error: {drc['message']}"
        )
        print(
            f"   status: executed (klt exit {entry['klt_exit_code']}), "
            f"{entry['device_group_count']} device groups"
        )
        print(
            f"   nets routed: {entry['routed_net_count']}/{entry['net_count']}"
            + (
                f"   unrouted: {', '.join(entry['unrouted_nets'])}"
                if entry["unrouted_nets"]
                else ""
            )
        )
        print(f"   drc: {drc_text}")
        if drc.get("by_rule"):
            for rule, count in drc["by_rule"].items():
                print(f"        {count:5d}  {rule}")
        print()
    summary = report["summary"]
    print(
        f"SUMMARY: {summary['executed']}/{summary['total']} blocks executed, "
        f"{summary['fully_routed']} fully routed, "
        f"{summary['drc_clean']} DRC-clean"
    )
    print(f"VERDICT: {summary['verdict']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--out-dir",
        default=DEFAULT_OUT_DIR,
        help=f"where GDS + response JSON land (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--format", choices=("text", "json"), default="text", help="report format"
    )
    parser.add_argument(
        "--keep-work",
        action="store_true",
        help="keep each group's intermediate klt gen GDS under <out-dir>/<block>.work/",
    )
    args = parser.parse_args(argv)

    try:
        from klayout_tools import __version__ as klt_version
    except ImportError:
        _fail(
            "klayout-tools is not importable. Run ./scripts/setup-env.sh and "
            "activate .venv (see docs/environment-setup.md)."
        )
    if "PDK_ROOT" not in os.environ and "GF180_PDK_PATH" not in os.environ:
        print(
            "note: neither PDK_ROOT nor GF180_PDK_PATH is set -- klt will fall "
            "back to its own PDK search roots (see docs/environment-setup.md)",
            file=sys.stderr,
        )

    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    plans = sorted(glob.glob(os.path.join(PLAN_DIR, "*.json")))
    blocks = [_execute_plan(plan, out_dir, args.keep_work) for plan in plans]
    blocks.extend(
        _probe_blocked(block, reason)
        for block, reason in sorted(BLOCKED_BLOCKS.items())
    )
    blocks.sort(key=lambda entry: entry["block"])

    executed = [entry for entry in blocks if entry["status"] == "executed"]
    fully_routed = [
        entry
        for entry in executed
        if entry["net_count"] and entry["routed_net_count"] == entry["net_count"]
    ]
    drc_clean = [entry for entry in executed if entry["drc"]["status"] == "clean"]
    verdict = (
        "analog layout DELIVERED"
        if len(fully_routed) == len(blocks) and len(drc_clean) == len(blocks)
        else "analog layout NOT delivered -- see layout/README.md"
    )
    report = {
        "schema_version": 1,
        "klt_version": klt_version,
        "plan_dir": os.path.relpath(PLAN_DIR, REPO_ROOT),
        "out_dir": out_dir,
        "blocks": blocks,
        "summary": {
            "total": len(blocks),
            "executed": len(executed),
            "fully_routed": len(fully_routed),
            "drc_clean": len(drc_clean),
            "verdict": verdict,
        },
    }

    report_path = os.path.join(out_dir, "analog-layout-report.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        _print_text(report)
        print(f"report: {os.path.relpath(report_path, REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
