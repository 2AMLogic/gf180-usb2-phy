"""Golden Python reference models for the USB full-speed bit-level codec.

These are the independent implementations the cocotb testbenches in this
directory check the Verilog in `rtl/` against, bit for bit -- the
"bit-exact" floor `spec/usb2-device-phy.md` #11 sets for this block's
digital logic. They are written straight from the prose rules in spec #2
and deliberately share no structure with the RTL (no clocks, no valid
strobes, no pipeline latency): a model that mirrors the implementation's
shape cannot catch the implementation's mistakes.

Line encoding convention, matching `rtl/usb_nrzi_encoder.v`:

    1 => J state, 0 => K state; idle / packet start is J.

Deliberately absent: SYNC, EOP, line-state decode, and every
serial-interface-engine concern (PIDs, CRC, endpoints). Those are out of
scope for this repo's bit-level codec -- see CLAUDE.md and spec #1/#2.

Pure stdlib, no cocotb import: this module is importable (and readable) on
its own, outside a simulator process.
"""

# Number of consecutive 1s after which the transmitter inserts a 0
# (spec/usb2-device-phy.md #2: "after every six consecutive 1s").
STUFF_AFTER = 6

# Idle / packet-start line state: J.
IDLE_J = 1


def nrzi_encode(bits, initial=IDLE_J):
    """Encode a data bit stream to NRZI line states.

    A data 0 transitions the line; a data 1 holds it. Returns the list of
    line states (1 = J, 0 = K), one per input bit.
    """
    line = initial
    out = []
    for bit in bits:
        if bit == 0:
            line ^= 1
        out.append(line)
    return out


def nrzi_decode(line_bits, initial=IDLE_J):
    """Decode NRZI line states back to a data bit stream.

    A transition recovers a 0; no transition recovers a 1. The inverse of
    `nrzi_encode` for the same `initial`.
    """
    prev = initial
    out = []
    for line in line_bits:
        out.append(1 if line == prev else 0)
        prev = line
    return out


def bit_stuff(bits):
    """Insert a 0 after every six consecutive 1s.

    `bits` is one packet's worth of data: this model has a packet boundary,
    which `rtl/usb_bit_stuffer.v` (a streaming module) deliberately does
    not.

    The insertion is positional, not data-dependent: the 0 goes in after
    the sixth 1 even when the next data bit is itself a 0, because the
    receiver removes a bit at exactly the same position.

    The rule survives the end of the packet. USB 2.0 #7.1.9: bit stuffing
    "is always enforced, without exception. If required by the bit stuffing
    rules, a zero bit will be inserted even if it is the last bit before
    the end-of-packet (EOP) signal." So a `bits` sequence ending on a run
    of exactly six 1s gets a trailing stuffed 0 appended -- reachable in
    ordinary traffic from a CRC16 residue ending in six 1s.

    The RTL emits that same trailing bit only when its wrapper flushes it
    (one clock of `in_valid` while `in_ready` is low); the testbenches
    drive that flush at every packet end so the DUT and this model stay
    comparable bit for bit. See `rtl/usb_bit_stuffer.v`'s header.

    Returns `(stuffed_bits, stuffed_flags)`, where `stuffed_flags[i]` is
    True exactly when `stuffed_bits[i]` is an inserted bit rather than data.
    """
    out = []
    flags = []
    ones = 0
    for bit in bits:
        if ones == STUFF_AFTER:
            out.append(0)
            flags.append(True)
            ones = 0
        out.append(bit)
        flags.append(False)
        ones = ones + 1 if bit == 1 else 0
    if ones == STUFF_AFTER:
        # The packet ends on six 1s: #7.1.9's "even if it is the last bit
        # before the EOP" case.
        out.append(0)
        flags.append(True)
    return out, flags


def bit_destuff(bits):
    """Remove stuffed 0s from a received bit stream.

    Returns `(data_bits, error_positions)`. `error_positions` holds the
    index (into `bits`) of every bit that occupied a stuff position but was
    a 1 rather than the required 0 -- i.e. a seventh consecutive 1, which
    is a bit-stuff error. The offending bit is removed either way, so the
    receiver stays bit-aligned with the transmitter.

    No packet-boundary special case is needed here: the stuff position is
    fixed by the run count, so a conformant transmitter's trailing stuff
    bit (see `bit_stuff`) is removed like any other. `bit_destuff` is the
    exact inverse of `bit_stuff` for every input, packet ends included.
    """
    out = []
    errors = []
    ones = 0
    for index, bit in enumerate(bits):
        if ones == STUFF_AFTER:
            if bit == 1:
                errors.append(index)
            ones = 0
            continue
        out.append(bit)
        ones = ones + 1 if bit == 1 else 0
    return out, errors
