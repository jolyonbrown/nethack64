/* OSCAR64 REPRO r28 - COMPILER HANG: a struct copied onto itself through a pointer, then read
 * NetHack: clone_mon() in makemon.c ("*m3 = *m2; ... if (m2->mnamelth)") in the measurement
 * harness, whose pointer stubs all return one global (alloc() below).  Oscar64 merges the two
 * reads of that void * volatile (a separate bug, r34), so m3 and m2 become one pointer and the
 * copy a copy onto itself.  The real alloc() returns a new block, so the cartridge build of
 * clone_mon() should not hit it.  save_restore() below hangs with no stubs and no self copy
 * in the source, at every optimisation level.  makemon.c is "compiler-hang" in the harness
 * since the 2026-11-08 baseline (memory flat at 185 MB); diagnosed 2026-11-12.
 * Cause: LoadStoreForwarding and PropagateVariableCopy record each struct copy and redirect a
 * later read of its destination to its source.  When source and destination are the same, the
 * read is unchanged but the pass reports a change, and its caller repeats it for ever.
 * PropagateVariableCopy itself turns "t = *p; *p = t;" into "*p = *p".
 * Expect when fixed: compiles in well under a second, emulation result 0.  Actual (v1.32.273,
 * patched pin c2f5cab, upstream main 4da3147): never finishes, at any -O level; clone_mon()
 * alone hangs at -O2, -Os and -O3 only.  run.py stops it after 120 s, so this file costs
 * "make repros" two minutes for as long as the compiler is unfixed.
 * Fixed by fix/makemon-hang on upstream main (PR #18 in docs/OSCAR64-UPSTREAM.md, a draft in
 * the fork) and by its backport nethack64/pin-makemon-hang: candidate for the patched pin,
 * Jolyon's decision pending (ADR-0007).
 * Workaround: none needed in port/.  Harness (T1.10, not applied yet): pointer stubs that
 * read nh_vl instead, "return (T)(unsigned)nh_vl;" in tools/measure/mkstubs.py; Oscar64
 * keeps both of those reads.
 * FLAGS: -e -Os
 */
struct monst_s
{
	struct monst_s *nmon;
	char pad[66];
	unsigned char mhp;
	unsigned char isminion;
	char pad2[10];
};

struct monst_s pool[2];
void * volatile nh_vp;

/* the harness's stub: every call returns the same pointer */
long * alloc(unsigned int n)
{
	return (long *)nh_vp;
}

struct monst_s * clone_mon(struct monst_s * mon)
{
	struct monst_s * m2, * m3;

	m2 = (struct monst_s *)alloc(sizeof(struct monst_s));
	*m2 = *mon;
	m2->nmon = 0;
	m2->mhp = mon->mhp / 2;
	mon->mhp -= m2->mhp;
	if (mon->isminion)
	{
		m3 = (struct monst_s *)alloc(sizeof(struct monst_s) + 4);
		*m3 = *m2;	/* m3 and m2 are one pointer: a copy onto itself */
		if (m2->mhp) m3->pad2[0] = 4;
		m2 = m3;
	}
	return m2;
}

/* the same hang without the stubs: no self copy in the source, the optimiser makes one */
struct monst_s mons[2];
volatile char vi;

int save_restore(struct monst_s * p, struct monst_s * q)
{
	struct monst_s t = *p;
	*p = t;
	*q = *p;
	return p->mhp;
}

int main(void)
{
	struct monst_s * m;

	nh_vp = &pool[0];
	pool[1].mhp = 21;
	pool[1].isminion = 1;
	m = clone_mon(&pool[1]);
	mons[0].mhp = 9;
	if (save_restore(mons + vi, mons + 1 - vi) != 9 || mons[1].mhp != 9)
		return 2;
	return m == &pool[0] && m->mhp == 10 && pool[1].mhp == 11 && m->pad2[0] == 4 ? 0 : 1;
}
