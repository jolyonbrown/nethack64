/* OSCAR64 REPRO r41 - COMPILER ABORT: a loop reads a global and then stores to it a value
 * the loop needs from before its first round (here the parameter that is also the bound)
 * NetHack: no site found.  A pin build that logs the step (control: this file) saw it
 * rewrite 4 reads in the 44 files that reach code generation in the harness (strncpy in
 * Oscar64's string.c, free_ttlist in topten.c), none in either bad form.  Not checked:
 * the 63 files that fail to compile, and src/.
 * Found 2026-11-13 while mapping the triggers of r36.
 * Cause: for a one-block loop without calls that reads a global and later stores temporary
 * t to it, InterCodeBasicBlock::SingleBlockLoopOptimisation ("check forwarding globals")
 * keeps the global in t: the read moves in front of the loop with t as its destination,
 * the store behind the loop.  It tests that t is not read in front of the read and not
 * changed behind the store.  That the loop does not need the value t has on entry is only
 * asserted (f: t is n); an assignment to t in front of the read is not looked for (g).
 * Expect when fixed: emulation result 0.  Actual, native and bytecode, v1.32.273, the pin
 * f001eba and upstream main 4da3147: 0 at -O0; at the default level, -O2, -Os, -O3 SIGABRT,
 * "SingleBlockLoopOptimisation ... Assertion `!mEntryRequiredTemps[sins->mSrc[0].mTemp]'
 * failed" (InterCode.cpp:23209, 23248, 25191).  g() alone: no compile-time diagnostic,
 * result 2 in those eight (g(3) is 9: gv read as this round's arr[i]).  An instrumented
 * pin without the assertion: 3.
 * Fix: ours, 12 lines (both tests made, the loop left alone when one fails), local
 * branches scratch/r41-fix-pin e5b8d38 and scratch/r41-fix-main 8affaca: 0 in all ten;
 * pin autotest 1251 emulations, none failing.  Not in the pin, not proposed upstream.
 * Workaround: none needed where checked.  "volatile" on the global gives 0 in all ten.
 * FLAGS: -e -Os
 */
char gv;
char arr[4] = {1, 2, 3, 4};

/* the value stored is the parameter, which the loop needs from its first round on */
__noinline int f(char n)
{
	int r = 0;
	char i;

	gv = 5;
	for (i = 0; i < n; i++)
	{
		r += gv;
		gv = n;
	}
	return r + gv;
}

/* the value stored is set in front of the read of gv; "arr[i] = 9" keeps it there */
__noinline int g(char n)
{
	int r = 0;
	char i;

	gv = 5;
	for (i = 0; i < n; i++)
	{
		char t = arr[i];

		arr[i] = 9;
		r += gv;
		gv = t;
	}
	return r + gv;
}

int main(void)
{
	int e = 0;

	if (f(3) != 5 + 3 + 3 + 3 || f(1) != 5 + 1) e |= 1;
	if (g(3) != 5 + 1 + 2 + 3) e |= 2;	/* 9 = 1 + 2 + 3 + 3 */
	return e;
}
