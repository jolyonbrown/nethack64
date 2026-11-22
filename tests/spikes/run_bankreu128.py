#!/usr/bin/env python3
"""
run_bankreu128.py - build tests/spikes/bankreu128.c for the C128 (-tf=prg, a file per bank),
make its Magic Desk 128 and REU images (tools/bank/c128_images.py), run it in headless x128
in C128 mode and report its checks of calls into cartridge and REU banks, and what such
calls cost (T2.13, ADR-0003 2026-11-21).

usage: tests/spikes/run_bankreu128.py [--oscar64 PATH] [--io-out]   (needs x128, xvfb-run; port 6502)

Exit status 0 when every check passes.
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_bankcall as rb  # noqa: E402  (label, mem)
import run_bankreu  # noqa: E402  (the checks, the same)
import run_c128  # noqa: E402  (the ROM names x128 needs)

SRC = os.path.join(rb.ROOT, "tests", "spikes", "bankreu128.c")
IMAGES = os.path.join(rb.ROOT, "tools", "bank", "c128_images.py")
N = 32
CHECKS = run_bankreu.CHECKS[:12] + ["the cartridge in again after REU calls (the MMU at $3A)"] + run_bankreu.CHECKS[13:]


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--oscar64", default="oscar64")
    ap.add_argument("--io-out", action="store_true",
                    help="-dIO_OUT: the bank call routine leaves the I/O out (bankgen.py --io-out)")
    a = ap.parse_args()
    os.makedirs(rb.OUT, exist_ok=True)
    prg = os.path.join(rb.OUT, "bankreu128.prg")
    cart = os.path.join(rb.OUT, "bankreu128.md128")
    reu = os.path.join(rb.OUT, "bankreu128.reu")
    r = subprocess.run([a.oscar64, "-Os", "-g", "-tm=c128", "-tf=prg"] + (["-dIO_OUT"] if a.io_out else []) +
                       ["-o=" + prg, SRC], capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n%s" % (r.stdout + r.stderr))
    subprocess.run([sys.executable, IMAGES, prg, cart, reu, "--reu-kb", "1024"], check=True)
    lbl = prg.rsplit(".", 1)[0] + ".lbl"
    done, result = rb.label(lbl, "spike_done"), rb.label(lbl, "spike_result")
    env = dict(os.environ, VICE="x128")
    subprocess.run(rb.VICE + ["launch", "--prg", prg, "--reu", "1024", "--reuimage", reu, "--headless", "--warp",
                              "--"] + run_c128.rom_args() + ["-cartmd128", cart],
                   check=True, capture_output=True, env=env)
    try:
        for _ in range(150):
            if rb.mem(done, 1)[:1] == [1]:
                break
            time.sleep(0.2)
        else:
            sys.exit("%s never set spike_done" % prg)
        b = rb.mem(result, 10)
        passed, ran, reu_same, cartb, alt = [b[i] | b[i + 1] << 8 for i in range(0, 10, 2)]
    finally:
        subprocess.run(rb.VICE + ["quit"], capture_output=True)
    bad = 0
    for i, what in enumerate(CHECKS):
        bit = 1 << i
        state = "pass" if passed & bit else ("FAIL" if ran & bit else "not run")
        bad += state != "pass"
        print("  %-7s %s" % (state, what.replace("EasyFlash", "cartridge")))
    print("an int (int, int) function, cycles a call (%d calls): into cartridge bank 1 %.1f; "
          "into REU bank 64, already in the window, %.1f" % (N, cartb / N, reu_same / N))
    print("three calls alternating REU banks 65, 64, 65, a 16 KB fetch each: %.0f cycles a call "
          "(%.2f ms at 1 MHz)" % (alt / 3, alt / 3 / 1000.0))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
