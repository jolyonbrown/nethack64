#!/usr/bin/env python3
"""
run_selftests.py - run the AUTOTEST builds in VICE across the target matrix.

Each case boots VICE with the debug cartridge (-debugcart).  The program
writes its result to $D7FF, VICE exits with that value as its exit status:
    0  pass
    1  VICE hit -limitcycles (program hung or never reached the exit)
    2+ a numbered failure from src/main.c autotest()

A screenshot of every case is saved to build/test-<case>.png on exit, so a
failure can be looked at afterwards.

Uses xvfb-run when it is installed (no windows pop up); set VICE_SHOW=1 to
watch the runs instead.

usage: run_selftests.py [build_dir]
"""
import os
import shutil
import subprocess
import sys

BUILD = sys.argv[1] if len(sys.argv) > 1 else "build"
VICE = os.environ.get("VICE", "x64sc")
CYCLES = os.environ.get("TEST_CYCLES", "300000000")  # ~5 min of C64 time, seconds in warp

CASES = [
    # name,            image,            kind,  reu KB
    ("prg",            "test.prg",       "prg", 0),
    ("prg-reu512",     "test.prg",       "prg", 512),
    ("ef",             "test-ef.crt",    "crt", 0),
    ("ef-reu512",      "test-ef.crt",    "crt", 512),
    ("ef-reu16m",      "test-ef.crt",    "crt", 16384),
    # the C128 in its own mode (T2.13): x128, the VDC's 80 columns, no KERNAL
    ("c128-reu512",    "test128.prg",    "c128", 512),
]

# Arch's VICE 3.7.1 package lacks some of x128's national ROMs, without which x128 will
# not start: name the international ones (as tests/spikes/run_c128.py does)
X128_ROMS = []
for _opt in ("kernalde", "kernalfi", "kernalfr", "kernalit", "kernalno", "kernalse", "kernalch"):
    X128_ROMS += ["-" + _opt, "kernal-318020-05.bin"]
for _opt in ("chargde", "chargfr", "chargse", "chargch", "chargno"):
    X128_ROMS += ["-" + _opt, "chargen-390059-01.bin"]

FAILS = {1: "timeout (limitcycles reached)", 2: "walk", 3: "wall blocking",
         4: "REU DMA", 5: "REU restore mismatch", 6: "lrand48 differs from glibc",
         7: "REU size probe changed the REU or its answer",
         8: "s80_putca did not write the character or its colour",
         9: "the keyboard buffer's PETSCII did not map to the game's keys"}


def run_case(name, image, kind, reu):
    path = os.path.join(BUILD, image)
    shot = os.path.abspath(os.path.join(BUILD, "test-%s.png" % name))
    vice = os.environ.get("VICE128", "x128") if kind == "c128" else VICE
    args = [vice, "-default", "-warp", "+sound", "-debugcart",
            "-limitcycles", CYCLES, "-exitscreenshot", shot]
    if kind == "c128":
        args += X128_ROMS
    if reu:
        args += ["-reu", "-reusize", str(reu)]
    if kind == "crt":
        args += ["-cartcrt", path]
    else:
        args += ["-autostartprgmode", "1", "-autostart", path]
    if shutil.which("xvfb-run") and not os.environ.get("VICE_SHOW"):
        args = ["xvfb-run", "-a"] + args
    try:
        r = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
        return r.returncode
    except subprocess.TimeoutExpired:
        return 1


def main():
    if not shutil.which(VICE) or not shutil.which(os.environ.get("VICE128", "x128")):
        sys.exit("VICE (%s) not found; see docs/TOOLCHAIN.md" % VICE)
    failed = 0
    for name, image, kind, reu in CASES:
        rc = run_case(name, image, kind, reu)
        status = "PASS" if rc == 0 else "FAIL (%d: %s)" % (rc, FAILS.get(rc, "unknown"))
        print("%-12s %s" % (name, status))
        failed += rc != 0
    print("%d/%d passed" % (len(CASES) - failed, len(CASES)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
