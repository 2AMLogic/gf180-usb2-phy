#!/usr/bin/env python3
"""Store one verification record's artifact bytes instead of committing them (#366).

``verification/records/<experiment>/artifacts/<record-id>/`` is the last
evidence tree in this repo still writing its raw bytes into git -- 646 blobs,
76.53 MiB, 40% of the repository (as of `22ceb85`, 2026-11-14), growing by another ~7 MiB at every
digital layout regeneration. DR-0008 ("stored evidence, manifest forward") moved
``sim/`` to the fleet artifact store and names automating this tree as its own
follow-up:

    "`verification/records/` and `layout/digital/` are out of this change; they
     can use a documented `klt artifact put` recipe plus the same CI check. A
     follow-up would automate them."

This is that automation. It reuses ``sim/harness/evidence_store.py`` unchanged:
the bytes go to the store through ``klt artifact put``, git keeps a manifest
under ``manifests/artifacts/<experiment>-<record-id>.manifest.json``, and the
record's own Markdown gains a "Stored evidence" table naming every object.

    store_verification_evidence.py --experiment post-layout-pvt \
        --record-id 20261015-011505-32db02a \
        --stage-dir sim/.work/.stage/post-layout-pvt/20261015-011505-32db02a \
        --exclude sta-corners.json

**Forward-only.** This stores a *staged* directory -- bytes that are not in
git yet -- and appends to a record that is not committed yet. It never reads,
moves, rewrites or deletes anything already under ``verification/records/``;
append-only (DR-0008 point 2) is untouched by construction, and
``verification/check_records.py --require-append-only`` stays green.

**Two differences from the `sim/` writer**, both forced by this tree:

* *Records are hand-authored.* ``sim/`` composes its record from the run's own
  data, so ``evidence_store.store_files`` writes the summary and refuses if it
  already exists. A verification record is written by hand first, so this
  helper **appends** the "Stored evidence" section to the existing file via the
  public ``evidence_store.summary_section`` helper instead.
* *The cited/uncited split is per file, not per record.* A single record
  directory holds both signoff-cited and uncited artefacts -- in
  ``post-layout-pvt/.../20261015-011505-32db02a/``, ``sta-corners.json``
  (0.01 MiB) is cited by ``manifests/gf180-usb2-phy.json`` while its 12
  siblings (7.98 MiB) are not. Cited artefacts must stay committed until
  ``klt signoff``'s ability to re-hash a manifest-backed citation is
  established (#375), so ``--exclude`` names them per file and they are left in
  the staging directory for the caller to commit.

**Fail closed** (DR-0008 point 3). Every failure raises
:class:`evidence_store.StoreError` and nothing is installed under
``manifests/`` or ``verification/``: no broker configured, no ``klt`` with the
``artifact`` verb, a ``klt`` too old to write ``artifact:<key>`` uris, an
unreachable or refusing broker, a put that fails part-way, a manifest that does
not match the bytes it claims. The staged bytes stay where they are, so nothing
is lost. **There is no flag, env var or fallback that commits the bytes
instead** -- that is the whole point of the change, and adding one would undo
it.

Exit codes: 0 stored; 1 nothing stored (fail closed); 2 usage.

Stdlib only; needs ``klt`` and ``$KLT_ARTIFACT_BROKER`` for a real run (the
unit tests inject a ``put`` and need neither).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sim" / "harness"))

import evidence_store  # noqa: E402  (needs the path insert above)
from evidence_store import StoreError  # noqa: E402

#: Logical ``name`` prefix of a stored verification artefact: exactly the path
#: the bytes would have had in the tree, so a manifest entry reads as the file
#: it replaces. ``scripts/check_artifact_manifests.py``'s ``EVIDENCE_ROOTS``
#: admits this root; keep the two in step.
NAME_ROOT = "verification/records"
#: The heading ``evidence_store.summary_section`` emits. Used only to refuse a
#: record that already carries one (storing twice would mint a second manifest
#: for the same record).
SECTION_HEADING = "## Stored evidence"

EXIT_OK, EXIT_STORE, EXIT_USAGE = 0, 1, 2


def name_prefix(experiment: str, record_id: str) -> str:
    """The logical name prefix for one record's artefact directory."""
    return f"{NAME_ROOT}/{experiment}/artifacts/{record_id}"


def record_path(repo_root: Path, experiment: str, record_id: str) -> Path:
    return repo_root / NAME_ROOT / experiment / "records" / f"{record_id}.md"


