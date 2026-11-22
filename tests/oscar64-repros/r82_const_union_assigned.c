/* OSCAR64 REPRO r82 - A CONST UNION CANNOT BE ASSIGNED TO A UNION OF ITS TYPE.
 * `dst = *src` with `const union u_s *src` stops with "error 3012: Cannot assign
 * incompatible types 'union u_s' != 'const union u_s'". C89 3.3.16.1: the right operand's
 * qualifiers don't matter in an assignment (the value is copied); the same code with a
 * struct compiles and is right. The union kin of r80: Oscar64 compares unions by less
 * than it compares structs by. The pin (87 commits), 2026-11-22; upstream main not built.
 * NetHack: wintty.c's tty_add_menu(), `item->identifier = *identifier` (an `anything`, the
 * menu item's identifier), in the C64 build since Phase 3.
 * Found 2026-11-22, measuring wintty.c in the C64 configuration.
 * Expect when fixed: compiles, "Emulation result 0".
 * Workaround: the const cast away, `*(anything *) identifier` (wintty.c, a comment
 * pointing here).
 */
union u_s { int a; char b; };

union u_s dst;

int put(const union u_s *src)
{
	dst = *src;
	return dst.a;
}

int main(void)
{
	union u_s v;

	v.a = 5;
	return put(&v) - 5;
}
