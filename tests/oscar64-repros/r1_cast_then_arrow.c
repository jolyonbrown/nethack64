/* OSCAR64 REPRO r1 - cast binds tighter than ->
 * NetHack: obj.h  #define ONAME(otmp) (((char *)(otmp)->oextra) + (otmp)->oxlth)
 * C says (char *)(p)->f casts the member; Oscar64 casts p then fails on ->.
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: tools/oscar_normalize.py rewrites to (char *)((p)->f).  Fixed by the
 * ADR-0007 compiler (commit 45, upstream 160c92b, 2026-11-14), which also covers casts
 * to non-pointer types, such as (int) (obj)->corpsenm.
 * FLAGS: -e
 */
struct obj { char *oextra; int oxlth; };
int main(void)
{
	struct obj o; char buf[4]; struct obj *p = &o;
	o.oextra = buf; o.oxlth = 1;
	return (int)(((char *)(p)->oextra) + (p)->oxlth - buf) == 1 ? 0 : 1;
}
