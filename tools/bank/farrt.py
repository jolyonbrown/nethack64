#!/usr/bin/env python3
"""farrt.py - write the far runtime: the translation routines the far-spaces compiler calls
(farxlN, farxoN, farxzN for each far space, farxzc for the library's string routines), the
page cache they share, the fault handler that pages from the REU, and nh_farcopy() for the
far names (ADR-0009, ADR-0010; T2.13).

usage: tools/bank/farrt.py --out FILE.c [--target c64|c128] [--frames N]
                           --space N:LO:HI:REUBANK [--space ...] [--chars N]

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
import sys


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
   too, Y kept. Not given to the compiler (--xz does): with it, a pointer stepped in a loop
   loses the carry into its high byte (the far-spaces fork, 2026-11-21: "INC P0" alone before
   the call; docs/OSCAR64-COMPAT.md), so the compiler uses farxl%(n)d and farxo%(n)d; the
   library's string routines call it through farxzc */
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
    ap.add_argument("--space", action="append", required=True, metavar="N:LO:HI:REUBANK")
    ap.add_argument("--chars", type=int, default=0, help="the character space's number")
    ap.add_argument("--xz", action="store_true",
                    help="give the compiler farxzN too (shorter calls; see nh_farxzN's comment)")
    a = ap.parse_args()
    spaces = []
    for s in a.space:
        n, lo, hi, bank = s.split(":")
        spaces.append((int(n), int(lo, 16), int(hi, 16), int(bank, 16)))
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
    out = ["""/* nh_farrt.c - the far runtime, written by tools/bank/farrt.py (%(args)s).
 * Spaces %(spaces)s; %(frames)d frames of cache; %(target)s. */

/* one entry a far page from $80 for each space: its RAM page, 0 when it is not in RAM */
unsigned char nh_tlb[%(ntlb)d];
#pragma align(nh_tlb, 256)
/* the cache's frames, and the space (0: free) and page each holds */
char nh_frames[%(frames)d * 256];
#pragma align(nh_frames, 256)
unsigned char nh_frame_space[%(frames)d], nh_frame_page[%(frames)d];
unsigned char nh_clock, farlast, nh_fy, nh_fx, nh_fpage, nh_fspace, nh_xoff, nh_xlo;
/* volatile: only the assembler writes them, so C would read their first values */
volatile unsigned nh_faults, nh_writebacks;
volatile unsigned char nh_rpage;

/* the pages of the compiler's groups of accesses: not evicted while pinned here */
unsigned char farpins[4];
#pragma runtime(farpins, farpins)

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
		lda nh_fy
		sta $df01
		rts
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
           io_in=io_in, io_out=io_out)]
    for n, lo, hi, _ in spaces:
        out.append(space_code(n, lo, hi, offs[n], n == a.chars, a.xz))
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
    open(a.out, "w").write("".join(out))


if __name__ == "__main__":
    main()