def resolve_excludes(stage_dir: Path, excludes) -> list[Path]:
    """``--exclude`` values as resolved paths inside ``stage_dir``.

    A value is read relative to ``stage_dir`` (``sta-corners.json``) or as an
    absolute path. A name that is not a file in the staging directory is a
    usage error, not a silent no-op: a typo'd exclusion would store a
    signoff-cited artefact and strip it from the tree.
    """
    out = []
    for raw in excludes:
        p = Path(raw)
        p = p if p.is_absolute() else stage_dir / p
        if not p.is_file():
            raise StoreError(f"--exclude {raw}: not a file in the staging directory")
        out.append(p.resolve())
    return out


def store_record_evidence(files, *, repo_root: Path, experiment: str, record_id: str,
                          record: Path, put=None) -> Path:
    """Store ``files``; commit only their manifest and the record's new section.

    Ordering is what makes this fail closed, and mirrors
    ``evidence_store.store_files``: (1) refuse before any put if the manifest
    exists, the record is missing, or the record already carries a "Stored
    evidence" section; (2) put every file; (3) install the manifest
    exclusively; (4) append the section. A failure in (1)-(2) leaves the
    repository untouched. Returns the manifest path.
    """
    mpath = evidence_store.manifest_path(repo_root, experiment, record_id)
    if os.path.lexists(mpath):
        raise StoreError(f"{mpath.relative_to(repo_root).as_posix()} already exists; "
                         "refusing to overwrite evidence")
    if not record.is_file():
        raise StoreError(f"{record} is not an existing record; write the record first, "
                         "then store its evidence, then commit both together")
    if SECTION_HEADING in record.read_text(encoding="utf-8"):
        raise StoreError(f"{record.name} already has a '{SECTION_HEADING}' section; "
                         "its evidence is stored already")
    if not files:
        raise StoreError("nothing staged to store")
    manifest, empty = (put or evidence_store.put_files)(files, repo_root)
    mrel = mpath.relative_to(repo_root).as_posix()
    evidence_store.install_manifest(manifest, mpath)
    with open(record, "a", encoding="utf-8") as fh:
        fh.write(evidence_store.summary_section(mrel, manifest, empty))
    return mpath


def run(args, *, put=None, preflight=None) -> Path:
    """Preflight, stage, store. Raises :class:`StoreError`; installs nothing on failure."""
    repo_root = Path(args.repo_root).resolve()
    stage_dir = Path(args.stage_dir).resolve()
    if not stage_dir.is_dir():
        raise StoreError(f"staging directory {args.stage_dir} does not exist")
    record = (Path(args.record).resolve() if args.record
              else record_path(repo_root, args.experiment, args.record_id))
    # Validates the experiment/record-id grammar before any work happens.
    evidence_store.manifest_path(repo_root, args.experiment, args.record_id)
    (preflight or evidence_store.preflight)(repo_root)
    evidence_store.refuse_tracked_stage(stage_dir, repo_root)
    files = evidence_store.stage_files(
        stage_dir, name_prefix(args.experiment, args.record_id),
        exclude=resolve_excludes(stage_dir, args.exclude))
    return store_record_evidence(files, repo_root=repo_root, experiment=args.experiment,
                                 record_id=args.record_id, record=record, put=put)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="Fail closed: on any failure nothing is installed and the staged bytes "
               "are left alone. There is no flag that commits the bytes instead.")
    ap.add_argument("--experiment", required=True,
                    help="experiment slug, e.g. post-layout-pvt")
    ap.add_argument("--record-id", required=True,
                    help="record id, e.g. 20261015-011505-32db02a")
    ap.add_argument("--stage-dir", required=True,
                    help="directory of this record's artefact bytes; must be "
                         "git-ignored or outside the checkout")
    ap.add_argument("--exclude", action="append", default=[], metavar="NAME",
                    help="a staged file to leave out (relative to --stage-dir). "
                         "Use once per signoff-cited artefact; those stay committed "
                         "until #375 settles klt signoff's manifest citations.")
    ap.add_argument("--record", default=None,
                    help="the record markdown to append to (default: "
                         "verification/records/<experiment>/records/<record-id>.md)")
    ap.add_argument("--repo-root", default=str(REPO_ROOT), help=argparse.SUPPRESS)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        mpath = run(args)
    except StoreError as exc:
        print(f"error: evidence could not be stored: {exc}\n"
              f"nothing was written under manifests/ or verification/; "
              f"staged bytes kept in {args.stage_dir}", file=sys.stderr)
        return EXIT_STORE
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    print(f"manifest  : {mpath.relative_to(Path(args.repo_root).resolve()).as_posix()}")
    print(f"record    : appended a '{SECTION_HEADING[3:]}' section")
    print(f"staged    : {args.stage_dir} (bytes are in the artifact store; "
          "do not commit them)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
