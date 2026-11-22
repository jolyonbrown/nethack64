#!/usr/bin/env python3
"""
host_video_compare.py - does the C64's tty screen layer draw what termcap draws?

Plays the same game on the host build (tools/host-build.sh: the tty port over termcap)
and the video build (tools/host-build.sh --video: the same tty port over
port/sys/c64/video.c and tools/host-s80.c), with the clock pinned by an LD_PRELOAD
time() so both games are the same, and the same keys: a seeded walk with some
inventory, look and search commands. After each command, once the game waits for the
next, both screens are read through one small VT100 emulator (both builds write to a
terminal) and must match character for character, but for the build date the
version line shows. Both terminals are 80x25, the C64's
screen. A control game with another clock must differ, so that a pass shows the
comparison can fail.

usage: tests/host_video_compare.py [--commands 300] [--seed 7]
Needs: both host builds; python3 -m pip install pexpect. Exit status 0 when all match.
"""
import argparse
import os
import random
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import host_smoke as hs  # noqa: E402  (the session driver and its prompts)

import pexpect  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDS = {"termcap": os.path.join(ROOT, "build", "host-install"),
          "video": os.path.join(ROOT, "build", "host-video-install")}
FIXTIME = "#include <time.h>\ntime_t time(time_t *t) { if (t) *t = %d; return %d; }\n"
CLOCK, CONTROL = 1700000000, 1700000777
ROWS, COLS = 25, 80


