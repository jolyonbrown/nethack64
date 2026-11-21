#!/usr/bin/env python3
"""
run_farrt128.py - write the far runtime for tests/spikes/farrt128.c (tools/bank/farrt.py:
far space 1 at pages $80-$BF in REU bank 1, the character space 6 at $C1-$FB in REU bank 0,
4 frames), build it with the far-spaces compiler for the C128 (-tf=prg, a file per bank),
make its REU image (tools/bank/c128_images.py), run it in headless x128 and report its checks
(T2.13, ADR-0009, ADR-0010).

usage: tests/spikes/run_farrt128.py --oscar64 PATH   (the far-spaces fork; x128; port 6502)

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

SRC = os.path.join(rb.ROOT, "tests", "spikes", "farrt128.c")
FARRT = os.path.join(rb.ROOT, "tools", "bank", "farrt.py")
IMAGES = os.path.join(rb.ROOT, "tools", "bank", "c128_images.py")
CHECKS = [
    "24 far literals read as their near copies, through 4 frames",
    "a list through 512 nodes of far space 1 holding far literals' bytes",
    "the library's strcpy, strcmp, memcpy, memset on far strings",
    "nh_farcopy() from space 1 across a page",
    "faults and write-backs happened; the MMU as it was",
    "a fault with the MMU at $3F switches the I/O in and out again",
    "a far literal and its near copy sum the same (the timing's check)",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--oscar64", required=True)
    a = ap.parse_args()
    os.makedirs(rb.OUT, exist_ok=True)
    subprocess.run([sys.executable, FARRT, "--out", os.path.join(rb.OUT, "nh_farrt.c"), "--target", "c128",
                    "--frames", "4", "--space", "1:80:bf:01", "--space", "6:c1:fb:00", "--chars", "6"], check=True)
    prg = os.path.join(rb.OUT, "farrt128.prg")
    for f in os.listdir(rb.OUT):
        if f.startswith("farrt128_ov"):
            os.remove(os.path.join(rb.OUT, f))
    r = subprocess.run([a.oscar64, "-Os", "-g", "-tm=c128", "-tf=prg", "-dOSCAR_FARCHARS", "-i=" + rb.OUT,
                        "-o=" + prg, SRC], capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n%s" % (r.stdout + r.stderr))
    cart, reu = os.path.join(rb.OUT, "farrt128.md128"), os.path.join(rb.OUT, "farrt128.reu")
    subprocess.run([sys.executable, IMAGES, prg, cart, reu, "--reu-kb", "512"], check=True)
    lbl = prg.rsplit(".", 1)[0] + ".lbl"
    done, result = rb.label(lbl, "spike_done"), rb.label(lbl, "spike_result")
    env = dict(os.environ, VICE="x128")
    subprocess.run(rb.VICE + ["launch", "--prg", prg, "--reu", "512", "--reuimage", reu, "--headless", "--warp",
                              "--"] + run_c128.rom_args(), check=True, capture_output=True, env=env)
    try:
        for _ in range(300):
            if rb.mem(done, 1)[:1] == [1]:
                break
            time.sleep(0.2)
        else:
            sys.exit("%s never set spike_done" % prg)
        b = run_c128ef.mem(result, 12)
        v = [b[i] | b[i + 1] << 8 for i in range(0, 12, 2)]
    finally:
        subprocess.run(rb.VICE + ["quit"], capture_output=True)
    bad = 0
    for i, what in enumerate(CHECKS):
        bit = 1 << i
        state = "pass" if v[0] & bit else ("FAIL" if v[1] & bit else "not run")
        bad += state != "pass"
        print("  %-7s %s" % (state, what))
    print("faults %d, write-backs %d; 40 bytes of a far literal in the cache %d cycles (%.1f a byte), "
          "near %d (%.1f a byte)" % (v[2], v[3], v[4], v[4] / 40, v[5], v[5] / 40))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
