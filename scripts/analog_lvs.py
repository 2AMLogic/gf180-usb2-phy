#!/usr/bin/env python3
"""Transistor-level LVS for the analog blocks: committed GDS vs. schematic netlist.

What this checks, precisely
---------------------------
Each committed analog stream under `layout/analog/*.gds` is compared against
the schematic export of the same block, `design/netlist/<block>.spice`. Unlike
the digital half (`scripts/digital_lvs.py`, a *gate-level* compare that holds
standard cells as black boxes), this is a **transistor-level** compare: every
MOSFET and resistor the deck recognises in the geometry has to pair with a
device of the same class in the schematic, wired to the same nets.

The compare uses the request shape the 2026-10-09 analog record established:

* **layout side** -- the GDS itself, extracted *inline* by `klt lvs` with the
  `gf180mcu` deck (``layout: {file, deck, top}``). The pre-extracted form
  (``layout: {netlist}``) does not work for this reference form -- see
  `--also-preextracted` below and that record's step 5.
* **reference side** -- a byte-identical copy of `design/netlist/<block>.spice`
  with ``"form": "subckt-call"``: the gf180mcu PDK netlists instantiate
  devices as subcircuit calls (`XMN_B1 ... nfet_03v3`), which `klt lvs`
  converts to plain elements internally.
* no LVS options are set. In particular nothing is relaxed: no
  `parameter_tolerance`, no `compare_parameters` override, no flattening.
  A mismatch is a result to record, not something to tune away
  (`CLAUDE.md`, "Verification is the product").

Where the layout-side netlist comes from
----------------------------------------
The request sets ``options.keep_extracted: true``, so `klt lvs` writes **the
netlist the compare itself built** to ``<request_dir>/.klt/lvs/<top>.spice``
and names it in ``environment.extracted_netlist``. This script copies it out
to ``<block>_layout.spice`` and freezes that: it is the exact layout side of
the verdict, not a second extraction that might differ from it.

(`keep_extracted` is a *request option*, not a CLI flag -- `klt lvs --help`
does not list it, which is easy to misread as the capability being absent.
It is not: it works on the pinned klt 0.9.0, and `environment.extracted_netlist`
is null only when a request leaves it off.)

A separate `klt extract` runs too, for one thing the compare does not emit: a
structured per-device JSON report (device classes and counts, per-device
parameters and nets). That is evidence only -- **the verdict always comes from
the `klt lvs` run**. Its netlist is also written out, so the two can be
compared; they agree except in how the poly resistor is carded (`klt lvs`
writes an `R` card, `klt extract` an `X` card), which the record states.

Cause analysis
--------------
With five blocks (up to 78 devices each) a by-hand reading of every
`device.unmatched` is not replayable. `--analyze` (on by default) therefore
writes `<block>-cause.json` beside each report: the port names each side
declares, how many layout nets carry no name label, and the body/bulk net of
every device per class on each side. Those three facts are read directly off
the two netlists -- they are measurements, not inferences -- and they are what
the record cites. See `verification/records/analog-lvs/`.

Usage
-----
    PDK=gf180mcuD python3 scripts/analog_lvs.py

Discovers every `layout/analog/*.gds` (rather than hard-coding block names),
requires a matching `design/netlist/<block>.spice` for each, and writes its
artifacts to `layout/analog/lvs/` (gitignored scratch -- the frozen copies
live under `verification/records/analog-lvs/`).

**Exit status is 0 only when every block reports `status: "match"`.** Any
mismatch, any missing reference netlist, and any tool failure is non-zero.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECK = "gf180mcu"
#: `klt extract` names a net it found no label for `$<n>`, which the SPICE
#: writer escapes as `\$<n>`. Such a net exists in the geometry but has no
#: name of its own, so it can never correspond to a reference net by name.
ANON_NET_RE = re.compile(r"^\\?\$\d+$")


def _is_number(token: str) -> bool:
    """True for a bare SPICE numeric value (`200000`, `1.5e3`, `2.2`)."""
    try:
        float(token)
    except ValueError:
        return False
    return True


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

    #339 may merge the two single-ended receivers and #252-style work may add
    streams; both are picked up by this glob with no edit here.
    """
    return sorted(
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(gds_dir, "*.gds"))
    )


