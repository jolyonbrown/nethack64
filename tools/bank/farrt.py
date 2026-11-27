#!/usr/bin/env python3
"""farrt.py - write the far runtime: the translation routines the far-spaces compiler calls
(farxlN, farxoN, farxzN for each far space, farxzc for the library's string routines), the
page cache they share, the fault handler that pages from the REU, and nh_farcopy() for the
far names (ADR-0009, ADR-0010; T2.13).

usage: tools/bank/farrt.py --out FILE.c [--target c64|c128] [--frames N] [--no-xz]
                           (--space N:LO:HI:REUBANK [--space ...] [--chars N] | --from-headers DIR...)

--from-headers reads the spaces from the headers' own pragmas, as the whole-game build has
them (c64conf.h, permonst.h, objclass.h, rm.h): `#pragma farsection(sec, n)` names a space's
section, `#pragma region(name, lo, hi, , bank, { ... })` the pages and bank of every region in
that section's bank (a space's names are a plain section beside its data), and
`#pragma farchars(n)` the character space.

Each --space is a far space N whose pages LO to HI (hex) are far, kept in REU bank REUBANK
(hex: REU address REUBANK:pp00 for page pp; tools/bank/c128_images.py puts the space's
section there, bank b at REU offset (b - 64) * 16 KB from $8000). A page outside LO-HI is
near and comes back as it is: a near object of a far type, or for the character space
(--chars N) any byte pointer below it.

The cache is --frames pages of RAM (default 16), aligned to a page. A fault takes a frame
by a clock that skips the page translated last (a copy between two far objects translates
one then the other) and the pages pinned for the compiler's groups (farpins), writes the
page it evicts back to the REU (no page knows whether it was written) and fetches the one
asked for. Faults and write-backs are counted (nh_faults, nh_writebacks). On a C128 the
REU's registers need the I/O in, so the handler switches it in around the DMA and puts
the MMU back as it was. The REU's registers are only written (AGENTS.md).
"""
import argparse
import os
import re
import sys


def from_headers(dirs):
    """[(n, lo, hi, reubank)] and the character space's number, from the headers"""
    farsec, regions, chars = {}, [], 0
    for d in dirs:
        for root, _, names in os.walk(d):
            for name in sorted(names):
                if not name.endswith(".h"):
                    continue
                text = open(os.path.join(root, name), encoding="latin-1").read()
                for m in re.finditer(r"#pragma\s+farsection\s*\(\s*(\w+)\s*,\s*(\d+)\s*\)", text):
                    farsec[m.group(1)] = int(m.group(2))
                for m in re.finditer(r"#pragma\s+region\s*\(\s*(\w+)\s*,\s*(0x[0-9a-fA-F]+|\d+)\s*,\s*"
                                     r"(0x[0-9a-fA-F]+|\d+)\s*,\s*,\s*(\d+)\s*,\s*\{([^}]*)\}", text):
                    regions.append((int(m.group(2), 0), int(m.group(3), 0), int(m.group(4)),
                                    [x.strip() for x in m.group(5).split(",") if x.strip()]))
                m = re.search(r"#pragma\s+farchars\s*\(\s*(\d+)\s*\)", text)
                if m:
                    chars = int(m.group(1))
    spaces = {}
    for sec, n in farsec.items():
        banks = {b for lo, hi, b, secs in regions if sec in secs}
        if len(banks) != 1:
            sys.exit("far section %s: in %d banks" % (sec, len(banks)))
        bank = banks.pop()
        off = (bank - 64) * 0x4000 - 0x8000
        if bank < 64 or off < 0 or off & 0xffff:
            sys.exit("far section %s: bank %d is not at a 64 KB boundary of the REU less $8000 "
                     "((bank - 64) mod 4 must be 2)" % (sec, bank))
        pages = [(lo >> 8, (hi - 1) >> 8) for lo, hi, b, _ in regions if b == bank]
        lo, hi = min(p[0] for p in pages), max(p[1] for p in pages)
        if n in spaces and spaces[n] != (lo, hi, off >> 16):
            sys.exit("far space %d: two banks" % n)
        spaces[n] = (lo, hi, off >> 16)
    return sorted((n, lo, hi, b) for n, (lo, hi, b) in spaces.items()), chars


