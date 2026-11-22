/*	c64heap.c	NetHack 3.4.3 for the Commodore 64 and C128 (Oscar64)	*/
/* NetHack may be freely redistributed.  See license for details. */

/*
 * The far heap (T2.14, ADR-0009 point 7): the level's monsters come from far space 7 and
 * its objects from far space 8 (c64conf.h, NH_FAR_HEAP), each the pages $80-$FF of its
 * space: 32 KB, kept in the REU and reached through the far runtime's page cache.  The host
 * games' near heap peaked at 11-24 KB in C64 bytes (docs/data/heap-peak-2026-11-22.txt),
 * which the resident side has no room for.
 *
 * A block of up to 256 bytes comes from a slab: pages of one 8-byte size class, a freed
 * block of the class first.  No such block crosses a page, so one translation serves all
 * of a monster's or an object's fields (ADR-0009 point 5).  A larger block (a shopkeeper
 * with its bill, 2,378 B; a vault guard, 397 B) takes whole pages from the top of the
 * space: the compiler translates each access to a struct larger than a page by itself.
 * A freed block goes back to its class, or its pages to a list of runs; a page given to a
 * class stays with it.  The free lists are kept in the free blocks themselves, so the near
 * side is these tables alone.
 *
 * The size freed is the size the caller computes from the block (monst.h's and obj.h's
 * macros: the struct, the extension, the name), as allocated.  A name shortened in place
 * (mon.c's newcham(), which drops an endgame player-monster's rank) only returns the block
 * to a smaller class, which then serves smaller requests from it: safe.
 */
#include "hack.h"

#ifdef NH_FAR_HEAP_SPACES
#include "eshk.h"
#include "vault.h"

/* A block larger than a page starts at a page, and the far types inside one keep their
 * entries within pages: a shopkeeper's bill entries (16 bytes from a multiple of 16) and
 * a vault guard's fake corridor (4 bytes from a multiple of 4), both after the monster's
 * struct (eshk.h, vault.h; ADR-0009 point 5).  Oscar64 accepts a negative array size
 * (compat #75), so static_assert. */
static_assert(sizeof (struct bill_x) == 16, "struct bill_x is 16 bytes (T2.14)");
static_assert((offsetof(struct monst_s, mextra) + offsetof(struct eshk_s, bill)) % 16 == 0,
	      "a shopkeeper's bill[] starts at a multiple of 16 in its block (T2.14)");
static_assert(sizeof (struct fakecorridor) == 4, "struct fakecorridor is 4 bytes (T2.14)");
static_assert((offsetof(struct monst_s, mextra) + offsetof(struct egd, fakecorr)) % 4 == 0,
	      "a guard's fakecorr[] starts at a multiple of 4 in its block (T2.14)");

/* a free block's link: its first two bytes, which no page boundary splits (a block starts
 * at a multiple of 8 in its page, or at a page) */
struct nh_hw7 { unsigned w; };
struct nh_hw8 { unsigned w; };
#pragma farspace(7, nh_hw7)
#pragma farspace(8, nh_hw8)

#define NH_HCLASSES	33	/* 8-byte classes up to 256 bytes; class 0 unused */
#define NH_HRUNS	8

struct nh_heap {
	unsigned freel[NH_HCLASSES];	/* each class's first free block (a far address), 0 none */
	unsigned cur[NH_HCLASSES];	/* where the class's current page has room, 0 none */
	unsigned lo, hi;		/* the pages lo..hi-1 are unused: slabs from lo up, large
					   blocks from hi down; both 0 until the first call */
	unsigned char rpage[NH_HRUNS], rcount[NH_HRUNS];	/* freed runs of pages */
	unsigned char nruns;
	unsigned lost;			/* pages of large blocks freed with the run list full */
};

static struct nh_heap nh_heaps[2];	/* space 7, space 8 */

static unsigned
nh_hget(int sp, unsigned a)
{
	return sp ? ((struct nh_hw8 *) a)->w : ((struct nh_hw7 *) a)->w;
}

static void
nh_hput(int sp, unsigned a, unsigned v)
{
	if (sp)
		((struct nh_hw8 *) a)->w = v;
	else
		((struct nh_hw7 *) a)->w = v;
}

/* a far address in space 7 (sp 0) or 8 (sp 1) for n bytes, or 0 */
static unsigned
nh_halloc(int sp, unsigned n)
{
	struct nh_heap *h = &nh_heaps[sp];
	unsigned a, sz, pages;
	int c, i, best;

	if (!h->hi)
		h->lo = 0x80, h->hi = 0x100;
	if (!n)
		n = 1;
	if (n <= 256) {
		c = (int) ((n + 7) >> 3);
		sz = (unsigned) c << 3;
		if ((a = h->freel[c]) != 0) {
			h->freel[c] = nh_hget(sp, a);
			return a;
		}
		if ((a = h->cur[c]) == 0) {
			if (h->lo >= h->hi)
				return 0;
			a = h->lo++ << 8;
		}
		/* room for another block of the class in this page? */
		h->cur[c] = ((a + sz) & 0xff) && ((a + sz) & 0xff) + sz <= 256 ? a + sz : 0;
		return a;
	}
	pages = (n + 255) >> 8;
	/* the smallest freed run that holds it, taken from its start */
	best = -1;
	for (i = 0; i < h->nruns; i++)
		if (h->rcount[i] >= pages && (best < 0 || h->rcount[i] < h->rcount[best]))
			best = i;
	if (best >= 0) {
		a = (unsigned) h->rpage[best] << 8;
		if (h->rcount[best] > pages) {
			h->rpage[best] += (unsigned char) pages;
			h->rcount[best] -= (unsigned char) pages;
		} else {
			h->nruns--;
			h->rpage[best] = h->rpage[h->nruns];
			h->rcount[best] = h->rcount[h->nruns];
		}
		return a;
	}
	if (h->hi - h->lo < pages)
		return 0;
	h->hi -= pages;
	return h->hi << 8;
}

static void
nh_hfree(int sp, unsigned a, unsigned n)
{
	struct nh_heap *h = &nh_heaps[sp];
	unsigned pages;
	int c;

	if (a < 0x8000)
		panic("far heap %d: freeing a near block", sp + 7);
	if (!n)
		n = 1;
	if (n <= 256) {
		c = (int) ((n + 7) >> 3);
		nh_hput(sp, a, h->freel[c]);
		h->freel[c] = a;
		return;
	}
	pages = (n + 255) >> 8;
	if ((a >> 8) == h->hi)
		h->hi += pages;		/* next to the unused pages: give them back */
	else if (h->nruns < NH_HRUNS) {
		h->rpage[h->nruns] = (unsigned char) (a >> 8);
		h->rcount[h->nruns++] = (unsigned char) pages;
	} else
		h->lost += pages;
}

struct monst_s *
nh_monalloc(unsigned n)
{
	unsigned a = nh_halloc(0, n);

	if (!a)
		panic("Monster space full; cannot get %u bytes", n);
	return (struct monst_s *) a;
}

void
nh_monfree(struct monst_s *m, unsigned n)
{
	nh_hfree(0, (unsigned) m, n);
}

struct obj_s *
nh_objalloc(unsigned n)
{
	unsigned a = nh_halloc(1, n);

	if (!a)
		panic("Object space full; cannot get %u bytes", n);
	return (struct obj_s *) a;
}

void
nh_objfree(struct obj_s *o, unsigned n)
{
	nh_hfree(1, (unsigned) o, n);
}

#endif /* NH_FAR_HEAP_SPACES */
