#!/usr/bin/env python3
"""
smoke_stress.py - run tests/host_smoke.py many times, in parallel, and count
how each run ended.  For chasing a smoke-test failure that is rare on CI.

Each worker plays on its own copy of the install (lock and save files are
per game directory).  The game seeds its dungeon from the clock, so workers
that start in the same second would replay one game; cycle c therefore seeds
the walk with c.  A failing cycle keeps its output and transcripts.

usage: tools/smoke_stress.py [--install build/host-install] [--workers 6]
                             [--cycles 100] [--first 0] [--out build/smoke-stress]
  --cycles is per worker.  For the sanitizer build (tools/host-build.sh
  --sanitize) use --install build/host-asan-install and set, for example,
  ASAN_OPTIONS=halt_on_error=0:detect_leaks=0:log_path=build/smoke-stress/asan
"""
import argparse
import collections
import contextlib
import io
import json
import os
import random
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def worker(inst, first, step, count, out):
    sys.argv = [sys.argv[0], inst]
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import host_smoke as hs
    seed, run = random.seed, hs.Session.run
    for c in range(first, first + step * count, step):
        ended = []

        def run_and_note(self, script):
            t = run(self, script)
            ended.append([self.ended, self.problem])
            return t
        hs.Session.run = run_and_note
        hs.random.seed = lambda _fixed, c=c: seed(c)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                hs.main()
                rc = 0
            except SystemExit as e:
                rc = e.code
        if rc != 0:
            d = os.path.join(out, "fail-%05d" % c)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "output.txt"), "w") as f:
                f.write(buf.getvalue())
            for name in ("smoke-s1.txt", "smoke-s2.txt"):
                if os.path.exists(os.path.join(inst, name)):
                    shutil.move(os.path.join(inst, name), os.path.join(d, name))
        print(json.dumps({"cycle": c, "rc": rc, "sessions": ended}), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", default="build/host-install")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--cycles", type=int, default=100)
    ap.add_argument("--first", type=int, default=0)
    ap.add_argument("--out", default="build/smoke-stress")
    ap.add_argument("--worker", nargs=4, help=argparse.SUPPRESS)
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    if a.worker:
        inst, first, step, count = a.worker
        worker(inst, int(first), int(step), int(count), out)
        return
    os.makedirs(out, exist_ok=True)
    procs = []
    for k in range(a.workers):
        inst = os.path.join(out, "inst-%d" % k)
        shutil.rmtree(inst, ignore_errors=True)
        shutil.copytree(a.install, inst, symlinks=True)
        procs.append(subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--out", out, "--worker",
             inst, str(a.first + k), str(a.workers), str(a.cycles)],
            stdout=subprocess.PIPE, text=True))
    outcomes = collections.Counter()
    for p in procs:
        for line in p.stdout:
            r = json.loads(line)
            outcomes[(r["rc"],) + tuple("%s%s" % (e, "; " + q if q else "")
                                        for e, q in r["sessions"])] += 1
        p.wait()
    print("%d cycles" % sum(outcomes.values()))
    for (rc, *sessions), n in outcomes.most_common():
        print("%5d  rc %d  %s" % (n, rc, " | ".join(sessions)))
    sys.exit(1 if any(k[0] for k in outcomes) else 0)


if __name__ == "__main__":
    main()
