/* farspace.c - far data through the compiler's far spaces, paged from the REU (ADR-0009).
 *
 * Needs an Oscar64 with far spaces (#pragma farspace / farsection, the feature branch of
 * T2.12).  `struct node` is a far type of space 1, and `nodes[]` is in a far section of
 * space 1 at $8000-$BFFF: 512 nodes of 32 bytes, 64 pages.  The compiler translates every
 * access through farxl1 (page X to the RAM page in A) or farxo1 (the address in A and X
 * plus the offset in Y to its RAM address), through tlb1[] (0: not in RAM).  On
 * a miss far_fault takes a page of the cache, 16 RAM pages at $6000-$6FFF, by a clock
 * that skips the pages pinned for the compiler's groups of accesses (farpins) and the page
 * translated last (a copy between two far objects translates its
 * source and then its destination), writes the page it evicts back to the REU, and
 * fetches the one asked for.  Space 1's page p lives at REU $01:pp00; the REU starts as
 * zeroes, and the program builds its data through far pointers, so every store and every
 * load is translated and most of them fault.  Near pages map to themselves, so a near
 * object of a far type works through the same pointers.
 *
 * Each check is a bit of spike_result[0], set when it passes; spike_result[1] holds the
 * checks that ran.  spike_result[2..3]: faults and write-backs; [4..5]: cycles for a walk of
 * 8 nodes, of a near type and of the far type with every page in the cache.  tests/spikes/run_farspace.py
 * reads them through VICE's monitor.  The REU's registers are only written (AGENTS.md).
 */
#include <c64/cia.h>
#include <string.h>

#pragma farspace(1, node)

#pragma section(farnodes, 0, , , bss)
#pragma farsection(farnodes, 1)
#pragma region(farr, 0x8000, 0xc000, , , { farnodes })
#pragma region(main, 0x0900, 0x6000, , , { code, data, bss, heap, stack })

#define NNODES	512
#define POOL	0x60		/* the cache: RAM pages $60-$6F */
#define NPOOL	16
#define REUBANK	1			/* space 1's pages: REU bank 1, page p at $pp00 */

struct node
{
	int				v;
	struct node *	next;
	char			tag;
	char			pad[3];
	long			sum;
	int				w[10];
};

#pragma bss(farnodes)
struct node nodes[NNODES];
#pragma bss(bss)

volatile unsigned spike_result[6];
volatile char spike_done;
volatile int sink;

unsigned char tlb1[256];
#pragma align(tlb1, 256)
unsigned char slot_page[NPOOL];
unsigned char clock_hand, farlast, fsave_y, fpage;
/* the pages of the compiler's groups of accesses (one translation for several fields):
   not evicted while they are pinned here */
unsigned char farpins[4];
#pragma runtime(farpins, farpins)
unsigned faults, writebacks;

__asm far_fault;

/* page X of space 1 to its RAM page, in A; Y kept */
__asm farxl1
{
		lda tlb1, x
		beq miss
		sta farlast
		rts
miss:	jmp far_fault
}
#pragma runtime(farxl1, farxl1)

/* the far pointer at zero page address X: its RAM address in ADDR, the page in A too, Y kept
   (the compiler's call for a page when the program has it; ADDR is set after farxl1, since
   a fault may use it) */
__asm farxz1
{
		lda $00, x
		sta __addr + 0
		lda $01, x
		tax
		lda tlb1, x
		beq zmiss
		sta farlast
		sta __addr + 1
		rts
zmiss:	lda __addr + 0
		pha
		jsr far_fault
		sta __addr + 1
		pla
		sta __addr + 0
		lda __addr + 1
		rts
}
#pragma runtime(farxz1, farxz1)

/* the address in A and X plus the offset in Y, translated: RAM address in A and X */
unsigned char xoff, xlo;

__asm farxo1
{
		sty xoff
		clc
		adc xoff
		bcc nc
		inx
nc:		sta xlo
		lda tlb1, x
		beq omiss
		sta farlast
		tax
		lda xlo
		rts
omiss:	jsr far_fault
		tax
		lda xlo
		rts
}
#pragma runtime(farxo1, farxo1)

