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

**Just opened, specification phase.** Nothing is designed yet, nothing has been
taped out, and nothing has been measured.

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

Nothing external blocks it; work can start at the specification. A sibling,
[`sky130-usb2-phy`](https://github.com/2AMLogic/sky130-usb2-phy), targets a
different PDK at a broader scope and is itself at specification stage — read it,
but see `CLAUDE.md` on not inheriting its scope.

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

## Target specification (DRAFT — engineering to ratify, see issue #1)

| Parameter | Target | Stretch |
|---|---|---|
| Role | device (peripheral) only | — |
| Signaling rate | full-speed, 12 Mbps | — (high-speed is out of scope, not a stretch) |
| Digital interface | UTMI | UTMI+ subset |
| Supply | 3.3 V | — |
| D+ pull-up | 1.5 kΩ, integrated, enable-controlled | — |
| Driver rise / fall | 4–20 ns into 50 pF, per USB 2.0 §7.3.2 | — |
| Crossover voltage | 1.3–2.0 V | — |
| Reference clock | 12 MHz external, ±0.25% | crystal-less, trimmed from SOF |
| Receiver | differential + two single-ended, with idle/SE0 detect | — |
| Signoff | DRC + LVS clean; eye and timing verified across PVT | — |

Every row is a commitment the verification suite has to be able to check —
which is why high-speed appears as an exclusion rather than an aspiration. The
numbers cited from the USB 2.0 specification are targets to be confirmed
against the specification text during ratification, not transcribed authority.

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
