# 16. Fix exponential walks and a stack overflow in native code block checks

| | |
|---|---|
| Branch | `fix/exponential-walks-2` in `~/src/oscar64-dev`, commit `3d70f44b8a9d` (stacked on #15) |
| Patch | [`tools/oscar64-upstream/patches/main/16-exponential-walks-2.patch`](../../tools/oscar64-upstream/patches/main/16-exponential-walks-2.patch) |
| Kind | compiler hang (exponential compile time) and a stack-overflow crash, native code |
| Since | v1.32.273 and main |
| NetHack | Repro r29. `display.c` never finishes compiling (`feel_location`, `newsym`) once the `obj_to_glyph` macro gap (compat #7) is worked around; with the walk fixes it compiles in 4.7 s. For the pin the work is split into two decisions: `nethack64/pin-walks-display` (walks 1 and 2, the `display.c` fix) and `nethack64/pin-r30` (upstream 3bb084f + 1073206, which fix r30 wrong code, plus walk 3, which 1073206 makes necessary). |
| Reviews | Opus (one round, ran probes): use-after-changes, 0 high, 1 medium, 5 low; fix-up: ready; final Codex check (2026-11-13): submit after changes, 3 open items below |
| Recommendation | **Submit after #15 (stacked on it); also built and validated alone on main (efc9d90), so it can go either way.** |

## In plain words

When Oscar64 turns a function into 6502 code it runs several checks that walk backwards or forwards through the function's blocks, and three of those checks visited a block once for every route that reaches it instead of once. A function with a long run of separate "if" statements has two-to-the-power-N routes, so compile time doubles with each extra "if": about 20 of them is already minutes, and this is why NetHack's display.c never finished compiling. One of the three checks could also chase its own tail around a loop until the compiler crashed. The fix makes each check remember which blocks it has already looked at, so the work grows with the size of the function instead of the number of routes; the answers the checks give are unchanged wherever the old code gave one, and where it used to crash the compiler now simply declines that optimisation. The new test fails with the unfixed compiler within seconds (crash) and passes in all ten configurations with the fix, the full test suite has no new failures, and every other test program compiles to the same bytes apart from one file that is known to vary from build to build. In this round the review's wording points were corrected (what the first check really does, which optimisation levels are affected, no unsupported counts or first-person claims), the commit was rebased twice because PR #15 moved underneath it and the compiler rebuilt and re-tested from the final commit, and the same commit was also built and validated on plain main so it can be sent with or without #15. The backport for our pinned compiler was split in two so you can decide separately: one branch that makes display.c compile (4.7 s instead of hanging), and one that takes two upstream commits fixing a wrong-code bug (r30) plus the third walk fix those commits make necessary. Three repro files (r29, r30, r31) are ready to be copied into the repo; r31 is a separate, still unfixed compiler abort found on the way.

## The fix

One commit, 4 files, +324/-5: oscar64/NativeCodeGenerator.cpp and .h, autotest/conditionchainwalktest.c (new, 217 lines), autotest/autotest.bat (registration).
1. NativeCodeBasicBlock::IsSameRegisterSource keeps the (block, loop count) pairs it has verified; a pair seen again returns true (it is an AND over predecessors that stops at the first failure).
2. NativeCodeBasicBlock::CanJoinEntryLoadStoreZP gets a visited set per check; it still sets mChecked on every block reached, so DoJoinEntryLoadStoreZP changes the same blocks.
3. NativeCodeBasicBlock::CheckSingleUseGlobalLoadStruct does its second (poisoned) walk once per block (new flag mPatchRecheck); an arrival at a block whose second walk is running fails as before (the added "|| mPatchFail" term is defensive only and is commented as such); the one extra effect of repeating the walk is kept through mPatchRejoin plus the new helper CheckSingleUseGlobalLoadStructLoop; both flags are cleared in NativeCodeProcedure::ResetPatched. Where the old check overflowed the stack the answer is now false (store left in place).
Commit message: /home/jolyon/nethack64/build/oscar64-wt/f16-scratch/commit-msg.txt (ends with exactly one "Co-Authored-By: Claude <noreply@anthropic.com>" trailer). Compiler rebuilt from the final commit (build exit 0); the binary /home/jolyon/nethack64/build/oscar64-wt/walks2/bin/oscar64 has the same md5 as the one the validation ran with.

## Regression test

autotest/conditionchainwalktest.c, registered in autotest/autotest.bat: one function per walk (16, 24 and 14 conditionals), the loop that overflowed the stack, and four more shapes of the structure check, all with asserts; functions called with more than one argument value. Sized so the unfixed compiler fails in seconds instead of hanging.
Before (main 4da3147 and main+#15): 6/10 configurations; -n at default/-O2/-Os/-O3 exit 139 (SIGSEGV) after 5.0-6.5 s on a quiet machine (7.5-12 s under load); -n -O0 passes in 2.1 s (3.3 s under load); the five -bc configurations pass.
After (fix/exponential-walks-2 and scratch/f16-alone): 10/10, 0.09-0.41 s each, at most 46 MB.
#15's test loopconditionpathtest.c: 10/10 with the walks2 compiler.
Pin: nethack64/pin-walks-display carries a reduced conditionchainwalktest.c (vsum(16) + argjoin(24)): 8-commit pin 10/10 but -n takes 2.5-5.9 s; with the fix 10/10 with -n at 0.18-0.20 s. nethack64/pin-r30 carries autotest/elementforwardwalktest.c: pin 6/10 (wrong code, result -1 at -n default/-O2/-Os/-O3), two upstream commits alone 6/10 (those four exit 139 after about 2.4 s), pin-r30 10/10 (0.06-0.24 s); and upstream's nestedcoordinatecopytest.c: pin 8/10, pin-r30 10/10.

## Evidence

**Repro matrix.** Examples with `oscar64 -e` (all under ulimit -v 2000000 and timeout):
- main 4da3147 (~/src/oscar64-base) and main+#15: vsum.c, argjoin.c, elem.c exit 124 at 60 s with 20-21 MB; loop.c exit 139 (SIGSEGV) after about 1.2 s at default/-O2/-Os/-O3, result 0 at -O0. `-e -O0 vsum.c` also times out at 60 s (walk 1 runs at -O0); -O0 argjoin/elem are fine.
- Fixed (walks2 and f16-alone): all four "Emulation result 0" in 0.06 / 0.12 / 0.07 / 0.02 s.
Growth sweep on main 4da3147 (seconds, quiet machine): vsum 12/14/16/18/20 conditionals = 0.06/0.22/1.67/14.88/over 100; argjoin 20/22/24/26 = 0.24/0.76/2.82/11.16; elem 12/14/16/18/20 = 0.15/0.94/8.26/71.24/over 100. Fixed: 12-26 conditionals 0.04-0.09 s; 60 conditionals 0.3 s (35 MB). v1.32.273 at -Os: argjoin 22/24/26 = 0.39/1.33/5.00; vsum 14/16/18 = 0.24/1.92/16.44, over 100 at 20.
nethack64 repros via run.py (REPRO_MEMORY_MB=1900):
- v1.32.273 and the 8-commit pin: r29 BROKEN (compiler hang, 120 s), r30 BROKEN (Execution failed '37'), r31 BROKEN (compiler crashed, signal 6).
- nethack64/pin-walks-display: r29 FIXED, r30 BROKEN, r31 BROKEN.
- nethack64/pin-r30: r29 BROKEN (hang), r30 FIXED, r31 BROKEN.
- main 4da3147: r29 BROKEN (hang), r30 FIXED, r31 BROKEN.
- fix/exponential-walks-2: r29 FIXED, r30 FIXED, r31 BROKEN.
NetHack display.c (harness copy in /home/jolyon/nethack64/build/oscar64-wt/f16-scratch/nh): 8-commit pin still compiling at 140 s, three gdb samples at 60/100/140 s all inside NativeCodeBasicBlock::CanJoinEntryLoadStoreZP under JoinEntryLoadStoreZP; pin-walks-display reaches the placement errors ("error 3034: Cannot place stack section") in 4.7 s (6.1 s under load), 493 MB; pin-r30 alone still hangs (exit 124 at 150 s). Workaround checked with the 8-commit pin: `#pragma optimize(push)` / `optimize(0)` before feel_location() and `optimize(pop)` after newsym() under `#ifdef __OSCAR64C__` reaches placement in 5.2 s.

**Autotest.** Run as make -k -j2 check, compared with autotest_diff.py against the base log.
- fix/exponential-walks-2 (main + #15 + this): 1541 successful emulations on main -> 1561 (ten configurations of each of the two new tests), 0 new failures, make exit 0. Log: /home/jolyon/nethack64/build/oscar64-wt/f16-scratch/autotest-walks2.log
- scratch/f16-alone (main + this only): 1541 -> 1551, 0 new failures. Log: /home/jolyon/nethack64/build/oscar64-wt/f16-scratch/autotest-alone.log
- nethack64/pin-walks-display: 1241 -> 1251, 0 new failures. Log: /home/jolyon/nethack64/build/oscar64-wt/f16-scratch/autotest-pin-walks-display.log
- nethack64/pin-r30: 1241 -> 1261, 0 new failures. Log: /home/jolyon/nethack64/build/oscar64-wt/f16-scratch/autotest-pin-r30.log

**Corpus.** corpus_diff.py, five configurations (-n -O0/-O2/-Os/-O3, -bc -O2):
- main+#15 vs fix/exponential-walks-2: 186 files; 857 compile with both, 856 byte-identical; differs: testint16mul.c at -bc -O2; status changed 3 (conditionchainwalktest.c n-O2/n-Os/n-O3 crash -> ok). Log: /home/jolyon/nethack64/build/oscar64-wt/f16-scratch/corpus-main.log
- main vs scratch/f16-alone: 185 files; 847 / 846; same one difference, same three status changes.
- testint16mul.c: the output follows the build, not the change. The walks2 binary and the plain base binary give the same bytes (md5 b9c6...), the #15 binary and the f16-alone binary give the other variant (6f5e...); each binary is reproducible run to run. This is the known build-dependent output noted in /home/jolyon/nethack64/tools/oscar64-upstream/README.md.
- pin vs nethack64/pin-walks-display: 155 files; 695 compile with both, 694 identical (only testint16mul.c bc-O2); status changed 0.
- pin vs nethack64/pin-r30: 156 files; 700 compile with both, 696 identical; the four differences are elementforwardwalktest.c n-O2/n-Os/n-O3 and nestedcoordinatecopytest.c n-O2, expected because the pin compiles these to wrong code; status changed 0.

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| review | medium | Pin branch bundled three separate decisions | Split into nethack64/pin-walks-display (5f5034a, walks 1 and 2, the display.c fix) and nethack64/pin-r30 (2efa19d on b52c9fe and 4fed155: the two upstream commits for r30 plus walk 3). Each was built and validated on its own. The old nethack64/pin-exponential-walks-2 (ae06ee8) is superseded and left untouched. |
| review | low | IsSameRegisterSource described wrongly | Reworded in the commit message, the test comment and the PR body: "does the A, X or Y register already hold the value this load gives, on every path into the block". |
| review | low | Affected optimisation levels and the -O0 time were overstated | Now "IsSameRegisterSource at every native optimisation level, the other two above -O0" and "-O0 takes a few seconds"; the PR body gives the measured 2.1 s. |
| review | low | First-person claims and an unsupported count in the model paragraph | Replaced by an impersonal sentence that uses only logged counts: every graph of four blocks (6.2 billion cases, 6.2 million where the old form never returns and the new one answers false) and 21 million random graphs of up to 14 blocks, 0 disagreements. No sentence suggests who ran anything. |
| review | low | Closing sentence and the #NNN placeholder | The PR body ends with one paragraph: the NetHack context, then exactly "Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described." (docs/OSCAR64-UPSTREAM.md decision 3). "#NNN" stays as the placeholder for PR #15's upstream number and is listed under before_submitting. |
| review | low | The added "\|\| mPatchFail" term cannot change the result | Kept as a defensive term; the code comment, the commit message and the PR body say so ("The mPatchFail term added to that test is defensive; the old condition already fails there."). |
| self | low | Base branch moved during the round | fix/pr440-runaway moved twice (c15930d -> 6225078 -> ce1a99b; comment-only changes in autotest/loopconditionpathtest.c and the message). Rebased each time, kept as one commit, rebuilt from the final commit. |
| self | low | testint16mul.c corpus difference needed an explanation | Shown to follow the compiler build and not the change; the PR body says so. |
| self | low | display.c sentence in the PR closing claimed more than was measured | Reworded from "still compiling ... because of the second walk, and compiles in 4.7 s" to "was still in the second walk after 140 s, and is through code generation in 4.7 s": the file does not link on its own (placement errors follow), and what was observed is three gdb samples inside the walk. |

<details><summary>Evidence for each finding</summary>

1. **Pin branch bundled three separate decisions** (Split into nethack64/pin-walks-display (5f5034a, walks 1 and 2, the display.c fix) and nethack64/pin-r30 (2efa19d on b52c9fe and 4fed155: the two upstream commits for r30 plus walk 3). Each was built and validated on its own. The old nethack64/pin-exponential-walks-2 (ae06ee8) is superseded and left untouched.)

   pin-walks-display: autotest 1241 -> 1251, 0 new failures; corpus 694/695 identical, status changed 0; display.c 4.7 s. pin-r30: autotest 1241 -> 1261, 0 new failures; corpus 696/700 identical with the four expected differences; r30 FIXED. git merge-tree: the two branches merge with each other and with pin-1ae3216, pin-charidx, pin-makemon-hang and pin-shknam-crash with 0 conflicts. Logs: /home/jolyon/nethack64/build/oscar64-wt/f16-scratch/pin.log and the two autotest-pin-*.log files.

2. **IsSameRegisterSource described wrongly** (Reworded in the commit message, the test comment and the PR body: "does the A, X or Y register already hold the value this load gives, on every path into the block".)

   Checked against the listing /home/jolyon/nethack64/build/oscar64-wt/f16-scratch/asm/vsum.asm: Y = 1 is kept across the chain for the second read.

3. **Affected optimisation levels and the -O0 time were overstated** (Now "IsSameRegisterSource at every native optimisation level, the other two above -O0" and "-O0 takes a few seconds"; the PR body gives the measured 2.1 s.)

   -e -O0 vsum.c exit 124 at 60 s on base; -O0 argjoin.c and elem.c compile normally; conditionchainwalktest.c -n -O0 passes in 2.1 s on a quiet machine (3.3 s under load).

4. **First-person claims and an unsupported count in the model paragraph** (Replaced by an impersonal sentence that uses only logged counts: every graph of four blocks (6.2 billion cases, 6.2 million where the old form never returns and the new one answers false) and 21 million random graphs of up to 14 blocks, 0 disagreements. No sentence suggests who ran anything.)

   /home/jolyon/nethack64/build/oscar64-wt/walks2-review-scratch/model/ex4-full.log ("exhaustive: total 6212501064 bad 0"; 6,175,104 old-loops cases) and rnd-big.log (7 styles x 3,000,000, 0 bad); investigation logs /home/jolyon/nethack64/build/oscar64-wt/walks2-scratch/f52/model/big1.log and big2.log. These are the earlier runs' logs; the model was not re-run in this round. The review's differential-compiler figures (0 mismatches on 81,165 / 486,160 / 139 calls) are the review's evidence and are not quoted in the PR.

5. **Closing sentence and the #NNN placeholder** (The PR body ends with one paragraph: the NetHack context, then exactly "Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described." (docs/OSCAR64-UPSTREAM.md decision 3). "#NNN" stays as the placeholder for PR #15's upstream number and is listed under before_submitting.)

   /home/jolyon/nethack64/build/oscar64-wt/f16-scratch/pr-body.md, last line; commit message has a single Co-Authored-By trailer and no session or model line.

6. **The added "|| mPatchFail" term cannot change the result** (Kept as a defensive term; the code comment, the commit message and the PR body say so ("The mPatchFail term added to that test is defensive; the old condition already fails there.").)

   Corpus byte-identical apart from the build-dependent testint16mul.c; autotest unchanged apart from the new tests.

7. **Base branch moved during the round** (fix/pr440-runaway moved twice (c15930d -> 6225078 -> ce1a99b; comment-only changes in autotest/loopconditionpathtest.c and the message). Rebased each time, kept as one commit, rebuilt from the final commit.)

   git rev-parse fix/exponential-walks-2~1 = ce1a99b576c44d624709ad70d08e35c1247e5a86 = fix/pr440-runaway at the last check; rebuilt binary md5 identical to the tested one (/home/jolyon/nethack64/build/oscar64-wt/f16-scratch/build-walks2-final.log, exit 0).

8. **testint16mul.c corpus difference needed an explanation** (Shown to follow the compiler build and not the change; the PR body says so.)

   walks2 and plain base binaries give md5 b9c6..., the #15 and f16-alone binaries give 6f5e...; each binary reproduces its own output run to run.

9. **display.c sentence in the PR closing claimed more than was measured** (Reworded from "still compiling ... because of the second walk, and compiles in 4.7 s" to "was still in the second walk after 140 s, and is through code generation in 4.7 s": the file does not link on its own (placement errors follow), and what was observed is three gdb samples inside the walk.)

   /home/jolyon/nethack64/build/oscar64-wt/f16-scratch/gdb-pin8-display.log (samples at 60/100/140 s in CanJoinEntryLoadStoreZP); pin-walks-display reaches "error 3034: Cannot place stack section" in 4.7 s. The function name feel_location comes from the investigation and was not re-derived.

</details>

## Final Codex check (gpt-6-astra, 2026-11-13)

Read-only `codex exec` on a packet of the final PR text, the commit and the earlier findings (as for PRs 1-14). Each finding was then checked by the lead.

| Severity | Finding | Checked | Resolution |
|---|---|---|---|
| medium | "testint16mul.c at `-bc -O2`, whose output depends on the compiler build and not on this change": the hashes given do not establish that | True as worded; now measured: with the compiler's heap zero-filled (`zeroheap.so` preload), plain main 4da3147, main with this change alone (efc9d90) and main with #15 and this change (3d70f44) give identical bytes for it (sha256 56269bcc...), twice each; without the preload main and efc9d90 give 5875acb7... and 3d70f44 gives 56269bcc... So the difference comes from memory the compiler reads before writing (OSCAR64-COMPAT.md #40, #41), not from this change | Open: before submitting, replace the clause with that measurement |
| low | The comment "A block whose second check is still running has mPatchUsed set" is too broad | True: `mPatchUsed = used \|\| !cleared` leaves it clear during a second check that started with the local overwritten and not used; an arrival there then passes the test, exactly as with the old condition, so behaviour is unchanged and only the comment overclaims | Open: before submitting, qualify the comment and the PR's explanation to second checks that start without the overwrite (comment only; the compiled compiler does not change) |
| low | The PR text's `#NNN` placeholders must become real references | True | Already on the "Before submitting" list: fill in once the parent PR has a number |

## Before submitting

- Replace "#NNN" (six places) with the upstream number of #15, or drop those references and use the standalone validation numbers if this goes alone.
- Choose: on top of #15 (3d70f44 on ce1a99b) or alone on main (efc9d90 on scratch/f16-alone); both were built and validated, and #15 and #16 merge cleanly in either order.
- The Windows/MSVC build was not run (two member flags and one method added to NativeCodeBasicBlock, using containers already used in that file).
- If upstream main or #15 moves: rebase, keep one commit, rebuild, and re-run at least the ten configurations.
- Done 2026-11-12 (Jolyon's decision): the commit ends with one `Co-Authored-By: Claude <noreply@anthropic.com>` line and no session link (message only; the tree is the one validated), and the PR text ends with the same AI-assistance sentence as every other PR.

## Risks and limitations

- The visited sets use a linear IndexOf, so each check is quadratic in the number of blocks; measured 0.3 s for 60 conditionals, not measured on very large functions beyond the autotest and corpus.
- The claim that walk 3 gives the same answer as before rests on the model comparison (a transcription of both versions, logs from the investigation and the review, not re-run in this round) plus the autotest and corpus results; it is not a proof on the compiler's own code.
- Where the old walk 3 overflowed the stack the new one answers false (optimisation not applied); that is the conservative direction.
- Windows/MSVC build and the samples makefile were not run; only Linux, C64 target.
- FindSharedGlobalAddressSumY has the same shape as walks 1 and 2 and is unchanged because it could not be made slow; it could still surface with some other input.
- -O0 native code was affected by walk 1 only; the fix covers it, but -O0 was measured only on the examples and the new test.
- The maintainer often takes the test and writes his own fix; the test is self-contained for that.

## Related bugs found, not fixed here

- r30 (wrong code): v1.32.273 forwards an array element copy past an overwrite of the element; repro returns 37 at default/-O1/-O2/-O3/-Os, 0 at -O0 and -bc. Fixed upstream by 3bb084f and 1073206, which are already in main 4da3147; the pin needs the backport (nethack64/pin-r30), and 1073206 is what introduced walk 3's exponential case and stack overflow.
- r31 (compiler abort, unfixed everywhere tested: v1.32.273, 8-commit pin, both new pin branches, main 4da3147, fix/exponential-walks-2): at -Os, BlockSizeCopyReduction emits "LDY #-1" and the assertion `linkerObject || (address >= 0 && address < 256)` fails (signal 6); reduced from invent.c display_pickinv(). A probable fix, "(mIns[si + 0].mAddress - 1) & 0xff", was not tried.
- Walk 1 (IsSameRegisterSource) also runs at -O0, so -O0 was not a workaround for that shape before the fix.
- r29 costs `make repros` 120 s for as long as it is unfixed in the compiler the repo uses (it is a hang, bounded by the harness timeout).

## Draft pull request

**Title:** Fix exponential walks and a stack overflow in native code block checks

````markdown
A function with a long run of independent conditionals can take minutes or hours to compile to native code, and one shape crashes the compiler. There are three causes; each of the first three examples below triggers one of them, the fourth is the crash.

`vsum.c` (two reads through the same pointer, 20 conditionals between them):

```c
#define C4(i) if (fl[i]) acc += 1; if (fl[i + 1]) acc += 2; if (fl[i + 2]) acc += 3; if (fl[i + 3]) acc += 4;

char fl[64], gk;
int acc;
volatile char buf[4], buf2[4];

__noinline int vsum(volatile char * p)
{
	int s = 0;

	s += p[1];
	C4(0) C4(4) C4(8) C4(12) C4(16)		// 20 conditionals
	if (gk) s += p[2];
	s += p[1];
	return s;
}

int main(void)
{
	buf[1] = 3; buf[2] = 4; buf2[1] = 7; buf2[2] = 8;
	if (vsum(buf) != 6)
		return 1;
	gk = 1; fl[1] = 1;
	if (vsum(buf2) != 22 || acc != 2)
		return 2;
	return 0;
}
```

`argjoin.c` (a value passed in a different argument position on two paths behind 32 conditionals):

```c
#define C4(i) if (fl[i]) acc += 1; if (fl[i + 1]) acc += 2; if (fl[i + 2]) acc += 3; if (fl[i + 3]) acc += 4;

char fl[64];
int acc;

__noinline int isink(int x, int y)
{
	return 100 * x + y;
}

__noinline int argjoin(int a, int b)
{
	int x = a * 3 + b;

	C4(0) C4(4) C4(8) C4(12) C4(16) C4(20) C4(24) C4(28)	// 32 conditionals
	if (fl[63]) return isink(x, 1);
	return isink(2, x);
}

int main(void)
{
	if (argjoin(5, 2) != 217 || argjoin(4, 5) != 217)
		return 1;
	fl[63] = 1; fl[1] = 1;
	if (argjoin(5, 2) != 1701 || argjoin(4, 5) != 1701 || acc != 4)
		return 2;
	return 0;
}
```

`elem.c` (a local array element overwritten in one arm, 20 conditionals behind it):

```c
#define C4(i) if (fl[i]) acc += 1; if (fl[i + 1]) acc += 2; if (fl[i + 2]) acc += 3; if (fl[i + 3]) acc += 4;

char arr[8] = {10, 20, 30, 40, 50, 60, 70, 80};
char fl[64], cb = 5;
int acc;

__noinline int use(char * p)
{
	return p[0] + p[1];
}

__noinline int elem(char k)
{
	char t[4];
	int r = 0;

	t[1] = 1;
	t[0] = arr[k];
	if (fl[63]) { r = use(t); t[0] = cb; r += use(t); }
	C4(0) C4(4) C4(8) C4(12) C4(16)		// 20 conditionals
	return r;
}

int main(void)
{
	if (elem(1) != 0)
		return 1;
	fl[63] = 1; fl[1] = 1;
	if (elem(2) != 31 + 6 || acc != 2)
		return 2;
	return 0;
}
```

`loop.c` (the same element, with a loop behind the overwrite instead of the conditionals):

```c
char arr[8] = {10, 20, 30, 40, 50, 60, 70, 80};
char fl[64], cb = 5;
int acc;

__noinline int use(char * p)
{
	return p[0] + p[1];
}

__noinline int f(unsigned char k)
{
	char t[4];
	int r = 0;
	char i;

	t[1] = 1;
	t[0] = arr[k];
	if (fl[63])
	{
		r = use(t);
		t[0] = cb;
		r += use(t);
	}
	for (i = 0; i < k; i++)
		acc += fl[i];
	return r;
}

int main(void)
{
	if (f(3) != 0)
		return 1;
	fl[63] = 1;
	fl[1] = 1;
	if (f(2) != 31 + 6 || acc != 1)
		return 2;
	return 0;
}
```

Reproduce with `oscar64 -e vsum.c` (and the other three), main `4da3147`, Linux.

Observed: `vsum.c`, `argjoin.c` and `elem.c` are each still compiling after 60 seconds (memory stays at about 21 MB; it is time only). `loop.c` ends in a segmentation fault after about a second, at the default level and with `-O2`, `-Os` and `-O3` (with `-O0` it compiles and returns 0).

Expected: each compiles in a fraction of a second and the emulation returns 0. With this change: 0.06 s, 0.12 s, 0.07 s and 0.02 s, "Emulation result 0".

How the time grows, with the conditionals of the same three functions written out one per line (`oscar64 -e`, seconds, before this change):

| conditionals | 12 | 14 | 16 | 18 | 20 | 22 | 24 | 26 |
|---|---|---|---|---|---|---|---|---|
| vsum | 0.06 | 0.22 | 1.67 | 14.88 | over 100 | | | |
| argjoin | | | | | 0.24 | 0.76 | 2.82 | 11.16 |
| elem | 0.15 | 0.94 | 8.26 | 71.24 | over 100 | | | |

With this change each of these takes between 0.04 and 0.09 s, and 60 conditionals take 0.3 s.

**Cause.** Three checks in `NativeCodeGenerator.cpp` walk the flow graph recursively and visit a block once per path instead of once. A run of N independent conditionals has 2^N paths through it.

1. `NativeCodeBasicBlock::IsSameRegisterSource` (does the A, X or Y register already hold the value this load gives, on every path into the block; used by `PartialBackwardValuePropagation` and `BackwardValuePropagation`) recurses into every predecessor and keeps no record of the blocks it has seen. `vsum.c`, where the index 1 stays in Y for the second read; every native optimisation level, `-O0` included.
2. `NativeCodeBasicBlock::CanJoinEntryLoadStoreZP` (can a zero page copy move up into the blocks in front of a join) has the same shape: it sets `mChecked` but does not test it. `argjoin.c`; native code above `-O0`.
3. `NativeCodeBasicBlock::CheckSingleUseGlobalLoadStruct` is guarded by `mPatched`, but since 1073206 (Fix too strong check for native structure copy forwarding) a block first reached behind an overwrite of the local is walked a second time, as poisoned, when a path reaches it without an overwrite, and nothing records that this was done, so every such path walks the block and everything behind it again (`elem.c`). If the blocks behind it form a loop that does not store to the local, the second walk comes back to the block it started from and starts again until the stack overflows (`loop.c`). Native code above `-O0`.

**Fix.**

1. `IsSameRegisterSource` keeps the (block, loop count) pairs it has verified. It is an AND over the predecessors that stops at the first failure, so a pair seen again returns true, as it did the first time. The loop count is part of the key because it changes the answer at a loop head.
2. `CanJoinEntryLoadStoreZP` gets a visited set per check. Its result depends only on the block, and it still sets `mChecked` on every block it reaches, so `DoJoinEntryLoadStoreZP` changes the same blocks as before.
3. In `CheckSingleUseGlobalLoadStruct` the second walk is done once per block (`mPatchRecheck`). An arrival at a block whose second walk is still running fails as before: such a block has `mPatchUsed` set, and a second walk that completed has left it clear. (The `mPatchFail` term added to that test is defensive; the old condition already fails there.) Repeating the second walk had one more effect, which is kept: started again from a block inside it, it could pass a block that overwrites the local and arrive, cleared, back at the block whose second walk was running, and fail there. This happens when an overwriting block leads straight back into a block that is walked a second time after it, so the overwriting block marks its successors (`mPatchRejoin`) and a marked block searches the blocks behind it for the overwriting block (`CheckSingleUseGlobalLoadStructLoop`). Both flags are cleared in `NativeCodeProcedure::ResetPatched`. The check gives the same answer as before wherever the old one returned; where it overflowed the stack the answer is now false, which leaves the store in place.

The old and the new form of the third check were also compared in a model of the algorithm (a transcription of the two versions, not the compiler's own code), with each block reduced to what its instruction scan can do. The two give the same answer on every graph of four such blocks (6.2 billion cases) and on 21 million random graphs of up to 14 blocks wherever the old one returns; where the old one never returns (6.2 million of the four-block cases) the new one answers false.

`FindSharedGlobalAddressSumY` has the same shape as the first two, but it only walks after matching one exact instruction sequence and could not be made to take long, so it is unchanged.

This is independent of #NNN (visited sets for `CollectBlocksToDominator`, `IsDirectLoopPathBlock` and `CheckLoopIndexX/YRegisters`); it is the same kind of problem in three other places, and the commit applies to main with or without #NNN.

**Test.** The new autotest `conditionchainwalktest.c` (registered in `autotest.bat`, picked up by the makefile) has one function per walk with 16, 24 and 14 conditionals, the loop that overflowed the stack, and four more shapes of the structure check, all with asserts on the values. The functions are called with more than one argument value so that the arguments are not folded into them. The sizes are chosen so that the unfixed compiler fails within seconds rather than hanging.

**Validation** on Linux, C64 target, against main `4da3147` with #NNN applied, in the ten autotest configurations (`-ea -g`, `-bc` and `-n`, default/`-O0`/`-O2`/`-Os`/`-O3`):

- New test before: `-n` at default, `-O2`, `-Os` and `-O3` crash (segmentation fault) after 5 to 6.5 s; `-O0 -n` passes in 2.1 s; the five `-bc` configurations pass. After: 10/10, 0.09 to 0.4 s each.
- Full autotest (`make -k check`): 1541 successful emulations on main, 1561 with #NNN and this change (the ten configurations of each of the two new tests), no new failures.
- 186 autotest and external test programs compiled with both builds in five configurations (`-n -O0/-O2/-Os/-O3`, `-bc -O2`): 857 compile with both, 856 are byte-identical. The one that differs is `testint16mul.c` at `-bc -O2`, whose output depends on the compiler build and not on this change: the build with #NNN and this change gives the same bytes for it as a build of plain main. The only status change is the new test going from crash to ok at `-n -O2/-Os/-O3`.
- The same commit on main alone, without #NNN: the four examples and the new test behave as above; full autotest 1551 successful emulations (the ten configurations of the new test), no new failures; 185 programs, 847 compile with both builds, 846 byte-identical, with the same one difference and the same three status changes.

Found while porting NetHack 3.4.3 to the C64: its `display.c` (`feel_location()`, `newsym()`) was still in the second walk after 140 s, and is through code generation in 4.7 s with the first two fixes (measured with v1.32.273 plus backported fixes, which is what the port builds with). Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described.
````
