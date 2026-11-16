/* nh_trace.c - which pages of the C64's data each turn of the host game touches
 * (docs/RAM-PLAN.md, T2.3), for tools/host-build.sh --trace.
 *
 * clang reports every load and store of the game's code
 * (-fsanitize-coverage=edge,trace-loads,trace-stores), and malloc, calloc, realloc and free
 * are wrapped (-Wl,--wrap=...), so each access can be put to the C64 object it would touch:
 *
 * - the stack is left out (locals stay in RAM in a far-data model);
 * - a named global is matched by name to the whole-game C64 map, which gives its C64 size
 *   and kind (tools/measure/trace/layout.py writes the table this reads); an offset into
 *   it is scaled to the C64 size, which keeps array indexes about right;
 * - an access to the executable's read-only data outside a named object is a string
 *   literal, scaled into the C64 build's 37.7 KB of resident strings;
 * - a heap block gets a C64 address of its own when it is allocated, its size scaled by
 *   the C64/host ratio of struct obj or struct monst when it is one of those (monsters are
 *   tested first: a monster's host size is within an object's with a name), from a slab
 *   allocator: blocks up to 256 B in pages of one size class (8-byte classes), freed blocks
 *   reused first, so monsters lie with monsters and objects with objects;
 * - anything else (libc, the tty window port's data) is counted but has no C64 page.
 *
 * Each kind of data has page-aligned regions of its own in the C64 far space, so a page
 * has one kind.  Every access to a C64 page also goes through simulated page caches of
 * 32, 64, 96 and 128 RAM pages with three replacement policies: first in first out (like
 * tests/spikes/fardata.c's), CLOCK (second chance: a reference bit set on each access) and
 * least recently used.  At every store to `moves` (++moves in moveloop) one line is
 * written: the turn, the pages touched in it by kind, the accesses by kind, the pages
 * touched over the last ten turns, and each cache's faults.  At exit, NH_TRACE_OUT.objects
 * lists each global's accesses and the turns it was touched in.  NH_TRACE_NEAR names
 * globals (one a line) to keep near: their accesses are counted as near and reach no page.
 * NH_TRACE_FAR names the kinds that are far, comma-separated (e.g. "mons,objects,heap", the
 * first set of ADR-0009); every other kind is counted as near.  Without it all are far.
 * Environment: NH_TRACE_LAYOUT (the table), NH_TRACE_OUT (the output); without them the
 * callbacks do nothing.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

enum { K_OTHER, K_LEVEL, K_VISION, K_DISPLAY, K_MONS, K_OBJECTS, K_GLOBALS, K_STRINGS, K_HEAP, K_NEAR, NKINDS };
static const char *kname[NKINDS] = { "other", "level", "vision", "display", "mons", "objects",
                                     "globals", "strings", "heap", "near" };

struct obj_ent { uintptr_t addr; uint32_t size, c64addr, c64size; uint8_t kind, hcat; unsigned long tot;
                 int lastturn, nturns; char name[48]; };

static struct obj_ent *ents, *heap;
static int nents, nheap, aheap;
static int state;                      /* 0 not started, 1 tracing, -1 off */
static FILE *out;
static uintptr_t stack_lo, stack_hi, ro_lo, ro_hi, moves_addr;
static uint32_t str_base, str_size, heap_next, obj_host, monst_host;
static unsigned long acc[NKINDS];
static int far_kind[NKINDS];           /* NH_TRACE_FAR: the kinds that are far */
#define PAGES 8192                     /* 2 MB of C64 far space */
static uint8_t page_kind[PAGES];
static uint8_t turnbits[PAGES / 8], ring[10][PAGES / 8];
static int ringpos, turns;
static const struct obj_ent *last;    /* the entry the previous access hit */

