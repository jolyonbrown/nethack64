#!/usr/bin/env python3
"""calls_game.py - play a game on the host's --calls build and keep its calls, for window.py.

usage: tools/measure/trace/calls_game.py OUT.bin [--commands 300] [--seed 7] [--clock N]

A new game as the C128 replays start one (the name from -u, as Unix NetHack takes it),
"Shall I pick ...?" answered n,
then Valkyrie, human, neutral from the menus. Then a seeded walk with some inventory, look
and search commands (as tests/host_video_compare.py's), with the clock pinned (LD_PRELOAD)
so a run repeats, and #quit at the end so that the calls reach OUT.bin (the hooks write it
at exit). Needs tools/host-build.sh --calls and pexpect.
"""
import argparse
import os
import random
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import host_smoke as hs  # noqa: E402

import pexpect  # noqa: E402

INST = os.path.join(ROOT, "build", "host-calls-install")
FIXTIME = "#include <time.h>\ntime_t time(time_t *t) { if (t) *t = %d; return %d; }\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("out")
    ap.add_argument("--commands", type=int, default=300)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--clock", type=int, default=1700000000)
    a = ap.parse_args()
    gamedir = os.path.join(INST, "nethackdir")
    for f in os.listdir(os.path.join(gamedir, "save")):
        os.remove(os.path.join(gamedir, "save", f))
    rnd = random.Random(a.seed)
    keys = [rnd.choice("hjklyubn") if rnd.random() < 0.9 else rnd.choice(["i", ":", "s", "5s"])
            for _ in range(a.commands)]
    with tempfile.TemporaryDirectory() as tmp:
        c, so = os.path.join(tmp, "fixtime.c"), os.path.join(tmp, "fixtime.so")
        open(c, "w").write(FIXTIME % (a.clock, a.clock))
        subprocess.run(["gcc", "-shared", "-fPIC", "-o", so, c], check=True)
        env = dict(os.environ, TERM="vt100", HOME=INST, LD_PRELOAD=so,
                   NH_CALLS_OUT=os.path.abspath(a.out), NETHACKOPTIONS="!autopickup")
        g = hs.Session.__new__(hs.Session)
        g.log = None
        g.eof = False
        g.child = pexpect.spawn(os.path.join(gamedir, "nethack"), ["-d", gamedir, "-u", "Agent"], env=env,
                                encoding="latin-1", dimensions=(25, 80), timeout=hs.ANSWER_WAIT)
        g.child.delaybeforesend = None
        g.expect([r"Shall I pick"], "pick")
        g.child.send("n")
        for step, key in (("role", "v"), ("race", "h"), ("alignment", "n")):
            i = g.expect([hs.MENU_END, r"Is this ok\?"], step)
            if i == 1:
                break
            g.child.send(key)
        i = g.expect([r"Is this ok\?", hs.MORE], "confirm")
        if i == 0:
            g.child.send("y")
            g.expect([hs.MORE], "welcome")
        g.command(" ", "the first turn")
        for k in keys:
            g.command(k, "command %r" % k)
        g.child.send("#quit\r")
        g.expect([hs.YN], "quit")
        g.child.send("y")
        g.finish("the end")
    print("%s: %d bytes" % (a.out, os.path.getsize(a.out)))


if __name__ == "__main__":
    sys.exit(main())
