/* fardata.c - what a far-data access through the REU costs (docs/RAM-PLAN.md).
 *
 * PRG build, VICE with an REU of 512 KB or more, interrupts off while measuring.
 *
 * The far space is the REU's first 512 KB in 256-byte pages.  A far pointer is three
 * bytes in zero page (fo offset, fpg page, fbk bank).  far_xlat turns it into a near
 * pointer np, also in zero page, so the access itself is an ordinary (np),y: a hit in a
 * translation table of 256 entries indexed by the page byte (tlb_bank[] holds the bank
 * whose page of that number is in RAM, tlb_ram[] its RAM page); otherwise far_fault()
 * finds the page in the page table (8 banks x 256 pages) and, if it is not in RAM, takes
 * the next RAM page of the cache (writing its old page back to the REU if it was
 * written) and fetches the page with one DMA.  The cache is up to 64 RAM pages at
 * $4000-$7FFF; the tables are at $C000-$CAFF; near copies of the test data at $8000-$BFFF
 * (RAM with BASIC banked out).
 *
 * Each workload runs on the near copy and on the far copy, cold (every page faults) and
 * warm.  The list keeps objects inside a page, as a far allocator would, so one
 * translation serves all of a node's fields; the table and the grid have records across
 * page boundaries and translate for every access.  Results (cycles, 32-bit, CIA 2 timers
 * A and B cascaded) are in spike_result[], checks in spike_ok; tests/spikes/run_fardata.py
 * reads them through VICE's monitor.  The REU registers are only written (AGENTS.md).
 */
#include <c64/cia.h>
#include <c64/reu.h>

#pragma region( main, 0x0880, 0x4000, , , { code, data, bss, heap, stack } )

#define PTAB		0xc000		/* page table: [bank << 8 | page] = RAM page, 0 if none */
#define TLB_BANK	0xc800		/* for each page number: the bank whose page is mapped, $ff none */
#define TLB_RAM		0xc900		/* for each page number: that page's RAM page */
#define RAMDIRTY	0xca00		/* for each RAM page: written since fetched */
#define POOL_PAGE	0x40		/* the cache: RAM pages $40-$7f */
#define NEAR		0x8000		/* the near copies */

#define ptab		((unsigned char *)PTAB)
#define tlb_bank	((unsigned char *)TLB_BANK)
#define tlb_ram		((unsigned char *)TLB_RAM)
#define ramdirty	((unsigned char *)RAMDIRTY)

volatile unsigned long spike_result[24];
volatile unsigned spike_ok;
volatile unsigned spike_count[4];
volatile char spike_done;
volatile unsigned sink;

__zeropage unsigned char fo, fpg, fbk;		/* the far pointer */
__zeropage unsigned char * np;				/* the near pointer it translates to */
/* volatile: Oscar64 does not take an inline assembler block as writing the variables it
   stores to, and used a copy of inp made before the block, still the far pointer, after it */
__zeropage unsigned char * volatile inp;	/* in place: a far pointer's offset and page ... */
__zeropage unsigned char ibk;				/* ... and bank; translating replaces the page */

unsigned char pool_size, clock_hand;
unsigned char pool_bank[64], pool_page[64];
unsigned faults, writebacks;

void far_fault(void);

/* Hit path: 3 + 4 + 3 + 2 + 4 + 3 + 3 + 3 cycles, the jump and the call.  A C function
 * whose assembler names the far and near pointers, so that the compiler knows it reads one
 * and writes the other: a bare `jsr` to an assembler routine from inline assembler does
 * not tell it, and it moved the next pointer's stores past the call. */
__noinline void xlat(void)
{
	__asm
	{
	retry:
		ldx fpg
		lda TLB_BANK, x
		cmp fbk
		bne miss
		lda TLB_RAM, x
		sta np + 1
		lda fo
		sta np
		jmp done
	miss:
		jsr far_fault
		jmp retry
	done:
	}
}

/* In place, inlined: 3 + 4 + 3 + 2 + 4 + 3 cycles on a hit.  The far pointer's page byte
 * becomes the RAM page, so inp is then the near pointer itself. */
