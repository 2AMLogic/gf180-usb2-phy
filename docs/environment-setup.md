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
