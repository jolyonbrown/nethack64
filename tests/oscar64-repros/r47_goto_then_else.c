/* OSCAR64 REPRO r47 - an `else` after a braceless `if (c) goto label;` is rejected:
 * "error 3006: Term starts with invalid token 'else'".  break, continue and return
 * in the same place are fine, and braces around the goto make it compile.
 * NetHack: 10 sites in 8 port/src files (artifact.c, bones.c, detect.c x3, hack.c,
 * mklev.c, objnam.c, shk.c, sp_lev.c); objnam.c stopped here once T1.30 had moved
 * its first error on (2026-11-14).
 * Cause: Parser::ParseStatement's TK_GOTO case returns without consuming the ';'
 * (TK_BREAK and TK_CONTINUE call ConsumeToken(TK_SEMICOLON)).  In a block the ';'
 * then parses as an empty statement, but after an if's then-branch the parser finds
 * ';' where it looks for else, ends the if, and the else starts a statement of its
 * own.  On v1.32.273, the pin and upstream main (16acc53, 2026-11-14).
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: tools/oscar_normalize.py wraps such a goto in braces.
 * FLAGS: -e
 */
int f(int a)
{
	if (a > 1) goto done;
	else a = 7;
done:
	return a;
}

int main(void) { return f(0) == 7 && f(5) == 5 ? 0 : 1; }