__forceinline void xlat2(void)
{
	__asm
	{
	retry:
		ldx inp + 1
		lda TLB_BANK, x
		cmp ibk
		bne miss
		lda TLB_RAM, x
		sta inp + 1
		jmp done
	miss:
		lda inp + 1
		sta fpg
		lda ibk
		sta fbk
		jsr far_fault
		jmp retry
	done:
	}
}

/* Called from assembler, so the compiler does not know who calls it: its state is static,
 * not in a frame that the static-stack layout could share with a caller's. */
static unsigned char ff_b, ff_p, ff_rp, ff_s, ff_ob, ff_op;
static unsigned char * ff_row;

void far_fault(void)
{
#define b	ff_b
#define p	ff_p
#define rp	ff_rp
#define s	ff_s
#define ob	ff_ob
#define op	ff_op
#define row	ff_row
	b = fbk;
	p = fpg;
	row = ptab + ((unsigned)b << 8);
	rp = row[p];
	if (!rp)
	{
		s = clock_hand;
		clock_hand = s + 1 == pool_size ? 0 : s + 1;
		rp = POOL_PAGE + s;
		if (pool_bank[s] != 0xff)
		{
			ob = pool_bank[s];
			op = pool_page[s];
			if (ramdirty[rp])
			{
				reu_store(((unsigned long)ob << 16) | ((unsigned)op << 8), (char *)((unsigned)rp << 8), 256);
				ramdirty[rp] = 0;
				writebacks++;
			}
			ptab[((unsigned)ob << 8) | op] = 0;
			if (tlb_bank[op] == ob)
				tlb_bank[op] = 0xff;
		}
		reu_load(((unsigned long)b << 16) | ((unsigned)p << 8), (char *)((unsigned)rp << 8), 256);
		pool_bank[s] = b;
		pool_page[s] = p;
		row[p] = rp;
		faults++;
	}
	tlb_bank[p] = b;
	tlb_ram[p] = rp;
#undef b
#undef p
#undef rp
#undef s
#undef ob
#undef op
#undef row
}

/* empty the cache (write nothing back: each test reloads its data) */
__noinline void far_reset(unsigned char size)
{
	for (unsigned i = 0; i < 0x800; i++)
		ptab[i] = 0;
	for (unsigned i = 0; i < 256; i++)
	{
		tlb_bank[i] = 0xff;
		ramdirty[i] = 0;
	}
	for (unsigned char i = 0; i < 64; i++)
		pool_bank[i] = 0xff;
	pool_size = size;
	clock_hand = 0;
	faults = writebacks = 0;
}

/* CIA 2 timer A counts cycles, timer B counts A's underflows: 32 bits */
__noinline void timer_start(void)
{
	cia2.cra = 0;
	cia2.crb = 0;
	cia2.ta = 0xffff;
	cia2.tb = 0xffff;
	cia2.crb = 0x51;			/* force load, start, count timer A underflows */
	cia2.cra = 0x11;			/* force load, start, continuous, count phi2 */
}

__noinline unsigned long timer_stop(void)
{
	cia2.cra = 0;
	cia2.crb = 0;
	unsigned a = cia2.ta, b = cia2.tb;
	return ((unsigned long)(0xffff - b) << 16) + (0xffff - a);
}

/* ---- the list: 200 nodes of 48 B, five to a page, linked in a scattered order ---- */

#define NODES	200
#define NODE	48

static unsigned node_off(unsigned i)
{
	return (i / 5) * 256 + (i % 5) * NODE;
}

static unsigned list_sum;

__noinline void make_list(void)
{
	unsigned char * near = (unsigned char *)NEAR;
	list_sum = 0;
	for (unsigned k = 0; k < NODES; k++)
	{
		unsigned i = (k * 37) % NODES, j = ((k + 1) * 37) % NODES;
		unsigned char * n = near + node_off(i);
		unsigned v = 1000 + i * 3;
		n[0] = v & 0xff;
		n[1] = v >> 8;
		list_sum += v;
		if (k + 1 < NODES)
		{
			/* near: the next node's address; the far copy's next pointer is three
			   bytes at 5..7: offset, page, bank 1 */
			*(unsigned char **)(n + 2) = near + node_off(j);
			n[5] = node_off(j) & 0xff;
			n[6] = node_off(j) >> 8;
			n[7] = 1;
		}
		else
		{
			*(unsigned char **)(n + 2) = 0;
			n[7] = 0xff;
		}
	}
	reu_store(0x10000ul, (char *)NEAR, 40 * 256);
}

