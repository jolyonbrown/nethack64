/* OSCAR64 REPRO r53 - `!` of a constant is not a constant in an initializer: "error
 * 3008: Constant initializer expected".  C89 3.4: `!0` is an integer constant
 * expression.  `static int k = !0;` and `{ "a", !0 }` in a static aggregate fail;
 * `(0 ? 0 : 1)` and `(0 == 0)` compile, and so does `!0` in code.
 * Cause: Expression::ConstantFold does not fold EX_LOGICAL_NOT (the comment on the r51
 * fix's FoldIntegerConstantExpression, Parser.cpp: "The general folder leaves logical
 * negation for code generation").  On v1.32.273, the pin and upstream main (16acc53).
 * NetHack: options.c 47, `{"ascii_map", &iflags.wc_ascii_map, !PREFER_TILED,
 * SET_IN_GAME}` in boolopt[], the file's first error under the C64 config (2026-11-14).
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: options.c writes `(PREFER_TILED ? FALSE : TRUE)`.
 * FLAGS: -e
 */
struct opt { const char *name; int def; };
static struct opt opts[] = { { "a", !0 }, { "b", !1 } };
static int k = !0;
int main(void)
{
	return opts[0].def == 1 && opts[1].def == 0 && k == 1 ? 0 : 1;
}
