# 05. Fix wrong exit data set of merged blocks and wrong exit block after value select expansion

| | |
|---|---|
| Branch | `fix/o0-nested-cond` in `~/src/oscar64-dev`, commit `1fa788c58389`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/05-o0-nested-cond.patch`](../../tools/oscar64-upstream/patches/main/05-o0-nested-cond.patch) |
| Kind | compiler crash with native code (wrong code once the crash is fixed alone) |
| Since | 83e805b (2026-08, already in v1.32.273); the exit-block hand-over bug since fb67321 (2025-07) |
| NetHack | None known. With native code the shape segfaults v1.32.273 and main at every level, `-Os` included, so if NetHack hit it we would see a crash, not wrong code; no NetHack file is known to (the `shknam.c` crash on v1.32.273 is a different bug, in `LoadConstantOperand`). Found by our corpus comparison at `-O0`. |
| Reviews | Opus (round 2, ran probes): submit-after-changes, 1 high, 1 medium, 2 low; Codex (read the diff): submit after changes; fix-up: ready; final Codex check: submit after changes; final Opus re-review: submit-after-changes |
| Recommendation | **Submit, both fixes in one PR: the first alone turns a compiler crash into wrong code. Lower priority for us than #1-#4.** |

## In plain words

Two mistakes in Oscar64's 6502 back end are fixed. First, when the compiler glues two code blocks together at the very end, a line added in August 2026 copied the "what we know about the CPU flags" note from the wrong block, so a plain jump could be emitted as a conditional branch that is never taken and a function like `c ? 3 : (d ? 4 : 5)` ran off its end; the same line crashed the compiler when the glued block was the last one. Second, and bigger than the earlier rounds said: since July 2025, when the compiler rewrites a "p ? 242 : -127"-style choice at the end of a function into a branch, it marked the wrong piece as the function's exit, so such a function silently returned early without storing its results, at every optimisation level, -Os included; since August 2026 that showed up as the compiler crash instead. The final reviewer proved this with a three-line function, which is now in the test suite and crashes both upstream main and our pinned v1.32.273 at all five native levels. The branch now picks the exit block by looking for the one block with no successors (which also covers a rarely used rewrite the previous version would have got wrong, though no program has been found that reaches it), adds a check that aborts the compile rather than mis-compiling if that ever goes wrong, and corrects the wording everywhere. Everything was re-run on the final commit: the full test suite (1561 runs, no failures), the corpus against upstream main (only the expected differences) and against the previous version of the fix (byte-identical). nethack64 builds with -Os, so this matters to us only if a NetHack file turns out to hit the end-of-function value-select shape; none is known to. The only thing left for you is the commit trailer (model name and session link), which I did not touch.

## The fix

Two changes in oscar64/NativeCodeGenerator.cpp on 4da3147, one commit. (1) MergeBasicBlocks: copy mNDataSet before advancing mTrueJump (unchanged from bed2d1b). (2) ExpandADCToBranch exit hand-over: the unconditional walk is replaced by a breadth-first search (bounded at 16 blocks) from the split block's successors for the first block with neither mTrueJump nor mFalseJump, which is the tail that inherited the exit block's missing successors and the temporary RTS; this also covers the two sign-extension expansions where the tail sits behind a conditional block (the old walk would have fallen back to the wrong arm). Fallback to mTrueJump kept. (3) New assert before 'Remove temporary RTS' that the popped instruction is an RTS, so a wrong hand-over aborts the compile instead of returning early. Tests: autotest/ternaryexitblocktest.c gains g() (the reviewer's allcrash.c shape, gi = p1 ? 242 : -127), so the test now crashes the before-compilers at every native level, not only -O0; comment corrected. nestedternaryjumptest.c and autotest.bat unchanged. Commit message and PR text corrected: bug 2 occurs at every -n level, dates from fb67321 and was a silent miscompile until 83e805b; 'stale' -> 'wrong'; volatile sentence qualified; limitations extended.

## Regression test

autotest/nestedternaryjumptest.c (unchanged): f, fv, fs reproduce the merged-block data-set bug; before, Emulation result -1 in all five -n configurations on 4da3147 and v1.32.273, passes -bc; after 10/10. autotest/ternaryexitblocktest.c (extended): f = unsigned char select at the end of a function (its select survives to ExpandADCToBranch only at -n -O0); g = `if (p0) ga = 2; else ga = 4; gb = (p0 >> 2) & 1; gi = p1 ? 242 : -127;` (int select, survives at every level). Before: compiler segfault (rc 139) in all five -n configurations on 4da3147 and v1.32.273, -bc passes; with the merge fix alone or on 66f227c: -1 in all five -n configurations (early return without the stores); after: 10/10. Both registered in autotest.bat after mixedwidthternary.c and picked up by the autotest makefile wildcard.

## Evidence

*These are the fix-up round's results, for commit `bed2d1b01064`. The last round changed the code; its re-validation of the final commit is under "Last round" below.*

**Repro matrix.** All with `oscar64 -ea -g {-bc|-n} {default|-O2|-O0|-Os|-O3}`, compilers 4da3147 (base) / v1.32.273 (pinned) / final fix bed2d1b. nestedternaryjumptest.c: base and pinned -bc x5 = 0, -n x5 = -1; fix 10 x 0. ternaryexitblocktest.c and review/cases/crash_min.c: base and pinned 9 x 0 and -n -O0 = segfault (rc139); fix 10 x 0. tools/oscar64-upstream/cases/o0_nested_conditional_int.c (expects 4): base and pinned 4 everywhere except -n -O0 = -1; fix 10 x 4. review/cases/prbody_example.c: base and pinned -1 at -n and -n -O0, 0 elsewhere; fix 10 x 0. cpp_probe.cpp (template/lambda/member): base and pinned -1 at -n -O0; fix 10 x 0. single_f_volatile_globals.c: base -1 in all five -n (pinned only at -n, -n -O0); fix 10 x 0. single_f_addr_taken.c: base/pinned -1 at -n and -n -O0; fix 10 x 0. s17_f5.c (fuzz-derived): base/pinned segfault at -n -O0; fix 10 x 0. ntj_volatile.c: base/pinned -1 in all five -n; fix 10 x 0 (no emulator hang observed here). probe_char.c: 7 everywhere with all three compilers (control). Per-function controls on 4da3147 (ntj_only_*): f -1/0/-1/0/0, fl pass, fp pass, fv -1/0/-1/0/0, fs 0/0/-1/0/0. Generated code for the PR example at -n: base `ORA #$04 / f0 eb BEQ f.s7`, fix `ORA #$04 / 4c f6 08 JMP f.s7`. Reviewer fuzz programs (800, 4160 runs, recorded 4da3147 and merge-only results vs final): pass/pass/pass 3714; fail/fail/fail 215; fail->pass 149; hang->pass 6; segfault->wrong->pass 44; segfault->pass->pass 2 (gen_313, gen_384: the only two passing runs whose code changed between merge-only and final); segfault->wrong->pass 1 (gen_17); compiler-assert/double-free identical 29; pass->fail 0.

