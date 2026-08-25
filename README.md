# gf180-usb2-phy

A USB 2.0 device PHY on the [gf180mcu](https://github.com/google/gf180mcu-pdk) open PDK,
designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools) and the open-source
flow — cocotb + Icarus and Yosys/OpenROAD on the digital side, xschem + ngspice
on the analog side.

It is the piece that sits between a USB connector and a chip's digital logic:
a differential transceiver for the D+/D− pair, the single-ended receivers and
pull-up control that USB uses to signal attachment and speed, and the encoding
and clock recovery needed to turn that wire into a byte stream at a UTMI
interface.

## Status

**Spec ratified; digital half at the DRC/LVS sign-off bar, analog half
simulation-complete with no layout.** Nothing has been taped out and nothing
has been measured on silicon.

| Half | Where it is |
|---|---|
| Digital (UTMI-side logic, §2/§3) | Verified bit-exact by cocotb, synthesized and placed-and-routed against `gf180mcu_fd_sc_mcu9t5v0`, **DRC-clean** and **LVS-matched** — `layout/digital/`, `verification/records/digital-drc/`, `verification/records/digital-lvs/` |
| Analog (driver, receivers, D+ pull-up) | Schematics captured and netlisted for all five blocks with full 45-corner PVT sweeps recorded — but **no layout**, and four spec rows currently fail in simulation. `layout/README.md` § "Analog" and `sim/spec-coverage.md` say exactly which, and why |

Read `sim/spec-coverage.md` for the per-spec-row pass/fail index; it is the
authority, and it records failures rather than hiding them.

**Deliberately narrow, in three directions.** This block is scoped smaller than
"a USB 2.0 PHY" and the scope is the point, not a limitation to be fixed later:

- **Device only.** No host, no OTG, no role switching. This block is always the
  peripheral end of the cable.
- **Full-speed only, 12 Mbps.** High-speed (480 Mbps) is *out of scope*, not a
  stretch goal — it is a substantially harder analog problem and nothing that
  motivates this block needs it.
- **Up to the UTMI boundary, and no further.** The serial interface engine
  above it — endpoints, CRC, enumeration, packet handling — is ordinary digital
  logic belonging to whatever chip integrates this PHY. It is not part of this
  block.

A sibling, [`sky130-usb2-phy`](https://github.com/2AMLogic/sky130-usb2-phy),
targets a different PDK at a broader scope — read it, but see `CLAUDE.md` on
not inheriting its scope.

USB-IF compliance certification is out of scope. Meeting the electrical
requirements in simulation is in scope; a certificate is a different kind of
artifact and this repo does not claim one.

## Built agent-native

Every specification, decision record, testbench, and line of documentation in
this repo is produced by AI agents working from a ratified spec and an
append-only evidence trail — not human-authored work that agents merely
assisted with. Verification is the product: every claim traces to a recorded
result. Where the agents hit friction with the open-source tooling — most often
[klayout-tools](https://github.com/2AMLogic/klayout-tools) — that friction gets
filed as a public issue against the tool itself, so the fix benefits everyone
using gf180mcu, not just this repo.

## Target specification

**Ratified 2026-08-10** — see [`spec/usb2-device-phy.md`](spec/usb2-device-phy.md)
for the full specification: the UTMI boundary (what is inside this block vs.
the integrator's serial interface engine), the digital interface, D+ pull-up,
driver characteristics, reference clock, receiver set, the fixed PVT corner
list, and the decision log behind each row that changed from the earlier
draft.

## Chipalooza

[`docs/chipalooza/challenge-5-proposal.md`](docs/chipalooza/challenge-5-proposal.md)
— this block written up against the Open Circuit Design **Chipalooza
Challenge #5** brief (GF180MCU / Wafer.Space): block type, an I/O list mapped
to the slot budget (including why D+/D− must be dedicated pads and cannot ride
a shared multiplexed analog line), the UTMI boundary statement, a spec table
whose every row is re-derived from `sim/` and `verification/` with a met/unmet
verdict at both the 3.3 V and 5.0 V rails, and a bench test plan. No spec row
is relaxed to make it pass — four of them are recorded as unmet.

## Repo layout

```
design/        schematics (xschem)
flow/          synthesis + place-and-route (Yosys, OpenROAD)
layout/        GDS + DRC/LVS reports (klayout-tools driven)
measurements/  silicon characterization (empty until tape-out)
rtl/           Verilog sources
sim/           analog testbenches + PVT corner results
spec/          ratified spec + decision records
verification/  cocotb testbenches
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
