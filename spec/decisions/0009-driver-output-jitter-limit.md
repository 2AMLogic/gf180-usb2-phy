# DR-0009 — Numeric limit for the §8.2 driver-output timing-jitter row

- **Status**: Proposed (awaiting ratification; not in force)
- **Date**: 2026-10-27
- **Raised by**: Builder agent, issue #249
- **Does not change**: the ratified spec text of §8.2 or any other section,
  any ratified bound, the full-speed-only, device-only, UTMI-boundary scope,
  or any existing evidence record. Ratifying this record is not the Builder's
  to grant.

## Context

T1 item 5 (full corner verification) renders `unmet` only because §8.2's
"Driver-output timing jitter" row has no numeric limit to grade against. The
§8.2 note says the limit must be "pulled verbatim from the physical USB 2.0
specification text" before any `sim/` record claims pass/fail, and that the
section numbers (§7.1.13–§7.1.15) were unconfirmed. The row is therefore
recorded as engineering data (`sim/driver-jitter/records/20261015-104027-d109790.md`)
and its envelope is deliberately uncited, since an envelope with no limited
measurement grades `pass` vacuously (klayout-tools#3769).

## Source (quoted, not recalled)

Text taken from *Universal Serial Bus Specification, Revision 2.0*, April 27,
2000, as extracted from a third-party mirror of the PDF
(`https://eater.net/downloads/usb_20.pdf`, 2026-10-27). The repo does not hold
the document, so the ratifier should re-check these quotes against the
usb.org copy.

**§7.1.13.1.1 Low-/full-speed Data Source Jitter:**

> The data jitter is measured with the same load used for maximum rise and
> fall times and is measured at the crossover points of the data lines, as
> shown in Figure 7-36.
>
> For full-speed transmissions, the jitter time for any consecutive
> differential data transitions must be within ±2.0 ns and within ±1.0 ns
> for any set of paired (JK-to-next JK transition or KJ-to-next KJ
> transition) differential data transitions.
>
> These jitter numbers include timing variations due to differential buffer
> delay and rise and fall time mismatches, internal clock source jitter, and
> noise and other random effects.

**§7.1.15.1 / Table 7-4 Full-speed Jitter Budget**, row "Source Driver
Jitter": next transition 2.0 ns, paired transition 1.0 ns. The table lists
"Source Frequency Tolerance (worst-case)" as a separate row (0.21 ns/bit) and
the text says the frequency-tolerance component "has been allocated to the
appropriate device", so the ±2.0 / ±1.0 ns above are the driver's own
allotment, not a share of a larger source number.

Correction to the §8.2 pointer: the limit is in §7.1.13.1.1; §7.1.15 is the
*receiver* jitter section and carries the budget table that confirms it.

## Derivation to this block's share

This block is the full-speed source driver, so its share of the system
budget is the Table 7-4 "Source Driver Jitter" row in full: no further
apportioning. Hub jitter, destination frequency tolerance and the receive
budget belong to other devices in the path.

## Decisions (proposed)

1. **Branch taken: numeric limit** (not "not pass/fail"). Add to the §8.2
   graded row set, for the driver-output timing-jitter row, measured at the
   differential crossover into the §6 50 pF load:
   - consecutive transitions: |deviation| ≤ **2.0 ns**
   - paired transitions: |deviation| ≤ **1.0 ns**
2. **Mapping to existing measurements** (`sim/driver-jitter`): the consecutive
   limit applies to `jit_cons_max_ps`. The paired limit is applied,
   conservatively, to `jit_grid_max_ps` (maximum deviation of any later
   edge from the nominal N × T_bit grid anchored at edge 1), which covers
   every JK-to-next-JK and KJ-to-next-KJ pair and also opposite-polarity
   pairs the spec does not limit. The ratifier may instead ask for a
   same-polarity-only measurement.
3. **What a pass would and would not show.** The existing testbench drives an
   ideal PWL stimulus, so its deviations are the driver's buffer delay and
   rise/fall mismatch only. The spec figure also includes internal clock
   source jitter and noise, which this block's simulation does not model.
   A pass is therefore evidence about the driver's contribution, not a claim
   about the whole source. Any claim wording must say so.
4. **Expected margin (engineering data, not a verdict).** Across the 45
   corners of record 20261015-104027-d109790 the largest `jit_grid_max_ps` is
   0.163 ps and the largest `jit_cons_max_ps` is 0.143 ps (peak-to-peak
   columns reach 0.261 ps). That is more than 6000× inside 1.0 ns and more
   than 13000× inside 2.0 ns. This is not graded until the limit is ratified.
5. The ratified §8.2 text and values are not edited here. After ratification,
   a separate issue puts the limits into the `sim/driver-jitter` request,
   re-mints the envelope (append-only), cites it with
   `rows: ["driver-output-timing-jitter"]`, drops the declared gap and
   regenerates the report. The existing limit-free envelope is not cited.

## Alternatives rejected

- **Not a pass/fail row for this block.** The spec gives a numeric limit for
  exactly this quantity at the source driver, so there is no reason to remove
  the row from grading.
- **Amending §8.2 in place.** That is a ratified-spec change; it goes through
  ratification of this record instead.
- **Citing the existing limit-free envelope.** It would grade `pass`
  vacuously (klayout-tools#3769).
- **Stating figures without a quote.** Rejected by the §8.2 note; the figures
  above are quoted from the specification text.
