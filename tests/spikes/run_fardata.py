#!/usr/bin/env python3
"""
run_fardata.py - build tests/spikes/fardata.c, run it in headless VICE with an REU and report
what a far-data access through the REU costs next to a near one (docs/RAM-PLAN.md).

usage: tests/spikes/run_fardata.py [--oscar64 PATH] [--reu KB]   (needs x64sc; port 6502)

Exit status 0 when every check of the far copies (sums, and writes surviving eviction)
passes.
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_bankcall as rb  # noqa: E402  (ROOT, OUT, VICE, label, mem)

SRC = os.path.join(rb.ROOT, "tests", "spikes", "fardata.c")
CHECKS = ["list near", "list far, cold", "list far, warm", "table near", "table far, cold",
          "table far, warm", "table far through a 32-page cache", "grid sweep near",
          "grid sweep far, cold", "grid sweep far, warm", "grid picks far",
          "grid writes survive eviction", "list far, in place", "table far, in place",
          "table far, one translation a record", "grid sweep far, in place"]


def run(prg, reu):
    lbl = prg[:-4] + ".lbl"
    done = rb.label(lbl, "spike_done")
    subprocess.run(rb.VICE + ["launch", "--prg", prg, "--reu", str(reu), "--headless", "--warp"],
                   check=True, capture_output=True)
    try:
        for _ in range(300):
            if rb.mem(done, 1)[:1] == [1]:
                break
            time.sleep(0.2)
        else:
            sys.exit("%s never set spike_done" % prg)
        r = rb.mem(rb.label(lbl, "spike_result"), 96)
        res = [r[i] | r[i + 1] << 8 | r[i + 2] << 16 | r[i + 3] << 24 for i in range(0, 96, 4)]
        o = rb.mem(rb.label(lbl, "spike_ok"), 2)
        c = rb.mem(rb.label(lbl, "spike_count"), 8)
        return res, o[0] | o[1] << 8, [c[i] | c[i + 1] << 8 for i in range(0, 8, 2)]
    finally:
        subprocess.run(rb.VICE + ["quit"], capture_output=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--oscar64", default="oscar64")
    ap.add_argument("--reu", type=int, default=512)
    a = ap.parse_args()
    os.makedirs(rb.OUT, exist_ok=True)
    prg = os.path.join(rb.OUT, "fardata.prg")
    r = subprocess.run([a.oscar64, "-Os", "-g", "-o=" + prg, SRC], capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n%s" % (r.stdout + r.stderr))
    res, ok, cnt = run(prg, a.reu)
    bad = 0
    for i, what in enumerate(CHECKS):
        good = ok & (1 << i)
        bad += not good
        print("  %-4s %s" % ("ok" if good else "FAIL", what))
    xlat = (res[11] - res[12]) / 1000.0
    print("translation, hit: %.1f cycles a call (%d for 1,000, %d for the empty loop)" % (xlat, res[11], res[12]))
    print("translation in place, inlined, hit: %.1f cycles (%d for 1,000, %d with the reload alone)" % (
        (res[19] - res[20]) / 1000.0, res[19], res[20]))
    print("page fault, clean: %.0f cycles each (16 in %d)" % (res[13] / 16.0, res[13]))
    print("faults: list %d, table %d; write-backs in the eviction check %d" % (cnt[0], cnt[1], cnt[2]))
    rows = [("list, 200 nodes, 1 translation each", 0, 1, 2),
            ("list, in place", 0, None, 15),
            ("table, 252 x 55 B, 3 fields, 3 translations", 3, 4, 5),
            ("table, in place", 3, None, 16),
            ("table, paged layout, 1 translation a record", 3, None, 17),
            ("grid sweep, 80 x 21 x 6 B, read + write", 6, 7, 8),
            ("grid sweep, in place", 6, None, 18)]
    print("%-46s %9s %9s %9s %7s" % ("workload", "near", "far cold", "far warm", "warm/near"))
    for what, n, c, w in rows:
        print("%-46s %9d %9s %9d %6.1fx" % (what, res[n], "" if c is None else res[c], res[w], res[w] / max(1, res[n])))
    print("%-46s %9d %9s %9d %6.1fx" % ("grid, 2,000 random reads", res[9], "", res[10], res[10] / max(1, res[9])))
    print("%-46s %9s %9s %9d %6.1fx" % ("table, warm pass through 32 cached pages", "", "", res[14],
                                        res[14] / max(1, res[3])))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
