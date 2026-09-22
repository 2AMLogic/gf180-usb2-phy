# DR-0002 — Vendor the shared USB protocol RTL from sky130-usb2-phy and adapt the wrapper to the canonical interfaces

- **Status**: Accepted
- **Date**: 2026-09-21
- **Decided by**: Builder agent, issue #84, executing the contract the
  master's DR-0002 Decision 6 assigns this repo
  ([sky130-usb2-phy#80, merged as
  `4f3b2c72f16672acd0227c788be1db01d41a3e96`](https://github.com/2AMLogic/sky130-usb2-phy/pull/80))
- **Affects**: `rtl/common/` (new, four vendored files), `reuse.lock.json`
  (new), `scripts/reuse-check.py` (new, copied from 2am),
  `rtl/usb_utmi_phy.v` (interface adaptation), the deleted
  `rtl/usb_nrzi_encoder.v` / `rtl/usb_nrzi_decoder.v` /
  `rtl/usb_bit_stuffer.v` / `rtl/usb_bit_destuffer.v`, every
  `verification/` testbench and request that drove the four modules,
  `flow/request-usb-utmi-phy-synth.json`, `rtl/README.md`,
  `verification/README.md`, `flow/README.md`, `.github/workflows/ci.yml`,
  `package.json`
- **Does not change**: the ratified spec. `spec/usb2-device-phy.md` §2/§3's
  block list, port set, and 12 MHz single-clock architecture are untouched;
  the four transforms' USB-visible behaviour (NRZI over J/K, stuff after
  six 1s, §7.1.9 flush) is byte-identical to what this repo's own suites
  verified before. This record documents **where the shared bytes live and
  how the wrapper talks to them**, not a relaxation of any ratified value.

## Context

`2AMLogic/2am#899` ratified cross-cutting rule 9 (`REUSE.md` @
`9032d1d`): shared PDK-independent RTL has **one master and stamped
copies**. sky130-usb2-phy#79 (master side, closed by PR #80 merged as
`4f3b2c72f16672acd0227c788be1db01d41a3e96`) classified both repos' `rtl/`
inventories and declared its own interfaces canonical (its DR-0002
Decision 3), on the ratified grounds that they are the natural shape of
its DR-0001 architecture (strobed bit-times, `bypass` from `OpMode 2'b10`,
`bit_is_jk` gating, SOP..EOP `enable`). Issue #84 — this record's issue —
is the consumer-side half the master's Decision 6 restates as this repo's
contract: vendor the four files byte-exact under `rtl/common/`, pin them
with a root `reuse.lock.json`, run a copy of 2am's `reuse-check.py` in CI,
and adapt **at this repo's boundary** (`usb_utmi_phy.v` and the
testbenches), never by editing the vendored bytes.

Why adapt here rather than keep the local interfaces: the master is master
by REUSE.md tie-break 2 (*precedence* — its four modules were committed
2026-08-07/08, this repo's 2026-08-17; re-verified during this issue, and
note tie-break 1 *lineage* does not apply: neither repo's `2am`
`repos.yml` entry carries `ported_from` — this repo's harness was
bootstrapped from `sky130-modexp`, not from sky130-usb2-phy). Keeping two
divergent interfaces for the same spec-defined transforms is exactly the
gap #76/#899 measured; the first consumer lock in the fleet lands here.

## Decision

### Decision 1 — Vendor the four shared modules byte-exact, pinned

