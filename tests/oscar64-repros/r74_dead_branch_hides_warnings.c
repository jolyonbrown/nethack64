/* OSCAR64 REPRO r74 - LOST DIAGNOSTICS: a function first reached from a branch the compiler
 * knows is dead is translated with warnings off, and so is every function first reached
 * from it.  Here `g`'s warning 2014 (numeric 0 used for nullptr) is printed when main's
 * `if (0) f();` is removed or made `if (gp)`, and not with it: main's dead branch calls `f`,
 * whose intermediate code (and its callee `g`'s) is generated while the branch's errors are
 * held back (InterCodeGenerator, `SetMinLevel(EERR_GENERIC)` for an always false `if`); when
 * main then calls `g` itself, `g` is translated already.  Errors are still reported.
 * v1.32.273, the pin (80 commits), upstream 4da3147.
 * NetHack: the whole-game builds print no warning from code generation at all (no 2014,
 * no 2026), where per-file compiles of the same sources print them: T2.12's far pointer
 * check (warning 2026) is silent in the build it is meant to guard.  Found 2026-11-18
 * looking for restore.c 742's warning 2026 in the whole build.
 * Expect when fixed: warning 2014 at g (the program exits 1 either way: only the warning counts).
 * Workaround: per-file compiles (tools/measure/measure_oscar64.py) for the warnings.
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
