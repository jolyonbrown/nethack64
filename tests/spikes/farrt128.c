/* farrt128.c - spike: the far runtime of tools/bank/farrt.py on a C128 (T2.13, ADR-0009,
 * ADR-0010), with the far-spaces compiler's far characters (fork commit 11).
 *
 * Far space 1 is `struct node`, 512 nodes of 32 bytes in a far section at $8000-$BFFF
 * (64 pages, bank 70: REU bank 1); far space 6 is the character space, its section at
 * $C100-$FBFF (bank 66: REU bank 0), holding this program's string literals (#pragma
 * strings) and a writable buffer. The runtime (nh_farrt.c, written by run_farrt128.py) has
 * 4 frames of cache, so most accesses fault and evict. The literals start in the REU (the
 * program's overlay files, tools/bank/c128_images.py), so a literal is read only through
 * the runtime; RAM at $C100-$FBFF holds this program's code and garbage.
 *
 * spike_result[0]: the checks passed (a bit each, run_farrt128.py names them), [1] those run;
 * [2..3]: faults and write-backs; [4..5]: CIA 2 cycles at 1 MHz for 40 bytes of a far
 * literal read in a loop with its page in the cache, and of a near copy (both through
 * byte pointers, so the near one pays the test). spike_dbg[0]: the library check's steps. */
#include <c64/cia.h>
#include <string.h>

#pragma region( main, 0x1d00, 0x8000, , , { code, data, bss, heap, stack } )

#pragma overlay( farrt128_ov66, 66 )
#pragma overlay( farrt128_ov70, 70 )

#pragma farspace(1, node)
#pragma section(farnodes, 0, , , bss)
#pragma farsection(farnodes, 1)
#pragma region(farnodes, 0x8000, 0xc000, , 70, { farnodes })

#pragma section(farchars, 0)
#pragma farsection(farchars, 6)
#pragma region(farchars, 0xc100, 0xfc00, , 66, { farchars })
#pragma farchars(6)
#pragma strings(code, farchars)

/* garbage over the space's addresses in bank 0: code lives there in the game */
#pragma section( hicode, 0 )
#pragma region( hicode, 0xc100, 0xd000, , , { hicode } )

#include "nh_farrt.c"

#define NNODES	512

struct node
{
	int				v;
	struct node *	next;
	char			tag;
	char			name[9];
	long			sum;
	int				w[7];
};

#pragma bss(farnodes)
struct node nodes[NNODES];
#pragma bss(bss)

#pragma bss(farchars)
char fbuf[64];
#pragma bss(bss)

const char * const words[] = {
	"zero, a far literal in the character space", "one, a far literal in the character space",
	"two, a far literal in the character space", "three, a far literal in the character space",
	"four, a far literal in the character space", "five, a far literal in the character space",
	"six, a far literal in the character space", "seven, a far literal in the character space",
	"eight, a far literal in the character space", "nine, a far literal in the character space",
	"ten, a far literal in the character space", "eleven, a far literal in the character space",
	"twelve, a far literal in the character space", "thirteen, a far literal in the character space",
	"fourteen, a far literal in the character space", "fifteen, a far literal in the character space",
	"sixteen, a far literal in the character space", "seventeen, a far literal in the character space",
	"eighteen, a far literal in the character space", "nineteen, a far literal in the character space",
	"twenty, a far literal in the character space", "twenty-one, a far literal in the character space",
	"twenty-two, a far literal in the character space", "twenty-three, a far literal in the space",
};

/* the same words, near (an array's initialiser is data, not a literal) */
char nearwords[24][52] = {
	"zero, a far literal in the character space", "one, a far literal in the character space",
	"two, a far literal in the character space", "three, a far literal in the character space",
	"four, a far literal in the character space", "five, a far literal in the character space",
	"six, a far literal in the character space", "seven, a far literal in the character space",
	"eight, a far literal in the character space", "nine, a far literal in the character space",
	"ten, a far literal in the character space", "eleven, a far literal in the character space",
	"twelve, a far literal in the character space", "thirteen, a far literal in the character space",
	"fourteen, a far literal in the character space", "fifteen, a far literal in the character space",
	"sixteen, a far literal in the character space", "seventeen, a far literal in the character space",
	"eighteen, a far literal in the character space", "nineteen, a far literal in the character space",
	"twenty, a far literal in the character space", "twenty-one, a far literal in the character space",
	"twenty-two, a far literal in the character space", "twenty-three, a far literal in the space",
};

volatile unsigned spike_result[6];
volatile int spike_dbg[1];
volatile char spike_done;
unsigned passed, ran;
char nearbuf[64];