def lvs_request(block: str) -> dict:
    """The `klt lvs` request for one block.

    Every path is a bare filename: the run's cwd is the out-dir, so the
    report echoes relative paths and stays replayable from whatever directory
    the frozen artifacts are copied into (the portability shape PR #81's
    review put on record for the digital harness).
    """
    return {
        "schema": "klt.lvs.request/1",
        "layout": {"file": f"{block}.gds", "deck": DECK, "top": block},
        "reference": {
            "netlist": f"{block}_reference.spice",
            "top": block,
            "form": "subckt-call",
        },
        # The only option set, and it is output-side: it makes `klt lvs` write
        # the netlist it extracted, and cannot change a verdict. Nothing here
        # relaxes the compare.
        "options": {"keep_extracted": True},
    }


def parse_spice_subckt(path: str, top: str) -> tuple[list[str], list[dict]]:
    """Return (port names, devices) for subcircuit ``top`` of a SPICE netlist.

    Handles the three card forms this harness meets:

    * the schematic export's subcircuit calls --
      `XMN_B1 BUF1 AMPOUT VSS VSS nfet_03v3 L=... W=...`;
    * `klt`'s extracted MOSFETs as `M` cards --
      `M$1 \\$7 AMPOUT \\$1 vsubs nfet L=0.28U ...`;
    * an `R` card -- `R$11 IBIASN VDD vsubs 200000 ppolyf_u_1k` -- which is how
      `klt lvs --keep_extracted` writes the poly resistor (`klt extract` writes
      the same device as an `X` card). Its resistance sits *between* the nets
      and the model, so it is cut off by value rather than by position.

    In every form a four-terminal MOS card is `name d g s b model`, so the body
    terminal is the fourth net -- which is what the cause analysis needs.
    """
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    # Join SPICE continuation lines ("+" in column 1) before tokenising.
    text = re.sub(r"\n\+\s*", " ", text)

    ports: list[str] = []
    devices: list[dict] = []
    in_top = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("*"):
            continue
        low = line.lower()
        if low.startswith(".subckt"):
            tok = line.split()
            if len(tok) >= 2 and tok[1] == top:
                in_top, ports = True, tok[2:]
            continue
        if low.startswith(".ends"):
            in_top = False
            continue
        if not in_top or line.startswith("."):
            continue
        tok = line.split()
        if not tok:
            continue
        kind = tok[0][0].upper()
        if kind not in ("M", "X", "R"):
            continue
        rest = tok[1:]
        # Everything from the first `k=v` token on is parameters, not nets.
        cut = next((i for i, t in enumerate(rest) if "=" in t), len(rest))
        head = rest[:cut]
        model: str | None = None
        if kind == "R":
            # `R<name> n1 n2 [n3] <value> [model]`: the bare numeric value ends
            # the net list. Positional, because an R card has 2 or 3 terminals.
            value_at = next((i for i, t in enumerate(head) if _is_number(t)), None)
            if value_at is not None:
                nets = head[:value_at]
                model = head[value_at + 1] if len(head) > value_at + 1 else None
            else:
                nets = head[:-1] if len(head) >= 2 else head
                model = head[-1] if len(head) >= 2 else None
        else:
            # `M`/`X`: the model is the last token before any parameters.
            nets = head[:-1] if len(head) >= 2 else head
            model = head[-1] if len(head) >= 2 else None
        devices.append(
            {"name": tok[0], "card": kind, "model": model, "nets": nets}
        )
    return ports, devices


def classify(model: str | None) -> str:
    """Coarse MOS class, so layout (`nfet`) and reference (`nfet_03v3`) pair.

    Only the two MOS families are classified. Everything else -- notably the
    `ppolyf_u_1k` poly resistor, whose name also begins with "p" -- is
    "other" and takes no part in the bulk-net comparison, which is a
    four-terminal MOS question.
    """
    m = (model or "").lower()
    if "pfet" in m:
        return "pfet"
    if "nfet" in m:
        return "nfet"
    return "other"


