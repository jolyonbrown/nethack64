/* OSCAR64 REPRO r67 - REJECTS VALID C: a macro whose replacement names the macro itself,
 * `#define value (value + 1)`, fails with error 4002 "Maximum macro expansion depth exceeded"
 * instead of expanding once: C99 6.10.3.4 says the macro's own name found while rescanning
 * its replacement is not replaced again (it then refers to the variable).  v1.32.273 and the
 * pin.  NetHack: none (it has no such macro); found 2026-11-16 in the speed harness's far
 * build (tools/measure/speed/far_post.h), which redefined `mons` in terms of itself.
 * Expect when fixed: compiles, exit 0.
 * Workaround: give the object another name, and define the macro in terms of that
 * (the far build compiles with -dmons=nh_mons_real).
 * FLAGS: -e
 */
int value = 5;
#define value (value + 1)

int main(void)
{
	return value == 6 ? 0 : 1;
}
