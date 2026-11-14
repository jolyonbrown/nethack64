/* OSCAR64 REPRO r50 - CRASH: SIGSEGV in InterCodeBasicBlock::LoadStoreForwarding
 * (InterCode.cpp:15124 in the pin, deep in its recursion over the blocks), compiling a
 * function that stores fopen()'s result in a global and then passes a string to a
 * function that stores to a global.  -Os, -O2 and -O3; -O0 compiles.  It compiles with
 * a function of our own in place of fopen(), an int global, an empty callee, or a
 * callee that takes an int or nothing; static or not, volatile or not, variadic or not
 * make no difference.
 * NetHack: questpgr.c load_qtlist(): msg_file = dlb_fopen(...) (fopen under the C64
 * configuration), later impossible().  Found 2026-11-14 once T1.10's stubs gave
 * impossible() a body; the real build will have one too.
 * On v1.32.273, the pin, the pin with 46e60d6 (r49's fix) and upstream main 4da3147.
 * Expect when fixed: compiles.
 * Workaround: none yet (TASKS T1.33).
 * FLAGS: -O2
 * COMPILE-ONLY
 */
#include <stdio.h>

FILE *fp;
int n;

void touch(const char *s)
{
	n = 0;
}

void load(void)
{
	fp = fopen("quest.dat", "r");
	touch("x");
}

int main(void)
{
	load();
	return 0;
}