def analyze_cause(block: str, layout_spice: str, reference_spice: str) -> dict:
    """Measure the three facts that explain this family of mismatch.

    All three are read directly off the two netlists; none is inferred from
    the `klt lvs` report's own prose:

    1. **port sets** -- which top-level pins each side declares. LVS seeds its
       search from corresponding pins; sets that do not overlap leave it
       nothing to start from.
    2. **unnamed layout nets** -- nets `klt extract` found no name label for.
       A net with no name cannot correspond to a reference net by name.
    3. **body/bulk nets per device class** -- the fourth terminal of every MOS
       card on each side. A layout whose bulk terminals land on the
       deck-synthesized substrate net or on an anonymous well, where the
       schematic names VSS/VDD, differs from the schematic on every device.
    """
    lay_ports, lay_devs = parse_spice_subckt(layout_spice, block)
    ref_ports, ref_devs = parse_spice_subckt(reference_spice, block)

    lay_nets = sorted({n for d in lay_devs for n in d["nets"]})
    unnamed = sorted(n for n in lay_nets if ANON_NET_RE.match(n))

    def bulk_nets(devs: list[dict]) -> dict[str, list[str]]:
        out: dict[str, set[str]] = {}
        for d in devs:
            cls = classify(d["model"])
            if cls == "other" or len(d["nets"]) < 4:
                continue
            out.setdefault(cls, set()).add(d["nets"][3])
        return {k: sorted(v) for k, v in sorted(out.items())}

    return {
        "block": block,
        "ports": {
            "layout": lay_ports,
            "reference": ref_ports,
            "only_in_layout": sorted(set(lay_ports) - set(ref_ports)),
            "only_in_reference": sorted(set(ref_ports) - set(lay_ports)),
            "common": sorted(set(lay_ports) & set(ref_ports)),
        },
        "layout_nets": {
            "total": len(lay_nets),
            "unnamed_count": len(unnamed),
            "unnamed": unnamed,
            "named": sorted(n for n in lay_nets if not ANON_NET_RE.match(n)),
        },
        "bulk_nets": {
            "layout": bulk_nets(lay_devs),
            "reference": bulk_nets(ref_devs),
        },
        "device_counts": {
            "layout": len(lay_devs),
            "reference": len(ref_devs),
        },
    }


