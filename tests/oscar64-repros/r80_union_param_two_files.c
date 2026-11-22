/* OSCAR64 REPRO r80 - A UNION PARAMETER IN A FUNCTION'S PROTOTYPE, SEEN IN TWO FILES, "DIFFERS".
 * Two translation units that both declare `int f(union u_s *p)` (as two files including one
 * header do) stop with "error 3025: Function declaration differs 'f'". Each unit parses its
 * own copy of the union, and Declaration::IsSame() compares union types only by identity:
 * a struct of the same tag and size is the same type there, a union never is. By value or
 * through a pointer, const or not, a typedef of it too. v1.32.273, the pin (87 commits),
 * upstream main 08b01c9 (2026-11-22).
 * NetHack: wintty.h's tty_add_menu() takes `const ANY_P *` (union any_s), and the C64 build
 * compiles the tty port (Phase 3): every file after the first that includes wintty.h.
 * Found 2026-11-22, measuring wintty.c, topl.c, getline.c in the C64 configuration.
 * Expect when fixed: compiles, "Emulation result 0".
 * Workaround: on the C64 only wintty.c, which defines and calls tty_add_menu() (every
 * other file calls it through windowprocs), sees its prototype (wintty.h, NH_WINTTY_C).
 * The second file is r80_union_param_two_files.inc (not a .c, so run.py takes it as no
 * repro of its own).
 * FLAGS: -e
 */
union u_s { int a; char b; };
int f(union u_s *p);

#pragma compile("r80_union_param_two_files.inc")

int main(void)
{
	union u_s u;

	u.a = 7;
	return f(&u) - 7;
}
