/* OSCAR64 REPRO r23 - WRONG CODE: a call through a function-pointer member of a global
 * struct is missing from the call graph, so the callee's frame overwrites the caller's
 * live locals
 * NetHack: every window call, `(*windowprocs.win_putstr)(...)` and the 43 other macros in
 * winprocs.h (windowprocs is a global struct of function pointers).  Found 2026-11-12 by
 * the agent fixing the upstream function-pointer-member regression (fix/fnptr-member).
 * GlobalAnalyzer unwraps `w.fn` (folded to a reference into w) to the variable w, so no
 * call edge from caller() to callee() is recorded.  With the native back end the frames
 * of callee() and helper() are then placed over caller()'s locals l1..l4.  Fails with
 * native code at every level, -O0 included (Oscar64's default back end is native, and
 * nethack64 builds with -Os -g); bytecode (-bc) is correct.  The same for an array of
 * structs (s[1].fn) and a nested struct (o.in.fn); a plain global function pointer and a
 * call through p->fn are correct.  On v1.32.273; upstream main 4da3147 rejects the
 * program (the separate 349b10a regression that fix/fnptr-member also fixes).
 * Expect when fixed: compiles, emulation result 0.  Actual at -Os: emulation result 1.
 * Workaround: none applied yet.
 * FLAGS: -e -Os
 */
struct procs { int (*fn)(int a, int b); } w;

__noinline int helper(int a, int b, int c, int d)
{
	int t[4];
	t[0] = a * 3; t[1] = b * 5; t[2] = c * 7; t[3] = d * 11;
	return t[0] + t[1] + t[2] + t[3];
}

__noinline int callee(int a, int b)
{
	int u = a + 100, v = b + 200, s = u * v;
	return helper(u, v, s, a ^ b) + s;
}

__noinline int caller(int x, int y)
{
	int l1 = x * 13, l2 = y * 17, l3 = x * y + 19, l4 = x - y;
	int r = w.fn(x, y);
	return l1 + l2 + l3 + l4 + r;
}

static int expected(int x, int y)
{
	int u = x + 100, v = y + 200, s = u * v;
	return x * 13 + y * 17 + (x * y + 19) + (x - y) + (u * 3 + v * 5 + s * 7 + (x ^ y) * 11) + s;
}

int main(void)
{
	w.fn = callee;
	for (int i = 0; i < 5; i++)
		if (caller(i, 2 * i + 1) != expected(i, 2 * i + 1))
			return 1;
	return 0;
}
