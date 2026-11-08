#!/usr/bin/env python3
"""Generate an oscar64 measurement harness for one NetHack source file.

usage: mkstubs.py incdir srcdir target.c out.c [also_defined.c ...]
"""
import os, re, subprocess, sys

inc, srcdir, target, out = sys.argv[1:5]
also = sys.argv[5:]
base = os.path.dirname(os.path.abspath(inc))
pp = subprocess.run(
    ["gcc", "-E", "-P", "-nostdinc", "-I", inc, "-I", os.path.join(base, "stub"),
     "-I", os.path.join(base, "fakelibc"),
     "-DSYSTEM_H", "-DNHSTDC", "-DUNWIDENED_PROTOTYPES", "-Dregister=", "-D__attribute__(x)=",
     os.path.join(inc, "hack.h")],
    capture_output=True, text=True, encoding="latin-1")
if pp.returncode:
    sys.stderr.write(pp.stderr[:3000]); sys.exit(1)
text = pp.stdout

def defs(path):
    s = open(path, encoding="latin-1").read()
    return set(re.findall(r"^([A-Za-z_]\w*)\s*\(", s, re.M)), s

defined, src = defs(os.path.join(srcdir, target))
for extra in also:
    defined |= defs(os.path.join(srcdir, extra))[0]
static_names = set(re.findall(
    r"^(?:STATIC_OVL|static|STATIC_PTR)\b[^\n;(]*\n([A-Za-z_]\w*)\s*\(", src, re.M))

protos = []
for m in re.finditer(r"^extern\s+([^;()]*?)\b([A-Za-z_]\w*)\s*\(([^;]*)\)\s*;\s*$", text, re.M):
    if m.group(2) in ("int", "char", "long", "void", "__attribute__") or "__attribute__" in m.group(3) or "(*" in m.group(1):
        continue
    protos.append((m.group(1).strip(), m.group(2), m.group(3).strip()))

lines = ['#include "hack.h"', '#include "dlb.h"', "",
         "/* opaque return values so the optimiser cannot fold stubbed calls */",
         "volatile long nh_vl; void * volatile nh_vp;", ""]
refs, seen = [], set()
for ret, name, args in protos:
    if name in seen:
        continue
    seen.add(name)
    if name in defined:
        if name not in static_names:
            refs.append(name)
        continue
    params = args if args else "void"
    is_void = re.fullmatch(r"(?:static\s+)?void", ret) is not None
    lines.append("#undef %s" % name)
    if is_void:
        body = ""
    elif "*" in ret:
        body = " return (%s)nh_vp; " % ret
    else:
        body = " return (%s)nh_vl; " % ret
    lines.append("%s %s(%s) {%s}" % (ret, name, params, body))

lines += ["", "void *nh_refs[] = {"] + ["  (void *)%s," % r for r in refs] + [
    "  0 };", "int main(void) { volatile int i; for (i = 0; nh_refs[i]; i++) ; return i; }"]
open(out, "w").write("\n".join(lines) + "\n")
print("refs:", len(refs), "stubs:", len(seen) - len(refs))
