#!/usr/bin/env python3
"""c128_images.py - make the C128 build's cartridge and REU images from the banks Oscar64
wrote beside a program (T2.13, ADR-0003 2026-11-21).

usage: tools/bank/c128_images.py PROGRAM.prg OUT.md128 OUT.reu [--reu-kb 2048] [--first 64]

A build for the C128 is a .prg (-tf=prg) with one `#pragma overlay( STEM_ovN, N )` per bank
N, STEM the program's file name without `.prg`: Oscar64's Linker::WritePrgFile then writes
each bank as a file of its own in the program's directory, named after the overlay
(`STEM_ovN.prg`), with its load address. Banks
below --first go into a Magic Desk 128 image, VICE's raw format (`-cartmd128`): bank b at
offset b * 16 KB, its bytes from $8000 (bank 0, which the C128's start code would read, is
left empty). Banks from --first on go into the REU image as tools/bank/crt_split.py puts
them: bank b at REU offset (b - first) * 16 KB, its address A at + (A - $8000), so that a far
space's section of $8000-$FFFF reaches the next bank's slot. Two banks that land on the same
REU bytes are an error. The REU image is padded to the REU's size, since VICE does not load a
shorter one.
"""
import argparse
import glob
import os
import re
import sys

BANK = 0x4000


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("prg")
    ap.add_argument("md128_out")
    ap.add_argument("reu_out")
    ap.add_argument("--first", type=int, default=64, help="first bank that goes to the REU")
    ap.add_argument("--reu-kb", type=int, default=2048, help="pad the REU image to this size")
    a = ap.parse_args()
    cart = bytearray(64 * BANK)
    reu = bytearray(a.reu_kb * 1024)
    used_reu = {}
    banks_c, banks_r = [], []
    stem = os.path.splitext(a.prg)[0]
    files = glob.glob(glob.escape(stem) + "_ov*.prg")
    if not files:
        sys.exit("no bank files beside %s (%s_ovN.prg)" % (a.prg, os.path.basename(stem)))
    for f in sorted(files):
        m = re.search(r"_ov(\d+)\.prg$", f)
        if not m:
            continue
        b = int(m.group(1))
        data = open(f, "rb").read()
        load, body = data[0] | data[1] << 8, data[2:]
        if not body:
            continue
        if b < a.first:
            if b >= 64 or load < 0x8000 or load + len(body) > 0xC000:
                sys.exit("%s: bank %d at $%04x, %d B: not inside a cartridge bank" % (f, b, load, len(body)))
            o = b * BANK + load - 0x8000
            cart[o:o + len(body)] = body
            banks_c.append(b)
        else:
            if load < 0x8000:
                sys.exit("%s: bank %d loads at $%04x" % (f, b, load))
            o = (b - a.first) * BANK + load - 0x8000
            if o + len(body) > len(reu):
                sys.exit("%s: bank %d does not fit a %d KB REU" % (f, b, a.reu_kb))
            for page in range(o >> 8, (o + len(body) + 255) >> 8):
                if page in used_reu:
                    sys.exit("bank %d lands on REU $%06x, which bank %d holds" % (b, page << 8, used_reu[page]))
                used_reu[page] = b
            reu[o:o + len(body)] = body
            banks_r.append(b)
    open(a.md128_out, "wb").write(bytes(cart))
    open(a.reu_out, "wb").write(bytes(reu))
    print("%s: %d cartridge bank(s); %s: %d REU bank(s)" % (os.path.basename(a.md128_out), len(banks_c),
                                                          os.path.basename(a.reu_out), len(banks_r)))


if __name__ == "__main__":
    main()
