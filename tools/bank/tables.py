#!/usr/bin/env python3
"""tables.py - the read-only tables of a whole-game build, for a plan's "bank_data".

usage: tools/bank/tables.py --int BUILD/nethack.int --map BUILD/nethack.map
                            [--src port/src] [--plan P --out P2] [--review]

A file-scope table that no code writes can live in the bank of the code that reads it,
together with the string literals it points to, if that code is all in one bank
(bankgen.py checks this against the plan and leaves the others resident).  From the
build's intermediate code (Oscar64 -rmp, nethack.int) this lists the resident objects of
the data section that no instruction stores to (a STORE*, STRCPY, COPY, FILL or MOVE whose target is
the object), and finds each one's definition in the sources.

What the intermediate code cannot show is a pointer into the table that leaves its bank
in a way the bank's own literals cannot: as a pointer to a struct or to a pointer, or
stored where code of another bank reads it.  --review prints, for each table, the uses in
its file that are not plain reads of an element (`t[i]`, `t[i].f`, `SIZE(t)`): an address
taken, the bare name passed on.  Those need reading by hand; a table that fails the
reading goes in the plan's "bank_data_skip".

--plan/--out writes P with "bank_data" set to the list (less "bank_data_skip") as P2.
"""
import argparse
import collections
import glob
import json
import os
import re

V = re.compile(r"V\((-?\d+) '([^']+)'[ A-Z]*\)")
MAPLINE = re.compile(r"^(?:(--|[0-9a-f]{2}):)?([0-9a-f]{4,5}) - ([0-9a-f]{4,5}) : ([^,]+), (\w+):(\S+)")
COMMENT_OR_STRING = re.compile(r'/\*.*?\*/|"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'', re.S)


def read_only(intf, mapf):
    """{name: size} of the resident data-section objects nothing stores to."""
    data = {}
    for line in open(mapf, errors="replace"):
        m = MAPLINE.match(line)
        if m and m.group(6) == "data" and m.group(5) == "DATA" and m.group(4) != "*":
            a, b = int(m.group(2), 16), int(m.group(3), 16)
            data[m.group(4)] = b if line.startswith("0000 - ") else b - a
    written, seen = collections.Counter(), set()
    for line in open(intf, errors="replace"):
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        op = parts[2].strip()
        for _, v in V.findall(line):
            seen.add(v)
        lhs, _, rhs = line.partition("<-")
        if op.startswith(("STORE", "STRCPY", "COPY", "FILL")):
            targets = V.findall(rhs.split(",")[0])
        elif op == "MOVE":
            targets = V.findall(lhs)
        else:
            continue
        for _, v in targets:
            written[v] += 1
    return {n: z for n, z in data.items() if n in seen and not written[n]}


def definition_files(names, src):
    """{name: [files]} of the file-scope definitions (with an initialiser) of the names."""
    out = collections.defaultdict(list)
    for path in sorted(glob.glob(os.path.join(src, "*.c"))):
        text = COMMENT_OR_STRING.sub(lambda m: " " * len(m.group(0)) if m.group(0)[0] == "/" else '""',
                                     open(path, encoding="latin-1").read())
        for m in re.finditer(r"(?m)^(?:[A-Za-z_][^;(){}=]*?[\s*])?([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)*=", text):
            if m.group(1) in names:
                out[m.group(1)].append(os.path.basename(path))
    return out


def review(name, path):
    """Uses of `name` in its file other than reading an element or taking its size."""
    text = COMMENT_OR_STRING.sub(lambda m: " " * len(m.group(0)) if m.group(0)[0] == "/" else '""',
                                 open(path, encoding="latin-1").read())
    odd = []
    for m in re.finditer(r"\b%s\b" % re.escape(name), text):
        before, after = text[:m.start()].rstrip(), text[m.end():].lstrip()
        line = text.count("\n", 0, m.start()) + 1
        if after.startswith("=") and not after.startswith("=="):
            continue                                       # the definition
        if re.search(r"(?:SIZE|sizeof)\s*\(?\s*$", before):
            continue
        if after.startswith("[") and not before.endswith("&"):
            continue
        odd.append("%d: %s" % (line, text[m.start() - 30:m.end() + 30].replace("\n", " ").strip()))
    return odd


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--int", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--src", default="port/src")
    ap.add_argument("--plan")
    ap.add_argument("--out")
    ap.add_argument("--review", action="store_true")
    a = ap.parse_args()
    ro = read_only(a.int, a.map)
    where = definition_files(set(ro), a.src)
    keys = []
    for n in sorted(ro):
        fs = where.get(n, [])
        if len(fs) == 1:
            keys.append("%s:%s" % (fs[0], n))
    print("tables.py: %d read-only data objects (%d B), %d with one definition in %s" % (
        len(ro), sum(ro.values()), len(keys), a.src))
    if a.review:
        for k in keys:
            f, n = k.split(":")
            for u in review(n, os.path.join(a.src, f)):
                print("  %s %s" % (k, u))
    if a.plan and a.out:
        plan = json.load(open(a.plan))
        skip = set(plan.get("bank_data_skip", []))
        plan["bank_data"] = [k for k in keys if k not in skip]
        json.dump(plan, open(a.out, "w"), indent=1, sort_keys=True)
        print("tables.py: %d tables in %s" % (len(plan["bank_data"]), a.out))


if __name__ == "__main__":
    main()
