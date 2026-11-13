/* OSCAR64 REPRO r43 - WRONG CODE, native code only: a pointer that a loop reads through
 * first and then sets to the address of an array element (&objs[k]) reads from a wrong
 * address in every iteration
 * NetHack: no site found.  A pin build that makes the check below both ways and logs each
 * call (control: this loop in hacklib.c) logged 188,676 calls in a harness run over
 * port/src and 6,276 in the four builds of src/, 381 and 16 accepted, none that the fixed
 * check refuses.  Not covered: the 61 files that do not compile, makemon.c (hang), shknam.c
 * (crash).
 * Found 2026-11-13 by the verification of r36.
 * Cause: PeepHoleOptimizerIterateN turns "reg = global + index" and the accesses through
 * (reg),y behind it into absolute indexed ones and drops the address computation if
 * CheckGlobalAddressSumYPointer finds every use.  That walk starts in the middle of a
 * block and marks it as visited at once; when a loop brings it back to the block's top
 * it stops, and a read in front of the computation is never seen.  The read then goes
 * through the index and a stale high byte: $0802 + 4 * k here.
 * Expect when fixed: emulation result 0.  Actual (v1.32.273, the pin f001eba, upstream main
 * 4da3147; native code at the default level, -O2, -Os, -O3): result 1, f(3, 2) returns 0,
 * not 65, and f(2, 1) 24676, not 25.  Native -O0 and bytecode are right.  Also wrong: an
 * int or char array, an index that changes in the loop, a call or (-O2, -Os, -O3) a
 * condition in the loop.  Right: a constant index.
 * Not fixed upstream.  Fix (TASKS T1.22): ours, two lines moved, scratch/r43-fix-pin
 * 67d2908 and scratch/r43-fix-main 6f811e3, or r40's 7a4f9ff: 0 in all ten.  Local.
 * Workaround: none needed where checked.  In source: assign in front of the read
 * ("if (i > 0) otmp = &objs[k];" at the top of the loop; 0 in all ten on v1.32.273 and
 * the pin).  Not: a second pointer set in front of the loop (r40), volatile.
 * FLAGS: -e -Os
 */
struct obj { char ox, oy; int quan; };
struct obj objs[4] = {{1, 2, 10}, {3, 4, 20}, {5, 6, 30}, {7, 8, 40}};
struct obj first = {0, 0, 5};

__noinline int f(int n, int k)
{
	int r = 0, i;
	struct obj * otmp = &first;

	for (i = 0; i < n; i++)
	{
		r += otmp->quan;	/* first iteration: first.quan = 5 */
		otmp = &objs[k];
	}
	return r;
}

int main(void)
{
	if (f(3, 2) != 65)	/* 5 + 30 + 30 */
		return 1;
	if (f(2, 1) != 25)	/* 5 + 20 */
		return 2;
	return 0;
}
