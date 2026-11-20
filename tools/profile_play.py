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

usage: tools/profile_play.py [--keys N] [--seed S] [-o OUT.json] [--install DIR]
needs: tools/host-build.sh --profile, python3 -m pip install pexpect, gprof

--install plays another install of the host game the same way, without gprof: the bank
spike's rewritten build (tools/host-build.sh --banked), whose functions check the
selected bank on entry, so a long game exercises far more of them than the smoke test.

--wide (ADR-0008, 2026-11-16) also uses the inventory: picks up, quaffs, reads, zaps, eats,
applies, wears, wields, throws, casts, kicks, engraves, opens doors and prays, with random
letters, so that cold code (items, spells, shops) is called too; --role picks the role, whose
starting kit decides much of that.  --merge adds this game's counts to an existing JSON.
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


# An object prompt ("What do you want to drink? [fg or ?*] ": a letter it offers is chosen),
# a direction prompt, and the other prompts of --wide's commands (ESC)
GETOBJ = r"\[([a-zA-Z$ -]*) or \?\*\] "
GETDIR = r"In what direction\? "
WISHES = ["blessed +2 silver dragon scale mail", "wand of digging", "magic marker", "bag of holding",
          "7 cursed potions of gain level", "blessed scroll of genocide", "ring of levitation",
          "blessed figurine of an Archon", "horn of plenty", "magic lamp"]
OTHER = r"Are you sure you want to pray\? \[yn\] \(n\) |\[\*\] "
TEXT = r"What do you want to (?:write|engrave|burn|melt|scribble|add)[^\r\n]*\? |For what do you wish\? "
PICK = r"\[([a-zA-Z]+)\] (?!\()"    # a choice with no default ("Which ring-finger, Right or Left? [rl] ")


