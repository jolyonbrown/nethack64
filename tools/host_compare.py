#!/usr/bin/env python3
"""host_compare.py - does a change to port/ leave the host game's behaviour as it was?

usage: tools/host_compare.py [--rev HEAD] [--seeds 5,6,8] [--keys 3000] [--out DIR]

Builds the host game of git revision REV (port/, tools/, tests/ from `git archive`, in
DIR/rev) and of the working tree (tools/host-build.sh, build/host-install), then plays the
same bot game on both (tools/profile_play.py, one per seed) with the clock pinned: an
LD_PRELOAD time() that always answers the same, so NetHack seeds its random numbers the
same way.  The transcripts must match byte for byte, but for the build date in the
version line.  A control game on the working tree with another clock must not match, so
that a pass shows the comparison can fail.  Exit status 0 when every seed matches.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTIME = "#include <time.h>\ntime_t time(time_t *t) { if (t) *t = %d; return %d; }\n"
CLOCK, CONTROL = 1700000000, 1700000777


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit("%s failed:\n%s" % (" ".join(cmd), (r.stdout + r.stderr)[-3000:]))
    return r


def normal(path):
    text = open(path, encoding="latin-1").read()
    return re.sub(r"last build [A-Za-z]{3} [A-Za-z]{3} +\d+ [\d:]+ \d{4}", "last build X", text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rev", default="HEAD")
    ap.add_argument("--seeds", default="5,6,8")
    ap.add_argument("--keys", type=int, default=3000)
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "host-compare"))
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    libs = {}
    for name, t in (("clock", CLOCK), ("control", CONTROL)):
        c = os.path.join(out, name + ".c")
        open(c, "w").write(FIXTIME % (t, t))
        libs[name] = os.path.join(out, name + ".so")
        run(["gcc", "-shared", "-fPIC", "-o", libs[name], c])
    rev = os.path.join(out, "rev")
    os.makedirs(rev)
    arch = subprocess.run(["git", "-C", ROOT, "archive", a.rev, "port", "tools", "tests"],
                          capture_output=True, check=True).stdout
    subprocess.run(["tar", "xf", "-", "-C", rev], input=arch, check=True)
    print("building %s ..." % a.rev, flush=True)
    run([os.path.join(rev, "tools", "host-build.sh")], cwd=rev)
    print("building the working tree ...", flush=True)
    run([os.path.join(ROOT, "tools", "host-build.sh")], cwd=ROOT)
    installs = {"rev": os.path.join(rev, "build", "host-install"),
                "tree": os.path.join(ROOT, "build", "host-install")}

    def play(which, seed, lib):
        inst = os.path.join(out, "%s-%d-%s" % (which, seed, os.path.basename(lib)[:-3]))
        shutil.copytree(installs[which], inst)
        tr = inst + ".txt"
        env = dict(os.environ, LD_PRELOAD=lib)
        return subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "profile_play.py"),
                                 "--install", inst, "--keys", str(a.keys), "--seed", str(seed),
                                 "-o", inst + ".json", "--transcript", tr],
                                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL), tr

    seeds = [int(x) for x in a.seeds.split(",")]
    jobs = []
    for sd in seeds:
        jobs.append((sd, play("rev", sd, libs["clock"]), play("tree", sd, libs["clock"])))
    ctl = play("tree", seeds[0], libs["control"])
    for _, (p1, _), (p2, _) in jobs:
        p1.wait(), p2.wait()
    ctl[0].wait()
    bad = 0
    for sd, (_, t1), (_, t2) in jobs:
        same = normal(t1) == normal(t2)
        bad += not same
        print("seed %d: %s (%d bytes)" % (sd, "same" if same else "DIFFERENT", len(normal(t1))))
    if normal(ctl[1]) == normal(jobs[0][1][1]):
        print("control: the same as with the other clock, so the comparison shows nothing")
        bad += 1
    else:
        print("control (another clock): different, as it should be")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
