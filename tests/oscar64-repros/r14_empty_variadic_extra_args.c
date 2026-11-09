/* OSCAR64 REPRO r14 - at -Os, calling an empty variadic function with extra arguments fails
 * NetHack: only the measurement harness hits it.  tools/measure/mkstubs.py writes empty
 * stubs such as `void You(const char *s, ...) {}`; at -Os every call with arguments
 * after the format fails: the first error of fountain.c (both configs) and of
 * questpgr.c and topten.c (C64 config).  The game's real variadic functions use
 * va_start/va_arg and compile.  Accepted at -O0.
 * Expect when fixed: compiles, emulation result 0.  Actual: error 3017 "Too many
 * arguments for function call".
 * Workaround: none needed in the game; the harness should give variadic stubs a
 * va_start body (TASKS T1.10).
 * FLAGS: -e -Os
 */
#include <stdarg.h>
void say(const char *s, ...) {}
int main(void)
{
	say("%d", 3);
	return 0;
}
