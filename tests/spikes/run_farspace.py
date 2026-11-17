#!/usr/bin/env python3
"""
run_farspace.py - build tests/spikes/farspace.c with an Oscar64 that has far spaces
(#pragma farspace, T2.12), run it in headless VICE with a 1 MB REU and report its checks
of far data paged from the REU, and what a far access costs (ADR-0009).

usage: tests/spikes/run_farspace.py --oscar64 PATH   (needs x64sc, xvfb-run; port 6502)

Exit status 0 when every check passes.
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_bankcall as rb  # noqa: E402  (label, mem)

SRC = os.path.join(rb.ROOT, "tests", "spikes", "farspace.c")
CHECKS = [
    "a list through all 512 far nodes (64 pages, a cache of 16): its sum",
    "every node changed in array order, then the list again",
    "far to far struct copies between distant pages, under eviction",
    "every node read back after the evictions: the stores survived",
    "near objects of the far type through the same code",
    "a list running from near nodes into far ones",
    "faults and write-backs happened",
    "the far region's own RAM never written (all went through translation)",
    "the timing walk without faults",
    "three objects' groups interleaved under eviction (pinned pages)",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--oscar64", required=True)
    a = ap.parse_args()
    os.makedirs(rb.OUT, exist_ok=True)
    prg = os.path.join(rb.OUT, "farspace.prg")
    inc = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(a.oscar64))), "include")
    r = subprocess.run([a.oscar64, "-i=" + inc, "-Os", "-g", "-o=" + prg, SRC], capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n%s" % (r.stdout + r.stderr))
    lbl = prg.rsplit(".", 1)[0] + ".lbl"
    done, result = rb.label(lbl, "spike_done"), rb.label(lbl, "spike_result")
    subprocess.run(rb.VICE + ["launch", "--prg", prg, "--reu", "1024", "--headless", "--warp"],
                   check=True, capture_output=True)
    try:
        for _ in range(150):
            if rb.mem(done, 1)[:1] == [1]:
                break
            time.sleep(0.2)
        else:
            sys.exit("%s never set spike_done" % prg)
        b = rb.mem(result, 12)
        if len(b) < 12:
            sys.exit("could not read the results: the program ran away (VICE's monitor did not answer)")
        passed, ran, faults, writebacks, tnear, tfar = [b[i] | b[i + 1] << 8 for i in range(0, 12, 2)]
    finally:
        subprocess.run(rb.VICE + ["quit"], capture_output=True)
    bad = 0
    for i, what in enumerate(CHECKS):
        bit = 1 << i
        state = "pass" if passed & bit else ("FAIL" if ran & bit else "not run")
        bad += state != "pass"
        print("  %-7s %s" % (state, what))
    print("faults %d, write-backs %d" % (faults, writebacks))
    print("a walk of 8 nodes: near %d cycles, far (in the cache) %d: %.1f cycles a node more" % (
        tnear, tfar, (tfar - tnear) / 8.0))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
