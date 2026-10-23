# DR-0008 — New corner-run evidence is stored out of tree; git keeps manifests

- **Status**: Accepted (evidence-storage policy only; no spec row, bound or tolerance changes)
- **Date**: 2026-10-23
- **Raised by**: Builder agent, issue #237
- **Does not change**: the ratified spec, any bound, the full-speed-only,
  device-only, UTMI-boundary scope, or the append-only evidence rule.

## Context

`sim/` carries about 92 MB of tracked run output (raw per-corner logs and
netlist snapshots), and every new campaign adds more. The fleet now has an
artifact store with a broker; operator decision 1.1 (2026-10-22) is that
evidence bytes are private and manifests are public.

## Decision

1. Records minted by `sim/run_corners.py` from this change on store their
   netlist snapshot and per-corner logs through `klt artifact put`. Git gets
   `manifests/artifacts/<experiment>-<record-id>.manifest.json` and the
   Markdown record, which lists each object's name, size and sha256.
2. **Manifest-forward only.** Already-committed evidence is not moved,
   rewritten or deleted; `CLAUDE.md` makes records append-only and this
   decision does not relax that. Manifests are themselves append-only.
3. **Fail closed.** No broker, no `klt artifact put`, a `klt` that writes
   non-`artifact:` uris, or a failed put exits 10 and commits nothing. There is
   no flag to commit the bytes when the broker is down (rejected: it would
   reintroduce the repository growth this decision removes and make the
   evidence location depend on the day's outage).
4. CI checks manifests offline (`scripts/check_artifact_manifests.py check`:
   schema, `artifact:` uris only, no stored object also committed). Hash
   verification against the broker (`klt artifact verify`) runs from a fleet
   worker, not CI.
5. The CI `klt` pin is **not** bumped. It is the signoff/layout build, and
   moving it would re-freeze `manifests/t1-signoff-report.json`. The artifact
   client is a separate install; the writer detects a `klt` that is too old.

## Consequences

- `sim/check_records.py` accepts a manifest in place of committed
  `netlist-snapshots/` and `corners/` files, and treats manifests as
  append-only.
- `verification/records/` and `layout/digital/` are out of this change; they
  can use a documented `klt artifact put` recipe plus the same CI check. A
  follow-up would automate them.
- Live behaviour against a real broker has not been exercised in this change;
  the first real campaign should be confirmed with `klt artifact verify`.