def run_block(block: str, gds_src: str, ref_src: str, out_dir: str, *,
              analyze: bool, also_preextracted: bool) -> dict:
    """Extract, compare, and (optionally) analyse one block. Returns a summary."""
    work = os.path.join(out_dir, block)
    os.makedirs(work, exist_ok=True)

    # Byte copies, so the frozen artifacts are self-contained and the request
    # names its inputs by bare filename.
    gds = os.path.join(work, f"{block}.gds")
    ref = os.path.join(work, f"{block}_reference.spice")
    shutil.copyfile(gds_src, gds)
    shutil.copyfile(ref_src, ref)

    summary: dict = {
        "block": block,
        "gds_sha256": sha256(gds),
        "reference_sha256": sha256(ref),
    }

    # --- evidence leg: the structured per-device report the compare does not
    #     emit. Its netlist is kept only to cross-check the compare's own.
    extract_spice = f"{block}_extract.spice"
    proc = sh(
        ["klt", "extract", f"{block}.gds", "--deck", DECK, "--top", block,
         "-o", extract_spice, "--format", "json"],
        cwd=work,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        sys.stderr.write(proc.stdout + proc.stderr)
        raise SystemExit(f"{block}: klt extract failed (exit {proc.returncode})")
    extract_report = json.loads(proc.stdout)
    with open(os.path.join(work, f"{block}-extract-report.json"), "w",
              encoding="utf-8") as fh:
        json.dump(extract_report, fh, indent=2)
    summary["extract"] = {
        "note": "evidence only; the verdict comes from the klt lvs run",
        "status": extract_report.get("status"),
        "devices": extract_report.get("device_count"),
        "nets": extract_report.get("net_count"),
        "pins": extract_report.get("pin_count"),
        "netlist_sha256": extract_report.get("netlist_sha256"),
    }

    # --- verdict leg: inline-extraction compare
    request_path = os.path.join(work, f"{block}-lvs-request.json")
    with open(request_path, "w", encoding="utf-8") as fh:
        json.dump(lvs_request(block), fh, indent=2)
    proc = sh(["klt", "lvs", f"{block}-lvs-request.json", "--format", "json"],
              cwd=work)
    if not proc.stdout.strip():
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"{block}: klt lvs produced no report (exit {proc.returncode})")
    report = json.loads(proc.stdout)
    with open(os.path.join(work, f"{block}-lvs-report.json"), "w",
              encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    counts = report.get("counts") or {}
    summary["lvs"] = {
        "status": report.get("status"),
        "exit_code": proc.returncode,
        "error_count": report.get("error_count"),
        "category_error_counts": report.get("category_error_counts") or {},
        "category_counts": report.get("category_counts") or {},
        "counts": counts,
        "body_verification": (report.get("body_verification") or {}).get("status"),
        "power_connectivity": (report.get("power_connectivity") or {}).get("status"),
    }

    # The layout side of the verdict, written by the compare itself
    # (options.keep_extracted). This -- not the klt extract output above -- is
    # what the record freezes and what the cause analysis reads.
    layout_spice = f"{block}_layout.spice"
    emitted = (report.get("environment") or {}).get("extracted_netlist")
    if not emitted or not os.path.exists(emitted):
        raise SystemExit(
            f"{block}: klt lvs did not emit an extracted netlist "
            f"(environment.extracted_netlist={emitted!r}) -- "
            "options.keep_extracted was expected to produce one"
        )
    shutil.copyfile(emitted, os.path.join(work, layout_spice))
    summary["layout_netlist_sha256"] = sha256(os.path.join(work, layout_spice))
    # Cross-check: the compare's netlist and the standalone extraction should
    # describe the same circuit. Any difference is recorded, never hidden.
    with open(os.path.join(work, layout_spice), encoding="utf-8") as fh:
        a = [ln for ln in fh.read().splitlines() if not ln.startswith("*")]
    with open(os.path.join(work, extract_spice), encoding="utf-8") as fh:
        b = [ln for ln in fh.read().splitlines() if not ln.startswith("*")]
    summary["netlist_cross_check"] = {
        "identical_ignoring_comments": a == b,
        "differing_lines": [x for x in a if x not in b],
    }

    if also_preextracted:
        # The 2026-10-09 record found this form cannot work for a
        # `subckt-call` reference. Re-measured rather than assumed; both
        # results are recorded, neither is picked over the other.
        pre_req = {
            "schema": "klt.lvs.request/1",
            "layout": {"netlist": extract_spice, "top": block},
            "reference": {"netlist": f"{block}_reference.spice", "top": block,
                          "form": "subckt-call"},
        }
        with open(os.path.join(work, f"{block}-lvs-request-preextracted.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(pre_req, fh, indent=2)
        proc_pre = sh(
            ["klt", "lvs", f"{block}-lvs-request-preextracted.json",
             "--format", "json"], cwd=work)
        if proc_pre.stdout.strip():
            pre_report = json.loads(proc_pre.stdout)
            with open(os.path.join(work, f"{block}-lvs-report-preextracted.json"),
                      "w", encoding="utf-8") as fh:
                json.dump(pre_report, fh, indent=2)
            pre_counts = pre_report.get("counts") or {}
            summary["lvs_preextracted"] = {
                "status": pre_report.get("status"),
                "exit_code": proc_pre.returncode,
                "error_count": pre_report.get("error_count"),
                "counts": pre_counts,
            }

    if analyze:
        cause = analyze_cause(block, os.path.join(work, layout_spice), ref)
        with open(os.path.join(work, f"{block}-cause.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(cause, fh, indent=2)
        summary["cause"] = {
            "ports_only_in_layout": cause["ports"]["only_in_layout"],
            "ports_only_in_reference": cause["ports"]["only_in_reference"],
            "unnamed_layout_nets": cause["layout_nets"]["unnamed_count"],
            "layout_bulk_nets": cause["bulk_nets"]["layout"],
            "reference_bulk_nets": cause["bulk_nets"]["reference"],
        }
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gds-dir", default=os.path.join(REPO_ROOT, "layout", "analog"),
                    help="directory of committed streams (default: layout/analog)")
    ap.add_argument("--netlist-dir",
                    default=os.path.join(REPO_ROOT, "design", "netlist"),
                    help="directory of schematic netlists (default: design/netlist)")
    ap.add_argument("--out-dir",
                    default=os.path.join(REPO_ROOT, "layout", "analog", "lvs"),
                    help="scratch out-dir (gitignored; default: layout/analog/lvs)")
    ap.add_argument("--blocks", nargs="*", default=None,
                    help="limit to these blocks (default: every committed stream)")
    ap.add_argument("--no-analyze", dest="analyze", action="store_false",
                    help="skip the per-block cause analysis (<block>-cause.json)")
    ap.add_argument("--also-preextracted", action="store_true",
                    help=("additionally run the pre-extracted layout form and "
                          "record its result beside the verdict (diagnostic)"))
    ap.add_argument("--format", choices=("text", "json"), default="text")
    args = ap.parse_args()

    blocks = discover_blocks(args.gds_dir)
    if not blocks:
        raise SystemExit(f"no *.gds found under {args.gds_dir}")
    if args.blocks:
        unknown = sorted(set(args.blocks) - set(blocks))
        if unknown:
            raise SystemExit(
                f"no committed stream for: {', '.join(unknown)} "
                f"(have: {', '.join(blocks)})"
            )
        blocks = [b for b in blocks if b in args.blocks]

    # A block whose reference netlist is missing fails loudly, before any
    # tool runs -- never silently skipped.
    missing = [b for b in blocks
               if not os.path.exists(os.path.join(args.netlist_dir, f"{b}.spice"))]
    if missing:
        raise SystemExit(
            "missing reference netlist for: "
            + ", ".join(f"{b} ({args.netlist_dir}/{b}.spice)" for b in missing)
        )

    os.makedirs(args.out_dir, exist_ok=True)
    summaries = []
    for block in blocks:
        summaries.append(run_block(
            block,
            os.path.join(args.gds_dir, f"{block}.gds"),
            os.path.join(args.netlist_dir, f"{block}.spice"),
            args.out_dir,
            analyze=args.analyze,
            also_preextracted=args.also_preextracted,
        ))

    matched = [s for s in summaries if s["lvs"]["status"] == "match"]
    all_match = len(matched) == len(summaries)

    if args.format == "json":
        json.dump({"blocks": summaries,
                   "matched": len(matched),
                   "total": len(summaries),
                   "status": "match" if all_match else "mismatch"},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        for s in summaries:
            lvs = s["lvs"]
            c = lvs["counts"]
            nets, devs, pins = c.get("nets", {}), c.get("devices", {}), c.get("pins", {})
            print(f"{s['block']}: {lvs['status']} "
                  f"(errors {lvs['error_count']}; "
                  f"devices {devs.get('layout')}/{devs.get('reference')}/"
                  f"{devs.get('matched')}; "
                  f"nets {nets.get('layout')}/{nets.get('reference')}/"
                  f"{nets.get('matched')}; "
                  f"pins {pins.get('layout')}/{pins.get('reference')})")
            if lvs["category_error_counts"]:
                print(f"    error categories: {lvs['category_error_counts']}")
            if "cause" in s:
                cause = s["cause"]
                print(f"    ports only in layout: {cause['ports_only_in_layout']}")
                print(f"    ports only in reference: {cause['ports_only_in_reference']}")
                print(f"    unnamed layout nets: {cause['unnamed_layout_nets']}")
                print(f"    bulk nets layout: {cause['layout_bulk_nets']}")
                print(f"    bulk nets reference: {cause['reference_bulk_nets']}")
        print(f"\n{len(matched)}/{len(summaries)} blocks match")

    if not all_match:
        print("analog LVS does NOT match -- this is a recorded result, "
              "not a harness failure", file=sys.stderr)
    return 0 if all_match else 1


if __name__ == "__main__":
    raise SystemExit(main())
