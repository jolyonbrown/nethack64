/* OSCAR64 REPRO r37 - WRONG CODE: the low byte of a call's result is replaced by a load of
 * an array element stored before the call: r + t[0] + use(t) gives r + t[0] + t[0]
 * NetHack: no site found.  A pin build that logs the faulty step (control: this file) saw
 * no read behind a call rewritten in the files that reach code generation in the harness:
 * with its usual inlined stubs (calls within a file, to the base files and to libc only),
 * and again with every stub __noinline (42 files).  Not checked: mhitm.c and mkobj.c (the
 * pin crashes on them with __noinline stubs) and the 61 files that do not compile.
 * Found 2026-11-13 by the review of the pin candidates.
 * Cause: the native peephole pass replaces reads of a zero page register by reads of the
 * global or static local the same byte was stored to ("STA zp; STA abs").  At a JSR to a
 * function that stores to no global, CheckSingleUseGlobalLoad walks on without asking
 * whether the call overwrites the register; PatchSingleUseGlobalLoad ignores calls.  The
 * byte for t[0] passes through ACCU and is read from there again before the call, so the
 * read of ACCU behind "JSR use", the result's low byte, becomes "LDA t[0]".
 * Expect when fixed: emulation result 0.  Actual, native only (bytecode gives 0): v1.32.273
 * and the pin f001eba 15 at the default level, -O2, -Os, -O3 and 12 at -O0; upstream main
 * 4da3147 12 at all five: there f() passes (main no longer re-reads ACCU) and g() fails.
 * Fix (TASKS T1.23): ours, 17 lines, local branch scratch/r37-backport-pin (both walks end
 * at a call that changes the register): 0 in all ten.  Not in the pin, not proposed
 * upstream.  A sibling in the same walk stays: a callee that stores through a pointer
 * counts as storing no global (r44).
 * Workaround: none needed in NetHack.  With the pin, make the call first ("u = use(t);
 * return r + t[0] + u;", 0 in all ten); not on main, which moves g()'s sum back in front.
 * FLAGS: -e -Os
 */
char arr[8] = {10, 20, 30, 40, 50, 60, 70, 80};
char fl;
unsigned acc;

__noinline unsigned use(char * q)
{
	return q[0] + q[1];
}

__noinline unsigned f(char k)
{
	char t[2];
	unsigned r = 0;

	t[1] = 1;
	t[0] = arr[k];
	if (!fl)
		r += use(t);
	t[0] = arr[k + 1];
	return r + t[0] + use(t);	/* r + t[0] is added up before the call */
}

/* The accumulator is needed for r ^ 0x55, so the element is read back from the register
 * for the sum: this form is wrong at -O0 and on upstream main as well. */
__noinline unsigned g(char k)
{
	char t[2];
	unsigned r = 0;

	t[1] = 1;
	t[0] = arr[k];
	if (!fl)
		r += use(t);
	t[0] = arr[k + 1];
	acc = (r ^ 0x55) + t[0];
	return acc + use(t);
}

int main(void)
{
	int e = 0;

	if (f(0) != 11 + 20 + 21) e |= 1;	/* r + t[0] + use(t) */
	if (f(2) != 31 + 40 + 41) e |= 1;
	if (g(0) != (11 ^ 0x55) + 20 + 21) e |= 4;
	if (g(2) != (31 ^ 0x55) + 40 + 41) e |= 4;
	fl = 1;
	if (f(0) != 20 + 21) e |= 2;		/* r stays 0 */
	if (f(1) != 30 + 31) e |= 2;
	if (g(0) != 0x55 + 20 + 21) e |= 8;
	if (g(1) != 0x55 + 30 + 31) e |= 8;
	return e;
}
