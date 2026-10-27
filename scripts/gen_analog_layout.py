#!/usr/bin/env python3
"""Generate analog-block layout from committed klt layout plans (issue #25).

Drives klayout-tools' netlist-driven layout-plan executor (Phase C,
``klayout_tools.layout_plan_execute``) over every plan under
``layout/analog/plans/``, then runs ``klt drc`` on whatever GDS each plan
produced, and prints one honest per-block verdict.

For the four blocks that do not depend on the driver re-size
(``DELIVERABLE_BLOCKS``) it also finishes the routing klt's plan path cannot
complete (issue #251): every net klt leaves unrouted is completed by a
scripted channel route (see "Scripted routing" below), and the result is
re-checked by a flat conductivity extraction -- never by the router's own
bookkeeping -- before a net counts as routed. ``--deliver`` writes the
routed GDS per block to ``layout/analog/<block>.gds`` plus
``layout/analog/provenance.json``; ``--check`` regenerates into a scratch
directory and compares every ``gds_sha256`` against that sidecar.

``differential_driver`` is not routed here (it follows the driver re-size,
issue #252); it is still executed and reported, as before, so the day
klayout-tools closes a gap the same command re-measures instead of someone
re-deriving the setup from prose. See ``layout/README.md`` and
``verification/records/analog-layout/`` for the full finding.

Scripted routing. Every plan places one row of tall vertical devices: MOS
source/drain are full-height metal-1 strips, gates end in a metal-1 pad on
top, resistors end in metal-1 heads. A pin gets a via1 on its metal-1 and a
metal-2 stub. Gate pins escape *up* to a per-net metal-3 track above the row,
everything else escapes *down* to a per-net metal-3 track below it (gate and
source/drain stubs of one device sit 0.43 um apart, closer than metal-2
spacing allows, so they never share a side). A net that has both kinds is
joined by one metal-2 corridor in a gap between two devices. Tracks never
share a y, so the only same-layer interactions are stub-vs-stub at distinct
pin x. No device is moved or re-sized; instance origins are snapped to the
0.005 um manufacturing grid, which klt's own placement does not do.

Exit codes (about *the run*, never about the quality of the layout -- read
the report for that):

  0  every plan was executed; a report was written (``--check``: and every
     gds_sha256 reproduced).
  1  the run itself failed (missing klt, unresolvable PDK, an unexpected
     exception).
  2  CLI usage error (argparse).
  3  ``--check`` only: a regenerated GDS does not match provenance.json.

Usage:

    PDK_ROOT=$HOME/.volare .venv/bin/python scripts/gen_analog_layout.py
    PDK_ROOT=$HOME/.volare .venv/bin/python scripts/gen_analog_layout.py --format json
    PDK_ROOT=$HOME/.volare .venv/bin/python scripts/gen_analog_layout.py --out-dir /tmp/o
    PDK_ROOT=$HOME/.volare .venv/bin/python scripts/gen_analog_layout.py --deliver
    PDK_ROOT=$HOME/.volare .venv/bin/python scripts/gen_analog_layout.py --check
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN_DIR = os.path.join(REPO_ROOT, "layout", "analog", "plans")
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "layout", "analog", "out")
DELIVER_DIR = os.path.join(REPO_ROOT, "layout", "analog")
PROVENANCE_PATH = os.path.join(DELIVER_DIR, "provenance.json")
NETLIST_DIR = os.path.join(REPO_ROOT, "design", "netlist")

# The four blocks that do not depend on the driver re-size (issue #251, child A
# of #245). differential_driver is child B (#252).
DELIVERABLE_BLOCKS = (
    "differential_receiver",
    "dplus_pullup",
    "se_receiver_dm",
    "se_receiver_dp",
)

# gf180mcuD layers (klt deck): metal1 34/0, via1 35/0, metal2 36/0,
# via2 38/0, metal3 42/0.
M1, VIA1, M2, VIA2, M3 = (34, 0), (35, 0), (36, 0), (38, 0), (42, 0)
GRID_UM = 0.005  # manufacturing grid
WIRE_UM = 0.28  # metal2 / metal3 minimum width and spacing
VIA_UM = 0.26  # via1 / via2 fixed size
TRACK_PITCH_UM = 0.70  # metal-3 track pitch (min is 0.56; headroom for the grid)
CHANNEL_MARGIN_UM = 2.0  # clear distance between the row and its first track
PIN_VIA_INSET_UM = 0.30  # via centre above the bottom of a source/drain strip
# A wire end reaches this far past a via centre: half the 0.26 um cut plus the
# 0.01 um metal overlap the deck's *.enclosing.via*.1 rules ask for.
END_EXT_UM = 0.14

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


def _execute_plan(
    plan_path: str, out_dir: str, keep_work: bool, final_dir: str | None
) -> dict:
    import klayout_tools.layout_plan_execute as lpe
    from klayout_tools.layout_plan import LayoutPlanError
    from klayout_tools.layout_plan_execute import (
        LayoutPlanExecuteError,
        execute_layout_plan_document,
        exit_code_for,
    )

    block = os.path.splitext(os.path.basename(plan_path))[0]
    with open(plan_path, encoding="utf-8") as handle:
        request = json.load(handle)

    scripted = final_dir is not None and block in DELIVERABLE_BLOCKS
    # klt's own result; the scripted-routing pass writes <block>.gds on top.
    klt_gds = os.path.join(out_dir, f"{block}.klt.gds" if scripted else f"{block}.gds")
    # The committed plan's own options.output is a bare filename (it documents
    # intent); the runner decides where artifacts actually land.
    request.setdefault("options", {})["output"] = klt_gds
    work_dir = os.path.join(out_dir, f"{block}.work") if keep_work else None
    if work_dir:
        os.makedirs(work_dir, exist_ok=True)

    # The executor reports per-net pins by port *name* only; the absolute port
    # coordinates the scripted router needs live in the generator reports it
    # hands to compose(), so observe that one call.
    captured: dict = {}
    original_compose = lpe.compose

    def _capturing_compose(compose_request, **kwargs):
        captured["request"] = compose_request
        return original_compose(compose_request, **kwargs)

    result: dict = {"block": block, "plan": os.path.relpath(plan_path, REPO_ROOT)}
    lpe.compose = _capturing_compose
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
    finally:
        lpe.compose = original_compose

    with open(os.path.join(out_dir, f"{block}-layout-plan.json"), "w") as handle:
        json.dump(response, handle, indent=2)
        handle.write("\n")

    nets = response.get("nets") or []
    klt_routed = {net["net"] for net in nets if net.get("routed")}
    gds_path = klt_gds
    routing: dict | None = None
    routed_names = set(klt_routed)
    if scripted:
        gds_path = os.path.join(final_dir, f"{block}.gds")
        routing = _complete_routing(
            klt_gds, gds_path, response, captured.get("request"), klt_routed
        )
        routed_names = {n for n, ok in routing["routed"].items() if ok}

    result.update(
        status="executed",
        klt_exit_code=exit_code_for(response),
        gds_path=os.path.relpath(gds_path, REPO_ROOT),
        device_group_count=len(response.get("device_groups") or []),
        net_count=len(nets),
        routed_net_count=len(routed_names),
        klt_routed_net_count=len(klt_routed),
        unrouted_nets=sorted(net["net"] for net in nets if net["net"] not in routed_names),
        unmapped_netlist_nets=sorted(response.get("unmapped_netlist_nets") or []),
        bbox_um=response.get("bbox_um"),
        warning_count=len(response.get("warnings") or []),
        drc=_run_drc(gds_path),
    )
    if routing is not None:
        result["routing"] = {
            "snapped_instances": routing["snapped_instances"],
            "l2n_net_count": routing["l2n_net_count"],
            "shorts": routing["shorts"],
            "problems": routing["problems"],
            "methods": routing["methods"],
        }
    return result


def _complete_routing(
    klt_gds: str, out_gds: str, response: dict, compose_request, klt_routed: set[str]
) -> dict:
    """Snap, route the nets klt left open, re-verify every net, write ``out_gds``."""
    import klayout.db as kdb

    layout = kdb.Layout()
    layout.read(klt_gds)
    top = layout.top_cell()
    geo = _Geometry(layout)
    snapped = _snap_instances(layout, top)

    ports: dict[tuple[str, str], tuple[float, float]] = {}
    origins = compose_request["placement"]["origins_um"]
    inst_origin = {
        inst.cell.name: (inst.trans.disp.x * layout.dbu, inst.trans.disp.y * layout.dbu)
        for inst in top.each_inst()
    }
    for block in compose_request["blocks"]:
        group = block["id"]
        # origins_um is klt's pre-snap placement; the instance is authoritative.
        cell_name = block["generator_report"].get("cell_name") or f"{group}_0"
        ox, oy = next(
            (xy for name, xy in inst_origin.items() if name.endswith(f"__{cell_name}")),
            (origins[group]["x"], origins[group]["y"]),
        )
        for port in block["generator_report"].get("ports") or []:
            ports[(group, port["name"])] = (ox + port["x_um"], oy + port["y_um"])

    routed = _route_scripted(geo, top, response, ports)
    check = _connectivity(geo, top, response.get("nets") or [], ports)
    l2n_nets = _l2n_net_count(layout, top)
    os.makedirs(os.path.dirname(out_gds), exist_ok=True)
    _write_gds(layout, out_gds)

    methods = {"klt-plan": 0, "scripted": 0}
    for net in response.get("nets") or []:
        if net["net"] in klt_routed:
            methods["klt-plan"] += 1
        elif routed["nets"].get(net["net"], {}).get("scripted"):
            methods["scripted"] += 1
    return {
        "routed": check["routed"],
        "shorts": check["shorts"],
        "problems": routed["problems"],
        "methods": methods,
        "snapped_instances": snapped,
        "l2n_net_count": l2n_nets,
        "per_net": routed["nets"],
    }


# --------------------------------------------------------------------------
# Scripted routing (issue #251)
# --------------------------------------------------------------------------


def _snap(um: float) -> float:
    return round(um / GRID_UM) * GRID_UM


class _Geometry:
    """Micron <-> dbu helpers bound to one layout."""

    def __init__(self, layout) -> None:
        import klayout.db as kdb

        self.db = kdb
        self.layout = layout
        self.dbu = layout.dbu

    def d(self, um: float) -> int:
        return int(round(um / self.dbu))

    def box(self, x0: float, y0: float, x1: float, y1: float):
        return self.db.Box(self.d(x0), self.d(y0), self.d(x1), self.d(y1))

    def centred(self, cx: float, cy: float, size: float):
        half = size / 2.0
        return self.box(cx - half, cy - half, cx + half, cy + half)

    def region(self, cell, layer: tuple[int, int]):
        return self.db.Region(cell.begin_shapes_rec(self.layout.layer(*layer)))


def _snap_instances(layout, top) -> int:
    """Snap every top-level instance origin to the manufacturing grid.

    klt's placement accumulates device widths that are not multiples of
    0.005 um (resistor lengths), so every device to the right of one lands
    off-grid and fails ``*.ongrid.1`` wholesale. Moving an origin by at most
    half a grid step changes no device and no size.
    """
    import klayout.db as kdb

    step = int(round(GRID_UM / layout.dbu))
    moved = 0
    for inst in list(top.each_inst()):
        trans = inst.trans
        nx = int(round(trans.disp.x / step)) * step
        ny = int(round(trans.disp.y / step)) * step
        if (nx, ny) == (trans.disp.x, trans.disp.y):
            continue
        new = kdb.Trans(trans.rot, trans.is_mirror(), kdb.Vector(nx, ny))
        top.replace(inst, kdb.CellInstArray(inst.cell_index, new))
        moved += 1
    return moved


def _device_region(geo: _Geometry, top, layer: tuple[int, int]):
    """Merged ``layer`` geometry of the placed devices only -- not the
    top-cell shapes klt's own router drew."""
    region = geo.db.Region()
    li = geo.layout.layer(*layer)
    for inst in top.each_inst():
        sub = geo.db.Region(inst.cell.begin_shapes_rec(li))
        region += sub.transformed(inst.trans)
    return region.merged()


