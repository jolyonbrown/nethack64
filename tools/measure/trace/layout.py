#!/usr/bin/env python3
"""layout.py - the table tools/measure/trace/nh_trace.c reads: the traced host game's globals
matched by name to the whole-game C64 build's, each with its C64 size, its kind and an address
in a C64 far space laid out kind by kind, page-aligned (docs/RAM-PLAN.md).

usage: tools/measure/trace/layout.py --game EXE --map C64.map --tree HOSTTREE --out FILE

--tree is the traced host build's tree (tools/host-build.sh --trace: build/host-trace), whose
headers give the host's sizeof(struct obj_s) and sizeof(struct monst_s) (the port's tags).  C64 data comes from the
map's data and bss sections and the strings in its resident code section; static frames
(locals: near in any far-data model) and the banks' own literals are left out.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

KINDS = ["other", "level", "vision", "display", "mons", "objects", "globals", "strings", "heap"]
VISION = {"could_see", "cs_rows0", "cs_rows1", "cs_rmin0", "cs_rmax0", "cs_rmin1", "cs_rmax1",
          "viz_clear", "viz_clear_rows", "left_ptrs", "right_ptrs", "viz_array", "viz_rmin", "viz_rmax"}
DISPLAY = {"gbuf", "gbuf_start", "gbuf_stop"}
OBJ = re.compile(r"^(?:(--|[0-9a-f]{2}):)?([0-9a-f]{4,5}) - ([0-9a-f]{4,5}) : ([^,]+), (\w+):(\S+)$")


def kind_of(name):
    if name == "level":
        return 1
    if name in VISION:
        return 2
    if name in DISPLAY:
        return 3
    if name == "mons":
        return 4
    if name in ("objects", "obj_descr"):
        return 5
    return 6


def c64_objects(mapfile):
    """{name: c64 size} of the named resident data, and the resident strings' total."""
    named, strings = {}, 0
    for line in open(mapfile, errors="replace"):
        m = OBJ.match(line.rstrip("\n"))
        if not m or m.group(5) not in ("DATA", "BSS"):
            continue
        if m.group(1) not in (None, "--"):
            continue                     # in a bank
        sec, name = m.group(6), m.group(4)
        if sec.startswith("nhbank_") or "@" in sec:
            continue
        a, b = int(m.group(2), 16), int(m.group(3), 16)
        size = b if (m.group(1) is None and m.group(2) == "0000") else b - a
        if size <= 0:
            continue
        if sec == "code" and name == "*":
            strings += size
        elif sec in ("data", "bss", "code") and name != "*":
            named[name] = max(named.get(name, 0), size)
    return named, strings


def host_sizes(tree):
    probe = '#include "hack.h"\n#include <stdio.h>\nint main(void) { printf("%u %u\\n", ' \
            '(unsigned)sizeof(struct obj_s), (unsigned)sizeof(struct monst_s)); return 0; }\n'
    with tempfile.TemporaryDirectory() as d:
        c, exe = os.path.join(d, "p.c"), os.path.join(d, "p")
        open(c, "w").write(probe)
        r = subprocess.run(["cc", "-std=gnu89", "-w", "-DUNWIDENED_PROTOTYPES", "-I" + os.path.join(tree, "include"),
                            "-o", exe, c], capture_output=True, text=True)
        if r.returncode:
            sys.exit("probe failed:\n" + r.stderr[-2000:])
        obj, monst = subprocess.run([exe], capture_output=True, text=True).stdout.split()
    return int(obj), int(monst)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--game", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--tree", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    named, strings = c64_objects(a.map)
    # the C64 far space: each kind in page-aligned regions of its own, objects packed
    by_kind = {}
    for name in sorted(named):
        by_kind.setdefault(kind_of(name), []).append(name)
    c64addr, nxt = {}, 0
    for k in range(1, 7):
        for name in by_kind.get(k, []):
            c64addr[name] = nxt
            nxt += named[name]
        nxt = (nxt + 255) & ~255
    str_base = nxt
    heap_base = (str_base + strings + 255) & ~255

    rows, moves = [], None
    nm = subprocess.run(["nm", "-S", "--defined-only", a.game], capture_output=True, text=True).stdout
    for line in nm.splitlines():
        f = line.split()
        if len(f) != 4 or f[2] not in "bBdDrRgGsSvV":
            continue
        addr, size, name = int(f[0], 16), int(f[1], 16), f[3]
        if name == "moves":
            moves = addr
        if size == 0:
            continue
        if name in named:
            rows.append((addr, size, c64addr[name], named[name], kind_of(name), name))
        else:
            rows.append((addr, size, 0, size, 0, name))
    if moves is None:
        sys.exit("no `moves` in %s" % a.game)
    ro = None
    for line in subprocess.run(["readelf", "-SW", a.game], capture_output=True, text=True).stdout.splitlines():
        m = re.search(r"\]\s+\.rodata\s+\S+\s+([0-9a-f]+)\s+[0-9a-f]+\s+([0-9a-f]+)", line)
        if m:
            ro = (int(m.group(1), 16), int(m.group(2), 16))
    if ro is None:
        sys.exit("no .rodata in %s" % a.game)
    obj, monst = host_sizes(a.tree)

    with open(a.out, "w") as o:
        o.write("moves %x\nrodata %x %x\nstrings %x %x\nheap %x\nobj %d\nmonst %d\n" % (
            moves, ro[0], ro[1], str_base, strings, heap_base, obj, monst))
        for r in rows:
            o.write("%x %d %x %d %d %s\n" % r)
    matched = [r for r in rows if r[4]]
    print("%d host globals, %d matched to the C64 map (%d B there of %d named); strings %d B; "
          "C64 far space to %#x, heap from %#x; host struct obj %d B, monst %d B" % (
              len(rows), len(matched), sum(r[3] for r in matched), sum(named.values()), strings,
              heap_base, heap_base, obj, monst))


if __name__ == "__main__":
    sys.exit(main())
