#!/usr/bin/env python3
"""wholesizes.py - function sizes from a whole-game Oscar64 build, for bankpart.py.

usage: tools/measure/wholesizes.py --map M --int I [--graph-in G] --out OUT

The per-file measurement (callgraph.py) sizes each function with other files' functions
replaced by stubs, which take their parameters in the zero page; in the game many callees
are recursive or address-taken and take them on the stack, so the code comes out larger
(BANKING-SPIKE.md: 1.16x).  This reads the map and the intermediate code of a whole-game
build (tools/bank/build_c64.py, even one whose link failed: the map lists unplaced objects
too) and writes {"functions": {name: {"size": B, "file": "f.c"}}} in callgraph.py's form.
A banked function's size is its name__bN object's, a resident one's its own; trampolines
(a resident name with a banked twin) are left out, since bankgen.py makes them.  Files come
from --graph-in where it knows the name, else from the source of the procedure's first
block in the intermediate code.  A function the build has no code for (inlined wherever it
was called, or never reached) is left out, and bankpart.py folds it into its callers.
--with-literals adds to each function the literals the map places after it in its section,
which is where Oscar64 puts a function's string constants: then bankpart.py needs no
--literals estimate.  Literals a failed link left unplaced are spread over the functions of
their section in proportion to the literals already credited to them.
"""
import argparse
import json
import os
import re
import sys

OBJ = re.compile(r"^(?:(?:--|[0-9a-f]{2}):)?([0-9a-f]{4,5}) - ([0-9a-f]{4,5}) : ([^,]+), (\w+):(\S+)")
BANKED = re.compile(r"^(\w+)__b(\d+)$")
PROC = re.compile(r"^([A-Za-z_]\w*): \S")
BLOCK_SRC = re.compile(r"^L\d+: .* (\S+/src/([\w.]+\.c))\s*$")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--map", required=True)
    ap.add_argument("--int", required=True)
    ap.add_argument("--graph-in", default=None, help="callgraph.py output, for files")
    ap.add_argument("--out", required=True)
    ap.add_argument("--with-literals", action="store_true",
                    help="add the literals placed after each function to its size")
    a = ap.parse_args()

    code, lit, last, left, sec_of = {}, {}, {}, {}, {}
    for line in open(a.map, errors="replace"):
        m = OBJ.match(line)
        if not m:
            continue
        n = int(m.group(2), 16) - int(m.group(1), 16)
        placed = not line.startswith("0000 -")
        if m.group(4) == "NATIVE_CODE":
            if n > 0:
                code[m.group(3)] = (n, m.group(5).startswith("nhbank_"))
                sec_of[m.group(3)] = m.group(5)
                if placed:
                    last[m.group(5)] = m.group(3)
        elif m.group(4) == "DATA" and placed and n > 0 and m.group(3) == "*" and m.group(5) in last:
            owner = last[m.group(5)]
            lit[owner] = lit.get(owner, 0) + n
        elif m.group(4) == "DATA" and not placed and n > 0 and m.group(3) == "*":
            left[m.group(5)] = left.get(m.group(5), 0) + n
    if a.with_literals:
        for sec, n in left.items():
            owners = {f: k for f, k in lit.items() if f in code and last.get(sec) and sec_of.get(f) == sec}
            share = sum(owners.values())
            for f, k in owners.items():
                lit[f] += n * k // share
    twins = {BANKED.match(k).group(1): n for k, (n, banked) in code.items() if banked and BANKED.match(k)}

    src = {}
    proc, header = None, True
    for line in open(a.int, errors="replace"):
        if line.startswith("----"):
            header = True
            continue
        if header:
            m = PROC.match(line)
            proc, header = (m.group(1) if m else None), False
            continue
        if proc and proc not in src:
            m = BLOCK_SRC.match(line)
            if m:
                src[re.sub(r"__b\d+$", "", proc)] = m.group(2)

    known = {}
    if a.graph_in and os.path.exists(a.graph_in):
        for k, v in json.load(open(a.graph_in))["functions"].items():
            known[k.split(":")[-1]] = v["file"]

    out, skipped = {}, 0
    for k, (n, banked) in code.items():
        name = BANKED.match(k).group(1) if BANKED.match(k) else k
        if not banked and name in twins:
            continue                       # a trampoline
        if not banked and name in out:
            continue
        f = known.get(name) or src.get(name)
        if not f:
            skipped += 1                   # not NetHack's (libc, the runtime, stubs)
            continue
        size = twins.get(name, n)
        if a.with_literals:
            size += lit.get(k, 0)        # the object's own literals (a banked twin's, not its trampoline's)
        out[name] = {"size": size, "file": f}
    json.dump({"functions": out}, open(a.out, "w"), indent=0, sort_keys=True)
    print("%d functions, %d B%s, from %d files; %d code objects outside NetHack's sources" % (
        len(out), sum(v["size"] for v in out.values()), " with %d B of literals" % sum(lit.values()) if a.with_literals else "",
        len({v["file"] for v in out.values()}), skipped))


if __name__ == "__main__":
    sys.exit(main())
