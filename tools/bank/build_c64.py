#!/usr/bin/env python3
"""build_c64.py - compile the whole of NetHack, rewritten for a bank plan by bankgen.py,
in one Oscar64 run, and check the calls in its listing (the banking spike,
docs/BANKING-SPIKE.md).

usage: tools/bank/build_c64.py --plan PLAN.json [--out DIR] [--check-only]

1. Sets up tools/measure/measure_oscar64.py's harness for the C64 configuration in DIR
   (default build/bank-c64): every port/src file, and stubs from mkstubs.py for what no
   file defines (libc, the window port), with its main() referring to every function.
2. Rewrites the sources with bankgen.py.
3. Compiles all of them in one Oscar64 run (-Os, a .prg).  The data does not fit in RAM
   yet (T2.3), so "could not place" errors for data are expected; the code is placed.
4. Checks the listing: every JSR or JMP in a function of bank N goes to a function of
   bank N, to resident code, or is a trampoline calling its own function; and no
   resident code calls into a bank except a trampoline.

Environment: OSCAR64 (the compiler; it must take banks past 63 for an 84-bank plan),
BANK_TIMEOUT (seconds for the compile, default 3600).
"""
import argparse
import collections
import json
import os
import re
import resource
import shutil
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "measure"))
import measure_oscar64 as mo   # noqa: E402

INSN = re.compile(r"^(?:([0-9a-f]{2}):)?([0-9a-f]{4}) : (?:[0-9a-f_ ]{8}) (\w+)\s+(\S+)?(?:\s*; \(([^ .)]+))?")
FUNC = re.compile(r"^([A-Za-z_]\w*): ; ")
BANKED = re.compile(r"^(\w+)__b(\d+)$")


def cap():
    resource.setrlimit(resource.RLIMIT_AS, (3000000 * 1024,) * 2)


def check(asm):
    """Calls that cross banks in an Oscar64 listing: [(caller, caller bank, callee,
    callee bank)], and the number of calls looked at."""
    bank_of, calls, cur, cur_bank = {}, [], None, None
    for line in open(asm, errors="replace"):
        m = FUNC.match(line)
        if m:
            cur, cur_bank = m.group(1), "unseen"
            continue
        m = INSN.match(line)
        if not m or cur is None:
            continue
        b = int(m.group(1), 16) if m.group(1) else None
        if cur_bank == "unseen":
            cur_bank = b
            bank_of[cur] = b
        if m.group(3) in ("JSR", "JMP") and m.group(5) and not m.group(4).startswith("("):
            calls.append((cur, b, m.group(5)))
    bad = []
    for caller, cb, callee in calls:
        if callee not in bank_of or callee == caller:
            continue
        tb = bank_of[callee]
        if tb is None or tb == cb:
            continue
        mm = BANKED.match(callee)
        if cb is None and mm and mm.group(1) == caller and int(mm.group(2)) == tb:
            continue                       # the trampoline calls its own function
        bad.append((caller, cb, callee, tb))
    return bad, len(calls), bank_of


OBJ = re.compile(r"^(--|[0-9a-f]{2}):([0-9a-f]{4,5}) - ([0-9a-f]{4,5}) : ([^,]+), (\w+):(\S+)")


