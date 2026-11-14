/* OSCAR64 REPRO r48 - a conditional expression as the middle operand of another,
 * `a ? b ? x : y : z`, is rejected: "error 3006: ':' expected".  C reads it as
 * `a ? (b ? x : y) : z`, and with those parentheses it compiles.
 * NetHack: 3 sites, pray.c 789 and 791 (pray.c's first compile error, at 790) and
 * shk.c 2668 (2026-11-14).
 * Cause: Parser::ParseConditionalExpression parses the middle operand with
 * ParseLogicOrExpression, where C allows any expression, so it stops at the inner
 * '?' and then wants ':'.  On v1.32.273, the pin and upstream main (16acc53).
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: parentheses round the inner conditional at each site (comments name r48).
 * FLAGS: -e
 */
int f(int a, int b)
{
	return a ? b ? 1 : 2 : 3;
}

int main(void) { return f(1, 1) == 1 && f(1, 0) == 2 && f(0, 1) == 3 ? 0 : 1; }
