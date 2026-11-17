#!/usr/bin/env python3
"""bankplace.py - which banks a bank plan's code could leave off the EasyFlash (ADR-0008).

usage: tools/measure/bankplace.py [--plan docs/data/bankplan-2026-11-15-stubs.json]
                                  [--profile build/profile-arcs.json] [--keep N ...]
                                  [--write PLAN_OUT]

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
    ap.add_argument("--keep", type=int, nargs="*", default=[63, 56, 48, 40, 32, 24, 16])
    ap.add_argument("--write", metavar="PLAN_OUT",
                    help="write the plan renumbered for ADR-0008: the banks entered most get 1-63 "
                         "(the EasyFlash), the others 64 up (the REU), in that order")
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
    used = sorted(set(bank.values()))        # the plan's banks, 1 up (bank 0 boots the cartridge)
    nb = len(used)
    order = sorted(used, key=lambda b: (-into[b], b))
    games = prof.get("games", [{}])
    print("plan %s: %d banks; profile %s: %d game(s), %d turns, levels %s" % (
        os.path.basename(a.plan), nb, os.path.basename(a.profile), len(games), turns, prof.get("levels")))
    print("banks never entered: %d" % sum(1 for b in used if into[b] == 0))
    for keep in a.keep:
        off = order[keep:]
        n = sum(into[b] for b in off)
        print("  %3d banks on the cartridge, %3d off it: %8.3f entries a turn into those (%d banks entered at all)"
              % (keep, len(off), n / turns, sum(1 for b in off if into[b])))
    print("entries a turn, banks entered most:", ", ".join("%d: %.1f" % (b, into[b] / turns) for b in order[:12]))
    if a.write:
        ef = order[:63]
        new = {b: i + 1 for i, b in enumerate(ef)}
        new.update({b: 64 + i for i, b in enumerate(order[63:])})
        out = dict(plan)
        out["banks"] = {k: new[b] for k, b in plan["banks"].items()}
        out["renumbered"] = {"from": os.path.basename(a.plan), "profile": os.path.basename(a.profile),
                             "old_to_new": {str(b): new[b] for b in used}}
        json.dump(out, open(a.write, "w"), indent=1, sort_keys=True)
        print("wrote %s: banks 1-%d on the EasyFlash, %d-%d in the REU" % (
            a.write, len(ef), 64, 63 + max(0, nb - 63)))


if __name__ == "__main__":
    main()
