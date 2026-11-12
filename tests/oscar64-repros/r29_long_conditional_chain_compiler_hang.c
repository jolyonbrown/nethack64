/* OSCAR64 REPRO r29 - COMPILER HANG: a long run of independent conditionals in a function
 * that keeps a value in a register across it
 * NetHack: feel_location() and newsym() in display.c.  v1.32.273 stops at an earlier error
 * there (3013 "Pointer expected" in obj_to_glyph(): the compat #7 shape with an (int) cast,
 * which oscar_normalize.py does not rewrite; T1.4); with that worked around, the
 * eight-commit patched pin is still in CanJoinEntryLoadStoreZP after 140 s.  Found
 * 2026-11-12.
 * Cause: two recursive walks over the predecessor graph in the native code optimiser keep
 * no visited set, so they visit a block once per path, and N conditionals in a row have
 * 2^N paths: CanJoinEntryLoadStoreZP (can a zero page copy move up into the blocks in
 * front of a join; argjoin below) and IsSameRegisterSource (does A, X or Y already hold
 * the value a load would give it, on every path into the block; vsum below).  Time only;
 * memory stays flat.  Native code; -O0 avoids the first walk only.
 * Expect when fixed: compiles in under a second, emulation result 0.  Actual (v1.32.273,
 * patched pin c2f5cab, upstream main 4da3147, -Os): compiler hang.  run.py stops it after
 * 120 s, so this file costs "make repros" two minutes for as long as the compiler is
 * unfixed.
 * Fixed by fix/exponential-walks-2 on upstream main (PR #16 in docs/OSCAR64-UPSTREAM.md, a
 * draft in the fork) and by its backport of these two walks, nethack64/pin-walks-display:
 * candidate for the patched pin, Jolyon's decision pending (ADR-0007); display.c then gets
 * through code generation in about 5 s.  nethack64/pin-r30 (the third walk) does not fix it.
 * Workaround: none applied (display.c does not get this far yet).  Without a compiler
 * fix: "#pragma optimize(push)" and "#pragma optimize(0)" in front of feel_location(),
 * "#pragma optimize(pop)" behind newsym(), inside #ifdef __OSCAR64C__.
 * FLAGS: -e -Os
 */
/* Growth, v1.32.273 at -Os: argjoin alone with 22/24/26 conditionals takes 0.4/1.3/5.0 s;
 * vsum alone with 14/16/18 takes 0.2/1.9/16 s, and over 100 s with 20. */
#define C4(i) if (fl[i]) acc += 1; if (fl[i + 1]) acc += 2; if (fl[i + 2]) acc += 3; if (fl[i + 3]) acc += 4;

char fl[64], gk;
int acc;
volatile char buf[4], buf2[4];

__noinline int isink(int x, int y)
{
	return 100 * x + y;
}

/* 36 conditionals between a value held in a register and the two calls that use it */
__noinline int argjoin(int a, int b)
{
	int x = a * 3 + b;

	C4(0) C4(4) C4(8) C4(12) C4(16) C4(20) C4(24) C4(28) C4(32)
	if (fl[63]) return isink(x, 1);
	return isink(2, x);
}

/* 24 conditionals between two reads through the same pointer (the index 1 stays in Y for
 * the second read) */
__noinline int vsum(volatile char * p)
{
	int s = 0;

	s += p[1];
	C4(0) C4(4) C4(8) C4(12) C4(16) C4(20)
	if (gk) s += p[2];
	s += p[1];
	return s;
}

int main(void)
{
	buf[1] = 3; buf[2] = 4; buf2[1] = 7; buf2[2] = 8;
	if (vsum(buf) != 6)
		return 1;
	if (argjoin(5, 2) != 217 || argjoin(4, 5) != 217)
		return 2;
	gk = 1; fl[1] = 1; fl[63] = 1;
	if (vsum(buf2) != 22)
		return 3;
	if (argjoin(5, 2) != 1701 || argjoin(4, 5) != 1701)
		return 4;
	return acc != 2 + 2 + 2;
}
