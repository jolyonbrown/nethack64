/* OSCAR64 REPRO r56 - a case or default label inside a block nested in the switch body
 * is rejected: "error 3006: Term starts with invalid token 'default'".  C89 3.6.1 and
 * 3.6.4.2: a case or default label may be on any statement within the switch body
 * (Duff's device puts them inside a do-while).
 * Cause: Parser::ParseSwitchStatement recognises case and default only directly in
 * the switch body; anywhere deeper ParseStatement takes them for the start of an
 * expression.  On v1.32.273, the pin and upstream main (16acc53).
 * NetHack: trap.c 1255 in steedintrap(): the braces of the POLY_TRAP case leave the
 * default: label inside its `if (!resists_magm(mtmp)) {` block (as in upstream 3.4.3),
 * the file's first error (2026-11-14).
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: trap.c moves the label after the block, with a break where the block
 * used to end the switch.
 * FLAGS: -e
 */
int f(int t, int c)
{
	int hit = 0;
	switch (t) {
	case 1:
		hit = 1;
		break;
	case 2:
		if (c) {
			hit = 2;
			break;
		default:
			return -1;
		}
	}
	return hit;
}
int main(void)
{
	return f(1, 0) == 1 && f(2, 1) == 2 && f(2, 0) == 0 && f(9, 0) == -1 ? 0 : 1;
}
