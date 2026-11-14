#!/usr/bin/env python3
"""
profile_play.py - play the gprof build of the host game for a while, then write
gprof's call graph as JSON arcs (caller, callee, calls) for the banking spike
(docs/BANKING-SPIKE.md: which calls are hot, not just which exist).

The game runs in discover mode (-X), so a death asks "Die?" and its default (n)
lets play go on.  The bot runs and walks at random, now and then travels to a
down staircase it has seen ('_', '>', '.') and goes down, searches and rests.  It is a
proxy for real play: exploration, monsters' turns, fighting, vision and level
creation, much less of inventory, shops and spells.

usage: tools/profile_play.py [--keys N] [--seed S] [-o OUT.json]
needs: tools/host-build.sh --profile, python3 -m pip install pexpect, gprof
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tests"))
import host_smoke as hs  # noqa: E402  (its Session and prompt handling)

INST = os.path.join(ROOT, "build", "host-prof-install")
GAMEDIR = os.path.join(INST, "nethackdir")
EXE = os.path.join(GAMEDIR, "nethack")

PRIMARY = re.compile(r"^\[(\d+)\]\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+(\d+)(?:\+\d+)?\s+(\S+) \[\d+\]")
CHILD = re.compile(r"^\s+[\d.]+\s+[\d.]+\s+(\d+)(?:/\d+)?\s+(\S+) \[\d+\]")


class Discover(hs.Session):
    """host_smoke's session, on the profiling build, in discover mode."""
    def __init__(self, name):
        import io
        import pexpect
        self.log = io.StringIO()
        env = dict(hs.ENV, HOME=INST, USER=name,
                   NETHACKOPTIONS=hs.ENV["NETHACKOPTIONS"].replace("name:smoke", "name:" + name))
        self.child = pexpect.spawn(EXE, ["-d", GAMEDIR, "-u", name, "-X"], env=env,
                                   encoding="latin-1", dimensions=(24, 80),
                                   timeout=hs.ANSWER_WAIT)
        self.child.logfile_read = self.log
        self.child.delaybeforesend = None
        self.eof = False
        self.problem = None
        self.ended = None


def arcs(gprof_text):
    """{caller: {callee: calls}} and {function: calls} from `gprof -b -q`."""
    out, totals, cur = {}, {}, None
    for line in gprof_text.split("\n"):
        if line.startswith("-----"):
            cur = None
            continue
        m = PRIMARY.match(line)
        if m:
            cur = m.group(3)
            totals[cur] = int(m.group(2))
            continue
        m = CHILD.match(line)
        if m and cur:
            out.setdefault(cur, {})[m.group(2)] = out.get(cur, {}).get(m.group(2), 0) + int(m.group(1))
    return out, totals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", type=int, default=6000, help="commands to type")
    ap.add_argument("--seed", type=int, default=64)
    ap.add_argument("-o", "--out", default=os.path.join(ROOT, "build", "profile-arcs.json"))
    a = ap.parse_args()
    if not os.path.exists(EXE):
        sys.exit("no profiling build at %s; run tools/host-build.sh --profile" % EXE)
    gmon = os.path.join(GAMEDIR, "gmon.out")
    if os.path.exists(gmon):
        os.remove(gmon)
    for f in os.listdir(os.path.join(GAMEDIR, "save")):
        os.remove(os.path.join(GAMEDIR, "save", f))
    rnd = random.Random(a.seed)
    stats = {"run": 0, "walk": 0, "travel": 0, "down": 0, "search": 0, "rest": 0}

    def play(s):
        s.command("", "the new game's start")
        for _ in range(a.keys):
            r = rnd.random()
            if r < 0.45:
                # a run (shift + direction) stops at anything interesting: it explores
                s.command(rnd.choice("HJKLYUBN"), "a run"); stats["run"] += 1
            elif r < 0.80:
                s.command(rnd.choice("hjklyubn"), "a step"); stats["walk"] += 1
            elif r < 0.88:
                s.command("_>.", "travel to a down staircase"); stats["travel"] += 1
                s.command(">", "going down"); stats["down"] += 1
            elif r < 0.95:
                s.command("s", "a search"); stats["search"] += 1
            else:
                s.command("20s", "a rest"); stats["rest"] += 1
        s.child.send("S")
        s.expect([r"Really save\? \[yn\] \(n\) "], "the save")
        s.child.send("y")
        s.finish("the save")

    s = Discover("prof")
    transcript = s.run(play)
    levels = sorted(set(int(x) for x in re.findall(r"Dlvl:(\d+)", transcript)))
    print("session: %s%s; commands %s; dungeon levels seen %s" % (
        s.ended, "; " + s.problem if s.problem else "", stats, levels))
    if not os.path.exists(gmon):
        sys.exit("no gmon.out: the game did not exit normally")
    g = subprocess.run(["gprof", "-b", "-q", EXE, gmon], capture_output=True, text=True)
    out, totals = arcs(g.stdout)
    json.dump({"keys": a.keys, "seed": a.seed, "commands": stats, "levels": levels,
               "calls": totals, "arcs": out}, open(a.out, "w"), indent=1, sort_keys=True)
    print("%d functions called, %d arcs, %d calls in all -> %s" % (
        len(totals), sum(len(v) for v in out.values()), sum(totals.values()), a.out))


if __name__ == "__main__":
    main()
