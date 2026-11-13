/* OSCAR64 REPRO r42 - WRONG CODE: an unsigned char stored in a loop that provably runs at
 * least once reads back, behind the loop, as the int from before the narrowing (here as the
 * constant 0, taken from that int's range) instead of the byte that was stored
 * NetHack: no site found.  The pin and the fixed build give the same code for every
 * function in the 86 listings the harness keeps (47 files compile to the end, every stub
 * __noinline) but 3 of vision.c (other registers; one read by hand) and the library's
 * sformat, sscanf, fscanf (not read).  Not checked: the 60 other files; the signed form.
 * Found 2026-11-13 by the review of the pin candidates.
 * Cause: InterCodeGenerator::CoerceType narrows an int to a char by renaming the wide
 * temporary; nothing cuts the value.  Once the value ranges show that the loop body runs
 * (n is 1..4), InterCodeBasicBlock::LoadStoreForwarding forwards the read behind the loop
 * from the store and it gets the int's range: [-3..0] cut to [0..255] leaves 0, and
 * RebuildIntegerRangeSet folds f() to "return 0".  A bound whose inferred range includes
 * 0, a do-while and straight-line code are right.
 * Expect when fixed: emulation result 0.  Actual: v1.32.273 and the pin f001eba 1 in all
 * ten configurations (native and bytecode; default level, -O0, -O2, -Os, -O3).
 * Fix: upstream 57655c5 masks unsigned narrowing in CoerceType (main 4da3147: 0 in all
 * ten), but its mask also zeroes a pointer coerced to a conditional's type: main gets
 * "(c ? p : q) == m" wrong.  Local branch scratch/r42-backport-pin: that hunk, 23 lines,
 * for integer types only: 0 in all ten.  Not in the pin.  A signed char read this way
 * ("gs = 126 + (i & 3)") stays wrong, on main as well.
 * Workaround: none needed in NetHack.  "gv = -(i & 3) & 0xff;", a volatile gv or a read
 * as "*(volatile unsigned char *)&gv" give 0 in all ten on both; a cast does not help.
 * FLAGS: -e -Os
 */
unsigned char gv;

__noinline int f(unsigned char x)
{
	unsigned char i, n = (x & 3) + 1;	/* 1..4: the loop runs at least once */

	for (i = 0; i < n; i++)
		gv = -(i & 3);			/* int 0, -1, -2, -3: the byte stored is 0, 255, 254, 253 */
	return gv;
}

int main(void)
{
	int a = f(1), b = f(3);

	if (a != 255 || b != 253)
		return a == 0 && b == 0 ? 1 : 2;	/* 1: gv read as the constant 0 */
	return 0;
}
