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
- **Netlist provenance**: schematic — the DUT of every experiment is the
  generated export under `design/netlist/`, not a post-layout extraction.
  There is no **analog** layout, so no extracted re-run exists to compare
  any electrical row against; this is blocked on #52. (The digital half
  does have a committed, DRC-clean, LVS-matched layout, and — as of #51's
  `post-layout-pvt` experiment — a first, partial SPEF-annotated post-layout
  STA re-run: `verification/records/post-layout-pvt/records/20260825-233200-1c84648.md`.
  No row in *this* table is a digital timing row, so that record does not
  change any verdict below; it is cited here only so "post-layout
  re-verification" for the digital half is discoverable from this index.
  That record's own parasitic annotation is incomplete (186/366 design
  nets, root-caused to a `klt sta` net-name-correlation gap filed as
  klayout-tools#1422) — it is not a substitute for a full extracted-netlist
  re-run, only the first honest attempt at one.)

## The table

Record IDs are current **as of this file's last edit**; records are
append-only, so a later re-run mints a new record ID in the same experiment
directory and names the one below in its **Supersedes** field. Trust the
experiment directory, and read its newest record.

| §8.2 row | Verified against | Experiment | Record | Verdict |
|---|---|---|---|---|
| Rise/fall time | §6 (4–20 ns into 50 pF) | `sim/driver-signal-quality/` | `20260817-203552-a408cb6` | **FAIL** — 3/45 corners exceed 20 ns |
| Crossover voltage | §6 (1.3–2.0 V) | `sim/driver-signal-quality/` | `20260817-203552-a408cb6` | **FAIL** — 2/45 corners below 1.3 V |
| Rise/fall matching | §6 (within 10 % of each other) | `sim/driver-signal-quality/` | `20260817-203552-a408cb6` | **FAIL** — 36/45 corners outside ±10 % |
| Full-speed signal quality | §6 rows as a set + monotonic single-zero-crossing transition | `sim/driver-signal-quality/` | `20260817-203552-a408cb6` | **FAIL** on the §6 numeric rows above; the monotonicity/single-crossing half **passes** at 45/45 |
| Driver-output timing jitter | §8.2's own note: no confirmed numeric limit ⇒ engineering data, no spec citation | `sim/driver-jitter/` | `20260817-203915-5a963e7` | **No pass/fail claimed** (see below) — data recorded at 45/45 |
| D+ pull-up tolerance | §5 (1.5 kΩ ±5 %) | `sim/dplus-pullup-tolerance/` | `20260817-203609-a408cb6` | **PASS** 45/45 |
| Receiver thresholds — differential | §4 (\|D+ − D−\| > 200 mV over 0.8–2.5 V common mode) | `sim/diff-receiver-sensitivity/` | `20260817-203852-5a963e7` | **FAIL** — 30/45 corners fail at the 2.5 V common-mode point; 45/45 pass at 0.8 V and 1.65 V |
| Receiver thresholds — single-ended D+ | §4 (VIH > 2.0 V, VIL < 0.8 V) | `sim/se-receiver-dp-thresholds/` | `20260817-203631-a408cb6` | **PASS** 45/45 |
| Receiver thresholds — single-ended D− | §4 (VIH > 2.0 V, VIL < 0.8 V) | `sim/se-receiver-dm-thresholds/` | `20260817-203654-a408cb6` | **PASS** 45/45 |
| DRC / LVS | §8.2 marks this "N/A — layout hygiene, not an electrical spec row" | `layout/digital/` | `verification/records/digital-drc/records/20260825-224815-6a83263.md`; `verification/records/digital-lvs/records/20260825-224930-6a83263.md` | **PASS for the digital half, not attempted for the analog half.** `klt drc` on `layout/digital/usb_utmi_phy.gds` is `clean` / 0 violations; gate-level `klt lvs` against the as-built netlist is `match` / 0 mismatches, with a passing negative control. The five analog blocks have **no committed GDS** (`layout/README.md` § "Analog"), so nothing analog can be checked yet. §11 requires both halves before signoff. |