/* the DMA of one page: A = RAM page, X = REU page, Y = command ($90 stash, $91 fetch) */
__asm far_dma
{
		sta $df03
		stx $df05
		lda #0
		sta $df02
		sta $df04
		sta $df07
		sta $df0a
		lda #REUBANK
		sta $df06
		lda #1
		sta $df08
		sty $df01
		rts
}

__asm far_fault
{
		sty fsave_y
		stx fpage
		inc faults
		bne nf
		inc faults + 1
nf:
next:	ldx clock_hand
		inx
		cpx #NPOOL
		bcc wrap
		ldx #0
wrap:	stx clock_hand
		txa
		clc
		adc #POOL
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
		lda slot_page, x
		beq free
		/* evict: its page leaves the table, and goes back to the REU */
		tay
		lda #0
		sta tlb1, y
		inc writebacks
		bne nw
		inc writebacks + 1
nw:		txa
		pha
		tya
		tax
		pla
		pha
		clc
		adc #POOL
		ldy #$90
		jsr far_dma
		pla
		tax
free:	lda fpage
		sta slot_page, x
		txa
		clc
		adc #POOL
		pha
		ldx fpage
		ldy #$91
		jsr far_dma
		pla
		ldx fpage
		sta tlb1, x
		sta farlast
		ldy fsave_y
		rts
}

unsigned passed, ran;

__noinline void dma(unsigned char ram, unsigned char reupage, unsigned char cmd)
{
	__asm {
		lda ram
		ldx reupage
		ldy cmd
		jsr far_dma
	}
}

__noinline void check(unsigned bit, char ok)
{
	ran |= bit;
	if (ok)
		passed |= bit;
}

/* CIA 2 timer A counting system clock cycles (the KERNAL does not use it) */
__noinline void timer_start(void)
{
	cia2.cra = 0;
	cia2.ta = 0xffff;
	cia2.cra = 0x11;
}

__noinline unsigned timer_stop(void)
{
	cia2.cra = 0;
	return 0xffff - cia2.ta;
}

__noinline long walk(struct node * n)
{
	long s = 0;
	while (n)
	{
		s += n->v;
		n = n->next;
	}
	return s;
}

/* three objects' fields interleaved: each object's group translated once and pinned, while
   the others' translations fault and evict (the page translated last alone would not keep a's
   page when c faults) */
__noinline void mix(struct node * a, struct node * b, struct node * c)
{
	a->sum = (long)a->v + b->v + c->v + a->w[9];
	b->w[0] = a->tag + b->tag + c->tag + a->w[8];
}

__noinline unsigned order(unsigned i)
{
	return (i * 37 + 11) & (NNODES - 1);
}

struct node nearnodes[8];

/* the same layout as a near type, for the timing */
struct nnode
{
	int				v;
	struct nnode *	next;
	char			tag;
	char			pad[3];
	long			sum;
	int				w[10];
};

struct nnode plain[8];

__noinline long nwalk(struct nnode * n)
{
	long s = 0;
	while (n)
	{
		s += n->v;
		n = n->next;
	}
	return s;
}

