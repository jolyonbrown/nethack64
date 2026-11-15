#!/usr/bin/env python3
"""summary.py - what a traced host game (tools/measure/trace/nh_trace.c) says about far data
on the C64 (docs/RAM-PLAN.md): pages and accesses a turn, page faults for each simulated cache,
and the cost of both at the spike's measured prices; and which globals to keep near.

usage: tools/measure/trace/summary.py TURNS [--near-kb N] [--skip N]

TURNS is NH_TRACE_OUT; TURNS.objects is read too.  --skip leaves out the first N turns (the
first level's creation).  Prices (tests/spikes/fardata.c): a translation 21 cycles, a fault
600; every far access is counted as a translation, an upper bound (a compiler that reuses a
translation for the next fields of the same object makes fewer).  --near-kb ranks the
globals by accesses per C64 byte and reports what keeping the best N KB near would leave.
"""
import argparse
import os
import sys

XLAT, FAULT, MHZ = 21, 600, 0.985


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))] if v else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("turns")
    ap.add_argument("--skip", type=int, default=1)
    ap.add_argument("--near-kb", type=float, default=4.0)
    a = ap.parse_args()

    head, rows, seen = None, [], set()
    for line in open(a.turns):
        if line.startswith("#"):
            head = line[1:].split("|")
            continue
        parts = [p.split() for p in line.split("|")]
        # a forked child (the save's compression) can flush a copy of the buffered tail:
        # keep each turn once, and only whole lines
        if len(parts) != 4 or not parts[0] or parts[0][0] in seen:
            continue
        if len(parts[0]) != len(head[0].split()) - 1 or len(parts[3]) != len(head[3].split()) - 1:
            continue
        seen.add(parts[0][0])
        rows.append(parts)
    rows = rows[a.skip:]
    pkinds = head[0].split()[2:]                       # after "turn pages:"
    akinds = head[1].split()[1:]                       # after "accesses:"
    sims = head[3].split()[1:]                         # after "faults:"
    n = len(rows)
    print("%d turns (the first %d left out)" % (n, a.skip))

    print("\npages touched a turn (C64 256-byte pages):     median    p90    max")
    tot = [sum(int(x) for x in r[0][1:]) for r in rows]
    print("  %-40s %6d %6d %6d" % ("all far data", pct(tot, .5), pct(tot, .9), max(tot)))
    for i, k in enumerate(pkinds):
        v = [int(r[0][1 + i]) for r in rows]
        print("  %-40s %6d %6d %6d" % (k, pct(v, .5), pct(v, .9), max(v)))
    w = [int(r[2][0]) for r in rows]
    print("  %-40s %6d %6d %6d" % ("over the last 10 turns", pct(w, .5), pct(w, .9), max(w)))

    print("\naccesses a turn:                                median    p90    max")
    far = []
    for r in rows:
        acc = dict(zip(akinds, (int(x) for x in r[1])))
        far.append(sum(v for k, v in acc.items() if k not in ("other", "near")))
    for i, k in enumerate(akinds):
        v = [int(r[1][i]) for r in rows]
        print("  %-40s %6d %6d %6d" % (k, pct(v, .5), pct(v, .9), max(v)))
    print("  %-40s %6d %6d %6d" % ("far (all but other and near)", pct(far, .5), pct(far, .9), max(far)))

    print("\nfar-data cost a turn, translations (%d cycles each, upper bound) + faults (%d each):" % (XLAT, FAULT))
    print("  %-12s %8s %8s %8s   %10s %10s %10s" % ("cache", "faults50", "faults90", "max", "ms median", "ms p90",
                                                     "ms mean"))
    for j, s in enumerate(sims):
        f = [int(r[3][j]) for r in rows]
        cost = [far[i] * XLAT + f[i] * FAULT for i in range(n)]
        print("  %-12s %8d %8d %8d   %10.0f %10.0f %10.0f" % (s, pct(f, .5), pct(f, .9), max(f),
                                                             pct(cost, .5) / MHZ / 1000, pct(cost, .9) / MHZ / 1000,
                                                             sum(cost) / max(1, n) / MHZ / 1000))

    objs = a.turns + ".objects"
    if os.path.exists(objs):
        g = []
        for line in open(objs):
            if line.startswith("#"):
                continue
            f = line.split()
            if f[0] in ("globals", "near") and f[3] != "-" and int(f[3]) > 0:
                g.append((int(f[4]) / int(f[3]), f[1], int(f[3]), int(f[4]), int(f[5])))
        g.sort(reverse=True)
        total = sum(x[3] for x in g)
        print("\nglobals by accesses per C64 byte (%d accessed; %d accesses in all):" % (len(g), total))
        cum_b = cum_a = 0
        for i, (d, name, size, acc, tt) in enumerate(g):
            cum_b += size
            cum_a += acc
            if i < 25 or cum_b <= a.near_kb * 1024:
                print("  %-24s %6d B %10d accesses (%5.1f%% so far, %6d B so far) in %d turns" % (
                    name, size, acc, 100.0 * cum_a / max(1, total), cum_b, tt))
            if cum_b > a.near_kb * 1024 and i >= 25:
                break
        best, b = [], 0
        for d, name, size, acc, tt in g:
            if b + size > a.near_kb * 1024:
                continue
            best.append(name)
            b += size
        kept = sum(x[3] for x in g if x[1] in best)
        print("keeping %d globals near (%d B, within %.1f KB) takes %.1f%% of the globals' accesses off the far path"
              % (len(best), b, a.near_kb, 100.0 * kept / max(1, total)))
        open(a.turns + ".near", "w").write("\n".join(best) + "\n")
        print("(their names: %s.near, for NH_TRACE_NEAR)" % a.turns)
    return 0


if __name__ == "__main__":
    sys.exit(main())
