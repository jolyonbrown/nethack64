#!/usr/bin/env python3
"""build_c64.py - compile the whole of NetHack, rewritten for a bank plan by bankgen.py,
in one Oscar64 run, and check the calls in its listing (the banking spike,
docs/BANKING-SPIKE.md).

usage: tools/bank/build_c64.py --plan PLAN.json [--out DIR] [--check-only]

1. Sets up tools/measure/measure_oscar64.py's harness for the C64 configuration in DIR
   (default build/bank-c64): every port/src file, and stubs from mkstubs.py for what no
   file defines (libc, the window port), with its main() referring to every function.
2. Rewrites the sources with bankgen.py.
3. Compiles all of them in one Oscar64 run (-Os, a .prg).  The data does not fit in RAM
   yet (T2.3), so "could not place" errors for data are expected; the code is placed.
4. Checks the listing: every JSR or JMP in a function of bank N goes to a function of
   bank N, to resident code, or is a trampoline calling into the bank it selected; and no
   resident code calls into a bank except a trampoline.  A call into the bank window is
   resolved through the map in the caller's bank (the listing names such an address after
   whichever bank's object is there).  Then checks the intermediate code, which names every
   direct callee, the same way, and that no banked function writes the bank register or
   has its address taken (so calls through pointers reach resident code only).  And
   tools/check_listing.py's two checks: no zero-page temporary past $8F (compat #72) and no
   branch out of range (compat #73).  Reports the bytes per bank, the resident code,
   resident code inside the bank window, and what a failed link left unplaced.

--linker-stubs: for an Oscar64 whose linker inserts the bank switches (Linker::InsertBankCalls,
the pin from commit 72, ADR-0007): bankgen.py gives trampolines only to the functions that
take or return strings, a call across banks in the intermediate code is expected (only one to
a renamed twin, name__bN, from outside its bank is not), and the stubs are counted.

Environment: OSCAR64 (the compiler; it must take banks past 63 for an 84-bank plan),
BANK_TIMEOUT (seconds for the compile, default 3600), BANK_MEMORY_MB (its address-space
cap, default 3000; the whole game needs more than that).
"""
import argparse
import collections
import json
import os
import re
import resource
import shutil
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "measure"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import measure_oscar64 as mo   # noqa: E402
import check_listing   # noqa: E402

INSN = re.compile(r"^(?:([0-9a-f]{2}):)?([0-9a-f]{4}) : (?:[0-9a-f_ ]{8}) (\w+)\s+(\S+)?(?:\s*; \(([^ .)]+))?")
FUNC = re.compile(r"^([A-Za-z_]\w*): ; ")
# a bank call stub (Linker::InsertBankCalls), resident or in its caller's bank: its bank and
# function bytes are data, which the listing shows as instructions (bank $20 as a JSR)
STUB = re.compile(r"^\S+@bankcall\d*: ; ")
BANKED = re.compile(r"^(\w+)__b(\d+)$")


def cap():
    mb = int(os.environ.get("BANK_MEMORY_MB", "3000"))
    resource.setrlimit(resource.RLIMIT_AS, (mb << 20,) * 2)


