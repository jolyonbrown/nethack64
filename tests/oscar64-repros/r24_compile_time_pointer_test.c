/* OSCAR64 REPRO r24 - WRONG CODE: a side-effect-free helper that tests a pointer, called
 * with a constant address, is evaluated at compile time with the wrong answer
 * NetHack: helpers called with constant addresses (string literals, &youmonst, &u...)
 * whose result the optimiser can work out at compile time; exposure not counted yet.
 * Found 2026-11-12 by the review of the upstream r19 fix.
 * At -O2/-Os/-O3 GlobalOptimizer::ReplaceConstCalls runs the helper in the ConstexprInterpreter,
 * whose EvalRelational compares a pointer with an integer as two integers, so any address
 * constant equals 0: has("abc") is 0.  The same for `0 != p`, `p == q` with p and q the same
 * address, and `if (p)`.  Native and bytecode, on v1.32.273 and upstream main 4da3147, and
 * not fixed by the r19 fix (a different code path).  -O0 and the default level are right.
 * Writing the comparison as `s != (const char *)0` gives correct code.
 * Expect when fixed: compiles, emulation result 0.  Actual at -Os: emulation result 1.
 * Workaround: none applied yet.
 * FLAGS: -e -Os
 */
static int has(const char *s) { return s != 0; }

int main(void)
{
	if (!has("abc"))
		return 1;
	return 0;
}