class VT100:
    """Just enough of a VT100 for NetHack's tty output: text, cursor motion, erasing."""

    def __init__(self):
        self.grid = [[" "] * COLS for _ in range(ROWS)]
        self.x = self.y = 0
        self.wrap = False
        self.saved = (0, 0)
        self.pending = ""

    def scroll(self):
        self.grid.pop(0)
        self.grid.append([" "] * COLS)

    def newline(self):
        if self.y == ROWS - 1:
            self.scroll()
        else:
            self.y += 1

    def put(self, c):
        if self.wrap:
            self.x = 0
            self.newline()
            self.wrap = False
        self.grid[self.y][self.x] = c
        if self.x == COLS - 1:
            self.wrap = True
        else:
            self.x += 1

    def erase(self, y, x0, x1):
        for x in range(x0, x1):
            self.grid[y][x] = " "

    def csi(self, params, final):
        p = [int(v) if v else 0 for v in params.lstrip("?").split(";")] if params else []
        n = (p[0] if p else 0) or 1
        if final in "Hf":
            self.y = min(max((p[0] if p else 1) or 1, 1), ROWS) - 1
            self.x = min(max((p[1] if len(p) > 1 else 1) or 1, 1), COLS) - 1
        elif final == "A":
            self.y = max(self.y - n, 0)
        elif final == "B":
            self.y = min(self.y + n, ROWS - 1)
        elif final == "C":
            self.x = min(self.x + n, COLS - 1)
        elif final == "D":
            self.x = max(self.x - n, 0)
        elif final == "K":
            mode = p[0] if p else 0
            self.erase(self.y, *{0: (self.x, COLS), 1: (0, self.x + 1), 2: (0, COLS)}[mode])
        elif final == "J":
            mode = p[0] if p else 0
            if mode == 0:
                self.erase(self.y, self.x, COLS)
                for y in range(self.y + 1, ROWS):
                    self.erase(y, 0, COLS)
            elif mode == 1:
                for y in range(self.y):
                    self.erase(y, 0, COLS)
                self.erase(self.y, 0, self.x + 1)
            else:
                for y in range(ROWS):
                    self.erase(y, 0, COLS)
        self.wrap = False if final in "HfABCDJ" else self.wrap
        # m (attributes), h/l (modes), r (scroll region) and the rest change no text

    def feed(self, data):
        s = self.pending + data
        self.pending = ""
        i = 0
        while i < len(s):
            c = s[i]
            if c == "\x1b":
                m = re.compile(r"\x1b(\[([0-9;?]*)([@-~])|[()][0-9A-Za-z]|[78=>]|.)").match(s, i)
                if not m or (m.group(0) == "\x1b[" + (m.group(2) or "") and not m.group(3)):
                    self.pending = s[i:]
                    return
                if m.group(3):
                    self.csi(m.group(2), m.group(3))
                elif m.group(0) == "\x1b7":
                    self.saved = (self.x, self.y)
                elif m.group(0) == "\x1b8":
                    self.x, self.y = self.saved
                i = m.end()
                continue
            if c == "\r":
                self.x, self.wrap = 0, False
            elif c == "\n":
                self.newline()
            elif c == "\b":
                self.x, self.wrap = max(self.x - 1, 0), False
            elif c == "\t":
                self.x = min((self.x // 8 + 1) * 8, COLS - 1)
            elif c >= " " and c != "\x7f":
                self.put(c)
            i += 1

    def text(self):
        # the version line ('v', typed to know the game waits) names each build's build time
        return re.sub(r"last build .*? \d{4}\.", "last build (date).",
                      "\n".join("".join(r) for r in self.grid))


def fixtime_lib(tmp, t):
    c = os.path.join(tmp, "fixtime%d.c" % t)
    so = os.path.join(tmp, "fixtime%d.so" % t)
    open(c, "w").write(FIXTIME % (t, t))
    subprocess.run(["gcc", "-shared", "-fPIC", "-o", so, c], check=True)
    return so


class Game(hs.Session):
    def __init__(self, inst, lib):
        gamedir = os.path.join(inst, "nethackdir")
        for f in os.listdir(os.path.join(gamedir, "save")):
            os.remove(os.path.join(gamedir, "save", f))
        env = dict(hs.ENV, HOME=inst, LD_PRELOAD=lib)
        self.log = None
        self.vt = VT100()
        self.child = pexpect.spawn(os.path.join(gamedir, "nethack"), ["-d", gamedir, "-u", "smoke"],
                                   env=env, encoding="latin-1", dimensions=(ROWS, COLS),
                                   timeout=hs.ANSWER_WAIT)
        self.child.logfile_read = self
        self.child.delaybeforesend = None
        self.eof = False

    # pexpect's log file: everything the game writes goes through the emulator
    def write(self, data):
        self.vt.feed(data)

    def flush(self):
        pass

    def settle(self):
        """Read what the game writes after the line we waited for, until it is quiet."""
        try:
            while True:
                self.child.read_nonblocking(65536, timeout=0.15)
        except (pexpect.TIMEOUT, pexpect.EOF):
            pass
        return self.vt.text()


def play(inst, lib, keys):
    g = Game(inst, lib)
    screens = []
    try:
        g.expect([r"NetHack, Copyright"], "start-up")
        g.command("", "the first turn")
        screens.append(g.settle())
        for k in keys:
            g.command(k, "command %r" % k)
            screens.append(g.settle())
    except hs.Stop as e:
        screens.append("STOPPED: %s" % e)
    g.child.terminate(force=True)
    return screens


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--commands", type=int, default=300)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    keys = [rnd.choice("hjklyubnhjklyubnhjklyubn") if rnd.random() < 0.9 else rnd.choice(["i", ":", "s", "5s"])
            for _ in range(a.commands)]
    with tempfile.TemporaryDirectory() as tmp:
        lib, ctl = fixtime_lib(tmp, CLOCK), fixtime_lib(tmp, CONTROL)
        termcap = play(BUILDS["termcap"], lib, keys)
        video = play(BUILDS["video"], lib, keys)
        control = play(BUILDS["video"], ctl, keys)
    bad = 0
    for i, (t, v) in enumerate(zip(termcap, video)):
        if t != v:
            bad += 1
            if bad <= 2:
                print("screen %d differs:" % i)
                for row, (rt, rv) in enumerate(zip(t.split("\n"), v.split("\n"))):
                    if rt != rv:
                        print("  %2d termcap |%s|\n  %2d video   |%s|" % (row, rt, row, rv))
    n = min(len(termcap), len(video))
    print("%d screens compared (%d and %d), %d differ" % (n, len(termcap), len(video), bad))
    same_control = sum(1 for t, c in zip(termcap, control) if t == c)
    print("control game (another clock): %d of %d screens the same" % (same_control, min(len(termcap), len(control))))
    ok = bad == 0 and len(termcap) == len(video) and same_control < min(len(termcap), len(control))
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
