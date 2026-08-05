# gf180-usb2-phy — agent instructions

Open-source canary block: a USB 2.0 device PHY on the gf180mcu PDK,
designed and verified by AI agents — a **mixed-signal** block.

- **PDK**: gf180mcu (open PDK).
  Digital: cocotb + Icarus, Yosys, OpenROAD. Analog: xschem + ngspice.
  Layout, DRC, and LVS go through klayout-tools (`klt`).
- **Friction protocol (the canary's job)**: every time klayout-tools is
  awkward, missing a capability, or wrong for what you need, file an issue at
  `2AMLogic/klayout-tools` describing the tool gap generically — that tracker is
  scoped to the tool, so keep design-specific detail (spec values, this repo's
  content) out of it and describe the gap, not the design.
- **Verification is the product**: no claim without a testbench. Recorded
  results are append-only evidence; a result is not superseded by deletion, it
  is superseded by a later record that says why.
- Spec changes go through `spec/` with a decision record. Agents do not relax
  the ratified spec to make a result pass.

## Scope discipline — the thing most likely to go wrong here

This block is scoped deliberately smaller than "a USB 2.0 PHY", and the
narrowing is load-bearing. Three instructions, in the order they are likely to
be violated:

- **Do not build high-speed.** 480 Mbps is *out of scope*, not a stretch goal.
  Full-speed at 12 Mbps is the target. If an architecture decision looks better
  "in case we want HS later," take the full-speed-optimal one instead and
  record the alternative in `spec/`.
- **Do not build the serial interface engine.** This block ends at the UTMI
  boundary. Endpoints, CRC, enumeration, and packet handling belong to whatever
  digital design integrates the PHY. If a testbench needs them, write the
  minimum stub inside `verification/` and say so — do not let a stub grow into
  a controller.
- **Do not inherit `sky130-usb2-phy`'s scope.** That sibling exists, is worth
  reading, and is scoped *broader* — different PDK, host-capable, high-speed as
  a stretch. Copy its harness patterns and its spec reasoning; do not copy its
  boundaries. Where the two differ, this repo's README is right for this repo.

The general rule behind all three: a canary block earns its keep by being
finished and verified, not by being general.

## Harness bootstrap

Copy rather than reinvent, from two siblings, each supplying one half:

- **Analog** — [`gf180-bandgap`](https://github.com/2AMLogic/gf180-bandgap) is
  the most mature block in the fleet and the source for the ngspice PVT-corner
  harness and the append-only evidence-record pattern. Same PDK, so its
  environment setup applies directly.
- **Digital** — [`sky130-modexp`](https://github.com/2AMLogic/sky130-modexp)
  for the cocotb testbench structure and the `klt functional-verification` /
  `klt synthesize` request shape. Different PDK, so take the pattern and not
  the PDK configuration.

See issue #2.

<!-- BEGIN LOOM ORCHESTRATION -->
This repository uses [Loom](https://github.com/rjwalters/loom) for AI-powered development orchestration — see the Loom repository for the full guide (roles, labels, worktrees, configuration). When installed, Loom also writes a locally-substituted copy of that guide to `.loom/CLAUDE.md`.
<!-- END LOOM ORCHESTRATION -->
