#!/usr/bin/env python3
"""
run_c128.py - build tests/spikes/c128.c for the C128, run it in headless x128 with an REU
and report what a C128 gives the port: RAM in view, the second bank, the REU, the VDC and
2 MHz, with timings (T2.12, the hardware discussion).

usage: tests/spikes/run_c128.py [--oscar64 PATH] [--reu KB]   (needs x128; port 6502)

Exit status 0 when every check passes.
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_bankcall as rb  # noqa: E402  (label, mem)

SRC = os.path.join(rb.ROOT, "tests", "spikes", "c128.c")
CHECKS = [
    "$0400-$1BFF is RAM (below the program; KERNAL never called)",
    "$D000-$DFFF is RAM at MMU $3F; I/O there at $3E; the RAM kept",
    "$E000-$EFFF is RAM (no KERNAL ROM)",
    "bank 1 holds other bytes than bank 0 at the same address",
    "REU: 16 KB stored from bank 0 and loaded back match",
    "VDC: bytes written to its own RAM read back",
    "2 MHz: the same loop takes fewer timer ticks",
]
TIMES = [
    ("bank 1 -> bank 0, 256 B (bnk1_readm)", 256),
    ("REU -> bank 0, 16 KB, 1 MHz", 16384),
    ("VDC, 2,000 B written (a screen)", 2000),
    ("loop, 1 MHz", 0),
    ("loop, 2 MHz", 0),
    ("REU -> bank 0, 16 KB, 2 MHz", 16384),
]


def rom_args():
    """Arch's VICE 3.7.1 package lacks some of x128's national ROMs (kernalfi,
    chargen-325167-01): x128 will not start without them, so name the international ones
    instead (2026-11-21)"""
    rom = []
    for opt in ("kernalde", "kernalfi", "kernalfr", "kernalit", "kernalno", "kernalse", "kernalch"):
        rom += ["-" + opt, "kernal-318020-05.bin"]
    for opt in ("chargde", "chargfr", "chargse", "chargch", "chargno"):
        rom += ["-" + opt, "chargen-390059-01.bin"]
    return rom


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--oscar64", default="oscar64")
    ap.add_argument("--reu", type=int, default=512)
    a = ap.parse_args()
    os.makedirs(rb.OUT, exist_ok=True)
    prg = os.path.join(rb.OUT, "c128.prg")
    r = subprocess.run([a.oscar64, "-Os", "-g", "-tm=c128", "-o=" + prg, SRC], capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n%s" % (r.stdout + r.stderr))
    lbl = prg.rsplit(".", 1)[0] + ".lbl"
    done, result, val = rb.label(lbl, "spike_done"), rb.label(lbl, "spike_result"), rb.label(lbl, "spike_val")
    env = dict(os.environ, VICE="x128")
    subprocess.run(rb.VICE + ["launch", "--prg", prg, "--reu", str(a.reu), "--headless", "--warp", "--"] + rom_args(),
                   check=True, capture_output=True, env=env)
    try:
        for _ in range(300):
            if rb.mem(done, 1)[:1] == [1]:
                break
            time.sleep(0.2)
        else:
            sys.exit("%s never set spike_done" % prg)
        b = rb.mem(result, 4)
        passed, ran = b[0] | b[1] << 8, b[2] | b[3] << 8
        v = rb.mem(val, 2 * len(TIMES))
    finally:
        subprocess.run(rb.VICE + ["quit"], capture_output=True)
    bad = 0
    for i, what in enumerate(CHECKS):
        bit = 1 << i
        state = "pass" if passed & bit else ("FAIL" if ran & bit else "not run")
        bad += state != "pass"
        print("  %-7s %s" % (state, what))
    for i, (what, n) in enumerate(TIMES):
        t = v[2 * i] | v[2 * i + 1] << 8
        print("  %6d ticks  %s%s" % (t, what, ", %.2f a byte" % (t / n) if n else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
