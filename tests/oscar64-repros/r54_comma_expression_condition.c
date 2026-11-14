/* OSCAR64 REPRO r54 - a comma expression as the condition of if, while, do-while or
 * switch is rejected: "error 3006: ')' expected".  C89 3.6.4, 3.6.5: the controlling
 * expression is an expression, and `a, b` is one.  The comma in a for header and in a
 * parenthesised `(a, b)` elsewhere compiles; so does `while ((a, b))`.
 * Cause: Parser::ParseParenthesisExpression (if, while, do-while) and
 * ParseSwitchStatement parse the condition with ParseExpression, which stops at a comma;
 * the comma operator is ParseListExpression's.  On v1.32.273, the pin and upstream main
 * (16acc53).
 * NetHack: restore.c 310 and 796, `while (fnext = newfruit(), mread(fd, ...),
 * fnext->fid != 0)` and the same for traps, the file's first error (2026-11-14).
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: tools/oscar_normalize.py doubles the parentheses of such a condition.
 * FLAGS: -e
 */
int n, m;
int step(void) { return ++n; }
int main(void)
{
	int k = 0;
	while (m = step(), m < 5)
		;
	if (k = 2, k == 2)
		k = 3;
	do
		k++;
	while (k++, k < 9);
	switch (m = 0, k) {
	case 9:
		return n == 5 && m == 0 ? 0 : 1;
	}
	return 1;
}
