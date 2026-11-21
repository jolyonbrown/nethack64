#!/usr/bin/env python3
"""
run_loram.py - build tests/spikes/loram.c, run it in headless VICE (EasyFlash) and report
what the cartridge's 16K mode maps at $8000 and $A000 with $01 = $37 and $36 (lever 2 of
T2.12: RAM under ROML).

usage: tests/spikes/run_loram.py [--oscar64 PATH]   (needs x64sc; port 6502)

Exit status 0 when every check passes.
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_bankcall as rb  # noqa: E402  (label, mem)

SRC = os.path.join(rb.ROOT, "tests", "spikes", "loram.c")
CHECKS = [
    "cartridge off, $01 = $36: RAM at $8000 and $A000",
    "16K mode, $01 = $37: ROML at $8000, ROMH at $A000",
    "16K mode, $01 = $36: RAM at $8000, ROMH at $A000",
    "16K mode, $01 = $37: a write to $8000 reaches the RAM under ROML",
    "16K mode, $01 = $36: code in the RAM at $8000 runs, reads ROMH at $A000",
    "back to $37: ROML again, the code kept in the RAM under it",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--oscar64", default="oscar64")
    a = ap.parse_args()
    os.makedirs(rb.OUT, exist_ok=True)
    crt = os.path.join(rb.OUT, "loram.crt")
    r = subprocess.run([a.oscar64, "-Os", "-g", "-tf=crt", "-o=" + crt, SRC], capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n%s" % (r.stdout + r.stderr))
    lbl = crt.rsplit(".", 1)[0] + ".lbl"
    done, result, seen = rb.label(lbl, "spike_done"), rb.label(lbl, "spike_result"), rb.label(lbl, "seen")
    subprocess.run(rb.VICE + ["launch", "--crt", crt, "--headless", "--warp"], check=True, capture_output=True)
    try:
        for _ in range(150):
            if rb.mem(done, 1)[:1] == [1]:
                break
            time.sleep(0.2)
        else:
            sys.exit("%s never set spike_done" % crt)
        b = rb.mem(result, 4)
        passed, ran = b[0] | b[1] << 8, b[2] | b[3] << 8
        s = rb.mem(seen, 10)
    finally:
        subprocess.run(rb.VICE + ["quit"], capture_output=True)
    bad = 0
    for i, what in enumerate(CHECKS):
        bit = 1 << i
        state = "pass" if passed & bit else ("FAIL" if ran & bit else "not run")
        bad += state != "pass"
        print("  %-7s %s" % (state, what))
    print("seen:", " ".join("%02x" % x for x in s))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
