/* OSCAR64 REPRO r77 - WRONG CODE: AN INDEX REGISTER KEPT ACROSS A CALL THAT CHANGES WHAT IT
 * COPIED.  `huge[idx(299)] = 1` ends with LDY ACCU+0 (the result's low byte as the index);
 * the next `small[idx(2)]` calls idx() again, which leaves its result in ACCU and does not
 * touch Y, and then reads `small,y`: the native code generator still takes Y for a copy of
 * ACCU+0, so it reads small[0x2b] (299's low byte), not small[2].  Every optimisation level
 * (-O0 too), native code; v1.32.273, the pin (to commit 83) and the far-spaces fork; right
 * on upstream main 4da3147 (2026-11-19).  Found 2026-11-21 writing an autotest for the
 * far-spaces fork (fardefaulttest.c: odd3[idx(2)] after huge[idx(299)] = 1).
 * NetHack: any two indexed accesses whose indexes are results of calls of small functions
 * the optimiser can see into: an array store or load at index f(x) and then another at
 * index g(y) (`levl[x][y]` with computed coordinates, `mvitals[monsndx(ptr)]`).  The host
 * build cannot show it; the banked C64 game does not run yet.
 * Expect when fixed: small[idx(2)] reads 6 (exit 0).
 * Workaround: none in the source (too common a pattern): the compiler must be fixed.  Fixed
 * by pin commit 84 (upstream 9d39d74 backported, 2026-11-21).
 * FLAGS: -n -e
 */
char small[3] = { 4, 5, 6 };
char huge[300];

__noinline int idx(int i) { return i; }

int main(void)
{
	huge[idx(299)] = 1;
	return small[idx(2)] != 6;
}
