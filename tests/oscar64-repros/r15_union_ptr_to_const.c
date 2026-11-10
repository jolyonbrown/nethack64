/* OSCAR64 REPRO r15 - a `union T *` does not convert to `const union T *`
 * NetHack: every `add_menu(win, glyph, &any, ...)` (87 calls): `anything any;` passed to
 * the `const ANY_P *` parameter of windowprocs.win_add_menu.  The first error of apply.c
 * and spell.c (both configs) and of pager.c (C64 config).  C89 3.3.16.1 and 3.3.2.2: a
 * pointer may gain qualifiers in an assignment or as an argument.  Oscar64 allows that
 * for struct and scalar pointers, but Declaration::IsSubType returns false for unions.
 * Fails in assignments and initialisations too, at every optimisation level (at -Os an
 * unused parameter skips the check).
 * Expect when fixed: compiles, emulation result 0.  Actual: error 3012 "Cannot assign
 * incompatible types 'const union u*' != 'union u*'".
 * Workaround: none applied yet.  An explicit cast compiles; one cast inside winprocs.h's
 * add_menu macro would cover every call (TASKS T1.8).
 * FLAGS: -e
 */
union u { int i; char c; };
static int get(const union u *p)
{
	return p->i;
}
int main(void)
{
	union u v;
	v.i = 0;
	return get(&v);
}
