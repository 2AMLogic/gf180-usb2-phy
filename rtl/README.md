# rtl

Verilog sources.

- `harness_counter.v` — a plain, parameterized (`WIDTH`, default 8) up
  counter with a synchronous active-low reset and a count-enable. **This is
  a throwaway smoke-test vehicle for the digital cocotb + `klt` harness
  bootstrapped by issue #7 — it has zero USB semantics** (no NRZI, no bit
  stuffing, no SYNC/EOP, nothing UTMI-boundary-shaped) and is not part of
  the PHY. It exists only to prove that `verification/` (cocotb + Icarus)
  and `flow/` (`klt synthesize` against gf180mcu) elaborate, simulate, and
  synthesize a real design end-to-end. Real PHY digital logic — NRZI
  encode/decode, bit stuffing/destuffing, SYNC/EOP handling, per
  `spec/usb2-device-phy.md` §2 — is future work and does not belong in this
  file; see `CLAUDE.md`'s scope-discipline rule.
