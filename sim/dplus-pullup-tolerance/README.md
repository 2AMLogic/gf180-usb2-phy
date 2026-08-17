# dplus-pullup-tolerance — the ±5 % pull-up row, and the harder question behind it

Substantiates `spec/usb2-device-phy.md` §5 (D+ pull-up: 1.5 kΩ nominal, ±5 %
tolerance across the full PVT envelope) and the §8.2 row "D+ pull-up
tolerance". See `sim/spec-coverage.md` for how this fits the rest of §8.2.

## Two questions, not one

The corner runner can only ask a **per-corner** question, because each PVT
point is an independent simulation:

> at this corner, is there a trim code inside 1.425–1.575 kΩ?

Record `20260817-203609-a408cb6` answers that, PASS at 45/45, worst-case
best-code error **2.01 %** (`ss_-40c_2.97v`). But that is a necessary, not a
sufficient, reading of §5. §5's mechanism is "a binary-weighted trim ladder set
**at test**" — one code is burned into a die at the tester's ambient and
supply, and then has to hold ±5 % over the whole temperature and supply
envelope. A per-corner result would still pass if the winning code changed from
corner to corner, which no real part can do.

`analyze_fixed_trim.py` closes that gap from the *same* evidence, with no
re-simulation: the corner logs already contain the full 32-code resistance
table at each of the 45 points (`print rvec` in the manifest's `derive`), so it
picks the best code at 27 °C / 3.30 V per process corner, holds it fixed, and
reads it back at all nine (T, V) points of that corner.

```
$ python3 sim/dplus-pullup-tolerance/analyze_fixed_trim.py
record   : 20260817-203609-a408cb6
logs     : 45 corner(s) under sim/dplus-pullup-tolerance/corners/20260817-203609-a408cb6/
criterion: one trim code chosen at 27 °C / 3.30 V, held across
           that process corner's whole (T, V) grid, must stay inside ±5 % of 1500 Ω (spec §5)

process    code     R@cal Ω       min Ω       max Ω   worst %  verdict
----------------------------------------------------------------------
ff            7      1500.4      1487.4      1520.7      1.38  PASS
fs           19      1488.1      1475.4      1508.2      1.64  PASS
sf           19      1485.2      1472.4      1505.3      1.84  PASS
ss           26      1509.9      1497.3      1530.1      2.01  PASS
tt           19      1486.6      1473.8      1506.7      1.74  PASS

Overall: PASS -- a single per-die trim code holds ±5 % over the temperature and supply axes of spec §8.1.
```

So the row passes on both readings, with roughly 3 % of margin against the ±5 %
window on the stricter one.

## What the numbers imply about the design

- Untrimmed, the effective pull-up spans **1722 Ω** (`ff_125c_3.63v`) to
  **2572 Ω** (`ss_-40c_2.97v`) — a ±20 % spread around its own mean, which is
  exactly the situation §5 predicted when it said a bare untrimmed gf180mcu
  poly resistor could not hold ±5 %.
- The ladder's average step is **3.08–3.38 %** of the minimum code. That is
  comfortably finer than the ±5 % window, so landing inside is design rather
  than luck, but it is not lavish: the worst-case quantization error alone is
  about ±1.7 %, and the measured worst-case (2.01 %) is close to that, meaning
  quantization — not drift — dominates the error budget.
- Codes actually used span 7 (`ff`) to 26 (`ss`), i.e. about 60 % of the
  ladder's 32-code range, so the ladder is neither running out of range nor
  mostly wasted.

## Caveats a reader should carry

- **VPU_REG is tied to the swept supply.** §5 calls for an internally regulated
  3.0–3.6 V pull-up rail, but no regulator has been designed
  (`design/` has no regulator schematic), so the testbench exposes the pull-up
  to the whole ±10 % supply excursion instead. This is conservative — a real
  regulator narrows the excursion — so the recorded numbers bound the regulated
  case rather than flattering it.
- **Schematic-level, not extracted.** Layout parasitics (poly contact and metal
  routing resistance in series with the ladder) will shift the absolute value
  and are not in this record. They shift it *up*, which the trim ladder has
  range to absorb, but that claim needs its own post-layout record before it is
  evidence.
- **Mismatch is not modelled.** These are nominal-corner device models with no
  Monte Carlo. §8.2 asks for a corner-matrix claim here, not a distribution
  claim, so that is in scope — but the ±5 % row for a *trimmed* resistor is
  ultimately a per-die statement, and a mismatch/Monte-Carlo record would be
  the natural next piece of evidence.