#define NSIZE 4
#define NPOL 3                         /* FIFO, CLOCK, LRU */
static const int simsize[NSIZE] = { 32, 64, 96, 128 };
static const char *polname[NPOL] = { "fifo", "clock", "lru" };
struct sim {
	int size, count, hand;
	uint16_t page[128];
	uint8_t ref[128];
	uint32_t stamp[128];
	int16_t where[PAGES];
	unsigned long faults;
};
static struct sim sims[NPOL][NSIZE];
static uint32_t lru_now;
static unsigned long heap_tot[3];      /* struct obj, struct monst, other blocks */
#define NCLASS 33                      /* 8-byte size classes up to 256 B */
#define MAXFREE 8192
static uint32_t cls_next[NCLASS];      /* next byte in the class's current page, 0 none */
static uint32_t cls_free[NCLASS][MAXFREE];
static int cls_nfree[NCLASS];

/* weak: util/'s programs link some of src/'s objects without decl.o */
extern long moves __attribute__((weak));

extern void *__real_malloc(size_t);
extern void *__real_calloc(size_t, size_t);
extern void *__real_realloc(void *, size_t);
extern void __real_free(void *);

static int cmp_ent(const void *a, const void *b)
{
	uintptr_t x = ((const struct obj_ent *)a)->addr, y = ((const struct obj_ent *)b)->addr;
	return x < y ? -1 : x > y;
}

static pid_t owner;                    /* a forked child must not flush our buffers */

static void finish(void)
{
	const char *op = getenv("NH_TRACE_OUT");
	char path[600];
	FILE *f;
	if (getpid() != owner)
		return;
	if (out)
		fclose(out);
	out = NULL;
	state = -1;
	if (!op)
		return;
	snprintf(path, sizeof path, "%s.objects", op);
	if (!(f = fopen(path, "w")))
		return;
	fprintf(f, "# kind name host_size c64_size accesses turns_touched (of %d)\n", turns);
	for (int i = 0; i < nents; i++)
		if (ents[i].tot)
			fprintf(f, "%s %s %u %u %lu %d\n", kname[ents[i].kind], ents[i].name, ents[i].size,
			        ents[i].c64size, ents[i].tot, ents[i].nturns);
	fprintf(f, "heap struct_obj - 48 %lu -\nheap struct_monst - 80 %lu -\nheap other - - %lu -\n",
	        heap_tot[0], heap_tot[1], heap_tot[2]);
	fclose(f);
}

