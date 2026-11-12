/* OSCAR64 REPRO r35 - WRONG CODE: after a volatile struct copy overwrites a struct, a read of an
 * earlier copy of that struct returns the new contents
 * NetHack: not exposed.  port/ and src/ contain no copy to or from a volatile struct (grep,
 * 2026-11-12).  Found by the review of the r28 fix, in the block of code that fix touches.
 * Cause: InterCodeBasicBlock::PropagateVariableCopy (InterCode.cpp) keeps a list of struct
 * copies and redirects a later read of a copy's destination to its source.  On each new
 * IC_COPY it works out which recorded copies the new one invalidates, but the statement that
 * drops them, ltemps.SetSize(j), sits inside "if (!ins->mVolatile)".  After a volatile copy
 * into *p the recorded "*q = *p" therefore stays, and "q->b" is compiled as "p->b".
 * Expect when fixed: emulation result 0 (f returns the old p->b, 1).  Actual (v1.32.273,
 * patched pin c2f5cab, upstream main 4da3147, with and without the r28 fix, -O0 to -O3 and
 * -Os, native and bytecode): result 1, f returns 3, the value the volatile copy put into *p.
 * Without __noinline the wrong value appears only below -O2.
 * Not fixed anywhere (TASKS T1.19): the r28 fix leaves it as it was.  The review's trial
 * fix, moving "ltemps.SetSize(j);" in front of that "if", made the review's test pass in all
 * ten autotest configurations; it has not been through the full autotest and is not in any
 * branch.
 * Workaround: none needed in NetHack.  Copying the volatile struct into a plain local first
 * ("t = vz; *p = t;") gives result 0 in the same configurations.
 * FLAGS: -e -Os
 */
struct S
{
	char a[20];
	int b;
};

struct S x, y;
volatile struct S vz;
volatile char vi;

__noinline int f(struct S * p, struct S * q)
{
	*q = *p;
	*p = vz;	/* volatile copy: must invalidate what is known about *p */
	return q->b;	/* the old p->b */
}

int main(void)
{
	int r;

	x.b = 1;
	y.b = 2;
	vz.b = 3;
	r = f(&x + vi, &y + vi);
	if (r != 1)
		return r == 3 ? 1 : 2;	/* 1: the stale forward described above */
	return x.b == 3 && y.b == 1 ? 0 : 3;
}
