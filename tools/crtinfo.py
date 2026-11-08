#!/usr/bin/env python3
"""
crtinfo.py - inspect or patch a .crt cartridge image header.

    crtinfo.py build/nethack-ef.crt                   show header + CHIP banks
    crtinfo.py build/nethack-ef.crt --subtype 1 --name "NETHACK"

Why --subtype: the Ultimate family (1541 Ultimate II+, Ultimate 64, C64
Ultimate) supports EasyFlash hardware sub-type 1, "REU-aware EasyFlash":
the cartridge leaves $DF00-$DF1F alone so a RAM Expansion Unit's registers
stay reachable.  The sub-type byte (header offset $1A) was added in CRT
format version 1.1, so this tool also raises the version to 1.1 when it
sets a sub-type (Oscar64 -csub writes the byte but leaves version 1.0).
See docs/HARDWARE.md.
"""
import argparse
import struct
import sys

TYPES = {0: "normal", 32: "EasyFlash", 60: "GMod2", 19: "Magic Desk", 62: "GMod3"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("crt")
    ap.add_argument("--subtype", type=int)
    ap.add_argument("--name")
    a = ap.parse_args()
    data = bytearray(open(a.crt, "rb").read())
    if data[:16] != b"C64 CARTRIDGE   ":
        sys.exit("not a CRT image")
    hlen = struct.unpack(">I", data[0x10:0x14])[0]
    ver = struct.unpack(">H", data[0x14:0x16])[0]
    ctype = struct.unpack(">H", data[0x16:0x18])[0]
    changed = False
    if a.subtype is not None:
        data[0x1A] = a.subtype
        if ver < 0x0101:
            data[0x14:0x16] = struct.pack(">H", 0x0101)
        changed = True
    if a.name is not None:
        data[0x20:0x40] = a.name.encode("ascii")[:32].ljust(32, b"\0")
        changed = True
    if changed:
        open(a.crt, "wb").write(data)
        ver = struct.unpack(">H", data[0x14:0x16])[0]
    print("%s: version %d.%d, type %d (%s), sub-type %d, EXROM %d GAME %d, name %r"
          % (a.crt, ver >> 8, ver & 0xFF, ctype, TYPES.get(ctype, "?"), data[0x1A],
             data[0x18], data[0x19], bytes(data[0x20:0x40]).rstrip(b"\0").decode("ascii", "replace")))
    p, banks = hlen, {}
    while p + 16 <= len(data) and data[p:p + 4] == b"CHIP":
        clen, _ctype, bank, addr, size = struct.unpack(">IHHHH", data[p + 4:p + 16])
        banks.setdefault(bank, []).append((addr, size))
        p += clen
    used = sum(s for v in banks.values() for _, s in v)
    print("%d CHIP packets in %d banks, %d KB of ROM used (EasyFlash max 1024 KB)"
          % (sum(len(v) for v in banks.values()), len(banks), used // 1024))


if __name__ == "__main__":
    main()
