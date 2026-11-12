#!/usr/bin/env python3
"""Compare two Oscar64 autotest logs: which test steps fail in each.

Make each log in an Oscar64 checkout with
    make -k -C make check > LOG 2>&1
(-k: keep going after a failing test, so one log lists every failure).
A failing step is make's "[makefile:LINE: TARGET] Error N" line; LINE is the
recipe line, i.e. which compiler configuration of TARGET failed.

usage: autotest_diff.py BASE.log NEW.log     exit 1 if NEW has a failure BASE lacks
       autotest_diff.py LOG                  list the failures in one log
"""
import re
import sys

STEP = re.compile(r"^make(?:\[\d+\])?: (?:\*\*\* )?\[([^\]:]*makefile):(\d+): ([^\]]+)\] Error (\d+)")


def failures(path):
    fails, emulations = set(), 0
    for line in open(path, errors="replace"):
        m = STEP.match(line)
        if m:
            fails.add((m.group(3), int(m.group(2)), int(m.group(4))))
        elif "Emulation result" in line:
            emulations += 1
    return fails, emulations


def show(label, items):
    print(f"{label}: {len(items)}")
    for t, ln, rc in sorted(items):
        print(f"   {t} (makefile:{ln}, exit {rc})")


def main(argv):
    if len(argv) == 2:
        f, e = failures(argv[1])
        print(f"emulations: {e}")
        show("failing steps", f)
        return 0
    if len(argv) != 3:
        print(__doc__)
        return 2
    (bf, be), (nf, ne) = failures(argv[1]), failures(argv[2])
    print(f"emulations: base {be}, new {ne}")
    show("new failures", nf - bf)
    show("fixed", bf - nf)
    show("failing in both", bf & nf)
    return 1 if nf - bf else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
