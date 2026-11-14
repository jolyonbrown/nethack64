#!/usr/bin/env python3
"""
host_smoke.py - play, save and restore the host build of port/.

A cheap behavioural regression test for changes to the shared game source:
if the converted/trimmed NetHack still starts, accepts commands, writes a
save file and restores it, the change probably did not break the engine.

The driver waits for the game instead of typing on a clock.  After each
command it types 'v' (version: takes no game time and prints one fixed
line) and reads until that line appears, answering any --More--, menu or
y/n prompt on the way.  A key that lands in one of those only beeps, so 'v'
is typed again after each answer.  Both sessions must then end by themselves
with exit status 0, so a crash shows up as the signal that killed the game.

Why (2026-11-14, T1.28): the fixed clock used before let --More-- prompts
swallow keys.  The scripted save and quit often never ran, the game was
killed at a timeout, and a CI run whose restore session died part-way
through dorecover() (run 43536929831) looked like a slow runner.

Needs: tools/host-build.sh to have run; python3 -m pip install pexpect
usage: tests/host_smoke.py [install_dir]   (default build/host-install)
"""
import io
import os
import random
import re
import signal
import sys
import time

try:
    import pexpect
except ImportError:
    sys.exit("pip install pexpect  (needed to drive the tty game)")

INST = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "build/host-install")
GAMEDIR = os.path.join(INST, "nethackdir")
EXE = os.path.join(GAMEDIR, "nethack")

ENV = dict(os.environ, TERM="vt100", USER="smoke", HOME=INST,
           NETHACKOPTIONS="name:smoke,role:Valkyrie,race:human,gender:female,"
                          "align:neutral,!autopickup,time,showexp")

# How long the game may take to answer one key.  A wait ends as soon as the
# answer arrives, so this only bounds a game that has hung.
ANSWER_WAIT = 60

SYNC = "v"                                   # the version command...
SYNCED = r"NetHack Version \d"               # ...and the line it prints
MORE = r"--More--"
MENU_END = r"\((end|\d+ of \d+)\) "
YN = r"\[[a-zA-Z$#*-]+\] \([a-zA-Z$#*-]\) "  # yn_function(): "[ynq] (n) "
# Text prompts a walk can raise: naming an object type seen in use (a
# monster's potion breaks nearby) and a vault guard.  ESC cancels the line,
# and with it the 'v' already typed into it.
NAMING = r"Call [^\r\n]*?: |who are you\?\" - "


class Stop(Exception):
    """The session cannot go on: the game ended, or stopped answering."""


class Session:
    def __init__(self):
        self.log = io.StringIO()
        self.child = pexpect.spawn(EXE, ["-d", GAMEDIR, "-u", "smoke"], env=ENV,
                                   encoding="latin-1", dimensions=(24, 80),
                                   timeout=ANSWER_WAIT)
        self.child.logfile_read = self.log
        self.child.delaybeforesend = None   # every key waits for an answer instead
        self.eof = False
        self.problem = None
        self.ended = None

    def expect(self, patterns, step):
        try:
            return self.child.expect(patterns)
        except pexpect.EOF:
            self.eof = True
            raise Stop("the game ended during " + step)
        except pexpect.TIMEOUT:
            raise Stop("no answer within %d s during %s" % (ANSWER_WAIT, step))

    def command(self, keys, step):
        """Type keys, then wait until the game asks for its next command."""
        self.child.send(keys + SYNC)
        for _ in range(200):
            i = self.expect([SYNCED, MORE, MENU_END, YN, NAMING], step)
            if i == 0:
                return
            # Space for --More--: ESC there would also hide the rest of the
            # turn's messages.  ESC closes a menu, takes a y/n prompt's
            # default and cancels a text prompt.
            self.child.send((" " if i == 1 else "\x1b") + SYNC)
        raise Stop("still answering prompts after 200 tries during " + step)

    def finish(self, step):
        """Answer the closing prompts until the game exits by itself."""
        for _ in range(200):
            i = self.expect([MORE, MENU_END, YN, NAMING, pexpect.EOF], step)
            if i == 4:
                self.eof = True
                return
            self.child.send({0: " ", 1: "\x1b", 2: "q", 3: "\x1b"}[i])
        raise Stop("still answering prompts after 200 tries during " + step)

    def run(self, script):
        try:
            self.expect([r"NetHack, Copyright"], "start-up")
            script(self)
        except Stop as e:
            self.problem = str(e)
        if self.eof:
            self.child.wait()   # the pty has closed, so the game is exiting
        else:
            self.child.terminate(force=True)
            self.ended = "killed by the test"
        if self.ended is None:
            sig = self.child.signalstatus
            self.ended = ("killed by signal %d (%s)" % (sig, signal.Signals(sig).name)
                          if sig is not None else "exit status %d" % self.child.exitstatus)
        return self.log.getvalue()


