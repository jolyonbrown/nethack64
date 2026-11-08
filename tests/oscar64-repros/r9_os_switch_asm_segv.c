/* OSCAR64 REPRO r9 - the compiler itself segfaults with -Os
 * (v1.32.273; -O1 and -O2 compile it fine).  Found in src/hal/sys.c.
 * A switch-based helper called from a function that takes its value from
 * an inline-asm block.  Expect when fixed: exit status 0 from the compiler.
 * Workaround: sys.c uses a lookup table instead of the switch.
 * FLAGS: -Os
 * COMPILE-ONLY
 */
static char conv(char c)
{
	switch (c)
	{
	case 13:  return '\n';
	case 20:  return 8;
	case 3:   return 27;
	case 95:  return 27;
	case 17:  return 'j';
	case 145: return 'k';
	case 29:  return 'l';
	case 157: return 'h';
	}
	if (c >= 65 && c <= 90)
		return c + 32;
	if (c >= 193 && c <= 218)
		return c - 128;
	if (c >= 97 && c <= 122)
		return c - 32;
	return c;
}
char getkey(void)
{
	char c = __asm {
		jsr $ffe4
		sta accu
	};
	if (!c)
		return 0;
	return conv(c);
}
int main(void) { return getkey(); }
