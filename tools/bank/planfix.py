#!/usr/bin/env python3
"""planfix.py - move functions out of the banks a whole-game build overflowed.

usage: tools/bank/planfix.py --plan P --map M --graph G [--profile PROF] --out P2
                             [--slack BYTES]

bankpart.py packs functions into banks by their sizes, but a function's size depends on
which functions share its bank (a call within a bank is direct, one to another bank goes
through a trampoline), so a plan built from one build's sizes can overflow a few banks in
the next.  Re-planning regroups everything and shifts the sizes again.  This keeps the plan
and, for each bank whose objects the build left unplaced (tools/bank/build_c64.py reports
them), moves the functions with the fewest calls inside their bank (from the host game's
profile, tools/profile_play.py) to the bank with the least room that takes each (best fit), until the bank has its
overflow plus --slack bytes to spare (less in a bank whose biggest function leaves less).  Sizes come from tools/measure/wholesizes.py
--with-literals on the same build.

--oversized handles a function too big for any bank (Oscar64 inlined the static helpers it
alone calls): the helpers its source calls but its intermediate code (--int) no longer does
are listed in the plan's "noinline" for bankgen.py and go to the bank with the most room,
with their size estimated as the function's growth over its per-file size (--per-file).

--add-banks B,B,... opens these empty banks for the moves, when the plan's own have no room
left (T2.12: the far build's code is bigger).  Banks past 103 are REU banks; a far space n's
data is bank 64+4n+2 and 64+4n+3 ($8000-$FFFF of REU 64 KB bank n, crt_split.py), so 104-105,
108-109, 112-113 and 116-117 are free.
"""
import argparse
import collections
import json
import re
import sys

