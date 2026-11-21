#!/usr/bin/env python3
"""Generate analog-block layout from committed klt layout plans (issue #25).

Drives klayout-tools' netlist-driven layout-plan executor (Phase C,
``klayout_tools.layout_plan_execute``) over every plan under
``layout/analog/plans/``, then runs ``klt drc`` on whatever GDS each plan
produced, and prints one honest per-block verdict.

For every block in ``DELIVERABLE_BLOCKS`` -- all five, since issue #252 added
``differential_driver`` to the four of issue #251 -- it also finishes the
routing klt's plan path cannot complete: every net klt leaves unrouted is
completed by a scripted channel route (see "Scripted routing" below), and the
result is re-checked by a flat conductivity extraction -- never by the
router's own bookkeeping -- before a net counts as routed. ``--deliver``
writes the routed GDS per block to ``layout/analog/<block>.gds`` plus
``layout/analog/provenance.json`` (merging per block, so ``--blocks <name>``
leaves the other entries untouched); ``--check`` regenerates into a scratch
directory and compares every ``gds_sha256`` against that sidecar.

One process per plan. The byte order of a stream depends on what ran earlier
in the same interpreter: ``dplus_pullup``'s records changed order the day
``differential_driver`` began executing ahead of it, so its recorded
``gds_sha256`` stopped reproducing even though the geometry was unchanged
(issue #335 -- the cause of the non-reproduction that record
``20261113-133000-f26c7be72693`` reported as not yet explained). A plan
therefore never shares a process with a sibling: a run with more than one
plan executes each in a child interpreter (``_execute_plan_isolated``) and
merges the per-block entries, so a block's GDS is a function of its own
inputs and not of which blocks were selected or in what order. ``--check``
reproduces all five committed streams. See ``layout/README.md`` and
``verification/records/analog-layout/`` for the measurement.

Scripted routing: that geometry layer lives in ``gen_analog_routing.py`` (issue #372); see its docstring.
asserts that and fails the run, naming the instance, if an origin is off-grid.

Body ties and pin labels (issue #346). klt's layout-plan executor derives
``connectivity[]`` from source/drain/gate terminals only -- its
``_TERMINAL_SUFFIXES`` table has no bulk entry -- so a device **body** is
never in a plan net and the contacted tap pads ``mos_array`` draws for
gf180mcu's tap-distance rule stay floating. And the only labels a plan run
leaves behind are the ones klt's own router writes: one per net it drew a
leg for, partially-routed nets included, which is neither the schematic's
port set nor a subset of it. LVS saw both: all five committed streams
mismatched, with every PMOS body on its own anonymous well, every NMOS body
on the deck-synthesized ``vsubs``, and internal nodes exported as pins.

So the same post-plan pass that completes the routing also re-reads the
plan's own netlist digest and, per device group, ties the group's body net
through EVERY ``TAP_PAD*`` port the generator drew for it -- substrate pads
on the nfet groups and n-well pads on the pfet groups alike -- and straps
the group's pads together in metal-1 so each drawn pad reaches the net the
schematic puts that body on (``_netlist_pin_map``, ``_strap_body_pads``),
then re-labels the top cell so its named nets are exactly the reference
``.subckt`` ports (``_write_pin_labels``). A pad the strap cannot carry
keeps its own escape stub, and same-net stubs within one via width of a
kept stub's column ride that stub's via-2. The tool gap is filed as
``2AMLogic/klayout-tools#5546``; nothing here edits a plan or a GDS by hand.

Exit codes (about *the run*, never about the quality of the layout -- read
the report for that):

  0  every plan was executed; a report was written (``--check``: and every
     gds_sha256 reproduced).
  1  the run itself failed (missing klt, unresolvable PDK, an isolated
     per-block run that reported nothing, an unexpected exception).
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

from klt_resolve import klt_argv

# The scripted-routing layer (issue #251) has lived in gen_analog_routing.py
# since issue #372; this import is its whole public surface. The layer
# constants it also defines (GRID_UM / WIRE_UM / TAP_PAD_PREFIX / M1) are
# imported back for the orchestration code below.
from gen_analog_routing import (  # noqa: E402
    GRID_UM,
    M1,
    TAP_PAD_PREFIX,
    WIRE_UM,
    _Geometry,
    _connectivity,
    _device_region,
    _l2n_net_count,
    _route_scripted,
    _snap,
    _write_gds,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN_DIR = os.path.join(REPO_ROOT, "layout", "analog", "plans")
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "layout", "analog", "out")
DELIVER_DIR = os.path.join(REPO_ROOT, "layout", "analog")
PROVENANCE_PATH = os.path.join(DELIVER_DIR, "provenance.json")
NETLIST_DIR = os.path.join(REPO_ROOT, "design", "netlist")

# Every analog block is delivered: the four of child A (issue #251) plus
# differential_driver, child B (issue #252), added once the driver re-size
# (#166/#167) landed and its plan routed 20/20.
DELIVERABLE_BLOCKS = (
    "differential_driver",
    "differential_receiver",
    "dplus_pullup",
    "se_receiver",
)

# gf180mcu's label purposes (datatype 10 on each metal). A kdb.Text on one of
# these names the conductor it sits on; `klt extract` reads nothing else, and
# a net with no text extracts as an anonymous `$<n>` (issue #346 cause C).
M1_LABEL = (34, 10)
LABEL_LAYERS = ((34, 10), (36, 10), (42, 10))
# One drawn tap pad's metal-1 square on the committed streams. This is the
# *checked default*, not the geometry's source of truth: `_strap_body_pads`
# derives each pad's actual square from the stream at its port coordinate
# and refuses a group whose pads drift from this value (the standard
# `scripts/analog_erc.py` holds itself to), never silently trusting it.
PAD_SQUARE_UM = 0.42

def _fail(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    raise SystemExit(1)


def _run_drc(gds_path: str) -> dict:
    argv = klt_argv() + [
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


def _stream_bbox_um(gds_path: str) -> dict | None:
    """The extent of the top cell of the stream at ``gds_path`` (um).

    Measured read-only from the stream itself -- never taken from klt's
    plan-stage response, which describes the pre-scripted-routing
    intermediate (``<block>.klt.gds``) for a scripted block while
    ``gds_path`` names the stream ``_complete_routing()`` wrote
    (issue #427): the upper-metal tracks the scripted pass adds lift the
    true envelope ~19% above the plan-stage one for ``differential_driver``,
    and both fields sit in the same ``blocks[]`` entry. Failures are
    reported by omission (``None``): the ``drc`` entry read from the same
    path carries the reason, and the exit-code contract stays about the
    run, never the quality of the layout.
    """
    import klayout.db as kdb

    try:
        layout = kdb.Layout()
        layout.read(gds_path)
        box = layout.top_cell().dbbox()
    except Exception:  # noqa: BLE001 -- the drc entry read from the same path carries the failure
        return None
    if box.empty():
        return None
    return {"x0": box.left, "y0": box.bottom, "x1": box.right, "y1": box.top}


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
            klt_gds,
            gds_path,
            response,
            captured.get("request"),
            klt_routed,
            _netlist_digest(plan_path, request),
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
        # The committed stream's own envelope, measured from gds_path after
        # scripted routing -- klt's plan-stage envelope describes
        # <block>.klt.gds, not this stream (issue #427), so it is kept under
        # its own name.
        bbox_um=_stream_bbox_um(gds_path),
        plan_bbox_um=response.get("bbox_um"),
        warning_count=len(response.get("warnings") or []),
        drc=_run_drc(gds_path),
    )
    if routing is not None:
        result["routing"] = {
            "l2n_net_count": routing["l2n_net_count"],
            "shorts": routing["shorts"],
            "problems": routing["problems"],
            "methods": routing["methods"],
        }
        result["body_ties"] = routing["body_ties"]
        result["pin_labels"] = routing["pin_labels"]
    return result


def _execute_plan_isolated(plan_path: str, out_dir: str, keep_work: bool) -> dict:
    """Execute one plan in a child interpreter and return its block entry.

    Shape-emission order leaks across ``execute_layout_plan_document()`` calls
    in one process (issue #335), so no plan shares an interpreter with a
    sibling. The child is this same script restricted to one block and asked
    for a machine-readable entry; a block that fails to execute still comes
    back as an entry (``status: execute-failed``) and does not stop the others.
    Only an isolated run that reports *nothing* fails the whole run.
    """
    block = os.path.splitext(os.path.basename(plan_path))[0]
    entry_path = os.path.join(out_dir, f"{block}-block-report.json")
    # A stale entry from an earlier run must never be mistaken for this one's.
    if os.path.exists(entry_path):
        os.remove(entry_path)
    argv = [
        sys.executable,
        os.path.abspath(__file__),
        "--blocks",
        block,
        "--out-dir",
        out_dir,
        "--emit-block-report",
        entry_path,
    ]
    if keep_work:
        argv.append("--keep-work")
    proc = subprocess.run(argv, capture_output=True, text=True)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0 or not os.path.exists(entry_path):
        detail = (proc.stderr or proc.stdout or "no output").strip()[-400:]
        _fail(
            f"{block}: the isolated run exited {proc.returncode} without "
            f"writing {entry_path}: {detail}"
        )
    with open(entry_path, encoding="utf-8") as handle:
        return json.load(handle)


def _netlist_digest(plan_path: str, request: dict) -> dict:
    """The plan's own reference netlist, digested by klt (Phase A).

    The same object ``klt``'s layout-plan executor validates the plan
    against, read a second time here for the two things its own
    ``connectivity[]`` derivation drops: each device's **body** terminal and
    every net's ``is_pin`` flag. Both are needed below and neither is
    recoverable from the executor's response.
    """
    from klayout_tools.netlist_digest import build_netlist_digest

    spec = request["netlist"]
    path = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(plan_path)), spec["path"])
    )
    return build_netlist_digest(
        path,
        top=spec.get("top"),
        form=spec.get("form", "plain-element"),
        deck=spec.get("deck"),
    )


def _tap_pad_pins(ports: list[dict]) -> list[str]:
    """Every contacted tap pad the generator drew for one device group, in
    the group report's own order.

    Every pad of one group contacts the same well (pfet) or the same
    substrate (nfet) conductor -- they are one conductor the moment any metal
    joins them, which is exactly what the strap does -- so all of them belong
    on the group's body net. Empty when the generator drew none (a poly
    resistor's substrate terminal: reported untied, not crashed on)."""
    return [
        str(p["name"])
        for p in ports
        if str(p.get("name", "")).startswith(TAP_PAD_PREFIX)
    ]


def _tap_pad_pin(ports: list[dict]) -> str | None:
    """The one tap pad to *escape* a group's body with: the bottom-facing one
    nearest the group's own x centre, so its stub drops straight into the
    bottom channel without crossing the device. ``None`` when the generator
    drew no pads. Every other pad of the group reaches this one through the
    body strap (:func:`_body_strap_boxes`), so the routed escape stays one
    stub per group no matter how many pads ``mos_array`` drew."""
    pads = [p for p in ports if str(p.get("name", "")).startswith(TAP_PAD_PREFIX)]
    if not pads:
        return None
    facing = [p for p in pads if p.get("direction_deg") == 270] or pads
    centre = sum(p["x_um"] for p in pads) / len(pads)
    return min(facing, key=lambda p: (abs(p["x_um"] - centre), p["name"]))["name"]


def _body_strap_boxes(
    pads: list[tuple[float, float]],
) -> list[tuple[float, float, float, float]]:
    """Metal-1 boxes (um, x0/y0/x1/y1) strapping one group's tap pads into a
    single conductor.

    ``mos_array`` puts every pad on the cell boundary: two pad columns at the
    left and right cell edges, up to several pad rows down the sides plus one
    row across the bottom and the top. The strap draws on exactly those
    lines -- a vertical along EVERY pad column and a horizontal along the
    outermost pad row each end -- so every box hugs the pads' own
    coordinates and the strap never enters the device interior (device
    metal starts 0.44 um inside the outermost pad column, measured on every
    committed ``mos_array`` cell; the inner pad columns sit between the side
    pads and the strips with the same clearance, and a column the spacing
    rule blocks is cut per-segment by ``_strap_body_pads``). Single-pad and
    single-line groups degrade to nothing / one strip."""
    half = WIRE_UM / 2
    points = sorted(set(pads))
    if len(points) < 2:
        return []
    xs = sorted({x for x, _ in points})
    ys = sorted({y for _, y in points})
    if len(xs) == 1:
        return [(xs[0] - half, ys[0] - half, xs[0] + half, ys[-1] + half)]
    if len(ys) == 1:
        return [(xs[0] - half, ys[0] - half, xs[-1] + half, ys[0] + half)]
    boxes: list[tuple[float, float, float, float]] = []
    for x in xs:
        boxes.append((x - half, ys[0] - half, x + half, ys[-1] + half))
    for y in (ys[0], ys[-1]):
        boxes.append((xs[0] - half, y - half, xs[-1] + half, y + half))
    return boxes


def _strap_body_pads(
    geo: _Geometry, top, nets: list[dict], ports: dict, dev_m1
) -> tuple[set[tuple[str, str]], list[str], dict]:
    """Strap each device group's tap pads together in metal-1 where the drawn
    routes leave room, and name the pads the strap already carries.

    Returns ``(strapped, problems, stats)``. ``strapped`` holds the ``(block,
    port)`` keys whose pad the strap connects to the group's escape pad, so
    the scripted router owes them no stub of their own; every pad it does NOT
    name keeps its own escape stub, so a group whose legs are all blocked is
    wired pad-by-pad instead of left floating.

    A leg is drawn only where it clears *foreign* metal-1 -- klt's own routes,
    every other group's device metal, and every strap leg drawn for a group
    processed earlier in this run -- by the metal-1 spacing rule: the
    executor runs gate/source routes across the pad rows of the tall
    ``mos_array`` cells (their bridged shapes sit 0.345 um above the top pad
    row on the committed streams), so a perimeter leg is checked, not
    assumed. Legs join the foreign set as they are drawn (the ``drawn``
    region below), so the clearance between two groups on different body
    nets is a measurement rather than an argument that every leg lies
    inside its own pads' row/column band. A group never blocks itself: its
    own legs enter the set only after it finishes, and an earlier group's
    legs are foreign exactly the way its pads -- which those legs overlap --
    already are. (Before issue #406 this relied on ``klt_m1`` staying a
    *live view*: a KLayout ``Region`` built from ``begin_shapes_rec`` re-reads
    the cell, so legs drawn into ``top`` were invisible to no one. That is
    an implementation detail of KLayout's lazy regions, measured on 0.30.12
    and 0.30.13, not a contract -- an eagerly-materialising Region would
    silently reduce the check to the stale snapshot the rule must never
    trust, so the legs are accumulated explicitly.)

    What a leg may touch of its own group is measured too: each tap pad's
    port coordinate is probed in the device metal (the lookup
    ``_pin_geometry`` uses for a via host) and the hit polygons themselves
    are the only metal-1 a leg may touch besides clear space;
    ``PAD_SQUARE_UM`` is only the committed size that measurement is
    checked against. A tap pad with no metal-1 at its port, pads that
    disagree on their square, or a square drifted from the committed size
    is refused outright and reported -- the way ``scripts/analog_erc.py``
    refuses a spec that drifted from its derivation -- never silently
    absorbed into the constant. A leg the rule blocks is cut back to its
    clear segments along its long axis -- dropping it whole would strand
    every pad behind the band, whose only remaining escape would be a stub
    parallel to a neighbouring stub 0.21 um away, colliding the two via-2
    cuts at the track. Segment ends snap outward to the manufacturing grid
    so no piece lands off ``metal1.ongrid.1``. A leg that would cover a
    non-tap port of the same group is refused outright and reported: the
    perimeter rule never does that on a ``mos_array`` cell, so a refusal
    means a generator this rule does not understand.

    ``stats`` counts ``legs_drawn`` / ``legs_dropped`` / ``groups_strapped``
    and records ``pad_square_um``, the distinct tap-pad squares measured
    across the run -- the report carries the observed value, not the
    constant."""
    strapped: set[tuple[str, str]] = set()
    problems: list[str] = []
    pads_by_group: dict[
        tuple[str, str], list[tuple[tuple[str, str], tuple[float, float]]]
    ] = {}
    group_ports: dict[str, set[str]] = {}
    for net in nets:
        for pin in net["pins"]:
            key = (pin["block"], pin["port"])
            if key not in ports:
                continue
            if str(pin["port"]).startswith(TAP_PAD_PREFIX):
                pads_by_group.setdefault((net["net"], pin["block"]), []).append(
                    (key, ports[key])
                )
            else:
                group_ports.setdefault(pin["block"], set()).add(pin["port"])

    klt_m1 = geo.region(top, M1)  # klt's own routes (recursive: devices too)
    layer = geo.layout.layer(*M1)
    stats = {"legs_drawn": 0, "legs_dropped": 0, "groups_strapped": 0}
    # Strap legs drawn so far, by earlier groups. Also kept out of
    # `klt_m1`'s hands on purpose: whether that Region re-reads `top` is
    # KLayout's laziness, not ours.
    drawn = geo.db.Region()
    observed_squares: set[tuple[float, float]] = set()
    for (net, block), pads in sorted(pads_by_group.items()):
        if len(pads) < 2:
            continue
        pad_ports = [
            {"name": key[1], "x_um": xy[0], "y_um": xy[1]} for key, xy in pads
        ]
        boxes = _body_strap_boxes([(xy[0], xy[1]) for _, xy in pads])
        if not boxes:
            continue
        unsafe = [
            port
            for port in group_ports.get(block, ())
            if any(
                bx0 <= ports[(block, port)][0] <= bx1
                and by0 <= ports[(block, port)][1] <= by1
                for bx0, by0, bx1, by1 in boxes
            )
        ]
        if unsafe:
            problems.append(
                f"{net}: body strap for {block} would cover non-tap port(s) "
                f"{', '.join(sorted(unsafe))} -- group left unstrapped"
            )
            continue
        # Only this group's own pad metal may touch a leg; everything else
        # must clear the metal-1 spacing rule. The pads are *measured*: each
        # tap pad's port coordinate is probed in the device metal (the same
        # lookup `_pin_geometry` uses for a via host) and the hit polygons
        # themselves become `allowed` -- PAD_SQUARE_UM is only the committed
        # size that measurement is checked against. A pad with no metal-1 at
        # its port, pads that disagree on their square, or a square drifted
        # from the committed size is a generator this rule does not
        # understand: the group is left unstrapped (every pad keeps its own
        # escape stub) and the surprise reported, never absorbed into the
        # constant.
        allowed = geo.db.Region()
        pad_size: tuple[float, float] | None = None
        refusal: str | None = None
        for key, (px, py) in pads:
            hits = dev_m1.interacting(geo.db.Region(geo.centred(px, py, 0.01)))
            if hits.is_empty():
                refusal = (
                    f"tap pad {key[1]} at ({px}, {py}) um has no metal-1 "
                    f"at its port"
                )
                break
            allowed += hits
            bb = hits.bbox()
            size = (
                round(bb.width() * geo.dbu, 4),
                round(bb.height() * geo.dbu, 4),
            )
            observed_squares.add(size)
            if pad_size is None:
                pad_size = size
            elif size != pad_size:
                refusal = (
                    f"tap pads disagree on their metal-1 square "
                    f"({size[0]}x{size[1]} vs {pad_size[0]}x{pad_size[1]} um)"
                )
                break
        if refusal is None and pad_size != (PAD_SQUARE_UM, PAD_SQUARE_UM):
            refusal = (
                f"drawn tap-pad square {pad_size[0]}x{pad_size[1]} um has "
                f"drifted from the committed {PAD_SQUARE_UM} um "
                f"(PAD_SQUARE_UM)"
            )
        if refusal is not None:
            problems.append(
                f"{net}: body strap for {block} refused: {refusal} -- "
                f"group left unstrapped"
            )
            continue
        # Foreign metal-1: klt's own routes, every device's metal, and every
        # strap leg drawn by a group processed before this one -- sized by
        # the spacing rule. The group's own pads are removed first: the legs
        # legitimately overlap them, and sized(0.28 um) they would otherwise
        # reject every leg of their own row.
        blocking = ((klt_m1 + dev_m1 + drawn) - allowed).sized(geo.d(WIRE_UM))

        def _clear(box) -> bool:
            leg = geo.db.Region(geo.box(*box)) - allowed
            # Intersection, not "interacting": a piece whose edge merely
            # touches the sized blocking shape sits at exactly the metal-1
            # spacing and is legal, but counts as interacting.
            return (leg & blocking).is_empty()

        def _clear_segments(box) -> list:
            x0, y0, x1, y1 = box
            vertical = (x1 - x0) < (y1 - y0)
            lo_edge, hi_edge = (y0, y1) if vertical else (x0, x1)
            strip = geo.db.Region(geo.box(*box))
            cuts = []
            # Clip the blocking shapes to the leg before reading band edges:
            # "interacting" returns whole polygons, and a serpentine's
            # bounding box spans the entire row, which would cut the leg at
            # nothing.
            for poly in ((blocking - allowed) & strip).each():
                b = poly.bbox()
                lo, hi = (
                    (b.bottom * geo.dbu, b.top * geo.dbu)
                    if vertical
                    else (b.left * geo.dbu, b.right * geo.dbu)
                )
                cuts.append((_snap(lo) - GRID_UM, _snap(hi) + GRID_UM))
            merged: list[list[float]] = []
            for lo, hi in sorted(cuts):
                if merged and lo <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], hi)
                else:
                    merged.append([lo, hi])
            free: list[tuple[float, float]] = []
            cursor = lo_edge
            for lo, hi in merged:
                if lo > cursor:
                    free.append((cursor, min(lo, hi_edge)))
                cursor = max(cursor, hi)
            if cursor < hi_edge:
                free.append((cursor, hi_edge))
            pieces = []
            for lo, hi in free:
                lo, hi = max(lo, lo_edge), min(hi, hi_edge)
                if hi - lo < WIRE_UM:
                    continue
                piece = (
                    (x0, _snap(lo), x1, _snap(hi))
                    if vertical
                    else (_snap(lo), y0, _snap(hi), y1)
                )
                if _clear(piece):
                    pieces.append(piece)
            return pieces

        clear: list[tuple[float, float, float, float]] = []
        for box in boxes:
            if _clear(box):
                clear.append(box)
            else:
                pieces = _clear_segments(box)
                if pieces:
                    clear.extend(pieces)
                else:
                    stats["legs_dropped"] += 1
        stats["legs_drawn"] += len(clear)
        if not clear:
            continue
        for box in clear:
            top.shapes(layer).insert(geo.box(*box))
            drawn.insert(geo.box(*box))
        # A pad is strapped when its pad square and the escape pad's square
        # end up in ONE merged polygon of (drawn legs + every pad square) --
        # per polygon, not per region: blocked leg pieces can leave a pad on
        # its own island.
        joined = geo.db.Region()
        for box in clear:
            joined.insert(geo.box(*box))
        joined += allowed
        joined.merge()

        def _poly_at(px: float, py: float):
            point = geo.db.Point(geo.d(px), geo.d(py))
            for poly in joined.each():
                if poly.bbox().contains(point) and poly.inside(point):
                    return poly
            return None

        escape = _tap_pad_pin(pad_ports)
        ex, ey = ports[(block, escape)]
        escape_poly = _poly_at(ex, ey)
        if escape_poly is None:
            continue
        for key, (px, py) in pads:
            if key[1] != escape and _poly_at(px, py) == escape_poly:
                strapped.add(key)
        stats["groups_strapped"] += 1
    stats["pad_square_um"] = [list(s) for s in sorted(observed_squares)]
    return strapped, problems, stats


