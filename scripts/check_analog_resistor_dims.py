#!/usr/bin/env python3
"""Check drawn resistor ``L``/``W`` in the analog GDS streams against the
design netlists.

Analog LVS pairs the five committed streams' resistors on topology alone:
``R`` is a ``subckt-call`` placeholder and ``L``/``W`` are
KLayout-secondary, so a match verifies no resistor dimension -- including
the DR-0010 trim-grid deviation the pull-up value depends on. This check
closes that gap for drawn geometry: it reads each resistor's drawn body off
the GDS resistor-marker layer, reads the netlist's ``r_length``/``r_width``,
compares the two exactly in integer database units, and fails on any
difference not explicitly sanctioned below.

Per block ``<block>`` (read from ``layout/analog/provenance.json`` -- never a
hard-coded list):

  * the committed ``layout/analog/<block>.gds``, plan
    ``layout/analog/plans/<block>.json`` and ``design/netlist/<block>.spice``
    must first satisfy the provenance contract of
    ``scripts/check_analog_provenance.py`` (hashes re-computed, DRC recorded
    clean). A stream whose bytes have drifted is refused, never measured;
  * each netlist resistor ``XR<NAME> ... <model> r_width=.. r_length=.. m=1``
    joins to the plan ``res_array`` group whose ``devices[].name == "<NAME>"``
    (all groups must be ``num: 1, dummy: 0``), and from there to the GDS cell
    ``<group_id>__<group_id>_0``;
  * the drawn extent is the bounding box of the resistor-marker layer
    (``110/5`` for ``PPOLYF_U``/``PPOLYF_U_1K``, ``110/11`` for ``RM1``)
    inside that cell, which is exactly ``L`` x ``W`` with no overhead;
  * a device that matches transposed (``W`` as ``L``) is reported as an
    **orientation** finding, distinct from a dimension mismatch.

The comparison is exact and integer: both sides are converted to whole
**nanometers** and compared as ints, with no float pipeline and no epsilon.
(When this check was curated the streams were on a 1 nm grid -- ``dbu ==
0.001`` -- so nanometres and database units were the same integers; the
streams have since been regenerated on a 0.5 nm grid, ``dbu == 0.0005``,
where raw database units would silently change meaning per stream. A
dimension that is not a whole number of nanometres on its stream's grid is
a fail-loud error, never a rounded pass.)

Differences are sanctioned only by the explicit allow-list below: exactly
the five ``dplus_pullup`` trim segments of DR-0010
(``spec/decisions/0010-dplus-pullup-trim-resistor-grid-snap.md``), each
carrying its own expected drawn value. An allow-listed instance drawn at any
*other* value fails, as does an un-allow-listed difference in either
direction, and an allow-list entry that has stopped being needed (the drawn
body now equals the netlist) fails until it is pruned deliberately.

This is a **drawn-geometry** claim: no resistance is computed, no ``klt lvs``
verdict changes, and no simulation is re-run. The klayout import is deferred
to ``main()`` so the comparison half stays importable -- and unit-testable
(``scripts/test_check_analog_resistor_dims.py``) -- on a bare ``python3``
with no klayout, which is why this script is a CI step beside the evidence
linters and *not* part of ``npm run lint``.

Usage: python3 scripts/check_analog_resistor_dims.py [--root DIR] [--json PATH]
Exit codes: 0 every dimension matches or is allow-listed, 1 a dimension
finding (mismatch, orientation, allow-list mismatch, stale entry), 2 an
environment or structural error (klayout missing, provenance drift, a
fail-loud guard, zero resistors found).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from check_analog_provenance import check as check_provenance

SIDECAR = "layout/analog/provenance.json"
PLAN_DIR = "layout/analog/plans"
NETLIST_DIR = "design/netlist"
GDS_DIR = "layout/analog"
NM_PER_UM = 1000

DR0010_DECISION = "spec/decisions/0010-dplus-pullup-trim-resistor-grid-snap.md"

#: The only sanctioned drawn-vs-netlist differences, keyed by
#: ``(block, instance)``. Each entry carries its own expected drawn value in
#: whole nanometres -- DR-0010's Drawn L column -- so a trim segment drawn at
#: any other length fails even though "dplus_pullup is allow-listed" would
#: have waved it through. No ``W`` appears here: every committed ``W`` matches
#: the netlist exactly.
ALLOW_LIST: dict[tuple[str, str], dict] = {
    ("dplus_pullup", "XR0"): {"l_nm": 420, "w_nm": 4000, "decision": DR0010_DECISION},
    ("dplus_pullup", "XR1"): {"l_nm": 685, "w_nm": 4000, "decision": DR0010_DECISION},
    ("dplus_pullup", "XR2"): {"l_nm": 1370, "w_nm": 4000, "decision": DR0010_DECISION},
    ("dplus_pullup", "XR3"): {"l_nm": 2745, "w_nm": 4000, "decision": DR0010_DECISION},
    ("dplus_pullup", "XR4"): {"l_nm": 5485, "w_nm": 4000, "decision": DR0010_DECISION},
}

#: device_class -> (GDS layer, datatype) of the resistor-marker layer whose
#: extent inside the resistor cell is exactly the drawn ``L`` x ``W``.
MARKER_LAYERS: dict[str, tuple[int, int]] = {
    "PPOLYF_U": (110, 5),
    "PPOLYF_U_1K": (110, 5),
    "RM1": (110, 11),
}

VERDICT_OK = ("match", "allow_listed")
VERDICT_FAIL = ("fail", "orientation", "allow_list_mismatch", "stale_allow_list")


class CheckError(Exception):
    """A fail-loud guard or an unreadable input; exits 2, never a pass."""


@dataclass
class NetlistResistor:
    instance: str
    model: str
    l_nm: int
    w_nm: int
    m: int


@dataclass
class Row:
    block: str
    instance: str
    model: str
    nl_l_nm: int
    nl_w_nm: int
    drawn_l_nm: int
    drawn_w_nm: int
    verdict: str
    note: str = ""


# --- pure helpers -----------------------------------------------------------


def marker_layer_for(device_class: str) -> tuple[int, int]:
    try:
        return MARKER_LAYERS[device_class]
    except KeyError:
        known = ", ".join(sorted(MARKER_LAYERS))
        raise CheckError(
            f"device class {device_class!r} has no resistor-marker layer in the "
            f"mapping table (known: {known})"
        ) from None


def param_to_nm(raw: str, param: str) -> int:
    """Parse a SPICE length value in microns into whole nanometres."""
    text = raw.strip().strip("'\"")
    if not text.endswith("u"):
        raise CheckError(
            f"{param}={raw!r} is not a micron value with a 'u' suffix; refusing "
            "to guess units"
        )
    try:
        um = float(text[:-1])
    except ValueError:
        raise CheckError(f"{param}={raw!r} is not a number") from None
    if um <= 0:
        raise CheckError(f"{param}={raw!r} must be positive")
    nm = um * NM_PER_UM
    nearest = round(nm)
    if abs(nm - nearest) > 1e-6:
        raise CheckError(f"{param}={raw!r} is not a whole number of nanometres")
    return nearest


def dbu_to_nm(units: int, dbu: float, ctx: str) -> int:
    """Convert a database-unit measure to whole nanometres on this stream's grid."""
    nm = units * dbu * NM_PER_UM
    nearest = round(nm)
    if abs(nm - nearest) > 1e-6:
        raise CheckError(
            f"{ctx}: {units} dbu at dbu={dbu} is {nm!r} nm, not a whole "
            "nanometre; the exact-integer comparison refuses to round it"
        )
    return nearest


