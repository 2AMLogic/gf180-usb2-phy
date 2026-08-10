# sim/ — evidence record format

This directory holds simulation testbenches and their results. Results are
**append-only evidence**: once a record is written, it is never edited or
deleted. A re-run — even one that corrects a mistake — mints a new record
with a new ID; a correction references the record it supersedes rather than
overwriting it in place.

This convention exists because `CLAUDE.md` commits this repo to two rules
that need a concrete schema to be enforceable:

- **Verification is the product.** No claim without a testbench. Every
  recorded result carries the full PVT corner matrix fixed in
  [`spec/usb2-device-phy.md`](../spec/usb2-device-phy.md) §8.1 (−40/27/125 °C,
  ±10% supply, the 5-corner gf180mcu process set — 45 points) unless the
  record explicitly states why a subset was used.
- **`sim/` is append-only evidence.** Re-runs get new records; records are
  never edited or deleted.

**This file is the authoritative convention.** The corner runner that
produces records in this format — how to run it, how to write a testbench,
PDK resolution, corner definitions — is documented in
[`sim/harness/README.md`](harness/README.md). If the harness and this
document ever disagree, this document wins and the harness is the thing that
gets fixed.

This harness is ported from the sibling
[`gf180-bandgap`](https://github.com/2AMLogic/gf180-bandgap) repository (same
PDK, so the environment setup and evidence-record convention below apply
directly) per `CLAUDE.md`'s "Harness bootstrap" instruction. What did *not*
port is `gf180-bandgap`'s bandgap-specific spec rows and test content — this
repo's PVT corners and pass/fail bounds come from
`spec/usb2-device-phy.md`, not from the sibling's bandgap spec.

## Directory / naming convention

Each testbench topic gets its own experiment directory:

```
sim/
  <experiment-slug>/                 # e.g. smoke-inverter, driver-rise-fall, pullup-tolerance
    testbench/                       # testbench netlist(s) / xschem export used
    netlist-snapshots/
      <record-id>.spice              # frozen DUT netlist used for this record
    corners/
      <record-id>/
        <corner-id>.log              # raw ngspice output per PVT point
                                      # e.g. ss_-40c_2.97v.log
    records/
      <record-id>.md                 # append-only summary record
```

- **`<experiment-slug>`** — short, descriptive, kebab-case name for what is
  being verified (`smoke-inverter`, and later `driver-rise-fall`,
  `pullup-tolerance`, `receiver-thresholds`, ...). One directory per distinct
  claim being tested, not per run.
- **`<record-id>`** — unique and traceable:
  `<YYYYMMDD>-<HHMMSS>-<short-git-sha>` (e.g. `20260810-153000-1a7ef75`).
  Re-runs simply mint a new `<record-id>`; nothing under `records/` is ever
  edited in place. The same `<record-id>` ties together the netlist snapshot,
  the raw per-corner logs, and the summary record for one run.
- **`<corner-id>`** — `<process>_<temp>c_<supply>`, e.g. `ss_-40c_2.97v.log`,
  `tt_27c_3.30v.log`, `ff_125c_3.63v.log`. The three fields are separated by
  the **last two** underscores, so the process field may itself contain one:

  - **`<process>`** — one or more lowercase alphanumeric tokens joined by
    underscores. For a circuit-level run this is the harness corner name
    (`tt`, `ss`, `ff`, `fs`, `sf`, and the passive-skew corners `res_ff`,
    `bjt_ss`, ...). For a device-level testbench that exercises one device
    family it is the gf180mcu model-section name that testbench selects
    (`typical`, `bjt_typical`, `res_ff`, ...). The vocabulary is deliberately
    **open**: gf180mcu ships a `.lib` section per device family (see
    `sim/harness/corners.py`), so the set grows with the families a testbench
    touches, and pinning it to `tt|ss|ff` would misname most device runs.
  - **`<temp>`** — the junction temperature in °C, signed, suffixed `c`:
    `-40c`, `27c`, `125c`. A record may add intermediate points but never
    fewer than the spec's mandated axis without a stated reason.
  - **`<supply>`** — one of:
    - `<volts>v` — the swept supply, e.g. `2.97v`, `3.30v`, `3.63v`;
    - `<node><volts>v` — when the swept rail is not the main supply and needs
      naming, e.g. `nwell2p97v`. `p` stands in for the decimal point so the
      field stays a single token with no underscore of its own;
    - `nosupply` — the testbench has no supply rail to sweep (a device
      testbench referred to its own source node and driven by an ideal
      source). This is one of the subset justifications the record's **Corner
      matrix run** field is required to spell out.
- **`testbench/`** is not versioned per record — it holds the current
  testbench netlist(s)/xschem export(s) used to generate records. If the
  testbench itself changes in a way that could affect comparability across
  records, note that in the new record's summary (e.g. under Claim or a
  free-text note).