def _netlist_pin_map(response: dict, compose_request, digest: dict) -> dict:
    """Resolve every netlist terminal of every placed device onto a generated
    port -- issue #346 causes A, B and C.

    Returns ``{"terminals", "ties", "untied", "problems"}``:

    ``terminals``
        ``{net: [{"block", "port"}, ...]}`` over the terminals klt's own
        ``connectivity[]`` derivation wires (``_TERMINAL_SUFFIXES``), rebuilt
        here because the executor's response drops the one-pin nets -- a net
        with a single terminal has nothing to route, but it is still a port
        that must be named.
    ``ties``
        the same shape for each device **body**. A terminal the generator's
        own suffix table does not map (MOS ``B``; a poly resistor's ``W``) is
        a body: klt therefore never puts it in a plan net, so the contacted
        tap pads ``mos_array`` draws for gf180mcu's tap-distance rule are
        left floating, every PMOS body extracts onto its own anonymous well
        net and every NMOS body onto the deck-synthesized ``vsubs``. That is
        what the first LVS record measured. Filed upstream as a tool gap;
        completed here the same way the scripted routes are.

        Every drawn pad of the group is a tie pin, not just one per group:
        they all contact the one well (pfet) or the one substrate (nfet) its
        devices sit in, and the strap (``_body_strap_boxes``) joins them in
        metal so the body net reaches each pad the generator drew. The
        scripted router still escapes one pad per group (``_tap_pad_pin``) --
        the strap carries the rest to it.
    ``untied``
        ``[{"block", "net"}]`` for a body on a group that draws no tap pad --
        a poly resistor's substrate terminal, which has no tap of its own and
        reaches ground through the shared substrate the nfet groups tie. Not
        a problem; the LVS run is what says whether it landed.
    """
    from klayout_tools.layout_plan_execute import (
        _TERMINAL_SUFFIXES,
        _device_owned_port_names,
    )

    reports = {
        block["id"]: block["generator_report"] for block in compose_request["blocks"]
    }
    by_key = {(d["name"], d["device_class"]): d for d in digest["devices"]}
    terminals: dict[str, list[dict[str, str]]] = {}
    ties: dict[str, list[dict[str, str]]] = {}
    untied: list[dict[str, str]] = []
    problems: list[str] = []
    seen: dict[str, set[tuple[str, str]]] = {}

    def _add(target: dict, net: str, block: str, port: str) -> None:
        if (block, port) in seen.setdefault(net, set()):
            return
        seen[net].add((block, port))
        target.setdefault(net, []).append({"block": block, "port": port})

    for group in response.get("device_groups") or []:
        ports = reports.get(group["id"], {}).get("ports") or []
        suffixes = _TERMINAL_SUFFIXES.get(group["generator"], {})
        candidates = {
            suffix: _device_owned_port_names(ports, suffix)
            for suffix in set(suffixes.values())
        }
        bodies: set[str] = set()
        for index, reference in enumerate(group["devices"]):
            device = by_key.get((reference["name"], reference["device_class"]))
            if device is None:
                continue
            for terminal, net in device["terminals"].items():
                if net is None:
                    continue
                suffix = suffixes.get(terminal)
                if suffix is None:
                    # Not a terminal this generator exposes a port for: the
                    # device's body. Tied below, per group, not per device.
                    bodies.add(net)
                    continue
                names = candidates.get(suffix, [])
                if index < len(names):
                    _add(terminals, net, group["id"], names[index])
        if not bodies:
            continue
        pads = _tap_pad_pins(ports)
        if not pads:
            untied.extend(
                {"block": group["id"], "net": net} for net in sorted(bodies)
            )
            continue
        if len(bodies) > 1:
            problems.append(
                f"{group['id']}: devices disagree on their body net "
                f"({', '.join(sorted(bodies))}) -- one group is one well, so "
                "this group cannot be tied; split it in the plan"
            )
            continue
        body_net = next(iter(bodies))
        for pad in pads:
            _add(ties, body_net, group["id"], pad)
    return {
        "terminals": terminals,
        "ties": ties,
        "untied": untied,
        "problems": problems,
    }