def parse_netlist_resistors(path: Path) -> dict[str, NetlistResistor]:
    """Extract the ``X``-card resistors (``r_width=``/``r_length=``) of a netlist.

    Continuation lines (``+``) are joined before parsing; comment cards
    (first character ``*``) and blank lines are skipped. The device model is
    the token immediately before the first ``key=value`` parameter, which is
    where both the generator's resistor and MOS cards place it.
    """
    logical: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("*"):
            continue
        if line.startswith("+"):
            if not logical:
                raise CheckError(f"{path.name}: continuation card before any top-level card")
            logical[-1] += " " + line[1:].strip()
        else:
            logical.append(line)

    resistors: dict[str, NetlistResistor] = {}
    for card_line in logical:
        tokens = card_line.split()
        if not tokens[0].startswith("X"):
            continue
        first_param = next(
            (i for i, t in enumerate(tokens) if "=" in t), None
        )
        if first_param is None or first_param < 2:
            continue
        params: dict[str, str] = {}
        for token in tokens[first_param:]:
            key, sep, value = token.partition("=")
            if sep:
                params[key] = value
        if "r_width" not in params or "r_length" not in params:
            continue
        inst = tokens[0]
        if not inst.startswith("XR"):
            raise CheckError(
                f"{path.name}: resistor instance {inst!r} lacks the XR prefix "
                "the plan join expects"
            )
        model = tokens[first_param - 1]
        if "m" not in params:
            raise CheckError(f"{path.name}: {inst} has no m= multiplier recorded")
        try:
            m = int(params["m"])
        except ValueError:
            raise CheckError(f"{path.name}: {inst} has unparsable m={params['m']!r}") from None
        if m != 1:
            raise CheckError(
                f"{path.name}: {inst} has m={m}: a multiplied instance makes "
                "per-unit and total length differ and is not supported by this check"
            )
        resistors[inst] = NetlistResistor(
            instance=inst,
            model=model,
            l_nm=param_to_nm(params["r_length"], f"{inst} r_length"),
            w_nm=param_to_nm(params["r_width"], f"{inst} r_width"),
            m=m,
        )
    return resistors


