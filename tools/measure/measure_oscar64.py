#!/usr/bin/env python3
"""
measure_oscar64.py - how much of port/src does Oscar64 compile, and how big is it?

For every port/src/*.c this builds a throw-away harness program:
    the file itself + the data files (decl/role/monst/objects/drawing)
    + generated stubs for every other extern.h function (opaque returns,
      so the optimiser cannot fold calls away)
    + a table referencing every non-static function the file defines
then reads the linker map (or error map, when it does not fit in 64KB) and
sums the native-code size of that file's functions.

It is a progress gauge for Phase 1 as much as a size estimate: the number of
files that compile goes up as port/ is fixed, and the byte totals feed the
ROM budget in docs/ARCHITECTURE.md.  It also prints sizeof() of the core
structs as Oscar64 lays them out (struct_sizes.c, run in Oscar64's emulator).

The libc/Unix shims (c64meas.h, c64meas-c64.h, stub/) exist only so files
parse; they are NOT the port's system layer.

usage: tools/measure/measure_oscar64.py [--config unix|c64] [file.c ...]
  unix (default): the host configuration (UNIX), exactly as measured for the
                  2026-11-08 baseline (docs/data/oscar64-baseline-2026-11-08.json)
  c64:            the C64 configuration (port/include/c64conf.h, -dC64, ADR-0006)
writes build/measure[-c64]/report.json and prints a table
environment: OSCAR64 (the compiler), MEASURE_TIMEOUT (seconds per file, default 150),
  MEASURE_MEMORY_MB (address-space cap per compile, default 3000; "compiler-oom" if hit)
"""
import argparse
import collections
import glob
import hashlib
import json
import os
import re
import resource
import shutil
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
OSCAR64 = os.environ.get("OSCAR64") or shutil.which("oscar64") or "oscar64"
BASE = ["decl.c", "role.c", "monst.c", "objects.c", "drawing.c"]
CONFIGS = {
    # unchanged since the 2026-11-08 baseline, so that run stays reproducible
    "unix": dict(out="measure", shim="c64meas.h", stubs=None, cpp=None,
                 defs=["-dSYSTEM_H", "-dNHSTDC", "-dUNWIDENED_PROTOTYPES", "-dregister="]),
    # c64conf.h never includes system.h, NHSTDC follows from __STDC__ and
    # config1.h sets UNWIDENED_PROTOTYPES for C64; -dregister= is compat #2.
    # mkstubs.py's gcc -E gets the same defines plus oscar64's predefines, so
    # both see one configuration.  Only errno.h is stubbed: files.c includes
    # it unconditionally; any other Unix header the C64 view reaches is an error.
    "c64": dict(out="measure-c64", shim="c64meas-c64.h", stubs=["errno.h"],
                cpp=["-DC64", "-Dregister=", "-D__OSCAR64C__=1", "-D__C64__=1", "-D__CBM__=1",
                     "-DOSCAR_TARGET_PRG=1"],
                defs=["-dC64", "-dregister="]),
}
CONFIG = "unix"
OUT = os.path.join(ROOT, "build", CONFIGS[CONFIG]["out"])
DEFS = CONFIGS[CONFIG]["defs"]
TIMEOUT = int(os.environ.get("MEASURE_TIMEOUT", "150"))
# Oscar64 can grow without bound (exponential walks over a function's flow graph: PR #440
# on explode.c reached 8-11 GB in 20 s).  Uncapped, the kernel's OOM killer stops it, or
# something else on the machine first; under the cap it ends in seconds in std::bad_alloc.
MEMORY_MB = int(os.environ.get("MEASURE_MEMORY_MB", "3000"))


def cap_memory():
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_MB << 20, MEMORY_MB << 20))


