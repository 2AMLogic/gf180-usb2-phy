# DR-0006 — UTMI `Reset` reaches the vendored RX transforms synchronously

- **Status**: Accepted (wrapper-internal implementation decision; no spec
  row changes)
- **Date**: 2026-10-10
- **Raised by**: Builder agent, issue #132
- **Amends**: DR-0002 Decision 5's last sentence ("the wrapper feeds all of
  them the same `int_rst_n`") for the two RX transforms, and DR-0005
  Decision 3 ("RX is unchanged ... not decided here"). DR-0002 and DR-0005
  are left unedited as history. This record is the current statement for
  RX. DR-0005 stays current for TX.
- **Does not change**: the ratified spec, the UTMI port set, the vendored
  bytes under `rtl/common/` (`reuse.lock.json` stamps unchanged), any TX
  behaviour, power-on `rst_n` behaviour, or the full-speed-only,
  device-only, UTMI-boundary-only scope.

## Context

After #130 (DR-0005), `rtl/usb_utmi_phy.v` still fed
`int_rst_n = rst_n & ~Reset` to the asynchronous reset port of the two
vendored RX transforms, `usb_nrzi_decoder` and `usb_bit_destuffer`. Both
use `always @(posedge clk_144 or negedge rst_144_n)`. So a link-driven
signal that is synchronous to the interface clock asserted and released an
asynchronous reset. No UTMI output is a combinational function of those
two modules' state (`RxActive`, `RxValid`, `RxError`, `DataIn` and
`LineState` are all wrapper registers), so there was no port glitch of the
kind DR-0005 fixed on TX. The release, however, was a reset
recovery/removal timing arc that the physical flow neither constrains nor
checks. `flow/request-usb-utmi-phy-sta*.json` declare only the clock port
and period.

Issue #132 asked which to do: make `Reset` reach the RX transforms
synchronously, or keep the asynchronous path and prove it safe with a
recovery/removal check.

## Analysis: required state versus observable behaviour

The RX pipeline, cell by cell. A cell sampled at edge t reaches
`line_state` at t, the decoder output at t+1, the destuffer output and
`sync_next` at t+2, and `RxValid`/`RxError` at t+3.

| Stage | Former reset (async, `int_rst_n`) | Who sees it |
|---|---|---|
| `usb_line_state_decode` | sync, loads J | decoder input |
| `usb_nrzi_decoder` | async: `prev_level`=1 (J), `data_strobe`=0, `data_bit`=0 | sync search, destuffer |
| `usb_sync_detector` | sync, `match`=0 | `sync_next` -> `rx_receiving` |
| `usb_bit_destuffer` | async: `ones_run`=0, `bit_valid`=0, `out_bit`=0, `stuff_err`=0 | byte assembly, `RxError` |
| `usb_eop_detector`, `rx_receiving`, `rx_assembly_en`, `rx_shift`/`rx_bitcnt`/`RxValid`, `RxError` | sync | ports |

What has to be true at the release edge (the first edge that samples
`Reset` low) is:

1. **NRZI reference.** The decoder's `prev_level` is idle J. On the
   release edge the decoder strobes the line-state register's reset value
   (J), so `prev_level` is J after that edge whatever it was before. What
   depends on the earlier value is the bit decoded on that edge, which is
   `J == prev_level`. With the reference at J that bit is a 1, the same as
   idle. With the reference left at a pre-reset K it is a 0. A 0
   immediately ahead of a SYNC whose first K is sampled on the release
   edge pushes the SYNC search off by one, and the packet is lost.
2. **Nothing stale reaches the SYNC search or the destuffer** on the
   release edge. Under the old asynchronous reset the decoder's
   `data_strobe` was 0 there.
3. **The destuffer** has a zero run, no forwarded bit and no error after
   every reset edge.
4. **Nothing at the ports** changes between edges. The edge that samples
   `Reset` high suppresses any byte or error the pipeline was about to
   deliver.

Item 4 already held under the asynchronous reset, because every port is a
wrapper register with a synchronous reset. Items 1 to 3 describe internal
state. The ports see item 1 only in the corner described above. Items 2
and 3 are not visible at the ports at all (see the evidence).

