#!/usr/bin/env python3
"""Gate-level LVS for the digital PHY: routed GDS vs. the as-built netlist.

What this checks, precisely
---------------------------
`klt place-and-route` writes three coupled artifacts for `rtl/usb_utmi_phy.v`:
a routed DEF, the merged GDS, and the *as-built* gate-level Verilog
(`write_verilog` — CTS buffers, resizes and antenna diodes included). This
script asks the one question LVS exists to answer for a standard-cell block:

    does the GDS instantiate exactly the cells the as-built netlist names,
    wired to exactly the same nets?

It answers it by comparing two netlists with `klt lvs`:

* **layout side** — `klt extract` on the routed GDS with every *logic* cell
  type held as an opaque black box (`--abstract-cells`), so the comparison is
  at the gate level rather than the transistor level. Physical-only cells
  (`fill_*`, `endcap`, `filltie`) are deliberately *not* abstracted: they are
  flattened, contribute zero devices, and therefore vanish from the compare —
  which is what makes a filler-bearing layout comparable against a netlist
  that (correctly) does not name fillers.
* **reference side** — a SPICE transcription of the as-built Verilog,
  generated here: one empty `.SUBCKT` per logic cell type and one `X` card per
  instance.

Why the transcription is not circular. The `.SUBCKT` *pin ordering* is read
back from the extracted layout netlist, because SPICE has no named-port
syntax and both sides must agree on a column order. Every *connection* is
mapped by **pin name** out of the Verilog's own named port connections
(`.A1(net)`), never by position — so an ordering taken from the layout side
cannot mask a real wiring difference: it would surface as a mismatch, not as
a false match. Supply pins are the one thing the Verilog does not name; they
are bound from `flow/request-usb-utmi-phy-par.json`'s own `power` block
(`power_net`/`ground_net`), i.e. from the same request that told OpenROAD's
`global_connect` how to wire them.

What this does NOT check: transistor-level equivalence of the standard cells
themselves (they are black boxes here — the foundry's own characterized GDS is
taken as correct), and anything analog. See `layout/README.md`.

Usage
-----
    PDK=gf180mcuD python3 scripts/digital_lvs.py

Runs against the committed signoff pair in `layout/digital/`
(`usb_utmi_phy.gds` + `usb_utmi_phy_routed.v`) by default; `--gds`/`--verilog`
point it at a fresh `flow/.klt/place-and-route/` run instead. Writes its
artifacts to `layout/digital/lvs/` (gitignored scratch — the frozen copies
live under `verification/records/digital-lvs/`) and prints the `klt lvs`
verdict. Exit status is 0 only on `status: "match"`.

    PDK=gf180mcuD python3 scripts/digital_lvs.py --negative-control

re-runs the same compare against a deliberately broken reference and requires
it to fail, which is what makes the clean result above mean something.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Cell-name prefixes that are physical-only fill/tie/endcap masters: present in
# the routed DEF/GDS because `klt place-and-route`'s `request.power` stage
# inserts them, absent from the as-built Verilog because they carry no logic.
# They are left un-abstracted on purpose (see the module docstring).
PHYSICAL_ONLY = ("__fill_", "__filltie", "__endcap")


def _sh(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def parse_verilog(path: str) -> tuple[list[str], list[tuple[str, str, dict[str, str]]]]:
    """Return (top-level port names, instances) from structural Verilog.

    Ports are expanded bit-by-bit (`DataIn[7:0]` -> `DataIn[0]` ...) to match
    the per-bit net names `klt extract --def-net-names` recovers from the DEF.
    Instances are `(cell_type, instance_name, {pin: net})`.
    """
    src = open(path, encoding="utf-8").read()
    # Strip line comments; the generated netlist has no block comments.
    src = re.sub(r"//[^\n]*", "", src)

    ports: list[str] = []
    for kind, rng, names in re.findall(
        r"\b(input|output|inout)\s+(\[\s*\d+\s*:\s*\d+\s*\])?\s*([^;]+);", src
    ):
        del kind
        for name in (n.strip() for n in names.split(",")):
            if not name:
                continue
            if rng:
                hi, lo = (int(x) for x in re.findall(r"\d+", rng))
                lo, hi = min(hi, lo), max(hi, lo)
                ports.extend(f"{name}[{i}]" for i in range(lo, hi + 1))
            else:
                ports.append(name)

    # `assign <port> = <net>;` aliases. Yosys emits one per output port whose
    # driver already has a name of its own (`assign LineState[0] =
    # line_state[0];`), and OpenROAD writes the DEF net under the *driver's*
    # name with the port hung off it as a PIN. `klt extract --def-net-names`
    # therefore recovers `line_state[0]`, not `LineState[0]` — so the port has
    # to be resolved through the alias before the two sides can be compared.
    aliases = {
        unescape_verilog(lhs): unescape_verilog(rhs)
        for lhs, rhs in re.findall(r"\bassign\s+([^=;]+?)\s*=\s*([^;]+?)\s*;", src)
    }
    ports = [aliases.get(p, p) for p in ports]

    instances: list[tuple[str, str, dict[str, str]]] = []
    for cell, inst, body in re.findall(
        r"\b(gf180mcu_fd_sc_\w+)\s+(\S+)\s*\(([^;]*?)\)\s*;", src, re.S
    ):
        conns = {
            pin: unescape_verilog(net)
            for pin, net in re.findall(r"\.(\w+)\s*\(([^)]*?)\)", body)
        }
        instances.append((cell, unescape_verilog(inst), conns))
    return ports, instances


def unescape_verilog(name: str) -> str:
    r"""Normalize a Verilog identifier to the plain net name the DEF carries.

    OpenROAD's `write_verilog` emits hierarchical names as *escaped
    identifiers*: `\u_destuffer/ones` — a backslash, then everything up to the
    terminating whitespace. A bit-select of one is written `\u_destuffer/ones
    [2]`, i.e. escaped identifier, terminator space, then the index. The DEF
    (and so `klt extract --def-net-names`) knows that net as
    `u_destuffer/ones[2]`, so both the leading backslash and the terminator
    space have to come back out before the two sides can be compared.
    """
    name = name.strip()
    if name.startswith("\\"):
        name = name[1:]
    return re.sub(r"\s+(?=\[)", "", name)


def parse_subckt_pins(spice_path: str) -> dict[str, list[str]]:
    """Pin order per `.SUBCKT` in a SPICE file (continuation lines folded)."""
    text = open(spice_path, encoding="utf-8").read()
    text = re.sub(r"\n\+\s*", " ", text)
    out: dict[str, list[str]] = {}
    for line in text.splitlines():
        m = re.match(r"\.SUBCKT\s+(\S+)\s*(.*)", line, re.I)
        if m:
            out[m.group(1)] = m.group(2).split()
    return out


def spice_name(net: str) -> str:
    r"""Render a net name the way KLayout's own SPICE writer renders it.

    Both sides of the compare have to spell a net identically, so this mirrors
    the escaping observed in `klt extract`'s output rather than inventing one:
    a name that does not begin with a letter (`_000_`, `$1043`) is written with
    a leading backslash; everything else — including names carrying `/` and
    `[...]`, e.g. `u_sync_detector/match[0]` — is written bare.
    """
    return net if re.match(r"^[A-Za-z]", net) else "\\" + net


def write_reference(
    out_path: str,
    top: str,
    ports: list[str],
    instances: list[tuple[str, str, dict[str, str]]],
    pin_order: dict[str, list[str]],
    power_net: str,
    ground_net: str,
    negative_control: bool = False,
) -> None:
    if negative_control:
        # Deliberately break one connection so a *passing* compare can be told
        # apart from a compare that never looked: rewire the first instance's
        # first non-supply input to the supply. `klt lvs` must report this as a
        # mismatch; if it still says "match", the harness is not testing
        # anything and the clean result above is worthless.
        cell, inst, conns = instances[0]
        for pin in pin_order[cell]:
            if pin not in (power_net, ground_net) and conns.get(pin):
                conns = dict(conns, **{pin: ground_net})
                break
        instances = [(cell, inst, conns)] + list(instances[1:])

    lines = [
        "* reference netlist for `klt lvs`, generated by scripts/digital_lvs.py",
        "* source: the as-built gate-level Verilog from `klt place-and-route`",
        "",
    ]
    cell_types = sorted({c for c, _, _ in instances})
    for cell in cell_types:
        pins = pin_order.get(cell)
        if pins is None:
            raise SystemExit(
                f"no extracted .SUBCKT pin order for cell type '{cell}' -- the "
                "layout does not instantiate a cell the netlist names"
            )
        lines.append(f".SUBCKT {cell} {' '.join(pins)}")
        lines.append(".ENDS")
    lines.append("")

    # Top-level pin order is taken verbatim from the extracted layout netlist
    # (`ports` is only used to cross-check that the two agree as a *set*), so
    # the two circuits' pin columns line up without depending on either side's
    # sort order. A port present on one side only is a real finding, so it is
    # raised here rather than papered over.
    top_pins = pin_order[top]
    expected = {spice_name(p) for p in ports} | {power_net, ground_net}
    if set(top_pins) != expected:
        only_layout = sorted(set(top_pins) - expected)
        only_netlist = sorted(expected - set(top_pins))
        raise SystemExit(
            "top-level pin sets differ between the extracted layout and the "
            f"as-built netlist: layout-only {only_layout}, netlist-only {only_netlist}"
        )
    lines.append(f".SUBCKT {top} {' '.join(top_pins)}")
    for cell, inst, conns in instances:
        args = []
        for pin in pin_order[cell]:
            if pin == power_net:
                args.append(power_net)
            elif pin == ground_net:
                args.append(ground_net)
            elif conns.get(pin):
                args.append(spice_name(conns[pin]))
            else:
                # A pin the as-built Verilog leaves unconnected -- CTS's own
                # `clkload*` dummy loads are instantiated with only their input
                # tied. Give it a per-instance dangling node so it stays a
                # one-terminal net on this side too, matching the isolated pin
                # shape the layout side extracts. Naming it (rather than
                # reusing one shared node) is what keeps two such pins from
                # being silently shorted together in the reference.
                args.append(spice_name(f"{inst}/{pin}.unconnected"))
        lines.append(f"X{spice_name(inst)} {' '.join(args)} {cell}")
    lines.append(".ENDS")
    lines.append("")
    open(out_path, "w", encoding="utf-8").write("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--gds",
        default=os.path.join(REPO_ROOT, "layout", "digital", "usb_utmi_phy.gds"),
        help="routed GDS to extract (default: the committed signoff copy)",
    )
    ap.add_argument(
        "--verilog",
        default=os.path.join(
            REPO_ROOT, "layout", "digital", "usb_utmi_phy_routed.v"
        ),
        help=(
            "as-built gate-level Verilog to compare against (default: the "
            "committed signoff copy). Must be `klt place-and-route`'s own "
            "`write_verilog` output for THIS GDS, not the pre-CTS synthesis "
            "netlist"
        ),
    )
    ap.add_argument(
        "--out-dir",
        default=os.path.join(REPO_ROOT, "layout", "digital", "lvs"),
        help="where to write the extracted/reference netlists and reports",
    )
    ap.add_argument("--top", default="usb_utmi_phy")
    ap.add_argument(
        "--par-request",
        default=os.path.join(REPO_ROOT, "flow", "request-usb-utmi-phy-par.json"),
    )
    ap.add_argument(
        "--negative-control",
        action="store_true",
        help=(
            "break one reference connection on purpose and require `klt lvs` to "
            "report a mismatch; exits 0 only when the compare correctly fails"
        ),
    )
    args = ap.parse_args()

    gds, verilog = args.gds, args.verilog
    for path in (gds, verilog):
        if not os.path.exists(path):
            raise SystemExit(
                f"missing {path} -- run the `klt synthesize` + `klt place-and-route` "
                "chain in flow/README.md first"
            )
    os.makedirs(args.out_dir, exist_ok=True)

    par_req = json.load(open(args.par_request, encoding="utf-8"))
    power_block = par_req.get("power") or {}
    power_net = power_block.get("power_net", "VDD")
    ground_net = power_block.get("ground_net", "VSS")

    ports, instances = parse_verilog(verilog)
    cell_types = sorted({c for c, _, _ in instances})
    print(
        f"as-built netlist: {len(instances)} instances, "
        f"{len(cell_types)} cell types, {len(ports)} top-level ports"
    )

    lef_dir = None
    pdk_root = os.environ.get("PDK_ROOT")
    if pdk_root:
        for root, _dirs, files in os.walk(pdk_root):
            if "gf180mcu_fd_sc_mcu9t5v0.lef" in files:
                lef_dir = os.path.join(root, "gf180mcu_fd_sc_mcu9t5v0.lef")
                break

    layout_spice = os.path.join(args.out_dir, f"{args.top}_layout.spice")
    extract_cmd = [
        "klt",
        "extract",
        gds,
        "--deck",
        "gf180mcu",
        "--top",
        args.top,
        "--def-net-names",
        "--top-cell-pins",
        "--pins",
        ",".join(ports + [power_net, ground_net]),
        "-o",
        layout_spice,
        "--format",
        "json",
    ]
    for cell in cell_types:
        if any(marker in cell for marker in PHYSICAL_ONLY):
            continue
        extract_cmd += ["--abstract-cells", cell]
    if lef_dir:
        extract_cmd += ["--abstract-cell-lef", lef_dir]

    proc = _sh(extract_cmd)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        raise SystemExit(f"klt extract failed (exit {proc.returncode})")
    extract_report = json.loads(proc.stdout)
    with open(
        os.path.join(args.out_dir, "extract-report.json"), "w", encoding="utf-8"
    ) as fh:
        json.dump(extract_report, fh, indent=2)
    print(
        f"extracted: {extract_report['net_count']} nets, "
        f"{extract_report['device_count']} loose devices, "
        f"{len(extract_report['abstracted_cells'])} abstracted cell types"
    )

    pin_order = parse_subckt_pins(layout_spice)
    suffix = "_reference_negctl" if args.negative_control else "_reference"
    reference_spice = os.path.join(args.out_dir, f"{args.top}{suffix}.spice")
    write_reference(
        reference_spice,
        args.top,
        ports,
        instances,
        pin_order,
        power_net,
        ground_net,
        negative_control=args.negative_control,
    )

    lvs_request = {
        "schema": "klt.lvs.request/1",
        "layout": {"netlist": layout_spice, "top": args.top},
        "reference": {"netlist": reference_spice, "top": args.top},
        "engine": "klayout",
    }
    request_path = os.path.join(
        args.out_dir,
        "lvs-request-negctl.json" if args.negative_control else "lvs-request.json",
    )
    with open(request_path, "w", encoding="utf-8") as fh:
        json.dump(lvs_request, fh, indent=2)

    proc = _sh(["klt", "lvs", request_path, "--format", "json"])
    if not proc.stdout.strip():
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"klt lvs produced no report (exit {proc.returncode})")
    report = json.loads(proc.stdout)
    report_name = (
        "lvs-report-negctl.json" if args.negative_control else "lvs-report.json"
    )
    with open(os.path.join(args.out_dir, report_name), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    status = report.get("status")
    print(f"klt lvs: status={status} mismatches={len(report.get('mismatches', []))}")
    for entry in report.get("mismatches", [])[:20]:
        print("  ", json.dumps(entry)[:200])
    if args.negative_control:
        if status == "match":
            print(
                "NEGATIVE CONTROL FAILED: a deliberately broken reference still "
                "compared as a match -- the clean result this harness reports is "
                "not evidence of anything"
            )
            return 1
        print("negative control OK: the broken reference is correctly rejected")
        return 0
    return 0 if status == "match" else 1


if __name__ == "__main__":
    raise SystemExit(main())
