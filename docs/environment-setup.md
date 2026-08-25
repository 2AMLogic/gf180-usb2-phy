# Environment setup

What a clean machine actually needs to run this repo's verification harnesses.
Each toolchain section below is added by whichever issue first bootstraps that
harness, and records what was *actually* needed on the machine it was
verified on — not what was assumed. Do not overwrite another toolchain's
section; append a new one instead.

## Analog toolchain

Needed to run `sim/` — the ngspice PVT-corner harness ported from the sibling
[`gf180-bandgap`](https://github.com/2AMLogic/gf180-bandgap) repository (see
`sim/harness/README.md`).

### What you need

| Tool | Why | Verified install |
|---|---|---|
| `ngspice` | circuit simulation | macOS: `brew install ngspice` (verified: Homebrew `ngspice-46`). Debian/Ubuntu: `apt-get install ngspice`. |
| gf180mcu PDK | device models (`sm141064.ngspice`, `design.ngspice`) | `pip install volare && volare enable --pdk gf180mcu <hash>` — see below |
| `xschem` | schematic capture (optional; not required to run the corner harness) | macOS: `brew install xschem`. Debian/Ubuntu: distro package. |
| Python ≥ 3.9 | the harness itself | stdlib only — no `pip install` needed for `sim/harness/`, no virtualenv |

### Installing the PDK with volare

The harness resolves the PDK from environment variables, a config file, or a
set of built-in search roots — see `sim/harness/pdk.py`'s resolution order and
`sim/harness/README.md` § "Prerequisites" for the full list. The straightforward
path on a clean machine:

```bash
pip install volare
volare ls-remote --pdk gf180mcu           # find the open_pdks version to install
volare enable --pdk gf180mcu <version-hash>
```

`volare enable` installs into `~/.volare/<variant>` (e.g. `~/.volare/gf180mcuD`)
and the harness finds it there automatically via its built-in search roots —
no environment variables need to be set by hand. This repo's harness was
verified against an install at `~/.volare/gf180mcuD`, open_pdks commit
`c6d73a35f524070e85faff4a6a9eef49553ebc2b` (installed via `volare` prior to
this issue; `volare ls-remote --pdk gf180mcu` will show a newer commit by the
time you read this — any recent one that resolves via `volare enable` works,
the harness pins nothing PDK-version-specific).

If the PDK lives somewhere volare didn't put it (a shared CI cache, a
pre-provisioned container image), point the harness at it directly instead of
relying on the search roots:

```bash
export GF180_PDK_PATH=/path/to/gf180mcuD        # the variant dir, contains libs.tech/
# or the open_pdks / OpenLane convention:
export PDK_ROOT=/path/to/pdk-root
export PDK=gf180mcuD
```

### Verifying the install

```bash
python3 sim/run_corners.py --check-env
```

prints `ngspice : OK ...` and `PDK : OK ...` (with the resolved path and how
it was found) when both are present, or a install hint and a non-zero exit
when something is missing.

```bash
source sim/env.sh
```

is the acceptance check this section promises: run from a clean shell (a
fresh terminal, no pre-set `PDK_ROOT`/`PDK`/`GF180_PDK_PATH`), it must resolve
the PDK and print a line like:

```
gf180mcu: PDK_ROOT=/Users/you/.volare PDK=gf180mcuD
```

If it instead prints `gf180mcu: PDK not found -- run ...`, the PDK is not
installed or not discoverable by any of the resolution steps above — install
it with `volare` as shown, or set `GF180_PDK_PATH`/`PDK_ROOT` to wherever it
actually lives.

### Running the full harness self-test

```bash
bash sim/selftest.sh              # unit tests + a real 45-point PVT smoke run (writes nothing)
bash sim/selftest.sh --record     # also mint a real evidence record under sim/smoke-inverter/records/
```

`sim/selftest.sh` degrades gracefully: if ngspice or the PDK are missing it
still runs the harness's own unit tests (no PDK required) and reports `SKIP`
for the simulation stage rather than failing outright — pass `--require-pdk`
to make that a hard failure instead (useful in CI once ngspice/the PDK are
provisioned there).

## Digital toolchain

