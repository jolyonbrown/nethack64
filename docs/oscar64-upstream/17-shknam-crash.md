# 17. Fix compile time evaluation of loops over constant pointer tables

| | |
|---|---|
| Branch | `fix/shknam-crash` in `~/src/oscar64-dev`, commit `392aa9ea8c42`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/17-shknam-crash.patch`](../../tools/oscar64-upstream/patches/main/17-shknam-crash.patch) |
| Kind | compiler crash (with a wrong count behind it) |
| Since | v1.32.273 and main |
| NetHack | Compat #11b (repro r27): `shknam.c` crashes v1.32.273 when it evaluates the loop that counts a const table of shopkeeper names at compile time; behind the crash it would count 1 name instead of 30. With the fix `shknam.c` compiles (2,578 bytes) and counts 30. |
| Reviews | Opus (one round, ran probes): use-after-changes, 1 high, 2 medium, 3 low; fix-up: ready; final Codex check: pending |
| Recommendation | **Submit after #1: on plain main this fix alone turns `0 != names[n]` loops from a crash into a wrong count of 0 until #1 is merged.** |

## In plain words

NetHack's shopkeeper-naming code counts a fixed list of 30 names with a tiny loop, and Oscar64 tries to run such a loop itself while compiling so the program just contains the answer. That shortcut had two slips: it looked for a size in the wrong place and crashed with no message, and behind the crash it would have counted 1 instead of 30 because it mistook the first name for the end-of-list marker. The 19-line fix corrects both, once for upstream's newest compiler and once for our pinned one, and adds a test with 13 checks. This round changed no code at all, only words. The commit messages lost the session link and now end with the single Co-Authored-By line you chose. The PR text had a wrong sentence ("three asserts fail") which now says correctly that 10 of the 13 checks fail when only half the fix is applied. It also gained a paragraph warning that on plain upstream the variant `0 != names[n]` gives a wrong count of 0 until our earlier null-comparison fix (#1) is merged too, which is why this PR should be sent after #1. The repro file r27 for our tree is finished, with its header corrected.

## The fix

Code unchanged from the reviewed commits (trees identical: main 3c689a92, pin 90ea15b0; git patch-id 3c579bd7 before and after, and the same on both branches). oscar64/InterCode.cpp, 19 lines changed (16 added, 3 replaced):
1. LoadConstantOperand, IT_POINTER case: `cop.mOperandSize = cop.mLinkerObject->mSize;` instead of `ins->mConst.mLinkerObject->mSize`.
2. New `static bool OperandConstantIsTrue(const InterOperand& op)`: float by mFloatConst; pointer true when mMemory != IM_ABSOLUTE or mIntConst != 0; otherwise mIntConst != 0 (the rule CheckIsConstBranch uses).
3. The IC_BRANCH cases of ConstSingleLoopOptimization and ConstInnerLoopOptimization call the helper. CheckIsConstBranch is untouched.
Plus autotest/constloopptrtest.c (154 lines) and three lines in autotest/autotest.bat.

This round, message only: both commits amended to end with exactly one trailer, `Co-Authored-By: Claude <noreply@anthropic.com>` (the Claude-Session line removed, nothing else changed). c0733e1 -> 392aa9e (fix/shknam-crash), c5048e6 -> 006793d (nethack64/pin-shknam-crash). The two messages are identical. Author and author date kept (Thu Nov 12 14:12:59 2026); unsigned. No rebuild: no source file in either worktree is newer than its bin/oscar64, both worktrees are clean.

## Regression test

autotest/constloopptrtest.c (154 lines, 13 asserts), registered in autotest/autotest.bat after loopdomtest.c; the autotest makefile picks it up by glob.

It covers: counting a null terminated string table by index and by pointer walk; using the pointer the loop ends on (strcmp of the last name); a struct table with a pointer member (count, sum, search with a compound condition); a table of function pointers (count, and calling the last one); a table of addresses inside an int array (checking both the address and the value); and two multi-block loops over a table with null entries in the middle (count_sparse == 4, weigh_sparse == 212), which go through ConstInnerLoopOptimization.

Re-run this round in the ten autotest configurations (-ea -g, -n and -bc, each at default, -O2, -O0, -Os, -O3), each under ulimit -v 2000000:
- fix on main (binary of the amended branch's tree): 10 of 10 "Emulation result 0"
- pin backport: 10 of 10
- main + the r19 fix + this fix (new scratch build b6c9347): 10 of 10
- unfixed main 4da3147, unfixed pin c2f5cab and v1.32.273: compiler segfault (exit 139) in the 8 optimising configurations, pass at -O0 in -n and -bc
- build with only the null-dereference line fixed (shknam-crash-partial): compiles, but the test fails in the same 8 configurations (Emulation result -1, first failing assert line 140, count_names) and passes at -O0. A printing copy of the test (t/clpt_print.c, same functions) shows 10 of the 13 checks wrong at default, -O2 and -Os (only total_prob and the two find_shop calls right) and 8 of 13 wrong at -O3 (checks 1, 2, 3, 4, 7, 8, 9, 13). So the test pins the branch fix in both evaluators. This replaces the earlier wrong statement that three asserts fail.

No float table case is in the test, deliberately: float truth tests have separate pre-existing bugs that fail even at -O0.

## Evidence

**Repro matrix.** All runs this round, one at a time, each under ulimit -v 2000000 with a 120 s timeout; ten configurations = -ea -g with -bc/-n at default, -O2, -O0, -Os, -O3. Logs in /home/jolyon/nethack64/build/oscar64-wt/f17-scratch/out/<label>/.

PR example (t/example.c, 3 names, assert(count() == 3)):
- 4da3147, v1.32.273, pin c2f5cab, main + r19 fix only: exit 139 in the 8 optimising configurations, pass at -O0
- null-fix-only build: assert fails in those 8 (count is 1), pass at -O0
- main + fix, main + r19 + fix, integration-final3 + fix, pin + fix: 10 of 10 result 0

Zero on the left (t/zeroleft.c prints four counts over the same table: `names[n]`, `names[n] != 0`, `0 != names[n]`, `!(0 == names[n])`):
- main + fix alone: 3 3 0 0 in the 8 optimising configurations; 3 3 3 3 at -O0
- main + r19 fix + this fix (b6c9347, built this round): 3 3 3 3 in 10 of 10
- integration-final3 + fix (2762656): 3 3 3 3 in 10 of 10
- pin + fix (has the r19 fix a6fe02b): 3 3 3 3 in 10 of 10
- null-fix-only build: 1 3 0 0 in the 8 optimising configurations
- 4da3147, v1.32.273, pin, r19-only: segfault in the 8 optimising configurations

r27 (through a copy of tests/oscar64-repros/run.py, REPRO_MEMORY_MB=1900; f17-scratch/r27-run.txt):
- v1.32.273, pin c2f5cab, main 4da3147, integration-final3: BROKEN, compiler crashed (signal 11)
- null-fix-only build: BROKEN, error 3007: Execution failed '1'
- main + fix, main + r19 + fix, main + 14 + fix, pin + fix: FIXED, runs, result 0
r27 in ten configurations: v1.32.273, 4da3147 and the pin crash in the 8 optimising ones and pass at -O0; main + fix and pin + fix give result 0 in 10 of 10.

Not re-run this round (earlier agents' measurements, unchanged trees): shknam.c in the measurement harness (pin backport: fits-not, 2578 bytes, 3 of 7 functions, names_avail folded to 30; v1.32.273, pin and integration-final3 segfault), and the gdb backtraces.

**Autotest.** Not re-run this round (message-only amend; trees identical to the validated ones). Recomputed from the saved logs with tools/oscar64-upstream/autotest_diff.py:
- Main, author's run (make -k -j2 check; this run was not under the memory cap): base 1541 emulations, new 1551, new failures 0, fixed 0, failing in both 0. Log /home/jolyon/nethack64/build/oscar64-wt/shknam-crash-scratch/v2/autotest-main-fix.log.
- Main, reviewer's run on a from-scratch build of the same tree, under the 2 GB cap: 1541 -> 1551, new failures 0, fixed 0, failing in both 0. Log /home/jolyon/nethack64/build/oscar64-wt/shknam-crash-review-scratch/autotest-main-review.log.
- Pin (under the cap): base 1241 (pin8-autotest.log), new 1251, new failures 0, fixed 0, failing in both 0. Log /home/jolyon/nethack64/build/oscar64-wt/shknam-crash-scratch/v2/autotest-pin-fix.log.
The 10 extra emulations in each are constloopptrtest.c in its ten configurations.

**Corpus.** Not re-run this round. Saved results of corpus_diff.py (-j 1, capped):
- Main, author's run, 4da3147 against the fix: 185 files (159 autotest sources including the new test + 26 tests/oscar64-repros) x 5 configurations; both compile 846; identical 845; different 1 (autotest/testint16mul.c at bc-O2, the known build-to-build noise); status changed 4, all autotest/constloopptrtest.c crash -> ok at n-O2, n-Os, n-O3, bc-O2. /home/jolyon/nethack64/build/oscar64-wt/shknam-crash-scratch/v2/corpus-main.log
- Main, reviewer's repeat with a clean build of the same tree: 846 both compile, 846 identical, 0 different, the same 4 status changes. /home/jolyon/nethack64/build/oscar64-wt/shknam-crash-review-scratch/corpus-main-review.log
- Pin against backport: 155 files (129 + 26) x 5; both compile 691; identical 691; different 0; the same 4 status changes. /home/jolyon/nethack64/build/oscar64-wt/shknam-crash-scratch/v2/corpus-pin.log
I counted the file sets this round (159 and 129 autotest sources after the makefile's helper exclusions, 26 repros); the PR text now states them.

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| opus review | high | Separate bug the pin still has (upstream 1ae3216 missing): t[k] of a const pointer table points 2k bytes too far; breaks sounds.c and an adjacent loop on the backport | out-of-scope (left alone as instructed; another agent backports 1ae3216 as r32 on its own pin branch) |
| opus review | medium | PR text is wrong: 'With only the first change ... three asserts fail' | fixed (PR bullet and regression_test text) |
| opus review | medium | On upstream main this fix alone turns one loop variant from a crash into a silent wrong count (r19 interaction); the PR should say so | fixed (new PR section 'Interaction with the null pointer comparison fix'; before_submitting keeps this PR after #1) |
| opus review | low | Commit trailers and the PR's closing sentence do not follow Jolyon's 2026-11-12 decision | fixed |
| opus review | low | r27 header: overstated scan claim, wrong 'found' date, workaround wording | fixed |
| opus review | low | Adjacent bugs confirmed but outside this fix (pointer/float branch folds, float-table truth test, error-file crash) | out-of-scope (no change to this PR; listed in adjacent_bugs for separate tracking) |

<details><summary>Evidence for each finding</summary>

1. **Separate bug the pin still has (upstream 1ae3216 missing): t[k] of a const pointer table points 2k bytes too far; breaks sounds.c and an adjacent loop on the backport** (out-of-scope (left alone as instructed; another agent backports 1ae3216 as r32 on its own pin branch))

   Not caused by this fix and not touched here. Nothing was re-run for it this round. Listed under risks and adjacent_bugs so that the pin decision for this fix is read together with r32: with the backport alone, `names[n] != names[2]` compiles to wrong code where it used to crash the compiler.

2. **PR text is wrong: 'With only the first change ... three asserts fail'** (fixed (PR bullet and regression_test text))

   Re-measured with the null-fix-only build (build/oscar64-wt/shknam-crash-partial): constloopptrtest.c gives Emulation result -1 in the 8 optimising configurations (first failing assert line 140) and 0 at -O0. The printing copy t/clpt_print.c prints F1 F2 F3 F4 p p p F8 F9 F10 F11 F12 F13 at default, -O2 and -Os (10 of 13 wrong) and F1 F2 F3 F4 p p F7 F8 F9 p p p F13 at -O3 (8 of 13), -n and -bc alike. PR bullet now reads: 'With only the first change: it compiles, but the test still fails in the same eight configurations: 10 of its 13 checks are wrong at the default level, `-O2` and `-Os`, and 8 at `-O3`.'

3. **On upstream main this fix alone turns one loop variant from a crash into a silent wrong count (r19 interaction); the PR should say so** (fixed (new PR section 'Interaction with the null pointer comparison fix'; before_submitting keeps this PR after #1))

   t/zeroleft.c over the PR's 3-name table, ten configurations: main + fix alone gives 0 for `0 != names[n]` and for `!(0 == names[n])` in the 8 optimising configurations and 3 at -O0, while `names[n]` and `names[n] != 0` give 3 everywhere. To state 'with both changes' from a direct measurement, a scratch compiler was built from fix/r19-null-compare 8ca7795 plus this commit (branch scratch/f17-r19-plus-shknam, b6c9347, worktree build/oscar64-wt/f17-r19-stack): all four forms count 3 in 10 of 10, and the new test passes 10 of 10. integration-final3 + fix and the pin backport also give 3 in 10 of 10. The PR refers to the r19 PR as #NNN with its title, as page 06 does, because no upstream number exists yet.

4. **Commit trailers and the PR's closing sentence do not follow Jolyon's 2026-11-12 decision** (fixed)

   Both commits amended, message only: the Claude-Session line removed, one trailer left ('Co-Authored-By: Claude <noreply@anthropic.com>'). c0733e1 -> 392aa9ea8c42 (tree 3c689a92 unchanged), c5048e6 -> 006793d90057 (tree 90ea15b0 unchanged); patch-id 3c579bd7 unchanged; the two messages are byte-identical. Patches re-exported to f17-scratch/patches; they differ from the previous exports only in the From hash line and the removed trailer. PR now ends '...Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described.' The Validation bullets were also reworded impersonally ('Compiled every ... programs of ours' removed).

5. **r27 header: overstated scan claim, wrong 'found' date, workaround wording** (fixed)

   Final file /home/jolyon/nethack64/build/oscar64-wt/f17-scratch/r27_const_pointer_table_loop_crash.c. Code and FLAGS unchanged. Header now says: 'In the measurement harness's results since the 2026-11-08 baseline; diagnosed 2026-11-12' (docs/data/oscar64-baseline-2026-11-08.json has shknam.c as compiler-crash, checked); 'A scan of port/src for loops that index a constant table by name found no other loop the optimiser runs this way' (scoped to what the reviewer's scan covered); 'Fixed by fix/shknam-crash on upstream main 4da3147 (proposed upstream as PR #17 in docs/OSCAR64-UPSTREAM.md) and by its backport nethack64/pin-shknam-crash on the patched pin'; 'Workaround: none needed if the backport is adopted; otherwise, in nameshk(), replace the count after nlp = shkgeneral by names_avail = SIZE(shkgeneral) - 1 (30, the same value)'. FLAGS line is at character 1882 (limit 2000); longest line 93. Run through run.py on nine compilers: BROKEN (signal 11) on the four unfixed ones, BROKEN (result 1) on the null-fix-only build, FIXED on the four fixed ones. Compat row 11b is in the nethack64 tree and is the lead's to update.

6. **Adjacent bugs confirmed but outside this fix (pointer/float branch folds, float-table truth test, error-file crash)** (out-of-scope (no change to this PR; listed in adjacent_bugs for separate tracking))

   The reviewer asked for no change. Not re-run this round.

</details>

## Before submitting

- Replace "#NNN" in the interaction paragraph with the upstream number of #1.
- Send after #1: on plain main this fix alone makes `0 != names[n]` loops count 0 instead of crashing.
- If upstream main has moved from 4da3147: rebase, re-run the ten configurations, the autotest and corpus_diff.py, and update the numbers.
- Done 2026-11-12 (Jolyon's decision): the commit ends with one `Co-Authored-By: Claude <noreply@anthropic.com>` line and no session link (message only; the tree is the one validated), and the PR text ends with the same AI-assistance sentence as every other PR.

## Risks and limitations

- On plain upstream main, this fix alone turns `for (n = 0; 0 != names[n]; n++)` (0 on the left) from a compiler crash into a silent wrong count of 0 at the optimising levels. Confirmed this round; fixed when the r19 null-comparison fix (#1) is also present (measured on a build of exactly r19 + this fix: 3 in 10 of 10). The PR now says so; send this PR after #1.
- The pin backport is not affected by that (the pin has the r19 fix), but on the pin a loop that compares table entries with a constant-index entry (e.g. `names[n] != names[2]`) still miscompiles because of the separate missing upstream fix 1ae3216 (reviewer's finding; being backported by another agent as r32). Not caused by this fix: before it, the same loop segfaulted the compiler.
- Pointer truth rule: a constant pointer counts as null only when it is IM_ABSOLUTE with value 0, the rule CheckIsConstBranch already uses. No path was found that produces a null pointer constant with another memory class, but that is not proven.
- The fix cannot be shown on shknam.c with bare main (main stops earlier at role.c error 3011); the NetHack evidence is the pin backport and the integration branch.
- The author's main autotest ran without the memory cap; the reviewer's capped re-run of the same tree gives the same numbers.
- Upstream may prefer a different shape (inline tests without a helper); the change is small enough to restyle.
- Nothing was pushed, forked or posted.

## Related bugs found, not fixed here

None fixed here; all confirmed by the reviewer, not re-run by me except where stated.
1. Upstream 1ae3216 missing from v1.32.273 and the pin: `t[k]` of a `* const` pointer table with constant k points 2k bytes too far (sounds.c:83 throne_msg[2], pager.c objexplain[VENOM_CLASS]). Being backported separately as r32; left alone as instructed.
2. `0 != names[n]` folded by offset only on upstream main: this is the r19 bug (PR #1); re-confirmed this round (counts 0 with this fix alone, 3 with r19 too).
3. Folded pointer and float branches outside the loop evaluators: `const char *p = "abc"; if (p)` and `float f = 0.5; if (f)` return 0 at -O2/-Os/-O3 on all compilers (r24's header already lists `if (p)`); suspect sites test mIntConst without a type check near InterCode.cpp 7390, 9329, 9366.
4. `for (n = 0; ftab[n]; n++)` over a static const float table returns 0 at every level including -O0 on all compilers.
5. Error-file crash: with -rmp, after an ordinary compile error the compiler segfaults in InterCodeProcedure::Disassemble (null mEntryBlock) called from Compiler::WriteErrorFile, so compile errors look like compiler crashes in the harness.
6. files.c crashes the pin in NativeCodeBasicBlock::SplitAt (native code generator), unrelated.
7. A curiosity seen this round on the null-fix-only build only: the printing copy of the test at default -bc prints 10 failed checks but returns 9. That build is not a candidate for anything.

## Draft pull request

**Title:** Fix compile time evaluation of loops over constant pointer tables

````markdown
A loop that walks a constant, null terminated table of pointers, with nothing in its body that needs run time, crashes the compiler at every optimisation level except `-O0`:

```c
#include <assert.h>