def load_res_array_groups(plan: dict) -> dict[str, dict]:
    """Index the plan's ``res_array`` groups by their single device name.

    Every group must be ``num: 1, dummy: 0`` with exactly one device: a
    series array (or dummy-flanked array) makes per-unit and total length
    differ, and this check measures per-unit cells only.
    """
    groups: dict[str, dict] = {}
    for group in plan.get("device_groups", []):
        if group.get("generator") != "res_array":
            continue
        gid = group.get("id", "<no id>")
        params = group.get("params", {})
        if params.get("num") != 1:
            raise CheckError(
                f"plan group {gid}: num={params.get('num')!r}, not 1; a series "
                "array makes per-unit and total length differ"
            )
        if params.get("dummy") != 0:
            raise CheckError(
                f"plan group {gid}: dummy={params.get('dummy')!r}, not 0"
            )
        devices = group.get("devices", [])
        if len(devices) != 1:
            raise CheckError(
                f"plan group {gid}: {len(devices)} devices, expected exactly 1 "
                "for a num:1 res_array"
            )
        name = devices[0].get("name")
        if name is None:
            raise CheckError(f"plan group {gid}: device has no name")
        if name in groups:
            raise CheckError(f"plan: device name {name!r} appears in two res_array groups")
        groups[name] = group
    return groups


def validate_join(block: str, netlist: dict[str, NetlistResistor], groups: dict[str, dict]) -> None:
    """Both directions of the netlist <-> plan resistor join must be exact."""
    for inst in netlist:
        dev_name = inst[2:]  # XR<NAME> -> <NAME>
        if dev_name not in groups:
            raise CheckError(
                f"{block}: netlist resistor {inst} has no res_array group with "
                f"device name {dev_name!r}"
            )
    for name, group in groups.items():
        inst = f"XR{name}"
        if inst not in netlist:
            raise CheckError(
                f"{block}: plan group {group['id']} device {name!r} has no "
                f"netlist instance {inst}"
            )


def compare(
    block: str,
    netlist: dict[str, NetlistResistor],
    measured: dict[str, tuple[int, int]],
    allow_list: dict[tuple[str, str], dict] | None = None,
) -> list[Row]:
    """Exact whole-nanometre comparison of drawn vs netlist ``L``/``W``."""
    if allow_list is None:
        allow_list = ALLOW_LIST
    rows: list[Row] = []
    for inst in sorted(netlist):
        spec = netlist[inst]
        if inst not in measured:
            raise CheckError(f"{block}: {inst} was joined but never measured")
        drawn_l, drawn_w = measured[inst]
        allowed = allow_list.get((block, inst))
        exact = (drawn_l, drawn_w) == (spec.l_nm, spec.w_nm)
        transposed = (drawn_w, drawn_l) == (spec.l_nm, spec.w_nm)
        allowed_exact = allowed is not None and (drawn_l, drawn_w) == (
            allowed["l_nm"], allowed["w_nm"]
        )
        allowed_transposed = allowed is not None and (drawn_w, drawn_l) == (
            allowed["l_nm"], allowed["w_nm"]
        )
        row = Row(
            block=block,
            instance=inst,
            model=spec.model,
            nl_l_nm=spec.l_nm,
            nl_w_nm=spec.w_nm,
            drawn_l_nm=drawn_l,
            drawn_w_nm=drawn_w,
            verdict="match",
        )
        if exact:
            if allowed is not None:
                row.verdict = "stale_allow_list"
                row.note = (
                    f"allow-list entry {block}.{inst} is no longer needed: the "
                    "drawn body equals the netlist value; prune it deliberately"
                )
        elif transposed:
            row.verdict = "orientation"
            row.note = (
                "marker extent matches transposed (W as L): check the cell's "
                "orientation, not its dimensions"
            )
        elif allowed_exact:
            row.verdict = "allow_listed"
            row.note = allowed["decision"]
        elif allowed_transposed:
            row.verdict = "orientation"
            row.note = f"transposed against the allowed value; {allowed['decision']}"
        elif allowed is not None:
            row.verdict = "allow_list_mismatch"
            row.note = (
                f"drawn L/W ({drawn_l}/{drawn_w} nm) differs from the allowed "
                f"({allowed['l_nm']}/{allowed['w_nm']} nm); {allowed['decision']}"
            )
        else:
            row.verdict = "fail"
        rows.append(row)
    return rows


