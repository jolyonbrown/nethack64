#!/usr/bin/env python3
"""
memmap.py - one-screen memory budget from Oscar64 .map files.

For each map: the sections (code/data/bss/heap/stack ...) with their ranges
and sizes, then the 15 largest objects.  Use it after every build that adds
code: the resident region in an EasyFlash build ends at $8000, and every
byte there is shared by the whole game.

usage: tools/memmap.py build/nethack-ef.map [more.map ...]
"""
import re
import sys


def report(path):
    sections, objects = [], []
    mode = None
    for line in open(path):
        line = line.rstrip()
        if line in ("sections", "regions", "objects", "objects by size"):
            mode = line
            continue
        m = re.match(r"^(?:--:)?([0-9a-f]{4}) - ([0-9a-f]{4}) : (\w+), ([\w@]+)", line)
        if not m:
            continue
        a, b = int(m.group(1), 16), int(m.group(2), 16)
        if mode == "sections" and "@" not in m.group(4) and m.group(3) != "SSTACK":
            sections.append((m.group(4), a, b))
        elif mode == "objects":
            objects.append((m.group(3), m.group(4), a, b))
    print("== %s" % path)
    for name, a, b in sections:
        print("  %-10s $%04x-$%04x %6d bytes" % (name, a, b, b - a))
    big = sorted(objects, key=lambda o: o[3] - o[2], reverse=True)[:15]
    print("  largest objects:")
    for name, kind, a, b in big:
        print("    %-28s %-18s %6d" % (name, kind, b - a))


for p in sys.argv[1:]:
    report(p)
