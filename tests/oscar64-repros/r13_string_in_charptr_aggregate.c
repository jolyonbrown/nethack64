/* OSCAR64 REPRO r13 - a string literal cannot initialise a `char *` element of an aggregate
 * NetHack: mail.c `static char *junk[] = { "Please disregard previous letter.", ... }`,
 * mail.c's first error under the C64 config.  In C a string literal has type char[N],
 * so it may initialise a `char *`.  Oscar64 types it `const char[N]`, so it never
 * converts to a non-const `char *`: not in an aggregate (this repro, even unreferenced),
 * a local initializer, an assignment or a `char *` argument (error 3012), at every
 * optimisation level.  A file-scope scalar `char *q = "a";` passes only where -O2/-Os
 * fold it away.  `const char *`, a `(char *)` cast and `return "a"` work.  gcc
 * -Wwrite-strings over the C64 view (host headers, 2026-11-10) flags only mail.c's junk[].
 * Expect when fixed: compiles, emulation result 0.  Actual: error 3008 "Incompatible
 * constant initializer".
 * Workaround: none applied yet (would be `const char *` where the strings are never
 * written; see OSCAR64-COMPAT.md).
 * FLAGS: -e
 */
static char *junk[] = { "ab", "c" };
int main(void)
{
	return junk[0][1] == 'b' && junk[1][0] == 'c' ? 0 : 1;
}
