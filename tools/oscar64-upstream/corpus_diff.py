#!/usr/bin/env python3
"""Compile one corpus with two Oscar64 builds and compare the .prg files byte for byte.

A front-end fix (parser, type check, preprocessor) should not change the code
generated for a program that both builds accept: every such file should give an
identical .prg.  A difference is either expected (the file uses the construct
the fix is about) or a regression.  This script does not decide which.

usage: corpus_diff.py BASE_OSCAR64 NEW_OSCAR64 [--src DIR_OR_FILE ...] [--out DIR] [-j N]

Default corpus: autotest/*.c and *.cpp from NEW's source tree (minus the
helper files autotest/makefile leaves out), plus nethack64's
tests/oscar64-repros/*.c.  Each file is compiled in five configurations.
Nothing is run in the emulator; autotest does that.
"""
import argparse
import concurrent.futures as cf
import filecmp
import glob
import os
import subprocess
import sys

CONFIGS = {
    "n-O2": ["-n", "-O2"],
    "n-Os": ["-n", "-Os"],
    "n-O0": ["-n", "-O0"],
    "n-O3": ["-n", "-O3"],
    "bc-O2": ["-bc", "-O2"],
}
# autotest/makefile's SRCS filter-out list: parts of multi-file tests
HELPERS = {"ambiguousoverload_trigger.c", "constconversionordertest_impl.c",
           "constconversionordertest_later.c", "opp_part1.cpp", "opp_part2.cpp",
           "funcvarlib.c"}
NH64 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def tree_of(cc):
    return os.path.dirname(os.path.dirname(os.path.realpath(cc)))


def corpus(new_cc, srcs):
    if not srcs:
        at = os.path.join(tree_of(new_cc), "autotest")
        srcs = [at, os.path.join(NH64, "tests", "oscar64-repros")]
    files = []
    for s in srcs:
        if os.path.isdir(s):
            files += sorted(glob.glob(os.path.join(s, "*.c")) + glob.glob(os.path.join(s, "*.cpp")))
        else:
            files.append(s)
    return [os.path.abspath(f) for f in files if os.path.basename(f) not in HELPERS]


def build(cc, src, cfg, out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        os.remove(out)
    try:
        r = subprocess.run([cc] + CONFIGS[cfg] + ["-o=" + out, src], capture_output=True,
                           text=True, timeout=180, cwd=os.path.dirname(src))
    except subprocess.TimeoutExpired:
        return "timeout"
    if r.returncode < 0:
        return "crash"
    return "ok" if r.returncode == 0 and os.path.exists(out) else "error"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("base")
    ap.add_argument("new")
    ap.add_argument("--src", nargs="*", default=[])
    ap.add_argument("--out", default=None)
    ap.add_argument("-j", type=int, default=os.cpu_count() or 4)
    a = ap.parse_args()
    out = a.out or os.path.join(NH64, "build", "corpus-diff")
    files = corpus(a.new, a.src)
    jobs = []
    with cf.ThreadPoolExecutor(a.j) as ex:
        for f in files:
            for cfg in CONFIGS:
                stem = os.path.basename(f).replace(".", "_") + "." + cfg + ".prg"
                b = os.path.join(out, "base", stem)
                n = os.path.join(out, "new", stem)
                jobs.append((f, cfg, b, n, ex.submit(build, a.base, f, cfg, b),
                             ex.submit(build, a.new, f, cfg, n)))
        same = differ = 0
        diffs, changes = [], []
        for f, cfg, b, n, fb, fn in jobs:
            sb, sn = fb.result(), fn.result()
            name = os.path.relpath(f, os.path.dirname(os.path.dirname(f))) + " " + cfg
            if sb != sn:
                changes.append(f"{name}: {sb} -> {sn}")
            elif sb == "ok":
                if filecmp.cmp(b, n, shallow=False):
                    same += 1
                else:
                    differ += 1
                    diffs.append(name)
    print(f"{len(files)} files x {len(CONFIGS)} configurations")
    print(f"both compile: {same + differ}  identical: {same}  different: {differ}")
    for d in diffs:
        print("  differs:", d)
    print(f"status changed: {len(changes)}")
    for c in changes:
        print("  ", c)
    return 1 if diffs or changes else 0


if __name__ == "__main__":
    sys.exit(main())
