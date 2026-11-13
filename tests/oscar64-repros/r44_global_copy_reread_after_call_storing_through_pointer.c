/* OSCAR64 REPRO r44 - WRONG CODE: a copy of a global is read from the global again behind
 * a call that stores to it through a pointer: "old = g; set(&g, 0); return !g && old;"
 * tests !g && g
 * NetHack: one site found, make_hallucinated() (potion.c:229-248): behind
 * set_itimeout(&HHallucination, xtime) "old" is tested as HHallucination itself, so the
 * messages for hallucination ending without a change of vision never appear (v1.32.273,
 * the pin; harness listings, not run: the harness takes every extern function's address;
 * without that the pin inlines set_itimeout here, right).  Method: r37 fix build against
 * this fix, 107 port/src files, -Os, stubs __noinline: in the 47 that reach code
 * generation two functions differ; rigid_role_checks() was right before.  Not checked:
 * the other 60 files; callees in other files (stubs store nothing).
 * Found 2026-11-13 by the verifier of the r37 fix.
 * Cause: CheckGlobalAliasing counts stores in the absolute modes, not "STA (zp),y", so
 * NativeCodeProcedure::Compile flags a function that stores only through pointers
 * LOBJF_NO_GLOBAL_STORES; CheckSingleUseGlobalLoad walks past a JSR to it, and
 * PatchSingleUseGlobalLoad turns the read of the copy behind it into a read of the global.
 * A non-recursive function's locals are static too: h().
 * Expect when fixed: emulation result 0.  Actual, native only (bytecode gives 0): v1.32.273
 * and the pin f001eba 7 at all five levels; upstream main 4da3147 7 at four, 3 at -O0.
 * Fix (TASKS T1.23): ours, one condition, local branch scratch/r44-fix-pin (8890301, on
 * top of the r37 fix): 0 in all ten.  Not in the pin, not proposed upstream.
 * Workaround: the callee also stores to a volatile global (0 in all ten, main too); or
 * read the copy through a volatile lvalue, "*(volatile long *)&g": 0 in all ten for f(),
 * g() on v1.32.273 and the pin (keeps "old" at potion.c:229); for h() only
 * "*(volatile char *)t" ("&t[0]": 4); on main h() stays 4.
 * FLAGS: -e -Os
 */
struct you { char ux, uy; };
struct you u = {5, 6};
long prop[2] = {5, 9};
char src[4] = {10, 20, 30, 40};

/* Each callee has two different callers, so its pointer stays a parameter. */
__noinline void set_itimeout(long * which, long val)
{
	*which = val;
}

__noinline void bump(char * p)
{
	p[0] += 100;
}

/* make_hallucinated(): "clearing temporary hallucination without toggling vision" */
__noinline char f(void)
{
	long old = prop[0];

	set_itimeout(&prop[0], 0);
	return !prop[0] && old;
}

__noinline char g(void)
{
	char ox = u.ux;

	bump(&u.ux);
	return ox != u.ux;
}

__noinline char h(char k)
{
	char t[2];
	char old;

	t[1] = 1;
	t[0] = src[k];
	old = t[0];
	bump(t);
	return old;
}

int main(void)
{
	int e = 0;

	set_itimeout(&prop[1], 3);
	if (!f()) e |= 1;
	if (!g()) e |= 2;
	if (h(1) != 20 || h(0) != 10) e |= 4;
	if (prop[0] != 0 || prop[1] != 3 || u.ux != 105) e |= 8;
	return e;
}