def check(asm, mapfile=None):
    """Calls that cross banks in an Oscar64 listing: [(caller, caller bank, callee,
    callee bank)], and the number of calls looked at.  Every bank's code starts at $8000,
    so the listing names an address in the bank window after whichever bank's object is
    there; with the map, such a call is resolved in the caller's own bank instead (a
    trampoline's, in the bank of its own function)."""
    spans = collections.defaultdict(list)       # bank (None: resident) -> [(start, end, name)]
    if mapfile and os.path.exists(mapfile):
        for line in open(mapfile, errors="replace"):
            m = OBJ.match(line)
            if m and m.group(5) == "NATIVE_CODE":
                spans[None if m.group(1) == "--" else int(m.group(1), 16)].append(
                    (int(m.group(2), 16), int(m.group(3), 16), m.group(4)))

    def within(bank, addr):
        for a, e, n in spans.get(bank, ()):
            if a <= addr < e:
                return n
        return None

    bank_of, calls, cur, cur_bank = {}, [], None, None
    selects, last_imm = collections.defaultdict(set), None
    for line in open(asm, errors="replace"):
        m = FUNC.match(line)
        if m:
            cur, cur_bank = m.group(1), "unseen"
            continue
        if STUB.match(line):
            cur = None
            continue
        m = INSN.match(line)
        if not m or cur is None:
            continue
        if m.group(3) == "LDA" and m.group(4) and m.group(4).startswith("#$"):
            last_imm = int(m.group(4)[2:], 16)
        elif m.group(3) == "STA" and m.group(4) and m.group(4).lower() == "$de00" and last_imm is not None:
            selects[cur].add(last_imm)
        b = int(m.group(1), 16) if m.group(1) else None
        if cur_bank == "unseen":
            cur_bank = b
            bank_of[cur] = b
        if m.group(3) in ("JSR", "JMP") and m.group(5) and not m.group(4).startswith("("):
            addr = int(m.group(4)[1:], 16) if re.match(r"^\$[0-9a-fA-F]{4}$", m.group(4)) else None
            calls.append((cur, b, m.group(5), addr))
    bad = []
    for caller, cb, callee, addr in calls:
        if spans and addr is not None and 0x8000 <= addr < 0xc000:
            if (cb is not None and within(cb, addr)) or within(None, addr):
                continue                   # in the caller's own bank, or resident
            if cb is None and any(within(bk, addr) for bk in selects.get(caller, ())):
                continue                   # a trampoline calls into the bank it has selected
            if cb is None and any(a == addr and n == "%s__b%d" % (caller, bk)
                                  for bk, sp in spans.items() if bk is not None for a, e, n in sp):
                continue                   # the trampoline calls its own function
            bad.append((caller, cb, "$%04x" % addr, None))
            continue
        if callee not in bank_of or callee == caller:
            continue
        tb = bank_of[callee]
        if tb is None or tb == cb:
            continue
        mm = BANKED.match(callee)
        if cb is None and mm and mm.group(1) == caller and int(mm.group(2)) == tb:
            continue                       # the trampoline calls its own function
        bad.append((caller, cb, callee, tb))
    return bad, len(calls), bank_of


OBJ = re.compile(r"^(--|[0-9a-f]{2}):([0-9a-f]{4,5}) - ([0-9a-f]{4,5}) : ([^,]+), (\w+):(\S+)")


def unplaced(mapfile):
    """Objects a failed link left unplaced (address 0000, no bank): {(kind, banked): bytes}."""
    out = collections.Counter()
    for line in open(mapfile, errors="replace"):
        m = re.match(r"^0000 - ([0-9a-f]{4,5}) : [^,]+, (\w+):(\S+)", line)
        if m:
            out[(m.group(2), m.group(3).startswith("nhbank_"))] += int(m.group(1), 16)
    return out


def longest_literal(mapfile):
    """The largest anonymous data object (a literal) placed in a bank of an Oscar64 map."""
    n = 0
    for line in open(mapfile, errors="replace"):
        m = OBJ.match(line)
        if m and m.group(1) != "--" and m.group(4) == "*" and m.group(5) == "DATA" \
                and m.group(6).startswith("nhbank_"):
            n = max(n, int(m.group(3), 16) - int(m.group(2), 16))
    return n


def sizes(mapfile):
    """From an Oscar64 map: bytes per bank (code and its literals), resident code, and the
    trampolines (resident functions with a banked name__bN); the linker's bank call stubs
    (name@bankcall) are in sizes.stubs."""
    per_bank, resident, objs, names = collections.Counter(), 0, {}, set()
    sizes.stubs = {}
    in_window = sizes.in_window = []
    for line in open(mapfile, errors="replace"):
        m = OBJ.match(line)
        if not m:
            continue
        if m.group(5) == "NATIVE_CODE":
            names.add(m.group(4))
            if m.group(1) == "--" and 0x8000 <= int(m.group(2), 16) < 0xc000:
                in_window.append(m.group(4))
        a, b = int(m.group(2), 16), int(m.group(3), 16)
        if b < a:
            continue
        bank = None if m.group(1) == "--" else int(m.group(1), 16)
        if bank is not None and m.group(6).startswith("nhbank_"):
            per_bank[bank] += b - a
        elif bank is None and m.group(5) == "NATIVE_CODE":
            resident += b - a
            objs[m.group(4)] = b - a
            if m.group(4).endswith("@bankcall"):
                sizes.stubs[m.group(4)] = b - a
    banked = {BANKED.match(n).group(1) for n in names if BANKED.match(n)}
    tramp = {n: z for n, z in objs.items() if n in banked}
    return per_bank, resident, tramp