**Autotest.** Final binary (built from bed2d1b source): `make -k -j4 -C .../o0-nested-cond/make check > /home/jolyon/nethack64/build/oscar64-wt/o0-nested-cond-scratch/autotest-fixup2.log`, make exit 0, 1561 "Emulation result 0" lines. autotest_diff.py autotest-base-4da3147.log autotest-fixup2.log: emulations base 1541, new 1561 (+20 = two new tests x 10 configurations), new failures 0, fixed 0, failing in both 0. An earlier probe run of the same code plus a temporary assert on the popped RTS (scratch/fixup/autotest-probe-assert.log) gave the same 1561/0/0/0 and the assert never fired.

**Corpus.** corpus_diff.py ~/src/oscar64-base/bin/oscar64 (4da3147) vs final bin/oscar64, --out /home/jolyon/nethack64/build/oscar64-wt/o0-nested-cond-scratch/corpus-fixup2 -j4: 184 files (166 autotest sources + 18 nethack64 tests/oscar64-repros) x 5 configurations (-n -O2, -n -Os, -n -O0, -n -O3, -bc -O2) = 920 builds. Both compile 854; identical 848; different 6; status changed 1; both fail 65 (13 files x 5: six autotest part files that are not standalone programs and seven repros that are compile failures by design). The 6 differences: nestedternaryjumptest.c at n-O2/n-Os/n-O0/n-O3 (the bug being fixed, BEQ -> JMP; the file also gained four asserts); structreturncontrolflow.c n-O0 (482 -> 481 bytes, a JMP right after LDX #$00 becomes the intended BEQ; passes with both, covered by make check); testint16mul.c bc-O2 (the known include-path quirk). The status change: ternaryexitblocktest.c n-O0 crash -> ok (the new test). Autotest-only view: 830 builds, 799 compile with both, 793 identical. Additional identity checks with the final binary: 67 samples compiled standalone at -n -Os, -n -O2, -n -O0: 66/66/64 compile with each compiler (same set; memmap/tsr.c, and at -O0 also hires/func3d.c and hiresmc/func3d.c, fail with both), 0 differing PRG, total bytes identical (434425 / 433522 / 483459). nethack64 src/ (main.c, hal/sys.c, hal/screen80.c) at -Os -g, -Os -g -dAUTOTEST, -O2 -g, -O0 -g: byte-identical PRGs (10335 / 12233 / 10173 / 12028 bytes).

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| opus | high | Merge fix turns a -n -O0 compiler segfault into silent wrong code; separate exit-block hand-over bug in ExpandADCToBranch | fixed |
| opus | medium | Regression test: fl and fp never reproduce the bug, -O2/-Os/-O3 failures depend on fp taking addresses, no test for the segfault symptom | fixed |
| opus | low | PR text inaccurate: 'returns -1', '-O2 with more functions', coverage claims, omitted segfault, 'only consumer', 'cannot make code larger', session link, model name | fixed |
| opus | low | Optionally copy mFDataSet as well when absorbing a conditional block | deferred |
| opus | low | Optionally assert that the instruction removed as the temporary RTS is an RTS | deferred |
| codex | medium | Copying the right block's data set does not prove it is current (Z/C conservative after late passes); mFDataSet transition unreviewed | deferred |
| codex | low | Test coverage less than advertised: fl not a wide-operand test, fs const-args/inlinable, first failing assert stops the rest, only f has all four combinations | fixed |
| codex | low | PR conflates emulator failure with a C return value; default-level failure of the PR example unsubstantiated | fixed |
| codex | low | Co-Authored-By trailer names Claude Opus 5.5 although the session ran on Claude Fable 5.1 | deferred |

<details><summary>Evidence for each finding</summary>

1. **Merge fix turns a -n -O0 compiler segfault into silent wrong code; separate exit-block hand-over bug in ExpandADCToBranch** (fixed)

   Reproduced: review/cases/crash_min.c at -n -O0: 4da3147 and v1.32.273 exit 139 (segfault), merge-fix-only build gives Emulation result -1 with the reviewer's listing (.s8: RTS instead of LDA #$0d; stale RTS at the end of .s7). Reviewer's variant builds confirm independence: nocopy and nojtb builds give the same -1 (not data-set dependent), exitonly build passes crash_min but still fails prbody_example at -n/-n -O0. Root cause confirmed in source: every expansion in ExpandADCToBranch moves the tail (with the temporary RTS) into rblock, reached either directly or through one unconditional block (neblock/mblock/iblock/ccblock), while the hand-over at :26633 locked mTrueJump. Adopted the reviewer's walk (follow mTrueJump while unconditional, 8-step limit, fall back to old behaviour), in upstream style with a comment. After: crash_min.c, cpp_probe.cpp, s17_f5.c pass 10/10; all 47 fuzz segfault runs (44 that gave wrong results with the merge fix alone, 2 that passed by luck, 1 whose only output was a warning) now pass; a probe build asserting that the instruction popped as the temporary RTS is an RTS never fired across the full autotest (1561 emulations); hand-over change is a no-op on the rest of the corpus and on 67 samples (byte-identical).

2. **Regression test: fl and fp never reproduce the bug, -O2/-Os/-O3 failures depend on fp taking addresses, no test for the segfault symptom** (fixed)

   Reproduced per-function on 4da3147 (-n/-O2/-O0/-Os/-O3): f -1/0/-1/0/0, fl all pass, fp all pass, fv -1/0/-1/0/0, fs 0/0/-1/0/0, exactly as the reviewer measured. Test comment now says f, fv, fs reproduce and fl, fp are controls, and that fp(&a,&b) keeps f and fv on 16-bit compares at -O2/-Os/-O3; the fourth input combination added to every function. New autotest/ternaryexitblocktest.c (crash_min.c with plain globals, which still segfaults 4da3147 and v1.32.273 at -n -O0, rc139) registered in autotest.bat. Both tests fail before (nestedternaryjumptest: -1 in all five -n configs; ternaryexitblocktest: segfault at -n -O0) and pass 10/10 after, on the final binary.

3. **PR text inaccurate: 'returns -1', '-O2 with more functions', coverage claims, omitted segfault, 'only consumer', 'cannot make code larger', session link, model name** (fixed)

   PR body rewritten: says the program falls off the end of f and the emulator reports -1; the -O2/-Os/-O3 trigger is arguments whose range cannot be narrowed (verified: single_f_volatile_globals.c fails all five -n configs on 4da3147); fl/fp described as controls; segfault symptom and second fix included; BuildPlacement named as another reader; no size guarantee claimed (the new test grows at -n -O2 as the reviewer observed); no claude.ai link in the PR body. Co-Authored-By model name kept as the task instructed (see codex finding 4).

4. **Optionally copy mFDataSet as well when absorbing a conditional block** (deferred)

   grep of all mFDataSet uses: the dump (15892-15901), BuildEntryDataSet (17375-17426) and BitFieldForwarding (49077+); the latter two assign mFDataSet = mNDataSet before reading it, so nothing reads the stale value after the final merge. Pure consistency change with no observable effect; left out to keep the patch minimal, noted in the PR's limitations.

5. **Optionally assert that the instruction removed as the temporary RTS is an RTS** (deferred)

   Built a probe binary with assert(mExitBlock->mIns.Last().mType == ASMIT_RTS) at the Pop and ran the full autotest (1561 emulations, 0 failures, assert never fired) and the 800 fuzz programs (no new compile failures). Not shipped, to keep the patch minimal; the result is reported as evidence that no other autotest path leaves the exit role on the wrong block.

6. **Copying the right block's data set does not prove it is current (Z/C conservative after late passes); mFDataSet transition unreviewed** (deferred)

   No concrete defect proposed or found. Empirical evidence added: 800 fuzz programs / 4160 runs with 0 pass-to-fail transitions and 121 passing runs with changed code (the reviewer inspected the new branches as always taken); corpus 848/854 byte-identical with every difference explained; nethack64 src identical at -Os/-O2/-O0. The staleness risk of the absorbed block's own set exists independently of this patch (BranchAccuAlternativeElimination maintains Z explicitly); stated as a known limitation in the PR rather than claimed away. mFDataSet: see opus finding 4.

7. **Test coverage less than advertised: fl not a wide-operand test, fs const-args/inlinable, first failing assert stops the rest, only f has all four combinations** (fixed)

   fl and fp are now documented as controls (they never failed before the fix). fs kept: measured alone it fails at -n -O0 on 4da3147 (so it does reach the native merge and is not folded away). Fourth input combination added to fl, fp, fv, fs. flwide variant not added: it would be another control, not a reproduction. The first-assert-stops point is inherent to assert-based autotests; the per-function reproduction is given in the test comment and the PR instead of claiming independent coverage.

8. **PR conflates emulator failure with a C return value; default-level failure of the PR example unsubstantiated** (fixed)

   Wording changed to 'falls off the end of f ... the emulator reports -1 and the compiler exits with status 20'. Default-level failure verified: prbody_example.c on 4da3147 and v1.32.273 gives -1 at -n and -n -O0, passes the other eight; passes 10/10 after.

9. **Co-Authored-By trailer names Claude Opus 5.5 although the session ran on Claude Fable 5.1** (deferred)

   Both reviewers flagged it. The task for this round says to keep the existing trailer lines as they are, so the commit still carries 'Co-Authored-By: Claude Opus 5.5' and the Claude-Session line. This session also ran on Claude Fable 5.1. Jolyon should amend the trailer (and drop the session link if he does not want it in upstream history) before pushing.

</details>

## Last round: final-check findings and what happened to them

Changed in the last round: code. Commit before it: `bed2d1b01064`.

| From | Severity | Finding | Resolution |
|---|---|---|---|
| opus final check, finding 1 | medium | Exit-block bug is not -O0-only; test only guarded -n -O0; PR/commit history wrong | fixed |
| opus final check, finding 2 | low | Walk picks the wrong block for the sign-extension expansions (latent) | fixed |
| opus final check, finding 2 (optional assert) | low | Ship the assert that the popped temporary RTS is an RTS | fixed |
| opus final check, finding 3 (a)-(e) and PR text issues 1-7 | low | PR text overclaims: volatile sentence, 83e805b 'never saw this', 'every expansion pattern', 'stale', test comment, missing limitations | fixed |
| codex final check, finding 2 | low | ternaryexitblocktest.c comment conflates baseline crash with merge-only early return | fixed |
| codex finding 1 / opus finding 3 (f) | low | Co-Authored-By model name and Claude-Session link in the commit trailer | left-for-jolyon |

<details><summary>Evidence, and what was re-run</summary>

1. **Exit-block bug is not -O0-only; test only guarded -n -O0; PR/commit history wrong** (fixed)

   Reproduced: the reviewer's adv/allcrash.c segfaults (rc 139) both ~/src/oscar64-base (4da3147) and ~/src/oscar64 (v1.32.273) in all five -n configurations and passes -bc 5/5; bed2d1b passes 10/10. Added that function as g() in autotest/ternaryexitblocktest.c (plain globals z=0,o=1,v=4; still rc 139 at all five -n levels on both before-compilers, 10/10 after). The reviewer's merge-only and 66f227c (83e805b's parent) builds give Emulation result -1 at all five -n levels on the new test, confirming the silent miscompile before 83e805b; git log -S confirms the hand-over line came in with fb67321 (2025-07-09, 'Fix split of function exit block in carry optimizastion'). Commit message, test comment, PR title and body no longer say -O0 for this bug and state the fb67321 -> 83e805b history.

2. **Walk picks the wrong block for the sign-extension expansions (latent)** (fixed)

   Confirmed in NativeCodeGenerator.cpp :25468-25585: both sign-extension patterns put the tail fblock behind ablock (BCC), so the old walk stopped at ablock and fell back to mTrueJump = ablock. Adopted the reviewer's breadth-first search over mTrueJump/mFalseJump for the first block without successors (the tail inherits the exit block's null successors). Verification: an instrumented build computing both the walk and the BFS over 160 autotest sources, 29 probe/case files, 2 new sign-extension candidates and 26 nethack64 repros at five -n levels reported 28 hand-overs, 0 disagreements, 0 fallbacks, 0 non-RTS pops; corpus_diff bed2d1b vs new: 855/855 builds byte-identical, 0 status changes. My own sign-extension candidates (c1.c, c2.c, 14 functions) never put that pattern into the exit block either, so the case stays unreached; the PR now says so ('every value select expansion' claim replaced by the structural argument plus a limitation note).

3. **Ship the assert that the popped temporary RTS is an RTS** (fixed)

   Shipped as assert(mExitBlock->mIns.Size() > 0 && mExitBlock->mIns.Last().mType == ASMIT_RTS) before the Pop at :73187. Reasons: NativeCodeGenerator.cpp already has 119 asserts; the makefile build has no NDEBUG so it is live there (the Visual Studio release configurations define NDEBUG, noted in the PR); with the merge fix a wrong hand-over would otherwise be a silent miscompile. It never fired: full autotest 1561 emulations, 0 failures; corpus 925 builds with identical outcomes to bed2d1b.

4. **PR text overclaims: volatile sentence, 83e805b 'never saw this', 'every expansion pattern', 'stale', test comment, missing limitations** (fixed)

   PR body rewritten: volatile sentence qualified (main fails -O2/-Os/-O3; v1.32.273 only default and -O0, per the reviewer's measurement); 83e805b sentence replaced by the fb67321 history; expansion-pattern claim replaced by the BFS argument; title now says 'wrong' not 'stale'; ternaryexitblocktest.c comment separates the pre-83e805b early return from the 4da3147 crash; Known limitations now list the BFS fallback (guarded by the assert) and SplitAt/SplitBlock (:16962, :72157) moving the exit role without mLocked (pre-existing, all affected autotest functions pass).

5. **ternaryexitblocktest.c comment conflates baseline crash with merge-only early return** (fixed)

   Comment rewritten: early return without stores until 83e805b, which made the final MergeBasicBlocks dereference a null successor so the compiler crashed; f's select survives to ExpandADCToBranch only at -n -O0, g's at every level.

6. **Co-Authored-By model name and Claude-Session link in the commit trailer** (left-for-jolyon)

   Trailer lines left exactly as they were, per the task; the PR body carries no claude.ai link.

**Re-validation.** Rebuilt from e8e2d25 source: make -C .../o0-nested-cond/make -j6 compiler, rc 0. Ten configurations (oscar64 -ea -g {-bc|-n} {none,-O2,-O0,-Os,-O3}) with the new binary, all 10/10 pass: autotest/nestedternaryjumptest.c, autotest/ternaryexitblocktest.c (new version), allcrash.c, allcrash_byte.c, allcrash_ret.c, crash_min.c, prbody_example.c, cpp_probe.cpp, s17_f5.c, o2crash1.c, single_f_volatile_globals.c, sext1.c, sext2.c, sx_a..sx_h.c, and two new sign-extension candidates c1.c/c2.c. Before: new ternaryexitblocktest.c segfaults (rc 139) at all five -n levels on 4da3147 and v1.32.273, passes -bc; gives -1 at all five -n levels with the reviewer's merge-only and 66f227c builds; nestedternaryjumptest.c gives -1 at all five -n levels on 4da3147. Instrumented scratch build (walk and BFS both computed): 28 hand-overs over autotest + cases + repros + candidates x 5 -n levels, 0 differ, 0 fallback, 0 non-RTS pop. Full autotest: make -k -j4 check > o0-nested-cond-scratch/autotest-final.log, 1561 'Emulation result 0'; autotest_diff.py vs autotest-base-4da3147.log: base 1541, new 1561, new failures 0, fixed 0, failing in both 0. corpus_diff.py 4da3147 vs new (--out o0-nested-cond-scratch/corpus-final -j4): 185 files x 5 = 925 builds; both compile 851, identical 845, different 6 (nestedternaryjumptest.c n-O2/n-Os/n-O0/n-O3 = the bug being fixed plus the added asserts; structreturncontrolflow.c n-O0 = 482->481 bytes, JMP after LDX #$00 becomes BEQ, passes; testint16mul.c bc-O2 = known include-path quirk); status changed 4 (ternaryexitblocktest.c crash -> ok at n-O2/n-Os/n-O0/n-O3); both fail 70 = 14 files x 5 (the 13 known non-standalone/by-design files plus tests/oscar64-repros/r25_constant_argument_and_indirect_call.c, added to nethack64 since the last round, compile error rc 20 with both compilers). corpus_diff.py bed2d1b vs new (--out o0-nested-cond-scratch/final/corpus-bfs): 855 both compile, 855 identical, 0 status changes. Evidence in /home/jolyon/nethack64/build/oscar64-wt/o0-nested-cond-scratch/final/ (build logs, scan/handover.txt, corpus-*.log, saved bed2d1b binary, instrumented tree).

</details>

## Final check (Codex, read-only, on the final commit)

<details><summary>SUBMIT AFTER CHANGES</summary>

VERDICT: SUBMIT AFTER CHANGES

1. **low — Commit trailers:** `Co-Authored-By: Claude Opus 5.5` contradicts the stated model provenance. Correct or remove that attribution before submission. Remove the `Claude-Session` link unless Jolyon intentionally wants it in permanent upstream history.

2. **low — `autotest/ternaryexitblocktest.c:9–11` and commit message:** The explanation conflates the baseline compiler crash with the early return observed **after applying only the merge fix**. State that distinction explicitly: the baseline dereferences a null successor during compilation; fixing that alone exposes removal of the wrong instruction and premature return. The PR body already makes this distinction correctly.

No concrete code defect or regression-test blocker is apparent from the supplied diff and evidence. The remaining data-set freshness concern is appropriately disclosed, rather than proven absent.

</details>

## Final check (Opus, re-ran the evidence)

**submit-after-changes.** Both code changes are correct and I could not make them produce wrong code: they fix the two bugs and changed nothing else I compiled. But the second bug is bigger than the PR says. A three-line function crashes both upstream main and our pinned compiler at every optimisation level, including -Os. Before August's upstream change the same code was compiled wrong without any error, and the new test only catches the bug at -O0. Add that three-line test and fix the -O0 and history wording (and the commit trailer), and it is ready to send.

- [medium] The exit-block bug is not -O0-only. The new test only guards the hand-over fix at -n -O0, and the PR and commit understate the bug and get its history wrong: 1. Add allcrash.c as an autotest, plus allcrash_byte.c if wanted (same function with `gc = p1 ? 16 : 1`), next to or instead of ternaryexitblocktest.c. It segfaults 4da3147 and v1.32.273 in all five native configurations, gives -1 in all five with merge-only, and passes 10/10 with bed2d1b.
2. Reword these to say the bug occurs at every -n level, not only -O0:
   - Root cause 2 in the PR.
   - The PR sentence "with -n -O0 the compiler then segfaults".
   - The commit message ("so at -O0 functions returned early and skipped their stores").
   - The ternaryexitblocktest.c comment.
3. State the history correctly: the hand-over bug dates from fb67321 (2025-07-09) and silently miscompiled these functions at every native level until 83e805b's line order turned it into a crash. Fixing only the merge would make it silent again.
- [low] The walk still picks the wrong block for the sign-extension expansions, so "every expansion pattern" is not true (latent: never triggered in my tests): Choose one of two options:
- Reword the PR, commit and code comment ("every value select expansion" rather than "every expansion pattern") and list the sign-extension case under Known limitations.
- Or replace the walk with a short breadth-first search over mTrueJump and mFalseJump from the split block for the one block that has neither successor (the tail inherits the exit block's null successors). I built this variant (scratch src-var/bfs.cpp). It is byte-identical to bed2d1b on all 237 compiles where a hand-over happens, and passes 10/10 on allcrash, allcrash_byte, crash_min, ternaryexitblocktest, nestedternaryjumptest, o2crash1, prbody_example and s17_f5.

Optionally, also ship the earlier reviewer's assert that the instruction popped as the temporary RTS really is an RTS. Asserts are live in normal oscar64 builds, so this fallback would then abort the compile instead of producing wrong code.
- [low] PR text: overclaims and inaccuracies: - Qualify the volatile sentence: on main; v1.32.273 fails it only at the default level and -O0.
- Replace sentence (b) with the history from finding 1.
- Fix (c) as in finding 2.
- Retitle, e.g. "Fix wrong exit data set after merging blocks and wrong exit block after value select expansion".
- Correct the test comment.
- Decide on the trailer, session link and footer before pushing.

## Before submitting

- Done 2026-11-12 (Jolyon's decision): the commit ends with one `Co-Authored-By: Claude <noreply@anthropic.com>` line and no session link (message only; the tree is the one validated, commit `e8e2d25fbe9c` before), and the PR text ends with the same AI-assistance sentence as every other PR.

## Risks and limitations

The BFS changes which block is locked as the exit block only when the exit block was split by ExpandADCToBranch; on the corpus (855 builds) and in all 28 observed hand-overs it chooses the same block as the old walk, and the sign-extension case it additionally covers was never reached in any test, so that path is reasoned, not exercised. If no successor-less block is found within 16 blocks the code falls back to mTrueJump and the new assert aborts the compile in makefile builds (the Visual Studio release configurations define NDEBUG, so there it would be a silent early return as before). The assert itself could in principle fire on a shape nobody has compiled; it never fired on 1561 autotest emulations, 925 corpus builds or the reviewer's 857+400 fuzz programs. The merge fix makes PutJump see the absorbed block's own exit set; a non-conservative set left by a late pass would still shorten a JMP wrongly (pre-existing; no instance found). SplitAt/SplitBlock move the exit role without mLocked (pre-existing; affected library functions pass). Code size can move by a byte where JMP and Bcc swap; the new test is 28 bytes larger at -n -O2. Not tested: real hardware. Commit trailer (model name, session link) still as Jolyon left it.

## Related bugs found, not fixed here

From the reviewer's 800 fuzz programs, unchanged by this fix (seen with 4da3147 and the fix compiler; v1.32.273 not run on them): (a) 215 runs give wrong results identically before and after, e.g. r1 gen_111 fails natively at every level but passes in bytecode (fuzz/r1/w/gen_111/t.c, -n ... FAIL:31), gen_110 fails in -bc and -bc -O2 too; (b) 29 compiler crashes: assertion NativeCodeGenerator.cpp:17819 (gen_169, gen_250 at -n, -O2, -Os, -O3), InterCode.cpp:9869 (r2 gen2_1074, gen2_1280 at -n -O2/-O3), Array.h:572 (gen2_1267, gen2_1270 at -n -O2/-O3), NumberSet.h:50 (gen2_1014 at -n -O3), "double free or corruption" (gen_130, gen_169, gen2_1060 at -n -O0). Also observed: single_f_volatile_globals.c fails all five -n levels on 4da3147 but only -n and -n -O0 on v1.32.273 (code generation differs between the two, not a bug by itself). Unverified observation from reading the code: NativeCodeBasicBlock::SplitAt (:16962) moves mExitBlock to the new tail block without transferring mLocked; not probed.

## Draft pull request

**Title:** Fix wrong exit data set of merged blocks and wrong exit block after value select expansion

````markdown
A nested conditional with `int` operands produces wrong native code when the outer condition is false. In this example `f` falls off its end, the emulator reports `Emulation result -1` and the compiler exits with status 20:

```c
#include <assert.h>

__noinline int f(int c, int d)
{
	return c ? 3 : (d ? 4 : 5);
}

int a = 0, b = 1;

int main(void)
{
	assert(f(a, b) == 4);
	assert(f(a, a) == 5);
	return 0;
}
```

Reproduce with `oscar64 -ea -g -n example.c` (fails at the default level and with `-O0`). When the arguments cannot be range-narrowed to 0..1, for instance with `volatile int a = 0, b = 1;`, `main` (4da3147) also fails with `-O2`, `-Os` and `-O3`; v1.32.273 fails that variant at the default level and `-O0` only. `-bc` is a passing control. Present on `main` and in v1.32.273.

The generated code for `f` ends like this:

```
.s6:  LDA P2 ; d
      ORA P3
      BEQ .s8
.s9:  LDA #$01
.s8:  EOR #$01
      ORA #$04
      BEQ .s7     ; should be JMP .s7: Z is always clear after ORA #$04
```

**Root cause 1.** The final `MergeBasicBlocks` appends a single-entry successor to its predecessor. Since 83e805b ("Fix loss of exit values when merging basic blocks") it also copies the successor's exit register data set, so that `PutJump`/`JumpByteSize` (`JUMP_TO_BRANCH`) can turn the trailing `JMP` into a two-byte branch when Z or C is known (`BuildPlacement` reads the set too, for placement only). The copy happens after `mTrueJump` has been advanced:

```cpp
mTrueJump = mTrueJump->mTrueJump;
mNDataSet = mTrueJump->mNDataSet;   // data set of the block beyond the absorbed one
```

Here `BranchAccuAlternativeElimination` has rewritten the inner `d ? 4 : 5` into `LDA #1 / EOR #1 / ORA #4` with a jump to the shared store block; the `ORA #4` block is merged into the `EOR #1` block, and the merged block receives the store block's set (Z known set), so `PutJump` emits `BEQ` for the unconditional jump. The same line dereferences a null pointer when the absorbed block has no successor, and then the compiler segfaults, with `-n` at every optimization level, for example on this function (part of the second test below):

```c
unsigned char ga, gb;
int gi;

__noinline void g(unsigned char p0, unsigned char p1)
{
	if (p0) ga = 2; else ga = 4;
	gb = (p0 >> 2) & 1;
	gi = p1 ? 242 : -127;
}
```

**Root cause 2.** The block without a successor that gets absorbed there is the block holding the temporary RTS, which should be the locked exit block. The `p1 ? 242 : -127` is still a `CMP #1 / LDA #0 / ADC #$ff / AND / EOR` value select in the exit block when `ExpandADCToBranch` turns it into a branch and splits the block. The trailing instructions, including the RTS, move into a new block behind one arm of the branch, but the hand-over at the end of `ExpandADCToBranch` (introduced in fb67321, "Fix split of function exit block in carry optimizastion") locks `mTrueJump`, the arm itself, as the exit block. "Remove temporary RTS" then popped the arm's `LDA #imm`, the epilogue was appended there, and the function returned early without its stores. From fb67321 until 83e805b that was a silent miscompile at every optimization level (checked on 66f227c, 83e805b's parent: `Emulation result -1` in all five native configurations); 83e805b's copy line turned it into the crash, and fixing only the merge would make it silent again.

**Fix.** In `MergeBasicBlocks`, copy the data set before advancing `mTrueJump`, so the merged block keeps the exit values of the block it absorbed (what 83e805b intended). In `ExpandADCToBranch`, hand the exit block role to the first block behind the new branch that has no successors: the tail block inherited the exit block's null successors together with the temporary RTS, and in every expansion pattern it is the only such block, including the two sign extension expansions where it sits behind a conditional block (a plain walk along unconditional jumps would stop short there). The search is bounded and falls back to the previous behaviour if it finds nothing. An assertion before "Remove temporary RTS" now checks that the instruction removed is an RTS, so a wrong hand-over aborts the compile instead of producing a function that returns early (live in the makefile build; the Visual Studio release configurations define `NDEBUG`). Applied alone, the merge fix does not cure the second example and the hand-over fix does not cure the first; they are independent.

**Tests.** `autotest/nestedternaryjumptest.c`: `f`, a `volatile int` version and a `static` version reproduce the first bug (the `int` ones at `-n` and `-n -O0`, the static one at `-n -O0`); the `unsigned long` and pointer versions are controls that never failed, and `fp(&a, &b)` taking the globals' addresses keeps `f` on full 16-bit compares, which makes it fail at `-O2`, `-Os` and `-O3` as well. Before the fix it fails in all five native configurations of the autotest and passes the five `-bc` ones; after, 10/10. `autotest/ternaryexitblocktest.c`: `g` above, whose `int` select reaches `ExpandADCToBranch` at every level, and `f`, a `gb = p0 ? 16 : 1` byte select that reaches it only at `-O0`; before, the compiler segfaults in all five native configurations and passes the five `-bc` ones (with the merge fix alone, or on 66f227c, the five native runs give `Emulation result -1` instead); after, 10/10. Both are registered in `autotest.bat`.

**Validation** against `main` 4da3147 on Linux:

- Full autotest (`make -k -C make check`): 1541 successful emulations on the baseline, 1561 with the patch and the two new tests, no failures in either run.
- All autotest programs compiled with both compilers in `-n -O2`, `-n -Os`, `-n -O0`, `-n -O3` and `-bc -O2` (799 builds that compile with both): byte-identical except the new test and one program, `structreturncontrolflow.c` at `-n -O0`, where a `JMP` directly after `LDX #$00` becomes the intended `BEQ` (482 -> 481 bytes; it passes). `testint16mul.c -bc -O2` differs only by the include path, as on the baseline. The only status changes are the second test's four native builds (crash -> ok).
- 66 of the 67 samples compile standalone at `-n -Os` and `-n -O2`, 64 at `-n -O0`; the same ones with both compilers, and all 196 PRG files are byte-identical.
- 1257 generated conditional-heavy C programs (two generators), native and bytecode runs checked against gcc: every compiler segfault (47 at `-n -O0`, and 10 programs that also crash at `-n`, `-O2`, `-Os` and `-O3`), 149 wrong results and 6 hangs become passes; no run goes from pass to fail; the runs that fail or crash the compiler identically before and after are unrelated issues.
- An instrumented build reported every exit block hand-over over the autotest sources, the generated programs and the probes: the chosen block always held the temporary RTS, the fallback never ran, and the new assertion never fired.
- A small 6502 project of ours (about 10 KB) is byte-identical at `-Os`, `-O2` and `-O0`.

**Known limitations.** Tested in the built-in emulator only. The merged block's exit set is now the absorbed block's own set, so passes that run after the last `BuildEntryDataSet` have to keep it conservative, as before this change; no counterexample was found. The merge loop still does not copy `mFDataSet` (nothing reads it after the final merge). The sign extension expansions were never observed in an exit block, so that branch of the hand-over is covered by the search's construction and the assertion rather than by a test. `SplitAt`/`SplitBlock` move the exit block role without moving `mLocked` (pre-existing; the library functions where it happens pass). Code size can move by a byte in either direction where a `JMP` becomes a branch or vice versa; no size guarantee is intended.

Found while porting NetHack 3.4.3 to the C64; the failing cases came out of small reproducers from our project. Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described.
````