def _augmented_nets(response: dict, ties: dict) -> list[dict]:
    """``response["nets"]`` with each body tie's tap pad added to its net,
    and an entry minted for a body net the plan path has none for."""
    nets = [dict(net, pins=list(net["pins"])) for net in response.get("nets") or []]
    by_name = {net["net"]: net for net in nets}
    for name, pins in sorted(ties.items()):
        net = by_name.get(name)
        if net is None:
            net = {"net": name, "pins": [], "routed": False}
            nets.append(net)
            by_name[name] = net
        net["pins"].extend(pins)
    return nets


def _write_pin_labels(
    geo: _Geometry, top, dev_m1, digest: dict, pin_map: dict, ports: dict
) -> dict:
    """Re-label the top cell so its named nets are exactly the reference
    ``.subckt`` ports -- issue #346 cause C.

    What klt leaves behind is one ``kdb.Text`` per net its own plan router
    drew a leg for, partially-routed nets included: a set that is neither
    the schematic's ports (it misses every net the scripted pass routes,
    including ``VSS`` on all five blocks) nor a subset of them (it names
    internal nodes, which then extract as top-level pins). Since a name is
    the only thing that makes a layout net a pin, every existing label is
    dropped and one is written per ``is_pin`` net of the digest, on the
    metal-1 label purpose at a device terminal of that net.
    """
    cleared = 0
    for pair in LABEL_LAYERS:
        index = geo.layout.layer(*pair)
        for cell in geo.layout.each_cell():
            texts = [s for s in cell.shapes(index).each() if s.is_text()]
            for shape in texts:
                cell.shapes(index).erase(shape)
            cleared += len(texts)

    pins_by_net: dict[str, list[dict]] = {
        net: list(pins) + list(pin_map["ties"].get(net, []))
        for net, pins in pin_map["terminals"].items()
    }
    for net, pins in pin_map["ties"].items():
        pins_by_net.setdefault(net, list(pins))
    written: dict[str, dict] = {}
    missing: list[str] = []
    index = geo.layout.layer(*M1_LABEL)
    for net in digest["nets"]:
        if not net.get("is_pin"):
            continue
        name = net["name"]
        at = None
        for pin in pins_by_net.get(name, []):
            key = (pin["block"], pin["port"])
            if key not in ports:
                continue
            x, y = ports[key]
            probe = geo.db.Region(geo.centred(x, y, 0.01))
            if dev_m1.interacting(probe).is_empty():
                continue
            at = (key, x, y)
            if not pin["port"].startswith(TAP_PAD_PREFIX):
                break
        if at is None:
            missing.append(name)
            continue
        (block, port), x, y = at
        top.shapes(index).insert(
            geo.db.Text(name, geo.db.Trans(geo.db.Vector(geo.d(x), geo.d(y))))
        )
        written[name] = {"block": block, "port": port}
    return {
        "cleared": cleared,
        "layer": list(M1_LABEL),
        "written": written,
        "unlabelled_ports": sorted(missing),
    }


