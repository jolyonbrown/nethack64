#!/usr/bin/env python3
"""cgsummary.py - what a callgrind run of the host game says about NetHack's speed on the C64
(docs/RAM-PLAN.md, the speed baseline): x86 instructions a turn, split by where they are spent.

usage: tools/measure/speed/cgsummary.py CALLGRIND.OUT [--top N]

Turns are counted from the calls of functions moveloop() makes once a turn (nh_timeout,
settrack, mcalcdistress).  Self cost is split by object and source file: NetHack's game code
(port/src), the tty window port (win/tty), and libraries (libc, ncurses).  On the C64 the game
code is the same C; the window port and the libraries are not (our own 80-column screen,
Oscar64's library), so they are reported apart.  Inclusive costs follow callgrind's per-call
records (a recursive function's inclusive cost counts its recursion more than once).
"""
import argparse
import collections
import re
import sys

ONCE_A_TURN = ("nh_timeout", "settrack", "mcalcdistress")


def load(path):
    """(total Ir, self Ir, calls, inclusive Ir, file, object) of each function in a callgrind
    output file; the last five are dicts keyed by function name."""
    names = {"fl": {}, "fn": {}, "ob": {}}
    self_ir = collections.Counter()
    call_ir = collections.Counter()
    calls = collections.Counter()
    fn_file, fn_obj = {}, {}
    cur_fn = cur_fl = cur_ob = None
    pending, after_calls = None, False
    total = None
    for line in open(path, errors="replace"):
        line = line.rstrip("\n")
        if not line or line[0] == "#":
            continue
        if line.startswith("summary:") or line.startswith("totals:"):
            total = int(line.split()[1])
            continue
        m = re.match(r"^(c?)(fl|fi|fe|fn|ob)=\((\d+)\)(?: (.*))?$", line)
        if m:
            callee, kind, idx, name = m.groups()
            table = names["fl" if kind in ("fl", "fi", "fe") else kind]
            if name is not None:
                table[idx] = name
            name = table.get(idx, "?")
            if callee:
                if kind == "fn":
                    pending = name
            elif kind == "fn":
                cur_fn = name
                fn_file.setdefault(name, cur_fl)
                fn_obj.setdefault(name, cur_ob)
            elif kind == "fl":
                cur_fl = name
            elif kind == "ob":
                cur_ob = name
            continue
        m = re.match(r"^calls=(\d+)", line)
        if m:
            calls[pending] += int(m.group(1))
            after_calls = True
            continue
        if line[0] in "0123456789+-*":
            parts = line.split()
            ir = int(parts[1]) if len(parts) > 1 else 0
            if after_calls:
                call_ir[(cur_fn, pending)] += ir
                after_calls = False
            else:
                self_ir[cur_fn] += ir
    incl = collections.Counter(self_ir)
    for (caller, callee), ir in call_ir.items():
        if caller != callee:
            incl[caller] += ir
    return total if total is not None else sum(self_ir.values()), self_ir, calls, incl, fn_file, fn_obj


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("callgrind_out")
    ap.add_argument("--top", type=int, default=30)
    a = ap.parse_args()
    total, self_ir, calls, incl, fn_file, fn_obj = load(a.callgrind_out)

    turns = {f: calls[f] for f in ONCE_A_TURN}
    nturns = max(turns.values())
    sum_self = sum(self_ir.values())
    print("total Ir %d (self costs sum to %d)" % (total, sum_self))
    print("turns: %s" % ", ".join("%s %d" % kv for kv in turns.items()))

    def where(fn):
        fl, ob = fn_file.get(fn) or "", fn_obj.get(fn) or ""
        if "/win/" in fl:
            return "window port (win/tty)"
        if "/sys/" in fl:
            return "system (sys/unix, sys/share)"
        if "nethack" in ob.rsplit("/", 1)[-1]:
            return "game code (src)" if "/src/" in fl else "game binary, no file"
        return "library " + re.sub(r"\.so.*", "", ob.rsplit("/", 1)[-1])

    by = collections.Counter()
    for fn, ir in self_ir.items():
        by[where(fn)] += ir
    print("\nself Ir by place:                         total      a turn    share")
    for k, v in by.most_common():
        print("  %-38s %12d %10.0f %7.1f%%" % (k, v, v / nturns, 100.0 * v / sum_self))

    print("\ninclusive Ir of the main phases:          total      calls    a call")
    for fn in ("newgame", "moveloop", "mklev", "makelevel", "goto_level", "movemon", "rhack", "dosave0",
               "vision_recalc", "flush_screen", "bot", "dochug", "m_move", "mfndpos", "newsym"):
        if incl.get(fn):
            print("  %-38s %12d %8d %10.0f" % (fn, incl[fn], calls[fn], incl[fn] / max(1, calls[fn])))

    game = [(ir, fn) for fn, ir in self_ir.items() if where(fn) == "game code (src)"]
    game.sort(reverse=True)
    gsum = sum(ir for ir, _ in game)
    print("\ngame code by self Ir (%d functions; %.0f a turn in all):" % (len(game), gsum / nturns))
    print("  %-26s %12s %7s %10s %9s %10s" % ("function", "self Ir", "share", "calls", "Ir/call", "a turn"))
    for ir, fn in game[:a.top]:
        print("  %-26s %12d %6.1f%% %10d %9.1f %10.0f" % (fn, ir, 100.0 * ir / gsum, calls[fn],
                                                         ir / max(1, calls[fn]), ir / nturns))
    return 0


if __name__ == "__main__":
    sys.exit(main())
