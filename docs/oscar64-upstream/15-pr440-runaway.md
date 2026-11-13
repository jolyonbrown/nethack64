# 15. Fix exponential walks over chains of conditionals

| | |
|---|---|
| Branch | `fix/pr440-runaway` in `~/src/oscar64-dev`, commit `ce1a99b576c4`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/15-pr440-runaway.patch`](../../tools/oscar64-upstream/patches/main/15-pr440-runaway.patch) |
| Kind | compiler runs out of memory (exposed on main by #440) |
| Since | the three walks are old (v1.32.273 and before); bf42402 (#440, 2026-10-24) exposed them at `-O2`/`-Os`/`-O3` |
| NetHack | Compat #30 (repro r26). `explode.c`: with upstream bf42402 (PR #440, which the ADR-0007 compiler carries for r25) the compiler grows past 8 GB on `explode()` and the kernel kills it; this machine's OOM killer stopped oscar64 44 times this week. v1.32.273 has the same bug at `-O0`/`-O1`, and at `-Os` whenever nothing folds the conditions away (r26). Commit 8 of the proposed patched pin. |
| Reviews | Opus (one round, ran probes): use-after-changes, 0 high, 3 medium, 5 low; Codex (read the diff): submit after changes; fix-up: ready; final Codex check (2026-11-13): submit after changes, 2 open items below |
| Recommendation | **Submit early, with or right after #4: it fixes an out-of-memory regression that #440 exposed, and main needs #4 before it can compile `explode.c` at all.** |

## In plain words

The bug: some compiler passes walk backwards through a function's blocks without remembering where they have already been, so a run of N independent "if" statements in a row is walked 2^N times; one of those walks also stores every visit, which is how the compiler grew past 8 GB on NetHack's explode() and got killed. The fix gives each of the four functions a "seen it already" list, so each block is visited once; the compiler's output does not change (849 of 850 comparison programs byte-identical, the odd one out being a known quirk of the unpatched compiler). The compiler code did not change in this round. What changed is wording: the commit message's test paragraph (on both the upstream branch and the pin branch) now says how the coverage experiment was done (each check removed but its Push kept, which is why those builds cost memory) and gives honest, load-dependent timings instead of "half a second"; the test's header comment no longer understates what the file costs an unfixed compiler; and the PR text has a new Test section, the corrected 1.04 GiB figure, re-measured timing ranges, and a note that a follow-up PR fixes three more walks of the same kind. I re-ran the test on both fixed compilers (20 of 20 pass, about 40 MB and about a second each) and on the unfixed ones (they pass too, but take 10 to 66 seconds and half a gigabyte), which is why a regression would show as time and memory rather than a failed assert. The full autotest and the 850-file comparison were not repeated this round, because only a comment and the message changed since they were run. One thing worth knowing: the example in the PR gives the right answer in native code, but at four bytecode optimisation levels it prints a wrong sum because of a different, older compiler bug that the PR now names openly.

## The fix

Unchanged from the reviewed commit (oscar64/ is byte-identical to c15930d on main and 2eaf2f3 on the pin; the main and pin compiler hunks are identical). InterCodeBasicBlock::CollectBlocksToDominator returns early when the block is already in `body` (IndexOf before Push), so it collects each block once in first-reached order instead of once per path. InterCodeBasicBlock::IsDirectLoopPathBlock and NativeCodeBasicBlock::CheckLoopIndexXRegisters / CheckLoopIndexYRegisters keep their signatures as wrappers and gain an overload carrying an ExpandingArray of visited blocks. Files: oscar64/InterCode.cpp, InterCode.h, NativeCodeGenerator.cpp, NativeCodeGenerator.h, plus autotest/loopconditionpathtest.c (new, 179 lines) and autotest/autotest.bat (+3). Total 239 insertions, 3 deletions on each parent. This round changed only the test's header comment (4 insertions, 3 deletions) and the commit message's test paragraph, on both branches; each branch is still one commit on its parent (4da3147 / f0b9ee6), author and author date preserved, single trailer "Co-Authored-By: Claude <noreply@anthropic.com>", unsigned.

## Regression test

autotest/loopconditionpathtest.c (blob d70d7adfac3b85a2505f5601f93f8960ddc9c89c, identical on both branches), registered in autotest/autotest.bat. Three address-taken functions: f (24 conditionals calling a __noinline bump) reaches CollectBlocksToDominator and IsDirectLoopPathBlock; g (18 inlined, int loop count) reaches CheckLoopIndexXRegisters; h (18 inlined, char loop count, `last = n;` after the loop) reaches CheckLoopIndexYRegisters and, at -O0, CheckLoopIndexXRegisters. It cannot fail on an unfixed compiler by design (a failing version would have to exhaust memory on the maintainer's machine): unfixed compilers pass it at 531-532 MiB and 10-66 s per native configuration; a regression shows as time and memory. Runs this round on the final commits, all under ulimit -v 2000000 and a timeout, one at a time: 20/20 "Emulation result 0" on the two fixed compilers, three times over (loads 5 to 19); unfixed 4da3147 and unfixed pin f0b9ee6 pass in all ten configurations at 531-532 MiB; .prg files byte-identical fixed vs unfixed in 10/10 configurations for both pairs. Header comment now ends: "f then costs about half a gigabyte of memory, g and h compile time, some seconds to tens of seconds each per native configuration. With the fix the file needs about 40 megabytes and about a second."

## Evidence

**Repro matrix.** All mine this round, 2 GB address-space cap, no exit 137 anywhere.
PR example chain.c (28 conditionals):
- unfixed 4da3147: std::bad_alloc (rc 134) in all ten configurations, 3.4-5.2 s, 1044-1046 MiB.
- v1.32.273: -n -O0 and -n default bad_alloc at 1043 MiB after 6.5 s; -n -Os compiles in 2.7 s at 61 MiB, prints 400, "Emulation result 1" (the wrong code #440 fixes).
- fixed main ce1a99b: native 2.0-7.5 s (-O3 7.5 s, 164 MiB), prints 432, result 0 in all five native and at -bc -O0; -bc default/-O2/-Os/-O3 compile in 0.8-3.5 s (at most 110 MiB) but print 455/456 with "error 3007: Execution failed" (separate bytecode bug).
Test file loopconditionpathtest.c:
- fixed main: native 0.51-3.17 s elapsed (0.47-1.10 s CPU), 38-41 MiB; bytecode 0.23-1.26 s, 24-26 MiB; loads 5-17.
- fixed pin f001eba: native 0.55-3.03 s, bytecode 0.18-0.80 s, same memory.
- unfixed 4da3147: native 10.0-27.4 s at load 3-7, 37.9-66.2 s at load 14-20 (CPU 9.7-32.2 s); bytecode 1.9-2.7 s and 5.8-10.4 s; 531-532 MiB; all pass.
- unfixed pin f0b9ee6: native 16.9-32.6 s (load 9-11) and 30.6-59.2 s (load 11-16); bytecode 1.6-3.0 s; 531 MiB; all pass.
- splits on unfixed 4da3147, native: f alone 1.3-1.8 s at 531 MiB; g alone 8.0-12.4 s at 30-31 MiB (-O0: 0.30 s, walk not reached); h alone 5.4-29.7 s at 29 MiB.
Coverage spot-check with the existing variant binaries (pr440-test/bin/oscar64-{all,noCBD,noIDLPB,noCLIX,noCLIY}) on the final file, at -n and -bc -O0: all 40/24 MiB; noCBD 530/531 MiB; noIDLPB 274/24 MiB; noCLIX bad_alloc at 1,087,236 KB (1061 MiB = 1.04 GiB) / 24 MiB; noCLIY passes at 1,089,120 KB (1063 MiB) / 24 MiB. The full 100-compile coverage tables are the pr440test investigation's and its reviewer's, not re-run here.
functionpointerparamtest.c on fixed main: 10/10 "Emulation result 0".

**Autotest.** Not re-run this round: since the last full runs only the test's header comment and the commit message changed (oscar64/ and autotest.bat are byte-identical to c15930d / 2eaf2f3, and the compiler binaries were not rebuilt). Last full runs, by the pr440test agent with make -k -j2: main c15930d 1551 emulations against 1541 on 4da3147, none failing; I checked its log (/home/jolyon/nethack64/build/oscar64-wt/pr440-test-scratch/autotest-main.log): 1551 "Emulation result" lines, all 0. Pin 2eaf2f3: 1241 of 1241, none failing (as reported by that agent; log autotest-pin.log in the same directory). This round I ran the new test and functionpointerparamtest.c in all ten configurations on the final commits (all pass).

**Corpus.** Not re-run this round (compiler unchanged). From the original investigation: 184 programs (autotest and samples) in five configurations with patched and unpatched main builds, 849 of 850 .prg files byte-identical; the one difference, testint16mul.c at -bc -O2, also differs between two builds of the unpatched source. The compiler sources have changed only in comments since that run. This round: the new test's .prg is byte-identical between fixed and unfixed compilers in all ten configurations, on main and on the pin.

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| Opus review 1 | medium | A fourth walk of the same kind is still exponential: NativeCodeBasicBlock::IsSameRegisterSource | Not in this PR. The PR's "Not addressed here" now says #NNN (fork PR #16) fixes three more walks of the same kind: IsSameRegisterSource, CanJoinEntryLoadStoreZP and CheckSingleUseGlobalLoadStruct. The intro keeps "three recursive walks (four functions)" for what this change covers. |
| Opus review 1 | medium | The PR's last sentence says Jolyon did the reproduction and validation himself | Fixed. The body ends with the agreed paragraph: "Found while porting NetHack 3.4.3 to the C64. Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described." No first-person claims remain ("on the machine we measured" and "I can open an issue" were reworded). |
| Opus review 1 | medium | The OOMs were on this host and recur; the measurement harness has no memory cap | Fixed by the lead in nethack64 commit 30adeed (measure_oscar64.py and make repros cap every compile at 3 GB and report compiler-oom). Not part of the upstream PR. Every oscar64 run this round was under ulimit -v 2000000 with a timeout. |
| Opus review 1 | low | The regression test cannot fail before the fix | Kept by design and stated plainly: the commit message, the test header and the PR Test section all say a regression shows as compile time and memory, not as a failed assert, and give the measured cost on an unfixed compiler. |
| Opus review 1 | low | The PR describes the trigger more narrowly than it really is | Fixed earlier by the lead and kept: the second paragraph and the commit message describe the general shape first (one arm holding a long chain before the arms join; no loop or function pointer needed), then what #440 changed. |
| Opus review 1 | low | The explode.c validation figure needs another unmerged fix and misquotes the before-#440 number | Fixed in the PR: the explode.c bullet gives 2.7 s / 0.36 GB for v1.32.273 and says main also needs the function-pointer-member fix (#NNN = fork PR #4). Not re-measured this round. |
| Opus review 1 | low | The PR example is cut short, and one timing differs from this host | Fixed: the example is chain2.c in full (verified byte-for-byte against the file run). Timings reworded from this round's runs: unfixed "after 3 to 6 seconds"; fixed "within a few seconds" instead of "about a second"; the Validation bullet says 0.8 to 7.5 s and at most 164 MiB instead of "under 3 s and 170 MB". |
| Opus review 1 | low | makemon.c still hangs with the fixed pin (T1.6), for a different reason | Not this PR and not claimed by it; handled separately as fork PR #18 (fix/makemon-hang) per the lead's resolutions. |
| Codex review (gpt-6-astra) | medium | CollectBlocksToDominator does not preserve its exact output or its unrestricted input contract | Fixed in wording by the lead and kept: commit message, code comment and PR Fix section say it returns each block once in first-reached order and that its only caller starts with an empty array and only asks whether any collected block modifies a temporary. No code change. |
| Codex review (gpt-6-astra) | low | The visited comments equate discovery with completed verification on cycles | Fixed earlier by the lead in the code comments and message: a revisited block has already passed (or been searched without finding the target), or is still on the recursion stack, which only happens on a cycle without a loop head, where the old code never terminated. Unchanged this round. |
| Codex review (gpt-6-astra) | medium | The test's source does not establish coverage of all four functions | Resolved by the pr440test agent's extended test (third function h) and its four one-check-removed builds; the PR Test section and the commit message now describe that experiment, including that each Push was kept. Spot-checked this round on the final file. |
| Codex review (gpt-6-astra) | medium | "Cannot harm a machine running an older compiler" is unsupported | Removed earlier; the PR and commit message state the measured cost, the machine (4-core laptop shared with other jobs) and the load averages instead of an assurance. |
| Codex review (gpt-6-astra) | low | Remaining-walk claim not checkable from the packet; "three walks" versus four functions | Wording is "three recursive walks over the predecessor graph (four functions)"; the remaining walks are no longer an unverifiable aside but a pointer to the PR that fixes them (#NNN = fork PR #16). |
| Codex review (gpt-6-astra) | low | Several explanatory claims are stronger than the code supports | Fixed earlier by the lead and kept: "can be affected", "once per path to it", "for each loop-invariant condition it tries to move". Timing and memory figures are presented as measurements with their conditions. |
| Lead's coverage check | medium | No Y-walk coverage in the two-function test, and the lead's no-CollectBlocksToDominator variant was a no-op | Resolved by the pr440test agent: function h added (needs `last = n;` after the loop to reach the Y walk on v1.32.273), and the CollectBlocksToDominator variant rebuilt correctly. The final test covers all four checks; on the pin the Y walk is not reached at -O0. |
| pr440test review | medium | The commit message's test paragraph (both branches) overstates the fixed compiler's speed and leaves out how the coverage was measured | Fixed by amending both commits (ce1a99b, f001eba). The paragraph now says each check was removed "but its Push kept, so that every revisit also costs memory", that the X variant exceeds a 2 GB address-space limit in four of five native configurations, and gives timings as ranges with the load: 8 to 66 s against 0.4 to 3.2 s native, 1 to 10 s against 0.15 to 1.3 s bytecode. The rest of each message is unchanged; the pin keeps its "d2ea285 here" wording. |
| pr440test review | low | The PR test paragraph has a unit slip (1.06 GiB), omits that the Push was kept, and gives timing ranges narrower than the re-runs | Fixed in the new Test section: 1.04 GiB; "each with one visited check removed but its `Push` kept"; timings re-measured on main and given as ranges with load averages (unfixed 10 to 66 s native, 2 to 10 s bytecode; fixed 0.5 to 3.2 s and 0.2 to 1.3 s), with CPU time alongside. |
| pr440test review | low | The PR draft does not end with the sentence the investigation quoted | Settled by Jolyon's decision rather than the reviewer's suggested wording: the body ends "Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described.", preceded by "Found while porting NetHack 3.4.3 to the C64." |
| pr440test review | low | The test's header comment understates what g and h cost an unfixed compiler | Fixed on both branches (the only file change this round): "f then costs about half a gigabyte of memory, g and h compile time, some seconds to tens of seconds each per native configuration. With the fix the file needs about 40 megabytes and about a second." |
| pr440test review | low | Exported patches, the pin, and the stacked walks2 branch still carry the old commit | Partly resolved, rest is the lead's. fix/exponential-walks-2 was already rebased onto ce1a99b by another agent (8b2fa93). The two exported patches in nethack64 are still stale and untracked (not mine to overwrite); fresh exports are in f15-scratch/patches-main and patches-pin. The accepted pin nethack64/v1.32.273-pin is still c2f5cab and was not touched. |

<details><summary>Evidence for each finding</summary>

1. **A fourth walk of the same kind is still exponential: NativeCodeBasicBlock::IsSameRegisterSource** (Not in this PR. The PR's "Not addressed here" now says #NNN (fork PR #16) fixes three more walks of the same kind: IsSameRegisterSource, CanJoinEntryLoadStoreZP and CheckSingleUseGlobalLoadStruct. The intro keeps "three recursive walks (four functions)" for what this change covers.)

   Reviewer: N=18 chain takes 29.78 s at -Os -n on fixed main, about 2.8x per conditional, also on unfixed 4da3147. fix/exponential-walks-2 is now 8b2fa93 directly on ce1a99b (git log --oneline).

2. **The PR's last sentence says Jolyon did the reproduction and validation himself** (Fixed. The body ends with the agreed paragraph: "Found while porting NetHack 3.4.3 to the C64. Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described." No first-person claims remain ("on the machine we measured" and "I can open an issue" were reworded).)

   docs/OSCAR64-UPSTREAM.md decision 3 (lines 27-31) gives this exact sentence; pr_body in this result.

3. **The OOMs were on this host and recur; the measurement harness has no memory cap** (Fixed by the lead in nethack64 commit 30adeed (measure_oscar64.py and make repros cap every compile at 3 GB and report compiler-oom). Not part of the upstream PR. Every oscar64 run this round was under ulimit -v 2000000 with a timeout.)

   git log: 30adeed "tools: cap Oscar64's memory in the harness and make repros; r26". This round: bad_alloc (rc 134) only where expected, no exit 137.

4. **The regression test cannot fail before the fix** (Kept by design and stated plainly: the commit message, the test header and the PR Test section all say a regression shows as compile time and memory, not as a failed assert, and give the measured cost on an unfixed compiler.)

   Unfixed 4da3147: all ten configurations pass at 531-532 MiB, native 10.0-66.2 s; fixed: 38-41 MiB, 0.5-3.2 s (unfixed-main-full.txt, unfixed-main-final.txt, fixed-final-*.txt in f15-scratch).

5. **The PR describes the trigger more narrowly than it really is** (Fixed earlier by the lead and kept: the second paragraph and the commit message describe the general shape first (one arm holding a long chain before the arms join; no loop or function pointer needed), then what #440 changed.)

   Re-checked: v1.32.273 hits bad_alloc on the example at -n -O0 and -n default (1043 MiB, 6.5 s), with no dependence on #440 (chain-v132273.txt).

6. **The explode.c validation figure needs another unmerged fix and misquotes the before-#440 number** (Fixed in the PR: the explode.c bullet gives 2.7 s / 0.36 GB for v1.32.273 and says main also needs the function-pointer-member fix (#NNN = fork PR #4). Not re-measured this round.)

   Reviewer measured 3.99 s / 369 MB with fnptr-member plus this fix, and 2.65 s / 362 MB on v1.32.273.

7. **The PR example is cut short, and one timing differs from this host** (Fixed: the example is chain2.c in full (verified byte-for-byte against the file run). Timings reworded from this round's runs: unfixed "after 3 to 6 seconds"; fixed "within a few seconds" instead of "about a second"; the Validation bullet says 0.8 to 7.5 s and at most 164 MiB instead of "under 3 s and 170 MB".)

   chain-unfixed-all10.txt: rc 134 in 10/10 at 3.39-5.23 s, 1044-1046 MiB. chain-fixed.txt: native 2.01-7.48 s (-O3 164 MiB), bytecode 0.77-3.52 s.

8. **makemon.c still hangs with the fixed pin (T1.6), for a different reason** (Not this PR and not claimed by it; handled separately as fork PR #18 (fix/makemon-hang) per the lead's resolutions.)

   Reviewer's gdb samples sit in InterCodeProcedure::LoadStoreForwarding's do/while loop, a fixed-point loop rather than a path explosion.

9. **CollectBlocksToDominator does not preserve its exact output or its unrestricted input contract** (Fixed in wording by the lead and kept: commit message, code comment and PR Fix section say it returns each block once in first-reached order and that its only caller starts with an empty array and only asks whether any collected block modifies a temporary. No code change.)

   Commit message paragraph 2 on both branches; .prg byte-identical fixed vs unfixed in 10/10 configurations of the test on main and pin this round, and 849/850 in the earlier corpus.

10. **The visited comments equate discovery with completed verification on cycles** (Fixed earlier by the lead in the code comments and message: a revisited block has already passed (or been searched without finding the target), or is still on the recursion stack, which only happens on a cycle without a loop head, where the old code never terminated. Unchanged this round.)

   Commit message paragraph 2; oscar64/ identical to the reviewed c15930d / 2eaf2f3 (git diff --stat shows only the test file).

11. **The test's source does not establish coverage of all four functions** (Resolved by the pr440test agent's extended test (third function h) and its four one-check-removed builds; the PR Test section and the commit message now describe that experiment, including that each Push was kept. Spot-checked this round on the final file.)

   coverage-spot.txt: noCBD 530/531 MiB at -n and -bc -O0; noIDLPB 274 MiB at -n; noCLIX bad_alloc at 1,087,236 KB at -n; noCLIY 1,089,120 KB at -n; all four checks in place 40/24 MiB.

12. **"Cannot harm a machine running an older compiler" is unsupported** (Removed earlier; the PR and commit message state the measured cost, the machine (4-core laptop shared with other jobs) and the load averages instead of an assurance.)

   PR Test section paragraph 3; commit message last paragraph.

13. **Remaining-walk claim not checkable from the packet; "three walks" versus four functions** (Wording is "three recursive walks over the predecessor graph (four functions)"; the remaining walks are no longer an unverifiable aside but a pointer to the PR that fixes them (#NNN = fork PR #16).)

   PR intro and "Not addressed here"; walks2-investigation.json names all three as NativeCodeBasicBlock members.

14. **Several explanatory claims are stronger than the code supports** (Fixed earlier by the lead and kept: "can be affected", "once per path to it", "for each loop-invariant condition it tries to move". Timing and memory figures are presented as measurements with their conditions.)

   PR paragraphs 1-2 and Cause section; commit message paragraphs 1 and 3.

15. **No Y-walk coverage in the two-function test, and the lead's no-CollectBlocksToDominator variant was a no-op** (Resolved by the pr440test agent: function h added (needs `last = n;` after the loop to reach the Y walk on v1.32.273), and the CollectBlocksToDominator variant rebuilt correctly. The final test covers all four checks; on the pin the Y walk is not reached at -O0.)

   Lead's log: AssertionError ('oscar64/InterCode.cpp', 2) (the guard text occurs more than once), so that variant equalled the full fix. This round on the final file: noCBD 530 MiB, noCLIY 1063 MiB at -n; unfixed h alone 5.4-29.7 s in five native configurations.

16. **The commit message's test paragraph (both branches) overstates the fixed compiler's speed and leaves out how the coverage was measured** (Fixed by amending both commits (ce1a99b, f001eba). The paragraph now says each check was removed "but its Push kept, so that every revisit also costs memory", that the X variant exceeds a 2 GB address-space limit in four of five native configurations, and gives timings as ranges with the load: 8 to 66 s against 0.4 to 3.2 s native, 1 to 10 s against 0.15 to 1.3 s bytecode. The rest of each message is unchanged; the pin keeps its "d2ea285 here" wording.)

   git log -1 --format=%B on both branches; diff of the two messages shows only the bf42402/d2ea285 paragraph. Ranges cover this round's runs and the reviewer's (pin 8.2 s, fixed 0.39 s).

17. **The PR test paragraph has a unit slip (1.06 GiB), omits that the Push was kept, and gives timing ranges narrower than the re-runs** (Fixed in the new Test section: 1.04 GiB; "each with one visited check removed but its `Push` kept"; timings re-measured on main and given as ranges with load averages (unfixed 10 to 66 s native, 2 to 10 s bytecode; fixed 0.5 to 3.2 s and 0.2 to 1.3 s), with CPU time alongside.)

   1,087,236 KB = 1061 MiB = 1.04 GiB (coverage-spot.txt). unfixed-main-full.txt, unfixed-main-final.txt, fixed-final-2/3/4.txt.

18. **The PR draft does not end with the sentence the investigation quoted** (Settled by Jolyon's decision rather than the reviewer's suggested wording: the body ends "Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described.", preceded by "Found while porting NetHack 3.4.3 to the C64.")

   docs/OSCAR64-UPSTREAM.md lines 27-31.

19. **The test's header comment understates what g and h cost an unfixed compiler** (Fixed on both branches (the only file change this round): "f then costs about half a gigabyte of memory, g and h compile time, some seconds to tens of seconds each per native configuration. With the fix the file needs about 40 megabytes and about a second.")

   git diff c15930d ce1a99b and 2eaf2f3 f001eba: only autotest/loopconditionpathtest.c, 4 insertions, 3 deletions. Splits on unfixed 4da3147: g 8.0-12.4 s, h 5.4-29.7 s (unfixed-main-split.txt).

20. **Exported patches, the pin, and the stacked walks2 branch still carry the old commit** (Partly resolved, rest is the lead's. fix/exponential-walks-2 was already rebased onto ce1a99b by another agent (8b2fa93). The two exported patches in nethack64 are still stale and untracked (not mine to overwrite); fresh exports are in f15-scratch/patches-main and patches-pin. The accepted pin nethack64/v1.32.273-pin is still c2f5cab and was not touched.)

   head -1 of tools/oscar64-upstream/patches/main/15-pr440-runaway.patch: "From dc87ab3..."; patches/pin/0008-*.patch: "From c2f5cab...". git branch --contains ce1a99b lists fix/exponential-walks-2.

   Resolved 2026-11-13: `nethack64/v1.32.273-pin` is f001eba, and `tools/oscar64-upstream/patches/pin/0008-*.patch` is f001eba ("From f001eba...", same patch-id). `patches/main/15-pr440-runaway.patch` is ce1a99b (same patch-id as `fix/pr440-runaway`).

</details>

## Final Codex check (gpt-6-astra, 2026-11-13)

Read-only `codex exec` on a packet of the final PR text, the commit and the earlier findings (as for PRs 1-14). Each finding was then checked by the lead.

| Severity | Finding | Checked | Resolution |
|---|---|---|---|
| low | "Expected, and the result with this change: ... prints 432 and returns 0" reads as unconditional, while the Validation section reports four bytecode configurations printing 455/456 (a separate bytecode bug) | True: the Validation bullet says so, the sentence does not | Open: before submitting, change it to "With this change it compiles in all ten configurations; native code and `-bc -O0` print 432 and return 0; the other bytecode configurations show the separate issue described below" |
| low | The PR text's `#NNN` placeholders must become real references | True | Already on the "Before submitting" list: fill in once the parent PR has a number |

