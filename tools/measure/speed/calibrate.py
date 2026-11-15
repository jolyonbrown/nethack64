#!/usr/bin/env python3
"""calibrate.py - how many 6502 cycles the C64 build spends for each x86 instruction the host
build executes, on NetHack's own code (docs/RAM-PLAN.md, the speed baseline).

usage: tools/measure/speed/calibrate.py [--out DIR] [--json FILE]

Builds tools/measure/speed/cal.c with the functions extract.py copies out of port/src, once per
workload (-DWORK=n): with gcc as tools/host-build.sh compiles the game, run under callgrind; and
with Oscar64 as the C64 build compiles it (-Os, the C64 configuration), run in Oscar64's emulator
with its profile (-ep).  Workload 0 only sets the level up and is subtracted from the others.
Both builds print a checksum and must agree.  Needs gcc, valgrind and oscar64.

For each workload: x86 instructions and 6502 cycles per call, and their ratio; then the 6502
profile's split by function, which shows Oscar64's runtime helpers (multiplication, 32-bit
arithmetic) apart from the functions that call them.
"""
import argparse
import hashlib
import json
import os
import re
import resource
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import cgsummary  # noqa: E402

OSCAR64 = os.environ.get("OSCAR64") or shutil.which("oscar64") or "oscar64"
WORKS = {1: "isok", 2: "dist2", 3: "is_pool + is_lava", 4: "mfndpos"}
FUNCS = ["isok", "dist2", "distmin", "online2", "strstri", "lowc", "is_pool", "is_lava", "on_level",
         "mfndpos", "mm_aggression", "curr_mon_load", "may_passwall", "may_dig", "bad_rock", "onscary",
         "sengr_at", "engr_at", "sobj_at", "t_at", "m_carrying", "which_armor"]
# as tools/host-build.sh compiles src/
HOST_CFLAGS = ["-O", "-g", "-std=gnu89", "-w", "-DUNWIDENED_PROTOTYPES"]
# as tools/bank/build_c64.py and measure_oscar64.py's c64 configuration compile it
C64_FLAGS = ["-Os", "-dC64", "-dregister="]


def cap():
    resource.setrlimit(resource.RLIMIT_AS, (3000 << 20, 3000 << 20))


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit("failed (%d): %s\n%s%s" % (r.returncode, " ".join(cmd), r.stdout[-3000:], r.stderr[-3000:]))
    return r.stdout


def prepare(out):
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(os.path.join(out, "data"))
    xs = run([sys.executable, os.path.join(HERE, "extract.py"), "--outdir", os.path.join(out, "x")] + FUNCS).split()
    # the C64 view of the headers: measure_oscar64.py's c64 configuration
    inc = os.path.join(out, "inc")
    shutil.copytree(os.path.join(ROOT, "port", "include"), inc)
    shutil.copy(os.path.join(ROOT, "tools", "measure", "c64meas-c64.h"), os.path.join(inc, "c64meas.h"))
    cfg = os.path.join(inc, "config.h")
    text = open(cfg, encoding="latin-1").read()
    open(cfg, "w", encoding="latin-1").write(
        text.replace('#include "config1.h"', '#include "c64meas.h"\n#include "config1.h"', 1))
    # Oscar64 mis-parses some comments inside monst.c's MON() invocations (as measure_oscar64.py)
    monst = os.path.join(out, "data", "monst.c")
    open(monst, "w", encoding="latin-1").write(
        run(["gcc", "-fpreprocessed", "-dD", "-E", "-P", os.path.join(ROOT, "port", "src", "monst.c")]))
    return xs, monst


def host(out, w, xs):
    exe = os.path.join(out, "host%d" % w)
    run(["gcc"] + HOST_CFLAGS + ["-I" + os.path.join(ROOT, "port", "include"), "-DWORK=%d" % w, "-o", exe,
                                 os.path.join(HERE, "cal.c")] + xs + [os.path.join(ROOT, "port", "src", "monst.c")])
    cg = os.path.join(out, "cg%d.out" % w)
    line = run(["valgrind", "-q", "--tool=callgrind", "--callgrind-out-file=" + cg, exe]).strip()
    total, self_ir, calls, incl, _, _ = cgsummary.load(cg)
    return line, total, self_ir, calls


