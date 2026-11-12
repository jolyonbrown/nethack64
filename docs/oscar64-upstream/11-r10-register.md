# 11. Fix register storage class not accepted

| | |
|---|---|
| Branch | `fix/r10-register` in `~/src/oscar64-dev`, commit `d091911f4c68`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/11-r10-register.patch`](../../tools/oscar64-upstream/patches/main/11-r10-register.patch) |
| Kind | rejects valid C |
| Since | v1.32.273 and main |
| NetHack | Compat #2 (repro r10): the `register` storage class, thousands of uses. Workaround: `-dregister=` on the command line. |
| Reviews | Opus (round 1, ran probes): submit-after-changes, 1 high, 3 medium, 4 low; Codex (read the diff): submit after changes; fix-up: ready; final Codex check: submit after changes |
| Recommendation | **Submit.** |

## In plain words

This last round was about the test file and the wording, not the compiler. The final reviewer caught that the test's `#define register` line (the trick old debug builds use to make the word disappear) came before most of the declarations it was supposed to protect, so the write-up's claim that it was 'after all other uses' was wrong; it now really is after main. He also pointed out that an empty macro could never show the bug the fix-up repaired (a macro body being treated as program code), so the test now ends with a deliberately unparsable macro body: I rebuilt the earlier, broken layout of the fix and confirmed the new test fails on it and passes on the real fix. The apparent contradiction about `#define register static` was two different probes being summarised in one sentence: that macro worked on the old compiler (10/10) and is now accepted but silently ignored (compiles, wrong result), exactly as `#define static` always was; the PR now says so plainly. Two wording fixes (the test's header comment, 'ten files' vs ten file/configuration pairs, and the commit's byte-identity claim) are applied. The whole Oscar64 test suite still passes (1541 to 1551 emulations, no new failures) and the branch is one commit on upstream main, ready for Jolyon to submit.

## The fix