def hero_died(s, transcript):
    """The game ended by itself at the end-of-game questions."""
    return (s.eof and s.ended == "exit status 0"
            and "possessions identified" in transcript)


def strip_tty(s):
    """Drop terminal control sequences so a transcript reads as text."""
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[()][0-9A-Za-z]|\x1b[=>78DEM]"
                  r"|[\x00-\x08\x0e-\x1f]", "", s)


def main():
    if not os.path.exists(EXE):
        sys.exit("no host build at %s; run tools/host-build.sh" % EXE)
    savedir = os.path.join(GAMEDIR, "save")
    for f in os.listdir(savedir):
        os.remove(os.path.join(savedir, f))
    random.seed(343)
    walk = "".join(random.choice("hjklyubn") for _ in range(150))

    def play_and_save(s):
        s.command("", "the new game's start")
        for k in walk:
            s.command(k, "the walk")
        s.command("i", "the inventory")
        s.command("s", "a search")
        s.command("s", "a search")
        s.child.send("S")
        s.expect([r"Really save\? \[yn\] \(n\) "], "the save")
        s.child.send("y")
        s.finish("the save")

    def restore_and_quit(s):
        s.expect([r"Restoring save file"], "the restore")
        s.command("", "the restore")
        for k in walk[:40]:
            s.command(k, "the walk after restoring")
        s.child.send("#quit\r")
        s.expect([r"Really quit\? \[yn\] \(n\) "], "the quit")
        s.child.send("y")
        s.finish("the quit")

    # The dungeon comes from the clock, and now and then the walk gets the
    # hero killed (20 of 600 local runs on 2026-11-14: 11 by a falling-rock
    # trap stepped on again and again, the rest by an arrow trap or small
    # monsters).  A death before the save says nothing about the engine, so
    # play a new game, in a new clock second.
    for game in range(1, 4):
        s1 = Session()
        t1 = s1.run(play_and_save)
        saved = os.listdir(savedir)
        if saved or not hero_died(s1, t1):
            break
        print("the hero died before the save (game %d); playing a new game" % game)
        second = int(time.time())
        while int(time.time()) == second:
            time.sleep(0.05)
    s2 = Session() if saved else None
    t2 = s2.run(restore_and_quit) if s2 else ""
    if s2 and hero_died(s2, t2) and "Really quit" not in t2:
        print("the hero died after the restore, so the quit was not reached")

    both = (t1 + t2).lower()
    checks = {
        "game started (status line shown)": "Dlvl:1" in t1,
        "game saved and exited (status 0)": bool(saved) and s1.ended == "exit status 0",
        "restore greeted the player": "welcome back" in t2,
        "restored game exited (status 0)": s2 is not None and s2.ended == "exit status 0",
        "no panic or impossible()": "panic" not in both and "program in disorder" not in both,
    }
    for name, ok in checks.items():
        print("%-36s %s" % (name, "ok" if ok else "FAIL"))
    if all(checks.values()):
        sys.exit(0)
    # Keep the evidence (CI uploads these files when the job fails).
    for tag, s, t in (("s1", s1, t1), ("s2", s2, t2)):
        if s is None:
            print("%s: not run (no save file after s1)" % tag)
            continue
        print("%s: %s%s" % (tag, s.ended, "; " + s.problem if s.problem else ""))
        with open(os.path.join(INST, "smoke-%s.txt" % tag), "w",
                  encoding="latin-1") as f:
            f.write(t)
    print("save dir after session 1: %s" % (saved or "empty"))
    last = t2 if s2 else t1
    print("--- end of the last session, control sequences stripped:")
    print(strip_tty(last)[-1200:])
    print("--- transcripts: %s/smoke-s1.txt, smoke-s2.txt" % INST)
    sys.exit(1)


if __name__ == "__main__":
    main()
