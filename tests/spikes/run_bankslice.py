#!/usr/bin/env python3
"""
run_bankslice.py - build tests/spikes/bankslice.c, move its bank 64 into an REU image
(tools/bank/crt_split.py), run it in headless VICE (EasyFlash + 1 MB REU) and report its
checks of a slice of code and tables in every bank (lever 3 of T2.12).

usage: tests/spikes/run_bankslice.py [--oscar64 PATH]   (needs x64sc; port 6502)

Exit status 0 when every check passes.
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_bankcall as rb  # noqa: E402  (label, mem)

SRC = os.path.join(rb.ROOT, "tests", "spikes", "bankslice.c")
SPLIT = os.path.join(rb.ROOT, "tools", "bank", "crt_split.py")
CHECKS = [
    "resident code calls a slice function (bank 1 mapped)",
    "EasyFlash bank 1 calls it directly",
    "REU bank 64 calls it directly",
    "a slice table and literal read from bank 2 and from REU bank 64",
    "bank 1 -> slice -> bank 2 and back: bank 1 mapped again",
    "REU 64 -> slice -> EasyFlash 1 and back: bank 64 in the window again",
    "the slice the same in banks 1, 2 and 64",
    "a slice function's address called from resident code, bank 2 mapped",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--oscar64", default="oscar64")
    a = ap.parse_args()
    os.makedirs(rb.OUT, exist_ok=True)
    full = os.path.join(rb.OUT, "bankslice-all.crt")
    crt = os.path.join(rb.OUT, "bankslice.crt")
    reu = os.path.join(rb.OUT, "bankslice.reu")
    r = subprocess.run([a.oscar64, "-Os", "-g", "-tf=crt", "-o=" + full, SRC], capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n%s" % (r.stdout + r.stderr))
    subprocess.run([sys.executable, SPLIT, full, crt, reu, "--reu-kb", "1024"], check=True)
    lbl = full.rsplit(".", 1)[0] + ".lbl"
    done, result = rb.label(lbl, "spike_done"), rb.label(lbl, "spike_result")
    subprocess.run(rb.VICE + ["launch", "--crt", crt, "--reu", "1024", "--reuimage", reu,
                              "--headless", "--warp"], check=True, capture_output=True)
    try:
        for _ in range(150):
            if rb.mem(done, 1)[:1] == [1]:
                break
            time.sleep(0.2)
        else:
            sys.exit("%s never set spike_done" % crt)
        b = rb.mem(result, 4)
        passed, ran = b[0] | b[1] << 8, b[2] | b[3] << 8
    finally:
        subprocess.run(rb.VICE + ["quit"], capture_output=True)
    bad = 0
    for i, what in enumerate(CHECKS):
        bit = 1 << i
        state = "pass" if passed & bit else ("FAIL" if ran & bit else "not run")
        bad += state != "pass"
        print("  %-7s %s" % (state, what))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
