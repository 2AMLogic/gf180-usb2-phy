#!/usr/bin/env python3
"""Audited inventories behind T1 items 1, 2.digital, 9 and 10.

`klt signoff` (>= 0.7.0) accepts a `kind: generic` envelope for these items
when it is bound to an audited artifact: the envelope declares
`"t1_item": <n>`, names the artifact in `provenance.input.path`, and the
manifest pins the same `content_hash`. That binding proves the artifact's
*bytes* are fresh. It proves nothing about whether the artifact is *true*, or
whether a file the inventory is about has moved underneath it.

So the artifacts bound here (except the routed GDS of 2.digital, which is
bound directly) are inventories that carry the sha256 of every member file,
and this module is both their only writer and their verifier:

* `build_*` derives an inventory from the tree and **raises** when the audit
  fails (a schematic with no derived netlist, a cocotb test no request runs, a
  sim/ directory nobody classified, ...). `--regen` therefore cannot write a
  `pass` envelope over a claim the tree does not support.
* `verify_item` rebuilds the same inventory from the live tree and compares it
  with the committed one, member by member, so a changed, deleted or newly
  added file fails with its name -- even though the inventory's own bytes did
  not change.

Pure stdlib; no klt, PDK, xschem, yosys, OpenROAD or ngspice. Nothing here
runs a simulation, a synthesis or a P&R flow; `sim/` and `verification/` are
only read. Gates that need a PDK or xschem (`design/netlist.py --check`, the
P&R flow) are named in the inventories and are NOT re-run here -- each
envelope's `summary` says so.

Pattern: 2AMLogic/gf180-temp-por `signoff/` (PR #361).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CI_WORKFLOW = ".github/workflows/ci.yml"
PACKAGE_JSON = "package.json"
SPEC = "spec/usb2-device-phy.md"
ENV_DOC = "docs/environment-setup.md"
SETUP_ENV = "scripts/setup-env.sh"
HARNESS_README = "sim/harness/README.md"
GDS_TOP = "layout/digital/usb_utmi_phy.gds"
ROUTED_NETLIST = "layout/digital/usb_utmi_phy_routed.v"
SYNTH_REQUEST = "flow/request-usb-utmi-phy-synth.json"
PAR_REQUEST = "flow/request-usb-utmi-phy-par.json"

# manifest key -> T1 item number
ITEM_NUMBER = {"1.analog": 1, "1.digital": 1, "2.digital": 2, "9": 9, "10": 10}
ITEM_ARTIFACTS = {
    "1.analog": "signoff/evidence/inventory-design-sources-analog.json",
    "1.digital": "signoff/evidence/inventory-design-sources-digital.json",
    "2.digital": GDS_TOP,
    "9": "signoff/evidence/inventory-testbenches.json",
    "10": "signoff/evidence/inventory-repo-hygiene.json",
}
ITEM_ENVELOPES = {
    "1.analog": "signoff/evidence/t1-item-1-analog-design-sources.json",
    "1.digital": "signoff/evidence/t1-item-1-digital-design-sources.json",
    "2.digital": "signoff/evidence/t1-item-2-digital-layout.json",
    "9": "signoff/evidence/t1-item-9-testbenches.json",
    "10": "signoff/evidence/t1-item-10-repo-hygiene.json",
}
ITEM_TITLES = {
    "1.analog": "Design sources (analog partition)",
    "1.digital": "Design sources (digital partition)",
    "2.digital": "Layout (digital partition)",
    "9": "Testbenches shipped",
    "10": "Repo hygiene",
}

# `sim/` directories that ship no `testbench*/` directory of their own. Each
# must be classified; a new one is unclassified and fails the audit.
NO_TESTBENCH_DIRS = {
    "harness": "shared corner-runner support code, not an experiment",
    "tests": "harness unit tests, not an experiment",
    "diff-receiver-mc": "Monte Carlo request builder (build_requests.py) for the fleet; ships no testbench of its own, reuses sim/diff-receiver-sensitivity/",
    "se-receiver-mc": "Monte Carlo request builder (build_requests.py) for the fleet; ships no testbench of its own, reuses the single-ended receiver deck",
}

# Commands a reader needs to reproduce a record from a cold checkout, each
# with the committed file that documents it. The audit requires the text to be
# present in that file, so the inventory cannot name a command nobody wrote down.
COLD_START = [
    ("./scripts/setup-env.sh", ENV_DOC),
    ("npm run check:ci", ENV_DOC),
    ("python3 sim/run_corners.py --check-env", HARNESS_README),
    ("python3 sim/run_corners.py <experiment>", HARNESS_README),
    ("bash sim/selftest.sh", HARNESS_README),
]
# Experiments that substantiate no spec row; every other experiment must be
# indexed by sim/spec-coverage.md, and every experiment that index names must
# ship a committed testbench.
NO_SPEC_ROW = {"smoke-inverter": "harness smoke test, claims no spec number",
    "driver-disabled-leakage": "engineering data; spec/usb2-device-phy.md has no numeric leakage row (tb.json: no limit adopted)",
}
SPEC_COVERAGE = "sim/spec-coverage.md"

# verification/test_*.py files that are plain unit tests, not cocotb testbenches.
NOT_COCOTB = {"test_check_records": "unit test of verification/check_records.py (run by `npm run lint`)",
    "test_check_statistical_na": "unit test of verification/check_statistical_na.py (run by `npm run lint`)",
}

_COLD_START_NEEDLE = {"<experiment>": "smoke-inverter"}

HYGIENE_FILES = ["README.md", "LICENSE", SPEC, ENV_DOC, CI_WORKFLOW, PACKAGE_JSON]

_NOT_RERUN = (
    "Gates that need xschem, the gf180mcu PDK, yosys or OpenROAD are not run "
    "by signoff/check.py or by the PDK-free CI job; they are named in the "
    "inventory, not claimed as having run."
)


class AuditError(Exception):
    """The tree does not support the claim an inventory would make."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def dump_json(data: dict) -> str:
    return json.dumps(data, indent=2) + "\n"