__noinline unsigned walk_near(unsigned char * n)
{
	unsigned s = 0;
	while (n)
	{
		s += n[0] | (n[1] << 8);
		n = *(unsigned char **)(n + 2);
	}
	return s;
}

__noinline unsigned walk_far(unsigned char o, unsigned char p)
{
	unsigned s = 0;
	fo = o;
	fpg = p;
	fbk = 1;
	while (fbk != 0xff)
	{
		xlat();
		s += np[0] | (np[1] << 8);
		fo = np[5];
		fpg = np[6];
		fbk = np[7];
	}
	return s;
}

__noinline unsigned walk_far2(unsigned char o, unsigned char p)
{
	unsigned s = 0;
	inp = (unsigned char *)(((unsigned)p << 8) | o);
	ibk = 1;
	while (ibk != 0xff)
	{
		xlat2();
		s += inp[0] | (inp[1] << 8);
		unsigned char no = inp[5], npg = inp[6], nb = inp[7];
		inp = (unsigned char *)(((unsigned)npg << 8) | no);
		ibk = nb;
	}
	return s;
}

/* ---- the table: 252 records of 55 B (mons[] has 382), three fields each ---- */

#define RECS	252		/* 55 pages contiguous, 63 in the paged layout: both fit 64 */
#define REC		55

static unsigned table_sum;

__noinline void make_table(void)
{
	unsigned char * t = (unsigned char *)NEAR;
	for (unsigned i = 0; i < RECS * REC; i++)
		t[i] = (i * 7 + 3) & 0xff;
	table_sum = 0;
	for (unsigned i = 0; i < RECS; i++)
		table_sum += t[i * REC + 1] + t[i * REC + 7] + t[i * REC + 40];
	reu_store(0x20000ul, (char *)NEAR, RECS * REC);
	/* bank 4: the same records four to a page, none across a page boundary, as a far
	   allocator would place them */
	for (unsigned i = 0; i < RECS; i++)
		reu_store(0x40000ul + ((unsigned long)(i / 4) << 8) + (i % 4) * REC, (char *)NEAR + i * REC, REC);
}

__noinline unsigned scan_near(void)
{
	unsigned s = 0;
	unsigned char * e = (unsigned char *)NEAR;
	for (unsigned i = 0; i < RECS; i++, e += REC)
		s += e[1] + e[7] + e[40];
	return s;
}

__noinline unsigned scan_far(void)
{
	unsigned s = 0, a = 0;
	fbk = 2;
	for (unsigned i = 0; i < RECS; i++, a += REC)
	{
		unsigned f;
		f = a + 1;  fo = f & 0xff; fpg = f >> 8; xlat(); s += np[0];
		f = a + 7;  fo = f & 0xff; fpg = f >> 8; xlat(); s += np[0];
		f = a + 40; fo = f & 0xff; fpg = f >> 8; xlat(); s += np[0];
	}
	return s;
}

__noinline unsigned scan_far2(void)
{
	unsigned s = 0, a = 0;
	for (unsigned i = 0; i < RECS; i++, a += REC)
	{
		inp = (unsigned char *)(a + 1);  ibk = 2; xlat2(); s += inp[0];
		inp = (unsigned char *)(a + 7);  ibk = 2; xlat2(); s += inp[0];
		inp = (unsigned char *)(a + 40); ibk = 2; xlat2(); s += inp[0];
	}
	return s;
}

/* one translation a record, in the paged layout */
__noinline unsigned scan_far3(void)
{
	unsigned s = 0;
	for (unsigned i = 0; i < RECS; i++)
	{
		inp = (unsigned char *)(((i >> 2) << 8) | (i & 3) * REC);
		ibk = 4;
		xlat2();
		s += inp[1] + inp[7] + inp[40];
	}
	return s;
}

