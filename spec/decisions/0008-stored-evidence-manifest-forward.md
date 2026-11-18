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

## Amendment A1 — one-time carve-out for one pre-DR-0008 run (2026-11-18)

- **Status**: **Proposed — awaiting ratification.** The operator authorised
  *proposing* this amendment (issue #364 comment, `/fleet:decide` round
  20261118-r16, q103, option (b)); that comment does not ratify it, and the
  Builder agent does not self-ratify. Section 2 above is not edited.
- **Raised by**: Builder agent, issue #364.

**Carve-out.** Decision 2 ("already-committed evidence is not moved, rewritten
or deleted") is relaxed **once, for named runs only**: a run committed before
this decision whose single `corners/<record-id>/` directory exceeds 10 MB may
have its raw logs moved out of the git tree into the artifact store. The only
current beneficiary is `driver-jitter` run `20260817-203915-5a963e7`
(45 logs, 88,786,939 bytes; 95% of the lines are empty ngspice vector-table
rows, defect fixed forward by #347).

**Conditions, all required:**

1. The bytes are stored with `klt artifact put` and
   `manifests/artifacts/driver-jitter-20260817-203915-5a963e7.manifest.json`
   lists each object's name, size and sha256.
2. `klt artifact verify` against the broker succeeds **before** any log leaves
   git (fail closed, per Decision 3). Recorded in the PR for #364: 45 of 45 ok;
   `--local` re-hash of the in-tree logs also 45 of 45 ok; sizes sum to
   88,786,939.
3. The frozen record `sim/driver-jitter/records/20260817-203915-5a963e7.md`
   and its netlist snapshot are **not** edited; the manifest alone satisfies
   `sim/harness/evidence_lint.py`, and the record's sha256 pin in
   `docs/characterization-report.md` is unchanged.
4. `sim/harness/evidence_lint.py` exempts only the *deletion* of exactly those
   45 manifest-named log paths (`ONE_TIME_CARVE_OUTS`); every other
   modification or deletion still fails.

**Not changed:** git history is not rewritten and nothing is force-pushed, so
clone size is unchanged (the blobs remain in history); the saving is about
85 MB per checkout and worktree. Not a general size exemption: adding a run to
`ONE_TIME_CARVE_OUTS` requires a further amendment. The ratified spec, every
bound and the scope are untouched. Disjoint from any forward-only amendment
for `verification/records/`; each uses its own dated section.
