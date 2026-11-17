# §8.2 coverage — which spec row is substantiated by which record

`spec/usb2-device-phy.md` §8.2 names the quantities every electrical claim
against this block must carry, and §8.1 fixes the 45-corner PVT matrix each of
them must be run over. This file is the **index** from those rows to the
append-only evidence that answers them. It is not the characterization report
(that is issue #27's artifact, and it will aggregate rather than replace this);
it exists so that "does every §8.2 row have a recorded pass/fail?" is a
question with a one-page answer instead of a directory crawl.

Every row below was run over the **full 45-corner matrix** of §8.1 — 5 process
corners (`tt`, `ff`, `ss`, `fs`, `sf`) × 3 temperatures (−40, 27, 125 °C) × 3
supplies (2.97, 3.30, 3.63 V). No subset justification is claimed by any of
these records, because none of them is a subset.

- **PDK**: `gf180mcuD` @ open_pdks `c6d73a35f524070e85faff4a6a9eef49553ebc2b`
- **Simulator**: ngspice-47
- **Netlist provenance** (current state: `layout/README.md` § "Analog"; the dated
  narrative that follows is history): **extracted, as of 2026-11-17 (issue
  #51)** — the DUT of every analog row's current record below is a committed
  parasitic-annotated extraction under `layout/analog/extracted/`, not the
  schematic export. All five blocks are extracted (`klt extract --parasitics`,
  klt 0.9.0, deck `gf180mcu`: the four new blocks in
  `verification/records/analog-extraction/records/20261117-011552-45b284d.md`,
  `differential_receiver` in the prior probe
  `20261115-180500-5279711.md`), each as-written plus a one-line
  port-reordered twin — klt's `.SUBCKT` port order differs from
  `design/netlist/`'s and every testbench instantiates positionally, so the
  as-written netlist either errors the harness leg or returns confidently
  wrong numbers (the trap holds on all four new blocks, re-measured in the
  extraction record). The full 45-corner matrix was re-run per experiment
  against the extracted netlists; each row below cites its extracted record,
  which names the schematic record it supersedes. **What moved:** the
  receiver rows (§4) and the pull-up row (§5) pass post-layout with the
  ratified limits unchanged; the driver §6 timing rows **fail post-layout** —
  trise 27.7–32.1 ns and tfall 28.5–33.0 ns against the 4–20 ns limits, and
  the rise crossover exceeds the 2.0 V ceiling at 15 of 45 corners — root-caused
  in the extraction record to the committed routing's own output-path Metal1
  resistance (~250 Ω series into the 50 pF load; an LVS-level extraction of
  the same stream reproduces the schematic timing, so the devices are not the
  cause). No limit was relaxed to record this; a failing post-layout row is
  a result, not a regression to hide (per #53's "Do not"). The engineering-data
  rows (jitter, disabled leakage, shared-pad bus) were re-run the same way
  with no pass/fail claimed, as before. The digital STA evidence is unchanged:
  `verification/records/post-layout-pvt/records/20261015-011505-32db02a.md`
  (regenerated layout of #131; three liberty corners, parasitics attached with `--def-pins`, 7 unannotated
  and 3 partially unannotated drivers, lumped capacitance with no wire RC
  delay, ideal clock, no lateral coupling; not RC signoff and not the §8.1
  45-corner matrix — see `manifests/README.md` item 5.digital).

  **History (schematic-era state, 2026-08 → 2026-09):** the DUT of every
  experiment in the table was then the generated export under
  `design/netlist/`, not a post-layout extraction; issue #52 closed
  (PR #57, 2026-08-26) without ever committing a GDS/OASIS for any of the
  five analog blocks, and the remaining friction was tracked at
  klayout-tools#1424 (a DRC regression, closed `NOT_PLANNED`/refuted
  2026-08-26 but re-confirmed by issue #61 on 2026-09-05 to still reproduce
  byte-for-byte against the exact commit the refutation's source inspection
  covered). gf180-usb2-phy#56's `dplus_pullup` design decision was resolved
  (operator ruling 2026-09-05, FLATTEN —
  `spec/decisions/0001-dplus-pullup-switch-device-flattening.md`): that
  block's switch devices were drawn one device per gate, `klt` ingested and
  placed it, and the §5 row was re-run against the flattened netlist. It
  then had a committed layout *plan* — but a plan is not a layout:
  `dplus_pullup` routed **6 of 21 nets** and the three receiver plans
  **1 of 8/9/9**, with both supplies and every ladder node unrouted, so
  there was no analog extraction to compare against and issue #53's analog
  acceptance criterion stayed unattempted. The two upstream gaps that held
  the routed-net count down were klayout-tools#1531 and #1467, both open at
  the time; the full per-net evidence is
  `verification/records/analog-layout/records/20260909-215500-29c5780.md`.
  (The digital half has had a committed,
  DRC-clean, LVS-matched layout and, as of issue #53's `post-layout-pvt`
  experiment, a SPEF post-layout STA re-run whose record reported 364/366 design
  nets *name-annotated*:
  `verification/records/post-layout-pvt/records/20260905-182000-80d4593.md`.
  **Name annotation is not attached capacitance.** A later record found the
  same extraction recipe reported full name annotation while OpenSTA applied
  no wire parasitics (`delay_changed: false`); the 364/366 figure was not
  re-checked for attachment.
  That record superseded an earlier, partial attempt
  (`20260825-233200-1c84648.md`, 186/366 nets name-annotated, filed as
  klayout-tools#1422 and fixed by #1423); the later
  record above shows that fix changed name matching, not attached
  capacitance. No row in *this* table is
  a digital timing row, so neither post-layout-pvt record changes any
  verdict below; both are cited here only so "post-layout re-verification"
  for the digital half is discoverable from this index.)

## The table

Record IDs are current **as of this file's last edit**; records are
append-only, so a later re-run mints a new record ID in the same experiment
directory and names the one below in its **Supersedes** field. Trust the
experiment directory, and read its newest record.

| §8.2 row | Verified against | Experiment | Record | Verdict |
|---|---|---|---|---|
| Rise/fall time | §6 (4–20 ns into 50 pF) | `sim/driver-signal-quality/` | `20261117-005434-45b284d` (supersedes `20261104-204550-2d31f87`, the schematic-netlist TXOE record of issue #277; this record's DUT is the committed post-layout extraction, issue #51) | **FAIL** 45/45 post-layout — rise 27.7–32.1 ns, fall 28.5–33.0 ns against the 4–20 ns limits, at every corner. Root cause in `verification/records/analog-extraction/records/20261117-011552-45b284d.md`: the committed routing's output-path Metal1 resistance (~250 Ω series into the 50 pF load; an LVS-level extraction of the same stream reproduces the schematic timing). Schematic verdict kept as history: **PASS** 45/45 — rise 4.04–8.65 ns, fall 4.12–8.77 ns. No limit relaxed. |
| Crossover voltage | §6 (1.3–2.0 V) | `sim/driver-signal-quality/` | `20261117-005434-45b284d` | **FAIL** 29/45 corners post-layout — rise crossing 1.678–2.090 V (above the 2.0 V ceiling at 15 corners), fall crossing 1.265–1.588 V (below the 1.3 V floor at 14 corners); same root cause as the rise/fall row. Schematic verdict kept as history: **PASS** 45/45 — 1.419–1.941 V (record `20261104-204550-2d31f87`) |
| Rise/fall matching | §6 (within 10 % of each other) | `sim/driver-signal-quality/` | `20261117-005434-45b284d` | **PASS** 45/45 post-layout — ratio 0.963–0.983 (the added series R slows both edges nearly equally). Schematic history: **PASS** 45/45 — 0.930–1.068 (`20261104-204550-2d31f87`, the issue #277 fix; [TXOE trf fix comparison note](notes/20261104-txoe-trf-fix-comparison.md)) |
| Full-speed signal quality | §6 rows as a set + monotonic single-zero-crossing transition | `sim/driver-signal-quality/` | `20261117-005434-45b284d` | **FAIL** post-layout — the set fails because the rise/fall and crossover rows above fail; the monotonicity half still passes (`xing_extra_ps` = 0 everywhere) and overshoot/undershoot stay in limit (`dp_over_mv` −3.5 to −0.98, `dp_under_mv` −0.38 to −0.06). Schematic history: **PASS** 45/45 (`20261104-204550-2d31f87`) |
| Driver-output timing jitter | §8.2's own note: no confirmed numeric limit ⇒ engineering data, no spec citation | `sim/driver-jitter/` | `20261117-010413-45b284d` (supersedes `20261104-204926-2d31f87`; DUT is the committed post-layout extraction, issue #51) | **No pass/fail claimed** (see below) — data recorded at 45/45 with TXOE=1 on the extracted netlist: `tprop` 12.38–14.51 ns, grid-pp jitter 350–456 ps, consecutive-pp 700–912 ps (the schematic-era record's sub-ps jitter is not comparable: it measured edge placement at the solver's resolution floor on a ~6 ns edge; the extracted ~29 ns edge resolves real data-dependent spread). Monotonicity control passes (`xings_extra_ps` = 0 everywhere) |
| Driver disabled-state leakage (TXOE=0) | No §6/§8.2 numeric limit: engineering data, no spec limit | `sim/driver-disabled-leakage/` | `20261117-005846-45b284d` (supersedes `20261104-205341-2d31f87`; DUT is the committed post-layout extraction, issue #51) | **No pass/fail claimed** — engineering data, no spec limit; 45/45 points completed on the extracted netlist. Worst release transient 41.7 µA at `ff_125c_2.97v` (host driving 3.3 V into a 2.97 V-supplied cell, over-rail case, same corner as the schematic-era worst); settled SE0-state leakage worst 33.6 nA (`ff_125c_3.63v`) |
| Shared-pad-bus host/device ownership on shared DP/DM | No §6/§8.2 numeric limit: engineering data, no spec limit (integration evidence for the DR-0004 pin contract, `spec/decisions/0004-digital-analog-pin-contract.md`) | `sim/shared-pad-bus/` | `20261117-010802-45b284d` (supersedes `20261106-181119-02e3661`; DUT is the composite of the five committed post-layout extractions, `layout/analog/extracted/shared_pad_dut_extracted.spice`, issue #51) | **No pass/fail claimed** — engineering data, no spec limit; 45/45 points completed post-layout. Reports pad voltages, receiver output levels and pad-crossing-to-output delays on the shared nets; the only checks are a functional-polarity smoke count and a harness-integrity check that the deliberate contention is visible to the current meter. No compliance claim: the pending DR-0004 rulings (§6 high-Z/leakage row; RXD not consumed by the digital side) are not settled here |
| D+ pull-up tolerance | §5 (1.5 kΩ ±5 %) | `sim/dplus-pullup-tolerance/` | `20261117-005250-45b284d` (supersedes `20260905-185112-6bfe679`; DUT is the committed post-layout extraction, issue #51) | **PASS** 45/45 post-layout — best-code error 0.08–2.29 % (worst `ss_125c_3.63v`), effective pull-up 1465.7–1527.8 Ω against 1425–1575 Ω, best trim code 25–31 across the grid; `r_code0` spread 28.5 % (harness integrity check now passes on the full grid). Schematic history: **PASS** 45/45 (`20260905-185112-6bfe679`, the flattened-netlist re-run of issue #56 / DR-0001) |
| Receiver thresholds — differential | §4 (\|D+ − D−\| > 200 mV over 0.8–2.5 V common mode) | `sim/diff-receiver-sensitivity/` | `20261117-013614-7cd74e7` (supersedes `20261008-193113-2e9f63e`; DUT is the committed post-layout extraction of `differential_receiver`, issue #51) | **PASS** — 45/45 corners at each of the 0.8 V, 1.65 V and 2.5 V common-mode points on the extracted netlist; worst input-referred threshold −84.0 mV (`fs_125c_2.97v`, 2.5 V common mode; was −81 mV schematic). Schematic history: **PASS**, worst −81 mV (`20261008-193113-2e9f63e`, the issue #97 sizing fix; the earlier 30/45 failure at 2.5 V retained as history below) |
| Receiver thresholds — single-ended D+ | §4 (VIH > 2.0 V, VIL < 0.8 V) | `sim/se-receiver-dp-thresholds/` | `20261117-004923-45b284d` (supersedes `20260817-203631-a408cb6`; DUT is the committed post-layout extraction, issue #51) | **PASS** 45/45 post-layout — trip point 1.162–1.476 V across the grid, hard rail at both VIL and VIH at every corner. Schematic history: **PASS** 45/45 (`20260817-203631-a408cb6`) |
| Receiver thresholds — single-ended D− | §4 (VIH > 2.0 V, VIL < 0.8 V) | `sim/se-receiver-dm-thresholds/` | `20261117-005048-45b284d` (supersedes `20260817-203654-a408cb6`; DUT is the committed post-layout extraction, issue #51) | **PASS** 45/45 post-layout — trip point 1.162–1.476 V, hard rail at both VIL and VIH at every corner. Schematic history: **PASS** 45/45 (`20260817-203654-a408cb6`) |
| DRC / LVS | §8.2 marks this "N/A — layout hygiene, not an electrical spec row" | `layout/digital/`; `layout/analog/` | `verification/records/digital-drc/records/20260825-224815-6a83263.md`; `verification/records/digital-lvs/records/20260825-224930-6a83263.md`; `verification/records/analog-layout/records/20261116-000742-8dff986.md`; `verification/records/analog-lvs/records/20261115-175000-5279711.md` | **PASS for the digital half. Analog layout delivered and LVS-matched; analog signoff still open.** `klt drc` on `layout/digital/usb_utmi_phy.gds` is `clean` / 0 violations; gate-level `klt lvs` against the as-built netlist is `match` / 0 mismatches, with a passing negative control (the digital rows are cited at their original records; later re-runs are in `verification/records/digital-drc/` and `digital-lvs/`). For analog, the current state is in `layout/README.md` § "Analog" and in the two head records cited at left: **all five** blocks (`differential_driver`, `differential_receiver`, `se_receiver_dm`, `se_receiver_dp`, `dplus_pullup`) have a committed, **fully routed** GDS under `layout/analog/` — 20/20, 8/8, 9/9, 9/9 and 21/21 nets — that `klt drc --deck gf180mcu` reports `clean` / 0 violations on, and transistor-level `klt lvs` against `design/netlist/*.spice` reads `status: "match"` with `error_count: 0` on every one of them, cited as T1 item `4.analog` (issue #247). What is still missing is the analog DRC **coverage attestation**
(#246) only: the **extracted-netlist re-simulation** (#53's analog half) landed on 2026-11-17 under issue #51 — every analog electrical row above now carries a post-layout record cited at left, from the committed extractions under `layout/analog/extracted/` (extraction record `verification/records/analog-extraction/records/20261117-011552-45b284d.md`); the receiver/pull-up rows pass post-layout and the driver §6 rows fail post-layout at the unchanged limits, each row stating both. The analog **ERC** result (#248) has since landed as a structural claim — graded `met` as T1 item `11.analog`, its envelopes carrying `check_status: not_checked`, so not a clean ERC verdict. The LVS run also compared no poly-resistor dimension (`R` excluded as a `placeholder_value`, `L`/`W`/`A`/`P` as `secondary`), so the DR-0010 trim-length deviation is not covered by it. The earlier states this row described are kept as history, not deleted: the DRC-violating receivers (klayout-tools#1424, cleared by the legal-width plan fix, issue #65), the `differential_driver` `rm1` ingestion error and the `dplus_pullup` blocker (issues #56/#70/#72), the incomplete routing and the `differential_receiver` LVS mismatch of `20261009-203500-7a8e831` all live on in `layout/analog/HISTORY.md` and in the superseded records `20260905-200628-80cb14c`, `20260905-190024-525c67c`, `20260921-130120-223bae5` and `20261113-151132-45afbeea4868`. **The driver rows passed the schematic matrix (issue #96); on the extracted netlists the §6 timing rows fail (issue #51) — recorded, not relaxed. The driver layout is committed and LVS-matched (issue #252).** §11 requires both halves before signoff. |

**No spec limit was relaxed to produce this table.** The four driver index
rows (§6: rise/fall time, crossover, rise/fall matching, and the full-speed
signal-quality row that aggregates them) failed in the first record,
`20260817-203552-a408cb6`, and pass at 45/45 in `20261015-104027-d109790`
(issue #96). The ratified §6 limits are unchanged; the fix is a re-size of the
output stage and predriver in `design/differential_driver.sch`. The old
record stays as the evidence of the 60/30 µm design.

**Post-layout status (2026-11-17, issue #51): the same four driver rows fail
again on the extracted netlists** — rise/fall 27.7–33.0 ns against the
4–20 ns limits at all 45 corners, rise crossover above 2.0 V at 15 corners
and fall crossover below 1.3 V at 14 (`20261117-005434-45b284d`). As before,
no limit is relaxed and the failing record stands; the root cause this time
is layout, not sizing — the committed routing's output-path Metal1 series
resistance (~250 Ω into the 50 pF load), per the extraction record's
bisection.

## Driver §6 rows — failure history and the fix (issue #96)

**Current result** (`20261015-104027-d109790`, supersedes
`20260817-203552-a408cb6`): 45/45 corners pass every §6 row, taken through
`klt sim` on the Spot batch fleet (ngspice-46). Rise 4.09–8.78 ns, fall
4.13–8.76 ns, `t_rise/t_fall` 0.944–1.086, crossover 1.405–1.883 V, overshoot
and undershoot ≤ 1.4 mV in magnitude, no extra zero crossings. Nominal
(`tt`/27 °C/3.30 V): rise 5.90 ns, fall 5.86 ns, ratio 1.006, crossover
1.633 V.

**Re-size**: output PMOS `W=60u` → `W=80u m=4`, output NMOS `W=30u` →
`W=30u m=4` (an effective 320u/120u, P:N ≈ 2.7:1 rather than 2:1), predriver
PMOS/NMOS `4u/2u` → `8u/2.5u`. The `rm1` ~36 Ω series termination and the poly
slew resistor are unchanged, so the §6 output resistance is untouched. The
larger output stage cuts the RC at the gate and lets the P:N ratio be tuned
for equal rise and fall.

**Residual risk, not a failure**: the fast corner (`ff`, −40 °C, 3.63 V) has
rise 4.094 ns and fall 4.132 ns, 2.3 % and 3.3 % above the 4 ns floor. That
is a pass, and it is also the thinnest margin in the table; layout parasitics
(none committed) will slow edges, which helps this end and costs margin at
the 20 ns end, where there is a factor of 2.3.

### What was wrong (history, from `20260817-203552-a408cb6`)

**Rise/fall matching, 36/45 corners.** `t_rise / t_fall` ranged from 0.979
(`sf_125c_3.63v`) to 1.402 (`fs_-40c_2.97v`) against a ratified window of
[0.90, 1.10]. The output stage was a 60 µm PMOS / 30 µm NMOS pair into a fixed
~36 Ω `rm1` series termination, so its pull-up was systematically weaker than
its pull-down once carrier mobility is accounted for, and the imbalance was
amplified by the skewed process corners (`fs` was worst, `sf` the only family
inside the window).

**Rise time > 20 ns, 3/45 corners:** `ss_125c_2.97v` (22.33 ns),
`fs_125c_2.97v` (20.92 ns) and `ss_125c_3.30v` (20.79 ns), the weakest-drive
corners of the matrix.

**Crossover < 1.3 V, 2/45 corners:** `fs_27c_2.97v` (1.2935 V) and
`fs_-40c_2.97v` (1.2968 V), the same asymmetry seen as a crossing below
mid-rail.

### Differential receiver at 2.5 V common mode (was 30/45 corners; now 45/45)

**Current result** (`20261008-193113-2e9f63e`, supersedes
`20260817-203852-5a963e7`, issue #97): all three common-mode points pass at
45/45 corners, against the unchanged ±200 mV requirement. Input-referred
threshold: −31.5…−14.5 mV at 0.8 V, −34.9…−16.1 mV at 1.65 V, −81.0…−18.5 mV
at 2.5 V (worst: `fs_125c_2.97v`); output levels are valid logic levels at
±200 mV everywhere. This run was taken through `klt sim` on the Spot batch
fleet (ngspice-46); its threshold is the interpolated `.meas ... WHEN`
crossing, so it is not quantised to the 1 mV sweep step the earlier records'
vector form was.

**What was wrong** (history, from `20260817-203852-5a963e7`): at the 0.8 V and
1.65 V common-mode points the input-referred threshold stayed within
−89…−32 mV, but at 2.5 V it degraded to −60…−500 mV and at 30 of the 45
corners the receiver read a **K** state (D+ − D− = −200 mV) as a **J**. The
original diagnosis (OTA output common mode above the buffer trip point) was
right in effect but the precise mechanism, found in issue #97, is that the
NMOS input pair cannot pull `AMPOUT` below its own tail node
(V_cm − V_GS,n ≈ 1.6 V at 2.5 V common mode), which sits above the old
mid-rail trip point of the first buffer inverter, so a K state never read low.

**Fix**: the first buffer inverter was made deliberately P-heavy
(`MP_B1`/`MN_B1` 8u/4u → 32u/2u), moving its trip point to about 0.65·VDD (2.13 V at tt/27 °C/3.3 V),
which is the OTA's balanced output level (VDD − |V_SG,p| of the diode load)
and tracks it over supply. This was the cheap sizing lever the issue named
first; the complementary-input-pair topology change was not needed. The
single-ended receivers and the spec are untouched.

Records `20261008-191800-f6a4f18` and `20261008-191928-8b1f27c` are 0/45
infrastructure-error records (the fleet runner image's klt predated the
client's request features) kept as append-only evidence of the failed
submissions; they carry no design result.

### Jitter — recorded, deliberately unjudged

§8.2's jitter note is explicit that this repo has no confirmed numeric USB 2.0
source-jitter limits from the physical specification text, forbids inventing
them, and permits `sim/` to "record measured jitter as engineering data without
a spec citation attached" until they are pulled. `sim/driver-jitter/`'s
manifest therefore declares **no** min/max limit on any jitter measurement; its
only check is a spread floor on propagation delay that asserts the corner sweep
actually moved. What the record contains:

- **Edge-to-edge timing variation across the corner set** (which is what the
  §8.2 method column asks for): driver propagation delay to the first
  differential crossing spans **3.02 ns** (`ff_-40c_3.63v` end) to **5.50 ns**
  (`ss_125c_2.97v` end) — a 2.48 ns spread across the 45 corners
  (`20261015-104027-d109790`, the re-sized driver; the superseded record had
  5.36–10.10 ns).
- **Data-dependent jitter within one corner**, over an 18-bit 12 Mbps pattern
  with run lengths 1, 1, 2, 1, 3, 1, 6, 1, 2: peak-to-peak ≤ **0.26 ps**
  consecutive-transition and ≤ **0.16 ps** against the ideal bit grid (the
  superseded record: 2.53 ps and 1.33 ps). At an
  83.33 ns bit time that is ~3 × 10⁻⁶ UI, i.e. negligible — and small enough
  to be at the resolution floor of the transient solver, so it should be read
  as "below the noise of this measurement", not as a precise figure.

The practical reading: the driver contributes essentially no data-dependent
jitter at full speed; what a system would see is the corner-to-corner
propagation-delay spread above, plus the reference-clock tolerance of §7, which
is not this experiment's subject.

## Digital (§2, §3) — where its evidence lives

§8.2's table is entirely analog; the digital UTMI-side logic's verification
floor is set by §11 ("verified by a cocotb testbench, bit-exact against
NRZI/bit-stuffing/SYNC/EOP/line-state behavior") rather than by a PVT row. That
evidence already exists and is not re-derived here:

| §11 digital clause | Record |
|---|---|
| NRZI encode/decode, bit stuffing/destuffing, codec loopback | `verification/records/bit-codec-functional/records/20260816-074908-4e92fcc.md` |
| SYNC detection, EOP detection, line-state decode, top-level UTMI wrapper | `verification/records/utmi-framing-functional/records/20260817-184228-72de176.md` |

Gate-level PVT timing closure of that logic across the same §8.1 grid is
**not** covered: STA exists at three liberty corners only (see the
netlist-provenance note above), and the SDF-annotated gate-level replay was
attempted and blocked (`verification/records/post-layout-functional/` record
`20261015-011506-32db02a`; zero-delay replay 111/111, SDF annotation still rejected, klayout-tools#2885/#2886). §8.2 does
not require it, so it is noted here as a known gap rather than claimed.

## Reproducing any row

```bash
python3 sim/run_corners.py --check-env          # ngspice + gf180mcu PDK present?
python3 sim/run_corners.py driver-signal-quality        # mints a new record
python3 sim/run_corners.py dplus-pullup-tolerance
python3 sim/run_corners.py diff-receiver-sensitivity
python3 sim/run_corners.py se-receiver-dp-thresholds
python3 sim/run_corners.py se-receiver-dm-thresholds
python3 sim/run_corners.py driver-jitter
python3 sim/dplus-pullup-tolerance/analyze_fixed_trim.py   # reads recorded logs
```

Each invocation writes a **new** record; nothing above is ever edited in place
(see `sim/README.md`, "Append-only rule").
