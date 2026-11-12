/* OSCAR64 REPRO r21 - WRONG CODE: a loop over a const table with negative entries, evaluated
 * at compile time, reads each negative entry as unsigned
 * NetHack: loops over xdir/ydir-style schar tables whose result the compiler can work out
 * at compile time (exposure not counted yet).  Found 2026-11-12 by the review of the
 * upstream r20 fix.
 * The optimiser runs the loop at compile time (ConstSingleLoopOptimization) and reads tab[]
 * through LoadConstantOperand, which builds the value from its bytes without sign extension:
 * s comes out as 65533 instead of -3.  Fails at the default level, -O2, -Os and -O3, native
 * and bytecode, on v1.32.273 and upstream main 4da3147; -O0 is correct.  With the r20 fix
 * alone (LoadConstantFold, see r20) -O2 and -O3 become correct, the default level and -Os
 * stay wrong.
 * Expect when fixed: compiles, emulation result 0.  Actual at -Os: emulation result 1.
 * Workaround: none applied yet.
 * FLAGS: -e -Os
 */
static const int tab[4] = {-3, 5, -7, 2};
int main(void)
{
	int s = 0;
	for (char i = 0; i < 4; i++)
		s += tab[i];
	if (s / 3 != -1)
		return 1;
	return 0;
}
