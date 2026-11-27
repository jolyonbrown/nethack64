#!/usr/bin/env python3
"""window.py - how often a bank plan makes the C128's window load an REU bank, from the
host game's calls (tools/host-build.sh --calls writes them to $NH_CALLS_OUT).

usage: tools/measure/trace/window.py --plan PLAN.json --exe NETHACK --calls CALLS.bin
                                     [--top 25] [--json OUT]

The model is the bank call routine's (tools/bank/bankgen.py, ADR-0008): a call into a
banked function from code in another bank (or from resident code) maps the callee's bank
and, on return, maps back the bank that was mapped before; a call within a bank is direct.
Banks 1-63 are the cartridge's, mapped in place; banks from 64 on are copied from the REU
into the RAM window ($8000-$BFFF) when the window holds another, a "load" (16 KB, about
16.6 ms of DMA at 1 MHz). Mapping a cartridge bank leaves the window's copy as it is.
Functions the plan does not name are resident, but for a host stand-in file's (bank_of()). The host's calls are not the C128's
exactly (the host has no far data, and Oscar64 inlines some small functions), so the
counts are estimates; the C128's own nh_fetches counter checks them.

Its blind spot is the port's own code, which the host build does not run: the RAM disk
(port/sys/c64/c64sys.c; the host uses libc's files), the near heap (c64heap.c), c64tty.c.
On fc51 those caused 83% of the loads from start-up to the first --More--
(docs/data/loads-c128fc51d-2026-11-27.txt) and this model saw none of them: 589 loads to the
first turn here against the C128's 3,772.

Loads are put to a phase by the outermost function of interest on the call stack
(makelevel: the level's creation; u_init; the character menus; otherwise play), and to
the call that caused each one: the caller and callee of a call, or of a return.
"""
import argparse
import collections
import json
import os
import struct
import subprocess
import sys

PHASES = [("makelevel", "level creation"), ("goto_level", "level change"), ("u_init", "u_init"),
          ("tty_player_selection", "character menus"), ("docrt", "full redraw"),
          ("dorecover", "restore"), ("dosave0", "save")]


def symbols(exe):
    """address -> 'file.c:function' from nm's line numbers (-l), functions only"""
    out = subprocess.run(["nm", "-l", "--defined-only", exe], capture_output=True, text=True,
                         check=True).stdout
    sym = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[1] not in "tT":
            continue
        addr, name = int(parts[0], 16), parts[2]
        src = os.path.basename(parts[3].rsplit(":", 1)[0]) if len(parts) > 3 else "?"
        sym[addr] = "%s:%s" % (src, name)
    return sym


def load_trace(exe, calls):
    """(names, events): each event an index into names, times 2, plus 1 for an entry.
    The executable's start comes first in the file (nm's addresses are from it: PIE)."""
    sym = symbols(exe)
    data = open(calls, "rb").read()
    words = struct.unpack_from("<%dI" % ((len(data) - 8) // 4), data, 8)
    index, names, events = {}, [], []
    for w in words:
        off = w >> 1
        k = index.get(off)
        if k is None:
            k = index[off] = len(names)
            names.append(sym.get(off, "?%x" % off))
        events.append(k * 2 + (w & 1))
    return names, events


_alias = {}


def bank_of(name, banks):
    """the plan's bank for a host function; a function from a file the plan does not know
    (tools/host-s80.c, the host's stand-in for src/hal/vdc80.c) takes the bank of the one
    function of that name the plan has, if there is exactly one"""
    if name in banks:
        return banks[name]
    src, _, fn = name.partition(":")
    if any(k.startswith(src + ":") for k in banks):
        return None
    key = id(banks)
    if key not in _alias:
        idx = collections.defaultdict(list)
        for k in banks:
            idx[k.split(":", 1)[1]].append(k)
        _alias[key] = idx
    hits = _alias[key].get(fn, [])
    return banks[hits[0]] if len(hits) == 1 else None


def simulate(names, events, banks, detail=True):
    """REU bank loads under the plan's banks ({'file.c:fn': bank}); with detail, counters by
    phase, by call or return, by bank and by the function whose bank was loaded"""
    fbank = [bank_of(n, banks) for n in names]
    fphase = [dict(PHASES).get(n.split(":", 1)[-1]) for n in names]
    stack = []          # (function, saved mapped bank, or -1 when the call was direct)
    mapped = None
    window = None
    total = 0
    by_phase, by_pair, by_bank, by_fn = (collections.Counter() for _ in range(4))
    phase_stack = []
    for e in events:
        f = e >> 1
        b = fbank[f]
        if e & 1:
            if fphase[f]:
                phase_stack.append(fphase[f])
            cb = fbank[stack[-1][0]] if stack else None
            if b is not None and b != cb:
                stack.append((f, mapped))
                mapped = b
                if b >= 64 and window != b:
                    window = b
                    total += 1
                    if detail:
                        c = names[stack[-2][0]] if len(stack) > 1 else None
                        by_phase[phase_stack[0] if phase_stack else "play"] += 1
                        by_pair["%s -> %s (%s -> %s)" % (c, names[f], cb, b)] += 1
                        by_bank[b] += 1
                        by_fn[names[f]] += 1
            else:
                stack.append((f, -1))
        else:
            # pop to the matching frame (a longjmp can skip exits)
            while stack and stack[-1][0] != f:
                stack.pop()
            if not stack:
                continue
            _, saved = stack.pop()
            if fphase[f] and phase_stack and phase_stack[-1] == fphase[f]:
                phase_stack.pop()
            if saved != -1:
                mapped = saved
                if saved is not None and saved >= 64 and window != saved:
                    window = saved
                    total += 1
                    if detail:
                        back = names[stack[-1][0]] if stack else None
                        by_phase[phase_stack[0] if phase_stack else "play"] += 1
                        by_pair["%s <- %s (%s <- %s)" % (back, names[f], saved, b)] += 1
                        by_bank[saved] += 1
                        if back:
                            by_fn[back] += 1
    return total, by_phase, by_pair, by_bank, by_fn


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--exe", required=True)
    ap.add_argument("--calls", required=True)
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--json", help="write the counts here too")
    a = ap.parse_args()
    banks = json.load(open(a.plan))["banks"]
    names, events = load_trace(a.exe, a.calls)
    total, by_phase, by_pair, by_bank, by_fn = simulate(names, events, banks)
    calls = sum(e & 1 for e in events)
    print("%d calls, %d REU bank loads (%.1f s of DMA at 16.6 ms each)" % (calls, total, total * 0.0166))
    for p, c in by_phase.most_common():
        print("  %-18s %7d" % (p, c))
    print("top calls and returns that load a bank:")
    for k, c in by_pair.most_common(a.top):
        print("  %7d  %s" % (c, k))
    print("banks loaded most:", ", ".join("%d: %d" % kv for kv in by_bank.most_common(12)))
    unknown = sum(1 for n in names if n.startswith("?"))
    if unknown:
        print("%d functions in the trace with no symbol" % unknown)
    if a.json:
        json.dump({"calls": calls, "loads": total, "by_phase": by_phase, "by_pair": by_pair,
                   "by_bank": {str(k): v for k, v in by_bank.items()}, "by_fn": by_fn},
                  open(a.json, "w"), indent=1)


if __name__ == "__main__":
    sys.exit(main())