Needed to run `verification/` and `flow/` — the cocotb + Icarus testbench
structure and the `klt functional-verification` / `klt synthesize` request
shape, ported from the sibling
[`sky130-modexp`](https://github.com/2AMLogic/sky130-modexp) repository's
`docs/environment.md` (the pattern named in `CLAUDE.md`'s "Harness
bootstrap" section) and re-targeted from the sky130A PDK to gf180mcu.
`verification/records/**/*.md` cite the versions below in each record's
`klt provenance` field; if you re-pin anything here, mint fresh records
rather than editing old ones (see `verification/README.md`'s append-only
rule).

### Provisioning: `scripts/setup-env.sh`

```bash
./scripts/setup-env.sh
```

This creates a local `.venv`, installs `klayout-tools` (`klt`) into it at
the pinned revision below, fetches the pinned `gf180mcu` PDK version via
`volare`, and reports which of `iverilog` / `yosys` / `openroad` are
missing from `$PATH` — with an actionable install pointer for each, never a
traceback. It is safe to re-run; it reuses an existing `.venv` and an
already-fetched PDK version.

Activate the venv for interactive use with:

```bash
source .venv/bin/activate
```

### Pinned versions

| Component | Pinned to | Resolved via |
|---|---|---|
| `klayout-tools` (`klt`) | git revision [`b3e284fff4243cdc5ab59a684d9c0582444b485d`](https://github.com/2AMLogic/klayout-tools/commit/b3e284fff4243cdc5ab59a684d9c0582444b485d) (klt 0.2.0) | `pip install "klayout-tools @ git+https://github.com/2AMLogic/klayout-tools@b3e284fff4243cdc5ab59a684d9c0582444b485d"` (what `scripts/setup-env.sh` runs) |
| `gf180mcu` PDK | `open_pdks` commit `c6d73a35f524070e85faff4a6a9eef49553ebc2b` (variants `gf180mcuA`/`B`/`C`/`D`; the digital harness uses `gf180mcuD`, whose standard-cell libraries are `gf180mcu_fd_sc_mcu7t5v0` / `gf180mcu_fd_sc_mcu9t5v0`) | `volare enable --pdk-root ~/.volare --pdk gf180mcu c6d73a35f524070e85faff4a6a9eef49553ebc2b` |
| `cocotb` | 2.0.1 (pulled in as a `klayout-tools` dependency) | installed alongside `klt` by `scripts/setup-env.sh` |
| Python | <= 3.13 (cocotb 2.0.1 refuses to build on 3.14+) | `scripts/setup-env.sh` auto-selects `python3.13` > `3.12` > `3.11` > `3.10` > `python3`, whichever is the newest compatible interpreter found on `$PATH` |

The `klt` revision is pinned by commit, not by version: klayout-tools has
not cut a PyPI release past `0.2.0`, so a version pin cannot express which
capabilities are present. The current pin was moved forward from
`af5791b5` by issue #25 specifically to pick up the netlist-driven
layout-plan compiler/executor (klayout-tools PR #1158 "Phase C",
`klayout_tools.layout_plan_execute`, plus its follow-up fix #1161) that
`scripts/gen_analog_layout.py` calls — see `layout/README.md`. `npm run
check:ci` was re-run against the new pin before it was committed.

`klt` in turn resolves `iverilog`/`yosys`/`openroad` and the PDK itself from
the host — it does not vendor them. Those are:

| Tool | Used for | Resolved version on the environment these records were produced on |
|---|---|---|
| Icarus Verilog (`iverilog`) | `klt functional-verification` | 12.0 (stable) – 13.0 (stable) verified across two environments (`iverilog -V`) |
| Yosys (`yosys`) | `klt synthesize` | 0.67 – 0.68+post verified across two environments (`yosys -V`) |
| OpenROAD (`openroad`) | `klt place-and-route` | not installed natively on the environments these records were produced on; provisioned via the pinned Docker image instead — see "OpenROAD" below. Exercised by issue #25 (`26Q3-1260-g06a5a02279`, image `openroad/orfs:26Q3-296-gda37dce1c`) |

Package-manager installs for the first two:

```bash
# macOS (Homebrew)
brew install icarus-verilog yosys

# Debian/Ubuntu
apt-get install iverilog yosys
```

### OpenROAD

`openroad` has no Homebrew formula or common-distro package as of this
writing, so it is provisioned via the pinned `openroad/orfs` Docker image
rather than a native install — the same route `sky130-modexp` (this
repo's digital-harness sibling, per `CLAUDE.md`'s "Harness bootstrap")
already uses. `scripts/openroad-docker.sh` (ported from that repo,
re-targeted for gf180mcu — no sky130-specific content, since the image
and invocation shape are PDK-agnostic; `klt place-and-route` resolves the
gf180mcu LEF/liberty deck itself) wraps the pinned
`openroad/orfs:26Q3-296-gda37dce1c` image's `openroad` binary as if it
were native on `$PATH`:

```bash
# one-off invocation
./scripts/openroad-docker.sh -version

# or symlink it onto $PATH so `klt place-and-route` resolves it directly
ln -sf "$(pwd)/scripts/openroad-docker.sh" .venv/bin/openroad
```

Requires `docker` with a reachable daemon. If the invoking user is not in
the host's `docker` group, set `OPENROAD_DOCKER_CMD` to a wrapper — the
script splits it into argv, so a multi-word value works:

```bash
OPENROAD_DOCKER_CMD='sudo -n docker' ./scripts/openroad-docker.sh -version
```

Bind-mounts the repo working
directory and the resolved PDK root (`$PDK_ROOT`, else `~/.ciel`, else
`~/.volare`) at identical absolute host paths inside the container — see
the script's own header comment for why (`klt place-and-route` bakes
absolute host paths into every generated OpenROAD Tcl script). Exercised
end-to-end by issue #25 (`openroad -version` inside the image reports
`26Q3-1260-g06a5a02279`) — see
`verification/records/place-and-route/` for the resulting routed digital
GDS and `flow/README.md` for the request-file flow.

If a native `openroad` binary is preferred instead, roughly in order of
effort:

1. **Precompiled binaries** — see
   [`The-OpenROAD-Project/OpenROAD` § Install](https://github.com/The-OpenROAD-Project/OpenROAD#install)
   for current release artifacts.
2. **Build from source via OpenROAD-flow-scripts** —
   [`The-OpenROAD-Project/OpenROAD-flow-scripts`](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts),
   `./build_openroad.sh --local` (a from-source build with its own toolchain
   dependencies — see that repo's own docs for platform prerequisites).

### `klt`'s gf180mcu PDK resolution

`klt pdk find --pdk gf180mcuD` (or any of the fetched `gf180mcuA`/`B`/`C`
variants) resolves the install root, per-tool asset directories, and
standard-cell libraries via the same `find_pdk()` discovery `klt pdk`/
`klt cells`/`klt synthesize` all share — no repo-specific PDK-fetch
mechanism. `klt pdk cells --pdk gf180mcuD` reports the available digital
standard-cell libraries directly:

```
gf180mcu_fd_sc_mcu7t5v0   (nominal supply 1.8V, corner ..._tt_025C_1v80)
gf180mcu_fd_sc_mcu9t5v0   (nominal supply 1.8V, corner ..._tt_025C_1v80)
```

`flow/request-harness-counter-synth.json` uses
`gf180mcu_fd_sc_mcu9t5v0` / `tt_025C_1v80` — see `flow/README.md`.

### Why local, not CI, for the PDK-heavy legs

Provisioning a real PDK in a hosted CI runner on every PR is a real,
recurring cost. Following `sky130-modexp`'s split: the tool-light leg
(`klt functional-verification`, Icarus/cocotb only, no PDK) is cheap enough
to run anywhere; `klt synthesize`, `klt place-and-route`, `klt drc`, and
the analog layout-plan runner (`scripts/gen_analog_layout.py`, which calls
`klayout_tools.layout_plan_execute` and then `klt drc`) all need the
fetched PDK and are run locally by a contributor with
`scripts/setup-env.sh`'s environment provisioned, with the result committed
as an append-only record under `verification/records/` (see
`verification/README.md`). [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
implements this split: it runs `npm run check:ci` (evidence-record lint +
`klt functional-verification`) on every push/PR to `main`, and does not run
`check:all`'s PDK-heavy `klt synthesize` leg — that stays local, per this
section. If you ever move a PDK-heavy leg into CI, update this section in
the same change rather than letting the two drift.
