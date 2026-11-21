#!/usr/bin/env python3
"""
run_farchar128.py - build tests/spikes/farchar128.c for the C128, run it in headless x128 in
C128 mode and report its checks of a character space in RAM bank 1 (ADR-0010, T2.13) and
what its accesses cost.

usage: tests/spikes/run_farchar128.py [--oscar64 PATH]   (needs x128; port 6502)

Exit status 0 when every check passes.
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_bankcall as rb  # noqa: E402  (label, mem)
import run_c128  # noqa: E402  (the ROM names x128 needs)
import run_c128ef  # noqa: E402  (mem, read line by line)

SRC = os.path.join(rb.ROOT, "tests", "spikes", "farchar128.c")
CHECKS = [
    "every byte of $C100-$FBFF written in bank 1 reads back",
    "bank-0 code at $C1xx runs and reads bank 1 at its own addresses",
    "bank 0 still holds that code (not the pattern)",
    "the stub puts the MMU back as it found it ($3E, $3A, $3F)",
    "a string copy far to near across $CFFF/$D000",
    "writes to bank 1 under the I/O leave the VIC alone",
    "the tested path: near reads near, far writes land in bank 1",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--oscar64", default="oscar64")
    a = ap.parse_args()
    os.makedirs(rb.OUT, exist_ok=True)
    prg = os.path.join(rb.OUT, "farchar128.prg")
    r = subprocess.run([a.oscar64, "-Os", "-g", "-tm=c128", "-o=" + prg, SRC], capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n%s" % (r.stdout + r.stderr))
    lbl = prg.rsplit(".", 1)[0] + ".lbl"
    done, result = rb.label(lbl, "spike_done"), rb.label(lbl, "spike_result")
    env = dict(os.environ, VICE="x128")
    subprocess.run(rb.VICE + ["launch", "--prg", prg, "--headless", "--warp", "--"] + run_c128.rom_args(),
                   check=True, capture_output=True, env=env)
    try:
        for _ in range(150):
            if rb.mem(done, 1)[:1] == [1]:
                break
            time.sleep(0.2)
        else:
            sys.exit("%s never set spike_done" % prg)
        b = run_c128ef.mem(result, 16)
        v = [b[i] | b[i + 1] << 8 for i in range(0, 16, 2)]
    finally:
        subprocess.run(rb.VICE + ["quit"], capture_output=True)
    passed, ran = v[0], v[1]
    bad = 0
    for i, what in enumerate(CHECKS):
        bit = 1 << i
        state = "pass" if passed & bit else ("FAIL" if ran & bit else "not run")
        bad += state != "pass"
        print("  %-7s %s" % (state, what))
    plain, near, far, scpy, fwr, own = v[2:8]
    print("cycles at 1 MHz, a byte access (256, loop included): plain %.1f; tested, near %.1f (+%.1f); "
          "tested, far %.1f (+%.1f); tested far write %.1f" % (
              plain / 256, near / 256, (near - plain) / 256, far / 256, (far - plain) / 256, fwr / 256))
    print("a 31-character string copied far to near: %d cycles (%.1f a byte); c1_own_sum(): %d cycles" % (
        scpy, scpy / 32, own))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