## Summary record format

Each run produces one `records/<record-id>.md` file with the following
fields:

- **Record ID** — the `<record-id>` for this run (matches the filename and
  the corresponding `netlist-snapshots/` / `corners/` subdirectory).
- **Claim** — which spec parameter/line this record substantiates (reference
  the ratified spec, e.g. `spec/usb2-device-phy.md#<anchor>`), or a statement
  that this record is harness self-verification and substantiates no spec
  claim.
- **Netlist provenance** — `schematic` (`design/...`) or `extracted`
  (post-layout, `layout/...`). Required so post-layout re-runs are
  distinguishable from the original schematic-level record.
- **Corner matrix run** — explicit list of (process corner, temperature,
  supply) points actually executed. Must be the full 45-point PVT matrix from
  `spec/usb2-device-phy.md` §8.1 unless the record states why a subset was
  used.
- **Statistical convention** (when applicable, e.g. Monte Carlo mismatch
  analysis) — N samples and sigma level reported. Used for distribution
  claims that are not a per-corner pass/fail (e.g. reporting a spread against
  an untrimmed spec).
- **Result** — per-corner pass/fail, plus an overall pass/fail against the
  ratified spec value.
- **Links** — paths to the testbench file(s), the frozen netlist snapshot,
  and the raw per-corner logs used to produce this record.
- **Timestamp / author** — when the record was created and who (human or
  agent) created it.
- **Supersedes** (optional) — the prior `<record-id>` this record supersedes,
  for corrections or for a post-layout extracted re-run that reports a
  schematic-vs-extracted delta against the schematic-level record.

## Append-only rule

`records/*.md` files are never edited or deleted after creation. A re-run or
a correction always creates a new record with a new `<record-id>`. If it
corrects or replaces a prior result, it references that prior record via
**Supersedes** rather than overwriting it. This applies even to typo fixes —
the append-only guarantee is what makes `sim/` usable as an evidence trail;
"fixing" an existing record in place would defeat that.

## Enforcement

This convention is checked, not merely documented. `sim/check_records.py`
(implementation: `sim/harness/evidence_lint.py`) reads every
`sim/<slug>/records/<record-id>.md` against the format above and fails on:

- a missing or empty one of the nine required fields above;
- a filename that is not a well-formed `<record-id>`, or a **Record ID**
  field that disagrees with its filename;
- a record with no `netlist-snapshots/<record-id>.spice` or no
  `corners/<record-id>/` logs — and, symmetrically, a snapshot or corner
  directory with no summary record to cite it;
- a `<corner-id>.log` name that does not parse under the grammar above;
- a **Supersedes** value that names a `<record-id>` with no record in the
  same experiment directory (write `(none)` when a record supersedes
  nothing);
- **append-only violations**: any file under `records/`,
  `netlist-snapshots/` or `corners/` modified, renamed, or deleted relative
  to the merge base with `origin/main`. Only additions are allowed.

The record-id grammar, the `- **Field**: value` block parser, and the git
merge-base/diff plumbing `evidence_lint.py` uses are shared with
`verification/check_records.py` (see issue #16) rather than duplicated —
only the checks specific to this convention (the corner-id grammar, the
netlist-snapshot/corner-log existence checks, and the
log-count-vs-predecessor check above) live in `sim/harness/evidence_lint.py`
itself. Its own self-test is `sim/harness/test_evidence_lint.py`, run
directly with `python3 sim/harness/test_evidence_lint.py`.

Run it directly:

```bash
python3 sim/check_records.py
python3 sim/check_records.py --require-append-only
```

The append-only half needs real git history; where the base ref does not
resolve (a shallow clone, say) it prints `SKIP` rather than passing silently,
and `--require-append-only` turns that skip into a failure.

If the checker and this document ever disagree, this document wins and the
checker is the thing that gets fixed. The evidence is never the thing that
gets fixed.

## What exists today

`sim/smoke-inverter/` is throwaway harness acceptance infrastructure — a
single minimum-size CMOS inverter built from gf180mcu primitives, proving the
corner runner's PVT plumbing (parameter substitution, `.lib` corner
sections, `.temp`) actually takes effect. It is **not** a PHY sub-block:
`design/` has no schematics yet, so there is no driver or receiver testbench
to write. See [`sim/harness/README.md`](harness/README.md) §"sim/smoke-inverter/"
for what it exercises and how to run it.

Once `design/` has real schematics, each PHY sub-block claim from
`spec/usb2-device-phy.md` (driver rise/fall time, D+ pull-up tolerance,
receiver thresholds, ...) gets its own `sim/<experiment-slug>/` directory
following the layout above.
