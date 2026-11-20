#!/usr/bin/env python3
"""
run_bankreu.py - build tests/spikes/bankreu.c, move its banks 64 and 65 into an REU image
(tools/bank/crt_split.py), run it in headless VICE (EasyFlash + 1 MB REU) and report its
checks of calls into REU banks, and what such calls cost (ADR-0008).

usage: tests/spikes/run_bankreu.py [--oscar64 PATH]   (needs x64sc, xvfb-run; port 6502)

Exit status 0 when every check passes.
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_bankcall as rb  # noqa: E402  (label, mem)

SRC = os.path.join(rb.ROOT, "tests", "spikes", "bankreu.c")
SPLIT = os.path.join(rb.ROOT, "tools", "bank", "crt_split.py")
N = 32
CHECKS = [
    "resident -> REU bank 64, int (int, int); the window holds 64",
    "recursion through REU banks 64 and 65 (a fetch at every call and return)",
    "recursion starting in REU bank 65",
    "recursion through EasyFlash bank 1 and REU bank 64",
    "REU 64 -> EasyFlash 2: byte in A, int in A/X, loop counter kept across calls",
    "REU 64 function pointer called back by resident code",
    "function pointers (stubs) of REU and EasyFlash functions passed to resident code",
    "long result from REU 65, called from REU 64",
    "tail call REU 64 -> 65; const table of function pointers from REU 64",
    "EasyFlash 1 -> REU 64 and 65 and back",
    "EasyFlash 1 -> REU 65: long result",
    "const table of REU and EasyFlash function pointers from resident code",
    "the cartridge on again after REU calls",
    "three fetches counted in the alternating calls; bank 0 at the end",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--oscar64", default="oscar64")
    ap.add_argument("--second-bank", type=int, default=65,
                    help="the bank number of the second REU bank (191: the end of a 2 MB REU)")
    a = ap.parse_args()
    os.makedirs(rb.OUT, exist_ok=True)
    full = os.path.join(rb.OUT, "bankreu-all.crt")
    crt = os.path.join(rb.OUT, "bankreu.crt")
    reu = os.path.join(rb.OUT, "bankreu.reu")
    r = subprocess.run([a.oscar64, "-Os", "-g", "-tf=crt", "-dU2BANK=%d" % a.second_bank, "-o=" + full, SRC], capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n%s" % (r.stdout + r.stderr))
    reu_kb = 2048 if a.second_bank >= 128 else 1024
    subprocess.run([sys.executable, SPLIT, full, crt, reu, "--reu-kb", str(reu_kb)], check=True)
    lbl = full.rsplit(".", 1)[0] + ".lbl"
    done, result = rb.label(lbl, "spike_done"), rb.label(lbl, "spike_result")
    subprocess.run(rb.VICE + ["launch", "--crt", crt, "--reu", str(reu_kb), "--reuimage", reu,
                              "--headless", "--warp"], check=True, capture_output=True)
    try:
        for _ in range(150):
            if rb.mem(done, 1)[:1] == [1]:
                break
            time.sleep(0.2)
        else:
            sys.exit("%s never set spike_done" % crt)
        b = rb.mem(result, 10)
        passed, ran, reu_same, ef, alt = [b[i] | b[i + 1] << 8 for i in range(0, 10, 2)]
    finally:
        subprocess.run(rb.VICE + ["quit"], capture_output=True)
    bad = 0
    for i, what in enumerate(CHECKS):
        bit = 1 << i
        state = "pass" if passed & bit else ("FAIL" if ran & bit else "not run")
        bad += state != "pass"
        print("  %-7s %s" % (state, what))
    print("an int (int, int) function, cycles a call (%d calls): into EasyFlash bank 1 %.1f; "
          "into REU bank 64, already in the window, %.1f" % (N, ef / N, reu_same / N))
    print("three calls alternating REU banks 65, 64, 65, a 16 KB fetch each: %.0f cycles a call "
          "(%.2f ms at 0.985 MHz)" % (alt / 3, alt / 3 / 985.0))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
