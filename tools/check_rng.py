#!/usr/bin/env python3
"""check_rng.py - src/hal/rng.c's lrand48() gives glibc's numbers (T2.7).

usage: tools/check_rng.py [-n N]

Compiles src/hal/rng.c with a small driver for Oscar64's emulator (oscar64 -e), which
prints, for each seed, the last of N numbers and a checksum of all of them, and compares
those with a reference: the 48-bit LCG in Python, itself checked against the host's
lrand48() through ctypes when there is a glibc.  Exit 0 when everything agrees.
"""
import argparse
import ctypes
import os
import re
import resource
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OSCAR64 = os.environ.get("OSCAR64") or shutil.which("oscar64") or "oscar64"
SEEDS = [1731700000, -1, 0, 1, 0x7FFFFFFF, -0x80000000, 0x12345678]
A, C, MASK = 0x5DEECE66D, 0xB, (1 << 48) - 1


def reference(seed, n):
    x = ((seed & 0xFFFFFFFF) << 16) | 0x330E
    last, total = 0, 0
    for _ in range(n):
        x = (A * x + C) & MASK
        last = x >> 17
        total = (total * 31 + last) & 0xFFFFFFFF
    return last, total


def check_against_glibc(n):
    try:
        libc = ctypes.CDLL("libc.so.6")
    except OSError:
        return "no glibc here: the reference is not cross-checked"
    libc.lrand48.restype = ctypes.c_long
    libc.srand48.argtypes = [ctypes.c_long]
    for seed in SEEDS:
        libc.srand48(seed)
        last, total = 0, 0
        for _ in range(n):
            last = libc.lrand48()
            total = (total * 31 + last) & 0xFFFFFFFF
        if (last, total) != reference(seed, n):
            sys.exit("the Python reference differs from glibc for seed %d" % seed)
    return "the reference agrees with glibc"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-n", type=int, default=20000)
    a = ap.parse_args()
    print(check_against_glibc(a.n))
    driver = """#include <stdio.h>
#include "rng.h"
static const long seeds[%d] = { %s };
int main(void)
{
	for (int k = 0; k < %d; k++) {
		unsigned long total = 0;
		long v = 0;
		srand48(seeds[k]);
		for (long i = 0; i < %dL; i++) {
			v = lrand48();
			total = total * 31 + (unsigned long) v;
		}
		printf("%%lx %%lx\\n", v, total);
	}
	return 0;
}
""" % (len(SEEDS), ", ".join("%dL" % s if s != -0x80000000 else "(-0x7fffffffL - 1)" for s in SEEDS),
       len(SEEDS), a.n)
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "drv.c"), "w").write(driver)
        cap = lambda: resource.setrlimit(resource.RLIMIT_AS, (3000 << 20, 3000 << 20))
        r = subprocess.run([OSCAR64, "-Os", "-e", "-i=" + os.path.join(ROOT, "src", "hal"),
                            "-o=" + os.path.join(d, "drv.prg"), os.path.join(d, "drv.c"),
                            os.path.join(ROOT, "src", "hal", "rng.c")],
                           capture_output=True, text=True, cwd=d, preexec_fn=cap)
    got = [l.split() for l in r.stdout.splitlines() if re.match(r"^[0-9a-f]+ [0-9a-f]+$", l.strip())]
    if r.returncode or len(got) != len(SEEDS):
        sys.exit("the emulator run failed (%d):\n%s%s" % (r.returncode, r.stdout[-2000:], r.stderr[-2000:]))
    bad = 0
    for seed, (last, total) in zip(SEEDS, got):
        want = reference(seed, a.n)
        ok = (int(last, 16), int(total, 16)) == want
        bad += not ok
        print("seed %11d: %s" % (seed, "ok" if ok else "DIFFERS: 6502 %s %s, glibc %x %x" % (last, total, *want)))
    print("%d seeds, %d numbers each: %s" % (len(SEEDS), a.n, "all agree" if not bad else "%d differ" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