def check_allowlist_coverage(rows: list[Row], allow_list: dict[tuple[str, str], dict]) -> None:
    known = {(r.block, r.instance) for r in rows}
    for key in allow_list:
        if key not in known:
            raise CheckError(
                f"allow-list entry {key} names no measured resistor; the streams "
                "or the allow-list have drifted"
            )


def ensure_nonempty(rows: list[Row]) -> None:
    if not rows:
        raise CheckError(
            "zero resistor devices found across all blocks -- a zero-resistor "
            "report is an error, never a pass"
        )


def verdict_fails(row: Row) -> bool:
    return row.verdict in VERDICT_FAIL


# --- measurement half (needs klayout; imported lazily in main) --------------


def measure_block(
    kdb, gds_path: Path, groups: dict[str, dict]
) -> dict[str, tuple[int, int]]:
    """Read each resistor group's drawn ``L``/``W`` off the marker layer.

    Values are returned in whole nanometres on the stream's own grid; a
    dimension that is not a whole number of nanometres is a fail-loud error.
    """
    layout = kdb.Layout()
    layout.read(str(gds_path))
    dbu = layout.dbu
    if not dbu or dbu <= 0:
        raise CheckError(f"{gds_path.name}: unreadable dbu {dbu!r}")
    measured: dict[str, tuple[int, int]] = {}
    for dev_name, group in sorted(groups.items()):
        device = group["devices"][0]
        device_class = device.get("device_class", "")
        layer, datatype = marker_layer_for(device_class)
        gid = group["id"]
        cell_name = f"{gid}__{gid}_0"
        cell = layout.cell(cell_name)
        if cell is None:
            raise CheckError(
                f"{gds_path.name}: no cell {cell_name} for res_array group {gid}"
            )
        layer_index = layout.layer(kdb.LayerInfo(layer, datatype))
        region = kdb.Region(cell.begin_shapes_rec(layer_index))
        if region.is_empty():
            raise CheckError(
                f"{gds_path.name}: cell {cell_name} has no {layer}/{datatype} "
                "marker geometry; the drawn body cannot be measured"
            )
        bbox = region.bbox()
        ctx = f"{gds_path.name}:{cell_name}"
        measured[dev_name] = (
            dbu_to_nm(bbox.width(), dbu, f"{ctx} L"),
            dbu_to_nm(bbox.height(), dbu, f"{ctx} W"),
        )
    return measured


# --- reporting ---------------------------------------------------------------


def _um(nm: int) -> str:
    return f"{nm / NM_PER_UM:g}"


def print_report(rows: list[Row]) -> None:
    print(
        f"{'block':<20} {'instance':<10} {'model':<13} {'netL':>7} {'netW':>7} "
        f"{'drawnL':>7} {'drawnW':>7}  verdict (um)"
    )
    for row in rows:
        verdict = {
            "match": "ok",
            "allow_listed": "ALLOWED (DR-0010)",
            "fail": "FAIL",
            "orientation": "ORIENTATION",
            "allow_list_mismatch": "FAIL (allow-list)",
            "stale_allow_list": "STALE ALLOW-LIST",
        }[row.verdict]
        print(
            f"{row.block:<20} {row.instance:<10} {row.model:<13} "
            f"{_um(row.nl_l_nm):>7} {_um(row.nl_w_nm):>7} "
            f"{_um(row.drawn_l_nm):>7} {_um(row.drawn_w_nm):>7}  {verdict}"
        )
        if row.note:
            print(f"    -> {row.note}")
    matches = sum(1 for r in rows if r.verdict == "match")
    allowed = sum(1 for r in rows if r.verdict == "allow_listed")
    failures = sum(1 for r in rows if verdict_fails(r))
    print(
        f"\n{len(rows)} resistor devices: {matches} exact, {allowed} "
        f"allow-listed, {failures} finding(s)"
    )