def _pin_geometry(geo: _Geometry, dev_m1, port_x: float, port_y: float, kind: str):
    """Via centre (um) and the host metal-1 polygon for one pin, or ``None``.

    Gates: the via sits on the port point (the centre of the top pad).
    Everything else: on the port's x, ``PIN_VIA_INSET_UM`` above the bottom of
    the metal-1 shape that owns the port, so the stub leaves from the lower
    end of the strip.
    """
    probe = geo.db.Region(geo.centred(port_x, port_y, 0.01))
    hits = dev_m1.interacting(probe)
    polys = list(hits.each())
    if not polys:
        return None
    poly = polys[0]
    cx = _snap(port_x)
    if kind == "top":
        cy = _snap(port_y)
    else:
        cy = _snap(poly.bbox().bottom * geo.dbu + PIN_VIA_INSET_UM)
    via = geo.db.Region(geo.centred(cx, cy, VIA_UM))
    if not (via - geo.db.Region(poly)).is_empty():
        return None
    return cx, cy


def _slot_candidates(geo: _Geometry, top) -> list[float]:
    """Metal-2 corridor x candidates: slots inside the gaps between
    neighbouring devices, plus one either side of the row."""
    boxes = sorted(
        (inst.bbox().left * geo.dbu, inst.bbox().right * geo.dbu)
        for inst in top.each_inst()
    )
    slots: list[float] = []
    pitch = 0.7
    for (_, prev_right), (next_left, _) in zip(boxes, boxes[1:]):
        lo, hi = prev_right + 0.6, next_left - 0.6
        x = lo
        while x <= hi:
            slots.append(_snap(x))
            x += pitch
    slots.append(_snap(boxes[0][0] - 1.5))
    slots.append(_snap(boxes[-1][1] + 1.5))
    return sorted(set(slots))


