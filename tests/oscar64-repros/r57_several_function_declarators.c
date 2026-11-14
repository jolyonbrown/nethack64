/* OSCAR64 REPRO r57 - a declaration with several function declarators,
 * `static void fa(void), fb(int), fc(void);`, makes the later calls fail: "error 3045:
 * Ambiguous function call 'fa'".  C89 3.5: each declarator declares its own function;
 * one declaration per function compiles.
 * NetHack: mkroom.c 21, `STATIC_DCL void NDECL(mkshop), FDECL(mkzoo,(int)),
 * NDECL(mkswamp);`, so that the call mkshop() at line 50 is the file's first error
 * (2026-11-14); the only such declaration in port/.  On v1.32.273, the pin and
 * upstream main (16acc53).
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: mkroom.c declares the three functions one per declaration.
 * FLAGS: -e
 */
static void fa(void), fb(int), fc(void);
int n;
int main(void)
{
	fa();
	fb(2);
	fc();
	return n == 7 ? 0 : 1;
}
static void fa(void) { n += 1; }
static void fb(int k) { n += k; }
static void fc(void) { n += 4; }
