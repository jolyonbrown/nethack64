/* OSCAR64 REPRO r55 - a storage class after a type qualifier, `const static int x;`,
 * is rejected: "error 3006: Declaration starts with invalid token 'static'".  C89 3.5
 * takes the declaration specifiers in any order (3.9.3 calls a storage class that is
 * not first obsolescent, not invalid); `static const` compiles.  At file scope and in
 * a block alike.
 * NetHack: version.c 125 (`const static struct version_info version_data` in
 * store_version()) and weapon.c 815 (`const static struct skill_range`), each file's
 * first error under the C64 config (2026-11-14).  On v1.32.273, the pin and upstream
 * main (16acc53).
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: tools/oscar_normalize.py writes `static const`.
 * FLAGS: -e
 */
const static struct ver { long a, b; } vd = { 1, 2 };
int f(void)
{
	const static int t = 3;
	return t;
}
int main(void)
{
	return vd.b == 2 && f() == 3 ? 0 : 1;
}