def _complete_routing(
    klt_gds: str,
    out_gds: str,
    response: dict,
    compose_request,
    klt_routed: set[str],
    digest: dict,
) -> dict:
    """Check origins, tie every body, route the nets klt left open, label the
    schematic's ports, re-verify every net, write ``out_gds``."""
    import klayout.db as kdb

    layout = kdb.Layout()
    layout.read(klt_gds)
    top = layout.top_cell()
    geo = _Geometry(layout)
    _assert_origins_on_grid(layout, top)

    ports: dict[tuple[str, str], tuple[float, float]] = {}
    origins = compose_request["placement"]["origins_um"]
    inst_origin = {
        inst.cell.name: (inst.trans.disp.x * layout.dbu, inst.trans.disp.y * layout.dbu)
        for inst in top.each_inst()
    }
    for block in compose_request["blocks"]:
        group = block["id"]
        # origins_um is klt's placement; the instance is authoritative.
        cell_name = block["generator_report"].get("cell_name") or f"{group}_0"
        ox, oy = next(
            (xy for name, xy in inst_origin.items() if name.endswith(f"__{cell_name}")),
            (origins[group]["x"], origins[group]["y"]),
        )
        for port in block["generator_report"].get("ports") or []:
            ports[(group, port["name"])] = (ox + port["x_um"], oy + port["y_um"])

    pin_map = _netlist_pin_map(response, compose_request, digest)
    ties = pin_map["ties"]
    tie_problems = pin_map["problems"]
    nets = _augmented_nets(response, ties)
    # A net klt already routed still has to be re-drawn once it gains a tap
    # pad: klt's own route reaches the device terminals only.
    dev_m1 = _device_region(geo, top, M1)
    # Strap each group's tap pads together in metal-1 where the drawn routes
    # leave room: the router then owes an escape stub only for pads the strap
    # does not already carry.
    strapped, strap_problems, strap_stats = _strap_body_pads(
        geo, top, nets, ports, dev_m1
    )
    route_nets = [
        dict(
            net,
            pins=[
                pin
                for pin in net["pins"]
                if (pin["block"], pin["port"]) not in strapped
            ],
        )
        for net in nets
    ]
    routed = _route_scripted(geo, top, route_nets, ports, force=set(ties), dev_m1=dev_m1)
    check = _connectivity(geo, top, nets, ports)
    labels = _write_pin_labels(geo, top, dev_m1, digest, pin_map, ports)
    l2n_nets = _l2n_net_count(layout, top)
    os.makedirs(os.path.dirname(out_gds), exist_ok=True)
    _write_gds(layout, out_gds)

    methods = {"klt-plan": 0, "scripted": 0}
    for net in nets:
        if net["net"] in klt_routed and net["net"] not in ties:
            methods["klt-plan"] += 1
        elif routed["nets"].get(net["net"], {}).get("scripted"):
            methods["scripted"] += 1
    return {
        "routed": check["routed"],
        "shorts": check["shorts"],
        "problems": tie_problems + strap_problems + routed["problems"],
        "methods": methods,
        "l2n_net_count": l2n_nets,
        "per_net": routed["nets"],
        "body_ties": {
            "nets": {
                net: sorted(pin["block"] for pin in pins)
                for net, pins in sorted(ties.items())
            },
            "tied_groups": sum(len(pins) for pins in ties.values()),
            "untied": pin_map["untied"],
            "problems": tie_problems,
            "straps": strap_stats,
        },
        "pin_labels": labels,
    }