/* ---- the grid: 80 x 21 cells of 6 B (levl[][]), a sweep and random accesses ---- */

#define CELLS	(80 * 21)
#define CELL	6

static unsigned grid_sum;

__noinline void make_grid(void)
{
	unsigned char * g = (unsigned char *)NEAR;
	grid_sum = 0;
	for (unsigned i = 0; i < CELLS; i++)
	{
		g[i * CELL] = (i * 13) & 0xff;
		g[i * CELL + 1] = 0;
		grid_sum += g[i * CELL];
	}
	reu_store(0x30000ul, (char *)NEAR, CELLS * CELL);
}

/* read each cell's first byte and write its second (cells start at even offsets, so a
   cell's first two bytes never straddle a page) */
__noinline unsigned sweep_near(void)
{
	unsigned s = 0;
	unsigned char * c = (unsigned char *)NEAR;
	for (unsigned i = 0; i < CELLS; i++, c += CELL)
	{
		s += c[0];
		c[1] = (unsigned char)i;
	}
	return s;
}

__noinline unsigned sweep_far(void)
{
	unsigned s = 0, a = 0;
	fbk = 3;
	for (unsigned i = 0; i < CELLS; i++, a += CELL)
	{
		fo = a & 0xff;
		fpg = a >> 8;
		xlat();
		s += np[0];
		np[1] = (unsigned char)i;
		ramdirty[(unsigned)np >> 8] = 1;
	}
	return s;
}

__noinline unsigned sweep_far2(void)
{
	unsigned s = 0, a = 0;
	for (unsigned i = 0; i < CELLS; i++, a += CELL)
	{
		inp = (unsigned char *)a;
		ibk = 3;
		xlat2();
		s += inp[0];
		inp[1] = (unsigned char)i;
		ramdirty[(unsigned)inp >> 8] = 1;
	}
	return s;
}

#define PICKS	2000

__noinline unsigned pick_near(void)
{
	unsigned s = 0, r = 12345;
	unsigned char * g = (unsigned char *)NEAR;
	for (unsigned k = 0; k < PICKS; k++)
	{
		r = r * 109 + 89;
		unsigned i = (r >> 4) % CELLS;
		s += g[i * CELL];
	}
	return s;
}

__noinline unsigned pick_far(void)
{
	unsigned s = 0, r = 12345;
	fbk = 3;
	for (unsigned k = 0; k < PICKS; k++)
	{
		r = r * 109 + 89;
		unsigned a = ((r >> 4) % CELLS) * CELL;
		fo = a & 0xff;
		fpg = a >> 8;
		xlat();
		s += np[0];
	}
	return s;
}

/* ---- the primitives ---- */

#define LOOPS	1000

__noinline unsigned long time_xlat(void)
{
	fo = 0; fpg = 0; fbk = 1;
	xlat();						/* now resident: every later call hits */
	timer_start();
	for (unsigned k = 0; k < LOOPS; k++)
		xlat();
	return timer_stop();
}

__noinline unsigned long time_xlat2(void)
{
	inp = 0;
	ibk = 1;
	xlat2();
	timer_start();
	for (unsigned k = 0; k < LOOPS; k++)
	{
		inp = 0;				/* each translation starts from the far pointer */
		xlat2();
	}
	return timer_stop();
}

__noinline unsigned long time_reload(void)
{
	timer_start();
	for (unsigned k = 0; k < LOOPS; k++)
	{
		inp = 0;
		__asm { nop }
	}
	return timer_stop();
}

__noinline unsigned long time_empty(void)
{
	timer_start();
	for (unsigned k = 0; k < LOOPS; k++)
		__asm { nop }
	return timer_stop();
}

/* 16 faults on pages not in RAM, clean evictions */
__noinline unsigned long time_faults(void)
{
	fo = 0; fbk = 1;
	timer_start();
	for (unsigned char p = 0; p < 16; p++)
	{
		fpg = p;
		xlat();
	}
	return timer_stop();
}

