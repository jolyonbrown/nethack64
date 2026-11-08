/* OSCAR64 REPRO r2 - unparenthesised nested conditional in the middle operand
 * NetHack: pray.c  u.ualign.record >= DEVOUT ? Hallucination ? "a" : "b" : ...
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: add parentheses by hand (few sites).
 * FLAGS: -e
 */
int main(void)
{
	int a = 1, b = 0, c = 1;
	const char *s = a ? b ? "x" : "y" : c ? "z" : "w";
	return s[0] == 'y' ? 0 : 1;
}
