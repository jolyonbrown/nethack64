#!/usr/bin/env python3
"""
run_bankcall.py - build tests/spikes/bankcall.c both ways, run each in headless VICE and
print what it measured (docs/BANKING-SPIKE.md): the cost of a call into another EasyFlash
bank through a trampoline, and of REU fetches into $8000.

usage: tests/spikes/run_bankcall.py      (needs oscar64, x64sc, xvfb-run; uses port 6502)
"""
import os
import re
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "build", "spikes")
SRC = os.path.join(ROOT, "tests", "spikes", "bankcall.c")
VICE = [sys.executable, os.path.join(ROOT, "tools", "vice.py")]
N = 64


def build(name, args):
    path = os.path.join(OUT, name)
    r = subprocess.run(["oscar64", "-Os", "-g"] + args + ["-o=" + path, SRC], capture_output=True, text=True)
    if r.returncode:
        sys.exit("build of %s failed:\n%s" % (name, r.stdout + r.stderr))
    return path


def label(lbl, name):
    for line in open(lbl):
        m = re.match(r"al ([0-9a-f]+) \.%s\s*$" % re.escape(name), line)
        if m:
            return int(m.group(1), 16)
    sys.exit("no label %s in %s" % (name, lbl))


def mem(addr, n):
    r = subprocess.run(VICE + ["mem", hex(addr), str(n)], capture_output=True, text=True)
    vals = [int(x, 16) for x in re.findall(r"\b[0-9a-f]{2}\b", r.stdout.split(":", 1)[-1])]
    return vals[:n]


def run(image, kind, reu):
    lbl = image.rsplit(".", 1)[0] + ".lbl"
    done, result = label(lbl, "spike_done"), label(lbl, "spike_result")
    subprocess.run(VICE + ["launch", "--" + kind, image, "--reu", str(reu), "--headless", "--warp"],
                   check=True, capture_output=True)
    try:
        for _ in range(100):
            if mem(done, 1)[:1] == [1]:
                break
            time.sleep(0.2)
        else:
            sys.exit("%s never set spike_done" % image)
        b = mem(result, 8)
        return [b[i] | b[i + 1] << 8 for i in range(0, 8, 2)]
    finally:
        subprocess.run(VICE + ["quit"], capture_output=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    crt = build("bankcall.crt", ["-tf=crt"])
    prg = build("reutime.prg", ["-dREUTIME"])
    res, same, cross, base = run(crt, "crt", 512)
    print("EasyFlash, %d calls each, cycles per call above the in-line loop:" % N)
    print("  resident call            %6.1f" % ((res - base) / N))
    print("  call within a bank       %6.1f" % ((same - base) / N))
    print("  call to another bank     %6.1f  (through a resident C trampoline)" % ((cross - base) / N))
    one, k1, k4, k16 = run(prg, "prg", 512)
    print("REU fetch into $8000 (cycles for the whole transfer, set-up included):")
    for what, c in (("1 byte", one), ("1 KB", k1), ("4 KB", k4), ("16 KB", k16)):
        print("  %-8s %6d  (%.0f us at 0.985 MHz)" % (what, c, c / 0.985))
    print("  per KB beyond the first byte: %.0f cycles" % ((k16 - one) / 16.0))


if __name__ == "__main__":
    main()
