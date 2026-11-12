/* OSCAR64 REPRO r30 - WRONG CODE: a value stored into a local array (or struct) element is
 * forwarded to a later read although one path overwrites the element in between
 * NetHack: no site identified yet (not searched).  Found 2026-11-12 while testing the fix
 * for r29: a regression test for the same family of walks failed in the emulator with
 * v1.32.273.
 * Cause: CheckSingleUseGlobalLoadStruct (native code optimiser) marks each block it has
 * checked.  A block first reached on the path behind the overwrite is not checked again
 * when the path without the overwrite reaches it, so the store "t[0] = arr[k]" is removed
 * and the read at the end uses arr[k] or the stale register.  Fixed upstream by 3bb084f
 * (2026-10-18) and 1073206 (2026-10-19); neither is in v1.32.273 (upstream main 4da3147
 * passes).  Native code at -O1 and above; -O0 and bytecode are right.
 * Expect when fixed: emulation result 0.  Actual (v1.32.273 and the eight-commit patched
 * pin, default level, -O1, -O2, -O3, -Os): emulation result 37 (f(2) returns 37, not 38).
 * Fixed by nethack64/pin-r30, candidate for the patched pin, Jolyon's decision pending
 * (ADR-0007): the two upstream commits (they are enough for this file) plus a fix for the
 * second one, which made the check exponential in the number of conditionals behind the
 * overwrite, and endless (compiler stack overflow) when a loop that does not store to the
 * element follows it (PR #16 in docs/OSCAR64-UPSTREAM.md carries that fix for upstream
 * main).
 * Workaround: none applied yet.
 * FLAGS: -e -Os
 */
char arr[8] = {10, 20, 30, 40, 50, 60, 70, 80};
char fl[64], cb = 5;
int acc;

__noinline int use(char * p)
{
	return p[0] + p[1];
}

__noinline void bump(void)
{
	acc++;
}

__noinline int f(char k)
{
	char t[4];
	int r = 0;
	char i;

	t[1] = 1;
	t[0] = arr[k];
	if (fl[63]) { r = use(t); t[0] = cb; r += use(t); }
	for (i = 0; i < k; i++) { if (fl[i + 8]) t[0] = i; bump(); }
	return r + t[0];
}

int main(void)
{
	int v;

	if (f(2) != 30)
		return 1;
	fl[63] = 1;
	fl[9] = 1;
	v = f(2);
	if (v != 31 + 6 + 1)
		return v;
	if (f(1) != 21 + 6 + 5)
		return 3;
	return 0;
}