## Decision

1. **The vendored RX transforms' asynchronous reset port takes `rst_n`
   only.** `usb_nrzi_decoder` and `usb_bit_destuffer` keep their
   power-on asynchronous reset, as before. UTMI `Reset` no longer reaches
   an asynchronous reset pin anywhere in this block.
2. **UTMI `Reset` reaches them through canonical inputs on the sampling
   edge** (wrapper-only, `rx_clear = !int_rst_n`):
   - **Decoder.** While `rx_clear` is high, `bit_strobe`, `bit_is_jk` and
     `bit_level` are forced high. Each reset edge decodes a J sample, which
     loads `prev_level` = J (item 1). The decoder module cannot give
     `prev_level` = J and `data_strobe` = 0 from the same edge, because the
     strobe that loads the reference also sets `data_strobe`. So:
   - **`rx_dec_mask`** is one new wrapper flop, `rx_dec_mask <= rx_clear`.
     It is high for exactly the one clock after an edge that sampled
     `int_rst_n` low. While it is high, the decoder's strobe is hidden from
     the SYNC search and the destuffer (`rx_dec_strobe = dec_data_strobe &&
     !rx_dec_mask`), which gives item 2. From the release edge onward the
     decoder's `prev_level`, `data_strobe` and `data_bit`, as seen
     downstream, match the old asynchronous behaviour cycle for cycle. This
     is not a registered copy of `Reset` driving a reset: it adds no
     release latency, and it suppresses only the strobe the old reset
     would also have produced as 0.
   - **Destuffer.** `enable` and `data_strobe` are forced low while
     `rx_clear` is high. With `enable` low the run counter is zeroed. With
     `data_strobe` low the transparent idle branch forwards nothing, so
     `bit_valid` is 0. `stuff_err` clears by its own default (item 3).
     `out_bit` holds instead of clearing. It is read only together with
     `bit_valid` (byte assembly), so the difference cannot be seen.
3. **The release edge is ordinary.** Nothing is held across it. A SYNC
   whose first K is the cell the release edge samples is received, and the
   first PID bit is neither dropped nor mis-decoded.

Every override is a data-input path sampled on the clock edge. An
asynchronous `Reset` assert or release therefore produces no
recovery/removal arc from the `Reset` input. Instead `Reset` has ordinary
setup/hold paths into the decoder, destuffer and `rx_dec_mask` flops, the
same kind of path it already had into every wrapper register.

## Evidence

Functional (RTL, pinned klt `0.5.0+ge8ca621a6961`, Icarus 13.0, cocotb
2.0.1). Record:
`verification/records/utmi-framing-functional/records/20261010-052224-9847dbc.md`.

- `verification/test_usb_utmi_phy.py` gains 52 RX reset cases (40
  edge-timed abort/release, 8 release-straight-into-SYNC, 4
  unsampled-pulse probes). The suite passes 105/105 on this RTL, both with
  RTL whitebox reads and ports-only.
- The same suite on the previous asynchronous RTL (`origin/main`
  `9847dbc`) passes 101/105. All 48 UTMI-legal edge-timed and
  straight-into-SYNC cases pass. The 4 failures are exactly the
  unsampled-pulse probes: a `Reset` pulse between edges clears the
  decoder's reference and in-flight bit and the destuffer's run, which
  corrupts or loses the packet in flight. This is the port-level
  difference between the two implementations, and it is a structural
  probe, not a UTMI-legal stimulus.
- Sensitivity (temporary RTL mutations, each reverted after its run):

  | Mutation | Whitebox run | Ports-only run |
  |---|---|---|
  | no `rx_dec_mask` | 65/105 | 105/105 |
  | decoder `bit_level` not forced | 96/105 | 104/105 |
  | decoder not forced at all | 96/105 | 104/105 |
  | destuffer `enable` not forced | 81/105 | 105/105 |
  | destuffer `data_strobe` not forced | 65/105 | 105/105 |
  | neither destuffer input forced | 69/105 | 105/105 |

  The single ports-only failure for the decoder mutations is
  `test_rx_utmi_reset_release_straight_into_sync` with K before reset,
  one reset clock and SYNC starting on the release edge (item 1).
