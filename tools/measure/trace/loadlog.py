#!/usr/bin/env python3
"""loadlog.py - which calls make the C128 game load REU banks: read a --load-log build's
ring of loads (tools/bank/bankgen.py --load-log) from a running x128, name each load's
caller and callee, and play a list of prompts and answers meanwhile.

usage: tools/measure/trace/loadlog.py record BUILD_DIR OUT.jsonl [--step N] [--append]
                                      [--script "PROMPT=KEYS;..."] [--minutes 20]
       tools/measure/trace/loadlog.py summary OUT.jsonl [--top 20]

record: x128 must be running the build at real speed (not warp: a poll every few ms has
to come before 16 more loads fill the ring) with the binary monitor on (tools/vice.py
launch, without --warp; a load's DMA alone takes 16 ms, and the ring holds 4). Each poll reads nh_fetches and, when it moved, the ring
(nh_flog, nh_flog_i), and writes each new load as a line of OUT: the count n, "call"
(the caller, its bank, the callee and its bank) or "ret" (the function returned to, its
bank), and the prompt waited for. Loads that came faster than the polls are counted as
missed. Every 2 s the screen is read (the VDC's, bit 7 off so that reverse video counts)
and, when the script's next prompt shows, its keys are typed; a --More-- that the script
does not wait for gets a space (unless --keep-more).
Every 20th poll also walks the near heap's free list: the least free seen is printed
(and with --heap-dump, the heap's blocks at that moment written out). A caller reached
through a function pointer (windowprocs) and a resident trampoline is misnamed: the stack
is not as the decoder expects there.
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
          "Pick the alignment=n;--More--=")
RING = 64          # bankgen.py --load-log's nh_flog: 4 entries of 16 bytes
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
    has_ring = "nh_flog" in labels   # a --load-log build; otherwise the heap alone
    name = namer(syms)
    steps = [tuple(s.split("=", 1)) for s in a.script.split(";") if s]
    v = vice.Vice()
    fl, fi, fc_at = labels.get("nh_flog"), labels.get("nh_flog_i"), labels["nh_fetches"]

    def fetches():
        b = v.mem_get(fc_at, 2)
        return b[0] | b[1] << 8

    def screen():
        d = v.vdc_read(0, 2000)
        return "".join(chr(b & 0x7F) if 32 <= (b & 0x7F) < 127 else " " for b in d)

    def heap_free():
        """the near heap's free bytes, from Oscar64's free list (crt.c: HeapNode, then
        blocks of {next, end}), or None before the first malloc()"""
        p, total = labels["HeapNode"], 0
        if not any(v.mem_get(p + 2, 2)):
            return None         # crt_malloc sets the dummy node's size on its first call
        for _ in range(64):
            b = v.mem_get(p, 4)
            p = b[0] | b[1] << 8
            if p == 0:
                return total
            if not labels["HeapStart"] <= p < labels["HeapEnd"]:
                return None     # not set up yet (or read in the middle of a change)
            e = v.mem_get(p + 2, 2)
            total += (e[0] | e[1] << 8) - p
        return None

    def heap_blocks():
        """the near heap block by block: (address, size, used, first bytes); a used block at p
        holds its end at p, its data from p + 2"""
        hs, he = labels["HeapStart"], labels["HeapEnd"]
        mem = v.mem_get(hs, he - hs)
        def w(x):
            return mem[x - hs] | mem[x - hs + 1] << 8
        free, b = {}, v.mem_get(labels["HeapNode"], 2)
        p = b[0] | b[1] << 8
        while p and hs <= p < he and len(free) < 256:
            free[p] = w(p + 2)
            p = w(p)
        rows, p = [], hs | 2
        while p < he - 2:
            e = free.get(p) or w(p)
            if not p < e <= he:
                break
            rows.append((p, e - p, p not in free, bytes(mem[p + 2 - hs:min(e, p + 18) - hs])))
            p = e
        return rows

    out = open(a.out, "a" if a.append else "w")
    last, missed, step = None, 0, a.step
    polls, low, step_low = 0, None, None
    t0 = tscr = time.time()
    while step < len(steps) and time.time() - t0 < a.minutes * 60:
        fc = fetches()
        if last is None:
            last = fc
        if fc != last and not has_ring:
            last = fc
        if fc != last:
            ring, i = v.mem_get(fl, RING), v.mem_get(fi, 1)[0]
            fc = fetches()
            n = (fc - last) & 0xFFFF
            if n > 0x8000:
                n = fc          # read before the game zeroed the counter
            take = min(n, RING // 16)
            missed += n - take
            for j in range(take, 0, -1):
                p = (i - 16 * j) % RING
                ev = decode(ring[p:p + 16], name)
                ev["n"], ev["step"] = fc - j + 1, steps[step][0]
                out.write(json.dumps(ev) + "\n")
            out.flush()
            last = fc
        polls += 1
        if polls % 20 == 0:
            f = heap_free()
            if f is not None and (step_low is None or f < step_low):
                step_low = f
            if f is not None and (low is None or f < low):
                low = f
                if a.heap_dump:
                    with open(a.heap_dump, "w") as hd:
                        hd.write("near heap at %d bytes free (loads %d, before %r)\n" % (f, fc, steps[step][0]))
                        for p, n, u, d in heap_blocks():
                            hd.write("%04x %5d %s %s  %s\n" % (p, n, "used" if u else "free", d[:8].hex(),
                                     "".join(chr(c) if 32 <= c < 127 else "." for c in d)))
        v.resume()
        if time.time() - tscr > 2:
            tscr = time.time()
            scr = screen()
            if "--More--" in scr and steps[step][0] != "--More--" and not a.keep_more:
                v.keys(" ")     # a message the script did not wait for: on with the game
            elif steps[step][0] in scr:
                print("%6.1f s  %5d loads, %d missed, near heap free %s at least (%s since the last "
                      "prompt): %s" % (time.time() - t0, fc, missed, low, step_low, steps[step][0]), flush=True)
                step_low = None
                if steps[step][1]:
                    v.keys(steps[step][1])
                step += 1
            v.resume()
        time.sleep(0.005)
    out.close()
    print("%s: %d loads missed; the near heap had %s bytes free at least (of %d)%s" % (
        a.out, missed, low, labels["HeapEnd"] - labels["HeapStart"], "" if step >= len(steps) else ", timed out"))
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
    r.add_argument("--heap-dump", help="write the near heap's blocks here at each new low")
    r.add_argument("--keep-more", action="store_true",
                   help="do not answer a --More-- that the script does not name with a space")
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
