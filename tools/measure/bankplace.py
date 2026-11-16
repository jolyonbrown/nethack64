#!/usr/bin/env python3
"""bankplace.py - which banks a bank plan's code could leave off the EasyFlash (ADR-0008).

usage: tools/measure/bankplace.py [--plan docs/data/bankplan-2026-11-15-stubs.json]
                                  [--profile build/profile-arcs.json] [--keep N ...]

For each bank of the plan, the calls a turn that enter it from outside (from another bank
or the resident core; gprof's arcs, tools/profile_play.py), a turn being a call of
mcalcdistress(). The banks entered most stay on the cartridge (--keep of them, executed in
place); the others would be copied into a RAM window when called (from the REU, or
unpacked). The entries a turn into those are an upper bound on such loads: the counts do
not say in which order the calls come, and a load is only needed when the window holds
another bank.
"""
import argparse
import collections
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=os.path.join(ROOT, "docs", "data", "bankplan-2026-11-15-stubs.json"))
    ap.add_argument("--profile", default=os.path.join(ROOT, "build", "profile-arcs.json"))
    ap.add_argument("--keep", type=int, nargs="*", default=[62, 56, 48, 40, 32, 24, 16])
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    prof = json.load(open(a.profile))
    turns = prof["calls"].get("mcalcdistress", 1)
    bank = {k.split(":", 1)[1]: b for k, b in plan["banks"].items()}
    into = collections.Counter()
    for caller, d in prof["arcs"].items():
        for callee, n in d.items():
            b = bank.get(callee)
            if b is not None and bank.get(caller) != b:
                into[b] += n
    nb = max(bank.values()) + 1
    order = sorted(range(nb), key=lambda b: -into[b])
    games = prof.get("games", [{}])
    print("plan %s: %d banks; profile %s: %d game(s), %d turns, levels %s" % (
        os.path.basename(a.plan), nb, os.path.basename(a.profile), len(games), turns, prof.get("levels")))
    print("banks never entered: %d" % sum(1 for b in range(nb) if into[b] == 0))
    for keep in a.keep:
        off = order[keep:]
        n = sum(into[b] for b in off)
        print("  %3d banks on the cartridge, %3d off it: %8.3f entries a turn into those (%d banks entered at all)"
              % (keep, len(off), n / turns, sum(1 for b in off if into[b])))
    print("entries a turn, banks entered most:", ", ".join("%d: %.1f" % (b, into[b] / turns) for b in order[:12]))


if __name__ == "__main__":
    main()
