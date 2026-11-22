#!/usr/bin/env python3
"""far_warnings.py - a whole-game link's warnings 2026 against the ones already reviewed.

usage: tools/bank/far_warnings.py LOG TREE [--accepted docs/data/farwarn-accepted.txt]
                                  [--write-accepted FILE]

Warning 2026 ("Pointer into a far space converted to a pointer outside it", the far-spaces
fork) marks a far address that goes on as a near pointer: harmless where it is only kept,
compared or cast back (a genericptr_t round trip), wrong where it is dereferenced as near
memory (fc20: the RAM disk's open-file table, far by the far default, reached through a
struct pointer, so every file's position came from the cartridge window). A link's 2026s
are only seen in the whole game, where every file is compiled together; this reads them from
the compile's log (LOG, the memlog), takes each one's source line from the build's tree
(TREE/src, TREE/inc), and keys it by file and the line's text, since bankgen.py's insertions
move the line numbers. With --accepted, each one not in that list is printed as NEW and the
exit status is 1: look at each before booting the build. The list's lines are
"file<TAB>source line<TAB>why it is harmless".
"""
import argparse
import collections
import os
import re
import sys

WARN = re.compile(r"/(src|inc)/([\w.]+)\((\d+), \d+\) : warning 2026")


def norm(s):
    return " ".join(s.split())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("log")
    ap.add_argument("tree")
    ap.add_argument("--accepted")
    ap.add_argument("--write-accepted", help="write every warning's key to FILE, to review")
    a = ap.parse_args()
    found = collections.Counter()
    lines = {}
    for line in open(a.log, errors="replace"):
        m = WARN.search(line)
        if not m:
            continue
        path = os.path.join(a.tree, m.group(1), m.group(2))
        if path not in lines:
            lines[path] = open(path, encoding="latin-1").read().split("\n")
        n = int(m.group(3))
        src = norm(lines[path][n - 1]) if n <= len(lines[path]) else "?"
        found[(m.group(2), src)] += 1
    accepted = {}
    if a.accepted and os.path.exists(a.accepted):
        for line in open(a.accepted, encoding="latin-1"):
            if line.strip() and not line.startswith("#"):
                f, src, why = (line.rstrip("\n").split("\t") + ["", ""])[:3]
                accepted[(f, norm(src))] = why
    new = [k for k in found if k not in accepted]
    for (f, src), n in sorted(found.items()):
        tag = "NEW " if (f, src) in new else "    "
        print("%s%-12s %2d  %s" % (tag, f, n, src[:100]))
    gone = [k for k in accepted if k not in found]
    print("%d warnings 2026 at %d places; %d new, %d accepted, %d accepted not seen" % (
        sum(found.values()), len(found), len(new), len(found) - len(new), len(gone)))
    if a.write_accepted:
        with open(a.write_accepted, "w", encoding="latin-1") as fh:
            fh.write("# far_warnings.py's accepted warnings 2026: file<TAB>source line<TAB>why\n")
            for (f, src) in sorted(found):
                fh.write("%s\t%s\t%s\n" % (f, src, accepted.get((f, src), "TODO")))
    return 1 if (a.accepted and new) else 0


if __name__ == "__main__":
    sys.exit(main())