def report_json(rows: list[Row], sidecar: dict) -> dict:
    by_block = {entry["block"]: entry for entry in sidecar["blocks"]}
    return {
        "claim": "drawn resistor L/W vs netlist r_length/r_width, whole nanometres",
        "blocks": [
            {
                "block": entry["block"],
                "gds": entry.get("gds", f"{GDS_DIR}/{entry['block']}.gds"),
                "gds_sha256": entry.get("gds_sha256"),
            }
            for entry in sidecar["blocks"]
        ],
        "rows": [
            {
                "block": r.block,
                "instance": r.instance,
                "model": r.model,
                "netlist_l_nm": r.nl_l_nm,
                "netlist_w_nm": r.nl_w_nm,
                "drawn_l_nm": r.drawn_l_nm,
                "drawn_w_nm": r.drawn_w_nm,
                "netlist_l_um": r.nl_l_nm / NM_PER_UM,
                "netlist_w_um": r.nl_w_nm / NM_PER_UM,
                "drawn_l_um": r.drawn_l_nm / NM_PER_UM,
                "drawn_w_um": r.drawn_w_nm / NM_PER_UM,
                "verdict": r.verdict,
                "note": r.note,
            }
            for r in rows
        ],
        "allow_list": {
            f"{block}.{inst}": entry for (block, inst), entry in ALLOW_LIST.items()
        },
        "summary": {
            "total": len(rows),
            "match": sum(1 for r in rows if r.verdict == "match"),
            "allow_listed": sum(1 for r in rows if r.verdict == "allow_listed"),
            "findings": sum(1 for r in rows if verdict_fails(r)),
            "by_block": {
                block: sum(1 for r in rows if r.block == block)
                for block in by_block
            },
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", type=Path, help="also write the machine-readable report here")
    args = parser.parse_args(argv)
    root = args.root

    try:
        import klayout.db as kdb
    except ImportError:  # pragma: no cover - environment, not logic
        print(
            "error: klayout is not importable. Provision the pinned environment "
            "with ./scripts/setup-env.sh and run this with that venv's python.",
            file=sys.stderr,
        )
        return 2

    try:
        # Refuse to measure anything unless the whole delivery contract holds
        # (scripts/check_analog_provenance.py re-hashes every GDS, netlist and
        # plan against provenance.json and requires the recorded DRC clean).
        errors, ok = check_provenance(root)
        if errors:
            for e in errors:
                print(f"check_analog_resistor_dims: refusing: {e}", file=sys.stderr)
            return 2
        for line in ok:
            print(line)

        sidecar = json.loads((root / SIDECAR).read_text(encoding="utf-8"))
        rows: list[Row] = []
        for entry in sidecar["blocks"]:
            block = entry["block"]
            netlist = parse_netlist_resistors(root / NETLIST_DIR / f"{block}.spice")
            plan = json.loads(
                (root / PLAN_DIR / f"{block}.json").read_text(encoding="utf-8")
            )
            groups = load_res_array_groups(plan)
            validate_join(block, netlist, groups)
            gds = root / entry.get("gds", f"{GDS_DIR}/{block}.gds")
            measured = measure_block(kdb, gds, groups)
            # measure_block keys by plan device name; the comparison and the
            # allow-list are keyed by netlist instance (XR<NAME>).
            measured = {f"XR{name}": dims for name, dims in measured.items()}
            rows.extend(compare(block, netlist, measured))

        ensure_nonempty(rows)
        check_allowlist_coverage(rows, ALLOW_LIST)
        print_report(rows)

        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(
                json.dumps(report_json(rows, sidecar), indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"report written to {args.json}")

        return 1 if any(verdict_fails(r) for r in rows) else 0
    except CheckError as e:
        print(f"check_analog_resistor_dims: {e}", file=sys.stderr)
        return 2
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"check_analog_resistor_dims: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
