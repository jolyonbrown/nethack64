/* OSCAR64 REPRO r36 - WRONG CODE: a variable read at the top of a loop and assigned a loop
 * invariant value (a load, k + 1) later in the same iteration reads the new value in the
 * first iteration too
 * NetHack: no site found (2026-11-13).  A pin compiler instrumented to log each such move
 * logged none in the 44 port/ files that reach code generation, nor in src/; the files that
 * do not compile yet were only searched by hand.  That check does not see the native-code
 * forms, r40 and r43.  Found 2026-11-12 by the review of the pin candidates.
 * Cause: InterCodeBasicBlock::InnerLoopOptimization (InterCode.cpp) moves an instruction that
 * is executed in every iteration and whose operands do not change in the loop in front of
 * the loop, and never asks whether the temporary it writes is still needed with the value
 * it has on entry.  "v = 5" and "v = arr[k]" write the same temporary, so the load lands in
 * front of the loop, behind "v = 5", and the 5 is gone.
 * Expect when fixed: emulation result 0.  Actual (v1.32.273, patched pin c2f5cab and
 * f001eba, upstream main 4da3147; default level, -O2, -Os, -O3; native and bytecode):
 * result 1, f(3, 2) returns 90 = 30 + 30 + 30, not 65 = 5 + 30 + 30.  -O0 is right.
 * Not fixed upstream or in the pin (TASKS T1.22).  Our fix keeps such an instruction in the
 * loop (local branches scratch/r36-fix-pin and scratch/r36-fix-main in the compiler clone,
 * not proposed upstream): result 0 in all ten configurations, autotest clean on the pin.
 * Workaround: take the first iteration out of the loop.  "volatile" on the variable does
 * not help, and assigning from a second variable set in front of the loop is not safe
 * (a char with a char sum stays wrong in native code: r40).  Native code has two more
 * forms of the same mistake that this fix does not reach: r40 (an int, or a one-block
 * loop) and r43 (a pointer set to a fixed address).
 * FLAGS: -e -Os
 */
char arr[4] = {10, 20, 30, 40};

__noinline int f(char n, char k)
{
	int r = 0;
	char v = 5;
	char i;

	for (i = 0; i < n; i++)
	{
		r += v;		/* first iteration: 5 */
		v = arr[k];	/* does not change in the loop */
	}
	return r;
}

int main(void)
{
	int a = f(3, 2), b = f(2, 1);

	if (a != 65 || b != 25)
		return a == 90 && b == 40 ? 1 : 2;	/* 1: the first iteration read arr[k] */
	return 0;
}
