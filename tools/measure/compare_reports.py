#!/usr/bin/env python3
"""
compare_reports.py - compare two measure_oscar64.py report.json files.

    tools/measure/compare_reports.py OLD.json NEW.json

Prints the status totals of both, every file whose record changed (status,
code size, functions, first error) and whether the Oscar64 struct sizes match.
Keys starting with '_' other than _struct_sizes (e.g. _meta) are ignored.
Exit code 0 when the two reports are identical record for record, 1 otherwise;
use it to check that a run reproduces a recorded baseline.
"""
import collections
import json
import sys


def load(path):
    with open(path) as f:
        return json.load(f)


def totals(rep):
    files = {k: v for k, v in rep.items() if not k.startswith("_")}
    st = collections.Counter(v["status"] for v in files.values())
    code = sum(v.get("code") or 0 for v in files.values())
    return ", ".join("%d %s" % (n, s) for s, n in sorted(st.items())) + "; %d bytes of native code" % code


def fmt(r):
    if r is None:
        return "-"
    return "%s %s %s %s" % (r.get("status"), r.get("code", ""), r.get("funcs", ""), r.get("error", ""))


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: compare_reports.py OLD.json NEW.json")
    old, new = load(sys.argv[1]), load(sys.argv[2])
    print("old:", totals(old))
    print("new:", totals(new))
    names = sorted(k for k in set(old) | set(new) if not k.startswith("_"))
    changed = 0
    for k in names:
        a, b = old.get(k), new.get(k)
        if a == b:
            continue
        changed += 1
        print("%-12s %s\n%12s -> %s" % (k, fmt(a), "", fmt(b)))
    same_sizes = old.get("_struct_sizes") == new.get("_struct_sizes")
    print("struct sizes:", "identical" if same_sizes else "DIFFER")
    print("%d of %d records differ" % (changed, len(names)))
    sys.exit(0 if changed == 0 and same_sizes else 1)


if __name__ == "__main__":
    main()
