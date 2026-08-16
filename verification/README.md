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

`test_harness_counter.py` verifies `rtl/harness_counter.v` — a throwaway
smoke-test vehicle with **zero USB semantics**, not any part of the PHY.
Its only job is to prove the cocotb + Icarus + `klt` digital harness
(issue #7, the digital half of #2) elaborates, simulates, and reports a
real result end-to-end. Everything else here verifies real PHY digital
logic: the bit-level codec of `spec/usb2-device-phy.md` §2 (NRZI
encode/decode, bit stuffing/destuffing). SYNC/EOP handling and
`LineState[1:0]` decode are still to come and their testbenches belong
here too, following the same convention.

Do not extend `test_harness_counter.py` itself to grow USB semantics, and
do not extend a bit-level codec testbench to grow framing or
serial-interface-engine semantics: write a new testbench against the real
module instead, per `CLAUDE.md`'s scope-discipline rule.

## Contents

### Bit-level codec (`spec/usb2-device-phy.md` §2)

- `usb_bit_model.py` — the golden Python reference models (NRZI
  encode/decode, bit stuff/destuff) the four codec testbenches below check
  the RTL against, bit for bit. Written straight from the prose rules in
  spec §2 and deliberately sharing no structure with the RTL (no clocks, no
  valid strobes, no pipeline latency): a model shaped like the
  implementation cannot catch the implementation's mistakes. Pure stdlib,
  no cocotb import, so it is readable and importable outside a simulator.
- `test_usb_nrzi_encoder.py` / `request-usb-nrzi-encoder.json` — cocotb
  testbench for `rtl/usb_nrzi_encoder.v`: reset-to-J, all-1s (a static
  line), all-0s (a transition every bit), a 512-bit randomized bit-exact
  cross-check against the model plus an NRZI round trip, `data_valid` gaps,
  and `init`.
- `test_usb_nrzi_decoder.py` / `request-usb-nrzi-decoder.json` — cocotb
  testbench for `rtl/usb_nrzi_decoder.v`: a line with no transitions at all
  (the idle/hold case, which correctly decodes to 1s), a transition every
  bit, a 512-bit randomized round trip, `line_valid` gaps (including
  wiggling the line during the gap to prove the transition reference is not
  disturbed), and `init`.
- `test_usb_bit_stuffer.py` / `request-usb-bit-stuffer.json` — cocotb
  testbench for `rtl/usb_bit_stuffer.v`: all-0s (never stuffs), all-1s
  (maximal stuffing density, and never more than six 1s emitted in a row),
  the positional insertion before a data 0, the "stream ends on exactly six
  1s" boundary, a 512-bit 1-biased randomized cross-check, the `in_ready`
  backpressure contract (one stall per inserted bit, never two clocks in a
  row), run-count survival across a gap, and `init`.
- `test_usb_bit_destuffer.py` / `request-usb-bit-destuffer.json` — cocotb
  testbench for `rtl/usb_bit_destuffer.v`: all-0s, stuffed-bit removal,
  **stuff-error injection** (seven consecutive 1s → a one-clock `stuff_err`
  pulse, re-flagged at every subsequent stuff position in a long 1 run), a
  512-bit 1-biased randomized round trip, run-count survival across a gap,
  and `init`.
- `tb_usb_bit_codec_loopback.v` — **testbench scaffolding, not PHY RTL**
  (which is why it lives here and not in `rtl/`): a structural harness
  wiring the whole TX path (stuffer → NRZI encoder) into the whole RX path
  (NRZI decoder → destuffer), so one Icarus elaboration can carry an
  RTL-to-RTL round-trip claim rather than an RTL-against-model one. It is
  explicitly *not* the top-level digital wrapper — no SYNC, no EOP, no
  line-state decode, no UTMI ports.
- `test_usb_bit_codec_loopback.py` / `request-usb-bit-codec-loopback.json`
  — cocotb testbench for that harness: a 512-bit 1-biased random stream,
  all-1s (which also checks the line never holds the same state for more
  than seven bit times — the entire point of bit stuffing), all-0s, and a
  second stream after `init`.

### Harness smoke test

- `test_harness_counter.py` — cocotb testbench for `rtl/harness_counter.v`,
  covering reset, hold-when-disabled, and a 500-case randomized
  cross-check (with wraparound) against a plain Python model. Driven by
  `klt functional-verification` (see `request-harness-counter.json`).
- `request-harness-counter.json` — `klt functional-verification` request
  driving `test_harness_counter.py` against `harness_counter.v` via Icarus.

### Evidence-record tooling

- `check_records.py` — the evidence-record linter (see "Enforcement"),
  originally ported unmodified from `sky130-modexp`. It also now houses the
  record-id grammar, `- **Field**: value` block parser, and git
  merge-base/diff plumbing shared with `sim/harness/evidence_lint.py` (see
  issue #16) — that module imports these names directly rather than keeping
  its own copy. This file stays strictly stdlib-only (no local imports) so
  it keeps working when copied standalone, which both `test_check_records.py`
  (below) and `sim/tests/test_evidence_lint.py` do.
- `test_check_records.py` — the linter's own self-test, likewise ported
  unmodified: one executable negative case per violation class named
  below, run against a throwaway fixture repo.
- `records/` — the append-only evidence records this convention produces.

Run every klt-driven functional-verification suite in this directory with:

```bash
npm run test
```

`package.json`'s `test` script chains one `klt functional-verification`
invocation per request file, and each of them is runnable on its own:

```bash
klt functional-verification verification/request-harness-counter.json --format json
klt functional-verification verification/request-usb-nrzi-encoder.json --format json
klt functional-verification verification/request-usb-nrzi-decoder.json --format json
klt functional-verification verification/request-usb-bit-stuffer.json --format json
klt functional-verification verification/request-usb-bit-destuffer.json --format json
klt functional-verification verification/request-usb-bit-codec-loopback.json --format json
```

A request needs one invocation each because `klt
functional-verification`'s request schema names a single `hdl_toplevel` —
there is no way to elaborate several independent top-levels in one run.
Adding a new module means adding a request file *and* extending the `test`
script, or CI will not exercise it.

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
  claim being verified. This repo currently has three:
  - `functional-smoke` — the harness-counter cocotb suite passes end-to-end
    via `klt functional-verification` (Icarus, no PDK dependency). A
    harness claim, not a PHY claim.
  - `synthesis-smoke` — the same design synthesizes cleanly via
    `klt synthesize` against gf180mcu.
  - `bit-codec-functional` — the real one: `spec/usb2-device-phy.md` §11's
    digital signoff line, for the bit-level half of §2 (NRZI
    encode/decode, bit stuffing/destuffing).
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

The records under `verification/records/` illustrate the format:

- `verification/records/functional-smoke/records/<record-id>.md` — all 3
  `test_harness_counter.py` cocotb tests pass via
  `klt functional-verification`. `provenance.pdk` is `"n/a"` — an
  Icarus/cocotb-only run has no PDK dependency.
- `verification/records/synthesis-smoke/records/<record-id>.md` —
  `harness_counter.v` synthesizes to 34 gf180mcu standard cells via
  `klt synthesize` against `gf180mcu_fd_sc_mcu9t5v0` / `tt_025C_1v80`.
  `provenance.pdk` names the resolved gf180mcu variant and `deck` carries
  the liberty content hash klt reports.
- `verification/records/bit-codec-functional/records/<record-id>.md` — the
  first record substantiating a real spec claim rather than a harness one:
  32 cocotb tests across five `klt functional-verification` invocations,
  bit-exact against `usb_bit_model.py`, covering the bit-level half of spec
  §2. Two things about it are worth copying:
  - **One record, five runs.** The convention is one experiment directory
    per distinct *claim*, not per invocation. The claim here is a single
    spec line, so the five envelopes are five artifacts under one
    `<record-id>`, and `provenance.inputs` lists the union of every source
    the claim depends on.
  - **The claim states what it does *not* cover.** Spec §2 also has
    SYNC/EOP and `LineState[1:0]` clauses; that logic does not exist yet,
    so the record says so explicitly rather than letting "verified against
    §2" imply more than was measured.

A future post-synthesis or post-P&R re-run of any of these claims, or a
record for the rest of the PHY digital logic once it exists, would live
under its own experiment directory with its own `<record-id>` following
this same convention.