def sizes(mapfile):
    """From an Oscar64 map: bytes per bank (code and its literals), resident code, and the
    trampolines (resident functions with a banked name__bN)."""
    per_bank, resident, objs = collections.Counter(), 0, {}
    for line in open(mapfile, errors="replace"):
        m = OBJ.match(line)
        if not m:
            continue
        a, b = int(m.group(2), 16), int(m.group(3), 16)
        if b < a:
            continue
        bank = None if m.group(1) == "--" else int(m.group(1), 16)
        if bank is not None and m.group(6).startswith("nhbank_"):
            per_bank[bank] += b - a
        elif bank is None and m.group(5) == "NATIVE_CODE":
            resident += b - a
            objs[m.group(4)] = b - a
    banked = {BANKED.match(n).group(1) for n in objs if BANKED.match(n)}
    tramp = {n: z for n, z in objs.items() if n in banked}
    return per_bank, resident, tramp


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "bank-c64"))
    ap.add_argument("--check-only", action="store_true", help="only check an earlier build's listing")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    prg = os.path.join(out, "nethack.prg")
    if not a.check_only:
        mo.CONFIG, mo.OUT, mo.DEFS = "c64", out, mo.CONFIGS["c64"]["defs"]
        mo.setup()
        src = os.path.join(out, "src")
        files = sorted(f for f in os.listdir(src) if f.endswith(".c"))
        cpp = mo.CONFIGS["c64"]["cpp"]
        env = dict(os.environ, MKSTUBS_DEFS=" ".join(cpp))
        h = os.path.join(out, "h_all.c")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "measure", "mkstubs.py"),
                            os.path.join(out, "inc"), src, "allmain.c", h] +
                           [f for f in files if f != "allmain.c"], env=env, capture_output=True, text=True)
        if r.returncode:
            sys.exit("mkstubs.py failed:\n" + r.stdout + r.stderr)
        print("stubs:", r.stdout.strip())
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "bank", "bankgen.py"),
                            "--plan", os.path.abspath(a.plan), "--dir", src,
                            "--inc", os.path.join(out, "inc"), "--inc", os.path.join(out, "stub"),
                            "--inc", os.path.join(out, "fakelibc"), "--cpp=-nostdinc",
                            "--cpp=-D__attribute__(x)=", "--report", os.path.join(out, "bankgen-report.json")] +
                           ["--cpp=" + c for c in cpp] + files, capture_output=True, text=True)
        if r.returncode:
            sys.exit("bankgen.py failed:\n" + r.stdout + r.stderr)
        print(r.stdout.strip())
        cmd = [mo.OSCAR64, "-rmp", "-Os", "-i=" + os.path.join(out, "inc"), "-i=" + os.path.join(out, "stub"),
               "-i=" + src, "-o=" + prg] + [os.path.join(src, f) for f in files] + [h] + mo.DEFS
        t = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=out, preexec_fn=cap,
                               timeout=int(os.environ.get("BANK_TIMEOUT", "3600")))
        except subprocess.TimeoutExpired:
            sys.exit("the compile did not finish")
        open(os.path.join(out, "compile.log"), "w").write(r.stdout + r.stderr)
        errs = [l for l in (r.stdout + r.stderr).splitlines() if "error" in l]
        kinds = collections.Counter(re.sub(r".*: error (\d+): ([^']*).*", r"\1 \2", e) for e in errs)
        print("compile: exit %d in %.0f s; %d error lines: %s" % (r.returncode, time.time() - t, len(errs),
                                                                  dict(kinds.most_common(6))))
    asm = prg[:-4] + ".asm"
    if not os.path.exists(asm):
        asm = prg[:-4] + ".error.asm"
    if not os.path.exists(asm):
        sys.exit("no listing")
    bad, n, bank_of = check(asm)
    banks = collections.Counter(b for b in bank_of.values() if b is not None)
    print("listing %s: %d functions, %d in %d banks, %d resident; %d calls; %d cross a bank "
          "without a trampoline" % (os.path.basename(asm), len(bank_of), sum(banks.values()), len(banks),
                                    sum(1 for b in bank_of.values() if b is None), n, len(bad)))
    for x in bad[:20]:
        print("  %s (bank %s) -> %s (bank %s)" % x)
    mp = asm[:-4] + ".map"
    if os.path.exists(mp):
        per_bank, resident, tramp = sizes(mp)
        if per_bank:
            v = sorted(per_bank.values())
            print("banks: %d used, %d B in all; per bank min %d, median %d, max %d B" % (
                len(v), sum(v), v[0], v[len(v) // 2], v[-1]))
        print("resident code: %d B, of which %d trampolines, %d B (%.1f B each)" % (
            resident, len(tramp), sum(tramp.values()), sum(tramp.values()) / max(1, len(tramp))))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