static void start(void)
{
	const char *lp = getenv("NH_TRACE_LAYOUT"), *op = getenv("NH_TRACE_OUT");
	FILE *f;
	char line[512], name[256];
	unsigned long long base_nm = 0;
	int cap = 0;

	state = -1;
	if (!lp || !op || !(f = fopen(lp, "r")))
		return;
	/* header: "moves <nm address>", "rodata <nm addr> <size>", "strings <c64 base> <size>",
	   "heap <c64 base>", "obj <host size>", "monst <host size>"; then entries
	   "<nm addr> <host size> <c64 addr> <c64 size> <kind> <name>" */
	while (fgets(line, sizeof line, f))
	{
		unsigned long long a, s, ca, cs;
		unsigned k;
		if (sscanf(line, "moves %llx", &a) == 1)
			base_nm = a;
		else if (sscanf(line, "rodata %llx %llx", &a, &s) == 2)
			ro_lo = a, ro_hi = a + s;
		else if (sscanf(line, "strings %llx %llx", &a, &s) == 2)
			str_base = a, str_size = s;
		else if (sscanf(line, "heap %llx", &a) == 1)
			heap_next = a;
		else if (sscanf(line, "obj %llu", &a) == 1)
			obj_host = a;
		else if (sscanf(line, "monst %llu", &a) == 1)
			monst_host = a;
		else if (sscanf(line, "%llx %llu %llx %llu %u %255s", &a, &s, &ca, &cs, &k, name) == 6)
		{
			if (nents == cap)
				ents = realloc(ents, (cap = cap ? cap * 2 : 1024) * sizeof *ents);
			memset(&ents[nents], 0, sizeof *ents);
			ents[nents].addr = a;
			ents[nents].size = s;
			ents[nents].c64addr = ca;
			ents[nents].c64size = cs;
			ents[nents].kind = k;
			ents[nents].lastturn = -1;
			strncpy(ents[nents].name, name, sizeof ents[nents].name - 1);
			nents++;
		}
	}
	fclose(f);
	{
		const char *np = getenv("NH_TRACE_NEAR");
		FILE *nf = np ? fopen(np, "r") : NULL;
		while (nf && fgets(line, sizeof line, nf))
		{
			if (sscanf(line, "%255s", name) != 1)
				continue;
			for (int i = 0; i < nents; i++)
				if (!strcmp(ents[i].name, name) && ents[i].kind != K_OTHER)
					ents[i].kind = K_NEAR;
		}
		if (nf)
			fclose(nf);
	}
	{
		const char *fp = getenv("NH_TRACE_FAR");
		for (int k = 0; k < NKINDS; k++)
		{
			size_t n = strlen(kname[k]);
			const char *q = fp;
			far_kind[k] = !fp;
			while (q && *q)
			{
				if (!strncmp(q, kname[k], n) && (q[n] == ',' || !q[n]))
					far_kind[k] = 1;
				q = strchr(q, ',');
				q = q ? q + 1 : NULL;
			}
		}
		far_kind[K_OTHER] = far_kind[K_NEAR] = 0;
		for (int i = 0; i < nents; i++)
			if (ents[i].kind != K_OTHER && !far_kind[ents[i].kind])
				ents[i].kind = K_NEAR;
	}
	for (int pl = 0; pl < NPOL; pl++)
		for (int z = 0; z < NSIZE; z++)
		{
			sims[pl][z].size = simsize[z];
			memset(sims[pl][z].where, 0xff, sizeof sims[pl][z].where);
		}
	{
		/* PIE: the load base from a symbol both sides know */
		uintptr_t base = (uintptr_t)&moves - base_nm;
		for (int i = 0; i < nents; i++)
			ents[i].addr += base;
		ro_lo += base;
		ro_hi += base;
		moves_addr = (uintptr_t)&moves;
	}
	qsort(ents, nents, sizeof *ents, cmp_ent);
	for (int i = 0; i < nents; i++)
		if (ents[i].kind != K_OTHER && ents[i].kind != K_NEAR)
			for (uint32_t p = ents[i].c64addr >> 8; p <= (ents[i].c64addr + ents[i].c64size - 1) >> 8 && p < PAGES; p++)
				page_kind[p] = ents[i].kind;
	for (uint32_t p = str_base >> 8; p <= (str_base + str_size - 1) >> 8 && p < PAGES; p++)
		page_kind[p] = K_STRINGS;
	/* the stack: this frame and up to 8 MB below the highest stack address used */
	{
		FILE *m = fopen("/proc/self/maps", "r");
		while (m && fgets(line, sizeof line, m))
		{
			unsigned long long lo, hi;
			if (strstr(line, "[stack]") && sscanf(line, "%llx-%llx", &lo, &hi) == 2)
				stack_lo = lo > (8u << 20) ? hi - (8u << 20) : 0, stack_hi = hi;
		}
		if (m)
			fclose(m);
	}
	if (!(out = fopen(op, "w")))
		return;
	fprintf(out, "# turn pages:");
	for (int k = 1; k < NKINDS; k++)
		fprintf(out, " %s", kname[k]);
	fprintf(out, " | accesses:");
	for (int k = 0; k < NKINDS; k++)
		fprintf(out, " %s", kname[k]);
	fprintf(out, " | pages_last_10_turns | faults:");
	for (int pl = 0; pl < NPOL; pl++)
		for (int z = 0; z < NSIZE; z++)
			fprintf(out, " %s%d", polname[pl], simsize[z]);
	fprintf(out, "\n");
	owner = getpid();
	atexit(finish);
	state = 1;
}

