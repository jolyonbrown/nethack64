#!/usr/bin/env python3
"""Per-function code sizes and the static call graph of NetHack, from a kept harness run.

usage: tools/measure/callgraph.py [MEASURE_DIR] [-o OUT.json]

MEASURE_DIR is a measure_oscar64.py output directory kept with MEASURE_KEEP=1 (default
build/measure-c64).  For each measured file it reads the map (function sizes, including
functions the harness could not place, which the map lists at address 0000), the
listing (calls: JSR and JMP to another function's entry) and the `.defs` sidecar (the
functions the file defines).  A call to another file's function lands on that file's stub
in the harness, so callees resolve by name across files.  Static functions that the
optimiser inlined have no code of their own and do not appear; their bytes are in their
callers.  Static names that more than one file defines are qualified as `file.c:name`.

Output JSON: {"functions": {name: {"file", "size", "static", "calls": {callee: sites}}},
"files": {file: {"code", "functions"}}, "data": {object: size} for named data objects}.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAPLINE = re.compile(r"^([0-9a-f]{4,5}) - ([0-9a-f]{4,5}) : ([A-Za-z_]\w*), NATIVE_CODE:code\s*$")
DATALINE = re.compile(r"^([0-9a-f]{4,5}) - ([0-9a-f]{4,5}) : ([A-Za-z_]\w*), DATA:data\s*$")
HEAD = re.compile(r"^([A-Za-z_]\w*): ; ")
CALL = re.compile(r"^[0-9a-f]{4} : (?:[0-9a-f_]{2} ){3}(JSR|JMP)\s+\S+\s*; \(([A-Za-z_]\w*?)(?:\.s\d+)? \+ (\d+)\)")
STATIC = re.compile(r"(?m)^(?:static|STATIC_OVL|STATIC_PTR)\b[^;{]*?\b([A-Za-z_]\w*)\s*\(")


def statics_of(path):
    """Names of the functions a source file defines as static (STATIC_OVL/STATIC_PTR
    expand to static in the measured configurations)."""
    src = open(path, encoding="latin-1").read()
    names = set(STATIC.findall(src))
    # K&R-converted definitions put the storage class on the line before the name
    for m in re.finditer(r"(?m)^(?:static|STATIC_OVL|STATIC_PTR)\b[^;{(]*\n([A-Za-z_]\w*)\s*\(", src):
        names.add(m.group(1))
    return names


def read_file(out, src_c):
    b = src_c[:-2]
    stem = os.path.join(out, "m_" + b)
    mp = stem + ".error.map" if os.path.exists(stem + ".error.map") else stem + ".map"
    asm = mp[:-4] + ".asm"
    defs_p = os.path.join(out, "h_%s.defs" % b)
    if not (os.path.exists(mp) and os.path.exists(asm) and os.path.exists(defs_p)):
        return None
    own = set(open(defs_p).read().split())
    sizes, data = {}, {}
    for line in open(mp, errors="replace"):
        m = MAPLINE.match(line)
        if m and m.group(3) in own and m.group(3) not in sizes:
            sizes[m.group(3)] = int(m.group(2), 16) - int(m.group(1), 16)
        m = DATALINE.match(line)
        if m:
            data[m.group(3)] = int(m.group(2), 16) - int(m.group(1), 16)
    calls = collections.defaultdict(collections.Counter)
    cur = None
    for line in open(asm, errors="replace"):
        m = HEAD.match(line)
        if m:
            cur = m.group(1)
            continue
        m = CALL.match(line)
        if m and cur in own:
            callee = m.group(2)
            if callee != cur:
                calls[cur][callee] += 1
    return own, sizes, calls, data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", nargs="?", default=os.path.join(ROOT, "build", "measure-c64"))
    ap.add_argument("-o", "--out", default=None)
    a = ap.parse_args()
    files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(a.dir, "src", "*.c")))
    per_file, defined_by = {}, collections.defaultdict(list)
    for f in files:
        r = read_file(a.dir, f)
        if r is None:
            continue
        per_file[f] = r
        for name in r[1]:
            defined_by[name].append(f)
    funcs, data = {}, {}
    for f, (own, sizes, calls, d) in per_file.items():
        st = statics_of(os.path.join(a.dir, "src", f))
        for name, size in sizes.items():
            key = name if len(defined_by[name]) == 1 or name not in st else "%s:%s" % (f, name)
            funcs[key] = {"file": f, "size": size, "static": name in st,
                          "calls": dict(calls.get(name, {}))}
        for k, v in d.items():
            data[k] = max(data.get(k, 0), v)
    # qualify calls to file-static names from their own file
    for key, fn in funcs.items():
        q = {}
        for callee, n in fn["calls"].items():
            local = "%s:%s" % (fn["file"], callee)
            q[local if local in funcs else callee] = n
        fn["calls"] = q
    report = {"source": os.path.relpath(a.dir, ROOT), "functions": funcs,
              "files": {f: {"code": sum(v["size"] for v in funcs.values() if v["file"] == f),
                            "functions": sum(1 for v in funcs.values() if v["file"] == f)}
                        for f in per_file},
              "data": data}
    out = a.out or os.path.join(a.dir, "callgraph.json")
    json.dump(report, open(out, "w"), indent=1, sort_keys=True)
    total = sum(v["size"] for v in funcs.values())
    print("%d files, %d functions, %d bytes of code; %d call edges -> %s" % (
        len(per_file), len(funcs), total, sum(len(v["calls"]) for v in funcs.values()), out))


if __name__ == "__main__":
    sys.exit(main())
