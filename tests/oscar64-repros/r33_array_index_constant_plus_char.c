/* OSCAR64 REPRO r33 - WRONG CODE: k[c + n] always reads the last element when the array of
 * ints has exactly 2c + 1 elements (int k[3] with "char i = 1 + n; return k[i];")
 * NetHack: no site identified (port/ not searched exhaustively); found 2026-11-12 by the
 * review of the r28 fix (makemon-hang).  Exposed: any array of 2 or 4 byte elements (int,
 * long, pointers, structs) with 2c + 1 elements, indexed by a char computed as constant +
 * variable; reads and writes.
 * Cause: PeepholeReplaceOptimization rewrites "t1 = n + c; t2 = t1 << s; LEA t2, k" into
 * "t2 = n << s; LEA t2, k + (c << s)" and moves the value range of the LEA's operand down
 * by c << s, but not the range of the shift's result.  The next range pass intersects that
 * stale range ([2..4] here) with the new one ([0..2]) and gets [2..2]: f() returns k[2] for
 * every n, and the store to n is removed.  v1.32.273 and the eight-commit patched pin
 * (ADR-0007): every level but -O0, native and bytecode.
 * NOT fixed upstream: main 4da3147 passes the global form (bit 1) only because 57655c5
 * ("Fix wrapping byte index in addressing") masks an unsigned char index with 255 before
 * the shift, so the pattern does not match; the parameter form (bit 2; -O2, -Os, -O3) and
 * the signed form (bit 4; default level too) are still wrong there.  Fixed by
 * nethack64/pin-charidx (one line of ours, not an upstream commit, not proposed upstream
 * yet): candidate for the patched pin, Jolyon's decision pending (ADR-0007).
 * Expect when fixed: compiles, emulation result 0.  Actual: emulation result 7 (v1.32.273
 * and the pin), 6 (main 4da3147 at -O2, -Os, -O3), 4 (main at the default level).
 * Workaround: none applied yet (the candidate pin commit is the fix).  In source: an int
 * index ("int i = 1 + n;"), or an array one element longer.
 * FLAGS: -e -Os
 */
int k[3] = {1, 21, 5};
char n;
signed char sn;

__noinline void set(char v)
{
	n = v;
}

__noinline void sets(signed char v)
{
	sn = v;
}

__noinline int f(void)
{
	char i = 1 + n;
	return k[i];
}

__noinline int g(char m)
{
	char i = 1 + m;
	return k[i];
}

__noinline int h(void)
{
	signed char i = 2 + sn;
	return k[i];
}

int main(void)
{
	int r = 0;

	set(0);
	if (f() != 21) r |= 1;
	set(1);
	if (f() != 5) r |= 1;

	if (g(0) != 21) r |= 2;
	if (g(1) != 5) r |= 2;

	sets(-2);
	if (h() != 1) r |= 4;
	sets(-1);
	if (h() != 21) r |= 4;
	sets(0);
	if (h() != 5) r |= 4;

	return r;
}