**No spec limit was relaxed to produce this table.** Four §6/§4 rows fail at
some corners; those are recorded as failures with the offending corner-ids and
measured values, per `CLAUDE.md` ("Agents do not relax the ratified spec to
make a result pass"). The design changes that would fix them are *not* in
scope here — this issue's product is the measurement.

## What each failure actually says

### Rise/fall matching (36/45 corners) — the dominant failure

`t_rise / t_fall` ranges from 0.979 (`sf_125c_3.63v`) to 1.402
(`fs_-40c_2.97v`) against a ratified window of [0.90, 1.10]. The driver's
output stage is a 60 µm PMOS / 30 µm NMOS pair into a fixed ~36 Ω `rm1` series
termination, so its pull-up is systematically weaker than its pull-down once
carrier mobility is accounted for, and the imbalance is amplified by the
skewed process corners (`fs` — fast NMOS, slow PMOS — is the worst, exactly as
the topology predicts; `sf` is the only corner family that lands inside the
window). This is a device-sizing result, not a measurement artifact.

### Rise time > 20 ns (3/45 corners)

`ss_125c_2.97v` (22.33 ns), `fs_125c_2.97v` (20.92 ns) and `ss_125c_3.30v`
(20.79 ns) — slow process, hot, low supply, i.e. the weakest-drive corner of
the matrix. The nominal-corner value is 15.1 ns, so the design has margin at
`tt` and loses it at the corner. The floor of the range (4 ns) is never
approached: the fastest corner is 10.8 ns.

### Crossover voltage < 1.3 V (2/45 corners)

`fs_27c_2.97v` (1.2935 V) and `fs_-40c_2.97v` (1.2968 V), both a few
millivolts under the 1.3 V limit and both on the fast-NMOS/slow-PMOS corner at
the low supply — the same asymmetry the matching failure comes from, seen as a
crossing that sits below mid-rail. Every other corner is comfortably inside
1.3–2.0 V (grid maximum 1.941 V at `sf_-40c_3.63v`).

### Differential receiver at 2.5 V common mode (30/45 corners)

At the 0.8 V and 1.65 V common-mode points the input-referred threshold stays
within −89…−32 mV, comfortably inside the ±200 mV §4 requires. At the 2.5 V
point it degrades to −60…−500 mV (the −500 mV entries are the saturating floor
of the sweep — see that experiment's testbench header — so they mean "at least
this bad"), and at 30 of the 45 corners the receiver still reads a **K** state
(D+ − D− = −200 mV) as a **J**. The mechanism is a systematic offset: the 5T
OTA's output common-mode sits near VDD − |V_GS,p|, well above the trip point of
the CMOS buffer that follows it, and the loop gain available to overcome that
difference collapses as the input common mode approaches the top of the range.
§4's 0.8–2.5 V common-mode range is ratified, so this is a real gap in the
receiver, not a testbench choice.

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
  differential crossing spans **5.36 ns** (`ff_-40c_3.63v` end) to **10.10 ns**
  (`ss_125c_2.97v` end) — a 4.74 ns spread across the 45 corners.
- **Data-dependent jitter within one corner**, over an 18-bit 12 Mbps pattern
  with run lengths 1, 1, 2, 1, 3, 1, 6, 1, 2: peak-to-peak ≤ **2.53 ps**
  consecutive-transition and ≤ **1.33 ps** against the ideal bit grid. At an
  83.33 ns bit time that is ~3 × 10⁻⁵ UI, i.e. negligible — and small enough
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

Gate-level PVT timing closure of that logic (standard-cell timing corners
across the same §8.1 grid) is **not** covered by any record yet; it needs a
synthesized netlist with SDF, which this repo does not produce today. §8.2 does
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
