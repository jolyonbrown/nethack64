/* OSCAR64 REPRO r51 - a conditional whose operands are a pointer and the null pointer
 * constant 0, `c ? p : 0` or `c ? 0 : p`, is rejected: "error 3013: Incompatible
 * conditional types".  C89 3.3.15: with one operand a pointer and the other a null
 * pointer constant, the result has the pointer's type.  `c ? p : (void *)0` and
 * `c ? p : (struct s *)0` compile; `0L` is rejected too.  Every context fails: return
 * value, initializer, assignment, argument.
 * NetHack: the first compile error of pray.c (649: `obj = ok_wep(uwep) ? uwep : 0;`),
 * muse.c (672), shk.c (693) and mon.c (1613) once T1.10-T1.35 had moved them on
 * (2026-11-14), and of more files before (OSCAR64-COMPAT.md's error classes).
 * Cause: InterCodeGenerator.cpp (around line 5254 in the pin) reports the error
 * whenever only one operand has a pointer base type, without allowing for a null
 * pointer constant.  On v1.32.273, the pin (42 commits) and upstream main 16acc53.
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: none in port/; fixed by the ADR-0007 compiler (commits 46-47, Codex's fix
 * and test, 2026-11-14).
 * FLAGS: -e
 */
struct s { int x; };
struct s a, *q = &a;

struct s *pick(int c)
{
	return c ? q : 0;
}

struct s *pick_swapped(int c)
{
	return c ? 0 : q;
}

int main(void)
{
	return pick(1) == q && pick(0) == 0 && pick_swapped(0) == q && pick_swapped(1) == 0 ? 0 : 1;
}