def _route_scripted(geo: _Geometry, top, response: dict, ports: dict) -> dict:
    """Complete every net klt left unrouted. Returns a per-net summary.

    ``ports`` maps ``(block, port)`` to an absolute ``(x_um, y_um)``.
    """
    dev_m1 = _device_region(geo, top, M1)
    existing_m2 = geo.region(top, M2).merged()
    bbox = top.bbox()
    y_low = bbox.bottom * geo.dbu - CHANNEL_MARGIN_UM
    y_high = bbox.top * geo.dbu + CHANNEL_MARGIN_UM

    todo = [net for net in response.get("nets") or [] if not net.get("routed")]
    todo.sort(key=lambda net: net["net"])
    slots = _slot_candidates(geo, top)
    reserved = geo.db.Region()  # new metal-2, to keep corridors apart
    reserved += existing_m2
    drawn: dict[str, dict] = {}
    low_k = 0
    high_k = 0
    problems: list[str] = []

    for net in todo:
        name = net["net"]
        pins = {"top": [], "bottom": []}
        for pin in net["pins"]:
            key = (pin["block"], pin["port"])
            if key not in ports:
                problems.append(f"{name}: no geometry for pin {key}")
                continue
            kind = "top" if pin["port"].endswith("_G") else "bottom"
            at = _pin_geometry(geo, dev_m1, *ports[key], kind)
            if at is None:
                problems.append(f"{name}: no metal-1 landing for pin {key}")
                continue
            pins[kind].append(at)
        if not pins["top"] and not pins["bottom"]:
            drawn[name] = {"scripted": False, "problems": problems}
            continue

        ys: dict[str, float] = {}
        if pins["bottom"]:
            ys["bottom"] = _snap(y_low - low_k * TRACK_PITCH_UM)
            low_k += 1
        if pins["top"]:
            ys["top"] = _snap(y_high + high_k * TRACK_PITCH_UM)
            high_k += 1

        corridor_x = None
        if len(ys) == 2:
            mean_x = sum(p[0] for k in pins.values() for p in k) / sum(
                len(k) for k in pins.values()
            )
            for x in sorted(slots, key=lambda s: (abs(s - mean_x), s)):
                strip = geo.db.Region(
                    geo.box(
                        x - WIRE_UM / 2, ys["bottom"] - END_EXT_UM,
                        x + WIRE_UM / 2, ys["top"] + END_EXT_UM,
                    )
                )
                if reserved.sized(geo.d(WIRE_UM)).interacting(strip).is_empty():
                    corridor_x = x
                    reserved += strip
                    break
            else:
                problems.append(f"{name}: no free metal-2 corridor slot")
                continue

        shapes = {M2: [], M3: [], VIA1: [], VIA2: []}
        for kind, points in pins.items():
            if not points:
                continue
            track_y = ys[kind]
            xs = [p[0] for p in points]
            for cx, cy in points:
                shapes[VIA1].append(geo.centred(cx, cy, VIA_UM))
                shapes[VIA2].append(geo.centred(cx, track_y, VIA_UM))
                lo, hi = sorted((cy, track_y))
                shapes[M2].append(
                    geo.box(cx - WIRE_UM / 2, lo - END_EXT_UM, cx + WIRE_UM / 2, hi + END_EXT_UM)
                )
            if corridor_x is not None:
                xs.append(corridor_x)
                shapes[VIA2].append(geo.centred(corridor_x, track_y, VIA_UM))
            half = WIRE_UM / 2
            shapes[M3].append(
                geo.box(
                    min(xs) - END_EXT_UM, track_y - half,
                    max(xs) + END_EXT_UM, track_y + half,
                )
            )
        if corridor_x is not None:
            shapes[M2].append(
                geo.box(
                    corridor_x - WIRE_UM / 2,
                    ys["bottom"] - END_EXT_UM,
                    corridor_x + WIRE_UM / 2,
                    ys["top"] + END_EXT_UM,
                )
            )
        for layer, boxes in shapes.items():
            target = top.shapes(geo.layout.layer(*layer))
            for box in boxes:
                target.insert(box)
        drawn[name] = {
            "scripted": True,
            "scripted_pins": len(pins["top"]) + len(pins["bottom"]),
            "tracks_um": ys,
            "corridor_x_um": corridor_x,
        }
    return {"nets": drawn, "problems": problems}


