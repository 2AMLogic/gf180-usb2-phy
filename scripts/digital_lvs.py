#!/usr/bin/env python3
"""Gate-level LVS for the digital PHY: routed GDS vs. the as-built netlist.

What this checks, precisely
---------------------------
`klt place-and-route` writes three coupled artifacts for `rtl/usb_utmi_phy.v`:
a routed DEF, the merged GDS, and the *as-built* gate-level Verilog
(`write_verilog` -- CTS buffers, resizes and antenna diodes included). This
script asks the two questions LVS exists to answer for a standard-cell block:

    does the GDS instantiate exactly the cells the as-built netlist names,
    wired to exactly the same signal nets?
    and does every power/ground pin land on the net it should?

It answers both with one `klt lvs` compare:

* **layout side** -- `klt extract` on the routed GDS with every cell of the
  standard-cell library instantiated for this block (read from
  `flow/request-usb-utmi-phy-par.json`'s own `pdk.cell_library`) held as an
  opaque black box (`--abstract-cells '<library>__*'`), so the comparison is
  at the gate level rather than the transistor level. Physical-only cells
  (`fill_*`, `endcap`, `filltie`) are abstracted like every other cell,
  deliberately with no name filter: `klt lvs` recognizes a power-only master
  structurally and prunes it from the signal compare itself (klayout-tools
  #1622, disclosed as `topology.power_only_pruned`), while the power/ground
  half below still checks it.
* **reference side** -- the as-built Verilog itself, via
  ``"form": "gate-level-verilog"`` (klayout-tools #1336): `klt lvs` reads
  the file as Verilog and converts it to plain-element SPICE internally,
  resolving every cell's pin order from the PDK library's own `.spice` data
  (``"library"``), never from a table maintained here.
* **power/ground half** -- ``"options.power_connectivity"`` with
  ``"expected_nets"`` naming the design's power/ground nets to themselves
  (read from `flow/request-usb-utmi-phy-par.json`'s `power` block, the same
  request that told OpenROAD's `global_connect` how to wire them). That
  upgrades the default cross-instance consistency check to an absolute
  verdict: a design wired *uniformly* wrong fails, not just one wired
  inconsistently. The plain-element SPICE references earlier records used
  could not ask this question at all (`power_connectivity.status` reads
  `"unchecked"` for that form -- the check is honored only for
  `gate-level-verilog`).

What this does NOT check: transistor-level equivalence of the standard cells
themselves (they are black boxes here -- the foundry's own characterized GDS
is taken as correct), rail/grid continuity in the physical sense (whether
the VDD rail is geometrically unbroken, IR drop -- `klt power` /
`klt ring-check`'s questions, which need routed geometry this compare no
longer sees), and anything analog. See `layout/README.md`.

Why the reference is a byte-identical copy of the as-built Verilog: the
compare's request document, and so the `klt lvs` envelope itself, echoes the
paths exactly as the request gave them. Copying the Verilog to
`<out-dir>/<top>_reference.v` keeps those echoed paths relative to the run's
own working directory (and so to the frozen artifacts committed beside the
envelope), instead of naming a worktree-absolute scratch path that only
re-hashes to `true` on the machine that produced it -- the
path-portability defect PR #81's review caught on this record's predecessor.

History: klayout-tools#1419 ("no supported path from place-and-route output
to an LVS verdict on the block it implemented") was filed from here per
`CLAUDE.md`'s friction protocol, and closed 2026-08-26 as #1336's
`gate-level-verilog` form. The hand-rolled SPICE transcription of the
as-built Verilog this script used to ship (`write_reference` /
`parse_verilog`-driven, pin order read back from the extracted layout) -- and
the four flow-level workarounds it carried -- is deleted with this form in
place. The port-parsing half of `parse_verilog` stays for the one thing the
tool leaves to the caller: `klt extract --pins` needs the module's
top-level port list, and there is no request-side counterpart (the
`gate-level-verilog` conversion reads the Verilog itself). The negative
control re-parses the raw Verilog text on its own -- it rewrites net
references *as written*, escaped identifiers and all, which the un-escaped
view `parse_verilog` returns cannot express.

Usage
-----
    PDK=gf180mcuD python3 scripts/digital_lvs.py

Runs against the committed signoff pair in `layout/digital/`
(`usb_utmi_phy.gds` + `usb_utmi_phy_routed.v`) by default; `--gds`/`--verilog`
point it at a fresh `flow/.klt/place-and-route/` run instead. Writes its
artifacts to `layout/digital/lvs/` (gitignored scratch -- the frozen copies
live under `verification/records/digital-lvs/`) and prints the `klt lvs`
verdict. Exit status is 0 only on a **full** pass: `status: "match"` *and*
`power_connectivity.status: "match"` with every declared expected net
exercised.

    PDK=gf180mcuD python3 scripts/digital_lvs.py --negative-control

re-runs the same compare against a deliberately broken reference and requires
it to fail, which is what makes the clean result above mean something.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    # therefore recovers `line_state[0]`, not `LineState[0]` -- so the port has
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
    identifiers*: `\u_destuffer/ones` -- a backslash, then everything up to
    the terminating whitespace. A bit-select of one is written `\u_destuffer/ones
    [2]`, i.e. escaped identifier, terminator space, then the index. The DEF
    (and so `klt extract --def-net-names`) knows that net as
    `u_destuffer/ones[2]`, so both the leading backslash and the terminator
    space have to come back out before the two sides can be compared.
    """
    name = name.strip()
    if name.startswith("\\"):
        name = name[1:]
    return re.sub(r"\s+(?=\[)", "", name)


