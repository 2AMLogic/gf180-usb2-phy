#!/usr/bin/env python3
"""Supply-connectivity ERC for the analog blocks: the T1 item 11.analog read.

What this checks, precisely
---------------------------
Each committed analog stream under `layout/analog/*.gds` gets a `klt erc`
**supply-spec** run against its own committed spec,
`layout/analog/erc-supply-spec-<block>.json`. That is the structural
power-delivery question of T1 item 11 (`klayout-tools`
`docs/design-evidence-tiers.md`): every declared supply resolves to exactly
one electrical island, no supply short, and every declared well/substrate
tie is *checked* (not skipped as degenerate) and reaches its supply.

The ERC half is only half of item 11.analog. The other half is item 4's own
LVS report with every declared supply paired in its `net_correspondence`,
which `verification/records/analog-lvs/` already carries -- this script
re-reads those committed reports and asserts the pairing, so the compound
citation is verified here rather than asserted in prose.

Why one spec per block (and not one shared spec)
------------------------------------------------
Two things differ per stream and neither can be factored out:

* **The supply names differ.** Four blocks run off `VDD`/`VSS`; `dplus_pullup`
  runs off `VPU_REG`/`VSS` and draws no `VDD` label at all. A shared spec
  declaring `VDD` would resolve zero labelled islands on that block and
  report `erc.unconnected_net` -- a spec artifact, not a layout defect.
* **The substrate assertion is per-stream geometry.** gf180mcu draws no
  pwell/tub layer for a native-substrate block (no `LVPWELL` 204/0 anywhere
  in these five streams, unlike the digital partition's standard-cell rows),
  so the substrate tie must be declared with `well_layer: null` plus
  `well_boxes` (klayout-tools#2255) -- literal micrometre boxes, derived from
  that stream's own diffusion.

`layout/analog/erc-supply-spec.notes.md` carries the full rationale for every
field; this docstring covers only what the harness does with it.

The `well_boxes` derivation, and why it is checked rather than trusted
---------------------------------------------------------------------
`well_boxes` is a *caller assertion*: nothing in the stream corroborates it,
which is why `klt erc` grades such a tie under its own
`erc_coverage.checked_by_well_assertion` bucket. So the boxes are not
hand-typed magic numbers here. They are derived from the stream by one
mechanical rule:

    substrate diffusion  = Comp (22/0) - Nwell (21/0)
    groups               = that region closed over a CLUSTER_GAP_UM (1.1 um)
                           proximity gap (`sized(+gap)`, merged, then
                           intersected back with the diffusion -- the closure
                           only says which shapes belong together, it is not
                           part of the asserted region)
    well_boxes           = the bounding box of each group's own diffusion

and this script **re-derives them on every run and refuses to proceed if a
committed spec's boxes have drifted** (`--regen-specs` to rewrite them on
purpose). A spec that no longer matches the geometry it describes is the
failure mode an asserted region invites, so it is a gate, not a comment.

Five properties of that rule are measured per block and recorded in the
summary, because they are what make the assertion evidence rather than
assertion (see `verdict` in the summary JSON):

* every drawn substrate tap (`Comp n Pplus` outside `Nwell`) lies inside the
  assertion -- so zero `erc.missing_tie` is a statement about all of them;
* every asserted polygon holds at least one such tap -- so no polygon is
  carried by its neighbours;
* the assertion covers far less than the whole top-cell extent, so it is not
  the unfalsifiable "the whole die is the substrate" claim `klt erc` skips as
  `degenerate_well_assertion`;
* the `Pplus` narrowing removes real `Comp` from inside the assertion, so the
  tap side is not `degenerate_tap_declaration` either;
* every asserted polygon holds a body-tie pad that reaches the ground rail
  *in metal* -- the gate that keeps `CLUSTER_GAP_UM` from being set finer
  than the drawn metal supports, measured in `tap_wiring_census`.

The negative control
--------------------
A run that only ever reports "clean" is not evidence. So each block is also
run against a deliberately-wrong spec, derived from its real one by two edits
(`--no-control` to skip):

* the substrate tie's `net` is pointed at the **positive** rail instead of
  ground -- every asserted substrate polygon must then report
  `erc.missing_tie`;
* an extra `kind: "supply"` net named `<neg>_NOT_IN_LAYOUT` is declared --
  which must report `erc.unconnected_net` at zero islands.

Both legs of the clean verdict therefore have a matching failing run, from
the same harness and the same stream.

The tap-wiring census
---------------------
`klt erc` joins conductors only through the declared `stackup`/`vias`; it has
no device recognition and does not model substrate conduction (its own
`erc_coverage.inapplicable` says so). So "the substrate is tied" from this
run means *each asserted patch holds a tap wired up to the ground rail in
metal*, not *every drawn tap pad is wired up*. Those differ in this layout,
measurably, so the census counts it rather than leaving it to prose: per
block, how many drawn substrate tap pads are contacted, and how many of
those reach the ground rail through `Contact`/`Metal1`/`Via*`/`Metal2-3`.
The record quotes those numbers as the stated limit of this evidence.

Usage
-----
    PDK=gf180mcuD python3 scripts/analog_erc.py
    python3 scripts/analog_erc.py --regen-specs     # rewrite well_boxes
    python3 scripts/analog_erc.py --klt .venv/bin/klt

Discovers every `layout/analog/*.gds` (never a hard-coded block list),
requires a matching committed spec for each, and writes its artifacts to
`layout/analog/erc/` (gitignored scratch -- the frozen copies live under
`verification/records/analog-erc/`).

**Exit status is 0 only when every block's verdict passes every gate above**,
including the negative control and the LVS supply pairing. Any violation, any
skipped tie, any drifted spec and any tool failure is non-zero.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECK = "gf180mcu"
GDS_DIR = "layout/analog"
OUT_DIR = "layout/analog/erc"
PROVENANCE = "layout/analog/provenance.json"
LVS_ARTIFACTS = "verification/records/analog-lvs/artifacts"

#: The ground rail every block shares. The positive rail is whatever other
#: net `layout/analog/provenance.json` records as body-tied for the block, so
#: `dplus_pullup`'s `VPU_REG` needs no special case here.
GROUND_NET = "VSS"

#: gf180mcu drawn layers, from the PDK's own `libs.tech/klayout/tech/gf180mcu.lyp`
#: at the pinned open_pdks revision and cross-checked against klayout-tools'
#: curated `gf180mcu` deck layer table (`klayout_tools/decks/gf180mcu.py`).
NWELL = (21, 0)
COMP = (22, 0)
POLY2 = (30, 0)
PPLUS = (31, 0)
NPLUS = (32, 0)
CONTACT = (33, 0)
METAL1 = (34, 0)
METAL1_LABEL = (34, 10)
VIA1 = (35, 0)
METAL2 = (36, 0)
VIA2 = (38, 0)
METAL3 = (42, 0)

#: The proximity gap the substrate-diffusion grouping closes over, in um.
#: It groups a device's diffusion with the body-tie pads drawn beside it.
#: Chosen by measurement, not taste (`--gap-scan`, and the table in
#: `layout/analog/erc-supply-spec.notes.md`): on these five streams the
#: partition is 17/6/6/6/6 polygons for every gap in 1.03-1.15 um, which is
#: the finest partition whose every polygon still holds a body-tie pad
#: wired to the ground rail in metal -- and 1.1 um sits in the middle of that
#: plateau. Finer (<= 1.03 um) splits the partition past what the drawn metal
#: supports and the run reports `erc.missing_tie`; coarser (>= 1.16 um)
#: merges groups and weakens the claim to 4/2/6/2/2 and then 1/2/6/2/2
#: polygons. The `every_asserted_polygon_has_a_metal_wired_tap` gate means
#: this constant cannot be set too fine without the run failing loudly, so
#: it is a granularity knob with a verified floor rather than a tuned
#: magic number.
CLUSTER_GAP_UM = 1.1

#: Tie names the committed specs use, so the harness can look their work
#: identities up in `erc_coverage` without re-parsing the spec twice.
NWELL_TIE = "nwell_pos_tap"
SUBSTRATE_TIE = "substrate_neg_tap"


class HarnessError(Exception):
    """A precondition of the run is unmet (spec drift, missing input)."""


def sh(cmd: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def discover_blocks(gds_dir: str) -> list[str]:
    """Block names from the committed streams, sorted, never hard-coded.

    The same glob `scripts/analog_lvs.py` uses, for the same reason: #339 may
    merge the two single-ended receivers and later work may add streams.
    """
    return sorted(
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(gds_dir, "*.gds"))
    )


def spec_path(block: str) -> str:
    return f"{GDS_DIR}/erc-supply-spec-{block}.json"


def supply_nets(root: str, block: str) -> tuple[str, str]:
    """``(positive, ground)`` for ``block``, from the committed provenance sidecar.

    `layout/analog/provenance.json`'s `body_tie_nets` is the generator's own
    record of which nets every device body is tied to, and
    `scripts/check_analog_provenance.py` keeps it honest. Reading the supply
    names from there rather than from a table in this file is what lets
    `dplus_pullup`'s `VPU_REG` need no special case.
    """
    with open(os.path.join(root, PROVENANCE)) as fh:
        sidecar = json.load(fh)
    entries = {e["block"]: e for e in sidecar.get("blocks", [])}
    if block not in entries:
        raise HarnessError(f"{PROVENANCE}: no entry for block {block!r}")
    nets = sorted(entries[block].get("body_tie_nets") or {})
    if GROUND_NET not in nets:
        raise HarnessError(f"{PROVENANCE}: {block}: body_tie_nets has no {GROUND_NET!r}: {nets}")
    positives = [n for n in nets if n != GROUND_NET]
    if len(positives) != 1:
        raise HarnessError(
            f"{PROVENANCE}: {block}: expected exactly one supply besides "
            f"{GROUND_NET!r}, got {positives}"
        )
    return positives[0], GROUND_NET


# --------------------------------------------------------------------------
# geometry (the only part that needs klayout)
# --------------------------------------------------------------------------


def _layout(kdb, path: str):
    layout = kdb.Layout()
    layout.read(path)
    tops = layout.top_cells()
    if len(tops) != 1:
        raise HarnessError(f"{path}: expected exactly one top cell, got {len(tops)}")
    return layout, tops[0]


def _region(kdb, layout, top, layer: tuple[int, int]):
    region = kdb.Region(top.begin_shapes_rec(layout.layer(*layer)))
    region.merge()
    return region


def _boxes_um(layout, region) -> list[list[float]]:
    """One ``[left, bottom, right, top]`` micrometre box per merged polygon.

    Sorted, so the derivation is byte-reproducible and a drift diff is
    readable rather than a reordering.
    """
    dbu = layout.dbu
    out = []
    for poly in region.each():
        box = poly.bbox()
        out.append(
            [
                round(box.left * dbu, 4),
                round(box.bottom * dbu, 4),
                round(box.right * dbu, 4),
                round(box.top * dbu, 4),
            ]
        )
    return sorted(out)


def derive_well_boxes(kdb, layout, top) -> list[list[float]]:
    """The substrate assertion for this stream: see this module's docstring.

    `Comp - Nwell` closed over `CLUSTER_GAP_UM`, one bounding box per
    resulting group of diffusion. Deliberately *not* `extent - Nwell` (klt erc's own
    `well_complement_of`, klayout-tools#3750): that is one die-sized polygon,
    so `erc.missing_tie` degrades to "does any contact anywhere reach the
    rail", which is the unfalsifiable pass the whole `ties[]` machinery
    exists to refuse. See the notes file's "Rejected alternatives".
    """
    comp = _region(kdb, layout, top, COMP)
    nwell = _region(kdb, layout, top, NWELL)
    substrate_comp = comp - nwell
    substrate_comp.merge()
    gap = int(round(CLUSTER_GAP_UM / layout.dbu))
    closure = substrate_comp.sized(gap)
    closure.merge()
    boxed = kdb.Region()
    for envelope in closure.each():
        # Back to the diffusion itself: the closure only says which shapes
        # belong together, it is not part of the asserted region.
        group = substrate_comp & kdb.Region(envelope)
        if group.is_empty():
            continue
        boxed.insert(group.bbox())
    boxed.merge()
    return _boxes_um(layout, boxed)


def assertion_facts(kdb, layout, top, boxes: list[list[float]]) -> dict:
    """The four falsifiability measurements the module docstring lists, plus
    the tap-wiring census -- all read off the geometry, none inferred."""
    dbu = layout.dbu
    scale = dbu * dbu
    comp = _region(kdb, layout, top, COMP)
    nwell = _region(kdb, layout, top, NWELL)
    pplus = _region(kdb, layout, top, PPLUS)
    nplus = _region(kdb, layout, top, NPLUS)

    asserted = kdb.Region()
    for left, bottom, right, top_um in boxes:
        asserted.insert(
            kdb.Box(
                int(round(left / dbu)),
                int(round(bottom / dbu)),
                int(round(right / dbu)),
                int(round(top_um / dbu)),
            )
        )
    asserted.merge()

    ptap = (comp & pplus) - nwell
    ptap.merge()
    ntap = (comp & nplus) & nwell
    ntap.merge()

    extent = kdb.Region(top.bbox())
    uncovered_extent = (extent - asserted).area()
    narrowed = (comp & asserted) - (comp & pplus)

    per_polygon_without_tap = 0
    for poly in asserted.each():
        if ptap.interacting(kdb.Region(poly.bbox())).count() == 0:
            per_polygon_without_tap += 1

    return {
        "asserted_polygons": asserted.count(),
        "asserted_area_um2": round(asserted.area() * scale, 4),
        "top_extent_area_um2": round(extent.area() * scale, 4),
        "extent_uncovered_fraction": (
            round(uncovered_extent / extent.area(), 6) if extent.area() else None
        ),
        "substrate_taps_drawn": ptap.count(),
        "substrate_tap_area_um2": round(ptap.area() * scale, 4),
        "substrate_tap_area_outside_assertion_um2": round((ptap - asserted).area() * scale, 6),
        "asserted_polygons_without_a_tap": per_polygon_without_tap,
        "tap_narrowing_removed_um2": round(narrowed.area() * scale, 4),
        "comp_area_inside_nwell_um2": round((comp & nwell).area() * scale, 4),
        "nwells_drawn": nwell.count(),
        "nwell_taps_drawn": ntap.count(),
    }


def tap_wiring_census(kdb, layout, top, ground: str, boxes: list[list[float]]) -> dict:
    """Which substrate tap pads actually reach ``ground`` in metal, and where.

    Builds the same conductor graph the spec declares -- `poly2`/`Metal1`/
    `Metal2`/`Metal3` joined through `Contact`/`Via1`/`Via2` -- finds the
    island carrying the ground label on `Metal1_Label`, and counts the
    substrate tap pads whose own `Contact` lands on it.

    Two things come out of that, and both matter to the verdict:

    * the **census**: how many drawn pads are contacted and how many of those
      reach the rail in metal. `klt erc`'s clean verdict does not state this
      (it has no device recognition and does not model substrate conduction),
      so the record states it instead;
    * the **per-asserted-polygon distribution**: how many metal-wired pads
      sit in each asserted substrate polygon. This is what makes the chosen
      granularity checkable rather than tuned -- a partition finer than the
      drawn metal supports has a polygon with none, and the run's own
      `every_asserted_polygon_has_a_metal_wired_tap` gate fails.
    """
    comp = _region(kdb, layout, top, COMP)
    nwell = _region(kdb, layout, top, NWELL)
    pplus = _region(kdb, layout, top, PPLUS)
    contact = _region(kdb, layout, top, CONTACT)
    ptap = (comp & pplus) - nwell
    ptap.merge()

    conductors: list = []
    layer_of: dict[str, list[int]] = {}
    for name, layer in (("poly2", POLY2), ("Metal1", METAL1), ("Metal2", METAL2), ("Metal3", METAL3)):
        for poly in _region(kdb, layout, top, layer).each():
            layer_of.setdefault(name, []).append(len(conductors))
            conductors.append((name, poly))

    parent = list(range(len(conductors)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for via_layer, lower, upper in (
        (CONTACT, "poly2", "Metal1"),
        (VIA1, "Metal1", "Metal2"),
        (VIA2, "Metal2", "Metal3"),
    ):
        for via in _region(kdb, layout, top, via_layer).each():
            footprint = kdb.Region(via)
            touching = [
                i
                for name in (lower, upper)
                for i in layer_of.get(name, [])
                if not kdb.Region(conductors[i][1]).interacting(footprint).is_empty()
            ]
            for other in touching[1:]:
                union(touching[0], other)

    label_positions = []
    iterator = top.begin_shapes_rec(layout.layer(*METAL1_LABEL))
    while not iterator.at_end():
        shape = iterator.shape()
        if shape.is_text():
            text = shape.text.transformed(iterator.trans())
            label_positions.append((shape.text.string, text.x, text.y))
        iterator.next()

    ground_m1 = kdb.Region()
    for name, x, y in label_positions:
        if name != ground:
            continue
        probe = kdb.Region(kdb.Box(x - 1, y - 1, x + 1, y + 1))
        seeds = [
            i
            for i in layer_of.get("Metal1", [])
            if not kdb.Region(conductors[i][1]).interacting(probe).is_empty()
        ]
        if not seeds:
            continue
        root = find(seeds[0])
        for i in layer_of.get("Metal1", []):
            if find(i) == root:
                ground_m1.insert(conductors[i][1])
    ground_m1.merge()

    contacted = 0
    wired = kdb.Region()
    for poly in ptap.each():
        pad_contacts = contact.interacting(kdb.Region(poly))
        if pad_contacts.is_empty():
            continue
        contacted += 1
        if not ground_m1.interacting(pad_contacts).is_empty():
            wired.insert(poly)
    wired.merge()

    dbu = layout.dbu
    per_polygon = []
    for left, bottom, right, top_um in sorted(boxes):
        box = kdb.Region(
            kdb.Box(
                int(round(left / dbu)),
                int(round(bottom / dbu)),
                int(round(right / dbu)),
                int(round(top_um / dbu)),
            )
        )
        per_polygon.append(wired.interacting(box).count())

    return {
        "ground_net": ground,
        "substrate_tap_pads_drawn": ptap.count(),
        "substrate_tap_pads_contacted": contacted,
        "substrate_tap_pads_reaching_ground_in_metal": wired.count(),
        "ground_label_count": sum(1 for name, _, _ in label_positions if name == ground),
        "metal_wired_taps_per_asserted_polygon": per_polygon,
    }


# --------------------------------------------------------------------------
# spec construction
# --------------------------------------------------------------------------


def build_spec(block: str, positive: str, ground: str, well_boxes: list[list[float]]) -> dict:
    """The committed spec for ``block``.

    Field-by-field rationale lives in
    `layout/analog/erc-supply-spec.notes.md`; the `_comment` below is the
    short form that travels with the spec's own content hash.
    """
    return {
        "_comment": [
            f"klt erc supply spec for layout/analog/{block}.gds -- the T1 item",
            "11.analog (power delivery, structural) artifact for this stream",
            "(issue #248). One spec per stream, because both the supply names",
            "and the substrate assertion are per-stream. Regenerate and re-run:",
            "",
            "    PDK=gf180mcuD python3 scripts/analog_erc.py",
            "",
            "which re-derives well_boxes from the GDS and fails on drift.",
            "Field-by-field rationale, the rejected alternatives and the",
            "measured limits of this evidence:",
            "layout/analog/erc-supply-spec.notes.md.",
            "",
            f"Supplies: {positive} (positive), {ground} (ground), read from this",
            "block's body_tie_nets in layout/analog/provenance.json.",
            "",
            f"substrate_neg_tap asserts {len(well_boxes)} substrate region(s).",
            "gf180mcu draws no pwell/tub layer for a native-substrate block, so",
            "well_layer is null and the region is asserted (klayout-tools#2255)",
            "and graded under erc_coverage.checked_by_well_assertion. The boxes",
            "are derived, not hand-typed: Comp (22/0) minus Nwell (21/0),",
            f"grouped by a {CLUSTER_GAP_UM} um proximity closure, one bounding box per",
            "group of diffusion -- the finest partition whose every polygon",
            "still holds a body-tie pad wired to ground in metal.",
        ],
        "stackup": [
            {"name": "poly2", "layer": "30/0", "role": "gate", "active_layer": "22/0"},
            {"name": "Metal1", "layer": "34/0", "label_layer": "34/10"},
            {"name": "Metal2", "layer": "36/0"},
            {"name": "Metal3", "layer": "42/0"},
        ],
        "vias": [
            {"name": "Contact", "layer": "33/0", "between": ["poly2", "Metal1"]},
            {"name": "Via1", "layer": "35/0", "between": ["Metal1", "Metal2"]},
            {"name": "Via2", "layer": "38/0", "between": ["Metal2", "Metal3"]},
        ],
        "nets": [
            {"name": positive, "kind": "supply"},
            {"name": ground, "kind": "supply"},
        ],
        "ties": [
            {
                "name": NWELL_TIE,
                "well_layer": "21/0",
                "tap_layer": "22/0",
                "tap_requires": ["32/0"],
                "connect_to": "Metal1",
                "net": positive,
            },
            {
                "name": SUBSTRATE_TIE,
                "well_layer": None,
                "well_boxes": well_boxes,
                "tap_layer": "22/0",
                "tap_requires": ["31/0"],
                "connect_to": "Metal1",
                "net": ground,
            },
        ],
    }


def build_control_spec(spec: dict, positive: str, ground: str) -> tuple[dict, str]:
    """The deliberately-wrong twin of ``spec`` -- see the module docstring.

    Two edits, both of which must produce a named finding: the substrate tie
    is pointed at the positive rail, and a supply the layout does not label
    is declared.
    """
    control = json.loads(json.dumps(spec))
    absent = f"{ground}_NOT_IN_LAYOUT"
    control["_comment"] = [
        "NEGATIVE CONTROL -- deliberately wrong, never evidence of a clean",
        "layout. Derived from this block's real spec by scripts/analog_erc.py:",
        f"  * {SUBSTRATE_TIE}.net points at {positive} (the positive rail)",
        "    instead of ground, so every asserted substrate polygon must",
        "    report erc.missing_tie;",
        f"  * an extra supply {absent!r} is declared, which the layout labels",
        "    nowhere, so it must report erc.unconnected_net at zero islands.",
        "A clean result here would mean the real spec's clean result proves",
        "nothing. See layout/analog/erc-supply-spec.notes.md.",
    ]
    control["nets"] = list(control["nets"]) + [{"name": absent, "kind": "supply"}]
    for tie in control["ties"]:
        if tie["name"] == SUBSTRATE_TIE:
            tie["net"] = positive
    return control, absent


# --------------------------------------------------------------------------
# verdicts
# --------------------------------------------------------------------------


def work_id(rule: str, name: str) -> str:
    return f'{rule}:["{name}"]'


def grade_run(report: dict, positive: str, ground: str, facts: dict, census: dict) -> dict:
    """The item-11 gates, read off the report rather than off the exit code.

    `klt erc` exits 4 on a run with no `--pdk`, because the *antenna* half
    rolls `not_checked`; item 11 grades `erc_status` and `erc_coverage`
    instead (docs/cli/erc.md, "Two verdicts"). So does this.
    """
    coverage = report.get("erc_coverage") or {}
    checked = set(coverage.get("checked") or [])
    skipped = coverage.get("skipped") or []
    islands = {net["name"]: net.get("matched_islands") for net in report.get("nets") or []}
    findings = report.get("erc_findings") or []
    rules = sorted({f.get("rule") for f in findings})

    gates = {
        "erc_status_clean": report.get("erc_status") == "clean",
        "zero_findings": report.get("erc_finding_count") == 0,
        "no_skipped_work": not skipped,
        "nwell_tie_checked": work_id("erc.missing_tie", NWELL_TIE) in checked,
        "substrate_tie_checked": work_id("erc.missing_tie", SUBSTRATE_TIE) in checked,
        "substrate_tie_graded_by_well_assertion": (
            work_id("erc.missing_tie", SUBSTRATE_TIE)
            in set(coverage.get("checked_by_well_assertion") or [])
        ),
        "positive_supply_one_island": islands.get(positive) == 1,
        "ground_supply_one_island": islands.get(ground) == 1,
        "every_substrate_tap_inside_assertion": (
            facts["substrate_tap_area_outside_assertion_um2"] == 0
        ),
        "every_asserted_polygon_holds_a_tap": facts["asserted_polygons_without_a_tap"] == 0,
        "every_asserted_polygon_has_a_metal_wired_tap": bool(
            census["metal_wired_taps_per_asserted_polygon"]
        )
        and min(census["metal_wired_taps_per_asserted_polygon"]) >= 1,
        "assertion_not_whole_extent": (facts["extent_uncovered_fraction"] or 0) > 0.01,
        "tap_narrowing_is_real": facts["tap_narrowing_removed_um2"] > 0,
        "no_undeclared_drawn_layers": not (
            coverage.get("layers_in_stream_without_declaration") or []
        ),
    }
    return {
        "gates": gates,
        "passed": all(gates.values()),
        "erc_status": report.get("erc_status"),
        "erc_finding_count": report.get("erc_finding_count"),
        "finding_rules": rules,
        "skipped_reasons": [s.get("reason") for s in skipped],
        "matched_islands": islands,
        "inapplicable": coverage.get("inapplicable") or [],
        "well_assertion_coverage": coverage.get("well_assertion_coverage") or [],
    }


def grade_control(report: dict, absent_net: str, asserted_polygons: int) -> dict:
    """The control must fail, in both of the two named ways."""
    findings = report.get("erc_findings") or []
    missing_tie = [
        f for f in findings if f.get("rule") == "erc.missing_tie" and f.get("layer") == SUBSTRATE_TIE
    ]
    unconnected = [
        f
        for f in findings
        if f.get("rule") == "erc.unconnected_net" and f.get("net") == absent_net
    ]
    islands = {net["name"]: net.get("matched_islands") for net in report.get("nets") or []}
    gates = {
        "erc_status_not_clean": report.get("erc_status") != "clean",
        "every_asserted_polygon_reports_missing_tie": (
            len(missing_tie) == asserted_polygons and asserted_polygons > 0
        ),
        "absent_supply_reports_unconnected_net": len(unconnected) >= 1,
        "absent_supply_has_zero_islands": islands.get(absent_net) == 0,
    }
    return {
        "gates": gates,
        "passed": all(gates.values()),
        "erc_status": report.get("erc_status"),
        "erc_finding_count": report.get("erc_finding_count"),
        "missing_tie_findings": len(missing_tie),
        "unconnected_net_findings": len(unconnected),
    }


def grade_lvs_pairing(root: str, block: str, positive: str, ground: str) -> dict:
    """Item 11's other half: both declared supplies paired in item 4's own LVS.

    Reads the newest committed `analog-lvs` artifacts directory, so the
    compound citation is *verified* here rather than asserted in prose. The
    pairing is a participation test, not a second opinion (the item's own
    text says so) -- hence `status == "match"` is gated too.
    """
    candidates = sorted(glob.glob(os.path.join(root, LVS_ARTIFACTS, "*")))
    if not candidates:
        raise HarnessError(f"{LVS_ARTIFACTS}: no committed analog-lvs artifacts")
    newest = candidates[-1]
    path = os.path.join(newest, f"{block}-lvs-report.json")
    if not os.path.exists(path):
        raise HarnessError(f"{path}: no committed LVS report for block {block!r}")
    with open(path) as fh:
        report = json.load(fh)
    paired = {
        entry["reference"]
        for entry in report.get("net_correspondence") or []
        if entry.get("layout") == entry.get("reference")
    }
    gates = {
        "lvs_status_match": report.get("status") == "match",
        "positive_supply_paired": positive in paired,
        "ground_supply_paired": ground in paired,
    }
    return {
        "gates": gates,
        "passed": all(gates.values()),
        "report": os.path.relpath(path, root),
        "lvs_status": report.get("status"),
        "power_connectivity_status": (report.get("power_connectivity") or {}).get("status"),
    }


def gap_scan(kdb, root: str, blocks: list[str], klt: str, gaps: list[float]) -> int:
    """Why `CLUSTER_GAP_UM` is 2.0 um, re-measurable rather than asserted.

    For each gap, derive the assertion that gap implies, run `klt erc` on it,
    and print the resulting polygon count and `erc.missing_tie` count per
    block. Writes nothing: this is the sensitivity measurement the notes file
    and the evidence record quote, not a spec generator.

    The shape it shows on these five streams is two plateaus -- a coarse one
    (device-group granularity) that reports clean, and a finer one that
    reports `erc.missing_tie` per asserted patch, because the layout wires
    one body-tie pad per device group to the rail and leaves the rest to
    substrate conduction, which `klt erc` does not model. Picking a gap
    inside the coarse plateau is picking the finest granularity the drawn
    metal supports; the `census` block reports the per-pad numbers that
    granularity does not state.
    """
    global CLUSTER_GAP_UM
    original = CLUSTER_GAP_UM
    try:
        print(f"{'gap_um':>7}  {'block':24} {'polygons':>8} {'missing_tie':>11}  erc_status")
        for gap in gaps:
            CLUSTER_GAP_UM = gap
            for block in blocks:
                positive, ground = supply_nets(root, block)
                layout, top = _layout(kdb, os.path.join(root, f"{GDS_DIR}/{block}.gds"))
                boxes = derive_well_boxes(kdb, layout, top)
                spec = build_spec(block, positive, ground, boxes)
                scratch = os.path.join(root, OUT_DIR, f"{block}-gap-{gap}-spec.json")
                with open(scratch, "w") as fh:
                    json.dump(spec, fh, indent=2)
                proc = sh(
                    [
                        klt, "erc", f"{GDS_DIR}/{block}.gds",
                        os.path.relpath(scratch, root), "--top", block,
                        "--deck", DECK, "--format", "json",
                    ],
                    cwd=root,
                )
                if not proc.stdout.strip():
                    print(f"error: klt erc failed for {block} at gap {gap}", file=sys.stderr)
                    return 1
                report = json.loads(proc.stdout)
                missing = sum(
                    1
                    for f in report.get("erc_findings") or []
                    if f.get("rule") == "erc.missing_tie"
                )
                print(
                    f"{gap:7.3f}  {block:24} {len(boxes):8} {missing:11}  "
                    f"{report.get('erc_status')}"
                )
    finally:
        CLUSTER_GAP_UM = original
    return 0


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


def run_block(
    kdb,
    root: str,
    block: str,
    klt: str,
    out_dir: str,
    regen: bool,
    control: bool,
) -> dict:
    gds_rel = f"{GDS_DIR}/{block}.gds"
    gds_abs = os.path.join(root, gds_rel)
    positive, ground = supply_nets(root, block)
    layout, top = _layout(kdb, gds_abs)
    if top.name != block:
        raise HarnessError(f"{gds_rel}: top cell {top.name!r} is not the block name {block!r}")

    derived = derive_well_boxes(kdb, layout, top)
    spec_rel = spec_path(block)
    spec_abs = os.path.join(root, spec_rel)

    if regen:
        with open(spec_abs, "w") as fh:
            json.dump(build_spec(block, positive, ground, derived), fh, indent=2)
            fh.write("\n")
        print(f"  regenerated {spec_rel} ({len(derived)} well_boxes)")
    if not os.path.exists(spec_abs):
        raise HarnessError(f"{spec_rel}: missing; run with --regen-specs to create it")

    with open(spec_abs) as fh:
        spec = json.load(fh)
    expected = build_spec(block, positive, ground, derived)
    if spec != expected:
        differing = sorted(
            key for key in set(spec) | set(expected) if spec.get(key) != expected.get(key)
        )
        raise HarnessError(
            f"{spec_rel}: no longer equals the derivation from {gds_rel} "
            f"(differing keys: {differing}). Re-run with --regen-specs if the "
            f"drift is intended, and re-mint the evidence record."
        )

    asserted_boxes = spec["ties"][1]["well_boxes"]
    facts = assertion_facts(kdb, layout, top, asserted_boxes)
    census = tap_wiring_census(kdb, layout, top, ground, asserted_boxes)

    report_rel = f"{out_dir}/{block}-erc-supply-report.json"
    proc = sh(
        [klt, "erc", gds_rel, spec_rel, "--top", block, "--deck", DECK, "--format", "json"],
        cwd=root,
    )
    if not proc.stdout.strip():
        raise HarnessError(f"{block}: klt erc produced no report (exit {proc.returncode})\n{proc.stderr}")
    report = json.loads(proc.stdout)
    with open(os.path.join(root, report_rel), "w") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")

    result = {
        "block": block,
        "gds": gds_rel,
        "gds_sha256": f"sha256:{sha256(gds_abs)}",
        "spec": spec_rel,
        "spec_sha256": f"sha256:{sha256(spec_abs)}",
        "supplies": {"positive": positive, "ground": ground},
        "report": report_rel,
        "exit_status": proc.returncode,
        "assertion": facts,
        "census": census,
        "verdict": grade_run(report, positive, ground, facts, census),
        "lvs_pairing": grade_lvs_pairing(root, block, positive, ground),
    }

    if control:
        control_spec, absent = build_control_spec(expected, positive, ground)
        control_spec_rel = f"{out_dir}/{block}-erc-control-spec.json"
        with open(os.path.join(root, control_spec_rel), "w") as fh:
            json.dump(control_spec, fh, indent=2)
            fh.write("\n")
        control_report_rel = f"{out_dir}/{block}-erc-control-report.json"
        cproc = sh(
            [
                klt, "erc", gds_rel, control_spec_rel, "--top", block,
                "--deck", DECK, "--format", "json",
            ],
            cwd=root,
        )
        if not cproc.stdout.strip():
            raise HarnessError(
                f"{block}: control klt erc produced no report (exit {cproc.returncode})\n{cproc.stderr}"
            )
        creport = json.loads(cproc.stdout)
        with open(os.path.join(root, control_report_rel), "w") as fh:
            json.dump(creport, fh, indent=2)
            fh.write("\n")
        result["control"] = {
            "spec": control_spec_rel,
            "report": control_report_rel,
            "exit_status": cproc.returncode,
            "absent_net": absent,
            "verdict": grade_control(creport, absent, facts["asserted_polygons"]),
        }

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=REPO_ROOT, help="repo root (default: this script's)")
    parser.add_argument("--klt", default="klt", help="klt executable (default: klt on $PATH)")
    parser.add_argument(
        "--regen-specs",
        action="store_true",
        help="rewrite each committed spec from the derivation instead of checking it",
    )
    parser.add_argument(
        "--no-control",
        action="store_true",
        help="skip the deliberately-wrong control run (not for evidence)",
    )
    parser.add_argument("--block", action="append", help="limit to this block (repeatable)")
    parser.add_argument(
        "--gap-scan",
        metavar="GAPS",
        help="comma-separated proximity gaps in um; report the assertion each "
        "implies and the erc.missing_tie count it produces, write no spec, and "
        "exit (the sensitivity measurement behind CLUSTER_GAP_UM)",
    )
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    try:
        import klayout.db as kdb
    except ImportError:  # pragma: no cover - environment, not logic
        print(
            "error: klayout is not importable. Provision the pinned environment "
            "with ./scripts/setup-env.sh and run this with that venv's python.",
            file=sys.stderr,
        )
        return 2

    blocks = discover_blocks(os.path.join(root, GDS_DIR))
    if args.block:
        unknown = sorted(set(args.block) - set(blocks))
        if unknown:
            print(f"error: no such committed stream(s): {unknown}", file=sys.stderr)
            return 2
        blocks = [b for b in blocks if b in args.block]
    if not blocks:
        print(f"error: no streams under {GDS_DIR}/*.gds", file=sys.stderr)
        return 2

    os.makedirs(os.path.join(root, OUT_DIR), exist_ok=True)

    if args.gap_scan:
        try:
            gaps = [float(g) for g in args.gap_scan.split(",") if g.strip()]
        except ValueError:
            print(f"error: --gap-scan expects numbers, got {args.gap_scan!r}", file=sys.stderr)
            return 2
        return gap_scan(kdb, root, blocks, args.klt, gaps)

    results = []
    for block in blocks:
        print(f"== {block}")
        try:
            results.append(
                run_block(
                    kdb, root, block, args.klt, OUT_DIR, args.regen_specs, not args.no_control
                )
            )
        except HarnessError as exc:
            print(f"FAIL {block}: {exc}", file=sys.stderr)
            return 1
        result = results[-1]
        verdict = result["verdict"]
        print(
            f"   erc_status={verdict['erc_status']} findings={verdict['erc_finding_count']} "
            f"islands={verdict['matched_islands']} "
            f"asserted_polygons={result['assertion']['asserted_polygons']} "
            f"-> {'PASS' if verdict['passed'] else 'FAIL'}"
        )
        for name, ok in sorted(verdict["gates"].items()):
            if not ok:
                print(f"   FAILED GATE {name}", file=sys.stderr)
        if not result["lvs_pairing"]["passed"]:
            for name, ok in sorted(result["lvs_pairing"]["gates"].items()):
                if not ok:
                    print(f"   FAILED LVS-PAIRING GATE {name}", file=sys.stderr)
        if "control" in result:
            cv = result["control"]["verdict"]
            print(
                f"   control: erc_status={cv['erc_status']} "
                f"missing_tie={cv['missing_tie_findings']} "
                f"unconnected_net={cv['unconnected_net_findings']} "
                f"-> {'PASS' if cv['passed'] else 'FAIL'}"
            )
            for name, ok in sorted(cv["gates"].items()):
                if not ok:
                    print(f"   FAILED CONTROL GATE {name}", file=sys.stderr)

    ok = all(
        r["verdict"]["passed"]
        and r["lvs_pairing"]["passed"]
        and (r.get("control", {}).get("verdict", {}).get("passed", True))
        for r in results
    )
    summary = {
        "schema_version": 1,
        "harness": "scripts/analog_erc.py",
        "deck": DECK,
        "cluster_gap_um": CLUSTER_GAP_UM,
        "blocks": results,
        "all_blocks_pass": ok,
    }
    summary_rel = f"{OUT_DIR}/analog-erc-summary.json"
    with open(os.path.join(root, summary_rel), "w") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")
    print(f"\nwrote {summary_rel}: all_blocks_pass={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