def space_code(n, lo, hi, off, chars, xz=False):
    """the three translation routines of space n, pages lo..hi far, its table at
    nh_tlb + off (one entry a page from $80)"""
    test = ["\t\tcpx #$%02x" % lo, "\t\tbcc near%d" % n]
    if hi < 0xff:
        test += ["\t\tcpx #$%02x" % (hi + 1), "\t\tbcs near%d" % n]
    ztest = ["\t\tcmp #$%02x" % lo, "\t\tbcc znear%d" % n]
    if hi < 0xff:
        ztest += ["\t\tcmp #$%02x" % (hi + 1), "\t\tbcs znear%d" % n]
    otest = [l.replace("near%d" % n, "onear%d" % n) for l in test]
    tlb = "nh_tlb + %d - $80" % off
    what = "the character space" if chars else "far space %d" % n
    return """
/* %(what)s: page X to its RAM page in A, Y kept */
__asm farxl%(n)d
{
%(test)s
		lda %(tlb)s, x
		beq miss%(n)d
		sta farlast
		rts
miss%(n)d:	lda #%(n)d
		jmp nh_far_fault
near%(n)d:	txa
		rts
}
#pragma runtime(farxl%(n)d, farxl%(n)d)

/* %(what)s: the address in A and X plus the offset in Y to its RAM address in A and X */
__asm farxo%(n)d
{
		sty nh_xoff
		clc
		adc nh_xoff
		bcc nc%(n)d
		inx
nc%(n)d:
%(otest)s
		sta nh_xlo
		lda %(tlb)s, x
		beq omiss%(n)d
		sta farlast
		tax
		lda nh_xlo
		rts
omiss%(n)d:	lda #%(n)d
		jsr nh_far_fault
		tax
		lda nh_xlo
onear%(n)d:	rts
}
#pragma runtime(farxo%(n)d, farxo%(n)d)

/* %(what)s: the pointer at zero page address X to its RAM address in ADDR, the page in A
   too, Y kept: the compiler's five-byte call for a page (the far-spaces fork's commit 13
   fixed a loop pass that lost the pointer's carry with it), and the library's string
   routines' through farxzc */
__asm nh_farxz%(n)d
{
		lda $00, x
		sta __addr + 0
		lda $01, x
%(ztest)s
		tax
		lda %(tlb)s, x
		beq zmiss%(n)d
		sta farlast
		sta __addr + 1
		rts
zmiss%(n)d:	lda __addr + 0
		pha
		lda #%(n)d
		jsr nh_far_fault
		sta __addr + 1
		pla
		sta __addr + 0
		lda __addr + 1
		rts
znear%(n)d:	sta __addr + 1
		rts
}
%(xzrt)s
""" % dict(n=n, test="\n".join(test), otest="\n".join(otest), ztest="\n".join(ztest), tlb=tlb, what=what,
                xzrt="#pragma runtime(farxz%d, nh_farxz%d)" % (n, n) if xz else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--target", choices=("c64", "c128"), default="c128")
    ap.add_argument("--frames", type=int, default=16)
    ap.add_argument("--space", action="append", default=[], metavar="N:LO:HI:REUBANK")
    ap.add_argument("--from-headers", nargs="+", metavar="DIR")
    ap.add_argument("--code-section", metavar="NAME",
                    help="put the runtime's code in this section (bankgen.py --io-out's nhio, below "
                         "$8000: the fault handler switches the I/O in)")
    ap.add_argument("--frames-section", metavar="NAME",
                    help="put the cache's frames and the page tables in this bss section (bankgen.py's "
                         "nh_c128_low)")
    ap.add_argument("--drop", type=int, action="append", default=[], metavar="N",
                    help="leave space N out (--from-headers reads the pragmas without the "
                         "preprocessor, so a space whose #if is off is found too)")
    ap.add_argument("--chars", type=int, default=0, help="the character space's number")
    ap.add_argument("--no-xz", action="store_true",
                    help="keep farxzN from the compiler, which then calls farxlN (11 bytes, not 5): "
                         "for a compiler before the far-spaces fork's commit 13")
    a = ap.parse_args()
    spaces = []
    for s in a.space:
        n, lo, hi, bank = s.split(":")
        spaces.append((int(n), int(lo, 16), int(hi, 16), int(bank, 16)))
    if a.from_headers:
        spaces, chars = from_headers(a.from_headers)
        spaces = [s for s in spaces if s[0] not in a.drop]
        a.chars = a.chars or (chars if chars not in a.drop else 0)
        print("far spaces: " + ", ".join("%d pages $%02x-$%02x REU bank $%02x" % s for s in spaces) +
              ("; characters: %d" % a.chars if a.chars else ""))
    if not spaces:
        sys.exit("no far spaces (--space or --from-headers)")
    spaces.sort()
    if any(lo < 0x80 for _, lo, _, _ in spaces):
        sys.exit("far pages start at $80 (the tables hold pages $80-$FF)")
    if not 1 <= a.frames <= 64:
        sys.exit("--frames 1 to 64")
    if a.chars and a.chars not in [s[0] for s in spaces]:
        sys.exit("--chars names no --space")
    top = max(n for n, _, _, _ in spaces)
    offs = {n: 128 * i for i, (n, _, _, _) in enumerate(spaces)}
    # space n's table less $80 (its first entry is page $80's) is at nh_tlb + offs[n] - 128;
    # nh_tlb is aligned to a page, so that is a low byte and a page offset from nh_tlb's
    tlb_lo = ", ".join("0x%02x" % ((offs[n] - 128) & 0xff) if n in offs else "0" for n in range(top + 1))
    tlb_hi = ", ".join("0x%02x" % (((offs[n] - 128) >> 8) & 0xff) if n in offs else "0" for n in range(top + 1))
    reu = ", ".join("0x%02x" % next((b for m, _, _, b in spaces if m == n), 0) for n in range(top + 1))
    io_in = "\t\tlda $ff00\n\t\tpha\n\t\tand #$fe\n\t\tsta $ff00\n" if a.target == "c128" else ""
    io_out = "\t\tpla\n\t\tsta $ff00\n" if a.target == "c128" else ""
    # the C128 starts the DMA at 1 MHz and puts its clock back after (src/hal/sys128.c's
    # sys128_speed(): a 1750 clone's guide says the C128 must be at 1 MHz for a DMA)
    dma = ("\t\tlda $d030\n\t\tpha\n\t\tand #$fe\n\t\tsta $d030\n\t\tlda nh_fy\n\t\tsta $df01\n"
           "\t\tpla\n\t\tsta $d030\n") if a.target == "c128" else "\t\tlda nh_fy\n\t\tsta $df01\n"
    out = ["""/* nh_farrt.c - the far runtime, written by tools/bank/farrt.py (%(args)s).
 * Spaces %(spaces)s; %(frames)d frames of cache; %(target)s. */

/* one entry a far page from $80 for each space: its RAM page, 0 when it is not in RAM;
   with the frames in their own section (the C128's low RAM), there too */
%(fsec)sunsigned char nh_tlb[%(ntlb)d];
#pragma align(nh_tlb, 256)
/* the cache's frames, and the space (0: free) and page each holds */
char nh_frames[%(frames)d * 256];
#pragma align(nh_frames, 256)
%(fsecend)s
unsigned char nh_frame_space[%(frames)d], nh_frame_page[%(frames)d];
unsigned char nh_clock, farlast, nh_fy, nh_fx, nh_fpage, nh_fspace, nh_xoff, nh_xlo;
/* volatile: only the assembler writes them, so C would read their first values */
volatile unsigned nh_faults, nh_writebacks;
volatile unsigned char nh_rpage;

/* the pages of the compiler's groups of accesses: not evicted while pinned here */
unsigned char farpins[4];
#pragma runtime(farpins, farpins)

/* before the first far access: no page in RAM, every frame free (the page tables may be in a
   section that the start-up code does not clear, the C128's low RAM) */
void nh_far_init(void)
{
	unsigned i;

	for (i = 0; i < sizeof(nh_tlb); i++)
		nh_tlb[i] = 0;
	for (i = 0; i < %(frames)d; i++)
		nh_frame_space[i] = 0;
	nh_clock = 0;
}

/* by space number: its table less $80, as a low byte and a page offset from nh_tlb's
   page, and its REU bank */
static const unsigned char nh_tlb_lo[%(nsp)d] = { %(tlb_lo)s };
static const unsigned char nh_tlb_hi[%(nsp)d] = { %(tlb_hi)s };
static const unsigned char nh_space_reu[%(nsp)d] = { %(reu)s };

/* one page between RAM page A and REU bank Y, page X; nh_fy holds the command ($90 stash,
   $91 fetch) */
__asm nh_far_dma
{
		sta $df03
		stx $df05
		sty $df06
		lda #0
		sta $df02
		sta $df04
		sta $df07
		sta $df0a
		lda #1
		sta $df08
%(dma)s		rts
}

/* page X of space A is not in RAM: fetch it into a frame and return the frame's RAM page
   in A, Y kept */
__asm nh_far_fault
{
		sta nh_fspace
		stx nh_fpage
		tya
		pha
		inc nh_faults
		bne nf
		inc nh_faults + 1
nf:
%(io_in)snext:	ldx nh_clock
		inx
		cpx #%(frames)d
		bcc wrap
		ldx #0
wrap:	stx nh_clock
		txa
		clc
		adc #>nh_frames
		cmp farlast
		beq next
		cmp farpins
		beq next
		cmp farpins + 1
		beq next
		cmp farpins + 2
		beq next
		cmp farpins + 3
		beq next
		stx nh_fx
		ldy nh_frame_space, x
		beq free
		/* evict: the page leaves its table and goes back to the REU */
		lda nh_tlb_lo, y
		sta clr + 1
		lda #>nh_tlb
		clc
		adc nh_tlb_hi, y
		sta clr + 2
		lda nh_space_reu, y
		pha
		ldy nh_frame_page, x
		lda #0
clr:	sta $ffff, y
		inc nh_writebacks
		bne nw
		inc nh_writebacks + 1
nw:		lda #$90
		sta nh_fy
		ldx nh_fx
		lda nh_frame_page, x
		tax
		pla
		tay
		lda nh_fx
		clc
		adc #>nh_frames
		jsr nh_far_dma
		ldx nh_fx
free:	lda nh_fspace
		sta nh_frame_space, x
		lda nh_fpage
		sta nh_frame_page, x
		lda #$91
		sta nh_fy
		ldy nh_fspace
		lda nh_tlb_lo, y
		sta set + 1
		lda #>nh_tlb
		clc
		adc nh_tlb_hi, y
		sta set + 2
		lda nh_space_reu, y
		tay
		ldx nh_fpage
		lda nh_fx
		clc
		adc #>nh_frames
		jsr nh_far_dma
		lda nh_fx
		clc
		adc #>nh_frames
		ldx nh_fpage
set:	sta $ffff, x
		sta farlast
		tax
%(io_out)s		pla
		tay
		txa
		rts
}
""" % dict(args=" ".join(sys.argv[1:]), spaces=", ".join(str(s[0]) for s in spaces), frames=a.frames,
           target=a.target, ntlb=128 * len(spaces), nsp=top + 1, tlb_lo=tlb_lo, tlb_hi=tlb_hi, reu=reu,
           io_in=io_in, io_out=io_out, dma=dma,
           fsec="#pragma bss( %s )\n" % a.frames_section if a.frames_section else "",
           fsecend="#pragma bss( bss )\n" if a.frames_section else "")]
    if a.code_section:
        out.insert(0, "#pragma code( %s )\n" % a.code_section)
    for n, lo, hi, _ in spaces:
        out.append(space_code(n, lo, hi, offs[n], n == a.chars, not a.no_xz))
    out.append("""
/* the far translation of page X of space A (any space): its RAM page in A, Y kept */
__asm nh_far_page
{
		sta nh_fspace
		tay
		lda nh_tlb_lo, y
		sta get + 1
		lda #>nh_tlb
		clc
		adc nh_tlb_hi, y
		sta get + 2
get:	lda $ffff, x
		beq gmiss
		sta farlast
		rts
gmiss:	lda nh_fspace
		jmp nh_far_fault
}

#pragma farchars(off)
/* n bytes at address p of far space s into near d, a page at a time (the far names:
   bankgen.py's nh_name_into(); plain addresses, so no byte test) */
void nh_farcopy(char *d, const char *p, unsigned n, unsigned char s)
{
	while (n)
	{
		unsigned char pg = (unsigned)p >> 8, lo = (unsigned)p & 0xff;
		unsigned k = 256 - lo;
		/* the RAM page through a volatile: the compiler does not see an __asm block's
		   store to a local, and keeps the local's value from before it */
		__asm
		{
			lda s
			ldx pg
			jsr nh_far_page
			sta nh_rpage
		}
		const char *r = (const char *)(((unsigned)nh_rpage << 8) | lo);
		if (k > n)
			k = n;
		n -= k;
		p += k;
		while (k--)
			*d++ = *r++;
	}
}
#pragma farchars(on)
""")
    if a.chars:
        out.append("""
/* the library's assembler string routines translate through this (-dOSCAR_FARCHARS) */
void farxzc(void)
{
	__asm { jmp nh_farxz%d }
}
""" % a.chars)
    if a.code_section:
        out.append("\n#pragma code( code )\n")
    open(a.out, "w").write("".join(out))


if __name__ == "__main__":
    main()