static void sim_access(struct sim *m, int pol, uint32_t p)
{
	int slot = m->where[p];
	if (slot >= 0)
	{
		m->ref[slot] = 1;
		m->stamp[slot] = lru_now;
		return;
	}
	m->faults++;
	if (m->count < m->size)
		slot = m->count++;
	else
	{
		if (pol == 0)
			slot = m->hand, m->hand = (m->hand + 1) % m->size;
		else if (pol == 1)
		{
			while (m->ref[m->hand])
				m->ref[m->hand] = 0, m->hand = (m->hand + 1) % m->size;
			slot = m->hand, m->hand = (m->hand + 1) % m->size;
		}
		else
		{
			slot = 0;
			for (int i = 1; i < m->size; i++)
				if (m->stamp[i] < m->stamp[slot])
					slot = i;
		}
		m->where[m->page[slot]] = -1;
	}
	m->page[slot] = p;
	m->where[p] = slot;
	m->ref[slot] = 1;
	m->stamp[slot] = lru_now;
}

static void mark(uint32_t c64)
{
	uint32_t p = c64 >> 8;
	if (p >= PAGES)
		return;
	turnbits[p >> 3] |= 1 << (p & 7);
	lru_now++;
	for (int pl = 0; pl < NPOL; pl++)
		for (int z = 0; z < NSIZE; z++)
			sim_access(&sims[pl][z], pl, p);
}

static void end_turn(void)
{
	unsigned pages[NKINDS] = { 0 }, window = 0;
	memcpy(ring[ringpos], turnbits, sizeof turnbits);
	ringpos = (ringpos + 1) % 10;
	for (int p = 0; p < PAGES; p++)
	{
		if (turnbits[p >> 3] & (1 << (p & 7)))
			pages[page_kind[p]]++;
		for (int r = 0; r < 10; r++)
			if (ring[r][p >> 3] & (1 << (p & 7)))
			{
				window++;
				break;
			}
	}
	fprintf(out, "%d", ++turns);
	for (int k = 1; k < NKINDS; k++)
		fprintf(out, " %u", pages[k]);
	fprintf(out, " |");
	for (int k = 0; k < NKINDS; k++)
		fprintf(out, " %lu", acc[k]);
	fprintf(out, " | %u |", window);
	for (int pl = 0; pl < NPOL; pl++)
		for (int z = 0; z < NSIZE; z++)
		{
			fprintf(out, " %lu", sims[pl][z].faults);
			sims[pl][z].faults = 0;
		}
	fprintf(out, "\n");
	memset(turnbits, 0, sizeof turnbits);
	memset(acc, 0, sizeof acc);
}

static const struct obj_ent *find(const struct obj_ent *v, int n, uintptr_t a)
{
	int lo = 0, hi = n - 1;
	while (lo <= hi)
	{
		int mid = (lo + hi) / 2;
		if (a < v[mid].addr)
			hi = mid - 1;
		else if (a >= v[mid].addr + v[mid].size)
			lo = mid + 1;
		else
			return &v[mid];
	}
	return NULL;
}

static void trace_access(uintptr_t a, int store)
{
	const struct obj_ent *e;

	if (state <= 0)
	{
		if (state < 0)
			return;
		start();
		if (state <= 0)
			return;
	}
	if (getpid() != owner)
		return;
	if (store && a == moves_addr)
		end_turn();
	if (a >= stack_lo && a < stack_hi)
		return;
	if (last && a >= last->addr && a < last->addr + last->size)
		e = last;
	else if ((e = find(ents, nents, a)) || (e = find(heap, nheap, a)))
		last = e;
	if (e)
	{
		acc[e->kind]++;
		if (e->kind == K_HEAP)
			heap_tot[e->hcat]++;
		else
		{
			struct obj_ent *w = (struct obj_ent *)e;
			w->tot++;
			if (w->lastturn != turns)
				w->lastturn = turns, w->nturns++;
		}
		if (e->kind != K_OTHER && e->kind != K_NEAR)
			mark(e->c64addr + (uint32_t)((uint64_t)(a - e->addr) * e->c64size / e->size));
		return;
	}
	if (a >= ro_lo && a < ro_hi)
	{
		if (!far_kind[K_STRINGS])
		{
			acc[K_NEAR]++;
			return;
		}
		acc[K_STRINGS]++;
		mark(str_base + (uint32_t)((uint64_t)(a - ro_lo) * str_size / (ro_hi - ro_lo)));
		return;
	}
	acc[K_OTHER]++;
}

