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

The libc/Unix shim (c64meas.h, stub/) exists only so files parse; it is NOT
the port's system layer.

usage: tools/measure/measure_oscar64.py [file.c ...]   (default: all)
writes build/measure/report.json and prints a table
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "build", "measure")
OSCAR64 = os.environ.get("OSCAR64") or shutil.which("oscar64") or "oscar64"
BASE = ["decl.c", "role.c", "monst.c", "objects.c", "drawing.c"]
DEFS = ["-dSYSTEM_H", "-dNHSTDC", "-dUNWIDENED_PROTOTYPES", "-dregister="]
TIMEOUT = int(os.environ.get("MEASURE_TIMEOUT", "150"))


def setup():
    if not os.path.isdir(os.path.join(ROOT, "port", "src")):
        sys.exit("no port/ tree - run tools/prepare-port-tree.sh first")
    shutil.rmtree(OUT, ignore_errors=True)
    for d in ("src", "inc"):
        shutil.copytree(os.path.join(ROOT, "port", "src" if d == "src" else "include"),
                        os.path.join(OUT, d))
    shutil.copytree(os.path.join(HERE, "stub"), os.path.join(OUT, "stub"))
    shutil.copy(os.path.join(HERE, "c64meas.h"), os.path.join(OUT, "inc"))
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
    g = subprocess.run([sys.executable, os.path.join(HERE, "mkstubs.py"), os.path.join(OUT, "inc"),
                        os.path.join(OUT, "src"), f, h] + base, capture_output=True, text=True)
    if g.returncode:
        return {"status": "stubgen-fail"}
    out = os.path.join(OUT, "m_%s.prg" % b)
    cmd = [OSCAR64, "-rmp", "-Os", "-i=" + os.path.join(OUT, "inc"), "-i=" + os.path.join(OUT, "stub"),
           "-o=" + out, os.path.join(OUT, "src", f)] + DEFS + \
          [os.path.join(OUT, "src", x) for x in base] + [h]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=OUT, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"status": "compiler-hang"}
    crashed = r.returncode < 0 or r.returncode >= 128
    errs = [l for l in (r.stdout + r.stderr).splitlines() if "error" in l]
    if crashed and not errs:
        return {"status": "compiler-crash"}
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
                       capture_output=True, text=True, cwd=OUT, timeout=TIMEOUT)
    return [l for l in r.stdout.splitlines() if re.match(r"^[a-z_]+ \d", l)]


def main():
    setup()
    files = sys.argv[1:] or sorted(os.path.basename(p) for p in glob.glob(os.path.join(OUT, "src", "*.c")))
    report = {}
    for f in files:
        res = measure(f)
        report[f] = res
        print("%-12s %-14s %6s  %s %s" % (f, res["status"], res.get("code", ""), res.get("funcs", ""),
                                          res.get("error", "")), flush=True)
    sizes = struct_sizes()
    report["_struct_sizes"] = sizes
    json.dump(report, open(os.path.join(OUT, "report.json"), "w"), indent=1)
    good = [r for k, r in report.items() if not k.startswith("_") and r.get("code")]
    print("\nfiles measured: %d of %d, native code in those: %d bytes" %
          (len(good), len(files), sum(r["code"] for r in good)))
    print("struct sizes (Oscar64):", "; ".join(sizes))


if __name__ == "__main__":
    main()
