/* OSCAR64 REPRO r16 - comparing a function pointer with a function name is rejected
 * NetHack: windows.c:113 `if (windowprocs.win_raw_print == def_raw_print)`, the first
 * error of windows.c under the C64 config.  C89 3.3.9: the operands of == may be
 * pointers to compatible types, and a function designator converts to a pointer.
 * Comparing two pointer variables, or a pointer with 0, works; `p == &f` fails too.
 * Expect when fixed: compiles, emulation result 0.  Actual: error 3013 "Incompatible
 * pointer types", at every optimisation level.
 * Workaround: none applied yet (TASKS T1.14).
 * FLAGS: -e
 */
static void f(const char *s)
{
	(void)s;
}
struct procs { void (*raw_print)(const char *); } w;
int main(void)
{
	w.raw_print = f;
	return w.raw_print == f ? 0 : 1;
}
