# verification/ — evidence record format

**This file is the authoritative convention.** The scripts under
`verification/` (`check_records.py`) implement it; if a script and this
document ever disagree, this document wins and the script is the thing that
gets fixed. This convention is ported, near-verbatim, from
[`sky130-modexp`](https://github.com/2AMLogic/sky130-modexp)'s
`verification/README.md` (the digital half of issue #2's harness bootstrap,
per `CLAUDE.md`) — same record schema, re-targeted from sky130 to gf180mcu.
It in turn adapts the record convention used by the analog canaries
(`2AMLogic/gf180-bandgap`'s `sim/README.md`) for a digital RTL flow: no
ngspice, no PVT corner sweep; the klt `provenance` block (klt version,
resolved PDK, deck/input content hashes) takes the place of a swept-corner
matrix.

This directory holds the cocotb testbench(es) and their results. Results
are **append-only evidence**: once a record is written, it is never edited
or deleted. A re-run — even one that corrects a mistake — mints a new
record with a new ID; a correction references the prior record it
supersedes rather than overwriting it.

This convention exists because `CLAUDE.md` commits this repo to rules that
need a concrete schema to be checkable rather than aspirational:

- **Verification is the product.** No claim without a testbench.
- **`verification/` is append-only evidence.** Re-runs get new records;
  records are never edited or deleted.

## Scope of this harness (read before adding a "real" testbench here)

Everything under `verification/` right now verifies `rtl/harness_counter.v`
— a throwaway smoke-test vehicle with **zero USB semantics**, not any part
of the PHY. Its only job is to prove the cocotb + Icarus + `klt` digital
harness (issue #7, the digital half of #2) elaborates, simulates, and
reports a real result end-to-end. When real PHY digital logic (NRZI
encode/decode, bit stuffing/destuffing, SYNC/EOP handling, per
`spec/usb2-device-phy.md` §2) is implemented, its testbenches belong here
too, following the same convention — but do not extend
`test_harness_counter.py` itself to grow USB semantics; write a new
testbench against the real module instead, per `CLAUDE.md`'s
scope-discipline rule.

## Contents

- `test_harness_counter.py` — cocotb testbench for `rtl/harness_counter.v`,
  covering reset, hold-when-disabled, and a 500-case randomized
  cross-check (with wraparound) against a plain Python model. Driven by
  `klt functional-verification` (see `request-harness-counter.json`).
- `request-harness-counter.json` — `klt functional-verification` request
  driving `test_harness_counter.py` against `harness_counter.v` via Icarus.
- `check_records.py` — the evidence-record linter (see "Enforcement"),
  originally ported unmodified from `sky130-modexp`. It also now houses the
  record-id grammar, `- **Field**: value` block parser, and git
  merge-base/diff plumbing shared with `sim/harness/evidence_lint.py` (see
  issue #16) — that module imports these names directly rather than keeping
  its own copy. This file stays strictly stdlib-only (no local imports) so
  it keeps working when copied standalone, which both `test_check_records.py`
  (below) and `sim/harness/test_evidence_lint.py` do.
- `test_check_records.py` — the linter's own self-test, likewise ported
  unmodified: one executable negative case per violation class named
  below, run against a throwaway fixture repo.
- `records/` — the append-only evidence records this convention produces.

Run the klt-driven functional-verification suite with:

```bash
klt functional-verification verification/request-harness-counter.json --format json
```

Run the record linter (and its self-test) with:

```bash
python3 verification/check_records.py
python3 verification/test_check_records.py
```

### Why no `cross_check.py` / `cross_check_tb.py` here

`sky130-modexp` additionally ships `cross_check.py` / `cross_check_tb.py` —
a deterministic multi-`WIDTH` driver that bypasses `klt` to elaborate
`modexp.v` at several parameter values, because `klt
functional-verification`'s request schema has no field to override a
Verilog `parameter` (see that repo's own README for the friction-protocol
issue this gap is filed under,
[`2AMLogic/klayout-tools#610`](https://github.com/2AMLogic/klayout-tools/issues/610)).
`harness_counter.v` is verified only at its default `WIDTH=8` — this
bootstrap issue does not make a multi-width correctness claim, so porting
that extra driver would be machinery the trivial smoke test does not need
(per issue #7's own guidance: "use judgment on how much of that machinery a
smoke test actually needs"). If a future testbench in this directory does
need a swept-parameter claim, port `cross_check.py`'s pattern then, against
the design that actually requires it.

## Directory / naming convention

Each distinct claim being verified gets its own experiment directory under
`verification/records/`:

```
verification/records/
  <experiment-slug>/                 # e.g. functional-smoke, synthesis-smoke
    records/
      <record-id>.md                 # append-only summary record
    artifacts/
      <record-id>/                   # frozen inputs/outputs for this run
        ...                          # e.g. the raw klt JSON envelope, the
                                      # cocotb results XML, a mapped
                                      # netlist snapshot
```

- **`<experiment-slug>`** — short, descriptive, kebab-case name for the
  claim being verified. This repo currently has two:
  - `functional-smoke` — the cocotb suite passes end-to-end via
    `klt functional-verification` (Icarus, no PDK dependency).
  - `synthesis-smoke` — the same design synthesizes cleanly via
    `klt synthesize` against gf180mcu.
  One directory per distinct claim, not per run. Future entries (e.g.
  `place-and-route`, `drc-lvs`, `gate-level-sim`) follow the same pattern
  once those legs of the maturity ladder are taken up.
- **`<record-id>`** — unique and traceable:
  `<YYYYMMDD>-<HHMMSS>-<short-git-sha>` (e.g. `20260810-205021-c819c95`),
  identical grammar to the analog canaries' convention. Re-runs mint a new
  `<record-id>`; nothing under `records/` or `artifacts/` is ever edited in
  place. `<short-git-sha>` is the design's git revision at the time the
  record was minted (necessarily the parent commit, since the commit that
  adds the record cannot cite its own hash).
- **`artifacts/<record-id>/`** is not a "corner" directory in the analog
  sense (a digital run has no PVT sweep) — it holds whatever raw outputs
  substantiate that specific record: the raw `klt` JSON envelope, the
  cocotb `results_icarus.xml` for a functional-verification record, and a
  mapped-netlist snapshot plus the Yosys script for a synthesis record.

## Record format

Each record is a markdown file, `records/<record-id>.md`, with two parts:

1. A machine-readable `<!-- record-meta ... -->` HTML-comment block
   containing JSON (invisible in a rendered preview, trivially parseable
   with the stdlib `json` module — no YAML dependency). Required keys:

   - `record_id` — must equal the filename stem.
   - `experiment` — the experiment-slug this record belongs to.
   - `supersedes` — `null`, or the `record_id` of a prior record in the
     same experiment directory this one corrects/replaces.
   - `git_revision` — the full design git revision this record was
     produced against.
   - `provenance` — the klt provenance block:
     - `klt_version`
     - `pdk.name` / `pdk.version` — the resolved PDK name/version, or
       `"n/a"` when the run has no PDK dependency (e.g. the Icarus-only
       functional-verification run, which never touches a standard-cell
       library).
     - `deck.content_hash` — the liberty/PDK deck's content hash klt
       reports, or `"n/a"` when not applicable.
     - `inputs` — a non-empty list of `{"path": ..., "content_hash": ...}`
       for every source file this record's claim depends on (at minimum,
       the RTL under test). Hashes use klt's own `"sha256:<hex>"` format.

2. Human-readable prose bullets, each a **required field**:

   - **Record ID** — matches the metadata block and the filename.
   - **Claim** — which spec/doc line this record substantiates.
   - **Design provenance** — `rtl` (`rtl/<file>.v` @ `<git-sha>`) today;
     once post-synthesis/post-P&R records exist, `netlist` (post-synthesis)
     or `layout` (post-P&R, extracted) analogous to the analog convention's
     schematic/extracted distinction.
   - **Run configuration** — the exact tool invocation and settings (engine,
     request file, PDK/corner if applicable, seed, ...).
   - **Statistical convention** — sample size / seed for a randomized claim,
     or `N/A` for a single deterministic run (e.g. one synthesis pass).
   - **Result** — the measured outcome(s) and an overall pass/fail against
     the claim.
   - **klt provenance** — human-readable echo of the metadata block's
     `provenance`, including the informational case where klt did not drive
     the run.
   - **Links** — paths to the driver/testbench script(s), the design under
     test, and the raw artifacts under `artifacts/<record-id>/`.
   - **Timestamp / author** — ISO-8601 UTC timestamp and who (human or
     agent) minted the record.
   - **Supersedes** — `none`, or the prior `<record-id>` this corrects.

## Append-only rule

`records/*.md` and `artifacts/**` are never edited or deleted after
creation. A re-run or correction always mints a new record with a new
`<record-id>`; a correction references the record it supersedes via the
**Supersedes** field rather than overwriting it in place. This applies even
to typo fixes — the append-only guarantee is what makes `verification/`
usable as an evidence trail.

## Provenance staleness (the point of the klt hash block)

A record's `provenance.inputs[].content_hash` pins the exact source content
the claim was measured against. `check_records.py` recomputes those hashes
from the current working tree for every **live** record (a record no other
record's `supersedes` field names) and fails if they no longer match — the
RTL changed since the record was minted, so the record's claim can no
longer be trusted at `HEAD` and a fresh record is required. Superseded
records are exempt from this re-check: they are frozen history describing
what was true at the commit they cite, not a live claim about the current
tree.

## Enforcement

This convention is checked, not merely documented.
`verification/check_records.py` needs nothing but Python 3 and `git`, reads
tracked files only, and fails on:

- a record missing a required field (metadata key or prose bullet), or with
  a placeholder/empty value;
- a filename or metadata `record_id` that is not a well-formed
  `<record-id>`, or the two disagreeing;
- a `supersedes` value naming a record that does not exist in the same
  experiment directory;
- a live record whose `provenance.inputs[].content_hash` no longer matches
  the current working tree (see "Provenance staleness" above);
- **append-only violations**: any file under `verification/records/`
  modified, renamed, or deleted relative to the merge base with
  `origin/main` (`--base-ref` to override, `--require-append-only` to turn
  an unresolvable base ref into a failure instead of a `SKIP`).

`verification/test_check_records.py` holds one executable negative case per
bullet above — plus positive controls that a valid record passes, that
*adding* a record is allowed, and that a superseded record is exempt from
the freshness re-check. Run it directly with
`python3 verification/test_check_records.py`; it builds a throwaway fixture
repo in a temp directory and invokes the real linter as a subprocess, so it
exercises the shipped entry point rather than a stand-in.

If the checker and this document ever disagree, this document wins and the
checker is the thing that gets fixed. The evidence is never the thing that
gets fixed.

## Worked example

The two records under `verification/records/`, both minted for this
bootstrap issue, illustrate the format:

- `verification/records/functional-smoke/records/<record-id>.md` — all 3
  `test_harness_counter.py` cocotb tests pass via
  `klt functional-verification`. `provenance.pdk` is `"n/a"` — an
  Icarus/cocotb-only run has no PDK dependency.
- `verification/records/synthesis-smoke/records/<record-id>.md` —
  `harness_counter.v` synthesizes to 34 gf180mcu standard cells via
  `klt synthesize` against `gf180mcu_fd_sc_mcu9t5v0` / `tt_025C_1v80`.
  `provenance.pdk` names the resolved gf180mcu variant and `deck` carries
  the liberty content hash klt reports.

A future post-synthesis or post-P&R re-run of either claim, or a record for
real PHY digital logic once it exists, would live under its own experiment
directory with its own `<record-id>` following this same convention.
