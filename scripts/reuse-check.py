#!/usr/bin/env python3
# Provenance: verbatim copy of 2AMLogic/2am scripts/reuse-check.py at
# commit 9032d1d629cfa77f15057586f7a3a5013dcd12bb (2026-09-21) — the same
# commit gf180-usb2-phy issue #84 / spec/decisions/0002 cite for REUSE.md
# rule 9. This copy is the per-repo CI leg (no network, no sibling
# checkout required); re-pin by re-copying from 2am and updating this
# comment and reuse.lock.json together.
"""
reuse-check.py — enforce REUSE.md (cross-cutting rule 9, 2am#899).

  ./scripts/reuse-check.py <repo-dir> [--siblings-root DIR]
      Validate ONE consumer's reuse.lock.json. Needs no network and nothing
      from this repo, so a block repo can run a copy of it in CI.

  ./scripts/reuse-check.py --fleet [--manifest repos.yml] [--root DIR]
                           [--require-pins]
      Validate every `consumes` / `ported_from` edge in repos.yml and report
      each `consumes` edge as PINNED or UNPINNED.

Exit 0 clean, 1 on any violation, 2 on usage error.

WHY A STAMP IS CHECKED THREE WAYS. A `vendored` entry's sha256 must equal the
local file (nobody edited the copy), and, when the sibling checkout is on disk,
the upstream file AT THE PINNED COMMIT (the stamp was not invented). Whether
upstream has MOVED since is a third, separate question and only ever a report:
a pin going stale is information the consumer acts on, not a defect in it.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

LOCK = "reuse.lock.json"
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
STATUSES = ("evaluate", "adopting", "kept")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def git(repo, *args):
    """stdout bytes, or None if git fails (missing commit, not a repo, ...)."""
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def check_repo(repo, siblings_root):
    """Return (errors, notes) for one consumer's lock file."""
    errors, notes = [], []
    path = os.path.join(repo, LOCK)
    if not os.path.isfile(path):
        return [f"{LOCK} not found in {repo}"], notes
    try:
        lock = json.load(open(path))
    except ValueError as e:
        return [f"{LOCK} is not valid JSON: {e}"], notes
    if lock.get("schema") != 1:
        errors.append(f"schema must be 1, got {lock.get('schema')!r}")

    for imp in lock.get("imports", []):
        src, commit, mode = imp.get("from", ""), imp.get("commit", ""), imp.get("mode")
        tag = f"import {src or '<no from>'}"
        if not re.match(r"^[\w.-]+/[\w.-]+$", src):
            errors.append(f"{tag}: `from` must be <owner>/<repo>")
        if not SHA1.match(commit):
            errors.append(f"{tag}: `commit` must be a full 40-hex SHA, got {commit!r}")
        if mode not in ("fetched", "vendored"):
            errors.append(f"{tag}: `mode` must be fetched|vendored, got {mode!r}")
        if not imp.get("files"):
            errors.append(f"{tag}: no `files` — an import that pins no bytes pins nothing")

        upstream = os.path.join(siblings_root, src.split("/")[-1])
        have_upstream = SHA1.match(commit) and git(upstream, "cat-file", "-e", commit + "^{commit}") is not None
        if not have_upstream:
            notes.append(f"{tag}: sibling checkout or commit not on disk — upstream stamps UNVERIFIED")

        for f in imp.get("files", []):
            up, local, want = f.get("upstream", ""), f.get("local"), f.get("sha256", "")
            ftag = f"{tag}: {up or '<no upstream>'}"
            if not SHA256.match(want):
                errors.append(f"{ftag}: `sha256` must be 64 hex")
                continue
            diverged = f.get("diverged")
            if diverged and not os.path.isfile(os.path.join(repo, diverged)):
                errors.append(f"{ftag}: `diverged` names {diverged}, which does not exist")
            if mode == "vendored":
                lp = os.path.join(repo, local or "")
                if not local or not os.path.isfile(lp):
                    errors.append(f"{ftag}: vendored entry needs an existing `local` file")
                elif sha256_bytes(open(lp, "rb").read()) != want and not diverged:
                    errors.append(f"{ftag}: {local} no longer matches its stamp and records no divergence")
            if have_upstream:
                blob = git(upstream, "show", f"{commit}:{up}")
                if blob is None:
                    errors.append(f"{ftag}: not present upstream at {commit[:12]}")
                elif sha256_bytes(blob) != want:
                    errors.append(f"{ftag}: stamp does not match upstream at {commit[:12]}")
                elif subprocess.run(["git", "-C", upstream, "diff", "--quiet", commit, "origin/HEAD", "--", up],
                                    capture_output=True).returncode == 1:  # 1 = differs; 128 = no origin/HEAD
                    notes.append(f"{ftag}: upstream has changed since {commit[:12]} — pin is stale")

    for t in lock.get("in_tree", []):
        ttag = f"in_tree {t.get('block', '<no block>')}"
        if t.get("status") not in STATUSES:
            errors.append(f"{ttag}: `status` must be one of {'|'.join(STATUSES)}")
        if not t.get("sibling"):
            errors.append(f"{ttag}: `sibling` is required — name the repo that builds this block")
        if t.get("status") == "kept":
            d = t.get("decision")
            if not d or not os.path.isfile(os.path.join(repo, d)):
                errors.append(f"{ttag}: `kept` requires an existing `decision` record")
        elif t.get("status") == "evaluate":
            notes.append(f"{ttag}: undecided against {t.get('sibling')}")
    return errors, notes


