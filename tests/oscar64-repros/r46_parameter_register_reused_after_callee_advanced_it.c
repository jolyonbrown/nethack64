/* OSCAR64 REPRO r46 - WRONG CODE: after sscanf("abc", ...) a later call that passes the
 * same literal gets the pointer sscanf left in the parameter register, so
 * strcmp(s, "abc") compares s with the end of "abc" and reports a difference
 * NetHack: not searched yet (TASKS T1.27).  Its sscanf calls (cmd.c, files.c) read from
 * buffers, not literals; the general shape is a callee that advances its own pointer
 * parameter through its address while the caller keeps using the register.
 * Mechanism, from the -n -Os listing: main puts the literal's address in P2/P3 for
 * sscanf, whose scanner advances the pointer in P2/P3 through &str; for strcmp main
 * loads P0/P1 only and keeps P2/P3 as the literal.  The r44 fix (#46: stores through a
 * pointer counted as stores) does not change it.
 * Found 2026-11-13 by Codex while reviewing the r42 fix (its scanf test suite); checked
 * the same day.
 * Expect when fixed: emulation result 0 (2 would mean the scan itself went wrong).
 * Actual: 1 with native code at -Os only, on v1.32.273, the pin (f001eba, b4dc4eb), the
 * r44 fix build and upstream main 4da3147; 0 at the default level, -O0, -O2, -O3, and 0
 * in bytecode at every level.
 * Workaround: none needed in port/ yet (T1.27).  In a test, compare the bytes directly.
 * FLAGS: -e -n -Os
 */
#include <stdio.h>
#include <string.h>

char s[8];

int main(void)
{
	int r;
	memset(s, 81, 8);
	r = sscanf("abc", "%s", s);
	if (r != 1 || s[0] != 'a' || s[1] != 'b' || s[2] != 'c' || s[3] != 0 || s[4] != 81)
		return 2;
	return strcmp(s, "abc") != 0;
}
