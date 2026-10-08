"""Diagnostic-only rewrite of the record's klt-extracted SPEF.

NOT signoff evidence. It exists to measure what record
20261008-200000-8139bb6's SPEF parasitics would do to timing if OpenSTA
could attach them (PR #104 annotation review), as an independent check on
the --def-pins re-extraction record 20261008-195826-74ccfac cites.

What that SPEF does (klt extract at the repo pin, run without --def-pins):
  * every DEF-named net is listed in *PORTS and gets a `*P <net>` *CONN
    entry, although only the DEF's PINS are real top-level ports;
  * each such net's RC network hangs off a node written as the bare net
    name (`_013_`) instead of an internal node (`_013_:1`). OpenSTA reads
    a bare name as a port pin, finds no such port (STA-1656 "pin ... not
    found"), drops every CAP/RES element touching it, and the net ends up
    with zero wire capacitance (see probe logs, `report_net _013_`).

Rewrite (mechanical, value-preserving): for every SPEF net that is a DEF
NETS entry but not a DEF PINS entry, (1) drop it from *PORTS and drop its `*P` line,
(2) rename the bare-name node to `<net>:1` wherever it appears in a
*CAP or *RES element (including coupling references from other nets).
No R or C value is changed, added or removed.

Usage: python3 -I repair_spef_hub_nodes.py <in.spef> <def> <out.spef>
"""
import re
import sys


def def_section_names(def_path, section):
    """Names declared in a DEF section (PINS or NETS)."""
    names, inside = set(), False
    for line in open(def_path):
        if line.startswith(section + " "):
            inside = True
            continue
        if line.startswith("END " + section):
            break
        if inside:
            m = re.match(r"\s*-\s+(\S+)", line)
            if m:
                names.add(m.group(1))
    return names


def unescape(name):
    return name.replace("\\", "")


def main(src, def_path, dst):
    ports = def_section_names(def_path, "PINS")
    def_nets = def_section_names(def_path, "NETS")
    lines = open(src).read().split("\n")
    # Pass 1: SPEF nets that are DEF (signal) NETS and not DEF PINS.
    # Anonymous `$N` nets and names the DEF does not declare (the seven
    # `ZN` nets on the floating clkload outputs) are left untouched.
    named = set()
    for line in lines:
        if line.startswith("*D_NET "):
            name = unescape(line.split()[1])
            if name in def_nets and name not in ports:
                named.add(name)

    def fix(tok):
        if ":" in tok:
            return tok
        return tok + ":1" if unescape(tok) in named else tok

    out, section, renamed, dropped = [], None, 0, 0
    for line in lines:
        if line.startswith("*PORTS"):
            section = "PORTS"
        elif line.startswith("*D_NET"):
            section = None
        elif line in ("*CONN", "*CAP", "*RES", "*END"):
            section = line[1:]
        parts = line.split()
        if section == "PORTS" and parts and not line.startswith("*"):
            if unescape(parts[0]) in named:
                dropped += 1
                continue
        if section == "CONN" and line.startswith("*P ") and unescape(parts[1]) in named:
            dropped += 1
            continue
        if section in ("CAP", "RES") and parts and parts[0].isdigit():
            nodes = parts[1:-1]
            new = [fix(t) for t in nodes]
            renamed += sum(a != b for a, b in zip(nodes, new))
            line = " ".join([parts[0], *new, parts[-1]])
        out.append(line)
    open(dst, "w").write("\n".join(out))
    print(f"ports_in_def={len(ports)} named_nonport_nets={len(named)} "
          f"node_tokens_renamed={renamed} port_or_conn_lines_dropped={dropped}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
