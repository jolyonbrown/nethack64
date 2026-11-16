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

--far TAG (repeatable) adds a far build of the 6502 side (T2.11): farify.py rewrites every
access through a `struct TAG *` to go through that type's table of pages first (far_pre.h),
the pointers being far addresses NH_VOFF from the real ones; the checksums must still be the
host's, and no page may fault.  --far-volatile makes the tables volatile: no translation is
reused, one an access.  --far-reuse models a compiler that translates a pointer once a value
(farify.py --reuse: variables with one definition; --far-reuse-all: all of them, at each
definition); --far-expand only macro-expands the functions first (the control for both).
Each far run also prints, for each workload, where the far cost goes, function by function.

Every 6502 listing is checked (tools/check_listing.py): no branch out of range (compat #73),
and no zero-page temporary past $8F, the end of Oscar64's area on the C64 (compat #72); past
it, the KERNAL's IRQ changes them on the real machine, and the emulator ticks the jiffy clock
at $A0-$A2.  A far build is an experiment, so a temporary in $90-$9F is reported as a finding
(the code would not run on a C64 as it is) and the run goes on; past $9F it stops too.
"""
import argparse
import glob
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
sys.path.insert(0, os.path.join(ROOT, "tools"))
import cgsummary  # noqa: E402
import check_listing  # noqa: E402

OSCAR64 = os.environ.get("OSCAR64") or shutil.which("oscar64") or "oscar64"
WORKS = {1: "isok", 2: "dist2", 3: "is_pool + is_lava", 4: "mfndpos"}
FUNCS = ["isok", "dist2", "distmin", "online2", "strstri", "lowc", "is_pool", "is_lava", "on_level",
         "mfndpos", "mm_aggression", "curr_mon_load", "may_passwall", "may_dig", "bad_rock", "onscary",
         "sengr_at", "engr_at", "sobj_at", "t_at", "m_carrying", "which_armor"]
# as tools/host-build.sh compiles src/
HOST_CFLAGS = ["-O", "-g", "-std=gnu89", "-w", "-DUNWIDENED_PROTOTYPES"]
# as tools/bank/build_c64.py and measure_oscar64.py's c64 configuration compile it
C64_FLAGS = ["-Os", "-xb", "-dC64", "-dregister="]	# -xb: as the game, which never returns to BASIC
ZP_END = check_listing.ZP_END	# the last byte of Oscar64's temporaries on the C64 (oscar64.md)
ZP_CLOCK = 0xA0		# the KERNAL's jiffy clock, $A0-$A2, which Oscar64's emulator ticks too


def cap():
    resource.setrlimit(resource.RLIMIT_AS, (3000 << 20, 3000 << 20))


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit("failed (%d): %s\n%s%s" % (r.returncode, " ".join(cmd), r.stdout[-3000:], r.stderr[-3000:]))
    return r.stdout


def zp_check(listing, what, experiment=False):
    """The listing's highest temporary, as text, and (in an experiment) the functions past $8F.
    Stops on a branch out of range, or a temporary past $8F (past $9F in an experiment)."""
    problems, top = check_listing.check(listing, ZP_CLOCK - 1 if experiment else ZP_END)
    if problems:
        sys.exit("%s: %s\n  %s" % (what, listing, "\n  ".join(problems)))
    past = check_listing.check(listing, ZP_END)[0] if experiment else []
    return ("$%02x %s" % top if top else "none"), past


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
    zp, _ = zp_check(os.path.join(out, "c64_%d.asm" % w), "workload %d" % w)
    line = next(l for l in o.splitlines() if l.startswith("work "))
    total = int(re.search(r"^Total Cycles (\d+)$", o, re.M).group(1))
    funcs = {}
    for m in re.finditer(r"^\s+\d+ : (\S+) : (\d+)$", o, re.M):
        if not re.match(r"^[0-9a-f]{4}$", m.group(1)):
            funcs[m.group(1)] = int(m.group(2))
    return line.strip(), total, funcs, zp


NH_VOFF = 0x4000


def far_runs(a, out, res, monst):
    fdir = os.path.join(out, "far")
    mode = ["--reuse-all"] if a.far_reuse_all else ["--reuse"] if a.far_reuse else ["--expand"] if a.far_expand else []
    print("\nfar build: " + run([sys.executable, os.path.join(HERE, "farify.py"), "--src", os.path.join(out, "x"),
                                 "--inc", os.path.join(out, "inc"), "--out", fdir] +
                                ["--type=" + t for t in a.far] + ["--cflag=-DC64", "--cflag=-Dregister="] + mode)
          .strip().replace("\n", "\n  "))
    defs = ["-dNH_FAR", "-dNH_VOFF=%d" % NH_VOFF] + ["-dNH_FAR_%s" % t.upper() for t in a.far] + \
        (["-dmons=nh_mons_real"] if "permonst" in a.far else []) + \
        (["-dNH_FAR_VOLATILE"] if a.far_volatile else []) + (["-dNH_FAR_COUNT"] if a.far_count else [])
    xs = sorted(glob.glob(os.path.join(fdir, "x", "x_*.c")))
    rows, counts, zps, past, ffuncs = {}, {}, {}, [], {}
    for w in [0] + sorted(WORKS):
        o = run([OSCAR64] + C64_FLAGS + ["-ep", "-dWORK=%d" % w, "-i=" + os.path.join(fdir, "inc")] + defs +
                ["-o=" + os.path.join(fdir, "c64_%d.prg" % w), os.path.join(HERE, "cal.c")] + xs + [monst],
                cwd=fdir, preexec_fn=cap)
        zps[w], p = zp_check(os.path.join(fdir, "c64_%d.asm" % w), "far build, workload %d" % w, True)
        past += ["workload %d: %s" % (w, x) for x in p]
        line = next(l for l in o.splitlines() if l.startswith("work ")).strip()
        faults = int(re.search(r"^faults (\d+)$", o, re.M).group(1))
        if line != res[w]["checksum"] or faults:
            sys.exit("far build, workload %d: %s, %d faults (the host: %s)" % (w, line, faults, res[w]["checksum"]))
        rows[w] = int(re.search(r"^Total Cycles (\d+)$", o, re.M).group(1))
        ffuncs[w] = {}
        for m in re.finditer(r"^\s+\d+ : (\S+) : (\d+)$", o, re.M):
            if not re.match(r"^[0-9a-f]{4}$", m.group(1)):
                ffuncs[w][m.group(1)] = ffuncs[w].get(m.group(1), 0) + int(m.group(2))
        m = re.search(r"^count (.*)$", o, re.M)
        if m:
            counts[w] = dict(zip(m.group(1).split()[0::2], map(int, m.group(1).split()[1::2])))
    print("far %s%s%s, same checksums, no faults; highest zero-page temporaries: %s" % (
        "+".join(a.far), " (volatile tables)" if a.far_volatile else "", (" (" + mode[0][2:] + ")") if mode else "",
        ", ".join("%d %s" % (w, zps[w]) for w in sorted(zps))))
    for x in past:
        print("  past Oscar64's zero page, would not run on a C64 as it is: " + x)
    print("workload              near cycles/call   far cycles/call   slower")
    summary = {}
    for w in sorted(WORKS):
        n = (res[w]["c64_cycles"] - res[0]["c64_cycles"]) / res[w]["calls"]
        f = (rows[w] - rows[0]) / res[w]["calls"]
        summary[WORKS[w]] = dict(near=n, far=f)
        print("  %-18s %18.1f %17.1f %8.2fx" % (WORKS[w], n, f, f / n))
    for w in sorted(WORKS):
        n = res[w]["calls"]
        cost = []
        for f in set(ffuncs[w]) | set(res[w]["c64_funcs"]):
            d = ((ffuncs[w].get(f, 0) - ffuncs[0].get(f, 0)) -
                 (res[w]["c64_funcs"].get(f, 0) - res[0]["c64_funcs"].get(f, 0))) / n
            if abs(d) >= 0.5:
                cost.append((d, f))
        summary[WORKS[w]]["far_cost_by_function"] = {f: round(d, 1) for d, f in cost}
        print("  far cost a call, %s: %s" % (WORKS[w], ", ".join("%s %+.1f" % (f, d) for d, f in
                                                              sorted(cost, reverse=True)[:6]) or "none"))
    if counts:
        print("translations a call (less workload 0):")
        for w in sorted(WORKS):
            c = {k: (v - counts[0].get(k, 0)) / res[w]["calls"] for k, v in counts[w].items()}
            summary[WORKS[w]]["translations"] = c
            print("  %-18s %s" % (WORKS[w], "  ".join("%s %.1f" % kv for kv in c.items())))
    return dict(types=a.far, volatile=a.far_volatile, mode=mode[0][2:] if mode else "plain", workloads=summary,
                zp_high={str(w): v for w, v in zps.items()}, zp_past_8f=past)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "speed-cal"))
    ap.add_argument("--json")
    ap.add_argument("--far", action="append", default=[], metavar="TAG")
    ap.add_argument("--far-volatile", action="store_true")
    ap.add_argument("--far-count", action="store_true", help="count the translations of each type (slower)")
    ap.add_argument("--far-expand", action="store_true", help="farify.py --expand (the control for --far-reuse)")
    ap.add_argument("--far-reuse", action="store_true", help="farify.py --reuse")
    ap.add_argument("--far-reuse-all", action="store_true", help="farify.py --reuse-all")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    xs, monst = prepare(out)
    res = {}
    for w in [0] + sorted(WORKS):
        hl, hir, hself, hcalls = host(out, w, xs)
        cl, ccyc, cfun, zp = c64(out, w, xs, monst)
        if hl != cl:
            sys.exit("workload %d: the builds disagree\n  host: %s\n  6502: %s" % (w, hl, cl))
        n = int(re.search(r"calls (\d+)", hl).group(1))
        res[w] = dict(checksum=hl, calls=n, host_ir=hir, host_self=dict(hself), c64_cycles=ccyc, c64_funcs=cfun,
                      zp_high=zp)
    base = res[0]
    print("workload               calls   x86 Ir/call   6502 cycles/call   cycles per Ir")
    summary = {}
    for w in sorted(WORKS):
        r = res[w]
        ir = r["host_ir"] - base["host_ir"]
        cy = r["c64_cycles"] - base["c64_cycles"]
        summary[WORKS[w]] = dict(calls=r["calls"], ir=ir, cycles=cy, ratio=cy / ir)
        print("  %-18s %7d %12.1f %18.1f %15.1f" % (WORKS[w], r["calls"], ir / r["calls"], cy / r["calls"], cy / ir))
    print("highest zero-page temporaries (Oscar64's area ends at $%02X): %s" % (
        ZP_END, ", ".join("%d %s" % (w, res[w]["zp_high"]) for w in sorted(res))))
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
    far = None
    if a.far:
        far = far_runs(a, out, res, monst)
    if a.json:
        exe = os.path.realpath(shutil.which(OSCAR64) or OSCAR64)
        json.dump({"tools": {"oscar64": "%s sha256 %s" % (os.path.basename(os.path.dirname(os.path.dirname(exe))),
                                                          hashlib.sha256(open(exe, "rb").read()).hexdigest()[:16]),
                             "gcc": run(["gcc", "--version"]).splitlines()[0],
                             "valgrind": run(["valgrind", "--version"]).strip()},
                   "host_cflags": HOST_CFLAGS, "c64_flags": C64_FLAGS, "workloads": summary, "far": far,
                   "raw": {str(k): v for k, v in res.items()}}, open(a.json, "w"), indent=1, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