BANK = 16384
# the HAL's files stay in their bank: their public functions switch the I/O in (src/hal/io128.h)
# and then call static helpers (vdc_rd, vdc_wr, ...) that expect it in, but a call to another
# bank goes through a stub that sets the MMU back to the I/O out (fc37: vdc_rd moved to REU
# bank 129 spun forever on $D600, RAM there)
PINNED_FILES = ("vdc80.c", "sys128.c")
LINE = re.compile(r"^(?:([0-9a-f]{2}):)?([0-9a-f]{4,5}) - ([0-9a-f]{4,5}) : ([^,]+), (\w+):nhbank_(\d+)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--graph", required=True)
    ap.add_argument("--profile", default="build/profile-arcs.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--slack", type=int, default=256)
    ap.add_argument("--oversized", action="store_true")
    ap.add_argument("--add-banks", default="", help="comma-separated bank numbers")
    ap.add_argument("--int", help="the build's intermediate code, for --oversized and --glue")
    ap.add_argument("--glue", action="store_true",
                    help="count what a move brings into its new bank besides the function: a bank "
                         "call stub for each callee in another bank, a string wrapper for each "
                         "string function it calls there (fork commit 6, bankgen.py --linker-stubs); "
                         "needs --int")
    ap.add_argument("--src", default="port/src", help="NetHack's sources, for --oversized")
    ap.add_argument("--per-file", default="build/callgraph-c64.json",
                    help="per-file sizes (tools/measure/callgraph.py), for --oversized")
    a = ap.parse_args()

    plan = json.load(open(a.plan))
    size = {k: v["size"] for k, v in json.load(open(a.graph))["functions"].items()}
    placed, left = collections.Counter(), collections.Counter()
    for line in open(a.map, errors="replace"):
        m = LINE.match(line)
        if m:
            n = int(m.group(3), 16) - int(m.group(2), 16)
            if n > 0:
                (left if m.group(1) is None else placed)[int(m.group(6))] += n

    arcs = collections.Counter()
    try:
        for u, cs in json.load(open(a.profile))["arcs"].items():
            for v, n in cs.items():
                arcs[(u, v)] += n
    except OSError:
        pass
    bank_of = {k.split(":", 1)[1]: b for k, b in plan["banks"].items()}
    inside = collections.Counter()
    for (u, v), n in arcs.items():
        if u in bank_of and bank_of.get(v) == bank_of[u]:
            inside[u] += n
            inside[v] += n

    banks = sorted(set(plan["banks"].values()))
    banks += [int(x) for x in a.add_banks.split(",") if x]
    # a bank whose biggest function leaves less than --slack keeps only what that leaves
    # (T2.12: seffects is 16,374 B, so 256 bytes of slack for every bank would rule it out)
    biggest = collections.Counter()
    for k, b in plan["banks"].items():
        biggest[b] = max(biggest[b], size.get(k.split(":", 1)[1], 0))
    slack = {b: max(0, min(a.slack, BANK - biggest[b])) for b in banks}
    free = {b: BANK - placed[b] - left[b] - slack[b] for b in banks}
    moves, fixed = [], set()
    if a.oversized:
        graph = json.load(open(a.graph))["functions"]
        calls, cur, header = collections.defaultdict(set), None, True
        for line in open(a.int, errors="replace"):
            if line.startswith("----"):
                header = True
                continue
            if header:
                m = re.match(r"^([A-Za-z_]\w*): \S", line)
                cur, header = (re.sub(r"__b\d+$", "", m.group(1)) if m else None), False
                continue
            m = cur and re.search(r"\tCALL\w*\t[^\t]*\t<-\tV\(-?\d+ '([^']*)'\)", line)
            if m:
                calls[cur].add(re.sub(r"__b\d+$", "", m.group(1)))
        per_file = {k.split(":")[-1]: v["size"] for k, v in json.load(open(a.per_file))["functions"].items()}
        for name, v in graph.items():
            if v["size"] <= BANK:
                continue
            text = open("%s/%s" % (a.src, v["file"]), encoding="latin-1").read()
            m = re.search(r"\n%s\s*\([^;{]*\)\s*\n\{" % re.escape(name), text)
            if not m:
                sys.exit("%s: cannot find the body of %s" % (v["file"], name))
            body = text[m.end():text.index("\n}\n", m.end())]
            statics = set(re.findall(r"^STATIC_(?:DCL|OVL|PTR)\s[^;(]*?\b(\w+)\s*(?:\(|FDECL|NDECL)", text, re.M))
            statics |= set(re.findall(r"^STATIC_DCL\s+\w+\s*\**\s*[FN]DECL\((\w+)", text, re.M))
            helpers = sorted(c for c in set(re.findall(r"\b([A-Za-z_]\w*)\s*\(", body))
                             if c in statics and c != name and c not in calls[name])
            if not helpers:
                sys.exit("%s (%d B) is bigger than a bank and inlines no static helper" % (name, v["size"]))
            estimate = max(0, v["size"] - per_file.get(name, v["size"]))
            to = max((t for t in banks if t not in left), key=lambda t: free[t])
            for h in helpers:
                plan["banks"]["%s:%s" % (v["file"], h)] = to
                plan.setdefault("noinline", []).append("%s:%s" % (v["file"], h))
            free[to] -= estimate
            fixed.add(plan["banks"]["%s:%s" % (v["file"], name)])
            print("  %s (%d B) keeps %d helpers out of line, to bank %d (about %d B): %s" % (
                name, v["size"], len(helpers), to, estimate, ", ".join(helpers)))
    # T2.12: with the bank call glue in the banks, a function moved to bank t brings a 6-byte
    # stub for each callee outside t (resident ones are called directly) and a caller wrapper
    # (f__tA) for each string function it calls outside t that has none there yet: far16's
    # moves, sized without these, overflowed every new bank by 4-5 KB
    STUB, WRAP = 6, 40
    glue_calls, has_wrap, wrapped = collections.defaultdict(set), set(), set()
    if a.glue:
        if not a.int:
            sys.exit("--glue needs --int")
        base = lambda n: re.sub(r"(?:__[btx]\d+|@\w+)+$", "", n)
        cur, header = None, True
        for line in open(a.int, errors="replace"):
            if line.startswith("----"):
                header = True
                continue
            if header:
                m = re.match(r"^([A-Za-z_]\w*): \S", line)
                cur, header = (base(m.group(1)) if m else None), False
                continue
            m = cur and re.search(r"\tCALL\w*\t[^\t]*\t<-\tV\(-?\d+ '([^']*)'\)", line)
            if m and base(m.group(1)) != cur:
                glue_calls[cur].add(base(m.group(1)))
        for line in open(a.map, errors="replace"):
            m = re.match(r"^(?:[0-9a-f]{2}:)?[0-9a-f]{4,5} - [0-9a-f]{4,5} : (\w+)__t(\d+), ", line)
            if m:
                has_wrap.add(m.group(1))
                wrapped.add((m.group(1), int(m.group(2))))

    def cost(name, t):
        if not a.glue or t in plan.get("resident_glue", ()):
            return size[name], ()
        extra, new = 0, []
        for c in glue_calls.get(name, ()):
            cb = bank_of.get(c)
            if cb is None or cb == t:
                continue
            extra += STUB
            if c in has_wrap and (c, t) not in wrapped:
                extra += WRAP
                new.append((c, t))
        return size[name] + extra, new

    def smallest(b):
        return min([size[k.split(":", 1)[1]] for k, bk in plan["banks"].items()
                    if bk == b and size.get(k.split(":", 1)[1])] or [0])
    # the banks of big functions first, while the new banks still have big holes
    for b in sorted(left, key=lambda b: (-smallest(b), b)):
        if b in fixed:
            continue
        need = left[b] + slack[b]
        members = [k for k, bk in plan["banks"].items() if bk == b and size.get(k.split(":", 1)[1])
                   and k.split(":", 1)[0] not in PINNED_FILES]
        members.sort(key=lambda k: (inside[k.split(":", 1)[1]], size[k.split(":", 1)[1]]))
        for k in members:
            if need <= 0:
                break
            name = k.split(":", 1)[1]
            n = size[name]
            # best fit: the bank with the least room that takes it, so the big holes stay for
            # the big functions (the most room first spread 33 overflows over every new bank)
            fits = [t for t in banks if t != b and t not in left and t not in fixed and free[t] >= cost(name, t)[0]]
            if not fits:
                continue
            to = min(fits, key=lambda t: free[t] - cost(name, t)[0])
            c, new = cost(name, to)
            plan["banks"][k] = to
            bank_of[name] = to
            wrapped.update(new)
            free[to] -= c
            need -= n
            moves.append((k, b, to, c))
        if need > 0:
            sys.exit("bank %d: no room elsewhere for %d more bytes" % (b, need))
    json.dump(plan, open(a.out, "w"), indent=0, sort_keys=True)
    for k, b, to, n in moves:
        print("  %-36s bank %3d -> %3d  (%d B)" % (k, b, to, n))
    print("%d functions moved out of %d overflowing banks" % (len(moves), len(left)))


if __name__ == "__main__":
    sys.exit(main())