ANYOBJ = re.compile(r"^(?:(?:--|[0-9a-f]{2}):)?[0-9a-f]{4,5} [-(] [0-9a-f]{4,5}\)? : ([^,]+), (\w+):(\S+)")
CALL = re.compile(r"\tCALL\w*\t[^\t]*\t<-\t(?:V\(-?\d+ '([^']*)'\)|(\S+))")
PROC = re.compile(r"^([A-Za-z_]\w*): \S")
WRAPPER = re.compile(r"^(\w+?)__([tx])(\d+)$")
BANKREG = "V(-1 '')+56832"     # $DE00, EasyFlash's bank register


def check_int(intfile, mapfile, linker_stubs=False):
    """Calls that cross banks, from the intermediate code, which names every direct callee.
    Returns the bad calls [(caller, caller bank, callee, callee bank)], the banked
    functions that store to the bank register, the direct calls looked at, and the calls
    through pointers made by banked functions.  With linker_stubs, the linker switches the
    bank for a call across banks, so only one that reaches a renamed twin (name__bN) from
    outside its bank, skipping the trampoline's string copies, is bad."""
    bank = {}
    for line in open(mapfile, errors="replace"):
        m = ANYOBJ.match(line)
        if m and m.group(2) == "NATIVE_CODE":
            sec = re.match(r"nhbank_(\d+)$", m.group(3))
            bank[m.group(1)] = int(sec.group(1)) if sec else None
    bad, switching, ncalls, ptr = [], set(), 0, 0
    copies_args = {WRAPPER.match(n).group(1) for n in bank if WRAPPER.match(n) and WRAPPER.match(n).group(2) == "t"}
    proc, header, selects, taken = None, True, set(), set()
    for line in open(intfile, errors="replace"):
        if line.startswith("----"):
            header = True
            continue
        if header:
            m = PROC.match(line)
            proc, header, selects = (m.group(1) if m else None), False, set()
            continue
        if proc is None or proc not in bank:
            continue                       # not emitted: inlined wherever it was called
        pb = bank.get(proc)
        f = line.split("\t")
        if len(f) > 2 and not f[2].startswith("CALL"):
            for ref in re.findall(r"V\(-?\d+ '(\w+__b\d+)'", line):
                taken.add((proc, ref))
        if len(f) > 2 and f[2].startswith("STORE") and BANKREG in line:
            if pb is not None:
                switching.add(proc)
            sel = re.search(r", CC:(\d+)", line)
            if sel:
                selects.add(int(sel.group(1)))
        m = CALL.search(line)
        if not m:
            continue
        if m.group(1) is None:
            ptr += pb is not None
            continue
        ncalls += 1
        callee, cb = m.group(1), bank.get(m.group(1))
        if cb is None or cb == pb:
            continue
        if pb is None and cb in selects:
            continue                       # a trampoline calls into the bank it has selected
        if linker_stubs:
            # bankgen.py's split trampolines: f__tA copies f's string arguments in bank A,
            # f__xN copies its string result in bank N (f__bN is f itself)
            w = WRAPPER.match(callee)
            if w and w.group(2) == "t":
                bad.append((proc, pb, callee, cb))     # skips the copies, from another bank
                continue
            if w and w.group(2) == "x" and w.group(1) in copies_args and \
                    not re.match(r"^%s(?:__t\d+)?$" % re.escape(w.group(1)), proc):
                bad.append((proc, pb, callee, cb))     # skips the argument copies
                continue
            if not BANKED.match(callee):
                continue                   # the linker inserts the bank switch
            if re.match(r"^%s(?:__t\d+)?$" % re.escape(BANKED.match(callee).group(1)), proc):
                continue                   # its trampoline (resident, or in the caller's bank)
        bad.append((proc, pb, callee, cb))
    return bad, sorted(switching), ncalls, ptr, sorted(taken)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "bank-c64"))
    ap.add_argument("--check-only", action="store_true", help="only check an earlier build's listing")
    ap.add_argument("--main", choices=("table", "real"), default="table",
                    help="table: the harness's main() referring to every function; real: the game's "
                         "own (newgame(); moveloop();), so only what it reaches is compiled and only "
                         "what it takes the address of is called through pointers")
    ap.add_argument("--linker-stubs", action="store_true",
                    help="the compiler's linker inserts the bank switches (see above)")
    ap.add_argument("--far", action="store_true",
                    help="the far spaces (T2.11-T2.12, ADR-0009): -dNH_FAR_SPACES for the compile and "
                         "for bankgen.py's view of the sources, and tools/measure/far_meas.c's runtime")
    ap.add_argument("--generate-only", action="store_true",
                    help="write the rewritten sources and compile.args (the compile's arguments, "
                         "relative to DIR) without compiling, e.g. to compile on a bigger machine")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    prg = os.path.join(out, "nethack.prg")
    if not a.check_only:
        mo.CONFIG, mo.OUT, mo.DEFS = "c64", out, mo.CONFIGS["c64"]["defs"]
        mo.setup()
        src = os.path.join(out, "src")
        files = sorted(f for f in os.listdir(src) if f.endswith(".c"))
        cpp = mo.CONFIGS["c64"]["cpp"]
        env = dict(os.environ, MKSTUBS_DEFS=" ".join(cpp))
        h = os.path.join(out, "h_all.c")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "measure", "mkstubs.py"),
                            os.path.join(out, "inc"), src, "allmain.c", h] +
                           [f for f in files if f != "allmain.c"], env=env, capture_output=True, text=True)
        if r.returncode:
            sys.exit("mkstubs.py failed:\n" + r.stdout + r.stderr)
        print("stubs:", r.stdout.strip())
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "bank", "bankgen.py"),
                            "--plan", os.path.abspath(a.plan), "--dir", src,
                            "--inc", os.path.join(out, "inc"), "--inc", os.path.join(out, "stub"),
                            "--inc", os.path.join(out, "fakelibc"), "--cpp=-nostdinc",
                            "--cpp=-D__attribute__(x)=", "--report", os.path.join(out, "bankgen-report.json")] +
                           ["--cpp=" + c for c in cpp] + (["--cpp=-DNH_FAR_SPACES"] if a.far else []) +
                           (["--linker-stubs"] if a.linker_stubs else []) +
                           files, capture_output=True, text=True)
        if r.returncode:
            sys.exit("bankgen.py failed:\n" + r.stdout + r.stderr)
        print(r.stdout.strip())
        if a.main == "real":
            text = open(h).read()
            stubs = text[:text.index("void *nh_refs[] = {")]
            h = os.path.join(out, "h_real.c")
            open(h, "w").write(stubs + "/* the game's own entry, as sys/unix/unixmain.c makes it */\n"
                               "int main(void) { newgame(); moveloop(); return 0; }\n")
        # -xb: the game never returns to BASIC, so main need not keep BASIC's zero page
        # (the pin's -Ot, part of -Os, then saves less in the game's functions)
        args = ["-rmp", "-Os", "-xb", "-i=inc", "-i=stub", "-i=src", "-o=nethack.prg"] + \
            ["src/" + f for f in files] + [os.path.basename(h)] + mo.DEFS
        if a.far:
            shutil.copy(os.path.join(ROOT, "tools", "measure", "far_meas.c"), out)
            args += ["-dNH_FAR_SPACES", "far_meas.c"]
        if a.generate_only:
            open(os.path.join(out, "compile.args"), "w").write("\n".join(args) + "\n")
            print("generated: compile in %s with oscar64 $(cat compile.args)" % out)
            return 0
        cmd = [mo.OSCAR64] + args
        t = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=out, preexec_fn=cap,
                               timeout=int(os.environ.get("BANK_TIMEOUT", "3600")))
        except subprocess.TimeoutExpired:
            sys.exit("the compile did not finish")
        open(os.path.join(out, "compile.log"), "w").write(r.stdout + r.stderr)
        errs = [l for l in (r.stdout + r.stderr).splitlines() if "error" in l]
        kinds = collections.Counter(re.sub(r".*: error (\d+): ([^']*).*", r"\1 \2", e) for e in errs)
        print("compile: exit %d in %.0f s; %d error lines: %s" % (r.returncode, time.time() - t, len(errs),
                                                                  dict(kinds.most_common(6))))
    asm = prg[:-4] + ".asm"
    if not os.path.exists(asm):
        asm = prg[:-4] + ".error.asm"
    if not os.path.exists(asm):
        sys.exit("no listing")
    mp = asm[:-4] + ".map"
    bad, n, bank_of = check(asm, mp)
    banks = collections.Counter(b for b in bank_of.values() if b is not None)
    print("listing %s: %d functions, %d in %d banks, %d resident; %d calls; %d cross a bank "
          "without a trampoline" % (os.path.basename(asm), len(bank_of), sum(banks.values()), len(banks),
                                    sum(1 for b in bank_of.values() if b is None), n, len(bad)))
    for x in bad[:20]:
        print("  %s (bank %s) -> %s (bank %s)" % x)
    zbad, top = check_listing.check(asm, check_listing.ZP_END)
    print("zero page and branches (check_listing.py): highest temporary %s, %d problem%s" % (
        "$%02x (%s)" % top if top else "none", len(zbad), "" if len(zbad) == 1 else "s"))
    for x in zbad[:20]:
        print("  " + x)
    if os.path.exists(mp) and os.path.exists(asm[:-4] + ".int"):
        ibad, switching, icalls, ptr, taken = check_int(asm[:-4] + ".int", mp, a.linker_stubs)
        print("intermediate code: %d direct calls; %d cross a bank without a trampoline; %d banked "
              "functions store to the bank register; %d calls through pointers from banked code; "
              "%d uses of a banked function's address" % (icalls, len(ibad), len(switching), ptr, len(taken)))
        for x in taken[:10]:
            print("  address of %s taken in %s" % (x[1], x[0]))
        for x in ibad[:20]:
            print("  %s (bank %s) -> %s (bank %s)" % x)
        for x in switching[:10]:
            print("  stores to the bank register: %s" % x)
        bad = bad + ibad + [(x, None, "$de00", None) for x in switching] + [(a, None, b, None) for a, b in taken]
    if os.path.exists(mp):
        per_bank, resident, tramp = sizes(mp)
        if per_bank:
            v = sorted(per_bank.values())
            print("banks: %d used, %d B in all; per bank min %d, median %d, max %d B" % (
                len(v), sum(v), v[0], v[len(v) // 2], v[-1]))
        print("resident code: %d B, of which %d trampolines, %d B (%.1f B each), and %d bank call "
              "stubs, %d B" % (resident, len(tramp), sum(tramp.values()), sum(tramp.values()) / max(1, len(tramp)),
                               len(sizes.stubs), sum(sizes.stubs.values())))
        if sizes.in_window:
            print("resident code inside the bank window $8000-$bfff: %d functions, e.g. %s" % (
                len(sizes.in_window), ", ".join(sizes.in_window[:5])))
        # the glue's stash slots (nhbank.h's NH_STASH_LEN) hold only strings copied out of
        # the bank window, so the largest literal a bank holds has to fit one, NUL and all
        hdr = os.path.join(os.path.dirname(mp), "src", "nhbank.h")
        slot = re.search(r"#define NH_STASH_LEN (\d+)", open(hdr).read()) if os.path.exists(hdr) else None
        if slot:
            lit = longest_literal(mp)
            print("largest literal in a bank: %d B, a stash slot %s B" % (lit, slot.group(1)))
            if lit > int(slot.group(1)):
                print("a literal in a bank is longer than a stash slot (NH_STASH_LEN in bankgen.py's header)")
                bad = bad + [("NH_STASH_LEN", None, "literal of %d B" % lit, None)]
        left = unplaced(mp)
        if left:
            print("left unplaced by the failed link: " + ", ".join(
                "%s %s %d B" % ("banked" if b else "resident", k.lower(), n) for (k, b), n in sorted(left.items())))
    return 1 if bad or zbad else 0


if __name__ == "__main__":
    sys.exit(main())
