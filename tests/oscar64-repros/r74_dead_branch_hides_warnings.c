/* OSCAR64 REPRO r74 - LOST DIAGNOSTICS: a function first reached from a branch the compiler
 * knows is dead is translated with warnings off, and so is every function first reached
 * from it.  Here `g`'s warning 2014 (numeric 0 used for nullptr) is printed when main's
 * `if (0) f();` is removed or made `if (gp)`, and not with it: main's dead branch calls `f`,
 * whose intermediate code (and its callee `g`'s) is generated while the branch's errors are
 * held back (InterCodeGenerator, `SetMinLevel(EERR_GENERIC)` for an always false `if`); when
 * main then calls `g` itself, `g` is translated already.  Errors are still reported.
 * v1.32.273, the pin (80 commits), upstream 4da3147.
 * NetHack: none measured; the whole far game prints the same 5,358 diagnostics with and
 * without the fix (2026-11-18).  Found looking for restore.c 742's warning 2026, missing
 * from the whole-game logs because their wrapper dropped warning lines, not because of this.
 * Expect when fixed: warning 2014 at g (the program exits 1 either way: only the warning counts).
 * Workaround: none needed for NetHack.
 * FLAGS: -e
 * DIAGNOSTIC: 2014
 */
char *gp;

__noinline void g(void)
{
	gp = 0;
}

__noinline void f(void)
{
	g();
}

int main(void)
{
	if (0)
		f();
	g();
	return 1;
}
