#!/usr/bin/env python3
"""loadlog.py - which calls make the C128 game load REU banks: read a --load-log build's
ring of loads (tools/bank/bankgen.py --load-log) from a running x128, name each load's
caller and callee, and play a list of prompts and answers meanwhile.

usage: tools/measure/trace/loadlog.py record BUILD_DIR OUT.jsonl [--step N] [--append]
                                      [--script "PROMPT=KEYS;..."] [--minutes 20]
       tools/measure/trace/loadlog.py summary OUT.jsonl [--top 20]

record: x128 must be running the build at real speed (not warp: a poll every few ms has
to come before 16 more loads fill the ring) with the binary monitor on (tools/vice.py
launch, without --warp). Each poll reads nh_fetches and, when it moved, the ring
(nh_flog, nh_flog_i), and writes each new load as a line of OUT: the count n, "call"
(the caller, its bank, the callee and its bank) or "ret" (the function returned to, its
bank), and the prompt waited for. Loads that came faster than the polls are counted as
missed. Every 2 s the screen is read (the VDC's, bit 7 off so that reverse video counts)
and, when the next prompt of the script (or one after it) shows, its keys are typed.
The default script plays a new game to the welcome --More--, as tools/measure/trace/
calls_game.py does on the host. A poll stops the CPU (the monitor), so the game runs
slower than at real speed; the loads it makes are the same.

summary: the loads of OUT by the prompt they came before, by call or return, by bank.
"""
import argparse
import collections
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import vice  # noqa: E402

SCRIPT = ("Who are you=Agent\r;Shall I pick=n;Pick a role=v;Pick the race=h;"
          "Pick the alignment=n;Is this ok=y;--More--=")
MAPLINE = re.compile(r"^(?:([0-9a-f]{2}):)?([0-9a-f]{4,5}) - ([0-9a-f]{4,5}) : ([^,]+), NATIVE_CODE:")


def symbols(d):
    syms = collections.defaultdict(list)   # bank (None: resident) -> [(start, end, name)]
    for line in open(os.path.join(d, "nethack.map"), errors="replace"):
        m = MAPLINE.match(line.strip())
        if m:
            b = int(m.group(1), 16) if m.group(1) else None
            syms[b].append((int(m.group(2), 16), int(m.group(3), 16), m.group(4)))
    labels = {}
    for line in open(os.path.join(d, "nethack.lbl")):
        p = line.split()
        if len(p) >= 3 and p[0] == "al":
            labels[p[2].lstrip(".")] = int(p[1], 16)
    return syms, labels


def namer(syms):
    def name(bank, addr):
        b = bank if 0x8000 <= addr < 0xC000 else None
        for s, e, n in syms.get(b, []):
            if s <= addr < e:
                return n
        return "?%04x" % addr
    return name


def decode(e, name):
    bank, call, tgt, st = e[0], e[1], e[2] | e[3] << 8, e[4:]
    if call == 1:
        saved, ret = st[4], (st[5] | st[6] << 8) + 1
        return {"k": "call", "from": name(saved, ret), "fb": saved, "to": name(bank, tgt), "tb": bank}
    return {"k": "ret", "to": name(bank, (st[2] | st[3] << 8) + 1), "tb": bank}


def record(a):
    syms, labels = symbols(a.build)
    if "nh_flog" not in labels:
        sys.exit("%s: no nh_flog (not a --load-log build)" % a.build)
    name = namer(syms)
    steps = [tuple(s.split("=", 1)) for s in a.script.split(";") if s]
    v = vice.Vice()
    fl, fi, fc_at = labels["nh_flog"], labels["nh_flog_i"], labels["nh_fetches"]

    def fetches():
        b = v.mem_get(fc_at, 2)
        return b[0] | b[1] << 8

    def screen():
        d = v.vdc_read(0, 2000)
        return "".join(chr(b & 0x7F) if 32 <= (b & 0x7F) < 127 else " " for b in d)

    out = open(a.out, "a" if a.append else "w")
    last, missed, step = None, 0, a.step
    t0 = tscr = time.time()
    while step < len(steps) and time.time() - t0 < a.minutes * 60:
        fc = fetches()
        if last is None:
            last = fc
        if fc != last:
            ring, i = v.mem_get(fl, 256), v.mem_get(fi, 1)[0]
            fc = fetches()
            n = (fc - last) & 0xFFFF
            take = min(n, 16)
            missed += n - take
            for j in range(take, 0, -1):
                p = (i - 16 * j) % 256
                ev = decode(ring[p:p + 16], name)
                ev["n"], ev["step"] = fc - j + 1, steps[step][0]
                out.write(json.dumps(ev) + "\n")
            out.flush()
            last = fc
        v.resume()
        if time.time() - tscr > 2:
            tscr = time.time()
            scr = screen()
            hit = [k for k in range(step, len(steps)) if steps[k][0] in scr]
            if hit:
                step = hit[0]
                print("%6.1f s  %5d loads, %d missed: %s" % (time.time() - t0, fc, missed, steps[step][0]),
                      flush=True)
                if steps[step][1]:
                    v.keys(steps[step][1])
                step += 1
            v.resume()
        time.sleep(0.005)
    out.close()
    print("%s: %d loads missed%s" % (a.out, missed, "" if step >= len(steps) else ", timed out"))
    return 0 if step >= len(steps) else 1


def summary(a):
    evs = [json.loads(line) for line in open(a.out)]
    by_step = collections.OrderedDict()
    for e in evs:
        by_step.setdefault(e["step"], []).append(e)
    for step, es in by_step.items():
        print("== before %r: %d loads (n %d-%d)" % (step, len(es), es[0]["n"], es[-1]["n"]))
        pairs, banks = collections.Counter(), collections.Counter()
        for e in es:
            if e["k"] == "call":
                pairs["%s (%s) -> %s (%s)" % (e["from"], e["fb"], e["to"], e["tb"])] += 1
            else:
                pairs["return to %s (%s)" % (e["to"], e["tb"])] += 1
            banks[e["tb"]] += 1
        for k, c in pairs.most_common(a.top):
            print("  %5d  %s" % (c, k))
        print("  banks loaded: " + ", ".join("%s: %d" % kv for kv in banks.most_common(10)))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("build")
    r.add_argument("out")
    r.add_argument("--script", default=SCRIPT, help="PROMPT=KEYS;... (\\r is RETURN)")
    r.add_argument("--step", type=int, default=0, help="start at this prompt of the script")
    r.add_argument("--append", action="store_true")
    r.add_argument("--minutes", type=float, default=20)
    s = sub.add_parser("summary")
    s.add_argument("out")
    s.add_argument("--top", type=int, default=20)
    a = ap.parse_args()
    if a.cmd == "record":
        a.script = a.script.replace("\\r", "\r")
        return record(a)
    return summary(a)


if __name__ == "__main__":
    sys.exit(main())
