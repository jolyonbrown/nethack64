/* OSCAR64 REPRO r49 - CRASH: SIGSEGV in NativeCodeBasicBlock::SplitAt(0), called from
 * SplitBranchTargetRegBlock, compiling a function that tests a pointer against a
 * global, clears the global, then calls free(): `if (p == g) g = 0; free(p);`.
 * A function of our own in place of free(), or no test, compiles.
 * NetHack: mkobj.c dealloc_obj() (that shape exactly) and files.c get_uchars() crash
 * the compiler at -Os in the measurement harness, found 2026-11-14 once T1.10's stubs
 * kept the calls to the message functions; standalone, this file needs -O0.
 * Cause: SplitAt does eblock->mTrueJump->mEntryBlocks.RemoveAll(this) unguarded
 * (NativeCodeGenerator.cpp:67990 in the pin), and mTrueJump is null when the block
 * being split is the procedure's exit block.  Fixed upstream by 46e60d6 ("Fix crash
 * on splitting exit block", 2026-10-04), which is on main (4da3147 compiles this);
 * v1.32.273 and the pin crash.  The pin with 46e60d6 cherry-picked compiles this and
 * both NetHack files.
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: none in port/; the fix belongs in the pin (ADR-0007, Jolyon's decision).
 * FLAGS: -O0 -e
 */
#include <stdlib.h>

struct thing { int x; };
struct thing *thrown;

void dealloc(struct thing *p)
{
	if (p == thrown) thrown = (struct thing *)0;
	free((void *)p);
}

int main(void)
{
	struct thing *t = malloc(sizeof(struct thing));
	thrown = t;
	dealloc(t);
	return thrown == 0 ? 0 : 1;
}