def _connectivity(geo: _Geometry, top, nets: list[dict], ports: dict) -> dict:
    """Flat conductivity check over metal1/via1/metal2/via2/metal3.

    Contacts, poly and diffusion are deliberately not part of the graph: a
    plan pin is a metal-1 shape, and what is being proven is the wiring.
    Returns ``{"routed": {net: bool}, "shorts": [[netA, netB], ...],
    "components": {net: n}}``; a net is routed when all its pins fall in one
    component that no other net's pin shares.
    """
    kdb = geo.db
    conductors = {}
    for name, layer in (("m1", M1), ("m2", M2), ("m3", M3)):
        conductors[name] = list(geo.region(top, layer).merged().each())
    parent: dict[tuple[str, int], tuple[str, int]] = {}

    def find(node):
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a, b):
        parent[find(a)] = find(b)

    def poly_at(layer_name: str, x: int, y: int):
        point = kdb.Point(x, y)
        for index, poly in enumerate(conductors[layer_name]):
            if poly.bbox().contains(point) and poly.inside(point):
                return (layer_name, index)
        return None

    for via_layer, lower, upper in ((VIA1, "m1", "m2"), (VIA2, "m2", "m3")):
        for shape in geo.region(top, via_layer).merged().each():
            centre = shape.bbox().center()
            a = poly_at(lower, centre.x, centre.y)
            b = poly_at(upper, centre.x, centre.y)
            if a and b:
                union(a, b)

    owner: dict[tuple[str, int], set[str]] = {}
    comps: dict[str, set[tuple[str, int]]] = {}
    for net in nets:
        for pin in net["pins"]:
            key = (pin["block"], pin["port"])
            if key not in ports:
                comps.setdefault(net["net"], set()).add(("missing", hash(key)))
                continue
            x, y = ports[key]
            node = poly_at("m1", geo.d(x), geo.d(y))
            if node is None:
                comps.setdefault(net["net"], set()).add(("missing", hash(key)))
                continue
            root = find(node)
            comps.setdefault(net["net"], set()).add(root)
            owner.setdefault(root, set()).add(net["net"])
    shorts = sorted(
        {tuple(sorted(names)) for names in owner.values() if len(names) > 1}
    )
    shorted_nets = {n for pair in shorts for n in pair}
    routed = {
        net: len(roots) == 1
        and not any(r[0] == "missing" for r in roots)
        and net not in shorted_nets
        for net, roots in comps.items()
    }
    return {
        "routed": routed,
        "shorts": [list(pair) for pair in shorts],
        "components": {net: len(roots) for net, roots in comps.items()},
    }


