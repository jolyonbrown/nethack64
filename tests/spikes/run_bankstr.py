#!/usr/bin/env python3
"""
run_bankstr.py - build tests/spikes/bankstr.c with nhbank.h and string wrappers written by
tools/bank/bankgen.py's own code, run it in headless VICE (EasyFlash) and report its checks
of strings passed between banks (T2.12, docs/BANKING-SPIKE.md).

usage: tests/spikes/run_bankstr.py [--oscar64 PATH]   (needs x64sc, xvfb-run; port 6502)

The compiler must have Linker::InsertBankCalls (the pin from commit 72, ADR-0007);
exit status 0 when every check passes.
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_bankcall as rb  # noqa: E402  (label, mem, run)

sys.path.insert(0, os.path.join(rb.ROOT, "tools", "bank"))
import bankgen  # noqa: E402

SRC = os.path.join(rb.ROOT, "tests", "spikes", "bankstr.c")
CHECKS = [
    "a literal of bank 2 reaches bank 16 copied",
    "the copy survives six nested calls that copy literals of their own",
    "literals of banks 16 and 2 reach bank 3 copied",
    "a result wrapper calls its function once",
    "a result that is the copied argument outlives the release",
    "every argument copy released",
    "the bank restored",
]
S = "const char * nh_a0"
# (name, return type, parameters, bank, calling banks): the functions bankstr.c calls
FUNCS = [
    ("consume", "void", [(S, "nh_a0", True)], 3, [2, 16]),
    ("hold", "void", [(S, "nh_a0", True)], 16, [2]),
    ("produce", "char *", [], 16, [2]),
    ("ident", "const char *", [(S, "nh_a0", True)], 16, [2]),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--oscar64", default="oscar64")
    a = ap.parse_args()
    out = os.path.join(rb.OUT, "bankstr")
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "nhbank.h"), "w").write(bankgen.header([2, 3, 16], linker_stubs=True))
    report = {"result_wrappers": 0, "caller_wrappers": 0}
    lines = []
    for name, ret, params, bank, callers in FUNCS:
        lines += bankgen.split_trampoline({"name": name, "static": False}, (ret, params, False),
                                          bank, callers, report)
    open(os.path.join(out, "bankstr_w.c"), "w").write("\n".join(lines) + "\n#pragma code(code)\n")
    crt = os.path.join(out, "bankstr.crt")
    r = subprocess.run([a.oscar64, "-Os", "-g", "-tf=crt", "-i=" + out, "-o=" + crt, SRC],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n%s" % (r.stdout + r.stderr))
    passed, ran, _, _ = rb.run(crt, "crt", 512)
    bad = 0
    for i, what in enumerate(CHECKS):
        bit = 1 << i
        state = "pass" if passed & bit else ("FAIL" if ran & bit else "not run")
        bad += state != "pass"
        print("  %-7s %s" % (state, what))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