- The RX clock-tolerance and RX sync-candidate characterizations never
  assert `Reset`. Re-run on this RTL, they reproduce their committed
  matrices byte for byte. See the carry-forward records in the same
  experiment directory.

## Coverage limits, recorded honestly

- **The mask and the destuffer clears are not visible at the ports.** A
  stray decoder strobe on the release edge is always followed by the 1
  decoded from the line-state register's J. That 1 returns the SYNC search
  to `match` = 0, and while reception is inactive the destuffer's
  `bit_valid` and run are ignored. Whatever these overrides leave behind
  cannot reach `RxActive`/`RxValid`/`RxError`/`DataIn`. They keep "Reset
  clears the RX transforms" true internally, and the RTL whitebox checks
  in the edge-timed test pin them. They are not what makes the ports
  correct. DR-0005 records the same limit for TX.
- **No physical timing claim.** No STA, recovery/removal or
  synthesized-netlist result was produced for this RTL. The committed
  routed netlist and layout (`layout/digital/`) predate this change and
  still contain the asynchronous RX path, as well as the TX path DR-0005
  removed. Replaying the updated suite on that netlist at zero delay
  fails the 4 unsampled-pulse probes as expected (record
  `verification/records/post-layout-functional/records/20261010-052227-9847dbc.md`).
  Re-synthesis, place-and-route, signoff and the post-layout records are
  #131's scope.
- **Remaining asynchronous arcs.** The block's own power-on `rst_n` still
  drives the asynchronous reset of all four vendored transforms, and its
  release is a recovery/removal arc. This decision does not change that.
  It is the integrator's reset-synchroniser contract, and the RTL port is
  already documented as a synchronous power-on reset. It is not
  link-driven.
- **Input-to-register paths are unconstrained today.** The committed STA
  requests declare a clock and nothing else: no input or output delays.
  So the new `Reset`-to-D paths are not checked yet, and neither are the
  existing ones from `Reset`, `TxValid`, `DataOut`, `OpMode`, `rxdp` and
  `rxdm`. Making those checks meaningful needs input-delay constraints in
  the STA request. That is a flow question for #131, not something this
  record asserts.
- **Synthesis cost was not measured here.** By construction it is one
  more flop (`rx_dec_mask`, no reset) and a few gates on the decoder and
  destuffer inputs. The synthesis-smoke record is refreshed with #131.

## Alternatives considered

- **Keep the asynchronous path and add an STA recovery/removal check.**
  Rejected. It would need clock-relative assertion/release constraints on
  a UTMI input, recovery/removal coverage of the affected `dffrnq` cells at
  every supported corner, and a netlist that matches this RTL. None of
  that exists, and the committed STA requests have no field for input
  delays. More fundamentally, it would still let a `Reset` pulse that no
  edge samples change RX state. That contradicts the synchronous UTMI
  contract DR-0005 adopted for TX, and the unsampled-pulse probe shows it
  at the ports.
- **Register `Reset` once and feed the registered copy to the
  asynchronous ports.** Rejected, for the reason DR-0005 gives. It holds
  the transforms in reset across the release edge, so the decoder would
  miss the release-edge sample and a SYNC starting on the release edge
  would lose its first bit. It also keeps an asynchronous arc, now from a
  flop instead of a port.
- **Feed `rst_n` only and add no synchronous clears.** Rejected. The
  decoder's reference would survive a reset at whatever level the line had
  on the first reset edge. With one reset clock and SYNC starting on the
  release edge, the packet is lost (the ports-only failure in the table
  above).
- **Only `enable` low for the destuffer (the issue's example).**
  Insufficient on its own. The transparent idle branch still forwards a
  strobed bit, so `bit_valid` would not clear (the "destuffer
  `data_strobe` not forced" row: 40 whitebox failures). It is combined
  with forcing `data_strobe` low.
- **Edit the vendored modules to add a synchronous clear port.**
  Rejected. The vendored bytes are stamped (DR-0002, `reuse.lock.json`),
  and the canonical inputs plus one wrapper flop already produce the
  required state.
