/* OSCAR64 REPRO r61 - REJECTS VALID C: the name of a function-like macro is expanded
 * even when no `(` follows it: "error 3068: Missing arguments for macro expansion".  In
 * C only the name followed by `(` invokes the macro (C89 3.8.3, C99 6.10.3p10); the name
 * alone is an ordinary identifier, here a struct member and a function used as a
 * pointer.  Cause: Scanner.cpp's macro expansion reads the next token and reports the
 * error when it is not `(`, instead of leaving the name as it is.  On v1.32.273, the pin
 * (59 commits) and upstream main (16acc53), checked 2026-11-15.
 * NetHack: nothing in the game's own source (all 108 files compile), but it stops the
 * bank generator's renaming macros (tools/bank/bankgen.py, `#define f(...)
 * f__bN(__VA_ARGS__)`) wherever f is also a struct member (botl.c: `role->rank[i]`) or
 * a function passed as a pointer.
 * Expect when fixed: compiles, emulation result 0 (gcc: exit 0).
 * Workaround: bankgen.py renames banked definitions in the text and defines a bank's
 * macro for f only in runs of code where f never appears without `(`; calls there go
 * through f's trampoline.
 * FLAGS: -e -Os
 */
int g(int x) { return x + 1; }
int g2(int x) { return x + 2; }
int (*fp)(int);
#define g(...) g2(__VA_ARGS__)
struct s { int g; };

int main(void)
{
	struct s v;
	v.g = 1;			/* the member, not the macro */
	fp = g;				/* the function g, not the macro */
	return fp(v.g) + g(v.g) - 5;	/* g(1) through the pointer is 2, the macro's g2(1) is 3 */
}
