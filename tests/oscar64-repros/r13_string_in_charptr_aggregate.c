/* OSCAR64 REPRO r13 - a string literal cannot initialise a `char *` element of an aggregate
 * NetHack: mail.c `static char *junk[] = { "Please disregard previous letter.", ... }`,
 * mail.c's first error under the C64 config.  In C a string literal has type char[N],
 * so it may initialise a `char *`; Oscar64 accepts `const char *junk[]` and a scalar
 * `char *q = "a";`, but not a `char *` array element or struct member.
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
