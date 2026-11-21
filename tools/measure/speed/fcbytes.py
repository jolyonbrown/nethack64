#!/usr/bin/env python3
"""fcbytes.py - the byte accesses the host game makes inside one function's calls, classified
from the disassembly, as an upper bound on what far characters' test would cost there
(ADR-0010, "Step 2's checks").

usage: tools/measure/speed/fcbytes.py CALLGRIND.OUT BINARY FUNCTION [--by-function N]

CALLGRIND.OUT is from `valgrind --tool=callgrind --dump-instr=yes --toggle-collect=FUNCTION`
over a host game (tools/profile_play.py --install DIR, with DIR/nethackdir/nethack a script
that runs the real binary that way; the binary must not be setuid for valgrind).  Each byte
load or store executed in the game's own code (not libc) is put in one class by its memory
operand: through a pointer (any base register but %rsp and %rip) with no displacement or with
an index register, the shape of `*p` and `p[i]`; through a pointer with a constant
displacement, the shape of a struct field and `p[k]`; or on the stack or a global.  On the
6502 the test is paid only on `char` accesses through a pointer whose target the compiler
does not know, so the first class is too wide (an indexed global array is counted there,
gcc having put its address in a register) and the second mostly struct fields (which take
the typed spaces' path or none); the first two together bound it.  libc's work (strncmp,
sprintf: C on Oscar64, so tested per byte) is not counted here; the calls of it are listed.
"""
import argparse
import bisect
import collections
import re
import subprocess

BYTE_OPS = ("movzbl", "movzbw", "movsbl", "movsbw", "movzbq", "movsbq")
BYTE_REG = re.compile(r"%(al|bl|cl|dl|sil|dil|bpl|spl|ah|bh|ch|dh|r\d+b)\b")
MEM = re.compile(r"(-?0x[0-9a-f]+)?\((%r\w+)?(?:,(%r\w+),\d)?\)")
WALK, DISP, STATIC = "through a pointer: no displacement, or an index", \
    "through a pointer: a constant displacement", "on the stack or a global"


def load(path):
    """{(object, address): executions} of the instructions collected"""
    names, counts = {}, collections.Counter()
    ob = cfn = None
    last, skip = 0, False

    def name(kind, s):
        m = re.match(r"\((\d+)\)(?: (.*))?$", s.strip())
        if not m:
            return s.strip()
        if m.group(2):
            names[(kind, m.group(1))] = m.group(2)
        return names.get((kind, m.group(1)), m.group(1))

    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("ob="):
            ob = name("ob", line[3:])
        elif line.startswith("cob="):
            name("ob", line[4:])
        elif line.startswith(("fn=", "cfn=")):
            cfn = name("fn", line.split("=", 1)[1])
        elif line.startswith("calls="):
            skip = True          # the next cost line is the call's inclusive cost
        else:
            m = re.match(r"^(0x[0-9a-f]+|[+-]\d+|\*)\s+(\S+)\s+(\d+)$", line)
            if not m:
                continue
            p = m.group(1)
            last = int(p, 16) if p.startswith("0x") else last if p == "*" else last + int(p)
            if skip:
                skip = False
            else:
                counts[(ob, last)] += int(m.group(3))
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("callgrind")
    ap.add_argument("binary")
    ap.add_argument("function")
    ap.add_argument("--by-function", type=int, default=0, metavar="N")
    a = ap.parse_args()
    counts = load(a.callgrind)
    dis = {}
    for line in subprocess.run(["objdump", "-d", "--no-show-raw-insn", a.binary], capture_output=True,
                               text=True).stdout.splitlines():
        m = re.match(r"^\s+([0-9a-f]+):\s+(.*)$", line)
        if m:
            dis[int(m.group(1), 16)] = m.group(2).strip()
    syms = []
    for line in subprocess.run(["nm", "-n", a.binary], capture_output=True, text=True).stdout.splitlines():
        p = line.split()
        if len(p) == 3 and p[1] in "tTwW":
            syms.append((int(p[0], 16), p[2]))
    starts = [s[0] for s in syms]
    entry = next((s[0] for s in syms if s[1] == a.function), None)
    cls, own, other, calls = collections.Counter(), 0, 0, 0
    per = collections.defaultdict(collections.Counter)
    libc = collections.Counter()
    for (o, addr), n in counts.items():
        if not o.endswith(a.binary.rsplit("/", 1)[-1]):
            other += n
            continue
        own += n
        calls += n if addr == entry else 0
        f = syms[bisect.bisect_right(starts, addr) - 1][1]
        per[f]["instructions"] += n
        ins = dis.get(addr, "")
        op = ins.split()[0] if ins else ""
        args = ins[len(op):]
        if op == "call" and "@plt" in args:
            libc[args.split("<")[-1].split("@")[0]] += n
        if not op or op.startswith(("lea", "nop", "call", "j")) or "(" not in args:
            continue
        if not (op in BYTE_OPS or (op.endswith("b") and op not in ("sub", "sbb")) or BYTE_REG.search(args)):
            continue
        m = MEM.search(args)
        k = STATIC if m.group(2) in (None, "%rsp", "%rip") else WALK if (m.group(3) or not m.group(1)) else DISP
        cls[k] += n
        per[f][k] += n
    c = max(calls, 1)
    print("%s: %d calls; %.0f instructions a call in the game's own code, %.0f in libc" % (
        a.function, calls, own / c, other / c))
    for k in (WALK, DISP, STATIC):
        print("  byte accesses %-50s %6.1f a call" % (k, cls[k] / c))
    print("  libc calls a call: " + ", ".join("%s %.1f" % (k, v / c) for k, v in libc.most_common(10)))
    if a.by_function:
        print("  %-22s %12s %8s %8s   (a call of %s)" % ("function", "instructions", "walking", "fields", a.function))
        for f, d in sorted(per.items(), key=lambda kv: -kv[1]["instructions"])[:a.by_function]:
            print("  %-22s %12.1f %8.1f %8.1f" % (f, d["instructions"] / c, d[WALK] / c, d[DISP] / c))


if __name__ == "__main__":
    main()
