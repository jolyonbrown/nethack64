/* OSCAR64 REPRO r18 - WRONG CODE: the char result of a call through a function pointer
 * The callee returns a char, signed char or unsigned char in the A register; the caller
 * of an indirect call (JSR bcexec) reads it from zero-page ACCU, which still holds the
 * low byte of the function's address.  No diagnostic.  short, int and long results are
 * fine.  At -Os and -O2 it shows once the target is not known at compile time; at -O0
 * every indirect call with a char result is wrong.
 * NetHack: every call through a pointer to a char or boolean (signed char) function.
 * yn_function() is `(*windowprocs.win_yn_function)` returning char, so `yn(...) == 'y'`
 * compares garbage once windowprocs is set at run time (checked with a windowprocs-shaped
 * probe, 2026-11-10).  Also at risk: the boolean filter callbacks in pickup.c (e.g.
 * query_objlist's `(*allow)(curr)`) and invent.c, and the region callbacks (region.c).
 * Found while checking a workaround for r17.
 * Expect when fixed: emulation result 0.  Actual: emulation result 1 (error 3007
 * "Execution failed"), also at -O2 and -O0.
 * Workaround: none yet; must be settled before game code runs (TASKS T1.13).
 * FLAGS: -e -Os
 */
signed char z0(void) { return 0; }
signed char z1(void) { return 1; }
volatile int k;
int main(void)
{
	signed char (*fp)(void) = z0;
	if (k)
		fp = z1;
	return fp() ? 1 : 0;
}