class Discover(hs.Session):
    """host_smoke's session, on the profiling build, in discover mode."""
    role = "Valkyrie"

    def wide_command(self, keys, step, rnd):
        """Type keys and answer what they ask (a letter the prompt offers, a direction, y to
        pray); the sync key only once the game waits for a command again."""
        import pexpect
        self.child.send(keys)
        synced = False
        recover = 0
        for _ in range(200):
            try:
                i = self.child.expect([hs.SYNCED, hs.MORE, hs.MENU_END, GETOBJ, GETDIR, OTHER, hs.YN,
                                       hs.NAMING, PICK, TEXT, r"Die\? \[yn\] \(n\) "], timeout=0.3 if not synced else 10)
            except pexpect.TIMEOUT:
                if synced:
                    # a prompt none of the patterns knows took the sync key: ESC cancels it
                    recover += 1
                    if recover > 3:
                        raise hs.Stop("no answer during " + step)
                    self.child.send("\x1b\x1b" + hs.SYNC)
                    continue
                self.child.send(hs.SYNC)
                synced = True
                continue
            except pexpect.EOF:
                self.eof = True
                raise hs.Stop("the game ended during " + step)
            if i == 0:
                return
            synced = False          # a prompt came instead: it took the sync key, if one was sent
            if i == 1:
                self.child.send(" ")
            elif i == 3:
                offered = self.child.match.group(1)
                choice = "".join(chr(c) for a, b in re.findall(r"(\w)-(\w)", offered)
                                 for c in range(ord(a), ord(b) + 1)) + re.sub(r"\w-\w", "", offered)
                choice = choice.replace("$", "").replace("-", "").replace(" ", "")
                self.child.send(rnd.choice(choice) if choice else "\x1b")
            elif i == 4:
                self.child.send(rnd.choice("hjklyubn<>."))
            elif i == 5 and "pray" in self.child.after:
                self.child.send("y")
            elif i == 8:
                self.child.send(rnd.choice(self.child.match.group(1)))
            elif i == 10:
                self.child.send("n")
            elif i == 9:
                self.child.send(rnd.choice(WISHES) + "\r" if "wish" in self.child.after else "Elbereth\r")
            else:
                self.child.send("\x1b")
        raise hs.Stop("still answering prompts after 200 tries during " + step)

    def __init__(self, name):
        import io
        import pexpect
        self.log = io.StringIO()
        env = dict(hs.ENV, HOME=INST, USER=name,
                   NETHACKOPTIONS=hs.ENV["NETHACKOPTIONS"].replace("name:smoke", "name:" + name)
                   .replace("role:Valkyrie,race:human,gender:female,align:neutral",
                            "role:%s,race:human,gender:random,align:random" % self.role))
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
    ap.add_argument("--install", help="play this install instead, with no call counts")
    ap.add_argument("--wide", action="store_true", help="use the inventory too (ADR-0008)")
    ap.add_argument("--role", default="Valkyrie")
    ap.add_argument("--merge", action="store_true", help="add to the counts already in --out")
    ap.add_argument("--transcript", help="write the game's output, as text, to this file: two "
                                         "builds that behave the same, given the same clock "
                                         "(an LD_PRELOAD time()), write the same transcript")
    a = ap.parse_args()
    global INST, GAMEDIR, EXE
    if a.install:
        INST = os.path.abspath(a.install)
        GAMEDIR = os.path.join(INST, "nethackdir")
        EXE = os.path.join(GAMEDIR, "nethack")
    if not os.path.exists(EXE):
        sys.exit("no build at %s; run tools/host-build.sh --profile" % EXE)
    gmon = os.path.join(GAMEDIR, "gmon.out")
    if os.path.exists(gmon):
        os.remove(gmon)
    for f in os.listdir(os.path.join(GAMEDIR, "save")):
        os.remove(os.path.join(GAMEDIR, "save", f))
    rnd = random.Random(a.seed)
    stats = {"run": 0, "walk": 0, "travel": 0, "down": 0, "search": 0, "rest": 0}

    Discover.role = a.role
    letters = "abcdefghijklmnopqrstuvwxyz"
    dirs = "hjklyubn<>."
    # (share, keys made from a random letter and direction) for --wide
    WIDE = [(0.04, lambda: ","), (0.03, lambda: "q"),
            (0.03, lambda: "r"), (0.03, lambda: "z"),
            (0.02, lambda: "e"), (0.03, lambda: "a"),
            (0.02, lambda: "W"), (0.02, lambda: "w"),
            (0.02, lambda: "t"), (0.02, lambda: "P"),
            (0.02, lambda: "Z"), (0.02, lambda: "\x04"),
            (0.01, lambda: "E"), (0.02, lambda: "o"),
            (0.01, lambda: "T"), (0.01, lambda: "#pray\r"), (0.01, lambda: "i"),
            (0.01, lambda: "d"), (0.01, lambda: ":")]

    def play(s):
        s.command("", "the new game's start")
        for _ in range(a.keys):
            r = rnd.random()
            if a.wide:
                if r < 0.4:
                    r = r / 0.4 * 1.0      # the old mix, in 40% of the commands
                else:
                    x = rnd.random() * sum(w for w, _ in WIDE)
                    for w, k in WIDE:
                        x -= w
                        if x <= 0:
                            break
                    s.wide_command(k(), "an inventory command", rnd)
                    stats["items"] = stats.get("items", 0) + 1
                    continue
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
    if a.transcript:
        open(a.transcript, "w", encoding="latin-1").write(hs.strip_tty(transcript))
    if s.problem:
        open(a.out + ".tail.txt", "w").write(hs.strip_tty(transcript)[-3000:])
    levels = sorted(set(int(x) for x in re.findall(r"Dlvl:(\d+)", transcript)))
    print("session: %s%s; commands %s; dungeon levels seen %s" % (
        s.ended, "; " + s.problem if s.problem else "", stats, levels))
    if a.install:
        for line in sorted(set(re.findall(r"nhbank: [^\r\n]*", transcript))):
            print(line)                  # a bank check that stopped the game
        sys.exit(0 if s.ended == "exit status 0" and not s.problem else 1)
    if not os.path.exists(gmon):
        sys.exit("no gmon.out: the game did not exit normally")
    g = subprocess.run(["gprof", "-b", "-q", EXE, gmon], capture_output=True, text=True)
    out, totals = arcs(g.stdout)
    games = [{"keys": a.keys, "seed": a.seed, "role": a.role, "wide": a.wide, "commands": stats,
              "levels": levels}]
    if a.merge and os.path.exists(a.out):
        old = json.load(open(a.out))
        games = old.get("games", [{k: old.get(k) for k in ("keys", "seed", "commands", "levels")}]) + games
        for f, n in old["calls"].items():
            totals[f] = totals.get(f, 0) + n
        for f, d in old["arcs"].items():
            for g2, n in d.items():
                out.setdefault(f, {})[g2] = out.get(f, {}).get(g2, 0) + n
        levels = sorted(set(levels) | set(old.get("levels", [])))
    json.dump({"keys": sum(x["keys"] for x in games), "seed": a.seed, "commands": stats, "levels": levels,
               "games": games, "calls": totals, "arcs": out}, open(a.out, "w"), indent=1, sort_keys=True)
    print("%d functions called, %d arcs, %d calls in all -> %s" % (
        len(totals), sum(len(v) for v in out.values()), sum(totals.values()), a.out))


if __name__ == "__main__":
    main()