def _member(root: Path, rel: str) -> dict:
    path = root / rel
    if not path.is_file():
        raise AuditError(f"{rel}: listed in an inventory but missing")
    return {"path": rel, "sha256": sha256_file(path)}


def _members(root: Path, rels) -> list[dict]:
    return [_member(root, rel) for rel in sorted(set(rels))]


def _glob(root: Path, pattern: str) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.glob(pattern) if p.is_file())


def _read(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text()
    except OSError as exc:
        raise AuditError(f"{rel}: unreadable ({exc})") from exc


def _read_json(root: Path, rel: str) -> dict:
    try:
        return json.loads(_read(root, rel))
    except ValueError as exc:
        raise AuditError(f"{rel}: not valid JSON ({exc})") from exc


def _norm(base: str, rel: str) -> str:
    """`rel` (relative to directory `base`) as a repo-relative POSIX path."""
    parts: list[str] = []
    for part in (Path(base) / rel).parts:
        if part == "..":
            if not parts:
                raise AuditError(f"{rel}: escapes the repository")
            parts.pop()
        elif part != ".":
            parts.append(part)
    return "/".join(parts)


def build_analog_design_inventory(root: Path = REPO_ROOT) -> dict:
    schematics = _glob(root, "design/*.sch")
    netlists = _glob(root, "design/netlist/*.spice")
    if not schematics:
        raise AuditError("design/*.sch: no schematics found")
    sch_cells = {Path(p).stem for p in schematics}
    net_cells = {Path(p).stem for p in netlists}
    if sch_cells != net_cells:
        raise AuditError(
            "design/ schematics and design/netlist/ netlists disagree: "
            f"schematic only {sorted(sch_cells - net_cells)}, "
            f"netlist only {sorted(net_cells - sch_cells)}"
        )
    gate = "python3 design/netlist.py --check"
    if '"--check"' not in _read(root, "design/netlist.py"):
        raise AuditError("design/netlist.py has no --check mode; the gate named is not real")
    return {
        "inventory": "design-sources-analog",
        "t1_item": 1,
        "partition": "analog",
        "regeneration_gate": {
            "command": gate,
            "runs_in": "locally only (needs xschem via `klt netlist` and the PDK); "
            "it is not run by CI or re-run by signoff/check.py",
        },
        "schematics": _members(root, schematics),
        "netlists": _members(root, netlists),
        "regeneration_inputs": _members(root, ["design/netlist.py", "design/xschemrc"]),
    }


def build_digital_design_inventory(root: Path = REPO_ROOT) -> dict:
    rtl = _glob(root, "rtl/*.v")
    vendored = _glob(root, "rtl/common/*.v")
    if not rtl or not vendored:
        raise AuditError("rtl/*.v or rtl/common/*.v: no sources found")
    synth = _read_json(root, SYNTH_REQUEST)
    listed = {_norm("flow", s) for s in synth.get("sources", [])}
    missing = sorted(p for p in listed if not (root / p).is_file())
    if missing:
        raise AuditError(f"{SYNTH_REQUEST} names sources that do not exist: {missing}")
    outside = sorted(listed - set(rtl) - set(vendored))
    if outside:
        raise AuditError(f"{SYNTH_REQUEST} names sources outside rtl/: {outside}")
    top = synth.get("hdl_toplevel")
    if not re.search(rf"^\s*module\s+{re.escape(str(top))}\b", _read(root, f"rtl/{top}.v"), re.M):
        raise AuditError(f"rtl/{top}.v does not declare module {top}")
    return {
        "inventory": "design-sources-digital",
        "t1_item": 1,
        "partition": "digital",
        "toplevel": top,
        "synthesis_request": {
            "file": _member(root, SYNTH_REQUEST),
            "sources_in_request": sorted(listed),
            "runs_in": "locally only (needs yosys and the PDK); not re-run here",
        },
        "rtl": _members(root, rtl),
        "rtl_vendored": _members(root, vendored + ["reuse.lock.json"]),
        "gate_level_netlist": _members(root, [ROUTED_NETLIST]),
    }


def _pins(root: Path) -> dict:
    ci = _read(root, CI_WORKFLOW)
    # a released `klayout-tools==X` or a git revision `klayout-tools @ git+...@<40-hex>`
    klt = re.search(r'"klayout-tools(?:==([0-9][0-9A-Za-z.+!-]*)| @ git\+[^"@]+@([0-9a-f]{40}))"', ci)
    cocotb = re.search(r'"cocotb==([0-9][0-9A-Za-z.]*)"', ci)
    if not klt or not cocotb:
        raise AuditError(f"{CI_WORKFLOW}: no pinned `klayout-tools` (==X or git revision) / `cocotb==X` install")
    klt_pin = klt.group(1) or klt.group(2)
    setup = _read(root, SETUP_ENV)
    rev = re.search(r'KLT_REV="([0-9a-f]{40})"', setup)
    if not rev:
        raise AuditError(f"{SETUP_ENV}: no KLT_REV pin")
    if f'COCOTB_PIN="{cocotb.group(1)}"' not in setup:
        raise AuditError(f"{SETUP_ENV} does not pin the same cocotb as {CI_WORKFLOW}")
    volare = re.search(r'VOLARE_GF180MCU_VERSION="([0-9a-f]{40})"', setup)
    if not volare:
        raise AuditError(f"{SETUP_ENV}: no VOLARE_GF180MCU_VERSION pin")
    if volare.group(1) not in _read(root, ENV_DOC):
        raise AuditError(f"{ENV_DOC} does not record the PDK pin {volare.group(1)}")
    env_doc = _read(root, ENV_DOC)
    if klt_pin not in env_doc or rev.group(1) not in env_doc:
        raise AuditError(f"{ENV_DOC} does not record both klt pins ({klt_pin}, {rev.group(1)[:8]})")
    return {
        "klayout_tools_ci_and_grader": klt_pin,
        "klayout_tools_setup_env_revision": rev.group(1),
        "cocotb": cocotb.group(1),
        "gf180mcu_open_pdks": volare.group(1),
    }


def _experiments(root: Path) -> tuple[dict, dict]:
    experiments: dict[str, dict] = {}
    without: dict[str, str] = {}
    for sim_dir in sorted(p for p in (root / "sim").iterdir() if p.is_dir()):
        slug = sim_dir.name
        if slug.startswith((".", "__")):
            continue
        tb_dirs = [d for d in ("testbench", "testbench-postlayout") if (sim_dir / d).is_dir()]
        if not tb_dirs:
            if slug not in NO_TESTBENCH_DIRS:
                raise AuditError(
                    f"sim/{slug}/ ships no testbench*/ files and is not classified in "
                    "NO_TESTBENCH_DIRS"
                )
            without[slug] = NO_TESTBENCH_DIRS[slug]
            continue
        files = [
            f"sim/{slug}/{d}/{f.relative_to(sim_dir / d).as_posix()}"
            for d in tb_dirs
            for f in (sim_dir / d).rglob("*")
            if f.is_file() and "__pycache__" not in f.parts
        ]
        # analysis scripts / READMEs that sit beside (not inside) testbench*/;
        # corners/, records/ and netlist-snapshots/ are evidence, not testbench.
        files += [
            f"sim/{slug}/{f.name}"
            for f in sim_dir.iterdir()
            if f.is_file() and f.suffix in {".py", ".md", ".sh"}
        ]
        experiments[slug] = {"testbench_dirs": tb_dirs, "files": _members(root, files)}
    return experiments, without


def _cocotb_test_files(root: Path) -> list[str]:
    return [p for p in _glob(root, "verification/test_*.py") if Path(p).stem not in NOT_COCOTB]


def _cocotb_requests(root: Path) -> dict:
    """verification/request-*.json -> the cocotb module and sources each runs."""
    requests = {}
    tests = {Path(p).stem for p in _cocotb_test_files(root)}
    run_by_request: set[str] = set()
    for rel in _glob(root, "verification/request-*.json"):
        req = _read_json(root, rel)
        module = (req.get("testbench") or {}).get("module")
        if module not in tests:
            raise AuditError(f"{rel}: testbench module {module!r} has no verification/{module}.py")
        run_by_request.add(module)
        gate_level = [
            s for s in req.get("sources", []) if s.startswith(".pdk-models")
        ]
        for src in req.get("sources", []):
            if src.startswith(".pdk-models"):
                continue  # fetched with the PDK, not committed
            repo_rel = _norm("verification", src)
            if not (root / repo_rel).is_file():
                raise AuditError(f"{rel}: source {src!r} does not exist")
        requests[rel] = {
            "module": module,
            "toplevel": req.get("hdl_toplevel"),
            "level": "gate" if gate_level else "rtl",
        }
    orphans = sorted(tests - run_by_request)
    if orphans:
        raise AuditError(f"cocotb tests no verification/request-*.json runs: {orphans}")
    return requests


def build_testbench_inventory(root: Path = REPO_ROOT) -> dict:
    experiments, without = _experiments(root)
    if not experiments:
        raise AuditError("sim/: no experiment ships a testbench")
    requests = _cocotb_requests(root)
    named = set(re.findall(r"sim/([a-z0-9-]+)/", _read(root, SPEC_COVERAGE)))
    claimed_without_bench = sorted(named - set(experiments))
    if claimed_without_bench:
        raise AuditError(
            f"{SPEC_COVERAGE} cites measurements from sim/ experiments that ship no "
            f"committed testbench: {claimed_without_bench}"
        )
    unindexed = sorted(set(experiments) - named - set(NO_SPEC_ROW))
    if unindexed:
        raise AuditError(f"sim/ experiments absent from {SPEC_COVERAGE}: {unindexed}")

    package = _read(root, PACKAGE_JSON)
    for rel, info in requests.items():
        if info["level"] == "rtl" and rel not in package:
            raise AuditError(f"{rel} is an RTL request but package.json's `test` never runs it")

    cold_start = []
    for command, source in COLD_START:
        needle = command
        for placeholder, value in _COLD_START_NEEDLE.items():
            needle = needle.replace(placeholder, value)
        if needle not in _read(root, source):
            raise AuditError(f"{source} does not document {needle!r}")
        cold_start.append({"command": command, "documented_in": source})

    try:
        variant = json.loads(_read(root, "sim/pdk.json"))["variant"]
    except (ValueError, KeyError) as exc:
        raise AuditError(f"sim/pdk.json: no readable variant ({exc})") from exc

    support = (
        ["sim/pdk.json", "sim/env.sh", "sim/run_corners.py", "sim/selftest.sh", "sim/spec-coverage.md"]
        + _glob(root, "sim/harness/*.py")
        + [HARNESS_README]
        + _glob(root, "sim/tests/*.py")
    )
    return {
        "inventory": "testbenches",
        "t1_item": 9,
        "pins": {
            **_pins(root),
            "gf180mcu_variant": variant,
            "pinned_in": [CI_WORKFLOW, SETUP_ENV, ENV_DOC, "sim/pdk.json"],
        },
        "cold_start": cold_start,
        "cocotb_requests": requests,
        "cocotb_tests": _members(root, _cocotb_test_files(root)),
        "cocotb_support": _members(
            root,
            _glob(root, "verification/request-*.json")
            + _glob(root, "verification/tb_*.v")
            + [f"verification/{name}.py" for name in sorted(NOT_COCOTB)]
            + [
                "verification/cocotb_helpers.py",
                "verification/usb_bit_model.py",
                "verification/rx_sync_candidate_summary.py",
            ],
        ),
        "analog_experiments": experiments,
        "sim_support": _members(root, support),
        "dirs_without_testbench": without,
    }


def build_hygiene_inventory(root: Path = REPO_ROOT) -> dict:
    if "Apache License" not in _read(root, "LICENSE"):
        raise AuditError("LICENSE: not the Apache-2.0 text the README declares")
    readme = _read(root, "README.md")
    for needle in ("spec/usb2-device-phy.md", "## Repo layout", "## License", "[LICENSE](LICENSE)"):
        if needle not in readme:
            raise AuditError(f"README.md: no {needle!r} (spec link / layout / license)")
    if not re.search(r"^## ", _read(root, SPEC), re.M):
        raise AuditError(f"{SPEC}: no sections")
    if "npm run check:ci" not in _read(root, CI_WORKFLOW):
        raise AuditError(f"{CI_WORKFLOW}: does not run `npm run check:ci`")
    check_ci = re.search(r'"check:ci":\s*"([^"]*)"', _read(root, PACKAGE_JSON))
    if not check_ci or "signoff/check.py" not in check_ci.group(1):
        raise AuditError(f"{PACKAGE_JSON}: check:ci does not run signoff/check.py")
    if "npm run check:ci" not in _read(root, ENV_DOC):
        raise AuditError(f"{ENV_DOC}: does not document how to reproduce (`npm run check:ci`)")
    return {
        "inventory": "repo-hygiene",
        "t1_item": 10,
        "assertions": [
            "LICENSE contains the Apache License text and README.md links it",
            "README.md links the ratified spec and has a repo-layout and a License section",
            f"{SPEC} is present with sections",
            f"{CI_WORKFLOW} runs `npm run check:ci`, and package.json's check:ci runs "
            "signoff/check.py (the inventory drift check)",
            f"{ENV_DOC} documents the reproduction commands",
        ],
        "files": _members(root, HYGIENE_FILES),
    }


INVENTORY_BUILDERS = {
    "1.analog": build_analog_design_inventory,
    "1.digital": build_digital_design_inventory,
    "9": build_testbench_inventory,
    "10": build_hygiene_inventory,
}


def _layout_summary(root: Path) -> str:
    if not (root / GDS_TOP).is_file():
        raise AuditError(f"{GDS_TOP} is missing")
    for rel in (PAR_REQUEST, "layout/digital/usb_utmi_phy.def", ROUTED_NETLIST):
        if not (root / rel).is_file():
            raise AuditError(f"{rel} is missing")
    return (
        f"Routed layout of the digital partition: {GDS_TOP}, bound by hash (the same GDS "
        "the item 3.digital DRC and item 11.digital supply-ERC citations were run on). "
        f"Its committed P&R flow is {PAR_REQUEST} (klt place-and-route; the pinned grader "
        "binds a single input path, so the flow request is named here and is not itself "
        "hash-bound; the item 11.digital place-and-route citation records the run). "
        "This asserts the routed layout artifact exists and is the one the committed DRC "
        "and ERC reports describe. " + _NOT_RERUN + " It does not assert area, timing or "
        "any analog layout (item 2.analog stays unmet: no analog GDS exists)."
    )


def build_envelope(root: Path, key: str) -> dict:
    """The generic envelope for `key`, derived from the bound artifact on disk."""
    artifact = ITEM_ARTIFACTS[key]
    if key == "2.digital":
        summary = _layout_summary(root)
    else:
        inv = json.loads(_read(root, artifact))
        if key == "1.analog":
            what = (
                f"{len(inv['schematics'])} xschem schematics and {len(inv['netlists'])} "
                f"derived netlists, regeneration gate {inv['regeneration_gate']['command']!r} "
                "(needs xschem and the PDK; not run in CI)"
            )
        elif key == "1.digital":
            what = (
                f"{len(inv['rtl'])} RTL sources, {len(inv['rtl_vendored'])} vendored files "
                "under rtl/common/, the synthesis request and the routed gate-level netlist "
                "item 4.digital LVS compares against (synthesis needs yosys and the PDK; not "
                "run in CI)"
            )
        elif key == "9":
            what = (
                f"{len(inv['cocotb_tests'])} cocotb tests mapped to "
                f"{len(inv['cocotb_requests'])} klt functional-verification requests, "
                f"{len(inv['analog_experiments'])} analog sim/ experiments with their "
                "testbench files, the cold-start invocations and the klt/cocotb/PDK pins "
                "(the analog benches need ngspice and the PDK; not run in CI)"
            )
        else:
            what = ", ".join(m["path"] for m in inv["files"]) + " with the stated assertions"
        summary = (
            f"Audited inventory for T1 item {ITEM_NUMBER[key]} ({ITEM_TITLES[key]}): {what}. "
            "Every member file is listed with its sha256 and signoff/check.py re-derives the "
            "inventory from the live tree, so the bound hash proves the inventory is current "
            "and the member hashes prove the files it describes are. It does not run a "
            "simulation, a synthesis or a flow, and re-derives no measured value. " + _NOT_RERUN
        )
    return {
        "schema_version": 1,
        "kind": "generic",
        "t1_item": ITEM_NUMBER[key],
        "status": "pass",
        "summary": summary,
        "source": artifact,
        "provenance": {
            "klt_version": None,
            "klayout_version": None,
            "pdk": None,
            "deck": None,
            "input": {
                "path": {"path": artifact, "scope": "repo"},
                "content_hash": sha256_file(root / artifact),
            },
        },
    }


def write_all(root: Path = REPO_ROOT) -> dict[str, str]:
    """Rebuild every inventory and envelope; returns {key: pinned content_hash}."""
    # Build everything before writing anything, so a failed audit leaves the
    # previous (honest) files untouched.
    inventories = {key: builder(root) for key, builder in INVENTORY_BUILDERS.items()}
    _layout_summary(root)
    (root / "signoff" / "evidence").mkdir(parents=True, exist_ok=True)
    for key, inventory in inventories.items():
        (root / ITEM_ARTIFACTS[key]).write_text(dump_json(inventory))
    pins = {}
    for key in ITEM_ENVELOPES:
        envelope = build_envelope(root, key)
        (root / ITEM_ENVELOPES[key]).write_text(dump_json(envelope))
        pins[key] = envelope["provenance"]["input"]["content_hash"]
    return pins


def _member_map(node) -> tuple[dict[str, str], object]:
    """Flatten {path,sha256} members to {path: hash}; return the rest."""
    members: dict[str, str] = {}

    def walk(value):
        if isinstance(value, dict):
            if set(value) == {"path", "sha256"}:
                members[value["path"]] = value["sha256"]
                return "<member>"
            return {k: walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v) for v in value]
        return value

    return members, walk(node)


