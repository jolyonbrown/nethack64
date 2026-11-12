/* OSCAR64 REPRO r34 - WRONG CODE: two reads of a volatile pointer through a pointer cast are
 * merged into one, at every optimisation level
 * NetHack: no game code.  port/ and src/ never read a volatile pointer variable through a
 * cast (grep, 2026-11-12).  The measurement harness does: tools/measure/mkstubs.py stubs
 * every pointer-returning function as "return (T *)nh_vp;" with "void * volatile nh_vp",
 * meant to be opaque to the optimiser.  It is not: in makemon.c the two newmonst() calls of
 * clone_mon() became one value, which turned "*m2 = *mon; *m3 = *m2;" into a struct copied
 * onto itself and exposed r28.  Found 2026-11-12 by the review of the r28 fix.
 * Cause: InterCodeGenerator.cpp, EX_TYPECAST from pointer to pointer, returns
 * ExValue(exp->mDecType, vr.mTemp, vr.mReference): still a reference to the variable, but
 * with the cast's type, which has no DTF_VOLATILE.  Dereference() takes the load's mVolatile
 * from that type, so the load is an ordinary one and equal loads are merged.
 * Expect when fixed: emulation result 0.  Actual (v1.32.273, patched pin c2f5cab, upstream
 * main 4da3147): result 6 at every level but -O0, native and bytecode (both cast forms
 * merged); result 2 at -O0, where get() is not inlined and the stub form survives.  Never
 * 0, and bit 1, the control without a cast, is never set.  The test reads $dd80/$dd81 of
 * Oscar64's emulator, which under -ei return a counter that increments on every read, so
 * merged reads compare equal.  Not fixed anywhere (TASKS T1.18); not part of the r28 fix.
 * Workaround: read into a plain variable first, "void *p = vp; return (T *)p;", or return
 * "(T *)(unsigned)nh_vl" from the volatile long; both keep every read (same test, result 0
 * from -O0 to -O3 and -Os, native and bytecode, on the three compilers).
 * FLAGS: -ei -Os
 */
#define HW (*(void * volatile *)0xdd80)

long * get(void)
{
	return (long *)HW;	/* the form of the harness stubs */
}

int main(void)
{
	int r = 0;
	void *c = HW, *d = HW;		/* control: reads without a cast */
	long *a = (long *)HW;
	long *b = (long *)HW;
	long *e = get();
	long *f = get();

	if (c == d) r |= 1;
	if (a == b) r |= 2;		/* the cast reads were merged */
	if (e == f) r |= 4;		/* the same after inlining */
	return r;
}