int main(void)
{
	*(volatile char *)1 = 0x36;			/* BASIC out: RAM at $A000-$BFFF */
	__asm { sei }

	unsigned ok = 0;

	make_list();
	far_reset(64);
	timer_start(); sink = walk_near((unsigned char *)NEAR + node_off(0)); spike_result[0] = timer_stop();
	ok |= sink == list_sum ? 0x0001 : 0;
	timer_start(); sink = walk_far(node_off(0) & 0xff, node_off(0) >> 8); spike_result[1] = timer_stop();
	ok |= sink == list_sum ? 0x0002 : 0;
	timer_start(); sink = walk_far(node_off(0) & 0xff, node_off(0) >> 8); spike_result[2] = timer_stop();
	ok |= sink == list_sum ? 0x0004 : 0;
	spike_count[0] = faults;
	timer_start(); sink = walk_far2(node_off(0) & 0xff, node_off(0) >> 8); spike_result[15] = timer_stop();
	ok |= sink == list_sum ? 0x1000 : 0;

	make_table();
	far_reset(64);
	timer_start(); sink = scan_near(); spike_result[3] = timer_stop();
	ok |= sink == table_sum ? 0x0008 : 0;
	timer_start(); sink = scan_far(); spike_result[4] = timer_stop();
	ok |= sink == table_sum ? 0x0010 : 0;
	timer_start(); sink = scan_far(); spike_result[5] = timer_stop();
	ok |= sink == table_sum ? 0x0020 : 0;
	timer_start(); sink = scan_far2(); spike_result[16] = timer_stop();
	ok |= sink == table_sum ? 0x2000 : 0;
	sink = scan_far3();
	timer_start(); sink = scan_far3(); spike_result[17] = timer_stop();
	ok |= sink == table_sum ? 0x4000 : 0;
	far_reset(32);
	sink = scan_far();
	timer_start(); sink = scan_far(); spike_result[14] = timer_stop();	/* 55 pages through 32 */
	ok |= sink == table_sum ? 0x0040 : 0;
	spike_count[1] = faults;

	make_grid();
	far_reset(64);
	timer_start(); sink = sweep_near(); spike_result[6] = timer_stop();
	ok |= sink == grid_sum ? 0x0080 : 0;
	make_grid();
	timer_start(); sink = sweep_far(); spike_result[7] = timer_stop();
	ok |= sink == grid_sum ? 0x0100 : 0;
	timer_start(); sink = sweep_far(); spike_result[8] = timer_stop();
	ok |= sink == grid_sum ? 0x0200 : 0;
	timer_start(); sink = sweep_far2(); spike_result[18] = timer_stop();
	ok |= sink == grid_sum ? 0x8000 : 0;
	timer_start(); sink = pick_near(); spike_result[9] = timer_stop();
	timer_start(); sink = pick_far(); spike_result[10] = timer_stop();
	ok |= sink == pick_near() ? 0x0400 : 0;

	/* the far grid's writes survive eviction: force every page out and read back */
	far_reset(8);
	{
		unsigned char good = 1;
		unsigned a = 0;
		fbk = 3;
		for (unsigned i = 0; i < CELLS; i++, a += CELL)
		{
			fo = a & 0xff; fpg = a >> 8; xlat();
			np[1] = (unsigned char)(i + 1);
			ramdirty[(unsigned)np >> 8] = 1;
		}
		a = 0;
		for (unsigned i = 0; i < CELLS; i++, a += CELL)
		{
			fo = a & 0xff; fpg = a >> 8; xlat();
			if (np[1] != (unsigned char)(i + 1))
				good = 0;
		}
		ok |= good && writebacks > 0 ? 0x0800 : 0;
		spike_count[2] = writebacks;
	}

	far_reset(64);
	spike_result[11] = time_xlat();
	spike_result[12] = time_empty();
	spike_result[19] = time_xlat2();
	spike_result[20] = time_reload();
	far_reset(64);
	spike_result[13] = time_faults();
	spike_count[3] = faults;

	spike_ok = ok;
	__asm { cli }
	spike_done = 1;
	for (;;)
		;
	return 0;
}