def diff_inventory(committed: dict, rebuilt: dict) -> list[str]:
    old, old_rest = _member_map(committed)
    new, new_rest = _member_map(rebuilt)
    problems = []
    for path in sorted(old.keys() | new.keys()):
        if path not in new:
            problems.append(f"{path}: listed in the inventory but no longer in the tree")
        elif path not in old:
            problems.append(f"{path}: in the tree but absent from the inventory")
        elif old[path] != new[path]:
            problems.append(f"{path}: changed since it was inventoried")
    if not problems and old_rest != new_rest:
        problems.append("inventory metadata (requests, pins, commands) differs from the tree")
    return problems


def verify_item(root: Path, key: str, manifest: dict) -> list[str]:
    """Every reason item `key`'s citation no longer describes the tree."""
    entry = (manifest.get("evidence") or {}).get(key)
    if not isinstance(entry, dict) or not entry.get("file") or not entry.get("content_hash"):
        return [f"manifest item {key}: needs one {{file, content_hash}} citation"]
    problems: list[str] = []
    envelope_rel = ITEM_ENVELOPES[key]
    if entry["file"] != envelope_rel:
        problems.append(f"manifest item {key}: cites {entry['file']!r}, expected {envelope_rel!r}")
    try:
        committed_env = json.loads(_read(root, envelope_rel))
    except (AuditError, ValueError) as exc:
        return problems + [f"{envelope_rel}: unreadable ({exc})"]

    artifact = ITEM_ARTIFACTS[key]
    if not (root / artifact).is_file():
        return problems + [f"{artifact}: bound artifact is missing"]
    actual = sha256_file(root / artifact)
    if entry["content_hash"] != actual:
        problems.append(
            f"manifest item {key}: pins {entry['content_hash']} but {artifact} hashes to {actual}"
        )
    if committed_env.get("kind") != "generic":
        problems.append(f"{envelope_rel}: kind must be 'generic'")
    item = ITEM_NUMBER[key]
    if committed_env.get("t1_item") != item or isinstance(committed_env.get("t1_item"), bool):
        problems.append(f"{envelope_rel}: t1_item is {committed_env.get('t1_item')!r}, expected {item}")
    prov_input = (committed_env.get("provenance") or {}).get("input") or {}
    if committed_env.get("source") != artifact or prov_input.get("path") != {
        "path": artifact,
        "scope": "repo",
    }:
        problems.append(
            f"{envelope_rel}: `source` and provenance.input.path must both name {artifact} "
            "(repo scope), so the grader and check.py read the same artifact"
        )
    if prov_input.get("content_hash") != actual:
        problems.append(f"{envelope_rel}: provenance.input.content_hash is stale vs {artifact}")

    builder = INVENTORY_BUILDERS.get(key)
    try:
        if builder is not None:
            rebuilt = builder(root)
            committed = json.loads(_read(root, artifact))
            problems += [f"{artifact}: {p}" for p in diff_inventory(committed, rebuilt)]
        expected_env = build_envelope(root, key)
    except (AuditError, ValueError) as exc:
        return problems + [f"item {key}: audit failed: {exc}"]
    if not problems and committed_env != expected_env:
        problems.append(
            f"{envelope_rel}: differs from the envelope derived from the tree "
            "(summary or provenance edited by hand)"
        )
    return problems
