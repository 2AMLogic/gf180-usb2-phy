# `manifests/artifacts/` — stored-evidence manifests

One file per stored run: `<bench>-<run-id>.manifest.json`, written by
`sim/run_corners.py` (issue #237). Each entry names one object in the fleet
artifact store by its sha256, with `size`, `kind` (`evidence`), `producer`
(`tool`, `version`, `loom.repo`, `commit`), `uri` (the logical
`artifact:<key>`, never a storage location) and `name`, the path the bytes
would have had under `sim/`. The format is klayout-tools' `docs/cli/artifact.md`.

Evidence bytes are private; these manifests are public. The run's Markdown
record is committed under `sim/<bench>/records/` with a "Stored evidence" table
(name, size, sha256).

Manifests are append-only evidence: never edit or delete one
(`sim/check_records.py --require-append-only` enforces it). CI runs
`python3 scripts/check_artifact_manifests.py check --tree <sha>`, which is
offline: it checks the schema and that no stored object's bytes are also
committed. It does **not** hash-verify; that is `klt artifact verify
<manifest>` with `KLT_ARTIFACT_BROKER` set, from a fleet worker.

See `sim/README.md`, "Stored evidence", and `spec/decisions/0008-stored-evidence-manifest-forward.md`.
