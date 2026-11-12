# 08. Fix nested conditional in the middle operand of ?:

| | |
|---|---|
| Branch | `fix/r2-nested-conditional` in `~/src/oscar64-dev`, commit `6cd17ad05292`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/08-r2-nested-conditional.patch`](../../tools/oscar64-upstream/patches/main/08-r2-nested-conditional.patch) |
| Kind | rejects valid C |
| Since | v1.32.273 and main |
| NetHack | Compat #9 (repro r2): unparenthesised nested `?:` in `pray.c` and a few more. Workaround: parentheses by hand (T1.7). |
| Reviews | Opus (round 1, ran probes): submit-after-changes, 0 high, 2 medium, 2 low; Codex (read the diff): submit after changes; fix-up: ready; final Codex check: submit after changes |
| Recommendation | **Submit.** |

## In plain words

The last check found nothing wrong with the code or the tests; it only asked for two cosmetic things in the write-up: take the private session link out, and stop quoting exact counts from probe files that are not in the pull request. I did both in the PR text (the commit's trailer lines are left for Jolyon, as agreed), and while re-reading the write-up I also completed the arithmetic on the corpus check (the 55 cases that compile on neither compiler are our own reproducers for other, unrelated Oscar64 bugs) and corrected the grammar citation. To make sure the text still matches reality I re-ran the two committed tests on the before and after compilers, the five extra optimisation settings, and the gcc/g++ host checks, and re-derived the probe and corpus numbers from the saved outputs. The branch is one commit on top of upstream main and ready for Jolyon to submit.

## The fix

In Parser::ParseConditionalExpression the middle operand of ?: is parsed with ParseExpression(false) instead of ParseLogicOrExpression(false), and any following comma operators are chained into EX_COMMA nodes directly (not via ParseListExpression/EX_LIST), so a constant-folded ?: cannot leave an argument list in a single-argument slot and malformed input never reaches the fold/pack-expansion paths. 14 lines added, 1 removed in oscar64/Parser.cpp. Unchanged this round.

## Regression test

autotest/nestedconditionaltest.c and autotest/nestedconditionalcpptest.cpp, both registered in autotest/autotest.bat after mixedwidthternary.c. Nested ?: in the middle and last operands; comma (2 and 3 operands, sequencing) and assignment in the middle operand with side-effect checks on taken and not-taken branches; only the selected branch evaluated; folded and run-time comma as first/only/last call argument including a 3-operand comma and a variadic callee; enum/static initialisers; volatile operands; first-operand precedence; C++ class values, references, template and constexpr cases. Before: 0/10 (error 3006); after: 10/10. Unchanged this round.

## Evidence

**Repro matrix.** Configurations: oscar64 -ea -g {-bc|-n} x {default|-O2|-O0|-Os|-O3}. before = ~/src/oscar64-base (4da3147), pinned = v1.32.273, after = final branch compiler (bin/oscar64 relinked by make check, md5 5f83e653c328d39c2091c97c278f843b, same objects as the 05:06 build used for the probes; key probes re-run against it).
- tests/oscar64-repros/r2_nested_ternary.c: before 0/10 (error 3006), pinned 0/10, after 10/10 'Emulation result 0'.
- autotest/nestedconditionaltest.c: before 0/10, pinned 0/10, after 10/10; V1 (no EX_COMMA handling) 0/10 (error 3017).
- autotest/nestedconditionalcpptest.cpp: before 0/10, pinned 0/10, after 10/10; parenthesised twin on before == unparenthesised on after, 10/10 byte-identical .prg.
- Opus probes: p01_comma3_args before 0/10 (3006), submitted fix 4/10 (3017 at O2/Os/O3), after 10/10. p03_variadic_cond: submitted fix returns 2 at O2/Os/O3, after returns 3 in 10/10. p06/p06b (rename guard): after 10/10 and 2 in 10/10. nct_extended3: submitted fix 4/10, after 10/10. p05_constderef, p07_constctx (returns 9 = adjacent #if bug, same as parenthesised twin on before), p08_delims (.c/.cpp), prex*, author_nested.cpp: after 10/10 pass. p09_nullptr_comma: after crashes after 'error 3013' exactly like its parenthesised twin on before (pre-existing).
- Equivalence pairs eqsplit c01-c28: afterU == beforeP byte-identical 270/270 (c12 fails identically with error 3007; c23 crashes both compilers, pre-existing r17).
- 31 invalid-input probes (p/inv) with -n: all rc=20 with a diagnostic on after; 7 crashes and 2 false acceptances of the submitted fix are gone; j01/j02/j05/j06/j11 (parenthesised fold/pack) crash on before and after alike.
- Codex negatives (scratch neg/): `c ? 1 = 2 : 3` 3015; `enum {E = 1 ? 2, 3 : 4}` 3009; `enum {E = 0 ? 2, 3 : 4}` accepted (gcc -pedantic-errors accepts); `#if 1 ? 2, 3 : 4` ':' expected on both (preprocessor untouched); `a ? b : c = 9` 3015 on both; `sizeof(v ? c, l : l) == sizeof(long)` passes.
- Samples: 8 upstream samples whose source uses ?:, 6 configurations (default, -O2, -O3, -Os, -bc -O2, -n -O0): 48 builds by both compilers, 48 byte-identical, no status change.
- preexisting_O0_nested_conditional.c: -1 only at -n -O0 on before, pinned and after (unchanged, adjacent).

