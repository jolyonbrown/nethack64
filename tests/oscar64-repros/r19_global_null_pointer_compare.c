/* OSCAR64 REPRO r19 - WRONG CODE: a file-scope pointer initialised to 0 compares as non-null
 * NetHack: file-scope pointers initialised to 0 or (T *)0, later tested with == 0 or != 0
 * (exposure not counted yet).  Found 2026-11-12 by the agent fixing r12.
 * At -O2, -Os and -O3, native and bytecode, `p == 0` is false and `p != 0` is true although
 * p holds 0, so the program returns 1.  -O0 and -O1 are correct.  The same holds for
 * `= (char *)0`, `= (void *)0`, a function-scope static and a function pointer, and in
 * `if`, `?:`, `&&`, `while` and `int r = (p == 0)`.  Correct: `if (!p)`, `if (p)`,
 * `p == (char *)0`, `p == NULL` (Oscar64's NULL is nullptr), a pointer without an
 * initialiser, an int initialised to 0, and elements of a pointer array initialised to 0.
 * Also wrong (found by the upstream fix's review): `!p` used as a value, `int r = !p;`
 * (at -O2/-Os/-O3; `!(char *)0` at every level), and `0 == n` for a pointer initialised
 * to `&c`, which comes out true at -O2/-Os/-O3.
 * Seen on v1.32.273 and on upstream main 4da3147.
 * Expect when fixed: compiles, emulation result 0.  Actual at -Os: emulation result 1.
 * Workaround: none applied yet.  In a condition, comparing with a cast null `(T *)0`, or
 * writing `if (!p)`, gives correct code (see OSCAR64-COMPAT.md).
 * FLAGS: -e -Os
 */
char *p = 0;
int main(void)
{
	if (p == 0)
		return 0;
	return 1;
}
