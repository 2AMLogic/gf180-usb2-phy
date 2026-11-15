# Roadmap

`gf180-usb2-phy` is a full-speed, device-only USB 2.0 PHY on the open gf180mcu
PDK, ending at the UTMI boundary, built to be finished and verified with the
open flow and to surface klayout-tools (`klt`) gaps along the way.

Status as of 2026-11-15, `main` @ `4bbdd5c`.

The verdict of record stays the machine-graded manifest
(`manifests/gf180-usb2-phy.json`, frozen report
`manifests/t1-signoff-report.json`, explained in `manifests/README.md`) and the
per-row index `sim/spec-coverage.md`. Tracker state is as read on 2026-11-15.

## Where it stands

Spec ratified 2026-08-10 (`spec/usb2-device-phy.md`). Nothing has been taped
out; `measurements/` stays empty until then.

The frozen report, graded by `klt` 0.9.0, reads **18 of 22 T1 item rows `met`,
one `not_applicable`, three `unmet`, tier `null`**. Tracking issue: #3.

Items 1, 2, 4, 8, 9, 10 and 11 are `met` in both partitions (analog layout:
five committed GDS, `layout/analog/provenance.json`, #251, #252; analog LVS:
five matches, #346, cited by #247; power delivery: ERC supply records, #248,
merged as PR #363). Item 6 is `met` for analog and not applicable to digital.
The digital partition is `met` on every other row. The three unmet rows are
all analog:

| T1 item (analog) | Report says | Issue |
|---|---|---|
| 3 DRC clean | `unmet`, `no_evidence` | #246 |
| 5 Full corner verification | `unmet`, `partial_coverage` | #249 |
| 7 Post-layout verification | `unmet`, `no_evidence` | #53 |

What the `met` rows do and do not say, in the repo's own words:

- Every electrical row in `sim/spec-coverage.md` is measured on the
  **schematic** netlist over the 45-corner grid. No analog row has been re-run
  against an extracted netlist.
- The analog LVS match (`verification/records/analog-lvs/`) compared MOS
  `L`/`W` and **no resistor dimension** (`layout/README.md`).
- The analog streams were DRC-clean in their generation runs, but no `klt drc`
  report with its coverage block is cited for them.

## Now

Completed since the 2026-11-13 snapshot: power-delivery ERC for the five
analog streams (#248, merged as PR #363, `11.analog` now renders `met`); the
Challenge #5 proposal rework (#355, PR #358 merged); standalone `klt drc`
records for the five streams (#368, `verification/records/analog-drc/`); and
the parasitic-extraction probe (#369,
`verification/records/analog-extraction/records/20261114-094500-22ceb8575799.md`).

1. **Check drawn resistor dimensions against the netlists (#370).** Closes the
   gap the LVS match declares. Done when a committed check and record list
   every poly resistor in the five blocks with drawn versus netlist `L`/`W`,
   with the DR-0010 pull-up deviation shown explicitly.
2. **Correct statements that still say there is no analog layout (#371).**
   The item 7.analog bullet of `manifests/README.md` and the
   `post-layout-pvt` entry of `verification/README.md`. Done when both
   describe the committed streams and `npm run check:ci` passes.

## Next

- **Cite `3.analog` (#246).** Blocked: `klt signoff` at 0.9.0 and 0.9.1
  rejects a list of reports under one item (klayout-tools#5031, fixed after
  0.9.1; 0.9.1 is the newest PyPI release as read today). Needs a release
  carrying that fix, a pin move in `.github/workflows/ci.yml` and
  `scripts/setup-env.sh` with the frozen report re-rendered, then the
  citation. Done when `3.analog` renders `met` with coverage quoted in
  `manifests/README.md`. The per-stream reports are committed
  (`verification/records/analog-drc/`).
- **Analog post-layout PVT (#53, analog half).** The extraction path is shown
  (probe record `20261114-094500-22ceb8575799`: `klt extract --parasitics`
  produces a netlist ngspice loads — 43 R, 10 ground C, 24 coupling C, 0 L —
  with one non-optional `.SUBCKT` port-order adaptation). Re-run the
  `sim/spec-coverage.md` rows on extracted netlists for all five blocks over
  the 45 corners, record per-row verdicts beside the schematic ones, cite as
  `7.analog`. #53's park stays formally on klayout-tools#1962 until it is
  re-stated, narrowed or released against this record.
- **Hermit simplifications awaiting an operator decision** (#319, #320, #331,
  #339, #344, #350, #360, #364, #380, #385; #359 is in progress under
  `loom:building`). Each is a self-contained removal or fold with its evidence
  in the issue; #339 (one cell for the two identical single-ended receivers)
  changes artifacts the manifest cites.

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
| #53 (`7.analog`) | park stays on klayout-tools#1962; the extraction record is what re-states, narrows or releases it |
| #51 (Challenge #5 maturation) | #53 |
| #126, #319, #320, #331, #339, #344, #350, #360, #364, #380, #385 | an operator decision (options in each issue) |
| #98, #99, #100, #195 | parked; see each issue |

Dispatchable today: #370 (points 5) and #382 (points 2) sit on `loom:issue`,
unclaimed. Now item 1 is #370; item 2's issue #371 is in triage awaiting
curation.

## Not planned

- High-speed (480 Mbps), host or OTG operation.
- A serial interface engine above UTMI (endpoints, CRC, enumeration).
- USB-IF compliance certification.
- Relaxing a ratified spec row to make a result pass.
