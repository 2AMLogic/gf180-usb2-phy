"""Scripted routing for the analog-block layout generator (issues #251, #372).

The geometry layer extracted from ``gen_analog_layout.py``: after klt's
layout-plan executor has placed and routed what it can, this module completes
every net it left unrouted with a scripted channel route and re-proves the
result (flat conductivity extraction plus KLayout's own LayoutToNetlist).
``gen_analog_layout.py`` imports everything public here; nothing in this
module imports back from it. The on-grid origin assertion stays in
``gen_analog_layout.py`` because it fails the run through ``_fail``, which
belongs to the orchestration side.

Scripted routing. Every plan places one row of tall vertical devices: MOS
source/drain are full-height metal-1 strips, gates end in a metal-1 pad on
top, resistors end in metal-1 heads. A pin gets a via1 on its metal-1 and a
metal-2 stub. Gate pins escape *up* to a per-net metal-3 track above the row,
everything else escapes *down* to a per-net metal-3 track below it (gate and
source/drain stubs of one device sit 0.43 um apart, closer than metal-2
spacing allows, so they never share a side). A net that has both kinds is
joined by one metal-2 corridor in a gap between two devices. Tracks never
share a y, so the only same-layer interactions are stub-vs-stub at distinct
pin x. No device is moved or re-sized. klt 0.9.0 places instance origins on the
0.005 um manufacturing grid (klayout-tools#4202, PR #4244); the generator

The layer-pair and geometry constants at the top are defined here; the
orchestration script imports the ones it also reads back from this module.
"""

from __future__ import annotations

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
# `mos_array`'s contacted well/substrate tap pads (klayout-tools #3648/#4143).
TAP_PAD_PREFIX = "TAP_PAD"


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


def _device_region(geo: _Geometry, top, layer: tuple[int, int]):
    """Merged ``layer`` geometry of the placed devices only -- not the
    top-cell shapes klt's own router drew."""
    region = geo.db.Region()
    li = geo.layout.layer(*layer)
    for inst in top.each_inst():
        sub = geo.db.Region(inst.cell.begin_shapes_rec(li))
        region += sub.transformed(inst.trans)
    return region.merged()


def _pin_anchor(port: str) -> tuple[str, str]:
    """``(channel side, via anchor)`` for one generated port name.

    Gate pins escape up, everything else down (a device's gate and
    source/drain stubs sit 0.43 um apart, closer than metal-2 spacing
    allows, so they never share a side). A tap pad escapes down like a
    source/drain, but takes its via on the port point the way a gate pad
    does: the pad is a 0.42 um square on the committed cells (measured and
    drift-checked by ``_strap_body_pads``, not trusted from a constant) and
    the via 0.26 um, so an inset via -- right for a full-height
    source/drain strip -- would not fit inside it.
    """
    if port.endswith("_G"):
        return "top", "centre"
    if port.startswith(TAP_PAD_PREFIX):
        return "bottom", "centre"
    return "bottom", "inset"


def _pin_geometry(geo: _Geometry, dev_m1, port_x: float, port_y: float, anchor: str):
    """Via centre (um) and the host metal-1 polygon for one pin, or ``None``.

    ``anchor="centre"`` puts the via on the port point itself -- right for a
    gate pad and for a tap pad, both of which are squares barely wider than
    the via. ``anchor="inset"`` puts it on the port's x,
    ``PIN_VIA_INSET_UM`` above the bottom of the metal-1 shape that owns the
    port, so the stub leaves from the lower end of a full-height
    source/drain strip.
    """
    probe = geo.db.Region(geo.centred(port_x, port_y, 0.01))
    hits = dev_m1.interacting(probe)
    polys = list(hits.each())
    if not polys:
        return None
    poly = polys[0]
    cx = _snap(port_x)
    if anchor == "centre":
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


def _route_scripted(
    geo: _Geometry,
    top,
    nets: list[dict],
    ports: dict,
    force: set[str] | None = None,
    dev_m1=None,
) -> dict:
    """Complete every net klt left unrouted, plus every net in ``force``.

    ``ports`` maps ``(block, port)`` to an absolute ``(x_um, y_um)``.
    ``force`` names the nets that must be re-drawn even though klt reports
    them routed -- a body tie adds a tap pad klt's own route never reached.
    """
    if dev_m1 is None:
        dev_m1 = _device_region(geo, top, M1)
    existing_m2 = geo.region(top, M2).merged()
    bbox = top.bbox()
    y_low = bbox.bottom * geo.dbu - CHANNEL_MARGIN_UM
    y_high = bbox.top * geo.dbu + CHANNEL_MARGIN_UM

    force = force or set()
    todo = [
        net for net in nets if not net.get("routed") or net["net"] in force
    ]
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
            kind, anchor = _pin_anchor(pin["port"])
            at = _pin_geometry(geo, dev_m1, *ports[key], anchor)
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
            stub_xs: list[float] = []
            for cx, cy in points:
                shapes[VIA1].append(geo.centred(cx, cy, VIA_UM))
                # A same-net stub landing within one via width of a kept
                # stub's column overlaps that stub's metal-2 band end to end,
                # so it rides the kept via-2: its own cut would sit 0.21 um
                # from the kept one, merging into an over-wide via that
                # fails ``via2.width.1``.
                rides = any(abs(cx - px) < VIA_UM for px in stub_xs)
                if not rides:
                    shapes[VIA2].append(geo.centred(cx, track_y, VIA_UM))
                stub_xs.append(cx)
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
