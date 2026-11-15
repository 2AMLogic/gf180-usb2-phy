# `manifests/artifacts/` — stored-evidence manifests

One file per stored run or record: `<bench>-<run-id>.manifest.json`. Each entry
names one object in the fleet artifact store by its sha256, with `size`, `kind`
(`evidence`), `producer` (`tool`, `version`, `loom.repo`, `commit`), `uri` (the
logical `artifact:<key>`, never a storage location) and `name`, the path the
bytes would have had in the tree. The format is klayout-tools'
`docs/cli/artifact.md`.

Two evidence trees write manifests here — the `name` root says which:

| writer | `name` root | since |
|---|---|---|
| `sim/run_corners.py` (analog corner campaigns) | `sim/` | issue #237, DR-0008 |
| `scripts/store_verification_evidence.py` (one verification record) | `verification/records/` | issue #366 |

`scripts/check_artifact_manifests.py` accepts a `name` under either root and
nothing else (its `EVIDENCE_ROOTS`); `layout/digital/`, DR-0008's other
deferred tree, has no writer and is not admitted.

Evidence bytes are private; these manifests are public. The Markdown record
stays committed — under `sim/<bench>/records/` or
`verification/records/<experiment>/records/` — with a "Stored evidence" table
(name, size, sha256).

Not everything under an admitted root moves: the artefacts that
`manifests/gf180-usb2-phy.json` cites as in-tree signoff evidence (24 under
`verification/records/`, as of `22ceb85`, 2026-11-14) stay committed and are
named in no manifest, until issue #375 establishes whether `klt signoff` can
re-hash a manifest-backed citation. Keeping a file tracked but unnamed passes
the no-committed-blob rule below, which inspects manifest-named paths only.

Manifests are append-only evidence: never edit or delete one
(`sim/check_records.py --require-append-only` enforces it). CI runs
`python3 scripts/check_artifact_manifests.py check --tree <sha>`, which is
offline: it checks the schema and that no stored object's bytes are also
committed. It does **not** hash-verify; that is `klt artifact verify
<manifest>` with `KLT_ARTIFACT_BROKER` set, from a fleet worker.

See `sim/README.md` and `verification/README.md`, both "Stored evidence", and
`spec/decisions/0008-stored-evidence-manifest-forward.md`.
