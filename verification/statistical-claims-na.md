# Statistical claims (T1 item 6) — digital partition: not applicable

<!-- statistical-na: spec_sha256=a7f5fd1c62fc17dcc008d45580eea7440b74b58e8fa8d2717c3bee052f2a19e9 -->

## Current statement (2026-10-30) — supersedes the statements of record below

**Why superseded.** DR-0010 (issue #251) added one row to the §12.1
decision-record index of `spec/usb2-device-phy.md`, which changed the spec's
SHA-256 from `2ef22302…` to `a7f5fd1c…`. The binding check
(`verification/check_statistical_na.py`) correctly refuses a pin that no
longer matches, so the statement is re-read and re-pinned here rather than
the old pin being edited in place.

**Re-read result.** The statement below still holds against the changed spec.
The only difference is the new §12.1 index row for DR-0010. That row records
a layout-only grid-snap of the `dplus_pullup` trim resistors; §5's
1.5 kΩ ±5 % value is unchanged and no spec section other than the §12.1 index
changed. It adds no digital row and no row whose pass/fail depends on a
random device parameter. The digital partition therefore still has no
statistical row. (Analog statistical rows remain classified by
`spec/decisions/0007-analog-statistical-rows.md`.)

**Binding.** The marker on line 3 now pins the SHA-256 of the spec as
changed by DR-0010. If the spec changes again, this statement must be re-read
and superseded the same way.

## Superseded statement (2026-10-27, pinned to spec_sha256 2ef22302…) — kept as history

Its marker is shown as plain text (`spec_sha256=2ef223023a76972c5afa853104a7a280521c966cf8c37dd8a3f5d3f390472555`) so the checker sees exactly one live marker. Its body follows unchanged.

### (2026-10-27 statement body)

**Why superseded.** The proposal of DR-0009 (issue #249) added one row to the
§12.1 decision-record index of `spec/usb2-device-phy.md`, which changed the
spec's SHA-256 from `dbe8aac4…` to `2ef22302…`. The binding check
(`verification/check_statistical_na.py`) correctly refuses a pin that no
longer matches, so the statement is re-read and re-pinned here rather than
the old pin being edited in place.

**Re-read result.** The statement below still holds against the changed spec.
The only difference is the new §12.1 index row for DR-0009. That row is a
pointer to a decision record, marked "PROPOSED, not in force"; §8.2 text is
unchanged, and it adds no digital row and no row whose pass/fail depends on a
random device parameter. The digital partition therefore still has no
statistical row. (DR-0009 itself concerns the analog driver-output jitter
row; analog statistical rows remain classified by
`spec/decisions/0007-analog-statistical-rows.md`.)

**Binding.** The marker on line 3 now pins the SHA-256 of the spec as
changed by DR-0009's proposal. If DR-0009 is ratified or the spec otherwise
changes again, this statement must be re-read and superseded the same way.

## Superseded statement (original, pinned to spec_sha256 dbe8aac4…)

The text below is the original statement, kept unchanged apart from its
marker, which is shown as plain text (`spec_sha256=dbe8aac42457097138c4d11d7d6ef21f2f7488d205525a1f021cb738e533e6fd`)
so the checker sees exactly one live marker.

T1 item 6 requires Monte Carlo evidence for "any accuracy, offset, or
matching spec row" and says a block whose spec has no statistical row must
say so explicitly. This file is that statement for the **digital partition**
(`usb_utmi_phy`, `rtl/*.v`; partition boundary in `manifests/README.md`).

**Statement.** The ratified spec (`spec/usb2-device-phy.md`) contains no
digital row whose pass/fail depends on a random device parameter. The digital
rows are functional correctness (cocotb against `rtl/`, 111 tests; see
`verification/records/`), receive bit-sampling versus clock tolerance (a
deterministic parametric sweep, DR-0003), and timing closure (STA over the
§8.1 corners, `verification/records/post-layout-pvt/`). Each is decided by a
deterministic corner or sweep, not a distribution. The statistical rows of
this block are all analog and are classified in
`spec/decisions/0007-analog-statistical-rows.md`.

**Binding.** The marker on line 3 pins the SHA-256 of the spec this statement
was written against. `verification/check_statistical_na.py` recomputes it and
fails when the spec changes, so a spec change that adds a digital statistical
row cannot leave this statement silently stale: whoever changes the spec must
re-read this file and re-pin it (a new record that says why; this file is not
edited to hide history — supersede it by a new dated statement).

**Grader form.** `klt signoff` grades this outcome from two hash-bound JSON
documents in `verification/statistical-na/`: `spec-rows.json` (the digital
rows of the ratified spec) and `na-statement.json` (one entry per row saying
why it is not statistical). They are the machine-readable form of the
statement above. Rendered with a current `klt` (0.7.1.dev1743) as
`6.digital` they grade `not_applicable`; rendered with the `klt` this repo's
CI pins (`e8ca621`, 0.5.0) the form is unknown and the item renders
`unmet` / `invalid_evidence`. `manifests/gf180-usb2-phy.json` therefore does
not cite them yet: the citation lands with the next `klt` pin bump, which
re-renders `manifests/t1-signoff-report.json` in the same change.

```json
"6.digital": {"not_applicable": {
  "spec":      {"file": "verification/statistical-na/spec-rows.json",
                "content_hash": "sha256:d91aac2a449eeaf6cba822e63931a5a409b7839734c8b61ce15f117622ce7388"},
  "statement": {"file": "verification/statistical-na/na-statement.json",
                "content_hash": "sha256:f4caf405678cb28a39ef0b828216c49a78adedca39d4edd0fc0800ea2b495ebc"}}}
```