def _assert_origins_on_grid(layout, top) -> None:
    """Fail the run if any top-level instance origin is off the 0.005 um grid.

    klt 0.9.0 places group origins on-grid (klayout-tools#4202); this keeps
    that protection without silently moving geometry the tool owns.
    """
    step = int(round(GRID_UM / layout.dbu))
    # ``each_trans()`` yields every repetition of an array instance (a single
    # element for a plain one), so an off-grid array step is caught too, not
    # only the base displacement. ``disp`` is the origin whatever the
    # instance's rotation / mirror (issue #458).
    bad = [
        f"{inst.cell.name} at ({t.disp.x * layout.dbu:.6f}, "
        f"{t.disp.y * layout.dbu:.6f}) um"
        for inst in top.each_inst()
        for t in inst.cell_inst.each_trans()
        if t.disp.x % step or t.disp.y % step
    ]
    if bad:
        _fail(
            f"instance origin(s) off the {GRID_UM} um manufacturing grid: "
            + "; ".join(bad)
        )


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
                f"{methods['scripted']} scripted"
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
            # Issue #346: what the stream ties and what it names. Both are
            # the difference between this stream and the one that mismatched
            # LVS on every block, so both are pinned here per stream.
            "body_tie_nets": {
                net: len(groups)
                for net, groups in sorted(entry["body_ties"]["nets"].items())
            },
            "pin_labels": sorted(entry["pin_labels"]["written"]),
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
        "--emit-block-report",
        metavar="PATH",
        help=argparse.SUPPRESS,  # internal: used by _execute_plan_isolated
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
    if args.emit_block_report is not None:
        if args.deliver or args.check:
            parser.error("--emit-block-report is incompatible with --deliver/--check")
        if not args.blocks or len(args.blocks) != 1:
            parser.error("--emit-block-report needs exactly one --blocks value")

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
    if (
        args.emit_block_report is None
        and "PDK_ROOT" not in os.environ
        and "GF180_PDK_PATH" not in os.environ
    ):
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
        # One process per plan (issue #335). A lone plan already has an
        # interpreter to itself, so it runs here; a child never re-isolates.
        if args.emit_block_report is None and len(plans) > 1:
            blocks = [
                _execute_plan_isolated(plan, out_dir, args.keep_work) for plan in plans
            ]
        else:
            blocks = [
                _execute_plan(plan, out_dir, args.keep_work, out_dir) for plan in plans
            ]
        blocks.sort(key=lambda entry: entry["block"])

        if args.emit_block_report is not None:
            if not blocks:
                _fail(f"no plan matched --blocks {' '.join(args.blocks)}")
            with open(args.emit_block_report, "w", encoding="utf-8") as handle:
                json.dump(blocks[0], handle, indent=2)
                handle.write("\n")
            return 0

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