__noinline void check(unsigned bit, char ok)
{
	ran |= bit;
	if (ok)
		passed |= bit;
}

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

__noinline int mylen(const char * s)
{
	int n = 0;
	while (s[n])
		n++;
	return n;
}

__noinline int same(const char * a, const char * b)
{
	while (*a && *a == *b)
		a++, b++;
	return *a == *b;
}

__noinline unsigned order(unsigned i)
{
	return (i * 37 + 11) & (NNODES - 1);
}

__noinline long walk(struct node * n)
{
	long s = 0;
	while (n)
	{
		s += n->v + n->name[2];
		n = n->next;
	}
	return s;
}

__noinline unsigned sum40(const char * p)
{
	unsigned s = 0;
	for (char i = 0; i < 40; i++)
		s += p[i];
	return s;
}

#pragma code( hicode )
__noinline void hicode_filler(void)
{
	__asm
	{
		nop
		nop
		nop
		nop
	}
}
#pragma code( code )

int main(void)
{
	__asm { sei }
	*(volatile char *)0xff00 = 0x3e;
	cia2.cra = 0;

	/* 1: every literal reads as its near copy, in order and back again, through 4 frames */
	char ok = 1;
	for (char i = 0; i < 24; i++)
		ok &= same(words[i], nearwords[i]);
	for (char i = 24; i-- > 0;)
		ok &= mylen(words[i]) == mylen(nearwords[i]);
	check(1, ok);

	/* 2: a list through every node of space 1, with a far literal's bytes in each */
	long expect = 0;
	unsigned k = order(0);
	struct node * head = &nodes[k];
	for (unsigned i = 0; i < NNODES; i++)
	{
		unsigned nk = order(i + 1);
		nodes[k].v = (int)(k * 3);
		const char * w = words[k % 24];
		for (char j = 0; j < 8; j++)
			nodes[k].name[j] = w[j];
		nodes[k].name[8] = 0;
		nodes[k].next = i + 1 < NNODES ? &nodes[nk] : nullptr;
		expect += k * 3 + nearwords[k % 24][2];
		k = nk;
	}
	check(2, walk(head) == expect);

	/* 3: the library's assembler routines on far strings, while the cache churns */
	unsigned lb = 0;
	strcpy(nearbuf, words[5]);
	if (same(nearbuf, nearwords[5])) lb |= 1;
	if (!strcmp(words[7], nearwords[7])) lb |= 2;
	if (strcmp(words[1], words[2]) < 0) lb |= 4;
	strcpy(fbuf, words[9]);
	walk(head);
	if (!strcmp(fbuf, nearwords[9])) lb |= 8;
	memcpy(nearbuf, words[3], 10);
	memset(fbuf, 'q', 4);
	walk(head);
	if (nearbuf[0] == 't' && nearbuf[9] == 'f') lb |= 16;
	if (fbuf[3] == 'q' && fbuf[4] == nearwords[9][4]) lb |= 32;
	spike_dbg[0] = lb;			/* which of the six steps passed */
	check(4, lb == 63);

	/* 4: nh_farcopy() from space 1 across a page (node 7 ends past $80FF) */
	char tmp[40], nm[9];
	nh_farcopy(tmp, (const char *)(unsigned)&nodes[7], 40, 1);
	for (char j = 0; j < 9; j++)
		nm[j] = nodes[7].name[j];		/* typed accesses: a far struct's array is not a char * */
	check(8, *(int *)tmp == nodes[7].v && tmp[32] == (char)nodes[8].v && same(tmp + 5, nm));

	/* 5: faults and write-backs happened, and the MMU is as it was */
	check(16, nh_faults > 100 && nh_writebacks > 50 && *(volatile char *)0xff00 == 0x3e);

	/* 6: a far store with the MMU at $3F (no I/O): the fault switches the I/O in for the
	 * DMA and back out */
	*(volatile char *)0xff00 = 0x3f;
	walk(head);
	strcpy(fbuf, words[11]);
	char cr = *(volatile char *)0xff00;
	*(volatile char *)0xff00 = 0x3e;
	check(32, cr == 0x3f && same(fbuf, nearwords[11]));

	/* timings: 40 bytes of a far literal with its page in the cache, and near */
	sum40(words[0]);
	timer_start();
	unsigned sf = sum40(words[0]);
	spike_result[4] = timer_stop();
	timer_start();
	unsigned sn = sum40(nearwords[0]);
	spike_result[5] = timer_stop();
	check(64, sf == sn);

	spike_result[0] = passed;
	spike_result[1] = ran;
	spike_result[2] = nh_faults;
	spike_result[3] = nh_writebacks;
	spike_done = 1;
	for (;;)
		;
	return 0;
}
