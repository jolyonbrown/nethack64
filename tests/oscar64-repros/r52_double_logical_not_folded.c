/* OSCAR64 REPRO r52 - `!!x` is folded to `x`: the wrong value for an integer, the wrong
 * type for a pointer.  **Wrong code with no diagnostic** for integers.  C89 3.3.3.3:
 * `!E` is 0 or 1 with type int, so `!!5` is 1, `!!(f & 0x100)` stored in a char is 1
 * and `!!p` is an int.  Oscar64 gives 5, 0 and a pointer ("Cannot assign incompatible
 * types 'i16' != 'struct s*'"); `!(!x)` is the same; -O0 to -Os.
 * Cause: Parser::ParsePrefixExpression handles `!` with Expression::LogicInvertExpression
 * (Declaration.cpp), which undoes an inner `!` by returning its operand.  That is right
 * where only the truth value matters (a condition), wrong for a value.  On v1.32.273,
 * the pin (48 commits) and upstream main (16acc53, 2026-11-14).
 * NetHack: 98 `!!` in port/ (35 files), e.g. `res = !!revive(obj)` (zap.c 1554) and
 * `!!(index(str, otmp->oclass))` as a `?:` operand (mon.c 868), the first error of
 * each file (2026-11-14).  Integer operands compile, to the wrong value.
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: none in port/; fixed by the ADR-0007 compiler (commits 54-55, with the fold
 * of `!` on constants, commits 52-53, 2026-11-14).
 * FLAGS: -e
 */
struct s { int x; };
struct s a, *p = &a;
int flags = 0x100;
volatile int five = 5;
int main(void)
{
	char c = !!(flags & 0x100);
	int n = !!five + !!five;
	int r = !!p;
	return c == 1 && n == 2 && r == 1 ? 0 : 1;
}
