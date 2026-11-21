#!/usr/bin/env python3
"""
run_c128ef.py - build tests/spikes/c128ef.c for the C128, make a 1 MB EasyFlash image whose
banks are tagged, run both in headless x128 (C128 mode, boot jumper off, REU) and report
whether the C128 in its own mode sees and switches the EasyFlash's banks (T2.12, ADR-0003).

usage: tests/spikes/run_c128ef.py [--oscar64 PATH] [--reu KB] [--jumper]  (x128; port 6502)

Exit status 0 when every bank read back its own tag at $8000 and $A000 with the MMU at $2A.
"""
import argparse
import os
import re
import struct
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_bankcall as rb  # noqa: E402  (label, mem)
import run_c128  # noqa: E402  (the ROM names x128 needs)

SRC = os.path.join(rb.ROOT, "tests", "spikes", "c128ef.c")
BANKS = [0, 1, 2, 31, 62, 63]
MODES = [0x04, 0x07]
CFGS = [0x2A, 0x3A]
ADDRS = [0x8000, 0xA000, 0xC000, 0xE000]


def mem(addr, n):
    """vice.py mem, read line by line: rb.mem's one regex over the whole dump also picks up
    hex-like pairs from the ASCII column once a dump runs past one line"""
    r = subprocess.run(rb.VICE + ["mem", hex(addr), str(n)], capture_output=True, text=True)
    out = []
    for line in r.stdout.splitlines():
        # ">C:2f00  00 01 ...  ascii": up to 16 hex pairs after the address, then the text
        m = re.match(r"^\S*?([0-9a-fA-F]{4})((?:\s+[0-9a-fA-F]{2}(?=\s|$)){1,16})", line.strip())
        if m:
            out += [int(t, 16) for t in m.group(2).split()]
    return out[:n]


def make_crt(path):
    """EasyFlash (.crt type 32): bank b's ROML chip all 0x80|b, its ROMH chip all 0xC0|b"""
    head = b"C64 CARTRIDGE   " + struct.pack(">IHHBB6x", 0x40, 0x0100, 32, 1, 0)
    head += b"C128EF SPIKE".ljust(32, b"\0")
    out = [head]
    for b in range(64):
        for load, tag in ((0x8000, 0x80 | b), (0xA000, 0xC0 | b)):
            out.append(b"CHIP" + struct.pack(">IHHHH", 0x2010, 2, b, load, 0x2000) + bytes([tag]) * 0x2000)
    with open(path, "wb") as f:
        f.write(b"".join(out))


def make_md128(path):
    """Magic Desk 128 raw image: 64 banks of 16 KB, the first 8 KB of bank b all 0x80|b and the
    second all 0xC0|b, so the report reads the same as the EasyFlash's"""
    with open(path, "wb") as f:
        for b in range(64):
            f.write(bytes([0x80 | b]) * 0x2000 + bytes([0xC0 | b]) * 0x2000)


def what(v, bank):
    if v == 0x80 | bank:
        return "ROML b%d" % bank
    if v == 0xC0 | bank:
        return "ROMH b%d" % bank
    if v == 0x11:
        return "RAM"
    if 0x80 <= v < 0xC0:
        return "ROML b%d!" % (v & 0x3F)
    if v >= 0xC0:
        return "ROMH b%d!" % (v & 0x3F)
    return "$%02x" % v


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--oscar64", default="oscar64")
    ap.add_argument("--reu", type=int, default=512)
    ap.add_argument("--jumper", action="store_true",
                    help="VICE's EasyFlash jumper option on (then GAME and EXROM read high at reset)")
    ap.add_argument("--cart", choices=("easyflash", "md128"), default="easyflash",
                    help="md128: VICE's Magic Desk 128, a banked cartridge made for C128 mode")
    a = ap.parse_args()
    os.makedirs(rb.OUT, exist_ok=True)
    prg = os.path.join(rb.OUT, "c128ef.prg")
    crt = os.path.join(rb.OUT, "c128ef.crt" if a.cart == "easyflash" else "c128md.bin")
    r = subprocess.run([a.oscar64, "-Os", "-g", "-tm=c128", "-o=" + prg, SRC], capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n%s" % (r.stdout + r.stderr))
    (make_crt if a.cart == "easyflash" else make_md128)(crt)
    lbl = prg.rsplit(".", 1)[0] + ".lbl"
    done, rd, d505, reu = (rb.label(lbl, n) for n in ("spike_done", "spike_read", "spike_d505", "spike_reu"))
    env = dict(os.environ, VICE="x128")
    if a.cart == "easyflash":
        extra = ["-cartcrt", crt, "-easyflashjumper" if a.jumper else "+easyflashjumper"]
    else:
        extra = ["-cartmd128", crt]
    extra = run_c128.rom_args() + extra
    subprocess.run(rb.VICE + ["launch", "--prg", prg, "--reu", str(a.reu), "--headless", "--warp", "--"] + extra,
                   check=True, capture_output=True, env=env)
    try:
        for _ in range(150):
            if rb.mem(done, 1)[:1] == [1]:
                break
            time.sleep(0.2)
        else:
            sys.exit("%s never set spike_done (did the C128 start in C64 mode?)" % prg)
        v = mem(rd, 2 * 2 * 6 * 4)
        dv = rb.mem(d505, 1)[0]
        rv = rb.mem(reu, 1)[0]
    finally:
        subprocess.run(rb.VICE + ["quit"], capture_output=True)
    print("  $D505 at start: $%02x (%s mode)" % (dv, "C64" if dv & 0x40 else "C128"))
    ok = True
    i = 0
    for m in MODES:
        for c in CFGS:
            print("  $DE02=$%02x MMU=$%02x" % (m, c))
            for b in BANKS:
                row = v[i:i + 4]
                i += 4
                print("    bank %2d: %s" % (b, ", ".join("$%04X %s" % (ad, what(x, b)) for ad, x in zip(ADDRS, row))))
                if c == 0x2A and m == 0x07 and (row[0] != 0x80 | b or row[1] != 0xC0 | b):
                    ok = False
    print("  REU round trip with the EasyFlash banked in: %s" % ("pass" if rv == 1 else "FAIL"))
    return 0 if ok and rv == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
