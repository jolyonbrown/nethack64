/* Compiler segfault (exit 139) with -n at the default level, -O2 and -Os on v1.32.273,
 * upstream main 4da3147 and the proposed patched pin: a loop over a const struct table
 * comparing a function-pointer member with a const function pointer.  Found 2026-11-12 by
 * the review of the patched pin.  NetHack compares such members with function names
 * (cmd.c:292), a shape not seen to crash; not a nethack64 repro. */
__noinline int donull(void) { return 1; }
__noinline int doredraw(void) { return 0; }
struct func_tab { char f_char; int (*f_funct)(void); };
const struct func_tab cmdlist[] = { {'.', donull}, {'R', doredraw}, {0, 0} };
int (* const dn)(void) = donull;
volatile int vi = 1;
int main(void)
{
	int n = 0;
	for (const struct func_tab *p = cmdlist; p->f_char; p++)
		if (p->f_funct == dn) n++;
	return n == 1 ? 0 : 1;
}