Compiler change unchanged from the reviewed fix-up: TK_REGISTER added after TK_EXTERN (inside the TK_IF..TK_ASM range that #define accepts), 'register' mapped in the scanner, accepted and skipped in ParseBaseTypeDeclaration and in the declaration-start lists of ParseSimpleExpression, ParseStatement and IsTypeToken; ParsePragma dispatches TK_REGISTER first with the existing #pragma register body moved into that branch. This round changed only autotest/registerstoragetest.c and the commit message: the header comment no longer overstates the standard; the empty `#define register` and defined_away() now follow main (prototype before main) so a conforming preprocessor cannot strip register from the declarations under test; an unused `#undef register` / `#define register )` at the end checks that a replacement list stays out of the program text (proven to fail on an out-of-range-token build); the commit message narrows the -dregister= byte-identity claim to the test in ten configurations, states that `#define register static` is now a no-op, and describes the new test layout.

## Regression test

/home/jolyon/nethack64/build/oscar64-wt/r10-register/autotest/registerstoragetest.c (169 lines, registered at the top of autotest/autotest.bat, picked up by autotest/makefile). Fails on main 4da3147 and v1.32.273 in all ten configurations with error 3005; passes on the fix in all ten, as C++, with -strict, -pp and the three extra autotest.bat configurations. Its trailing `#define register )` additionally fails (error 3006) on a build whose TK_REGISTER lies outside the TK_IF..TK_ASM range, i.e. the first reviewed version of the fix.

## Evidence

*These are the fix-up round's results, for commit `7ef4f25451a0`. The last round changed the test; its re-validation of the final commit is under "Last round" below.*

**Repro matrix.** Configurations -ea -g {-bc,-n} x {default,-O2,-O0,-Os,-O3}; before = ~/src/oscar64-base/bin/oscar64 (4da3147), after = worktree bin/oscar64 (7ef4f25), pinned = ~/src/oscar64/bin/oscar64 (v1.32.273). tests/oscar64-repros/r10_register_keyword.c: before 0/10, after 10/10. review/example.c (PR example): before 0/10 (`example.c(3, 25) : error 3005`), after 10/10. autotest/registerstoragetest.c: before 0/10, after 10/10, pinned 0/10. review/pragma_register.c: before 10/10, reviewed fix 0/10, after 10/10, pinned 10/10. pp_define_register_body.c: before 10/10, reviewed fix 0/10, after 10/10. pp_define_register_inject.c: before 0/10, reviewed fix 10/10 (wrong), after 0/10. pp_define_register_static.c: before 10/10, after 0/10 (silent, same as `#define static` on main 0/10; stated limitation). fixup/reg_pragma_and_define.c (pragma + register local): before 0/10, after 10/10. Valid-C probes review/v/v01-v20 after: all pass except v10/v15/v20, which fail identically with register removed on all compilers. C++ probes review/cpp after: pass except c02 (pre-existing crash, fails without register) and c07 (`template<register int N>`, correctly rejected). Preprocessor directive probes (#ifdef/#ifndef/defined/macro parameter named register): before 2/2, after 0/2, same as `#ifdef inline` on main (0/2). Keyword vs -dregister= on the test (pragma line removed): 10/10 byte-identical.

**Autotest.** make -k -j4 -C /home/jolyon/nethack64/build/oscar64-wt/r10-register/make check > /home/jolyon/nethack64/build/oscar64-wt/r10-register-scratch/autotest-fixup.log; no make errors in the log. autotest_diff.py /home/jolyon/nethack64/build/oscar64-wt/autotest-base-4da3147.log autotest-fixup.log: emulations base 1541, new 1551 (+10 = the new test in ten configurations); new failures 0; fixed 0; failing in both 0.

**Corpus.** corpus_diff.py ~/src/oscar64-base/bin/oscar64 <worktree>/bin/oscar64 --out /home/jolyon/nethack64/build/oscar64-wt/r10-register-scratch/corpus-fixup -j4: 179 files x 5 configurations (n-O2, n-Os, n-O0, n-O3, bc-O2) = 895 pairs; both compile 830; identical 829; different 1; status changed 10; both fail 55 (895 - 830 - 10). The 10 status changes are autotest/registerstoragetest.c and oscar64-repros/r10_register_keyword.c, error -> ok in all five configurations (both use register; intended). The 1 difference is autotest/testint16mul.c bc-O2 and is not caused by the fix: the output depends on the include-directory path string. With -bc -O2 on one binary alone, -ii=<worktree>/include gives md5 6f5e7d9b and -ii=<base>/include gives b9c6a49f, for the before compiler and the after compiler alike (include trees identical by diff -r). Extra, PR-440 style: all 65 .prg files from the samples makefile built with both compilers using the same -ii are byte-identical (both builds exit 0, no errors).

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| opus | high | Keyword breaks Oscar64's own #pragma register(name, address) | fixed |
| opus | medium | #define register <body> skips the directive and compiles the body as program text | fixed |
| opus | medium | #ifdef/#ifndef/#undef/defined()/macro parameters named register stop working | deferred |
| opus | medium | Regression test covers declarations only | fixed |
| opus | low | Misuse is accepted silently in more places than the PR says | fixed |
| opus | low | Code using register as a name now fails; struct member named register crashes the compiler | out-of-scope |
| opus | low | PR and commit text contain inaccurate claims | fixed |
| opus | low | Side findings: pre-existing bugs on main and v1.32.273 | out-of-scope |
| codex | medium | Storage class after type specifier (int register a; int g(int register x)) unsupported | out-of-scope |
| codex | medium | 'Only a hint and may be ignored' misstates C; constraint violations (file scope, &r, register register) are not diagnosed | deferred |
| codex | low | 'No existing token value changes' claim is false (token inserted mid-enum) | fixed |
| codex | low | Validation supports only narrow conclusions (corpus configs, -dregister= equivalence) | fixed |
| codex | medium | Regression test misses prototypes, function pointers, volatile, pointer const, while-body local, committed C++ test | fixed |
| codex | low | PR text needs narrower, more accurate claims (C++17 extension, corpus configs, implicit int) | fixed |

<details><summary>Evidence for each finding</summary>

1. **Keyword breaks Oscar64's own #pragma register(name, address)** (fixed)

   Reproduced: review/pragma_register.c (#pragma register(__sp,0x23)/(__fp,0x25)) before 10/10, fix-as-reviewed 0/10 (error 3006 Invalid pragma directive), pinned v1.32.273 10/10. Cause confirmed in Parser::ParsePragma: it only dispatches TK_IDENT and matches the pragma by strcmp on mTokenIdent, which is stale for a keyword. Fix: ParsePragma now tests TK_REGISTER first and the existing pragma body is moved (unchanged, re-indented) into that branch; the Opus variant duplicated the 40-line body instead, so I did not adopt it as written. After fix-up: pragma_register.c 10/10; the four malformed-pragma error paths (unknown register name, missing name, bad start number, missing comma) print identical messages before and after; `#pragma register(__tmpy, 0x02)` added to the test is a byte-level no-op (10/10 configurations identical with and without the line).

2. **#define register <body> skips the directive and compiles the body as program text** (fixed)

   Reproduced: pp_define_register_static.c before 10/10 -> fix-as-reviewed 0/10 (Emulation result 1, silent); pp_define_register_inject.c (body `int g_injected = 5;`) rejected before, accepted after; pp_define_register_body.c (`#define register volatile`) before 10/10, after 0/10 'Function declaration differs main'. Cause: Scanner.cpp:757 accepts keyword macro names only in TK_IF..TK_ASM and TK_REGISTER sat after TK_MEMMAP. Fix: TK_REGISTER and "'register'" moved to directly after TK_EXTERN. After fix-up: inject rejected again (0/10, same error as main), body 10/10. Residual, stated in the PR: `#define register static` is defined but never expanded (0/10 on main, fix and pinned alike), exactly as `#define static` on main (pp_kw_macro_effective.c 0/10 on all three) - keyword macros never expand in Oscar64.

3. **#ifdef/#ifndef/#undef/defined()/macro parameters named register stop working** (deferred)

   Reproduced on the fix (0/2 each): pp_ifdef_register.c, pp_ifdef_register_undefined.c, pp_silent.c, pp_silent2.c, pp_guard_ifndef.c, pp_macro_param_named_register.c; all 2/2 on main and pinned. #undef register silently ignored but harmless (pp_undef_register.c 2/2 after). Same limitation for every keyword: pp_other_kw_ifdef.c (`#ifdef inline`) fails 0/2 on main and pinned too. Making directives accept keyword tokens by spelling is a separate scanner change (Scanner.cpp:887-917 and defined()), so it stays out of this PR and is listed as a known limitation. NetHack's only directive use is the empty `#define register` (port/src/mkmaze.c:901), which works (covered by the new test).

4. **Regression test covers declarations only** (fixed)

   autotest/registerstoragetest.c now also has `#pragma register(__tmpy, 0x02)` at the top, a prototype and definition differing only in register, a function-pointer parameter type with a register parameter, `register volatile int`, `register int * const`, a register local inside a while body, and an empty `#define register` placed after all other uses (so it cannot hide them on the before compiler) followed by a function using register. Before 0/10 (error 3005 at line 17), after 10/10; as .cpp 10/10, -strict 10/10, -pp 10/10; the three extra autotest.bat configurations (-O2 -xz -Oz -n, -O2 -Oo -n, -O2 -Ox -n) pass; gcc -std=c99 -pedantic and g++ -std=c++14 run it with exit 0.

5. **Misuse is accepted silently in more places than the PR says** (fixed)

   Reproduced on the fix (2/2 each, compile and run): i01 file scope, i02 &r, i03 register function, i04 typedef register, i05 static register, i07 extern register, i08 register register, i09 struct member, i10 cast, i11 sizeof, i16 array, i17 compound literal, c08 new register int. Main already accepts (static int)l, sizeof(static int) and struct members with static (s01-s03 2/2). Still rejected after: register static, bare register;, implicit-int register x;, int register = 0. PR text reworded to list these. Narrowing to the ParseDeclaration storage-class loop was rejected: `const static int x` is already rejected on main, so the narrow form would reject `const register`, and the accept-and-ignore form is the maintainer's own typename precedent.

6. **Code using register as a name now fails; struct member named register crashes the compiler** (out-of-scope)

   Reproduced: n01-n04 compile on main and pinned, fail on the fix; n03 and i22 (member named register) exit 139. The crash is pre-existing for any keyword-named member: s06-s09 (`int static;`, `int while;`, `int extern;`) exit 139 on main 4da3147 and on the fix, while v1.32.273 exits 20 cleanly, so it is a regression in main independent of this change (also i09 `struct s { register int a; }` segfaults main before the fix). Compatibility break stated in the PR; crash listed under adjacent bugs.

7. **PR and commit text contain inaccurate claims** (fixed)

   (1) token position claim: the token now sits next to TK_EXTERN and the PR no longer claims values are unchanged; (2) verified main prints `example.c(3, 25)`; (3) verified the testint16mul -bc -O2 output follows the include-directory string, not the build location: before compiler with -ii=<worktree>/include gives md5 6f5e7d9b, after compiler with -ii=<base>/include gives b9c6a49f, each binary flips with -ii alone, include trees identical by diff -r; (4) commit message no longer says 'no valid program is affected'; (5) PR now covers the pragma, preprocessor interactions, identifier break, C++ wording (deprecated in C++11, removed in C++17, word stays reserved) and a samples comparison (65/65 byte-identical). Attribution trailers kept as they were, per instructions; that remains Jolyon's call.

8. **Side findings: pre-existing bugs on main and v1.32.273** (out-of-scope)

   All reproduced identically on before, fix and pinned compilers: side/loop_b2.c returns -246 instead of 10 in 4/10 configurations (-O2/-O3, -n and -bc) with 'warning 2017: Invalid value range'; side/fnret_a.c and fnret_c.c (`pick(1)(4)`) segfault the compiler in 6/10 configurations on main and fix and 10/10 on v1.32.273; cpp/c02_noreg.cpp (`auto * p = "ab";`) segfaults 10/10 on all three. Not caused by this change; listed in adjacent_bugs.

9. **Storage class after type specifier (int register a; int g(int register x)) unsupported** (out-of-scope)

   Reproduced: ord_int_register.c, ord_long_register.c, ord_param_int_register.c fail on the fix (0/2). But `int static a;` and `int g(int static x)` fail identically on main and v1.32.273 (ord_int_static.c, ord_int_register_param_static_main.c 0/2 on all three), and `const static int` is rejected on main too: Oscar64 never accepted a storage class after a type specifier. `unsigned register int c` passes (2/2). register now behaves exactly like static here; stated in the PR as a limitation rather than fixed, since fixing it means changing storage-class parsing for all specifiers.

10. **'Only a hint and may be ignored' misstates C; constraint violations (file scope, &r, register register) are not diagnosed** (deferred)

   Confirmed behaviour: i01, i02, i08 compile and run on the fix (2/2). Diagnostics would need a retained DTF flag plus an address-of check and a C/C++ split (C++11/14 allow &r), which is not minimal and not the maintainer's practice (typename, and static/extern in casts and sizeof are accepted silently on main). Commit and PR wording changed to 'allocation hint may be ignored' and the missing diagnostics are listed as limitations.

11. **'No existing token value changes' claim is false (token inserted mid-enum)** (fixed)

   Confirmed from the diff (TK_REGISTER before TK_NUMBER shifted TK_NUMBER..TK_DECLTYPE). Token values are used only in memory (TK_ constants appear in Parser, Scanner, Declaration, Compiler, Constexpr, GlobalAnalyzer/Optimizer, InterCodeGenerator; nothing serialises them), so the shift is harmless; the token now sits after TK_EXTERN (TK_INLINE onward shift instead) and the PR makes no claim about values. Autotest, corpus and samples comparisons confirm no output change.

12. **Validation supports only narrow conclusions (corpus configs, -dregister= equivalence)** (fixed)

   PR now states the five corpus configurations explicitly, uses the same -ii for the samples comparison, gives exact counts (179 files x 5 = 895 pairs; 830 both compile; 829 identical; 1 different, explained; 10 status changes; 55 both fail), and limits the -dregister= claim to the test file (10/10 byte-identical: fixed compiler with keyword vs main with -dregister=).

13. **Regression test misses prototypes, function pointers, volatile, pointer const, while-body local, committed C++ test** (fixed)

   All added except a separate committed .cpp file: prototype `static int add_one(register int);` with `int add_one(int)` definition, `int (*fn)(register int)` parameter, `register volatile int v`, `register int * const p = &tv`, `register int t` inside a while body. The test compiled as C++ passes 10/10 and the C++ address-taking case (fixup/cpp_addr.cpp, `*(&x)` on a register local) passes 2/2; a committed .cpp copy was not added because the C and C++ parse paths for these declarations are the same ParseBaseTypeDeclaration code and it would add ten emulations without new coverage. Codex's note that the test had no while-body local was correct and is fixed.

14. **PR text needs narrower, more accurate claims (C++17 extension, corpus configs, implicit int)** (fixed)

   PR body rewritten: C++ acceptance described as leniency (deprecated C++11, removed C++17, word still reserved); five corpus configurations named; implicit-int `register x;` described as unsupported by Oscar64 for every storage class (`static x;` fails the same way on main), not as invalid C89.

</details>

## Last round: final-check findings and what happened to them

Changed in the last round: test. Commit before it: `7ef4f25451a0`.

| From | Severity | Finding | Resolution |
|---|---|---|---|
| codex final check #1 | medium | Empty #define register sits before main, contrary to 'placed after all other uses' | fixed |
| codex final check #2 | medium | Committed test cannot detect a #define register <body> leak (empty body has nothing to leak) | fixed |
| codex final check #3 | medium | Conflicting evidence for #define register static (before 10/10 vs 0/10 on main, fix and pinned) | fixed |
| codex final check #4 | low | Test header comment overstates the standard ('hint only', 'must be accepted and ignored') | fixed |
| codex final check #5 | low | 'ten files' miscounts (file, configuration) pairs; commit's byte-identity claim unqualified | fixed |
| self (reading Scanner.cpp for #3) | low | Docs and patch file outside the worktree still describe commit 7ef4f25 | left-for-jolyon |

<details><summary>Evidence, and what was re-run</summary>

1. **Empty #define register sits before main, contrary to 'placed after all other uses'** (fixed)

   Confirmed: in 7ef4f25 the macro and defined_away() were at lines 91-101, before main. Now defined_away has a prototype before main and its definition, preceded by the empty #define register, follows main; under conforming expansion the macro can no longer strip register from the volatile, pointer-const, for-init, nested-block and switch cases. New test: main 4da3147 0/10 (error 3005 at (17,31)), pinned v1.32.273 0/10, fix 10/10; gcc -std=c99 -pedantic-errors and g++ -std=c++14 run it with exit 0.

2. **Committed test cannot detect a #define register <body> leak (empty body has nothing to leak)** (fixed)

   Added at the end of the test, after the empty macro: `#undef register` + `#define register )` (unused; a leaked `)` cannot parse anywhere). Proof with a scratch build of the fix with TK_REGISTER moved back after TK_MEMMAP (outside TK_IF..TK_ASM, the reviewed commit's layout; build at r10-register-scratch/final/leakvariant): old test 10/10 on that variant (leak undetected), new test 0/10 with `registerstoragetest.c(169, 18) : error 3006: Declaration starts with invalid token ')'`; pp_define_register_body.c 0/10 and pp_define_register_inject.c 10/10 on the variant confirm it leaks. On the real fix the new test is 10/10. `#undef register` is a no-op on Oscar64 for a keyword (Scanner.cpp TK_PREP_UNDEF acts on TK_IDENT only) and keeps gcc from warning about a macro redefinition.

3. **Conflicting evidence for #define register static (before 10/10 vs 0/10 on main, fix and pinned)** (fixed)

   Re-run of the exact reproducers, ten configurations each. review/pp_define_register_static.c (`#define register static`, counter() called three times must return 3): main 4da3147 10/10, pinned v1.32.273 10/10, fix 0/10, where all ten compile with no diagnostic and print `Emulation result 1` (exit 20 from the nonzero result). review/pp_kw_macro_effective.c (`#define static`, same shape): 0/10 on main, pinned and fix alike. The '0/10 on main, fix and pinned' in the earlier write-up referred to the `#define static` probe, not to `#define register static`. Cause read from Scanner.cpp:757-760: a keyword macro is stored under Ident::Unique(TokenNames[tok]) = "'register'" (quoted), so it can never match an identifier. The PR body and commit message now state the regression explicitly, separating compile success from runtime result.

4. **Test header comment overstates the standard ('hint only', 'must be accepted and ignored')** (fixed)

   Header now reads: 'Exercise register storage-class declarations (C89 3.5.1, C99 6.7.1) for locals and function parameters; the allocation hint may be ignored. The keyword must not break the zero page register pragma, which has the same name, nor the preprocessor's handling of a macro named after it.'

5. **'ten files' miscounts (file, configuration) pairs; commit's byte-identity claim unqualified** (fixed)

   PR body now says 'the ten (file, configuration) pairs that go from error to ok are two source files that use register in all five configurations'. Commit message now says 'the regression test compiled with the keyword and the same file compiled on main with -dregister= give byte-identical output in all ten autotest configurations'; re-verified today on the amended test (minus the pragma line, which -dregister= would expand): 10/10 identical.

6. **Docs and patch file outside the worktree still describe commit 7ef4f25** (left-for-jolyon)

   docs/oscar64-upstream/11-r10-register.md (table row, 'Draft pull request' section, finding-4 text saying 'placed after all other uses') and tools/oscar64-upstream/patches/main/11-r10-register.patch were generated from 7ef4f25. The branch tip is now d091911 with a 169-line test; they need regenerating (git format-patch) and the PR text replaced with the one below. I did not touch them because they are outside the worktree and scratch directory.

**Re-validation.** Test-only change (autotest/registerstoragetest.c; oscar64/*.cpp untouched, bin/oscar64 unchanged apart from the relink make check does). On the final test content, ten configurations -ea -g {-bc|-n} x {none,-O2,-O0,-Os,-O3}: main 4da3147 0/10 (error 3005 'Identifier not defined register' at (17,31)), pinned v1.32.273 0/10, fix 10/10; as .cpp 10/10; -strict 10/10; -pp 10/10; -O2 -xz -Oz -n / -O2 -Oo -n / -O2 -Ox -n 3/3; gcc -std=c99 -Wall -pedantic and -pedantic-errors exit 0, g++ -std=c++14 exit 0. Pragma line no-op: with vs without `#pragma register(__tmpy, 0x02)` 10/10 byte-identical on the fix. Keyword (fix) vs -dregister= (main) on the test minus the pragma line: 10/10 byte-identical. Leak detection: scratch variant of the fix with TK_REGISTER outside TK_IF..TK_ASM fails the new test 0/10 (error 3006 on the leaked ')') while passing the old test 10/10. Finding-3 reproducers: pp_define_register_static.c main 10/10, pinned 10/10, fix 0/10 (compiles, Emulation result 1); pp_kw_macro_effective.c 0/10 on all three. Full autotest: make -k -j4 -C .../r10-register/make check > r10-register-scratch/autotest-final.log; autotest_diff.py vs autotest-base-4da3147.log: emulations base 1541, new 1551, new failures 0, fixed 0, failing in both 0; no make errors; registerstoragetest appears 10 times. Branch: one commit d091911 on 4da3147, working tree clean, 5 files (+228/-43); after the relink bin/oscar64 still gives 10/10 on the test. Corpus not re-run (no compiler change; the previous run corpus-fixup: 179x5, 830 compile on both, 829 identical, 1 explained -ii difference, 10 error->ok, stands).

</details>

## Final check (Codex, read-only, on the final commit)

<details><summary>SUBMIT AFTER CHANGES</summary>

VERDICT: SUBMIT AFTER CHANGES

1. **Medium — `autotest/registerstoragetest.c:93`: the empty macro precedes most local-declaration coverage.** It appears before `main`, contrary to the claim that it is “placed after all other uses.” With conforming macro expansion, it removes `register` from the volatile, pointer-const, for-init, nested-block and switch tests. Oscar’s current macro limitation masks this weakness. Move the macro and `defined_away` definition after `main`, adding a prototype before `main`.

2. **Medium — PR text: “placing the token inside the `TK_IF..TK_ASM` range”.** The implementation addresses the reported directive-body leak, but the committed empty macro cannot detect its return: there is no replacement text to leak. Add a small separate regression containing an unused `#define register )` followed by an ordinary `main`. This is a valid macro definition and directly tests that its replacement text stays out of the parser.

3. **Medium — conflicting evidence for `#define register static`.** The earlier findings say both “before 10/10” and “0/10 on main, fix and pinned”; risk 3 says it worked on main. These accounts cannot establish the same baseline behavior. Reconcile them with the exact reproducer and distinguish compilation success from runtime success. Keep the resulting compatibility regression explicit; existing keyword-macro bugs do not make newly broken valid preprocessing uses harmless.

4. **Low — `autotest/registerstoragetest.c:3`: “hint only” and “must be accepted and ignored”.** This retains the standards overstatement the prose revisions addressed. Replace it with: “Exercise register storage-class declarations for locals and parameters. The allocation hint may be ignored.” The standard does not require ignoring it, and its other constraints remain relevant.

5. **Low — PR validation: “the ten files that go from error to ok are the two that use `register`.”** Change “ten files” to “ten (file, configuration) pairs across two source files.” Also narrow the commit’s unqualified byte-identity claim to the tested regression source and ten configurations, as the PR body already does.

The supplied diff shows the pragma dispatch and token-placement fixes implemented consistently. I found no additional implementation defect from the material provided; execution results remain the author’s reported evidence.

</details>

## Before submitting

- Make the AI-assistance line the same in every PR body (some end with a sentence, some with a "Generated with Claude Code" footer), as Jolyon decides.
- Commit trailers: drop the `Claude-Session:` line and use one `Co-Authored-By:` line, as Jolyon decides for all PRs (see OSCAR64-UPSTREAM.md).

## Risks and limitations

1) `#define register static` (or any body) is now accepted but never expands: the one valid-C use this change silently breaks (compiles, wrong result); stated in the PR and commit. 2) `register` as an identifier stops compiling (never valid C/C++); keyword-named struct members hit a pre-existing segfault on main. 3) Constraint violations (file scope, &r, duplicate or combined storage classes, casts, sizeof, members) are accepted silently, like static/extern already are. 4) `int register a;` rejected like `int static a;`. 5) #ifdef/#ifndef/#undef/defined()/macro parameters cannot name register, as for every keyword. 6) Token values from TK_INLINE onward shift by one; in-memory only, autotest/corpus/samples show no output change. 7) Not tested on hardware; no code generation change. 8) `#define register )` in the test is deliberately unparsable so a leak is caught anywhere it lands; a maintainer may find it odd (comment explains it). 9) Outside my scope: docs/oscar64-upstream/11-r10-register.md and tools/oscar64-upstream/patches/main/11-r10-register.patch still describe 7ef4f25 and need regenerating for d091911; commit trailers (Co-Authored-By, Claude-Session) left as they were for Jolyon.

## Related bugs found, not fixed here

All pre-existing on upstream main 4da3147 and reproduced by me, none touched here. (a) Wrong code: `for (unsigned char c = 250; c != 4; c++) n++;` returns -246 instead of 10 at -O2 and -O3 (-n and -bc), with 'warning 2017: Invalid value range'; also on v1.32.273, so it affects nethack64 (review/side/loop_b2.c; worth a tests/oscar64-repros entry with a wider loop counter as workaround). (b) Compiler segfault calling the result of a function returning a function pointer, `pick(1)(4)`: 6/10 configurations on main, 10/10 on v1.32.273 (review/side/fnret_a.c, fnret_c.c). (c) Compiler segfault on C++ `auto * p = "ab";` in all configurations on main and v1.32.273 (review/cpp/c02_noreg.cpp). (d) Parse error inside a struct member declaration segfaults main (exit 139) where v1.32.273 exits 20: any keyword-named member (`int static;`, `int while;`, `int extern;`, review/i/s06-s09) and `struct s { register int a; }` on main before this fix (i09). (e) Keyword macros never expand: `#define static` is accepted and ignored (review/pp_kw_macro_effective.c), and #ifdef/#ifndef/defined()/macro parameters cannot name a keyword (`#ifdef inline` fails). (f) Generated bytecode for autotest/testint16mul.c at -bc -O2 depends on the include-directory path string (-ii) on main alone. (g) review/v/v10, v15, v20: two-declarator for-init with an unsigned char loop, a block-scope prototype `int g(int);` after a definition, and the fnret crash, fail with or without register on all compilers.

## Draft pull request

**Title:** Fix register storage class not accepted

````markdown
The `register` storage class is rejected with error 3005. C89 3.5.1 / C99 6.7.1 define it as a storage-class specifier whose allocation hint may be ignored; code ported from the 1990s, such as NetHack, uses it in thousands of local and parameter declarations.

```c
#include <assert.h>

static int sum(register const unsigned char * p, register unsigned char n)
{
	register int s = 0;
	while (n--)
		s += *p++;
	return s;
}

int main(void)
{
	static const unsigned char bytes[] = {1, 2, 3, 4, 5};
	register int i, t = 0;
	for (i = 0; i < 4; i++)
		t += i;
	assert(t == 6);
	assert(sum(bytes, 5) == 15);
	return 0;
}
```

Reproduce with `oscar64 -ea -g -n example.c` (same with `-bc` and at every optimisation level). Observed: `example.c(3, 25) : error 3005: Identifier not defined 'register'`, exit status 20. Expected: the program compiles, prints `Emulation result 0` and exits 0, as it does with gcc (`-std=c99 -pedantic`) and g++.

**Root cause.** `Scanner::NextRawToken` has keyword entries for `typedef`, `static`, `auto`, `extern` and `inline` but none for `register`, so the word reaches the parser as `TK_IDENT`. `Parser::ParseStatement` sees no declaration-starting token, parses an expression and fails on the identifier lookup; in a parameter list `IsTypeToken()` returns false, so `f(register int x)` is not recognised as a function declarator either.

**Fix.** Add `TK_REGISTER` next to `TK_EXTERN` and map `register` to it in the scanner. The parser accepts and ignores it the way it ignores `typename`: a `TK_REGISTER` case in `ParseBaseTypeDeclaration` that skips the token and recurses (locals, parameters, `const register`), and `TK_REGISTER` in the declaration-start lists of `ParseSimpleExpression`, `ParseStatement` and `IsTypeToken`. Two consequences of making the word a keyword are handled: `#pragma register(name, address)` no longer arrives as an identifier, so `ParsePragma` tests `TK_REGISTER` first and the existing pragma body moves into that branch unchanged (`git diff -w` shows the move); and placing the token inside the `TK_IF..TK_ASM` range keeps `#define register <body>` a valid directive instead of leaving the body in the token stream (with the token outside that range, `#define register volatile` followed by `main` fails with "Function declaration differs 'main'"). No code generation changes: the regression test compiled with the keyword, and the same file (minus its `#pragma register` line, which `-dregister=` would expand) compiled on main with `-dregister=`, are byte-identical in all ten configurations.

**Test.** `autotest/registerstoragetest.c`, registered in `autotest.bat` and picked up by the makefile, covers register locals with several declarators and initialisers, register parameters of char, pointer, struct pointer, long, float and typedef'd types, `const register`, `register volatile`, a register pointer with `const`, a prototype and definition differing only in `register`, a function-pointer parameter type with a register parameter, a `for (register int k = 0; ...)` header, register locals in a while body, nested blocks and a switch case, and `#pragma register(__tmpy, 0x02)` (the C64 default, so a no-op: the .prg is identical with and without the line). After `main`, where they cannot hide the other uses from a preprocessor that expands them, an empty `#define register` precedes a function with register parameters (the idiom NetHack uses), and an unused `#define register )` checks that the replacement list stays out of the program text: with the token outside the `TK_IF..TK_ASM` range the test fails in all ten configurations with "Declaration starts with invalid token ')'". The test fails on main with error 3005 in all ten `autotest/makefile` configurations and passes with this change; it also passes as C++, with `-strict`, with `-pp`, and in the three extra `autotest.bat` configurations. gcc `-std=c99 -pedantic-errors` and g++ `-std=c++14` compile and run it with exit 0.

**Validation** against main `4da3147` on Linux (gcc 13.3), C64 target:

- Example above and the new test: 0/10 before, 10/10 after (`-bc`/`-n` x default/`-O0`/`-O2`/`-O3`/`-Os`).
- Full autotest (`make -k check`): 1541 successful emulations on main, 1551 with this change (the ten new ones), no failures in either run.
- 179 C/C++ sources (the autotest directory plus local test files) in five configurations (`-n -O0`/`-O2`/`-O3`/`-Os`, `-bc -O2`): 830 (file, configuration) pairs compile on both compilers, 829 are byte-identical; the ten (file, configuration) pairs that go from error to ok are two source files that use `register` in all five configurations. The one difference, `testint16mul.c` at `-bc -O2`, is independent of this change: on either binary alone the output changes with the include-directory string passed via `-ii`.
- All 65 .prg files built by the samples makefile are byte-identical before and after when both compilers use the same `-ii`.
- `#pragma register` with the default C64 addresses compiles and runs in all ten configurations before and after, and the pragma's error messages for an unknown register name, a missing name, a bad start address and a missing comma are unchanged.
- `#define register static` followed by a function whose `register int n = 0` counter is expected to persist: on main 10/10 (the macro expands, `n` is static, the third call returns 3); with this change the program compiles without a diagnostic in all ten configurations and returns 1, because the macro no longer expands. The same program with `#define static` in place of the register macro returns 1 on main as well.

**Known limitations.** `register` is accepted and ignored wherever a type specifier may start, with no diagnostic: at file scope, on an object whose address is taken, after `static`, `extern` or `typedef`, repeated, in casts, `sizeof`, struct members, compound literals and C++ `new`. This mirrors how the compiler already treats `static` and `extern` in casts and `sizeof`. A storage class after the type specifier (`int register a;`) is rejected, exactly as `int static a;` is. Like every other keyword, `register` cannot be redefined by `#define`: the directive is accepted, but the macro is recorded under the token's display name and never expands, so `#define register static` is silently a no-op where main honoured it (the one valid-C use this change breaks; the common empty `#define register` keeps working), and `#undef`, `#ifdef`, `#ifndef`, `defined()` and macro parameter lists cannot name `register`, as they cannot name any keyword. Programs that used `register` as an identifier, which was never valid C or C++, stop compiling. In C++ mode the keyword is accepted without a warning although C++17 removed the storage class (the word stays reserved).

This was prepared with AI assistance (Claude Code); the change and all measurements above were checked by running the commands shown, and two independent reviews were applied before submission.
````
