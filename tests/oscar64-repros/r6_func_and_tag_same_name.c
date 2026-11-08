/* OSCAR64 REPRO r6 - a function and a struct tag with the same name
 * NetHack: struct attack (permonst.h) + boolean attack(struct monst *) (uhitm.c)
 * Expect when fixed: compiles, emulation result 0.
 * FLAGS: -e
 */
struct foo { int a; };
int foo(int x) { return x; }
struct bar { int b; } bar;
int main(void)
{
	struct foo f; f.a = 1; bar.b = 2;
	return foo(f.a) + bar.b == 3 ? 0 : 1;
}
