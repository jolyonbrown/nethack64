#!/usr/bin/env python3
"""
run_bankstub.py - build tests/spikes/bankstub.c, run it in headless VICE (EasyFlash) and
report its checks of calls between banks through linker stubs, and what such a call
costs (docs/BANKING-SPIKE.md).

usage: tests/spikes/run_bankstub.py [--oscar64 PATH]   (needs x64sc, xvfb-run; port 6502)

The compiler must have Linker::InsertBankCalls (the pin from commit 72, ADR-0007);
exit status 0 when every check passes.
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_bankcall as rb  # noqa: E402  (label, mem, run)

SRC = os.path.join(rb.ROOT, "tests", "spikes", "bankstub.c")
CHECKS = [
    "resident -> bank 1, int (int, int)",
    "recursion through banks 1 and 2 from resident code (stack parameters)",
    "recursion starting in bank 2",
    "bank 1 -> bank 2: byte in A, int in A/X, loop counter kept in Y",
    "bank 1 function pointer called back by resident code",
    "function pointers (a stub's address) passed to resident code",
    "const table of function pointers called from bank 1",
    "long result from bank 2",
    "tail call bank 1 -> bank 2, from bank 2",
    "recursion started from bank 2",
    "const table of function pointers called from resident code",
    "tail call and byte call from resident code",
    "bank restored after the timing loops",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--oscar64", default="oscar64")
    a = ap.parse_args()
    os.makedirs(rb.OUT, exist_ok=True)
    crt = os.path.join(rb.OUT, "bankstub.crt")
    r = subprocess.run([a.oscar64, "-Os", "-g", "-tf=crt", "-o=" + crt, SRC], capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n%s" % (r.stdout + r.stderr))
    passed, ran, cross, same = rb.run(crt, "crt", 512)
    bad = 0
    for i, what in enumerate(CHECKS):
        bit = 1 << i
        state = "pass" if passed & bit else ("FAIL" if ran & bit else "not run")
        bad += state != "pass"
        print("  %-7s %s" % (state, what))
    print("%d calls of an int (int, int) function: %.1f cycles each into another bank, "
          "%.1f within the bank, so %.1f for the switch" % (
              rb.N, cross / rb.N, same / rb.N, (cross - same) / rb.N))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