def setup():
    if not os.path.isdir(os.path.join(ROOT, "port", "src")):
        sys.exit("no port/ tree - run tools/prepare-port-tree.sh first")
    shutil.rmtree(OUT, ignore_errors=True)
    for d in ("src", "inc"):
        shutil.copytree(os.path.join(ROOT, "port", "src" if d == "src" else "include"),
                        os.path.join(OUT, d))
    stubs = CONFIGS[CONFIG]["stubs"]
    if stubs is None:
        shutil.copytree(os.path.join(HERE, "stub"), os.path.join(OUT, "stub"))
    else:
        os.makedirs(os.path.join(OUT, "stub"))
        for h in stubs:
            shutil.copy(os.path.join(HERE, "stub", h), os.path.join(OUT, "stub", h))
    shutil.copy(os.path.join(HERE, CONFIGS[CONFIG]["shim"]), os.path.join(OUT, "inc", "c64meas.h"))
    # gcc -E (used by mkstubs.py) needs Oscar64's libc headers minus #pragmas
    osc_inc = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(OSCAR64))), "include")
    fl = os.path.join(OUT, "fakelibc")
    os.makedirs(fl)
    for h in ("string.h", "stdlib.h", "stdio.h", "time.h", "stddef.h", "stdarg.h", "limits.h", "ctype.h"):
        src = os.path.join(osc_inc, h)
        if os.path.exists(src):
            text = re.sub(r"^#pragma.*$", "", open(src).read(), flags=re.M)
            open(os.path.join(fl, h), "w").write(text)
    cfg = os.path.join(OUT, "inc", "config.h")
    text = open(cfg, encoding="latin-1").read()
    text = text.replace('#include "config1.h"', '#include "c64meas.h"\n#include "config1.h"', 1)
    open(cfg, "w", encoding="latin-1").write(text)
    ux = os.path.join(OUT, "inc", "unixconf.h")
    text = open(ux, encoding="latin-1").read()
    text = re.sub(r"^#define TERMINFO", "/* #define TERMINFO */", text, flags=re.M)
    open(ux, "w", encoding="latin-1").write(text)
    # Oscar64 mis-parses some comments inside the huge MON()/OBJECT() macro
    # invocations; the data tables are measured comment-free.
    for f in ("monst.c", "objects.c"):
        p = os.path.join(OUT, "src", f)
        r = subprocess.run(["gcc", "-fpreprocessed", "-dD", "-E", "-P", p],
                           capture_output=True, text=True, encoding="latin-1")
        if r.returncode == 0:
            open(p, "w", encoding="latin-1").write(r.stdout)


def measure(f):
    b = f[:-2]
    src = open(os.path.join(OUT, "src", f), encoding="latin-1").read()
    names = set(re.findall(r"^([A-Za-z_]\w*)\s*\(", src, re.M))
    base = [x for x in BASE if x != f]
    h = os.path.join(OUT, "h_%s.c" % b)
    env = {k: v for k, v in os.environ.items() if k != "MKSTUBS_DEFS"}
    if CONFIGS[CONFIG]["cpp"] is not None:
        env["MKSTUBS_DEFS"] = " ".join(CONFIGS[CONFIG]["cpp"])
    g = subprocess.run([sys.executable, os.path.join(HERE, "mkstubs.py"), os.path.join(OUT, "inc"),
                        os.path.join(OUT, "src"), f, h] + base, capture_output=True, text=True,
                       env=env)
    if g.returncode:
        return {"status": "stubgen-fail"}
    out = os.path.join(OUT, "m_%s.prg" % b)
    cmd = [OSCAR64, "-rmp", "-Os", "-i=" + os.path.join(OUT, "inc"), "-i=" + os.path.join(OUT, "stub"),
           "-o=" + out, os.path.join(OUT, "src", f)] + DEFS + \
          [os.path.join(OUT, "src", x) for x in base] + [h]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=OUT, timeout=TIMEOUT,
                           preexec_fn=cap_memory)
    except subprocess.TimeoutExpired:
        return {"status": "compiler-hang"}
    crashed = r.returncode < 0 or r.returncode >= 128
    # bad_alloc: the cap stopped it; SIGKILL that is not our timeout: the OOM killer did
    if crashed and ("std::bad_alloc" in r.stderr or r.returncode == -9):
        return {"status": "compiler-oom"}
    errs = [l for l in (r.stdout + r.stderr).splitlines() if "error" in l]
    if crashed and not errs:
        # the signal tells a segfault (11) from an abort (6); a crash that does not
        # repeat needs it (vault.c crashed once in 77 runs on 2026-11-12)
        return {"status": "compiler-crash",
                "signal": -r.returncode if r.returncode < 0 else r.returncode - 128}
    # (v1.32.273: -rmp itself segfaults after ordinary compile errors; those
    #  files are reported as compile-error, which is the real problem.)
    m = out[:-4] + ".map" if os.path.exists(out[:-4] + ".map") else out[:-4] + ".error.map"
    code, seen = 0, set()
    if os.path.exists(m):
        for line in open(m):
            mm = re.match(r"^([0-9a-f]{4}) - ([0-9a-f]{4}) : (\w+), NATIVE_CODE:", line)
            if mm and mm.group(3) in names and mm.group(3) not in seen:
                seen.add(mm.group(3))
                code += int(mm.group(2), 16) - int(mm.group(1), 16)
    placement_only = all("Could not place" in e or "Cannot place" in e for e in errs)
    status = "ok" if not errs else ("fits-not" if placement_only and seen else "compile-error")
    for p in glob.glob(os.path.join(OUT, "m_%s*" % b)) + [h]:
        os.remove(p)
    return {"status": status, "code": code, "funcs": "%d/%d" % (len(seen), len(names)),
            "error": re.sub(r".*/", "", errs[0]) if status == "compile-error" else ""}