#define LOAD(n)  void __sanitizer_cov_load##n(void *p)  { trace_access((uintptr_t)p, 0); }
#define STORE(n) void __sanitizer_cov_store##n(void *p) { trace_access((uintptr_t)p, 1); }
LOAD(1) LOAD(2) LOAD(4) LOAD(8) LOAD(16)
STORE(1) STORE(2) STORE(4) STORE(8) STORE(16)

/* ---- the heap ---- */

static void heap_add(void *p, size_t n)
{
	uint32_t c64, at;
	uint8_t hcat;
	if (state == 0 && &moves)
		start();
	if (!p || state < 0)
		return;
	last = NULL;
	/* the C64 size: struct monst and struct obj (and their extras) by their own ratio,
	   anything else at about half (pointers, ints and longs halve) */
	if (monst_host && n >= monst_host && n < monst_host + 96)
		c64 = 80 + (n - monst_host), hcat = 1;
	else if (obj_host && n >= obj_host && n < obj_host + 40)
		c64 = 48 + (n - obj_host), hcat = 0;
	else
		c64 = n / 2 ? n / 2 : 1, hcat = 2;
	if (c64 <= 256)
	{
		/* a slab: pages of one 8-byte size class, freed blocks first */
		int c = (c64 + 7) / 8;
		uint32_t sz = c * 8;
		if (cls_nfree[c])
			at = cls_free[c][--cls_nfree[c]];
		else
		{
			if (!cls_next[c] || (cls_next[c] & 255) + sz > 256)
			{
				heap_next = (heap_next + 255) & ~255u;
				cls_next[c] = heap_next;
				heap_next += 256;
			}
			at = cls_next[c];
			cls_next[c] += sz;
		}
	}
	else
	{
		heap_next = (heap_next + 255) & ~255u;
		at = heap_next;
		heap_next += c64;
	}
	if (nheap == aheap)
		heap = __real_realloc(heap, (aheap = aheap ? aheap * 2 : 1024) * sizeof *heap);
	{
		/* insert in address order */
		int i = nheap;
		while (i > 0 && heap[i - 1].addr > (uintptr_t)p)
		{
			heap[i] = heap[i - 1];
			i--;
		}
		heap[i].addr = (uintptr_t)p;
		heap[i].size = n ? n : 1;
		heap[i].c64addr = at;
		heap[i].c64size = c64;
		heap[i].kind = far_kind[K_HEAP] ? K_HEAP : K_NEAR;
		heap[i].hcat = hcat;
		nheap++;
	}
	for (uint32_t q = at >> 8; q <= (at + c64 - 1) >> 8 && q < PAGES; q++)
		page_kind[q] = far_kind[K_HEAP] ? K_HEAP : K_NEAR;
}

static void heap_del(void *p)
{
	int lo = 0, hi = nheap - 1;
	if (!p || state <= 0)
		return;
	last = NULL;
	while (lo <= hi)
	{
		int mid = (lo + hi) / 2;
		if ((uintptr_t)p < heap[mid].addr)
			hi = mid - 1;
		else if ((uintptr_t)p > heap[mid].addr)
			lo = mid + 1;
		else
		{
			uint32_t c64 = heap[mid].c64size;
			if (c64 <= 256)
			{
				int c = (c64 + 7) / 8;
				if (cls_nfree[c] < MAXFREE)
					cls_free[c][cls_nfree[c]++] = heap[mid].c64addr;
			}
			memmove(heap + mid, heap + mid + 1, (nheap - mid - 1) * sizeof *heap);
			nheap--;
			return;
		}
	}
}

void *__wrap_malloc(size_t n)
{
	void *p = __real_malloc(n);
	heap_add(p, n);
	return p;
}

void *__wrap_calloc(size_t a, size_t b)
{
	void *p = __real_calloc(a, b);
	heap_add(p, a * b);
	return p;
}

void *__wrap_realloc(void *p, size_t n)
{
	void *q = __real_realloc(p, n);
	if (q)
	{
		heap_del(p);
		heap_add(q, n);
	}
	return q;
}

void __wrap_free(void *p)
{
	heap_del(p);
	__real_free(p);
}