def break_one_connection(src_path: str, dst_path: str, cell_library: str) -> str:
    """Copy ``src_path`` to ``dst_path`` rewiring exactly one connection.

    The deliberately broken reference for `--negative-control`: the first
    standard-cell instance's first non-constant connection is re-pointed at
    a *different* declared net of the same module. Both nets still exist by
    the Verilog's own declarations (the break must survive `klt lvs`'s
    Verilog parsing, not work around it), but the reference now describes
    connectivity the layout does not implement: the abandoned net loses a
    terminal and the target net gains one, so a *passing* compare can be
    told apart from a compare that never looked -- `klt lvs` must report
    this as a mismatch; if it still says "match", the harness is not
    testing anything and the clean result is worthless.

    Replaces the SPICE-transcription break this script's predecessor used
    (rewiring `write_reference()`'s first instance -- gone with that
    function). Returns a one-line description of what was rewired.
    """
    text = open(src_path, encoding="utf-8").read()
    inst_re = re.compile(
        rf"\b({re.escape(cell_library)}__\w+)\s+(\S+)\s*\(([^;]*?)\)\s*;", re.S
    )
    match = inst_re.search(text)
    if match is None:
        raise SystemExit(
            "negative control found no standard-cell instance to break"
        )
    cell, inst, body = match.group(1), match.group(2), match.group(3)

    def is_constant(net_text: str) -> bool:
        return re.match(r"^1'[bdh]", net_text, re.I) is not None

    named = [
        (pin, net)
        for pin, net in re.findall(r"\.(\w+)\s*\(([^)]*?)\)", body)
        if not is_constant(net)
    ]
    if not named:
        raise SystemExit(
            f"negative control found no named connection on instance '{inst}'"
        )
    pin, net_a = named[0]
    # A visible, net-text-distinct rewiring target: another net of the same
    # instance first, any declared net of any later instance otherwise.
    net_b = next((n for _, n in named[1:] if n != net_a), None)
    if net_b is None:
        for _c, _i, later_body in inst_re.findall(text):
            for _p, n in re.findall(r"\.(\w+)\s*\(([^)]*?)\)", later_body):
                if not is_constant(n) and n != net_a:
                    net_b = n
                    break
            if net_b is not None:
                break
    if net_b is None or net_b == net_a:
        raise SystemExit(
            "negative control found no second net to rewire the first "
            "connection to -- cannot build a deliberately broken reference"
        )

    old = f".{pin}({net_a})"
    new = f".{pin}({net_b})"
    broken_body, count = body.replace(old, new, 1), 1
    if old not in body:
        pattern = rf"{re.escape(f'.{pin}')}\s*\(\s*{re.escape(net_a)}\s*\)"
        broken_body, count = re.subn(pattern, new, body, count=1)
    if count != 1:
        raise SystemExit(
            f"negative control failed to rewrite '.{pin}({net_a})' on "
            f"instance '{inst}'"
        )
    with open(dst_path, "w", encoding="utf-8") as fh:
        fh.write(text[: match.start(3)] + broken_body + text[match.end(3) :])
    return f"{cell} {inst}: .{pin}({net_a}) -> .{pin}({net_b})"


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
            "report it; exits 0 only when the compare correctly fails"
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
    cell_library = (par_req.get("pdk") or {}).get("cell_library")
    if not cell_library:
        raise SystemExit(
            f"{args.par_request} names no pdk.cell_library -- the standard-cell "
            "library to abstract and compare against cannot be derived"
        )

    ports, _instances = parse_verilog(verilog)
    print(
        f"as-built netlist: {len(_instances)} instances, "
        f"{len(ports)} top-level ports (after assign-alias resolution)"
    )

    lef_dir = None
    pdk_root = os.environ.get("PDK_ROOT")
    if pdk_root:
        for root, _dirs, files in os.walk(pdk_root):
            if f"{cell_library}.lef" in files:
                lef_dir = os.path.join(root, f"{cell_library}.lef")
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
        "--abstract-cells",
        f"{cell_library}__*",
        "-o",
        layout_spice,
        "--format",
        "json",
    ]
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
        f"{len(extract_report['abstracted_cells'])} abstracted cell types "
        f"(wildcard {cell_library}__*, fill/tap included -- klt lvs prunes "
        "the power-only ones itself)"
    )

    # The reference the compare names: a byte-identical copy of the as-built
    # Verilog (clean run) or the one-connection-broken scratch copy
    # (negative control). Copying rather than pointing at the repo path
    # keeps the request document -- and so the envelope -- naming its
    # reference relative to the run's own working directory, the
    # portability shape PR #81's review put on record.
    suffix = "_reference_negctl" if args.negative_control else "_reference"
    reference_netlist = os.path.join(args.out_dir, f"{args.top}{suffix}.v")
    if args.negative_control:
        breakage = break_one_connection(verilog, reference_netlist, cell_library)
        print(f"negative control: rewired {breakage}")
    else:
        shutil.copyfile(verilog, reference_netlist)

    lvs_request = {
        "schema": "klt.lvs.request/1",
        "layout": {"netlist": layout_spice, "top": args.top},
        "reference": {
            "netlist": reference_netlist,
            "top": args.top,
            "form": "gate-level-verilog",
            "library": cell_library,
        },
        "engine": "klayout",
        "options": {
            "power_connectivity": {
                "expected_nets": {power_net: power_net, ground_net: ground_net},
            },
        },
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
    power = report.get("power_connectivity") or {}
    power_status = power.get("status")
    print(
        f"klt lvs: status={status} mismatches={len(report.get('mismatches', []))}"
    )
    print(f"power_connectivity: status={power_status}")
    if power_status == "unchecked":
        print(f"  reason: {power.get('reason')}")
    else:
        print(
            f"  pins: {power.get('power_pins')} "
            f"(derivation {power.get('power_pins_derivation')})"
        )
        for finding in power.get("findings", [])[:5]:
            print("  ", json.dumps(finding)[:240])
    for entry in report.get("mismatches", [])[:20]:
        print("  ", json.dumps(entry)[:240])

    if args.negative_control:
        if status == "match" and power_status == "match":
            print(
                "NEGATIVE CONTROL FAILED: a deliberately broken reference still "
                "compared clean on both the signal and the power/ground half "
                "-- the results this harness reports are not evidence of anything"
            )
            return 1
        print("negative control OK: the broken reference is correctly rejected")
        return 0

    unchecked = power.get("unchecked_expected_pins", [])
    passed = status == "match" and power_status == "match" and not unchecked
    if unchecked:
        print(
            f"declared expected_nets never exercised by this run: {unchecked} "
            "(see docs/cli/lvs.md -- a signoff-grade check wants this empty)"
        )
    if passed:
        print(
            "full gate-level LVS pass: signal compare matched and every "
            "power/ground pin reached its expected net"
        )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