def struct_sizes():
    r = subprocess.run([OSCAR64, "-e", "-i=" + os.path.join(OUT, "inc"), "-i=" + os.path.join(OUT, "stub"),
                        "-o=" + os.path.join(OUT, "sizes.prg"), os.path.join(HERE, "struct_sizes.c")] + DEFS,
                       capture_output=True, text=True, cwd=OUT, timeout=TIMEOUT, preexec_fn=cap_memory)
    sizes = [l for l in r.stdout.splitlines() if re.match(r"^[a-z_]+ \d", l)]
    if not sizes:
        errs = [l for l in (r.stdout + r.stderr).splitlines() if "error" in l]
        print("struct_sizes.c failed (rc %d): %s" % (r.returncode, errs[0] if errs else "no output"),
              file=sys.stderr)
    return sizes


# git-ignored makedefs output (tools/host-build.sh --generate-only)
GENERATED = ("include/pm.h", "include/onames.h", "include/date.h", "include/vis_tab.h", "src/vis_tab.c")


def provenance():
    """Where the numbers came from; tools that compare reports skip '_' keys."""
    def out(cmd):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return ""
        # a failing command (git outside a checkout) records nothing, not its error text
        return (r.stdout + r.stderr).strip() if r.returncode == 0 else ""
    def ver(s):
        m = re.search(r"\d+\.\d+\.\d+", s)
        return m.group(0) if m else "unknown"
    gen = hashlib.sha256()
    for p in GENERATED:
        if p == "include/date.h":
            continue    # build timestamp; the tables are what matters
        with open(os.path.join(ROOT, "port", p), "rb") as fh:
            gen.update(fh.read())
    exe = shutil.which(OSCAR64) or OSCAR64
    try:
        with open(exe, "rb") as fh:
            exe_sha = hashlib.sha256(fh.read()).hexdigest()[:16]
    except OSError:
        exe_sha = "unknown"
    # the version alone does not tell v1.32.273 from v1.32.273 plus patches (ADR-0007)
    return {"config": CONFIG, "oscar64_defs": DEFS, "mkstubs_defs": CONFIGS[CONFIG]["cpp"],
            "oscar64": ver(out([OSCAR64, "-v"])), "oscar64_sha256": exe_sha,
            "memory_limit_mb": MEMORY_MB, "gcc": ver(out(["gcc", "-dumpfullversion"])),
            "git": out(["git", "-C", ROOT, "describe", "--always", "--dirty"]) or "unknown",
            "generated_tables_sha256": gen.hexdigest()[:16],
            "date": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}


def main():
    global CONFIG, OUT, DEFS
    ap = argparse.ArgumentParser(description="Oscar64 compile status and code size per port/src file")
    ap.add_argument("--config", choices=sorted(CONFIGS), default="unix")
    ap.add_argument("files", nargs="*", help="port/src files (default: all)")
    args = ap.parse_args()
    # check names before setup() deletes the previous run's output
    bad = [f for f in args.files if os.path.basename(f) != f or not f.endswith(".c")
           or not os.path.isfile(os.path.join(ROOT, "port", "src", f))]
    if bad:
        ap.error("not a port/src/*.c file name: " + " ".join(bad))
    # without makedefs' output every file would fail; say so instead of measuring
    missing = [p for p in GENERATED if not os.path.isfile(os.path.join(ROOT, "port", p))]
    if missing:
        sys.exit("missing generated port/%s: run tools/host-build.sh --generate-only"
                 % ", port/".join(missing))
    CONFIG = args.config
    OUT = os.path.join(ROOT, "build", CONFIGS[CONFIG]["out"])
    DEFS = CONFIGS[CONFIG]["defs"]
    setup()
    files = args.files or sorted(os.path.basename(p) for p in glob.glob(os.path.join(OUT, "src", "*.c")))
    report = {}
    for f in files:
        res = measure(f)
        report[f] = res
        print("%-12s %-14s %6s  %s %s" % (f, res["status"], res.get("code", ""), res.get("funcs", ""),
                                          res.get("error", "")), flush=True)
    sizes = struct_sizes()
    report["_struct_sizes"] = sizes
    report["_meta"] = provenance()
    json.dump(report, open(os.path.join(OUT, "report.json"), "w"), indent=1)
    good = [r for k, r in report.items() if not k.startswith("_") and r.get("code")]
    print("\nfiles measured: %d of %d, native code in those: %d bytes" %
          (len(good), len(files), sum(r["code"] for r in good)))
    status = collections.Counter(r["status"] for k, r in report.items() if not k.startswith("_"))
    print("status (%s config):" % CONFIG, ", ".join("%d %s" % (n, s) for s, n in sorted(status.items())))
    print("struct sizes (Oscar64):", "; ".join(sizes))


if __name__ == "__main__":
    main()
