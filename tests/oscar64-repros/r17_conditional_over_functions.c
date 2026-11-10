/* OSCAR64 REPRO r17 - `c ? f : g` over two functions gets the wrong type
 * NetHack: do.c:688 `query_objlist(..., all_categories ? allow_all : allow_category)`,
 * the first error of do.c under the C64 config.  C89 3.3.15: both operands convert to
 * pointers to the same function type, and so does the result.  Oscar64 types the
 * result as a pointer to the return type, so it does not match a function-pointer
 * parameter (with void functions it becomes void * and happens to fit).
 * NetHack's functions return boolean (signed char); this repro uses int so that it does
 * not also depend on r18.
 * Expect when fixed: compiles, emulation result 0.  Actual: error 3012 "Cannot assign
 * incompatible types 'i16(*)(struct o*)*' != 'i16*'", at every optimisation level;
 * `&fa : &fb` fails the same way.
 * Workaround: none applied yet (TASKS T1.14).  Choosing the function into a pointer
 * variable first compiles, but for NetHack's boolean functions the call through the
 * pointer then hits r18.
 * FLAGS: -e
 */
struct o { int x; };
static int fa(struct o *p) { return p->x + 1; }
static int fb(struct o *p) { return p->x + 2; }
static int call(int (*fn)(struct o *))
{
	struct o v;
	v.x = 0;
	return fn(&v);
}
volatile int k;
int main(void)
{
	return call(k ? fa : fb) == 2 ? 0 : 1;
}
