/* OSCAR64 REPRO r63 - WRONG CODE: a call with constant arguments, folded at compile time,
 * gives the value of the wrong argument when the function has an unused parameter.
 * GlobalOptimizer's ReplaceConstCalls evaluates a call to a function without side
 * effects whose arguments are all constants (ConstexprInterpreter), binding each argument
 * at its parameter's mVarIndex.  The same Optimize pass marks a parameter the body never
 * reads DTF_FPARAM_UNUSED and renumbers it as a local (func->mNumVars++), so the unused
 * b below gets index 0, a's offset: binding 2 to b overwrites the 7 bound to a, and
 * pick(7, 2) folds to 2.  It happens when the callee's turn in the pass comes before the
 * caller's (here main calls pick first), and the folded call is not folded away by its
 * caller first (caller takes a run-time argument).  v1.32.273, the pin and upstream main
 * (16acc53) all return 1 at -O2, -Os and -O3, native and bytecode; -O0 is right.
 * NetHack: in the banked whole-game compile, check_recordfile()'s
 * fqname(RECORD, SCOREPREFIX, 0), whose fqname() is `return basename;` without
 * PREFIXES_IN_USE, folded to 5, SCOREPREFIX, and failed as "Cannot assign incompatible
 * types 'const u8*' != 'i16'" (then a crash writing the .error.int file).  Had the two
 * types matched it would have compiled to wrong code without a word.  The per-file
 * measurement compiles never show it: their harness takes every function's address,
 * and an address-taken function keeps its parameters.  Found 2026-11-15.
 * Expect when fixed: emulation result 0.
 * Workaround: none in the source; fixed by the ADR-0007 compiler (commits 66-67,
 * 2026-11-15): the interpreter binds nothing for an unused parameter.
 * FLAGS: -e -O2
 */
volatile int v;

int pick(int a, int b)
{
	return a;
}

int caller(int x)
{
	return pick(7, 2) + x;
}

int main(void)
{
	v = 0;
	int s = pick(v, v);
	int r = caller(v);
	return r != 7 || s != 0;
}
