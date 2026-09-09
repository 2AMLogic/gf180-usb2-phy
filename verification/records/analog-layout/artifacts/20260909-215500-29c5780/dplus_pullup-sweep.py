#!/usr/bin/env python3
"""Focused dplus_pullup sweep at the new klt pin (issue #68 measurement only)."""
import copy, json, os, subprocess, sys

# This file is frozen evidence: it is the exact sweep driver this record's
# run used, with only the repo root de-hard-coded (it was an absolute path to
# the authoring worktree). Re-run with:
#   PDK_ROOT=$HOME/.volare .venv/bin/python \
#     verification/records/analog-layout/artifacts/<record-id>/dplus_pullup-sweep.py
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 5))
PLAN = os.path.join(REPO, "layout/analog/plans/dplus_pullup.json")
OUT = "/tmp/aly68-sweep"
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, REPO)

from klayout_tools.layout_plan import LayoutPlanError
from klayout_tools.layout_plan_execute import (
    LayoutPlanExecuteError,
    execute_layout_plan_document,
)

BASE = json.load(open(PLAN))


def drc(gds):
    p = subprocess.run(
        [sys.executable, "-m", "klayout_tools.cli", "drc", gds,
         "--deck", "gf180mcu", "--format", "json"],
        capture_output=True, text=True)
    try:
        d = json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"status": "error", "msg": (p.stderr or p.stdout)[:200]}
    v = d.get("violations") or []
    by = {}
    for x in v:
        r = x.get("rule") or x.get("check") or "?"
        by[r] = by.get(r, 0) + 1
    return {"count": len(v), "by_rule": by,
            "layers_checked": d.get("coverage", {}).get("layers_checked")}


def run(label, mutate):
    req = copy.deepcopy(BASE)
    mutate(req)
    gds = os.path.join(OUT, label.replace("/", "_") + ".gds")
    req.setdefault("options", {})["output"] = gds
    try:
        resp = execute_layout_plan_document(
            req, request_dir=os.path.dirname(PLAN), work_dir=None)
    except (LayoutPlanError, LayoutPlanExecuteError) as e:
        print(f"{label:46s} EXECUTE-FAILED: {e}")
        return
    except Exception as e:  # noqa: BLE001
        print(f"{label:46s} INGEST-FAILED: {e}")
        return
    nets = resp.get("nets") or []
    routed = sum(1 for n in nets if n.get("routed"))
    legs = [l for n in nets for l in (n.get("legs") or [])]
    legs_routed = sum(1 for l in legs if l.get("routed"))
    d = drc(gds)
    json.dump(resp, open(os.path.join(OUT, label.replace("/", "_") + ".json"), "w"), indent=2)
    print(f"{label:46s} nets {routed}/{len(nets)}  legs {legs_routed}/{len(legs)}  "
          f"drc {d['count']} {d['by_rule'] if d['by_rule'] else ''}")


def set_routing(**kw):
    def f(req):
        req["routing"].update(kw)
    return f


def set_spacing(v):
    def f(req):
        for row in req["rows"]:
            row["spacing_um"] = v
    return f


def combo(*fns):
    def f(req):
        for fn in fns:
            fn(req)
    return f


def set_orient(o):
    def f(req):
        for g in req["device_groups"]:
            g["orientation"] = o
    return f


print("== A. spacing_um sweep (metal primary 0.28 + cross metal2) ==")
for s in (2.0, 2.5, 3.0, 3.5, 4.0, 5.0):
    run(f"spacing={s}", set_spacing(s))

print()
print("== B. orientation sweep (spacing 3.0, cross metal2) ==")
for o in ("mirror_x", "mirror_y", "rotate_180"):
    run(f"orientation={o}", set_orient(o))

print()
print("== C. primary-layer probe (old record item 4 revisited) ==")
run("layer=metal2 cross=metal3 w=0.28",
    set_routing(layer_role="metal2", cross_block_layer_role="metal3", width_um=0.28))
run("layer=metal2 cross=metal3 w=0.30",
    set_routing(layer_role="metal2", cross_block_layer_role="metal3", width_um=0.30))
run("layer=metal cross=metal3 w=0.28",
    set_routing(layer_role="metal", cross_block_layer_role="metal3", width_um=0.28))

print()
print("== D. width probe on committed layers ==")
for w in (0.28, 0.30, 0.36):
    run(f"metal/metal2 width={w}", set_routing(width_um=w))