`rtl/common/{usb_nrzi_encoder,usb_nrzi_decoder,usb_bit_stuffer,usb_bit_destuffer}.v`
are byte-exact copies of `2AMLogic/sky130-usb2-phy` at commit
`4f3b2c72f16672acd0227c788be1db01d41a3e96` (upstream `rtl/<m>.v` → local
`rtl/common/<m>.v`, REUSE.md's own worked-example mapping). The root
`reuse.lock.json` pins that commit with per-file SHA-256s computed from
it; `scripts/reuse-check.py` (a verbatim copy of 2am's checker at
`9032d1d`, provenance-stamped in its header) validates the stamps in CI.
No `diverged:` entries: any future divergence requires a superseding
record here and defeats the one-master rule this vendoring exists to
enforce. The old same-named modules under `rtl/` are **deleted** —
superseded by the vendored copies, not kept as fallbacks.

### Decision 2 — The interface adaptation mapping (per module)

The vendored bytes never change, so `rtl/usb_utmi_phy.v` adapts. The
mapping, module by module (canonical port lists are in the master's
DR-0002 Decision 3 and are visible in the vendored headers):

| Local (deleted) | Canonical (vendored) | Boundary adaptation in `usb_utmi_phy.v` |
|---|---|---|
| `init`/`data_valid`/`data_bit` → `line_valid`/`line_bit` (12 MHz valid-strobe) | `bit_stb`/`bypass`/`sof`/`bit_in` → `level_out` (+ `clk`, `rst_n`) | The TX state machine (now the canonical framer shape: IDLE→SYNC→DATA→FLUSH→HOLD→EOP0/EOP1/EOPJ) issues a strobed bit-time per clock; `sof` on the packet's first bit re-derives the idle-J reference; `bypass` from `OpMode == 2'b10` (raw body bits only — SYNC stays framed); `level_out` drives the pads through a combinational mux, so each consumed bit gets exactly one wire clock and TX_HOLD owes the last bit its visible clock before EOP. |
| `init`/`line_valid`/`line_bit` → `data_valid`/`data_bit` | `bit_strobe`/`bit_level`/`bit_is_jk` → `data_strobe`/`data_bit` (+ `clk_144`, `rst_144_n`) | Strobed on every genuine J/K sample from the line-state decode; **`bit_is_jk` derives from that same decode** (low during SE0/SE1 by construction), so EOP and bus-reset cells never decode as data. The canonical module has no `init`, which matches this repo's documented free-run RX — the old wrapper already never re-initialized the decoder mid-packet. |
| `init`/`in_valid`/`in_ready` → `out_valid`/`out_bit`/`out_stuffed` (ready/valid) | `bit_stb`/`bypass`/`sof`/`bit_in` → `bit_out`/`consume`/`stuff_pending_after` (+ `clk`, `rst_n`) | Back-pressure inverts: the byte shifter advances on `consume == 1` and re-presents the same bit otherwise. The old flush idiom (one clock of `in_valid` while `in_ready` is low) is replaced by the `stuff_pending_after` lookahead: a last consumed bit with the lookahead high spends one TX_FLUSH bit-time on the forced §7.1.9 trailing stuff bit before TX_HOLD and EOP. `sof` on the first post-SYNC bit starts the run counter fresh (see Decision 3). |
| `init`/`in_valid`/`in_bit` → `out_valid`/`out_bit`/`stuff_err` | `enable`/`data_strobe`/`data_bit` → `bit_valid`/`out_bit`/`stuff_err` (+ `clk_144`, `rst_144_n`) | `enable` = the wrapper's `rx_receiving` (armed from `usb_sync_detector.sync_next` one clock before the first post-SYNC bit reaches the destuffer) — the SOP..EOP gate replacing the old `init` packet-start clear. While low the destuffer is transparent (SYNC search shape) and its run counter holds at zero, so idle can never raise a false stuff error; EOP dropping `rx_receiving` zeroes the counter for the next packet. Byte assembly gates on `rx_receiving` so the transparent SYNC bits are never assembled. `stuff_err` semantics are unchanged (seven consecutive 1s). |

### Decision 3 — Stuffing scope follows the master: SYNC never reaches the stuffer

The pre-vendoring wrapper ran SYNC **through** the stuffer (run count
carrying from SYNC's trailing 1 into the PID field). The canonical
architecture runs SYNC **around** it: the encoder is strobed with the SYNC
pattern directly, and the stuffer's `sof` (first byte, bit 0 of TX_DATA)
starts the run counter fresh at the first post-SYNC bit — matching USB
2.0 §7.1.9's scope (stuffing covers PID..CRC) and both repos' golden
models. This is observable only for a payload opening with a run of 1s
(a stuff after the sixth payload one, not after five); it is pinned by
`test_loopback_leading_ones_payload_canonical_stuff_scope`, and the
wrapper testbench's `_expected_wire_dpdm` model encodes the canonical
scope. Not a spec relaxation: spec §2 fixes the ordering
(stuff→NRZI on TX), not the run-counter's initial condition, and the
master's scope is the one both golden models now share.

### Decision 4 — Local dispositions (the ledger entries the master's Decision 5 assigns here)

- **`rtl/usb_utmi_phy.v`** — **kept, in-tree, by tier rule**: it is this
  repo's integration top (the counterpart of the master's
  `usb_utmi_top.v`/`usb_tx_serializer.v`/`usb_rx_path.v` integration
  tier), which the master's own DR-0002 Decision 2 classifies as
  integration/consumer architecture, not shared protocol logic. Since
  this issue it additionally carries the interface adaptation of
  Decision 2 — the single place the canonical interfaces meet this repo's
  12 MHz, no-oversampling, registered-LineState architecture.
- **`rtl/harness_counter.v`** — **kept, in-tree, as harness mechanics**
  under rule 9's widening: it is a throwaway smoke-test vehicle with zero
  USB semantics (rtl/README.md's own words), exists only to prove the
  cocotb/Icarus + `klt` harness end-to-end, and therefore shares nothing
  with any sibling. Not vendorable, not a candidate.
- Not recorded as lock `in_tree` entries: that ledger is scoped to
  same-PDK siblings ("every block this repo designs itself although a
  same-PDK sibling builds one"), and sky130-usb2-phy is a different PDK —
  the cross-PDK shared surface (PDK-independent protocol RTL) is exactly
  what the `imports` entry of Decision 1 pins instead. The three
  architecture-bound functional pairs (sync detection, line-state
  reporting, EOP detection) stay local per the master's DR-0002
  Decision 4 and need no ledger entry of either kind: they are not
  same-name modules and not shared.

### Decision 5 — Clocking vocabulary: `clk_144` is a name, not a frequency

Two vendored modules name their clock/reset ports `clk_144`/`rst_144_n`
— the master's 144 MHz oversampling domain, which this repo does not
have (spec §3: one bit per 12 MHz interface clock, no oversampling). The
wrapper instantiates them on the interface clock with the strobes
asserted on every active clock; nothing in the transforms depends on the
12× relationship (that ratio lives in the master's `usb_bit_sync.v`,
which is architecture-bound and not vendored). Recorded here so the next
reader does not "fix" the port names — renaming would break the byte
stamps. The vendored modules take an asynchronous active-low reset (the
master's style); the local modules keep synchronous resets; the wrapper
feeds all of them the same `int_rst_n`.

### Decision 6 — Verification re-derived against the canonical interfaces

Every testbench that drove a deleted module is rewritten against its
canonical interface (the per-module suites, the loopback harness — now
the minimal canonical caller, discharging the flush duty itself — and
the wrapper suite's wire model). All suites re-run green with new
append-only records (`verification/records/`); the old records bind to
the deleted netlists and stand as history. `scripts/reuse-check.py` runs
in CI beside `check:ci` (per-repo mode: no network, no sibling
checkout), and `klt synthesize` re-runs against the updated source list.

## Alternatives considered

- **Keep the local interfaces and record `diverged:` entries** — rejected:
  a divergence entry is for a *kept behavioural difference*, and there is
  none worth keeping — the interfaces differ only in handshake shape, and
  maintaining a private shape for spec-defined transforms re-creates the
  divergence #76 measured. REUSE.md's contract for a consumer is
  byte-exact vendoring plus boundary adaptation.
- **Adopt by re-implementing the canonical interfaces locally** — rejected:
  that keeps two implementations of the same spec text, which is the
  exact gap rule 9 exists to close; only vendored bytes make divergence
  structurally detectable.
- **Vendoring the sync/line-state/EOP modules too** — rejected by the
  master's DR-0002 Decision 4 (architecture-bound functional pairs); this
  record concurs: this repo's no-oversampling, decoded-bit-stream,
  registered-LineState shapes are its own ratified architecture
  (spec §2/§3), not the master's oversampling recovery.

## Consequences

- The four shared transforms now have exactly one implementation in the
  fleet's USB repos, master-side; this repo's copies are stamped, and any
  future local edit is a CI failure rather than a silent divergence.
- `usb_utmi_phy.v` (and only it) owns the interface adaptation; upstream
  interface changes now carry a real adaptation cost here — the master's
  DR-0002 Consequences section already commits it to treating these
  interfaces as a downstream surface.
- One latent second-packet defect in the master's own framer pattern was
  found and corrected at this boundary: the entering edge encodes SYNC
  bit 0 from `sync_idx`'s pre-edge value, which the master's
  `usb_tx_framer.v` leaves at 7 after a packet — encoding SYNC_BYTE[7]
  (a 1) as bit 0 of every packet after the first and corrupting the SYNC
  pattern (unreachable in its single-packet-per-reset testbench). This
  wrapper re-arms `sync_idx` to 0 when SYNC exits; pinned by
  `test_loopback_back_to_back_packets_minimal_gap`. Worth an upstream
  note to the master when it next touches its framer.
- Master-side bug fixes in the four modules arrive by re-vendoring:
  bump the lock's `commit`, re-copy, re-pin the SHA-256s, re-run the
  suites, append the records.
- The wrapper's UTMI port set, wire-level behaviour (KJKJKJKK SYNC,
  SE0,SE0,J EOP, §7.1.9 flush), and RX-visible semantics (`RxActive`
  arming, `RxError` on seven consecutive 1s) are unchanged — re-verified,
  not assumed, by the re-run suites.

## References

- Issue #84 (this reconciliation), #76 (measured the divergence), #31/#32
  (built the deleted local modules and the wrapper).
- sky130-usb2-phy #79 / PR #80 (master side, merged as
  `4f3b2c72f16672acd0227c788be1db01d41a3e96`) and its
  `spec/decision-records/0002-shared-protocol-rtl-master-and-interfaces.md`
  (master verdict, canonical interfaces, functional pairs, this repo's
  assigned ledger entries).
- `2AMLogic/2am#899`; `2AMLogic/2am` `REUSE.md` rule 9 @ `9032d1d`
  (lock/vendoring contract, master tie-breaks, worked example) and
  `scripts/reuse-check.py` @ `9032d1d` (the checker copy).
- USB 2.0 Specification Rev 2.0 §7.1.9 (NRZI, bit stuffing, the
  stuff-bit-before-EOP duty).
