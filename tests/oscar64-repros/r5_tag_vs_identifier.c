/* OSCAR64 REPRO r5 - struct tags share the ordinary identifier namespace
 * NetHack: 369 x `struct obj *obj` parameters; also struct attack + attack(),
 * struct mkroom + mkroom(), `struct mvitals {...} mvitals[]`.
 * In C the tag namespace is separate; here a later `struct obj *otmp` in the
 * scope of a variable named obj fails with "Struct expected".
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: tools/oscar_normalize.py renames the colliding tags (obj -> obj_s ...).
 * FLAGS: -e
 */
struct obj { struct obj *nobj; int v; };
int f(struct obj *obj)
{
	struct obj *otmp;
	int s = 0;
	for (otmp = obj; otmp; otmp = otmp->nobj)
		s += otmp->v;
	return s;
}
int main(void)
{
	struct obj a, b;
	a.nobj = &b; b.nobj = 0; a.v = 1; b.v = 2;
	return f(&a) == 3 ? 0 : 1;
}
