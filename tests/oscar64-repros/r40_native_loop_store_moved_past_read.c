/* OSCAR64 REPRO r40 - WRONG CODE, native code only: a variable that a loop reads first and
 * then assigns a constant or another variable (r += v; v = 30;) reads the new value in the
 * first iteration too
 * NetHack: one place has the shape and compiles the same with the fix.  A pin with the
 * fix, logging each store the fix keeps in its loop, logged initworm() (worm.c) and nothing
 * else in the 44 port/ files that reach code generation (native -Os); worm.c's code
 * with and without the fix differs in two label names.  Not checked: the 63 files that
 * do not compile yet, src/, other levels.
 * Found 2026-11-13 by the review of the r36 fix.
 * Cause: NativeCodeBasicBlock::OptimizeSimpleLoopInvariant (NativeCodeGenerator.cpp) moves
 * "LDA #c; STA zp" and "LDA zp1; STA zp2" out of a one-block loop to in front of it when
 * nothing else in the block changes zp (zp1, zp2), and never asks whether the block reads
 * the stored location above the store.  r36 is the same mistake in the intermediate code.
 * Expect when fixed: emulation result 0.  Actual (v1.32.273, the pin f001eba, upstream main
 * 4da3147, pin and main also with the r36 fix; native): result 7 at the default level, -O2,
 * -Os, -O3 (f(3) returns 90, not 65; g(2, 100, 200) 600, not 305; h(2, 7) 60, not 37) and
 * 4 at -O0 (h only: its variable is a parameter).  Bytecode is right.
 * Not fixed upstream, not in the pin.  Fix: ours, both moves ask ReferencesZeroPage first,
 * scratch/r36-native-fix-pin 5997864 and scratch/r40-native-fix-main 3ac93dd: 0 in all
 * ten.  Still wrong with 5997864 at -O0: an int parameter assigned an int parameter
 * (v = w), through the "LDY zp" move; 8cae5da on it cures that (T1.22).  All local.
 * Workaround: take the first iteration out of the loop (0 in all ten on v1.32.273, the
 * pin and main).  "volatile" on the variable does not help, nor does reading it into a
 * second variable first (t = v; v = 30; r += t;).
 * FLAGS: -e -Os
 */
__noinline int f(char n)
{
	int r = 0;
	int v = 5;
	char i;

	for (i = 0; i < n; i++)
	{
		r += v;		/* first iteration: 5 */
		v = 30;		/* LDA #30; STA v */
	}
	return r;
}

__noinline int g(char n, int a, int b)
{
	int r = 0;
	int v = 5;
	int w = a + b;
	char i;

	for (i = 0; i < n; i++)
	{
		r += v;		/* first iteration: 5 */
		v = w;		/* LDA w; STA v */
	}
	return r;
}

__noinline int h(char n, char v)
{
	int r = 0;
	char i;

	for (i = 0; i < n; i++)
	{
		r += v;		/* first iteration: the argument */
		v = 30;
	}
	return r;
}

int main(void)
{
	int e = 0;

	if (f(3) != 65 || f(2) != 35) e |= 1;
	if (g(3, 10, 20) != 65 || g(2, 100, 200) != 305) e |= 2;
	if (h(3, 5) != 65 || h(2, 7) != 37) e |= 4;
	return e;
}