int main(void)
{
	/* the table: near pages to themselves, the far pages not in RAM */
	for (int i = 0; i < 256; i++)
		tlb1[i] = (i >= 0x80 && i < 0xc0) ? 0 : i;
	/* the REU's first two banks cleared, through the cache's first page */
	memset((char *)(POOL << 8), 0, 256);
	for (unsigned char p = 0x80; p < 0xc0; p++)
		dma(POOL, p, 0x90);
	/* and the far region's RAM made garbage: a missed translation reads it */
	memset((char *)0x8000, 0xee, 0x4000);

	/* a list through every node, in a scrambled order */
	long expect = 0;
	unsigned k = order(0);
	struct node * head = &nodes[k];
	for (unsigned i = 0; i < NNODES; i++)
	{
		unsigned nk = order(i + 1);
		nodes[k].v = (int)(k * 3);
		nodes[k].tag = (char)k;
		nodes[k].w[9] = (int)k;
		nodes[k].next = i + 1 < NNODES ? &nodes[nk] : nullptr;
		expect += k * 3;
		k = nk;
	}
	check(0x0001, walk(head) == expect);

	/* every node changed in array order, then the list again */
	for (unsigned i = 0; i < NNODES; i++)
		nodes[i].v++;
	check(0x0002, walk(head) == expect + NNODES);

	/* far to far copies between pages far apart, under eviction */
	char ok = 1;
	for (unsigned i = 0; i < 64; i++)
	{
		unsigned a = (i * 8) & (NNODES - 1), b = (NNODES - 1 - i * 8) & (NNODES - 1);
		struct node * pa = &nodes[a], * pb = &nodes[b];
		*pb = *pa;
		if (pb->v != (int)(a * 3 + 1) || pb->tag != (char)a || pb->w[9] != (int)a)
			ok = 0;
	}
	check(0x0004, ok);

	/* the stored fields survive evictions: every node read back */
	ok = 1;
	for (unsigned i = 0; i < NNODES; i++)
	{
		unsigned src = i;
		/* nodes written by the copies above hold their source's fields */
		for (unsigned j = 0; j < 64; j++)
			if (i == ((NNODES - 1 - j * 8) & (NNODES - 1)))
				src = (j * 8) & (NNODES - 1);
		if (nodes[i].tag != (char)src || nodes[i].w[9] != (int)src)
			ok = 0;
	}
	check(0x0008, ok);

	/* near objects of the far type, through the same code */
	for (char i = 0; i < 8; i++)
	{
		nearnodes[i].v = i;
		nearnodes[i].next = i < 7 ? &nearnodes[i + 1] : nullptr;
	}
	check(0x0010, walk(nearnodes) == 28);

	/* far and near mixed in one list */
	nearnodes[7].next = &nodes[order(NNODES - 1)];
	check(0x0020, walk(nearnodes) == 28 + (long)order(NNODES - 1) * 3 + 1);
	nearnodes[7].next = nullptr;

	/* groups under eviction: a node and one far away, for every node */
	for (unsigned i = 0; i < NNODES; i++)
		mix(&nodes[i], &nodes[(i + 200) & (NNODES - 1)], &nodes[(i + 333) & (NNODES - 1)]);
	ok = 1;
	for (unsigned i = 0; i < NNODES; i++)
	{
		unsigned j = (i + 200) & (NNODES - 1), k = (i + 333) & (NNODES - 1);
		if (nodes[i].sum != (long)nodes[i].v + nodes[j].v + nodes[k].v + nodes[i].w[9])
			ok = 0;
	}
	check(0x0200, ok);

	check(0x0040, faults > NNODES / 8 && writebacks > 0);
	/* the far region's own RAM was never written */
	/* (below $A000: above it a .prg reads BASIC's ROM) */
	check(0x0080, *(volatile char *)0x8000 == (char)0xee && *(volatile char *)0x9fff == (char)0xee);

	/* timing: a walk of 8 nodes, near, and far with their pages in the cache */
	for (char i = 0; i < 8; i++)
	{
		nodes[i * 8].v = i;
		nodes[i * 8].next = i < 7 ? &nodes[i * 8 + 8] : nullptr;
	}
	for (char i = 0; i < 8; i++)
	{
		plain[i].v = i;
		plain[i].next = i < 7 ? &plain[i + 1] : nullptr;
	}
	walk(&nodes[0]);
	__asm { sei }
	unsigned f0 = faults;
	timer_start();
	sink = (int)nwalk(plain);
	spike_result[4] = timer_stop();
	timer_start();
	sink = (int)walk(&nodes[0]);
	spike_result[5] = timer_stop();
	__asm { cli }
	check(0x0100, faults == f0);

	spike_result[2] = faults;
	spike_result[3] = writebacks;
	spike_result[0] = passed;
	spike_result[1] = ran;
	spike_done = 1;
	for (;;)
		;
	return 0;
}
