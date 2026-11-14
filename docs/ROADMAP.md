# Roadmap

`gf180-usb2-phy` is a full-speed, device-only USB 2.0 PHY on the open gf180mcu
PDK, ending at the UTMI boundary, built to be finished and verified with the
open flow and to surface klayout-tools (`klt`) gaps along the way.

Status as of 2026-11-13, `main` @ `b2fa2c7`.

The verdict of record stays the machine-graded manifest
(`manifests/gf180-usb2-phy.json`, frozen report
`manifests/t1-signoff-report.json`, explained in `manifests/README.md`) and the
per-row index `sim/spec-coverage.md`. Tracker state is as read on 2026-11-13.

## Where it stands

Spec ratified 2026-08-10 (`spec/usb2-device-phy.md`). Nothing has been taped
out; `measurements/` stays empty until then.

The frozen report, graded by `klt` 0.9.0, reads **17 of 22 T1 item rows `met`,
one `not_applicable`, four `unmet`, tier `null`**. Tracking issue: #3.

Items 1, 2, 4, 8, 9 and 10 are `met` in both partitions (analog layout: five
committed GDS, `layout/analog/provenance.json`, #251, #252; analog LVS: five
matches, #346, cited by #247). Item 6 is `met` for analog and not applicable
to digital. The digital partition is `met` on every other row. The four unmet
rows are all analog:

| T1 item (analog) | Report says | Issue |
|---|---|---|
| 3 DRC clean | `unmet`, `no_evidence` | #246 |
| 5 Full corner verification | `unmet`, `partial_coverage` | #249 |
| 7 Post-layout verification | `unmet`, `no_evidence` | #53 |
| 11 Power delivery (structural) | `unmet`, `no_evidence` | #248 |

What the `met` rows do and do not say, in the repo's own words:

- Every electrical row in `sim/spec-coverage.md` is measured on the
  **schematic** netlist over the 45-corner grid. No analog row has been re-run
  against an extracted netlist.
- The analog LVS match (`verification/records/analog-lvs/`) compared MOS
  `L`/`W` and **no resistor dimension** (`layout/README.md`).
- The analog streams were DRC-clean in their generation runs, but no `klt drc`
  report with its coverage block is cited for them.

## Now

1. **Power delivery, analog partition (#248, in progress).** Done when an
   analog ERC supply spec sits beside `layout/digital/erc-supply-spec.json`,
   `klt erc` reports for the five streams are committed with zero
   `erc.unconnected_net`, `erc.supply_short` and checked `erc.missing_tie`,
   and `11.analog` renders `met`.
2. **Bring the Challenge #5 proposal in line with the tree (#355, PR #358).**
   The PR carries `loom:changes-requested` and a CI failure. Done when it
   merges with `npm run check:ci` green.
3. **Standalone `klt drc` records for the five analog streams** (the first
   deliverable of #246, which does not depend on the pin; no issue of its
   own). Done when one append-only record per stream under
   `verification/records/` pins the GDS hash and deck hash and quotes
   `coverage.layers_in_stream_without_rules`, `coverage.rules_skipped` and
   `coverage.deck_scope`. The manifest citation stays with #246.
4. **Probe parasitic extraction on one analog stream** (first step of #53's
   analog half; no issue of its own). Done when a record states whether the
   pinned `klt` produces a parasitic-annotated netlist that ngspice loads for
   `differential_receiver.gds`, with what the extraction models and omits, or
   names the upstream klayout-tools issue filed for the gap.
5. **Check drawn resistor dimensions against the netlists** (closes the gap
   the LVS match declares; no issue of its own). Done when a committed check
   and record list every poly resistor in the five blocks with drawn versus
   netlist `L`/`W`, with the DR-0010 pull-up deviation shown explicitly.
6. **Correct statements that still say there is no analog layout** (no issue
   of its own): the item 7.analog bullet of `manifests/README.md` and the
   `post-layout-pvt` entry of `verification/README.md`. Done when both
   describe the committed streams and `npm run check:ci` passes.

## Next

- **Cite `3.analog` (#246).** Blocked: `klt signoff` at 0.9.0 and 0.9.1
  rejects a list of reports under one item (klayout-tools#5031, fixed after
  0.9.1; 0.9.1 is the newest PyPI release as read today). Needs a release
  carrying that fix, a pin move in `.github/workflows/ci.yml` and
  `scripts/setup-env.sh` with the frozen report re-rendered, then the
  citation. Done when `3.analog` renders `met` with coverage quoted in
  `manifests/README.md`. Now item 3 supplies the reports.
- **Analog post-layout PVT (#53, analog half).** After Now item 4 shows an
  extraction path: re-run the `sim/spec-coverage.md` rows on extracted
  netlists for all five blocks over the 45 corners, record per-row verdicts
  beside the schematic ones, cite as `7.analog`. The park note on #53 ("no
  analog GDS to extract yet") no longer matches the tree.
- **Hermit simplifications awaiting a decision** (#319, #320, #331, #339,
  #344, #350; #359 newly proposed). Each is a self-contained removal or fold
  with its evidence in the issue; #339 (one cell for the two identical
  single-ended receivers) changes artifacts the manifest cites.

## Later

- **Close `5.analog` (#249).** The only declared gap is
  `driver-output-timing-jitter`: spec 8.2 has no numeric limit. DR-0009
  (`spec/decisions/0009-driver-output-jitter-limit.md`) is `Proposed`.
  Question first: is the proposed limit, and its quoted USB 2.0 source,
  ratified through the review lane in `ratification/`?
- **RX sampling against independent host clocks (#126, DR-0003).** DR-0003 is
  `Proposed`. Question first: may the proposed 4x transition-resynchronized
  scheme with an external 48 MHz clock land as a decision-record update, and
  have the USB 2.0 limits it relies on been checked against the primary
  source? No RTL follows until then.
- **`VPU_REG` rail.** Row G of `docs/chipalooza/challenge-5-proposal.md` is
  recorded unmet at the 2.97 V supply corner. Question first: does the block regulate the
  pull-up rail itself or does the spec take a narrower supply guarantee? That
  is a spec decision record, not a design tweak.

## Blocked and waiting

| Item | Waiting on |
|---|---|
| #3 tracker | every T1 row `met`; stays parked by design |
| #246 (`3.analog` citation) | a klayout-tools release after 0.9.1 with klayout-tools#5031, then a pin move |
| #249 (`5.analog`) | ratification of DR-0009 |
| #53 (`7.analog`) | its park note being re-read against the committed streams |
| #51 (Challenge #5 maturation) | #53 |
| #126, #319, #320, #331, #339, #344, #350 | an operator decision (options in each issue) |
| #98, #99, #100, #195 | parked; see each issue |

Dispatchable today: #248 and #355 are already claimed. Now items 3 to 6 have
no issue yet; until they are filed the repo has no unclaimed ready work.

## Not planned

- High-speed (480 Mbps), host or OTG operation.
- A serial interface engine above UTMI (endpoints, CRC, enumeration).
- USB-IF compliance certification.
- Relaxing a ratified spec row to make a result pass.