def _l2n_net_count(layout, top) -> int:
    """Independent cross-check of ``_connectivity``: KLayout's own
    LayoutToNetlist over the same five layers. With every plan net routed and
    nothing shorted, the top circuit carries exactly one net per plan net (an
    open adds one, a short removes one)."""
    import klayout.db as kdb

    l2n = kdb.LayoutToNetlist(kdb.RecursiveShapeIterator(layout, top, []))
    conductors = {
        name: l2n.make_layer(layout.layer(*pair), name)
        for name, pair in (
            ("m1", M1), ("v1", VIA1), ("m2", M2), ("v2", VIA2), ("m3", M3)
        )
    }
    for name in conductors:
        l2n.connect(conductors[name])
    for lower, via, upper in (("m1", "v1", "m2"), ("m2", "v2", "m3")):
        l2n.connect(conductors[lower], conductors[via])
        l2n.connect(conductors[via], conductors[upper])
    l2n.extract_netlist()
    return sum(1 for _ in l2n.netlist().top_circuit().each_net())


def _write_gds(layout, path: str) -> None:
    import klayout.db as kdb

    options = kdb.SaveLayoutOptions()
    options.format = "GDS2"
    options.gds2_write_timestamps = False
    layout.write(path, options)


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        routing = entry.get("routing")
        if routing:
            methods = routing["methods"]
            print(
                f"   routing: {methods['klt-plan']} nets by klt-plan, "
                f"{methods['scripted']} scripted; {routing['snapped_instances']} "
                f"instance origins snapped to the 0.005 um grid"
            )
            print(
                f"   cross-check: KLayout LayoutToNetlist finds "
                f"{routing['l2n_net_count']} wired nets (plan has {entry['net_count']})"
            )
            for pair in routing["shorts"]:
                print(f"   SHORT: {' <-> '.join(pair)}")
            for problem in routing["problems"]:
                print(f"   problem: {problem}")
        print(f"   drc: {drc_text}")
        if drc.get("by_rule"):
            for rule, count in drc["by_rule"].items():
                print(f"        {count:5d}  {rule}")
        print()
    summary = report["summary"]
    print(
        f"SUMMARY: {summary['executed']}/{summary['total']} blocks executed, "
        f"{summary['fully_routed']} fully routed, "
        f"{summary['drc_clean']} DRC-clean; "
        f"of the four child-A blocks {summary['deliverable_routed']}/"
        f"{summary['deliverable_total']} fully routed, "
        f"{summary['deliverable_ok']}/{summary['deliverable_total']} also DRC-clean"
    )
    print(f"VERDICT: {summary['verdict']}")


