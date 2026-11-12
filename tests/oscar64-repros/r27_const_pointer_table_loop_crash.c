/* OSCAR64 REPRO r27 - COMPILER CRASH: a loop over a constant table of pointers that the
 * optimiser runs at compile time makes the compiler segfault
 * NetHack: nameshk() in shknam.c, line 310: after nlp = shkgeneral the loop
 * for (names_avail = 0; nlp[names_avail]; names_avail++) continue; counts a constant
 * NULL-terminated table of 30 shopkeeper names.  v1.32.273 and the eight-commit patched pin
 * (ADR-0007) segfault on shknam.c (C64 configuration, -Os) after about 2.5 s, and so does
 * upstream main 4da3147 with our other fixes (nethack64/integration-final3); this file
 * crashes plain main 4da3147 too.  In the measurement harness's results since the
 * 2026-11-08 baseline; diagnosed 2026-11-12.  A scan of port/src for loops that index a
 * constant table by name found no other loop the optimiser runs this way.
 * Cause: ConstSingleLoopOptimization and ConstInnerLoopOptimization run such a loop at
 * compile time and read each table entry through LoadConstantOperand, whose pointer case was
 * copied from LoadConstantFold and still takes the operand size from
 * ins->mConst.mLinkerObject, the load instruction's unused constant operand (null).  Behind
 * that crash both evaluators decide the loop branch by mIntConst alone, so a pointer to a
 * string at offset 0 counts as null and the loop stops after one step (count 1 instead
 * of 4).  Any level but -O0, native and bytecode.
 * Expect when fixed: compiles, emulation result 0.  Actual at -Os: compiler crashed
 * (signal 11).  Fixed by fix/shknam-crash on upstream main (PR #17 in
 * docs/OSCAR64-UPSTREAM.md, a draft in the fork) and by its backport
 * nethack64/pin-shknam-crash: candidate for the patched pin, Jolyon's decision pending
 * (ADR-0007).
 * Workaround: none applied yet.  Without the pin commit: in nameshk(), replace the count
 * after nlp = shkgeneral by names_avail = SIZE(shkgeneral) - 1 (30, the same value).
 * FLAGS: -e -Os
 */
static const char * const shkgeneral[] = {
    "Hebiwerie", "Possogroenoe", "Asidonhopo", "Manlobbi", 0
};

int main(void)
{
	const char * const *nlp = shkgeneral;
	int names_avail;

	for (names_avail = 0; nlp[names_avail]; names_avail++)
		continue;
	if (names_avail != 4)
		return 1;
	if (nlp[names_avail - 1][0] != 'M')
		return 2;
	return 0;
}