def c64(out, w, xs, monst):
    o = run([OSCAR64] + C64_FLAGS + ["-ep", "-dWORK=%d" % w, "-i=" + os.path.join(out, "inc"),
                                    "-o=" + os.path.join(out, "c64_%d.prg" % w), os.path.join(HERE, "cal.c")] +
            xs + [monst], cwd=out, preexec_fn=cap)
    line = next(l for l in o.splitlines() if l.startswith("work "))
    total = int(re.search(r"^Total Cycles (\d+)$", o, re.M).group(1))
    funcs = {}
    for m in re.finditer(r"^\s+\d+ : (\S+) : (\d+)$", o, re.M):
        if not re.match(r"^[0-9a-f]{4}$", m.group(1)):
            funcs[m.group(1)] = int(m.group(2))
    return line.strip(), total, funcs


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "speed-cal"))
    ap.add_argument("--json")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    xs, monst = prepare(out)
    res = {}
    for w in [0] + sorted(WORKS):
        hl, hir, hself, hcalls = host(out, w, xs)
        cl, ccyc, cfun = c64(out, w, xs, monst)
        if hl != cl:
            sys.exit("workload %d: the builds disagree\n  host: %s\n  6502: %s" % (w, hl, cl))
        n = int(re.search(r"calls (\d+)", hl).group(1))
        res[w] = dict(checksum=hl, calls=n, host_ir=hir, host_self=dict(hself), c64_cycles=ccyc, c64_funcs=cfun)
    base = res[0]
    print("workload               calls   x86 Ir/call   6502 cycles/call   cycles per Ir")
    summary = {}
    for w in sorted(WORKS):
        r = res[w]
        ir = r["host_ir"] - base["host_ir"]
        cy = r["c64_cycles"] - base["c64_cycles"]
        summary[WORKS[w]] = dict(calls=r["calls"], ir=ir, cycles=cy, ratio=cy / ir)
        print("  %-18s %7d %12.1f %18.1f %15.1f" % (WORKS[w], r["calls"], ir / r["calls"], cy / r["calls"], cy / ir))
    for w in sorted(WORKS):
        r = res[w]
        cy = r["c64_cycles"] - base["c64_cycles"]
        print("\n%s: 6502 cycles by function (less workload 0), and x86 self Ir" % WORKS[w])
        names = set(r["c64_funcs"]) | set(k for k in r["host_self"] if k in FUNCS or k == "main")
        rows = []
        for f in names:
            c = r["c64_funcs"].get(f, 0) - base["c64_funcs"].get(f, 0)
            h = r["host_self"].get(f, 0) - base["host_self"].get(f, 0)
            if c > 0 or h > 0:
                rows.append((c, h, f))
        for c, h, f in sorted(rows, reverse=True)[:12]:
            print("  %-16s %12d cycles %5.1f%%   %10d Ir %s" % (f, c, 100.0 * c / max(1, cy), h,
                                                               "  %5.1f cycles/Ir" % (c / h) if h else ""))
    if a.json:
        exe = os.path.realpath(shutil.which(OSCAR64) or OSCAR64)
        json.dump({"tools": {"oscar64": "%s sha256 %s" % (os.path.basename(os.path.dirname(os.path.dirname(exe))),
                                                          hashlib.sha256(open(exe, "rb").read()).hexdigest()[:16]),
                             "gcc": run(["gcc", "--version"]).splitlines()[0],
                             "valgrind": run(["valgrind", "--version"]).strip()},
                   "host_cflags": HOST_CFLAGS, "c64_flags": C64_FLAGS, "workloads": summary,
                   "raw": {str(k): v for k, v in res.items()}}, open(a.json, "w"), indent=1, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