def _routing_method(methods: dict) -> object:
    if not methods["scripted"]:
        return "klt-plan"
    if not methods["klt-plan"]:
        return "scripted"
    return {"klt-plan": methods["klt-plan"], "scripted": methods["scripted"]}


def _routed_ok(entry: dict) -> bool:
    """Every plan net verified connected, and no two nets shorted."""
    return (
        entry["status"] == "executed"
        and bool(entry["net_count"])
        and entry["routed_net_count"] == entry["net_count"]
        and not entry.get("routing", {}).get("shorts")
    )


def _block_ok(entry: dict) -> bool:
    return _routed_ok(entry) and entry["drc"]["status"] == "clean"


def _deliver(blocks: list[dict], klt_version: str, partial: bool) -> list[str]:
    """Copy each fully routed, short-free block into ``layout/analog/`` and
    merge its entry into provenance.json. Returns the blocks refused.

    DRC status is *recorded*, not gated on: a block whose only violations sit
    inside a klt-generated device cell (see layout/README.md) is still the
    honest, reproducible stream, and the sidecar says exactly how clean it is.
    """
    refused: list[str] = []
    existing: dict[str, dict] = {}
    if os.path.exists(PROVENANCE_PATH):
        with open(PROVENANCE_PATH, encoding="utf-8") as handle:
            existing = {e["block"]: e for e in json.load(handle)["blocks"]}
    os.makedirs(DELIVER_DIR, exist_ok=True)
    for entry in blocks:
        block = entry["block"]
        if block not in DELIVERABLE_BLOCKS:
            continue
        if not _routed_ok(entry):
            refused.append(block)
            continue
        source = os.path.join(REPO_ROOT, entry["gds_path"])
        target = os.path.join(DELIVER_DIR, f"{block}.gds")
        shutil.copyfile(source, target)
        selector = "" if not partial else f" --blocks {block}"
        existing[block] = {
            "block": block,
            "gds": os.path.relpath(target, REPO_ROOT),
            "gds_sha256": _sha256(target),
            "netlist_sha256": _sha256(os.path.join(NETLIST_DIR, f"{block}.spice")),
            "plan_sha256": _sha256(os.path.join(PLAN_DIR, f"{block}.json")),
            "klt_version": klt_version,
            "regeneration_command": (
                "PDK_ROOT=$HOME/.volare .venv/bin/python "
                f"scripts/gen_analog_layout.py --deliver{selector}"
            ),
            "routing_method": _routing_method(entry["routing"]["methods"]),
            "net_count": entry["net_count"],
            "drc": entry["drc"],
        }
    if existing:
        document = {
            "schema_version": 1,
            "blocks": [existing[name] for name in sorted(existing)],
        }
        with open(PROVENANCE_PATH, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2)
            handle.write("\n")
    return refused


