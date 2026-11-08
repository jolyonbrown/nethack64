/* OSCAR64 REPRO r1 - cast binds tighter than ->
 * NetHack: obj.h  #define ONAME(otmp) (((char *)(otmp)->oextra) + (otmp)->oxlth)
 * C says (char *)(p)->f casts the member; Oscar64 casts p then fails on ->.
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: tools/oscar_normalize.py rewrites to (char *)((p)->f).
 * FLAGS: -e
 */
struct obj { char *oextra; int oxlth; };
int main(void)
{
	struct obj o; char buf[4]; struct obj *p = &o;
	o.oextra = buf; o.oxlth = 1;
	return (int)(((char *)(p)->oextra) + (p)->oxlth - buf) == 1 ? 0 : 1;
}