def check_fleet(manifest, root, require_pins):
    import yaml  # fleet mode only: a block repo's CI copy never needs PyYAML

    repos = {r["name"]: r for r in yaml.safe_load(open(manifest))["repos"]}
    errors, report = [], []
    for name, r in repos.items():
        for field in ("consumes", "ported_from"):
            for dep in r.get(field) or []:
                edge = f"{name} -{field}-> {dep}"
                if dep == name:
                    errors.append(f"{edge}: self-edge")
                    continue
                if dep not in repos:
                    errors.append(f"{edge}: no such record in {os.path.basename(manifest)}")
                    continue
                for end in (r, repos[dep]):
                    if end.get("firewall") or end.get("privileged"):
                        errors.append(f"{edge}: touches firewall/privileged repo {end['name']}")
                if field == "consumes" and r.get("visibility") == "public" and repos[dep].get("visibility") != "public":
                    errors.append(f"{edge}: a public consumer may not import from a non-public repo")

    for field in ("consumes", "ported_from"):  # cycles, per edge kind
        state = {}

        def visit(n, trail):
            if state.get(n) == "done":
                return
            if state.get(n) == "open":
                errors.append(f"{field} cycle: {' -> '.join(trail[trail.index(n):] + [n])}")
                return
            state[n] = "open"
            for d in repos.get(n, {}).get(field) or []:
                if d in repos and d != n:
                    visit(d, trail + [n])
            state[n] = "done"

        for n in repos:
            visit(n, [])

    unpinned = 0
    for name, r in repos.items():
        if not r.get("consumes"):
            continue
        pinned = set()
        lock_path = os.path.join(root, r.get("dir", name), LOCK)
        if os.path.isfile(lock_path):
            try:
                pinned = {i.get("from", "").split("/")[-1] for i in json.load(open(lock_path)).get("imports", [])}
            except ValueError:
                errors.append(f"{name}: {LOCK} is not valid JSON")
        for dep in r["consumes"]:
            ok = dep in pinned
            unpinned += 0 if ok else 1
            report.append(f"{'PINNED  ' if ok else 'UNPINNED'}  {name} -> {dep}")
    print("\n".join(report))
    print(f"\n{len(report) - unpinned} pinned, {unpinned} unpinned, of {len(report)} declared edges")
    if require_pins and unpinned:
        errors.append(f"{unpinned} declared edge(s) have no pin (--require-pins)")
    return errors


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Enforce REUSE.md: pinned, stamped reuse between block repos.")
    ap.add_argument("repo", nargs="?", help="consumer repo directory (per-repo mode)")
    ap.add_argument("--siblings-root", help="where sibling checkouts live (default: the repo's parent)")
    ap.add_argument("--fleet", action="store_true", help="check every edge in repos.yml")
    ap.add_argument("--manifest", default=os.path.join(here, "..", "repos.yml"))
    ap.add_argument("--root", default=os.path.expanduser("~/GitHub"), help="workspace root for --fleet")
    ap.add_argument("--require-pins", action="store_true", help="--fleet: an unpinned edge is fatal")
    a = ap.parse_args()
    if a.fleet == bool(a.repo):
        ap.error("give exactly one of <repo-dir> or --fleet")

    if a.fleet:
        errors, notes = check_fleet(a.manifest, a.root, a.require_pins), []
    else:
        repo = os.path.abspath(a.repo)
        errors, notes = check_repo(repo, a.siblings_root or os.path.dirname(repo))
    for n in notes:
        print(f"note: {n}")
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
