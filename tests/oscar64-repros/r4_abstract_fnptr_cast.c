/* OSCAR64 REPRO r4 - cast to a function-pointer type with an abstract declarator
 * NetHack: apply.c  (int FDECL((*),(MONST_P,OBJ_P)))0  ->  (int (*)(struct monst *, struct obj *))0
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: tools/oscar_normalize.py drops casts of literal 0 (null pointer constant).
 * FLAGS: -e
 */
struct monst; struct obj;
int main(void)
{
	int (*fp)(struct monst *, struct obj *) = (int (*)(struct monst *, struct obj *))0;
	return fp ? 1 : 0;
}
