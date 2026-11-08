/* OSCAR64 REPRO r11 - K&R (old-style) function definitions are not accepted
 * NetHack 3.4.3 defines all ~2,350 functions this way.  This one is by design
 * (Oscar64 targets C99), so it is listed for completeness, not as a bug.
 * Workaround: tools/kr2ansi.py + tools/ansi_manual_fixes.py convert the source.
 * FLAGS: -e
 */
int add(int, int);
int
add(a, b)
int a, b;
{
	return a + b;
}
int main(void) { return add(2, 3) == 5 ? 0 : 1; }
