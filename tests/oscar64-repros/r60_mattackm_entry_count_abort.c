/* OSCAR64 REPRO r60 - COMPILER ABORT with native code: NetHack's mattackm(), reduced,
 * stops the compiler in NativeCodeBasicBlock::RemoveUnusedResultInstructions:
 * "NativeCodeGenerator.cpp:16018: ... Assertion `mIndex == 1000 || mNumEntries ==
 * mEntryBlocks.Size()' failed" (SIGABRT), at every native level; bytecode is right.
 * Cause (Codex, checked here): NativeCodeBasicBlock::JoinEntryLoadStoreZP moves the
 * zero-page load and store at the top of the block after the switch into the
 * predecessors that can take them, and sends the others through a new block; it removed
 * those from the block's entry list without decrementing mNumEntries, so the count and
 * the list disagree.  On v1.32.273, the pin (59 commits) and upstream main (7a37b06,
 * fetched 2026-11-15).
 * NetHack: mhitm.c, mattackm().  Found 2026-11-14 once the measurement harness's stubs
 * became __noinline (docs/BANKING-SPIKE.md): with stubs Oscar64 could inline, the file
 * compiled, so a real build would have aborted where the harness did not.
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: none in port/ (only the measurement harness compiles mhitm.c so far); the
 * fix is a missing `mNumEntries--` (Codex), with a test: pin candidate commits 60-61,
 * Jolyon's decision (ADR-0007).
 * FLAGS: -e -Os
 */
volatile int input;
int mons[4];
int hit;
struct monst { int *data; char mcanmove; };

__noinline int clone_mon(struct monst *m) { return input; }
__noinline int passivemm(struct monst *a, int strike, int died) { return died ? 2 : hit; }

__noinline int mattackm(struct monst *magr, struct monst *mdef)
{
	int i, strike = 0, struck = 0, res[6] = {0};
	for (i = 0; i < 6; i++) {
		switch (input) {
		case 254:
			if (input) return 0;
			if (strike) {
				if (mdef->data == &mons[1] || mdef->data == &mons[2])
					clone_mon(mdef);
			} else
				strike = (i >= 2 && res[i - 2] == 1);
		}
		if (!(res[i] & 4))
			res[i] = passivemm(magr, strike, res[i] & 2);
		if (res[i] & 2) return res[i];
		if (!magr->mcanmove) return res[i];
		if (res[i] & 1) struck = 1;
	}
	return struck ? 1 : 0;
}

int main(void)
{
	struct monst a = {0, 1}, b = {0, 1};
	if (mattackm(&a, &b) != 0)
		return 1;
	hit = 1;
	return mattackm(&a, &b) != 1;
}