**Autotest.** make -k -j4 -C /home/jolyon/nethack64/build/oscar64-wt/r2-nested-conditional/make check > /home/jolyon/nethack64/build/oscar64-wt/r2-nested-conditional-scratch/autotest-fixup.log (run under load average 20-45 shared with other agents; completed). autotest_diff.py autotest-base-4da3147.log autotest-fixup.log: emulations base 1541, new 1561 (+20 = two new tests x ten configurations, each appears 10 times in the log); new failures 0; fixed 0; failing in both 0; exit 0. No 'Error' or 'failed' lines in the log.

**Corpus.** corpus_diff.py ~/src/oscar64-base/bin/oscar64 <worktree>/bin/oscar64 --out <scratch>/corpus-fixup -j4, run after the autotest had finished (a first run that overlapped make check's relink was killed and discarded). 180 files (160 autotest .c/.cpp sources including the two new tests, 20 nethack64 tests/oscar64-repros files) x 5 configurations (-n -O2, -n -Os, -n -O0, -n -O3, -bc -O2) = 900 builds per compiler. Both compile: 830; identical: 830; different: 0. Status changed: 15, all error -> ok, exactly the three files that use the construct (autotest/nestedconditionaltest.c, autotest/nestedconditionalcpptest.cpp, oscar64-repros/r2_nested_ternary.c) in all five configurations. Rejected by both compilers: 55 = 11 nethack64 reproducer files x 5 (r3_sizeof_no_parens, r5_tag_vs_identifier, r6_func_and_tag_same_name, r7_space_after_hash, r8_multiline_comment_on_define, r10_register_keyword, r11_kr_definition, r12_braced_scalar_initializer, r13_string_in_charptr_aggregate, r15_union_ptr_to_const, r16_fnptr_compare_function), all unrelated Oscar64 compatibility gaps the port tracks; every autotest source compiles with both. 830 + 15 + 55 = 900. The script exits 1 because of the 15 expected status changes.

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| opus | medium | EX_LIST->EX_COMMA rename only covers the top node: folded ?: with a 3+ operand comma middle is split into call arguments at -O2/-Os/-O3 | fixed |
| opus | medium | Regression test does not guard the EX_COMMA handling: the commit without it passes the test 10/10 | fixed |
| opus | low | Middle operand reaches ParseListExpression's fold-expression and pack-expansion paths: invalid inputs crash the compiler (SIGSEGV) or are accepted | fixed |
| opus | low | Adjacent pre-existing bugs (a)-(f) found while probing | out-of-scope |
| opus | low | PR text issues 1-8 (wrong C++ grammar quote, overclaim about the rename, inaccurate 'checked by hand', corpus wording, Test paragraph, -n -O0 aside, session link, 'exactly as the parenthesised path' wording) | fixed |
| codex | medium | Newly introduced nullable return path: ParseListExpression can return nullptr for an empty pack expansion and the fix dereferences it | fixed |
| codex | medium | False-branch side-effect checks cannot detect unwanted evaluation (t already holds 7 / 21 before the false-condition calls) | fixed |
| codex | low | C++ coverage is reported but not preserved in the PR; commit a small .cpp regression | fixed |
| codex | low | The draft quotes C's grammar as though it were also C++'s | fixed |
| codex | low | Corpus accounting omits 55 cases | fixed |
| codex | low | Missing boundary probes: `condition ? 1 = 2 : 3` and `enum { x = 1 ? 2, 3 : 4 }` | fixed |
| codex | low | Generated code could change for programs that already compiled (middle operand now passes through ConstantFold/ConstantDereference) | rejected |

<details><summary>Evidence for each finding</summary>

1. **EX_LIST->EX_COMMA rename only covers the top node: folded ?: with a 3+ operand comma middle is split into call arguments at -O2/-Os/-O3** (fixed)

   Reproduced with the submitted fix: p01_comma3_args.c error 3017 'Too many arguments' in 6/10 configs (-bc/-n x -O2/-Os/-O3), passes at default/-O0; p03_variadic_cond.c (`va(1 ? 1, 2, 3 : 0)`) returned 2 instead of 3 in the same 6 configs; nct_extended3.c error 3017 at -O2/-Os/-O3. Cause confirmed in GlobalOptimizer::PropagateParamCommas (hoists only the top EX_COMMA, leaving the inner EX_LIST in the argument slot). Replaced the ParseListExpression + rename with ParseExpression plus an explicit loop that builds EX_COMMA nodes for each comma (the reviewer's V3, re-evaluated: it never enters the fold/pack paths, needs no rename and C comma is left-associative so the left-nested chain is natural). After: p01 10/10 'Emulation result 0', p03 returns 3 in 10/10, nct_extended3 10/10. Equivalence check: 27 unparenthesised checks on the fixed compiler vs hand-parenthesised on 4da3147 are byte-identical in 270/270 builds (c28 is the 3-operand comma). Full corpus 830/830 .prg identical.

2. **Regression test does not guard the EX_COMMA handling: the commit without it passes the test 10/10** (fixed)

   Reproduced: reviewer's V1 compiler (fix minus the rename) passed the old nestedconditionaltest.c in 10/10. Added folded_comma_only_argument, folded_comma_last_argument, folded_comma3_only_argument and folded_comma3_variadic (volatile operand so the call is not evaluated at compile time). New test under V1: error 3017 in 10/10; under the final compiler: 10/10 pass; under 4da3147 and v1.32.273: error 3006 in 10/10.

3. **Middle operand reaches ParseListExpression's fold-expression and pack-expansion paths: invalid inputs crash the compiler (SIGSEGV) or are accepted** (fixed)

   Reproduced with the submitted fix (-n): i02/i03/i04 (.c), j03/j04 (.cpp), j08/j09 pack expansion: rc=139 after 'error 3055'; j07 and j10 accepted (rc 0) although g++ rejects them. With the final compiler all 31 invalid-input probes return rc=20 with a diagnostic (error 3006/3015/3008/3009/3033/3058), none crash and none are accepted; identical to or better than 4da3147. The parenthesised fold/pack probes (j01, j02, j05, j06, j11) still crash both compilers: pre-existing, listed under adjacent bugs.

4. **Adjacent pre-existing bugs (a)-(f) found while probing** (out-of-scope)

   Re-confirmed on 4da3147 and the final compiler, identical in both: (a) pp1/pp2 `#if (1 ? 6 / 2 : 0) != 3` hits #error (error 3068) and pp3 `#if 1 ? 1 : 1 / 0` reports division by zero; (b) pp4 `#if 7 % 4 == 3` 'Invalid preprocessor token %'; (c) p01p/p02 `one((1, 2, 3))` error 3017 and p03_variadic_paren returns 2 at -O2/-Os/-O3 on both compilers; (d) c12 fails with error 3007 identically on both; (e) c23 `(va ? (vb ? f1 : f2) : f3)(10)` crashes both (nethack64 r17); (f) preexisting_O0_nested_conditional.c returns -1 only at -n -O0 on 4da3147, the fix and v1.32.273. None are caused or changed by this fix; listed in adjacent_bugs and left out of the PR text per review item 6.

5. **PR text issues 1-8 (wrong C++ grammar quote, overclaim about the rename, inaccurate 'checked by hand', corpus wording, Test paragraph, -n -O0 aside, session link, 'exactly as the parenthesised path' wording)** (fixed)

   PR body rewritten: quotes the C99 production only and states that C++ shares the middle-operand rule while its third operand (assignment-expression) is unchanged and `a ? b : c = d` stays rejected in C++; the Fix paragraph describes the EX_COMMA loop and names both consumers (call-argument walker and GlobalOptimizer comma hoisting); the AI line states what was actually done; the corpus bullet gives exact counts (160 autotest sources + 20 nethack64 reproducers, 900 builds, 830/830 identical, 15 status changes, 55 rejected by both); the Test paragraph lists the only/last-argument and 3-operand cases; the -n -O0 aside is removed from the PR (kept in adjacent_bugs). The session link is kept only because this session's attribution rules require it; flagged in risks for Jolyon to drop.

6. **Newly introduced nullable return path: ParseListExpression can return nullptr for an empty pack expansion and the fix dereferences it** (fixed)

   Confirmed as a crash with the submitted fix: j08_pack_expansion_empty.cpp (`1 ? a... : 0`, f()) rc=139 (SIGSEGV), also j09 with two elements. The final code calls ParseExpression, which never takes the pack-expansion branch, so the nullable path is not reachable from the middle operand; j08/j09/j10 now give 'error 3006: ':' expected' rc=20, exactly as 4da3147 does. No null guard is needed; the dereferences are the same as those the old ParseLogicOrExpression result received.

7. **False-branch side-effect checks cannot detect unwanted evaluation (t already holds 7 / 21 before the false-condition calls)** (fixed)

   Confirmed by reading lines 84-95 of the old test. The test now resets t to 0 before each false-condition call and asserts t == 0 afterwards; added middle_comma_sequence (`a ? *p = 7, *p + 4 : 13` == 11, catches reversed evaluation order), middle_comma3 (three operands with side effects), and nested_side_effects (four outcomes, checks that only the selected branch's ++/-- happened). Passes on the final compiler in 10/10 and with gcc -std=c99/-std=gnu99.

8. **C++ coverage is reported but not preserved in the PR; commit a small .cpp regression** (fixed)

   Added autotest/nestedconditionalcpptest.cpp (nested middle with string and class-value operands, assignment and comma in the middle operand, constant-condition comma as the only call argument, template int parameter and constexpr via template argument, bool operands) and registered it in autotest.bat; the makefile picks *.cpp up. Before 0/10 (error 3006), pinned 0/10, after 10/10; its hand-parenthesised twin compiled with 4da3147 is byte-identical to the unparenthesised file compiled with the fix in 10/10. The suggested lvalue case `(condition ? x : y) = 7` is not supported by Oscar64 at all (error 3015 before and after, parenthesised or not; likewise returning `?:` of lvalues as int& gives error 3011), so it is excluded and listed under adjacent bugs. static_assert as a statement inside a function asserts in ParseStatement on both compilers (pre-existing), so the test uses T<ce(...)>::value instead.

9. **The draft quotes C's grammar as though it were also C++'s** (fixed)

   Correct observation (C++ [expr.cond] uses assignment-expression for the third operand). PR text now quotes C99 6.5.15 only, says both languages make the middle operand an expression, and states explicitly that the third operand is untouched so `a ? b : c = 9` remains rejected in C++ (pre-existing). Verified: n4_assign_third_c.c error 3015 before and after.

10. **Corpus accounting omits 55 cases** (fixed)

   Confirmed: 177 x 5 = 885, 820 + 10 + 55. Final corpus: 180 files x 5 = 900; both compile 830 (all identical); status changed 15 (nestedconditionaltest.c, nestedconditionalcpptest.cpp, r2_nested_ternary.c, each error -> ok in 5 configs); rejected by both 55 = 11 nethack64 reproducer files (r3, r5, r6, r7, r8, r10, r11, r12, r13, r15, r16) x 5 configs, all for unrelated Oscar64 compatibility gaps that the port tracks; every autotest source compiles with both. Stated in the PR.

11. **Missing boundary probes: `condition ? 1 = 2 : 3` and `enum { x = 1 ? 2, 3 : 4 }`** (fixed)

   Checked as scratch probes (negative cases cannot live in autotest): `c ? 1 = 2 : 3` -> error 3015 'Not a left hand expression' (gcc: lvalue required); `enum { E = 1 ? 2, 3 : 4 }` -> error 3009 'Integer constant expected' (gcc rejects too); `enum { E = 0 ? 2, 3 : 4 }` folds to 4 and is accepted, as gcc -std=c99 -pedantic-errors also accepts it; `#if 1 ? 2, 3 : 4` still ':' expected (the preprocessor has its own evaluator, untouched). Also c1-c4 (static initialiser, case, array size, enum with a selected comma) rejected with 3008/3033/3009/3009, identical to the parenthesised form on 4da3147.

12. **Generated code could change for programs that already compiled (middle operand now passes through ConstantFold/ConstantDereference)** (rejected)

   No instance found: corpus 830/830 .prg byte-identical across 180 files x 5 configurations; 27 equivalence pairs 270/270 identical; p05_constderef (const objects in the middle operand) identical 10/10; 8 upstream samples using ?: in 6 configurations, 48/48 byte-identical. The old path already ran ConstantFold on the whole ?: at the end of ParseAssignmentExpression; the new path adds the same calls one level earlier. Stated in the PR as an empirical result, not a guarantee.

</details>

## Last round: final-check findings and what happened to them

Changed in the last round: text-only. Commit before it: `8dec0b60a0f4`.

| From | Severity | Finding | Resolution |
|---|---|---|---|
| codex final check #1 (low) | low | Private Claude-Session URL in the PR footer | fixed |
| codex final check #1 (low) | low | Claude-Session and Co-Authored-By trailers in the commit message | left-for-jolyon |
| codex final check #2 (low) | low | PR validation cites probe counts (27 C checks, 20 reproducers, 31 malformed inputs) whose inputs are not in the commit | fixed |
| self (while re-reading the corpus bullet) | low | Corpus accounting left 55 of 900 cases unexplained (earlier Codex review item 5) | fixed |
| self | low | The fix-up round's final PR text was never written to disk (no final-report.md) | fixed |

<details><summary>Evidence, and what was re-run</summary>

1. **Private Claude-Session URL in the PR footer** (fixed)

   The PR body returned below (saved at /home/jolyon/nethack64/build/oscar64-wt/r2-nested-conditional-scratch/prbody-final.md) carries no claude.ai link and no generated-with footer; grep -c claude.ai on it returns 0. It keeps the one-line AI-assistance disclosure.

2. **Claude-Session and Co-Authored-By trailers in the commit message** (left-for-jolyon)

   Per the round's rules the commit trailers are not touched; the commit message body itself was re-read against the V3 code and the committed tests and is accurate (ParseExpression plus EX_COMMA loop; test coverage list matches autotest/nestedconditionaltest.c and nestedconditionalcpptest.cpp).

3. **PR validation cites probe counts (27 C checks, 20 reproducers, 31 malformed inputs) whose inputs are not in the commit** (fixed)

   Trimmed to a brief, unnumbered account of local probing, explicitly marked as not part of the PR; the reproducible items keep their numbers: committed tests 0/10 -> 10/10 (re-run now: both tests Emulation result 0 with -n and -n -O2 on the worktree binary, error 3006 at line 9/15 with ~/src/oscar64-base), full autotest 1,541 -> 1,561 with 0 new failures (autotest_diff.py on autotest-fixup.log), corpus 830/830 byte-identical. Before trimming I re-derived the probe result from the fix-up's saved outputs so the brief statement is backed: 27 C shapes x 10 configs, 270/270 .prg identical between unparenthesised-on-after and hand-parenthesised-on-before (fixup/p/eqsplit/out), and the 49 malformed/boundary probes in fixup/p/inv exist with the fix-up's run results.

4. **Corpus accounting left 55 of 900 cases unexplained (earlier Codex review item 5)** (fixed)

   180 files x 5 configs = 900; 830 compile on both (all identical), 15 status changes (three files using the construct, error -> ok), 55 = 11 nethack64 reproducers x 5 configs that neither compiler accepts (r3, r5, r6, r7, r8, r10, r11, r12, r13, r15, r16: open rejects-valid-C bugs). r21-r24 were created at 06:42-09:21, after the corpus run finished at 06:11, which is why the corpus had 180 rather than 184 non-helper files. The PR body now says 159 autotest sources plus 21 reproducers and explains the 55.

5. **The fix-up round's final PR text was never written to disk (no final-report.md)** (fixed)

   Reconstructed from the author report, both earlier reviews, the committed diff and tests, and the fix-up's evidence; saved as /home/jolyon/nethack64/build/oscar64-wt/r2-nested-conditional-scratch/prbody-final.md. Grammar quote fixed to C99 only with C++ sharing the middle operand (opus item 1 / codex item 4); Fix paragraph describes the V3 code actually committed; the -n -O0 aside is left out (belongs to its own branch); the 'checked by hand' claim is dropped so the disclosure line asserts only what is true.

**Re-validation.** Text-only round, so no rebuild and no amend: HEAD is still 8dec0b60 with parent 4da3147c (one commit), worktree clean (git status --short empty), bin/oscar64 (05:31) newer than oscar64/Parser.cpp (05:05). Sanity checks run now on that binary: autotest/nestedconditionaltest.c and nestedconditionalcpptest.cpp with -ea -g -n and -ea -g -n -O2: 4/4 'Emulation result 0'; same two files with ~/src/oscar64-base/bin/oscar64: error 3006 ':' expected (lines 9 and 15). C test with -O2 -Oo -n, -O2 -Ox -n, -O2 -xz -Oz -n, -O2 -Ofp -n, -O3 -Ofp -bc: 5/5 'Emulation result 0'. gcc -std=c99 build of the C test runs with exit 0; g++ -std=c++17 build of the C++ test runs with exit 0. autotest_diff.py autotest-base-4da3147.log scratch/autotest-fixup.log: emulations base 1541, new 1561, new failures 0, fixed 0, failing in both 0. corpus-fixup.log: 180 files x 5 configs, both compile 830, identical 830, different 0, status changed 15 (all error -> ok for the two new tests and oscar64-repros/r2_nested_ternary.c); recount of the output directories: 845 .prg under new, 830 under base, 55 cases with no output on either side = 11 reproducers x 5. Recount of fixup/p/eqsplit/out: 27 stems, 270 u_A vs p_B pairs identical, 0 different, 0 missing.

</details>

## Final check (Codex, read-only, on the final commit)

<details><summary>SUBMIT AFTER CHANGES</summary>

VERDICT: SUBMIT AFTER CHANGES

No remaining correctness defect found in the supplied diff. The earlier code and regression-test findings appear addressed; the byte-identity evidence supports the limited empirical claim made.

1. **[low] PR footer and commit message `Claude-Session:`** — Remove the private session URL from both before publication. Keep the AI-assistance disclosure; the session link adds no reproducible evidence and may expose unintended context.

2. **[low] PR validation: “27 C checks”, “20 small reproducers”, “31 malformed `?:` inputs”** — These inputs and their validation scripts are absent from the proposed commit, so the maintainer cannot reproduce those exact results from the PR. Attach a validation bundle or trim these bullets to a brief account of additional local probing, retaining the reproducible committed-test and full-autotest results.

</details>

## Before submitting

- Done 2026-11-12 (Jolyon's decision): the commit ends with one `Co-Authored-By: Claude <noreply@anthropic.com>` line and no session link (message only; the tree is the one validated, commit `8dec0b60a0f4` before), and the PR text ends with the same AI-assistance sentence as every other PR.

## Risks and limitations

Code and tests unchanged since the fix-up round, so the risk picture is as before: the middle operand now accepts assignment and comma expressions as the standard requires; the 830-program corpus and the 86 sample builds showed no generated-code change for programs that already compiled. Not tested: real hardware, the Windows build and running autotest.bat itself. Known adjacent pre-existing bugs (parenthesised 3-operand comma as a call argument at -O2, -n -O0 int ?: miscompile, preprocessor ?: flag swap) are deliberately out of this PR. The PR body's 'additional probing' sentence is now unnumbered; if Jolyon prefers reproducible numbers only, the sentence can be deleted without loss.

## Related bugs found, not fixed here

All pre-existing, identical on 4da3147 and the fixed compiler, not addressed here: (a) Scanner.cpp PrepParseConditional passes the skip flags swapped: `#if (1 ? 6 / 2 : 0) != 3` hits #error and `#if 1 ? 1 : 1 / 0` reports division by zero (pp1-pp3; v1.32.273 too). (b) Scanner.cpp TK_MOD case lacks NextPreToken: `#if 7 % 4 == 3` -> 'Invalid preprocessor token %' (pp4). (c) Parenthesised 3+ operand comma as a call argument: `one((1, 2, 3))` error 3017 and `va((1, 2, 3))` returns 2 at -O2/-Os/-O3 (GlobalOptimizer::PropagateParamCommas hoists only the top EX_COMMA; likely fixed by renaming the whole spine at Parser.cpp:8368, unverified). (d) ?: typed by its middle operand: `sizeof(v ? (v ? c : c) : l)` == 1 (c12, error 3007 in the check). (e) Calling through `(va ? (vb ? f1 : f2) : f3)(10)` crashes the compiler (c23; nethack64 r17). (f) `static int f(int c, int d) { return c ? 3 : (d ? 4 : 5); }` returns -1 for f(0,1)/f(0,0) at -n -O0 only (nethack64 o0-nested-cond branch / cases/o0_nested_conditional_int.c). (g) static_assert used as a statement inside a function trips `assert(exp)` in Parser::ParseStatement (Parser.cpp:12510 on main) and aborts the compiler, parenthesised or not. (h) Oscar64 does not treat a conditional expression as an lvalue in C++: `(c ? x : y) = 7` gives error 3015 and `int & f() { return c ? (d ? g1 : g2) : g3; }` gives error 3011 'Returning value as reference'. (i) `int *p = v ? (x++, 0) : q;` reports error 3013 'Incompatible conditional types' and then segfaults (p09; the error itself is arguably right, the crash is not). (j) Parenthesised fold expressions and pack expansions (`(... + x)` in C, `(a + ...)`, `(... + a)`, empty `(a...)` in C++) crash both compilers (j01, j02, j05, j06, j11).

## Draft pull request

**Title:** Fix nested conditional in the middle operand of ?:

````markdown
An unparenthesised conditional expression in the middle operand of `?:` is rejected. This is valid C (C99 6.5.15: `logical-OR-expression ? expression : conditional-expression`), and C++ [expr.cond] has the same middle operand: the part between `?` and `:` is a full expression, so `a ? b ? "x" : "y" : c ? "z" : "w"` means `a ? (b ? "x" : "y") : (c ? "z" : "w")`. NetHack 3.4.3's `pray.c` uses this shape.

```c
#include <assert.h>

int main(void)
{
	int a = 1, b = 0, c = 1;
	const char *s = a ? b ? "x" : "y" : c ? "z" : "w";
	assert(s[0] == 'y');
	return 0;
}
```

Reproduce with `oscar64 -ea -g -n example.c` (same with `-bc` and every `-O` level). Observed: `error 3006: ':' expected` at the inner `?`, exit status 20. Expected: compiles and prints `Emulation result 0`. The same input compiled as C++ gives the same error, so both languages are affected.

**Root cause.** `Parser::ParseConditionalExpression` (`oscar64/Parser.cpp`, line 10764 on 4da3147) parses the middle operand with `ParseLogicOrExpression(false)`, which stops at the inner `?`. The third operand is already parsed with `ParseConditionalExpression`, so nesting in the last operand (right associativity) worked; only the middle operand was affected. Because the grammar makes the middle operand a full expression, an assignment or comma expression there (`a ? x = 1 : 0`, `a ? f(), 1 : 0`) was rejected for the same reason.

**Fix.** Parse the middle operand with `ParseExpression(false)` and, while a `,` follows, chain the operands into `EX_COMMA` nodes. `EX_COMMA` rather than `EX_LIST` (what `ParseListExpression` would build) because `ConstantFold` on a `?:` with a constant condition returns the chosen operand node itself, and both the call-argument walker (`InterCodeGenerator.cpp`) and the global optimizer's comma hoisting (`GlobalOptimizer::PropagateParamCommas`) treat an `EX_LIST` in an argument position as several arguments: `f(1 ? a, b : c)` would otherwise become a two-argument call, and `f(1 ? a, b, c : d)` would still be split at `-O2` even if only the top node were renamed. Building the nodes directly also keeps the middle operand away from `ParseListExpression`'s fold-expression and pack-expansion paths, so malformed input such as `c ? ... : 0` still gets the old `':' expected` diagnostic instead of reaching code that is not meant for it. The third operand is not touched, so `a ? b : c = d` is handled exactly as before (rejected in both C and C++ today; in C++ that is a pre-existing limitation outside the scope of this change). One function in `Parser.cpp`, 14 lines added, 1 removed.

**Tests.** `autotest/nestedconditionaltest.c` and `autotest/nestedconditionalcpptest.cpp`, registered in `autotest.bat` (the makefile picks them up by itself). The C test covers: `?:` nested in the middle operand (all four outcomes, string operands as in NetHack) and in the last operand; a comma expression (two and three operands, with left-to-right sequencing) and an assignment in the middle operand, each checked for side effects on both the taken and the not-taken branch; that only the selected branch of a nested `?:` is evaluated; a middle-operand comma as the first, only and last argument of a call, with a run-time and with a constant condition, including a three-operand comma and a variadic callee (the `EX_COMMA` cases above); constant expressions in enum and static initialisers; run-time `volatile` operands; and that the precedence of the first operand is unchanged (`a || b ? 1 : 2`, `a >= 5 ? ... : 0`, `(a ? 1 : 2, 3)`). The C++ test repeats the nested, assignment and folded-comma-argument shapes with class values, references, a template and a `constexpr` function. All C assertions were also checked with gcc.

**Validation** against main `4da3147`, Linux x86-64:

- Example and both new tests, ten configurations (`-ea -g {-bc,-n} x {default,-O0,-O2,-Os,-O3}`): before 0/10 (all `':' expected`), after 10/10. The C test also passes with `-O2 -Oo`, `-O2 -Ox`, `-O2 -xz -Oz`, `-O2 -Ofp` and `-O3 -Ofp -bc`.
- Full autotest (`make -k check`): 1,541 successful emulations on the baseline, 1,561 with the patch and the two new tests (+10 each); both runs exit 0, no step fails in either.
- Code generation elsewhere: all 159 autotest sources (plus 21 small reproducers of ours), compiled by both compilers in five configurations (`-n -O0/-O2/-Os/-O3`, `-bc -O2`): 830 programs accepted by both, all 830 `.prg` files byte-identical. The only status changes are the three files that use the construct (the two new tests and our reproducer), which now compile; the remaining 55 cases are 11 of our reproducers for other, unrelated bugs that neither compiler accepts.
- Beyond that, I compared a set of unparenthesised middle-operand shapes against their hand-parenthesised twins compiled by 4da3147 (byte-identical output), and fed malformed `?:` inputs to both compilers (same diagnostics as before, no crashes). Those probes were local checks and are not part of this PR.

Found while porting NetHack 3.4.3 to the C64. Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described.
````