## Before submitting

- Fill in the two "#NNN" placeholders: the explode.c Validation bullet refers to the function-pointer-member fix (#4); "Not addressed here" refers to the three-more-walks fix (#16). If #16 is not open upstream when this goes out, name the three functions as a follow-up instead.
- Send with or after #4: the explode.c figure depends on it.
- If upstream main has moved from 4da3147: rebase and re-run the evidence (the new test and functionpointerparamtest.c in ten configurations, the full autotest, the example).
- Decide whether to open an upstream issue for the bytecode wrong-sum bug before or with this PR (the PR example shows it at four bytecode levels).
- Done 2026-11-12 (Jolyon's decision): the commit ends with one `Co-Authored-By: Claude <noreply@anthropic.com>` line and no session link (message only; the tree is the one validated), and the PR text ends with the same AI-assistance sentence as every other PR.

## Risks and limitations

1. The test detects a regression only as compile time and memory; no assert fails. On a slow or loaded autotest machine an unfixed compiler needs about half a gigabyte and up to a minute per native configuration for this one file. 2. Timings are heavily load-dependent on this machine (4-core/8-thread laptop shared with other agents): the fixed compiler took up to 3.2 s elapsed at load above 12 although its CPU time stayed at or under 1.1 s; the PR and commit message therefore give ranges with the load stated. 3. CollectBlocksToDominator's output is deliberately not identical (unique blocks in first-reached order); a future caller that passes a prepopulated array would get different behaviour. Its only caller today starts empty. 4. IndexOf-based visited sets are quadratic in the region size; fine for the block counts seen (597 blocks in explode()), not a general guarantee. 5. Three PR claims rest on the earlier investigation and were not re-run by me: "more than 5 minutes at -n -Os" once only the first walk is fixed, the explode.c figures (4.0 s / 0.37 GB, needs the fnptr-member fix), and the explode() block/path counts. 6. The PR example shows wrong output at four bytecode levels (separate bug); the PR says so, but a maintainer running the example with -bc will see it.

## Related bugs found, not fixed here

1. Three more exponential walks (NativeCodeBasicBlock::IsSameRegisterSource, CanJoinEntryLoadStoreZP, CheckSingleUseGlobalLoadStruct; the last also a stack overflow, main only): fixed by fork PR #16 (fix/exponential-walks-2, now 8b2fa93 on top of ce1a99b). 2. Bytecode wrong-sum bug: with -bc at -O1 or above, a loop body with 24 or more inlined `if (mask & bit) acc += k` conditionals computes a wrong sum, also on v1.32.273; visible on the PR example (455/456 instead of 432). Unreported upstream; reduced file /home/jolyon/nethack64/build/oscar64-wt/pr440-runaway-scratch/repro/variant3-direct.c. 3. "error 3027: Invalid branch target 'w3'" on upstream main only (found by the pr440test agent; /home/jolyon/nethack64/build/oscar64-wt/pr440-test-scratch/y/c3_w3.c). Unreported. 4. makemon.c still hangs in LoadStoreForwarding's fixed-point loop: separate, fork PR #18. 5. explode.c on main needs the fnptr-member fix (fork PR #4) before it compiles at all.

## Draft pull request

**Title:** Fix exponential walks over chains of conditionals

````markdown
Since bf42402 (#440, preserve parameters of address-taken functions) the compiler can run out of memory on code it used to compile: NetHack 3.4.3's `explode()` at `-Os` went from 2.7 s and 0.36 GB to more than 8 GB in 20 s, when the kernel's OOM killer stopped it. #440 is right; it exposes an older problem. Three recursive walks over the predecessor graph (four functions) have no visited set, so in a chain of independent conditionals they visit a block once per path to it, and the number of paths doubles with every conditional.

Code can be affected when one arm of a conditional holds a long chain of independent conditionals before the two arms join, at any optimisation level where the conditions are not constant (whether it is depends on which passes reach the shape). A loop body is the common case (the latch is the join), but no loop and no function pointer are needed: v1.32.273 runs out of memory on the example below at `-O0` and `-O1`. What #440 changed is that a function called directly with constant arguments and also through a function pointer no longer gets the constants folded into its body at `-O2`, `-Os` and `-O3`; in `explode()` that folding used to remove the chain.

### Example

```c
#include <stdio.h>

int acc;

void bump(int v)
{
	acc += v;
}

/* address taken, so after bf42402 its parameters stay non-constant */
void f(int x, unsigned long y, int n)
{
	int i;

	for (i = 0; i < n; i++)
	{
		if (x == 0)
			bump(100);
		else
		{
			if (y & 0x1ul) bump(1);
			if (y & 0x2ul) bump(2);
			if (y & 0x4ul) bump(3);
			if (y & 0x8ul) bump(4);
			if (y & 0x10ul) bump(5);
			if (y & 0x20ul) bump(6);
			if (y & 0x40ul) bump(7);
			if (y & 0x80ul) bump(8);
			if (y & 0x100ul) bump(9);
			if (y & 0x200ul) bump(10);
			if (y & 0x400ul) bump(11);
			if (y & 0x800ul) bump(12);
			if (y & 0x1000ul) bump(13);
			if (y & 0x2000ul) bump(14);
			if (y & 0x4000ul) bump(15);
			if (y & 0x8000ul) bump(16);
			if (y & 0x10000ul) bump(17);
			if (y & 0x20000ul) bump(18);
			if (y & 0x40000ul) bump(19);
			if (y & 0x80000ul) bump(20);
			if (y & 0x100000ul) bump(21);
			if (y & 0x200000ul) bump(22);
			if (y & 0x400000ul) bump(23);
			if (y & 0x800000ul) bump(24);
			if (y & 0x1000000ul) bump(25);
			if (y & 0x2000000ul) bump(26);
			if (y & 0x4000000ul) bump(27);
			if (y & 0x8000000ul) bump(28);
		}
	}
}

void (*fp)(int, unsigned long, int) = f;

int main(void)
{
	f(0, 0xfffffffful, 2);
	fp(1, 0x0f0f0f0ful, 1);
	printf("%d\n", acc);
	return acc != 200 + (1+2+3+4) + (9+10+11+12) + (17+18+19+20) + (25+26+27+28);
}
```

```
oscar64 -e -n -Os chain.c
```

Observed on 4da3147: the compiler's memory grows until it is killed. Under a 2 GB address-space limit (`ulimit -v 2000000`) it ends in `std::bad_alloc` after 3 to 6 seconds, at about 1 GB, in all ten autotest configurations (`-n` and `-bc`, each at default, `-O2`, `-O0`, `-Os` and `-O3`). v1.32.273 does the same at `-n -O0` and at `-n` (default); at `-n -Os` it compiles the file within 3 s, but the program prints 400 and returns 1: it folds `x = 0` into `f`, the wrong code #440 fixes.

Expected, and the result with this change: it compiles within a few seconds, and the program prints 432 and returns 0.

### Cause

`InterCodeBasicBlock::CollectBlocksToDominator` (InterCode.cpp) collects the blocks between a block and its dominator by recursing over `mEntryBlocks` and pushing every block it reaches, without checking whether it is already in the array, so it stores a block once per path to it. Between the latch and the head of the loop above there are 28 consecutive diamonds, so 2^28 paths. In `explode()` the region has 140 blocks and 149,130,697 paths; the array reaches 134 million entries before `new` fails. Its neighbours `IsDirectDominatorBlock` (memoised with `mPatched`), `CollectDominatorPath` and `CollectLoopBody` (both check `IndexOf` first) do not have the problem.

Once that is fixed, two more walks of the same shape show up as time instead of memory (the example then takes more than 5 minutes at `-n -Os`): `InterCodeBasicBlock::IsDirectLoopPathBlock`, which `MoveConditionOutOfLoop` calls twice per body block for each loop-invariant condition it tries to move and which explores every path when the answer is no, and `NativeCodeBasicBlock::CheckLoopIndexXRegisters` / `CheckLoopIndexYRegisters` in `ReduceIndexXYZeroShuffle`, which explore every path when the answer is yes.

### Fix

Each walk gets a visited set. `CollectBlocksToDominator` returns when the block is already in `body`: it has been collected with everything behind it, so the walk now returns each block once, in the order first reached, instead of once per path; its only caller starts it with an empty array and only asks whether any collected block modifies a temporary, which the duplicates did not change. `IsDirectLoopPathBlock` and `CheckLoopIndexX/YRegisters` keep their signatures and get an overload carrying an `ExpandingArray` of visited blocks: a revisited block is one whose predecessors were already searched without finding the target (so `false`), or one that already passed the check (so `true`, since any failure ends the check at once). They return what they returned before wherever the old code terminated (a block seen again while still on the recursion stack means a cycle without a loop head, on which the old code never terminated).

### Test

`autotest/loopconditionpathtest.c` takes the address of three functions whose loop bodies contain a chain of 24, 18 and 18 independent conditionals, and checks each with a direct call and with calls through a function pointer under two masks. It is registered in `autotest.bat` and runs in the usual ten configurations. `f` (a short path beside a chain of calls to a `__noinline` function) reaches `CollectBlocksToDominator` and `IsDirectLoopPathBlock`; `g` (an `int` loop count whose high byte stays in X across the chain) reaches `CheckLoopIndexXRegisters`; `h` (a byte loop count, with a condition of the chain kept in Y) reaches `CheckLoopIndexYRegisters`, and `CheckLoopIndexXRegisters` again at `-O0`.

That each walk is reached was checked by building the fix four more times, each with one visited check removed but its `Push` kept, so that every revisit also costs memory. Without the `CollectBlocksToDominator` check the file needs 531 MiB in all ten configurations; without the `IsDirectLoopPathBlock` check 275 MiB in eight (not at `-O0`); without either register check 1.04 GiB in the five native configurations, and the X variant ends in `std::bad_alloc` under a 2 GB address-space limit in four of them. With all four checks in place the file needs 40 MiB native and 26 MiB bytecode.

The chains are sized so that a compiler without the fix still gets through the file. Measured with 4da3147 on a 4-core laptop shared with other jobs, at load averages between 3 and 20: 10 to 66 seconds (10 to 33 s of CPU time) and 531 MiB per native configuration, 2 to 10 seconds and 532 MiB per bytecode configuration. All asserts pass, and the `.prg` files are byte-identical to the fixed compiler's in all ten configurations. With the fix, on the same machine at load averages between 5 and 17: 0.5 to 3.2 seconds (0.5 to 1.1 s of CPU time) and 40 MiB native, 0.2 to 1.3 seconds and 26 MiB bytecode. Without the fix only the `CollectBlocksToDominator` walk costs memory; the other three cost time (`g` alone: 8 to 12 s at 31 MiB where its walk is reached; `h` alone: 5 to 30 s at 29 MiB). A regression therefore shows as compile time and memory, not as a failed assert.

### Validation

- The example compiles in all ten configurations with this change, in 0.8 to 7.5 s and at most 164 MiB (`-n -O3` is the slowest). The five native configurations and `-bc -O0` print 432 and return 0; the other four bytecode configurations print 455 or 456, which is the separate bytecode problem described below.
- `functionpointerparamtest.c` still passes in all ten configurations, so #440 is kept.
- Full autotest on top of 4da3147: 1551 emulations, none failing, against 1541 and none on 4da3147; the ten new ones are this test.
- 184 programs (autotest and samples) compiled with both builds in five configurations: 849 of 850 `.prg` files byte-identical; the one difference (`testint16mul.c` at `-bc -O2`) also differs between two builds of the unpatched source.
- NetHack's `explode.c`: 4.0 s and 0.37 GB with this fix (v1.32.273, which folds the constants: 2.7 s and 0.36 GB). On main this also needs the fix for function pointer members of global structs (#NNN): main currently stops on `explode.c` with "Not a simple type".

### Not addressed here

- #NNN fixes three more walks of the same kind, which cost time rather than memory and are older than #440: `NativeCodeBasicBlock::IsSameRegisterSource`, `CanJoinEntryLoadStoreZP` and `CheckSingleUseGlobalLoadStruct`. It is stacked on this change.
- A separate, older bytecode problem showed up while reducing this: with `-bc` at `-O1` or above, a loop body with 24 or more inlined `if (mask & bit) acc += k` conditionals computes a wrong sum (also on v1.32.273, with a direct call); native code and `-bc -O0` are right. The example above shows it once it compiles. A reduced file is available for a separate issue.

Found while porting NetHack 3.4.3 to the C64. Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described.
````
