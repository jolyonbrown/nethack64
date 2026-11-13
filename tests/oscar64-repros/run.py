#!/usr/bin/env python3
"""
Run every Oscar64 compatibility repro and say which are still broken.

Each rNN_*.c file documents one Oscar64 behaviour that NetHack 3.4.3's source
trips over, the workaround we use, and what "fixed" looks like.  Re-run this
after every Oscar64 upgrade (`make repros`): when a repro flips to FIXED the
matching workaround in tools/oscar_normalize.py (or elsewhere) can be retired,
and docs/OSCAR64-COMPAT.md should be updated.

Header keys read from each file's first comment:
    FLAGS: <oscar64 flags>     e.g. -e (run in Oscar64's built-in emulator)
    ENV: NAME=value ...        extra environment for the compiler itself (r38: glibc's
                               MALLOC_PERTURB_, for a bug that depends on old heap contents)
    COMPILE-ONLY               success = compiler exits 0
Otherwise success = compiles and "Emulation result 0".
"""
import glob
import os
import re
import resource
import subprocess
import sys
import tempfile

OSCAR64 = os.environ.get("OSCAR64", "oscar64")
HERE = os.path.dirname(os.path.abspath(__file__))
# Some Oscar64 bugs make the compiler's memory grow without bound; uncapped, the kernel's
# OOM killer stops it (or something else).  Under the cap it ends in std::bad_alloc.
MEMORY_MB = int(os.environ.get("REPRO_MEMORY_MB", "3000"))


def cap_memory():
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_MB << 20, MEMORY_MB << 20))


def run(path):
    head = open(path).read(2000)
    flags = re.search(r"FLAGS:\s*(.*)", head)
    flags = flags.group(1).split() if flags else ["-e"]
    compile_only = "COMPILE-ONLY" in head
    env = re.search(r"ENV:\s*(.*)", head)
    env = dict(os.environ, **dict(kv.split("=", 1) for kv in env.group(1).split())) if env else None
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "r.prg")
        try:
            r = subprocess.run([OSCAR64] + flags + ["-o=" + out, path],
                               capture_output=True, text=True, timeout=120, preexec_fn=cap_memory,
                               env=env)
        except subprocess.TimeoutExpired:
            return "BROKEN", "compiler hang"
    text = r.stdout + r.stderr
    if (r.returncode < 0 or r.returncode >= 128) and ("std::bad_alloc" in text or r.returncode == -9):
        return "BROKEN", "compiler out of memory (cap %d MB)" % MEMORY_MB
    if r.returncode < 0 or r.returncode >= 128:
        return "BROKEN", "compiler crashed (signal %d)" % (-r.returncode if r.returncode < 0 else r.returncode - 128)
    err = [l for l in text.splitlines() if "error" in l]
    if err:
        return "BROKEN", re.sub(r".*?: error", "error", err[0])[:70]
    if compile_only:
        return ("FIXED", "compiles") if r.returncode == 0 else ("BROKEN", "exit %d" % r.returncode)
    m = re.search(r"Emulation result (-?\d+)", text)
    if m and m.group(1) == "0":
        return "FIXED", "runs, result 0"
    return "BROKEN", "wrong result %s" % (m.group(1) if m else "?")


def main():
    try:
        subprocess.run([OSCAR64], capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("oscar64 not found (set OSCAR64=/path/to/oscar64)")
    files = sorted(glob.glob(os.path.join(HERE, "r*_*.c")),
                   key=lambda p: int(re.match(r"r(\d+)", os.path.basename(p)).group(1)))
    fixed = 0
    for f in files:
        status, why = run(f)
        fixed += status == "FIXED"
        print("%-38s %-7s %s" % (os.path.basename(f), status, why))
    print("%d of %d repros now pass" % (fixed, len(files)))


if __name__ == "__main__":
    main()
