#!/usr/bin/env python3
"""Partition NetHack's functions into a resident core and banks, and count how often
play would cross between them (the banking spike, docs/BANKING-SPIKE.md).

usage: tools/measure/bankpart.py [--graph build/callgraph-c64.json]
                                 [--profile build/profile-arcs.json]
                                 [--resident BYTES ...] [--bank BYTES]

Sizes come from the Oscar64 harness (tools/measure/callgraph.py): what a function costs
on the C64.  Call counts come from the gprof build of the host game
(tools/profile_play.py): how often each caller calls each callee in play.  A host
function with no C64 code of its own (a static that Oscar64 inlined) is folded into the
caller that calls it most; functions outside NetHack's src/ (libc, the tty window port)
are taken as resident and free.

For each resident budget: choose the resident core greedily by calls absorbed per byte,
cluster the rest by heaviest call first into banks of --bank bytes, pack the clusters
first-fit, and count the calls that leave their bank (a call into a resident function
never does; a call from the resident core into a bank always does).  Counts are reported
per game turn, taking one call of movemon() as one turn.
"""
import argparse
import collections
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load(graph_p, prof_p):
    g = json.load(open(graph_p))["functions"]
    size, home = {}, {}
    for k, v in g.items():
        name = k.split(":")[-1]
        size[name] = size.get(name, 0) + v["size"]
        home[name] = v["file"]
    p = json.load(open(prof_p))
    arcs = collections.Counter()
    for u, cs in p["arcs"].items():
        for v, n in cs.items():
            if u != v:
                arcs[(u, v)] += n
    # fold host-only NetHack functions (statics Oscar64 inlined) into their main caller
    nh = set(size)
    callers = collections.defaultdict(collections.Counter)
    for (u, v), n in arcs.items():
        callers[v][u] += n
    def owner(f, depth=0):
        if f in nh or depth > 8:
            return f
        if not callers[f]:
            return f
        return owner(callers[f].most_common(1)[0][0], depth + 1)
    folded = collections.Counter()
    for (u, v), n in arcs.items():
        u2, v2 = owner(u), owner(v)
        if u2 != v2:
            folded[(u2, v2)] += n
    turns = sum(n for (u, v), n in arcs.items() if v == "movemon") or 1
    return size, home, folded, turns, p


def partition(size, arcs, resident_budget, bank):
    nh = set(size)
    inbound = collections.Counter()
    for (u, v), n in arcs.items():
        if v in nh:
            inbound[v] += n
    resident, used = set(), 0
    for f in sorted((f for f in inbound if size[f] > 0), key=lambda f: -inbound[f] / size[f]):
        if used + size[f] <= resident_budget:
            resident.add(f)
            used += size[f]
    banked = [f for f in nh if f not in resident]
    cl = {f: f for f in banked}
    members = {f: [f] for f in banked}
    csize = {f: size[f] for f in banked}
    def find(f):
        while cl[f] != f:
            cl[f] = cl[cl[f]]
            f = cl[f]
        return f
    for (u, v), n in sorted(arcs.items(), key=lambda x: -x[1]):
        if u in cl and v in cl:
            a, b = find(u), find(v)
            if a != b and csize[a] + csize[b] <= bank:
                if csize[a] < csize[b]:
                    a, b = b, a
                cl[b] = a
                members[a] += members.pop(b)
                csize[a] += csize.pop(b)
    bins = []
    for root in sorted(members, key=lambda r: -csize[r]):
        for b in bins:
            if b["size"] + csize[root] <= bank:
                b["size"] += csize[root]
                b["funcs"] += members[root]
                break
        else:
            bins.append({"size": csize[root], "funcs": list(members[root])})
    where = {}
    for i, b in enumerate(bins):
        for f in b["funcs"]:
            where[f] = i
    cross = 0
    for (u, v), n in arcs.items():
        if v not in nh or v in resident:
            continue
        if u in resident or u not in nh or where.get(u) != where.get(v):
            cross += n
    return resident, used, bins, cross


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", default=os.path.join(ROOT, "build", "callgraph-c64.json"))
    ap.add_argument("--profile", default=os.path.join(ROOT, "build", "profile-arcs.json"))
    ap.add_argument("--resident", type=int, nargs="*", default=[0, 4096, 8192, 12288, 16384, 24576])
    ap.add_argument("--bank", type=int, default=16384)
    ap.add_argument("--literals", default=None,
                    help="per-file string literal bytes (JSON {file: [count, bytes]}), spread over "
                         "each file's functions by code size, since literals travel with their code")
    ap.add_argument("--flash-banks", type=int, default=0,
                    help="hybrid: this many banks execute in place, the coldest rest are REU overlays")
    a = ap.parse_args()
    size, home, arcs, turns, p = load(a.graph, a.profile)
    if a.literals:
        lit = json.load(open(a.literals))
        per_file = collections.Counter()
        for f, s in size.items():
            per_file[home[f]] += s
        for f in size:
            fl = home[f]
            if fl in lit and per_file[fl]:
                size[f] += int(lit[fl][1] * size[f] / per_file[fl])
    total = sum(n for (u, v), n in arcs.items() if v in size)
    print("profile: %d commands, levels %s, %d calls to NetHack functions, %d turns (movemon)" % (
        sum(p["commands"].values()), p["levels"], total, turns))
    print("code: %d functions, %d B; bank size %d B" % (len(size), sum(size.values()), a.bank))
    print("%9s %8s %6s %14s %10s" % ("resident", "used", "banks", "calls leaving", "per turn"))
    for r in a.resident:
        resident, used, bins, cross = partition(size, arcs, r, a.bank)
        print("%9d %8d %6d %14d %10.1f" % (r, used, len(bins), cross, cross / turns))
        if a.flash_banks and len(bins) > a.flash_banks:
            where = {f: i for i, b in enumerate(bins) for f in b["funcs"]}
            into = collections.Counter()
            for (u, v), n in arcs.items():
                if v in where and v not in resident and (u in resident or where.get(u) != where[v]):
                    into[where[v]] += n
            order = sorted(range(len(bins)), key=lambda i: into[i])
            cold = order[:len(bins) - a.flash_banks]
            cold_calls = sum(into[i] for i in cold)
            print("          hybrid: %d banks in flash, %d coldest as REU overlays (%d B): "
                  "%d calls into them, %.2f per turn; the hottest of them %d calls" % (
                      a.flash_banks, len(cold), sum(bins[i]["size"] for i in cold), cold_calls,
                      cold_calls / turns, max(into[i] for i in cold)))


if __name__ == "__main__":
    sys.exit(main())
