#!/usr/bin/env python3
"""crt_split.py - move the banks an EasyFlash cannot hold from a .crt into an REU image.

usage: tools/bank/crt_split.py IN.crt OUT.crt OUT.reu [--first 64]

Oscar64 (the pin, commit 62) writes banks 64 and above into an EasyFlash .crt as ordinary
CHIP packets, "for post-processing" (it warns). ADR-0008: those banks live in the REU and
are copied into the 16 KB window at $8000 when called. Bank b goes to REU offset
(b - first) * 16 KB: its $8000 half at +0, its $A000 half at +8 KB, which is what the bank
call routine fetches (tools/bank/bankgen.py, tests/spikes/bankreu.c). A far space's section
(T2.12) is a region of $8000-$FFFF in one bank, so its bank also has $C000 and $E000 CHIPs: they
go on to +16 KB and +24 KB, so that bank 64 + 4n + 2 puts the space's address A at REU
n * 64 KB + A. Two CHIPs that land on the same REU bytes are an error. The REU image is padded
to the REU's size (--reu-kb), since VICE does not load a shorter one; VICE loads it with
-reuimage (tools/vice.py --reuimage).
"""
import argparse
import struct
import sys


def chips(data):
    hlen = struct.unpack(">I", data[0x10:0x14])[0]
    pos = hlen
    while pos < len(data):
        if data[pos:pos + 4] != b"CHIP":
            sys.exit("no CHIP packet at offset %d" % pos)
        plen, ctype, bank, load, size = struct.unpack(">IHHHH", data[pos + 4:pos + 16])
        yield pos, plen, bank, load, data[pos + 16:pos + 16 + size]
        pos += plen


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("crt_in")
    ap.add_argument("crt_out")
    ap.add_argument("reu_out")
    ap.add_argument("--first", type=int, default=64, help="first bank that goes to the REU")
    ap.add_argument("--reu-kb", type=int, default=1024,
                    help="pad the image to the REU's size (VICE ignores a shorter image)")
    a = ap.parse_args()
    data = open(a.crt_in, "rb").read()
    if data[:16] != b"C64 CARTRIDGE   ":
        sys.exit("%s is not a .crt" % a.crt_in)
    hlen = struct.unpack(">I", data[0x10:0x14])[0]
    keep = [data[:hlen]]
    reu = {}
    moved = set()
    for pos, plen, bank, load, body in chips(data):
        if bank < a.first:
            keep.append(data[pos:pos + plen])
            continue
        if load not in (0x8000, 0xa000, 0xc000, 0xe000) or len(body) > 0x2000:
            sys.exit("bank %d: a CHIP at $%04x of %d bytes" % (bank, load, len(body)))
        o = (bank - a.first) * 0x4000 + (load - 0x8000)
        if o in reu:
            sys.exit("bank %d: the CHIP at $%04x lands on REU $%06x, which another bank holds"
                     % (bank, load, o))
        reu[o] = body
        moved.add(bank)
    image = bytearray(max([o + 0x2000 for o in reu] + [a.reu_kb * 1024]))
    for o, body in reu.items():
        image[o:o + len(body)] = body
    open(a.crt_out, "wb").write(b"".join(keep))
    open(a.reu_out, "wb").write(bytes(image))
    banks = sorted(moved)
    print("%s: %d bank(s) kept; %s: %d bank(s) (%s), %d bytes" % (
        a.crt_out, len(keep) // 2, a.reu_out, len(banks),
        ", ".join(map(str, banks)) or "none", len(image)))


if __name__ == "__main__":
    main()
