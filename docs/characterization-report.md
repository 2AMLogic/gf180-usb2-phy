# Characterization report (T1 checklist item 8)

This is the aggregated artifact required by
[`klayout-tools/docs/design-evidence-tiers.md`](https://github.com/2AMLogic/klayout-tools/blob/main/docs/design-evidence-tiers.md)'s
T1 checklist, item 8 ("Characterization report" — "one aggregated, current
artifact summarizing per-spec-row performance across conditions, with the
evidence record each verdict rests on"). It is a **pre-silicon** artifact —
schematic-level PVT-corner simulation, not measured hardware — and is
distinct from `measurements/`, which this repo reserves for post-tape-out
silicon characterization (empty until tape-out; see `README.md`'s "Repo
layout").

It aggregates rather than replaces [`sim/spec-coverage.md`](../sim/spec-coverage.md),
which remains the authoritative row-by-row index from each §8.2 spec row to
its evidence record and the detailed engineering discussion of every
failure. This document adds the provenance/staleness envelope T1 item 8
asks for and states, once, why this repo did not produce it via `klt
signoff`.

## Why this is hand-assembled, not `klt signoff` output

Per issue #27's implementation guidance, `klt signoff`'s current interface
(`klayout-tools` v0.2.0, verified 2026-08-18) was checked against this
repo's evidence layout before writing this report by hand. Neither of its
two aggregation modes fits:

**1. Envelope-aggregation mode (`klt signoff <files>`)** requires each
input to be a JSON envelope matching one of `klt drc`/`klt lvs`/`klt
extract`/`klt sim`/`klt yield`/`klt pex`'s own output shapes
(`klayout_tools/signoff.py`'s `_classify()` recognizes exactly those six).
This repo's `sim/` evidence is produced by the ngspice PVT-corner harness
ported from `gf180-bandgap` (`sim/harness/`, documented in
`sim/README.md`) — a repo-owned tool, not `klt sim` — and its records are
Markdown, not JSON. Pointing `klt signoff` directly at a record fails
immediately:

```
$ klt signoff sim/driver-signal-quality/records/20260817-203552-a408cb6.md
klt signoff: envelope file 'sim/driver-signal-quality/records/20260817-203552-a408cb6.md' is not valid JSON: Expecting value: line 1 column 1 (char 0)
```

**2. Manifest tier-verdict mode (`klt signoff --manifest`)** renders the
full T1–T4 item skeleton mechanically parsed from `klayout-tools`'
`docs/design-evidence-tiers.md` and grades each item's cited evidence —
but every item (including item 8 itself) is graded by the *same* six-kind
`_classify()` check as mode 1: an item is `"met"` only when its evidence
resolves to a passing `drc`/`lvs`/`extract`/`sim`/`yield`/`pex` envelope.
There is no seventh "characterization report" kind, and the doc's own item
8 text — unlike items 3, 4, 6, and 7 — names no `klt`-verb-shaped
machine-checkable evidence for it. That is: even where this mode is
reachable, it has no way to validate item 8's own artifact — it can only
grade *other* items against `klt`'s native JSON outputs. (Reachability
itself is also environment-dependent: this mode reads
`docs/design-evidence-tiers.md` relative to the `klayout-tools` package's
own install location, so it needs a `klayout-tools` checkout with that doc
present alongside the installed package, which a bare `pip`/`uv tool`
install of `klayout-tools` does not ship.)

**Conclusion**: `klt signoff` aggregates `klt`'s own native JSON envelope
kinds; it has no ingestion path for this repo's (and `gf180-bandgap`'s)
Markdown evidence-record convention, and item 8 is not a kind it grades in
either mode. Per this issue's acceptance criteria, that is the documented
fallback rather than a blocker: this report is hand-assembled from
`sim/spec-coverage.md` and the underlying records, exactly as item 8's own
text describes. Filed as a generic tool-gap issue at
[`2AMLogic/klayout-tools`](https://github.com/2AMLogic/klayout-tools) per
this repo's friction protocol (`CLAUDE.md`):
[`klayout-tools#1152`](https://github.com/2AMLogic/klayout-tools/issues/1152).

## Provenance

- **Spec revision**: `spec/usb2-device-phy.md`, status "Ratified
  2026-08-10" (issue #1), last touched at commit
  `51d01dfa7de9f365fcaf09725143c293c09ca868`.
- **This report reflects `main` at commit**
  `b8da35a55241716abc376a0e06aa18664e79ddff` (merge of PR #43, "Run full
  45-corner PVT verification vs ratified spec", 2026-08-18) — the point at
  which every record cited below existed.
- **PDK**: `gf180mcuD` @ open_pdks `c6d73a35f524070e85faff4a6a9eef49553ebc2b`.
- **Simulator**: ngspice-47.
- **Netlist provenance**: schematic — every analog record below is against
  the generated export under `design/netlist/`, not a post-layout
  extraction (no `layout/` content exists yet — see the DRC/LVS row below).

### Staleness check

Each cited record's file is content-hashed below (`sha256`). Regenerate
this table with `shasum -a 256 <path>` for any row and compare — a mismatch
means the record was superseded (a new record ID exists in the same
experiment directory, per `sim/`'s append-only convention) and this report
must be re-aggregated against the newer record before being trusted. Per
`design-evidence-tiers.md`'s "Staleness is failure" rule, an unmatched hash
here disqualifies this report, not just the underlying record.

| Evidence record | sha256 |
|---|---|
| `sim/driver-signal-quality/records/20260817-203552-a408cb6.md` | `dbbbb0ee7ba61358b6fdc96549d774e3ff8dc841eddf4571e29dc92ed6528165` |
| `sim/driver-jitter/records/20260817-203915-5a963e7.md` | `276edcecbc3e24279e22aaf505c6f409df8042860ecf321aa3ba78af985126ed` |
| `sim/dplus-pullup-tolerance/records/20260817-203609-a408cb6.md` | `ccf677b754e18473b927b724450a829b3308c0051d9c205176c011310b9a63bb` |
| `sim/diff-receiver-sensitivity/records/20260817-203852-5a963e7.md` | `64351104194e8c58f766073c1e28a9438af811d50c7fd9294cc04ca610c0c28f` |
| `sim/se-receiver-dp-thresholds/records/20260817-203631-a408cb6.md` | `96235a7ef9181bc4e92af9bee7fa65877594ee712936c3d7399c6874f710f99e` |
| `sim/se-receiver-dm-thresholds/records/20260817-203654-a408cb6.md` | `6f6a7eb2ceacac6249a743c67401f720ad800620a55e223abb011026a88f7b29` |
| `verification/records/bit-codec-functional/records/20260816-074908-4e92fcc.md` | `4e3353e8b1ecfa443f0dfd9be0862f7d7aa623ce08d44beeda35313b75469e3f` |
| `verification/records/utmi-framing-functional/records/20260817-184228-72de176.md` | `254cd8dfee31e3f527694288818a38ddccd939921c920be0bb8ca15369257f73` |

## §8.2 aggregate — every analog spec row, no exceptions

Full corner-matrix detail (per-corner values, failure mechanisms, and the
engineering explanation for each) lives in
[`sim/spec-coverage.md`](../sim/spec-coverage.md); this table restates only
the verdict and citation for each row, so this artifact stands alone as the
one-page T1 item 8 answer.

**No spec limit was relaxed and no failing row is reclassified here.** Four
rows fail at some corners; one carries no pass/fail claim by the ratified
spec's own design (see below) — both are recorded as-is, per `CLAUDE.md`
("Agents do not relax the ratified spec to make a result pass").

| §8.2 row | Verdict | Evidence record |
|---|---|---|
| Rise/fall time | **FAIL** — 3/45 corners exceed the 20 ns bound | `sim/driver-signal-quality/records/20260817-203552-a408cb6.md` |
| Crossover voltage | **FAIL** — 2/45 corners below the 1.3 V bound | `sim/driver-signal-quality/records/20260817-203552-a408cb6.md` |
| Rise/fall matching | **FAIL** — 36/45 corners outside the ±10 % bound (dominant failure) | `sim/driver-signal-quality/records/20260817-203552-a408cb6.md` |
| Full-speed signal quality | **FAIL** on the §6 numeric rows above; monotonicity/single-zero-crossing passes 45/45 | `sim/driver-signal-quality/records/20260817-203552-a408cb6.md` |
| Driver-output timing jitter | **No pass/fail claimed** — §8.2's own note forbids a numeric bound absent from the ratified spec text; recorded as engineering data, 45/45 | `sim/driver-jitter/records/20260817-203915-5a963e7.md` |
| D+ pull-up tolerance | **PASS** 45/45 | `sim/dplus-pullup-tolerance/records/20260817-203609-a408cb6.md` |
| Receiver thresholds — differential | **FAIL** — 30/45 corners fail at the 2.5 V common-mode point; 45/45 pass at 0.8 V and 1.65 V | `sim/diff-receiver-sensitivity/records/20260817-203852-5a963e7.md` |
| Receiver thresholds — single-ended D+ | **PASS** 45/45 | `sim/se-receiver-dp-thresholds/records/20260817-203631-a408cb6.md` |
| Receiver thresholds — single-ended D− | **PASS** 45/45 | `sim/se-receiver-dm-thresholds/records/20260817-203654-a408cb6.md` |
| DRC / LVS | **Not applicable yet** — no `layout/` content to run `klt drc` / `klt lvs` against | — |

**Summary**: 3 of 9 electrical rows PASS at every one of the 45 corners; 4
FAIL at some corners (details and root-cause discussion in
`sim/spec-coverage.md`); 1 carries no spec-mandated pass/fail bound by
design; DRC/LVS await a layout. This is the honest current state of the
design against the ratified spec — the acceptance criteria for this report
explicitly forbid hiding or softening that.

## §11 digital coverage (not a PVT-row claim)

§8.2's table is entirely analog. The digital UTMI-side logic's
verification floor is set by spec §11 (bit-exact functional correctness
against NRZI/bit-stuffing/SYNC/EOP/line-state behavior via a cocotb
testbench), which is already substantiated:

| §11 clause | Verdict | Evidence record |
|---|---|---|
| NRZI encode/decode, bit stuffing/destuffing, codec loopback | **PASS** | `verification/records/bit-codec-functional/records/20260816-074908-4e92fcc.md` |
| SYNC detection, EOP detection, line-state decode, top-level UTMI wrapper | **PASS** | `verification/records/utmi-framing-functional/records/20260817-184228-72de176.md` |

Gate-level PVT timing closure of that logic (standard-cell STA across the
same §8.1 corner grid) is not covered by any record yet — it needs a
synthesized netlist with SDF, which this repo does not produce today. §8.2
does not require it; it is noted here as a known gap, not claimed.

## Reproducing this report

```bash
# Re-run any experiment (mints a new append-only record):
python3 sim/run_corners.py driver-signal-quality
python3 sim/run_corners.py driver-jitter
python3 sim/run_corners.py dplus-pullup-tolerance
python3 sim/run_corners.py diff-receiver-sensitivity
python3 sim/run_corners.py se-receiver-dp-thresholds
python3 sim/run_corners.py se-receiver-dm-thresholds

# Re-check the tool-fit finding above against the installed klt version:
klt --version
klt signoff sim/driver-signal-quality/records/*.md   # expected to fail: not JSON
echo '{"kind":"mixed-signal"}' | klt signoff --manifest -   # needs a klayout-tools
                                                              # checkout with docs/
                                                              # alongside the install

# Re-hash every cited record and diff against the "Staleness check" table above:
shasum -a 256 \
  sim/driver-signal-quality/records/20260817-203552-a408cb6.md \
  sim/driver-jitter/records/20260817-203915-5a963e7.md \
  sim/dplus-pullup-tolerance/records/20260817-203609-a408cb6.md \
  sim/diff-receiver-sensitivity/records/20260817-203852-5a963e7.md \
  sim/se-receiver-dp-thresholds/records/20260817-203631-a408cb6.md \
  sim/se-receiver-dm-thresholds/records/20260817-203654-a408cb6.md \
  verification/records/bit-codec-functional/records/20260816-074908-4e92fcc.md \
  verification/records/utmi-framing-functional/records/20260817-184228-72de176.md
```

This report is itself append-only in spirit: a later re-run that changes
any cited record's hash means this report is stale and must be superseded
by a new version of this file (or a dated addendum), never silently edited
to hide the drift.
