#!/usr/bin/env python3
"""warmplan.py - keep the host game's hot calls off the REU banks (ADR-0008).

usage: tools/bank/warmplan.py --plan P --map M --graph G [--profile PROF] --out P2
                              [--min-calls 60] [--slack 256] [--moves 400]

A bank of 64 and above lives in the REU: the bank call routine copies its 16 KB into the
window when a call enters it, and again when a call from it returns there, about 16 ms
each.  From the host game's profile (tools/profile_play.py: caller, callee, calls) this
counts the copies a plan costs, then moves functions one at a time: the one in an REU
bank that causes the most copies goes into the cartridge bank (1-63) it calls or is
called from most, and if that bank has no room, the coldest functions there (those whose
moving to the REU costs the fewest copies, and less than the move saves) go to the
function's old bank, or another REU bank with room (--add-banks opens empty ones).  It stops when no function causes --min-calls copies or more.  Sizes
come from wholesizes.py's graph (G), bank fill from the build's map (M); planfix.py repairs
what the next build overflows.
"""
import argparse
import collections
import json
import re

BANK = 16384
LINE = re.compile(r"^([0-9a-f]{2}):([0-9a-f]{4,5}) - ([0-9a-f]{4,5}) : ([^,]+), (\w+):nhbank_(\d+)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--graph", required=True)
    ap.add_argument("--profile", default="build/profile-arcs.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-calls", type=int, default=60)
    ap.add_argument("--slack", type=int, default=256)
    ap.add_argument("--moves", type=int, default=400)
    ap.add_argument("--add-banks", default="",
                    help="comma-separated empty REU banks the evicted functions may go to")
    a = ap.parse_args()

    plan = json.load(open(a.plan))
    funcs = json.load(open(a.graph))["functions"]
    size = {k: v["size"] for k, v in funcs.items()}
    key = {k.split(":")[1]: k for k in plan["banks"]}
    bank = {k.split(":")[1]: b for k, b in plan["banks"].items()}
    fixed = set(plan.get("resident_glue", []))
    used = collections.Counter()
    for line in open(a.map, errors="replace"):
        m = LINE.match(line)
        if m:
            used[int(m.group(6))] += int(m.group(3), 16) - int(m.group(2), 16)
    prof = json.load(open(a.profile))
    keys = prof.get("keys") or 1
    calls = collections.defaultdict(collections.Counter)   # f -> partner -> calls either way
    arcs = []
    for caller, d in prof["arcs"].items():
        for callee, n in d.items():
            if caller != callee:
                arcs.append((caller, callee, n))
                calls[caller][callee] += n
                calls[callee][caller] += n

    def copies(c, f, bc, bf):
        """REU copies of n calls from c (in bank bc) to f (in bf); None is resident."""
        if bc is None or bf is None or bc == bf:
            return (bf is not None and bf >= 64 and bc is None) * 0
        return (bf >= 64) + (bc >= 64)

    def total():
        return sum(n * copies(c, f, bank.get(c), bank.get(f)) for c, f, n in arcs
                   if bank.get(c) is not None or bank.get(f) is not None)

    def cost_of(g, b):
        """Copies g's calls cost with g in bank b."""
        return sum(n * copies(g, p, b, bank.get(p)) for p, n in calls[g].items())

    reu = sorted(set(b for b in bank.values() if b >= 64 and b not in fixed) |
                 set(int(x) for x in a.add_banks.split(",") if x))
    before = total()
    moved = []
    for _ in range(a.moves):
        # the function in an REU bank whose calls cost the most copies
        cand = [(cost_of(g, bank[g]), g) for g in calls if bank.get(g, 0) >= 64 and g in size
                and bank[g] not in fixed]
        if not cand:
            break
        cand.sort(reverse=True)
        done = False
        for w, f in cand[:20]:
            if w < a.min_calls:
                break
            old = bank[f]
            # the cartridge bank it calls or is called from most
            partner = collections.Counter()
            for p, n in calls[f].items():
                pb = bank.get(p)
                if pb is not None and pb < 64 and pb not in fixed:
                    partner[pb] += n
            for t, _ in partner.most_common(3):
                gain = w - cost_of(f, t)
                if gain <= 0:
                    continue
                need = used[t] + size[f] + a.slack - BANK
                evict, got = [], 0
                room = collections.Counter({b: BANK - a.slack - used[b] for b in reu})
                room[old] += size[f]
                if need > 0:
                    # the coldest functions of t, by what moving them to the REU costs, each
                    # to `old` if it has room, else to the REU bank with the most
                    others = sorted(((cost_of(g, old) - cost_of(g, t), g) for g, b in bank.items()
                                     if b == t and g in size and g != f and size[g] > 0), key=lambda x: x[0])
                    loss = 0
                    for dl, g in others:
                        if got >= need:
                            break
                        d = old if room[old] >= size[g] else max(reu, key=lambda b: room[b])
                        if room[d] < size[g]:
                            continue
                        room[d] -= size[g]
                        evict.append((g, d))
                        got += size[g]
                        loss += cost_of(g, d) - cost_of(g, t)
                    if got < need or loss >= gain:
                        continue
                for g, d in evict:
                    bank[g] = d
                    used[t] -= size[g]
                    used[d] += size[g]
                bank[f] = t
                used[old] -= size[f]
                used[t] += size[f]
                moved.append((f, old, t, w, gain, evict))
                done = True
                break
            if done:
                break
        if not done:
            break
    for name, b in bank.items():
        plan["banks"][key[name]] = b
    json.dump(plan, open(a.out, "w"), indent=1, sort_keys=True)
    after = total()
    for f, old, t, w, gain, ev in moved[:40]:
        print("  %-24s %3d -> %2d  saves %7d copies%s" % (f, old, t, gain,
              ("; out: " + ", ".join(g for g, _ in ev[:4]) + (" ..." if len(ev) > 4 else "")) if ev else ""))
    print("warmplan: %d moves; REU copies in the profile %d -> %d (%.0f -> %.0f a key, "
          "about %.2f -> %.2f s a key at 16 ms)" % (len(moved), before, after, before / keys,
                                                     after / keys, before / keys * 0.0164,
                                                     after / keys * 0.0164))


if __name__ == "__main__":
    main()
