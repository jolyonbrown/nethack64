/* OSCAR64 REPRO r14 - an empty variadic function called with constant extra arguments fails
 * NetHack: only the measurement harness hits it.  tools/measure/mkstubs.py writes empty
 * stubs such as `void You(const char *, ...) {}`.  A body with no side effects (empty,
 * or only va_start/va_end) makes the call constant-folded, and the inliner has no
 * variadic case, so a call whose arguments are all constants fails: the first error of
 * fountain.c (both configs) and of questpgr.c and topten.c (C64 config).  Fails at every
 * level except -O0; a call with a run-time argument compiles.  The game's real variadic
 * functions use va_arg and compile.
 * Expect when fixed: compiles, emulation result 0.  Actual: error 3017 "Too many
 * arguments for function call".
 * Workaround: none needed in the game.  The harness's variadic stubs need a body with a
 * side effect, e.g. `nh_vl = 0;` (TASKS T1.10; checked in a scratch harness 2026-11-10).
 * FLAGS: -e -Os
 */
#include <stdarg.h>
void say(const char *s, ...) {}
int main(void)
{
	say("%d", 3);
	return 0;
}