static const char * const names[] = { "Alpha", "Beta", "Gamma", 0 };

int count(void)
{
	int n;
	for (n = 0; names[n]; n++)
		;
	return n;
}

int main(void)
{
	assert(count() == 3);
	return 0;
}
```

```
oscar64 -e -g -Os count.c
```

Observed on main 4da3147 (and on v1.32.273): the compiler segfaults, exit 139, no message. Same at default, `-O2` and `-O3`, native and bytecode. Expected: it compiles and prints `Emulation result 0`.

### Cause

`ConstSingleLoopOptimization` and `ConstInnerLoopOptimization` run such a loop at compile time and read the table through `LoadConstantOperand`. Two things go wrong.

1. The `IT_POINTER` case of `LoadConstantOperand` was copied from `LoadConstantFold`, where the result is written into `ins->mConst`. It still ends with

   ```cpp
   cop.mOperandSize = ins->mConst.mLinkerObject->mSize;
   ```

   but here the result is the local operand `cop`, and `ins` is the load instruction, whose unused constant operand has no linker object. Any table entry that refers to a global (a string, a function, the address of a variable) is a null dereference.

2. With that corrected the loop above ran to the wrong count, 1 instead of 3. Both evaluators decide an `IC_BRANCH` by `mIntConst` alone, and a pointer to a global at offset 0 has `mIntConst == 0` although it is not null. `CheckIsConstBranch` already has the right rule.

### Fix

- `LoadConstantOperand` takes the size from `cop.mLinkerObject`, the object the reference names.
- A small helper, `OperandConstantIsTrue`, applies the rule `CheckIsConstBranch` uses: a float by its float value, a pointer is true when it is not `IM_ABSOLUTE` or has a non zero value, anything else by `mIntConst`. The `IC_BRANCH` cases of the two loop evaluators call it. `CheckIsConstBranch` itself is unchanged.

### Interaction with the null pointer comparison fix

With this change alone, the same loop written with the 0 on the left, `for (n = 0; 0 != names[n]; n++)`, no longer crashes but counts 0 instead of 3 at every level except `-O0`: a comparison of an integer constant 0 with a pointer is folded by offset only, and the first table entry is a pointer at offset 0. #NNN ("Fix pointer compared with integer constant 0 folding as not equal") fixes that; with both changes the loop counts 3 in all ten autotest configurations. `names[n]` and `names[n] != 0` count 3 with this change alone.

### Test

`autotest/constloopptrtest.c` (registered in `autotest.bat`) runs single block and multi block loops over null terminated tables of strings, of functions and of addresses of globals, over a struct table with a pointer member, and over a table with null entries in the middle, and uses the pointers the loops end on. 13 asserts.

- Before: the compiler segfaults in the 8 optimising configurations of the autotest (`-n` and `-bc`, each at default, `-O2`, `-Os`, `-O3`); `-O0` passes.
- With only the first change: it compiles, but the test still fails in the same eight configurations: 10 of its 13 checks are wrong at the default level, `-O2` and `-Os`, and 8 at `-O3`.
- After: `Emulation result 0` in all ten configurations.

### Validation

- `make -k -j2 -C make check`: 1551 emulations, all result 0. The suite on 4da3147 has 1541 and no failures; the 10 extra are the new test in its ten configurations.
- The 159 autotest sources (the new test included) and 26 small reproducers from the NetHack port, 185 files, compiled in five configurations (`-n` at `-O2`, `-Os`, `-O0`, `-O3`, and `-bc -O2`) with 4da3147 and with this change, and the `.prg` files compared: of the 846 cases that compile with both, 845 are byte identical. The one that differs is `testint16mul.c` at `-bc -O2`, whose output also differs between two builds of the same compiler source; a repeat of the comparison with a second build of this change gave 846 of 846 identical. The only status changes are the four optimising configurations of the new test going from crash to ok.

Found while porting NetHack 3.4.3 to the C64 (`shknam.c` counts its table of shopkeeper names this way). Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described.
````
