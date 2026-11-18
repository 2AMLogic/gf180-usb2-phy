# DR-0012 — Renumber the analog-statistical-rows record from DR-0007 to DR-0011

- **Status**: Accepted — resolved decision block on issue #381, option (a)
  (attended `/fleet:decide` session, 2026-11-18; auto-selected under
  `--yolo 70`, confidence 78%, not an operator ruling).
- **Date**: 2026-11-18
- **Raised by**: Builder agent, issue #381
- **Does not change**: any spec row, bound or tolerance, the classification
  in the renumbered record, or any frozen evidence record.

## Context

`spec/decisions/` held two records numbered DR-0007:
`0007-analog-statistical-rows.md` (2026-10-17) and
`0007-retire-bootstrap-harness-counter.md` (2026-10-20). They were numbered
independently while §12.1 listed only DR-0001. `scripts/check_decision_records.py`
carried a single-entry exemption so its uniqueness property passed.

## Decision

1. `0007-analog-statistical-rows.md` is renamed to
   `0011-analog-statistical-rows.md`; its H1 becomes `# DR-0011` and its body
   is otherwise unchanged.
2. `0007-retire-bootstrap-harness-counter.md` stays DR-0007. Two frozen,
   append-only evidence records cite it by path, so it cannot be renamed.
3. Live by-path citations of the analog record, and the abbreviated
   "DR-0007" mentions that meant it, are updated to DR-0011.
4. The checker's `DUPLICATE_PREFIX_EXEMPTION` is deleted; property (a) now
   has no exemption.

## Consequences

- **Historical ambiguity.** Text written before this record that says
  "DR-0007" may mean either record; read it by path, and in git history
  assume the analog record unless the context is `harness_counter`. Superseded
  sections of `verification/statistical-claims-na.md` keep their original
  path citations as history. There is now no DR-0007 analog record, and DR-0011
  is out of date order relative to DR-0008..DR-0010.
- **No spec value changes.** §12.1 gains this record's row and the analog row
  moves to DR-0011; the spec's SHA-256 changes, so
  `verification/statistical-claims-na.md` is superseded and re-pinned.

## Alternatives rejected

- Keep the exemption permanently: leaves "DR-0007" ambiguous forever.
- Renumber the harness-counter record: frozen records cite it by path and
  `--require-append-only` enforces that.