def _check_provenance(blocks: list[dict], partial: bool) -> list[str]:
    """Compare freshly regenerated GDS hashes to provenance.json."""
    if not os.path.exists(PROVENANCE_PATH):
        return ["layout/analog/provenance.json does not exist"]
    with open(PROVENANCE_PATH, encoding="utf-8") as handle:
        recorded = {e["block"]: e for e in json.load(handle)["blocks"]}
    fresh = {entry["block"]: entry for entry in blocks}
    mismatches: list[str] = []
    for block, record in sorted(recorded.items()):
        entry = fresh.get(block)
        if entry is None:
            if not partial:
                mismatches.append(f"{block}: not regenerated")
            continue
        if entry["status"] != "executed":
            mismatches.append(f"{block}: did not execute")
            continue
        got = _sha256(os.path.join(REPO_ROOT, entry["gds_path"]))
        if got != record["gds_sha256"]:
            mismatches.append(f"{block}: gds_sha256 {got} != recorded {record['gds_sha256']}")
        for key, path in (
            ("netlist_sha256", os.path.join(NETLIST_DIR, f"{block}.spice")),
            ("plan_sha256", os.path.join(PLAN_DIR, f"{block}.json")),
        ):
            if _sha256(path) != record[key]:
                mismatches.append(f"{block}: {key} is stale (input changed since delivery)")
    return mismatches


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
    parser.add_argument(
        "--blocks",
        nargs="+",
        metavar="BLOCK",
        help="only run these blocks (default: every plan)",
    )
    parser.add_argument(
        "--deliver",
        action="store_true",
        help="copy each fully routed, short-free child-A block to "
        "layout/analog/<block>.gds and merge it into layout/analog/provenance.json "
        "(DRC status is recorded there, not gated on)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="regenerate into a scratch directory and compare every gds_sha256 "
        "to layout/analog/provenance.json (exit 3 on mismatch); writes nothing "
        "into the repository",
    )
    args = parser.parse_args(argv)
    if args.deliver and args.check:
        parser.error("--deliver and --check are mutually exclusive")

    try:
        from klayout_tools import __version__ as klt_version
    except ImportError:
        _fail(
            "klayout-tools is not importable. Run ./scripts/setup-env.sh and "
            "activate .venv (see docs/environment-setup.md)."
        )
    try:
        import klayout.db  # noqa: F401
    except ImportError:
        _fail("the klayout python module is not importable (it ships with klt).")
    if "PDK_ROOT" not in os.environ and "GF180_PDK_PATH" not in os.environ:
        print(
            "note: neither PDK_ROOT nor GF180_PDK_PATH is set -- klt will fall "
            "back to its own PDK search roots (see docs/environment-setup.md)",
            file=sys.stderr,
        )

    scratch = tempfile.mkdtemp(prefix="gen-analog-layout-") if args.check else None
    try:
        out_dir = os.path.abspath(scratch or args.out_dir)
        os.makedirs(out_dir, exist_ok=True)

        plans = sorted(glob.glob(os.path.join(PLAN_DIR, "*.json")))
        if args.blocks:
            wanted = set(args.blocks)
            known = {os.path.splitext(os.path.basename(p))[0] for p in plans}
            if wanted - known:
                parser.error(f"unknown block(s): {', '.join(sorted(wanted - known))}")
            plans = [p for p in plans if os.path.splitext(os.path.basename(p))[0] in wanted]
        blocks = [_execute_plan(plan, out_dir, args.keep_work, out_dir) for plan in plans]
        blocks.sort(key=lambda entry: entry["block"])

        executed = [entry for entry in blocks if entry["status"] == "executed"]
        fully_routed = [
            entry
            for entry in executed
            if entry["net_count"] and entry["routed_net_count"] == entry["net_count"]
        ]
        drc_clean = [entry for entry in executed if entry["drc"]["status"] == "clean"]
        deliverable = [e for e in blocks if e["block"] in DELIVERABLE_BLOCKS]
        all_plans = len(glob.glob(os.path.join(PLAN_DIR, "*.json")))
        verdict = (
            "analog layout DELIVERED"
            if len(blocks) == all_plans
            and len(fully_routed) == len(blocks)
            and len(drc_clean) == len(blocks)
            else "analog layout NOT delivered -- see layout/README.md"
        )
        report = {
            "schema_version": 2,
            "klt_version": klt_version,
            "plan_dir": os.path.relpath(PLAN_DIR, REPO_ROOT),
            "out_dir": out_dir,
            "blocks": blocks,
            "summary": {
                "total": len(blocks),
                "executed": len(executed),
                "fully_routed": len(fully_routed),
                "drc_clean": len(drc_clean),
                "deliverable_total": len(deliverable),
                "deliverable_routed": sum(1 for e in deliverable if _routed_ok(e)),
                "deliverable_ok": sum(1 for e in deliverable if _block_ok(e)),
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
            if not args.check:
                print(f"report: {os.path.relpath(report_path, REPO_ROOT)}")

        if args.deliver:
            partial = bool(args.blocks)
            refused = _deliver(blocks, klt_version, partial)
            for block in refused:
                print(
                    f"NOT delivered: {block} (not fully routed / shorted)",
                    file=sys.stderr,
                )
            print(
                "provenance: "
                + os.path.relpath(PROVENANCE_PATH, REPO_ROOT)
                + (f" (refused: {', '.join(refused)})" if refused else "")
            )
        if args.check:
            mismatches = _check_provenance(blocks, bool(args.blocks))
            if mismatches:
                for line in mismatches:
                    print(f"CHECK FAILED: {line}", file=sys.stderr)
                return 3
            print(f"CHECK OK: {len(blocks)} block(s) regenerated; provenance reproduced")
        return 0
    finally:
        if scratch:
            shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
