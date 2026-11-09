/* OSCAR64 REPRO r12 - a braced initializer for a scalar is rejected once the variable is used
 * NetHack: decl.c `const char *occtxt = DUMMY;` (hack.h: #define DUMMY { 0 }); the
 * harness reports it at decl.h(193) as allmain.c's first error under the C64 config.
 * C89 3.5.7: "The initializer for a scalar shall be a single expression, optionally
 * enclosed in braces."  Unreferenced, the same definition compiles.
 * Expect when fixed: compiles, emulation result 0.  Actual: error 3008 "Non constant
 * initializer".
 * Workaround: none applied yet (would be `= 0` in decl.c; see OSCAR64-COMPAT.md).
 * FLAGS: -e
 */
const char *p = { 0 };
int main(void)
{
	return p == 0 ? 0 : 1;
}
