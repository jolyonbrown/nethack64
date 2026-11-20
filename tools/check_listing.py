#!/usr/bin/env python3
"""check_listing.py - look in Oscar64 listings (.asm) for two problems the compiler does not
report itself.

usage: tools/check_listing.py [--zp-end ADDR] LISTING...

1. Zero-page temporaries past the end of Oscar64's area (compat #72, repro r69).  On the C64
   the zero page is Oscar64's up to $8F and the KERNAL's from $90 (oscar64.md, "Zero page
   usage"; docs/ARCHITECTURE.md), and Oscar64 does not check that a function's temporaries
   fit (oscar64.md: "No check for running out of temporary registers").  Past $8F the
   KERNAL's IRQ changes them: STKEY $91, the jiffy clock $A0-$A2 (which Oscar64's emulator
   ticks too), the keyboard and cursor bytes; KERNAL calls use more.  Reported: every
   function with a temporary (an operand `T<n> + <k>`) past --zp-end (default $8F).
2. Branches to no instruction: a relative branch whose target is not the start of an
   instruction in the listing, because its offset was written truncated (compat #73, repro
   r70) or worked out from the wrong instruction sizes (compat #74, r71).

Banked listings (addresses written BB:XXXX) are read bank by bank.  A temporary used only
through an index register (`T1 + 0,x`) counts at its base address, so its last bytes may be
higher.  Prints the highest temporary of each listing (the headroom).  Exit 1 if anything
was found.
"""
import argparse
import re
import sys

FUNC = re.compile(r"^([A-Za-z_][\w@.]*): ;")
# bank (optional), address, three bytes, mnemonic, operand
INS = re.compile(r"^(?:([0-9a-f]{2}):)?([0-9a-f]{4}) : ([0-9a-f]{2}) ([0-9a-f_]{2}) ([0-9a-f_]{2}) "
                 r"([A-Z]{3})\b(.*)$")
TEMP = re.compile(r"\bT\d+ \+ \d+")
BRANCHES = {"BPL", "BMI", "BVC", "BVS", "BCC", "BCS", "BNE", "BEQ"}
ZP_END = 0x8F		# the last byte of Oscar64's temporaries on the C64; the KERNAL's from $90


def check(path, zp_end):
    """(problems, highest temporary as (address, function) or None) for one listing."""
    starts, branches, high, func = set(), [], {}, None
    for line in open(path, errors="replace"):
        m = FUNC.match(line)
        if m:
            func = m.group(1)
            continue
        m = INS.match(line)
        if not m:
            continue
        bank, addr, op, b1, b2, mnem, rest = m.groups()
        bank, addr = bank or "", int(addr, 16)
        starts.add((bank, addr))
        if func and re.search(r"@bankcall\d*$", func):
            continue    # a bank call stub: its bank and function bytes are data, not code
        if mnem in BRANCHES and b1 != "__" and b2 == "__":
            off = int(b1, 16)
            branches.append((bank, addr, addr + 2 + (off - 256 if off >= 128 else off), func))
        elif TEMP.search(rest) and b1 != "__" and b2 == "__" and func:
            high[func] = max(high.get(func, 0), int(b1, 16))
    problems = []
    for f, a in sorted(high.items(), key=lambda kv: -kv[1]):
        if a > zp_end:
            problems.append("%s: temporaries up to $%02x, past $%02x (compat #72)" % (f, a, zp_end))
    for bank, addr, target, f in branches:
        if (bank, target) not in starts:
            problems.append("%s: the branch at %s$%04x goes to $%04x, which is no instruction "
                            "(compat #73, #74)" % (f, bank + ":" if bank else "", addr, target))
    top = max(((a, f) for f, a in high.items()), default=None)
    return problems, top


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--zp-end", type=lambda s: int(s, 0), default=ZP_END,
                    help="the last zero-page address temporaries may use (default 0x8f)")
    ap.add_argument("listings", nargs="+")
    a = ap.parse_args()
    bad = 0
    for path in a.listings:
        problems, top = check(path, a.zp_end)
        print("%s: %s%s" % (path, "highest temporary $%02x (%s)" % top if top else "no temporaries",
                            ", %d problem%s" % (len(problems), "" if len(problems) == 1 else "s")
                            if problems else ", ok"))
        for p in problems:
            print("  " + p)
        bad += bool(problems)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
