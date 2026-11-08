#!/usr/bin/env python3
"""
host_smoke.py - play, save and restore the host build of port/.

A cheap behavioural regression test for changes to the shared game source:
if the converted/trimmed NetHack still starts, accepts commands, writes a
save file and restores it, the change probably did not break the engine.

Needs: tools/host-build.sh to have run; python3 -m pip install pexpect
usage: tests/host_smoke.py [install_dir]   (default build/host-install)
"""
import os
import random
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


def session(keys):
    child = pexpect.spawn(EXE, ["-d", GAMEDIR, "-u", "smoke"], env=ENV,
                          encoding="latin-1", dimensions=(24, 80), timeout=10)
    out = ""
    for k in keys:
        time.sleep(0.1)
        child.send(k)
        try:
            out += child.read_nonblocking(65536, timeout=0.3)
        except (pexpect.TIMEOUT, pexpect.EOF):
            pass
    try:
        child.expect(pexpect.EOF, timeout=15)
        out += child.before or ""
    except pexpect.TIMEOUT:
        child.terminate(force=True)
        out += "\n[TIMEOUT]"
    return out


def main():
    if not os.path.exists(EXE):
        sys.exit("no host build at %s; run tools/host-build.sh" % EXE)
    savedir = os.path.join(GAMEDIR, "save")
    for f in os.listdir(savedir):
        os.remove(os.path.join(savedir, f))
    random.seed(343)
    walk = "".join(random.choice("hjklyubn") for _ in range(150))

    s1 = session(["\r", "\r"] + list(walk) + ["i", "\x1b", "s", "s", "S", "y"])
    saved = os.listdir(savedir)
    s2 = session(["\r", "\r"] + list(walk[:40]) + ["#quit\r", "y", "q", "q", "\r", "\r", "\r"])

    checks = {
        "game started (status line shown)": "Dlvl:1" in s1,
        "save file written": bool(saved),
        "restore greeted the player": "welcome back" in s2,
        "no panic": "panic" not in (s1 + s2).lower(),
    }
    for name, ok in checks.items():
        print("%-36s %s" % (name, "ok" if ok else "FAIL"))
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
