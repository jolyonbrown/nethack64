# 12. Fix spaces and tabs between '#' and a preprocessor directive name

| | |
|---|---|
| Branch | `fix/r7-hash-space` in `~/src/oscar64-dev`, commit `9ffb4fba7b3d`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/12-r7-hash-space.patch`](../../tools/oscar64-upstream/patches/main/12-r7-hash-space.patch) |
| Kind | rejects valid C (preprocessor) |
| Since | v1.32.273 and main |
| NetHack | Compat #3 (repro r7): `# define` with a space after `#`, more than 1,500 lines in NetHack's headers. Workaround: `tools/oscar_normalize.py`. |
| Reviews | Opus (round 1, ran probes): submit-after-changes, 1 high, 2 medium, 3 low; Codex (read the diff): submit after changes; fix-up: ready; final Codex check: submit after changes |
| Recommendation | **Submit.** |

## In plain words

C lets you write "# define" or "#  ifdef" with blanks after the hash; NetHack's headers do this everywhere, and Oscar64 choked on it. The fix skips those blanks before reading the directive name. The last reviewer suspected, without being able to run anything, that the skip could run off the end of a macro's text and glue a '#' produced by a macro to a word in the line that used the macro, turning it into a fake #define. He was right: Oscar64 stores every macro body with one blank on the end, the skip ate that blank, and the next read fell through into the caller's line. The skip now stops at that last blank, so the behaviour at the edge of a macro is exactly what it was before the fix. Everything was re-run: the eight edge-case probes, the regression test and example in all ten configurations, the full autotest (1551 runs, none failing), the 184-program byte comparison and the 67 samples. One sample looked different, but swapping include directories between the two compilers swaps the result and a shared include directory makes them identical, so that is the known install-path effect, not this change.

## The fix

In both Scanner::NextRawToken and Scanner::NextSkipRawToken, the '#' case skips spaces and tabs before collecting the directive name (not in assembler macro text, where "# x" is an immediate operand). This round: the skip no longer consumes the final blank of a macro expansion text (Macro::SetString always appends one), so the following NextChar() reads that blank instead of popping the expansion, and a macro body ending in '#' cannot form a directive with the caller's text (`#define HASH() #` / `HASH()define X 1` is rejected again, as on 4da3147). The `!blanks` guard keeps "# #" as two tokens. Comments and the commit message were updated to describe the boundary rule; test file unchanged.

## Regression test

autotest/prep_hash_space_test.c (registered in autotest.bat, picked up by autotest/makefile), unchanged this round: indented directives in active and skipped groups, nested #if/#ifdef/#elif/#else/#endif with depth tracking, # include, # undef, "# x" against "#x", "##", and '#' immediates in assembler macro text. 0/10 before, 10/10 after. The expansion-boundary cases (HASH()define X 1 and seven variants) are must-fail programs, which autotest cannot express without bespoke harness rules; they are documented in the PR body and kept as probes in /home/jolyon/nethack64/build/oscar64-wt/r7-hash-space-scratch/final/.

## Evidence

*These are the fix-up round's results, for commit `b0b40809fb82`. The last round changed the code; its re-validation of the final commit is under "Last round" below.*

**Repro matrix.** All with -ea -g in the ten configurations; B = ~/src/oscar64-base (4da3147), F0 = submitted fix 4d2acc6 (binary preserved in r7-hash-space-scratch/fix0), A = final, P = pinned v1.32.273. Scripts: r7-hash-space-scratch/mx.sh (ten configurations) and q.sh; probes in r7-hash-space-scratch/probes/ (copies of the review's p/ files plus x1-x13, y1-y5).
- autotest/prep_hash_space_test.c: B 0/10, F0 0/10, A 10/10, P 0/10. tests/oscar64-repros/r7_space_after_hash.c and pr_example.c: B 0/10, A 10/10.
- Asm immediates asm1, asm2, asm3, asm4, asm5, e11: B 10/10, F0 0/10, P 10/10, A 10/10. asm6 ('#E' no space, pre-existing error 3068): rejected by B, F0, P, A. asm7/asm9 (spaced directives inside __asm, active and skipped): B 0/10, A 10/10. asm8, g1 controls: B and A 10/10.
- e12 (macro expanding to '#' then 'define'): B 0/10, F0 10/10 (bug), A 0/10 (rejected again), P 0/10. x12 (unspaced '#define D #define X 1' then D): accepted by B, A and P alike (pre-existing); x13 (same with '# define' in the body): B 0/10, A 10/10 (consistent with x12).
- '# #': x2 STRINGIZE(# #) gives \"# #\" on B, F0, A, P (10/10); x3/c8 'a # # b' rejected by all; x1 TWO_HASHES stringized indirectly fails on all (pre-existing indirect-stringify defect).
- EOF: e1/x5/x6 (active '#' at EOF, no trailing newline) error 3006 on B/F0/A; e2/e3/x7 (skipped group, '#'+blank/tab at EOF, no #endif) 10/10 on all; x8/x9 10/10 on all. No hang or crash anywhere.
- Stringify: x10 (STR1 == STR2 == STR3) B 0/10, A 10/10; c9 B 0/10, A 10/10 (same wrong strings as c9b '#x' on B); c6/c7 B compile error, A emulation -1 (pre-existing stringify defects now visible).
- Still rejected before and after (out of scope): c2 comment between '#' and name, c12/e1 null directive, e4 \\f/\\v.
- Now accepted, matching gcc: c3 line splice, c4 CRLF, c5 skipped '# elif', e5 300 blanks, e6 '# pragma once', e7 skipped '# include'/'# error', e8 active '# error' (exit 1, error 3032), e9 oscar extensions, e10 mid-line (B already accepts mid-line '#define'), cpp1 C++ (0/10 -> 10/10); cpp1b/cpp2/c10 controls fail identically on B and A for unrelated reasons (local-scope CAT).
- Adjacent, not this change: y4_n4.c/y5_sum.c/x11 at -n -O3 return wrong values on B, A and P alike (see adjacent_bugs).

**Autotest.** make -k -j4 -C /home/jolyon/nethack64/build/oscar64-wt/r7-hash-space/make check (nohup, waited with tail --pid) > /home/jolyon/nethack64/build/oscar64-wt/r7-hash-space-scratch/autotest-fixup.log. autotest_diff.py /home/jolyon/nethack64/build/oscar64-wt/autotest-base-4da3147.log autotest-fixup.log: emulations base 1541, new 1551 (+10 = the new test in ten configurations); new failures 0; fixed 0; failing in both 0. All 1551 'Emulation result' lines are 0; no make error lines. The compiler had been rebuilt from the committed Scanner.cpp before the run (make check also relinks it).

**Corpus.** corpus_diff.py ~/src/oscar64-base/bin/oscar64 <worktree>/bin/oscar64 --out r7-hash-space-scratch/corpus-fixup -j4 (run after make check finished, not concurrently). 179 files (159 autotest/*.c and *.cpp + 20 tests/oscar64-repros/*.c) x 5 configurations (-n -O0/-O2/-O3/-Os, -bc -O2) = 895 compilations per compiler. Both compile: 830; identical: 829; different: 1; status changed: 10; fail with both: 55 (895 - 830 - 10). The one difference is autotest/testint16mul.c -bc -O2, the known include-path dependence of 4da3147's bytecode output: re-verified by swapping include paths (base compiler with -ii=<worktree>/include gives the new bytes, new compiler with -ii=~/src/oscar64-base/include gives the base bytes; the two include trees are identical by diff -rq). The 10 status changes are autotest/prep_hash_space_test.c and oscar64-repros/r7_space_after_hash.c, error -> ok in all five configurations; both use the fixed construct. Additionally all 68 samples/ files (67 .c + memmap/easyflashcall.cpp) compiled standalone with both compilers in -n -O2 and -bc: 136 compilations, 133 byte-identical, 3 fail with both (games/missile.c -bc, memmap/tsr.c both), 0 differ (r7-hash-space-scratch/samples-cmp.txt).

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| both | high | Breaks inline-asm immediates written as '# name' in macro text (Opus finding 1 / Codex finding 2) | fixed |
| opus | medium | '# x' now compiles to the same wrong strings as '#x' (trailing blank, unexpanded indirect stringify) | fixed |
| both | medium | Test's '##' and stringify assertions were vacuous; asm path, skipped '# elif', C == 3, branch-selecting '# elif'/'# else' and depth tracking untested (Opus finding 3 / Codex finding 4) | fixed |
| opus | low | Blank skip runs past the end of a macro expansion, so a macro expanding to '#' can form a directive (e12) | fixed |
| both | low | '# #' scanned as the '##' token (Opus finding 5 / Codex finding 1) | fixed |
| opus | low | Comments, the null directive and form feed / vertical tab between '#' and the name are still rejected | out-of-scope |
| opus | low | PR text issues 1-9 (wrong error line numbers, '56 repro files', false asm claims, '## unchanged', vacuous test claims, stringify wording, standard citations, commit message, missing samples check) | fixed |
| codex | medium | Removing the NextChar() success checks introduces an unverified EOF assumption (possible infinite loop) | rejected |
| codex | low | Also test '#/**/define' and a backslash-newline between '#' and the name | deferred |
| codex | low | PR text: narrower claims ('check unchanged so behaviour unchanged', 'group never ends', 'no codegen touched so no runtime change', corpus as universal compatibility, commit message '##' claim) | fixed |

<details><summary>Evidence for each finding</summary>

1. **Breaks inline-asm immediates written as '# name' in macro text (Opus finding 1 / Codex finding 2)** (fixed)

   Reproduced with the submitted fix (F0 = copy of 4d2acc6's binary in r7-hash-space-scratch/fix0): asm1, asm2, asm3, asm4, asm5 and e11 (review p/ probes) are exit 0 / emulation 0 in 10/10 with base 4da3147 and with pinned v1.32.273, and exit 20 in 10/10 with F0 ('error 3027: Invalid assembler operand' or 'error 3068: Invalid preprocessor command'). Cause: the blank skip ran whenever '#' took the directive path, which in assembler mode includes offset 1 of any macro body or argument. Fix adopted after evaluating Opus's V1 variant myself: the skip is guarded by `if (!mAssemblerMode || !mMacroExpansion)`, so assembler macro text keeps the old TK_HASH + name reading while directives in source lines (also inside __asm blocks, asm7/asm9) are still recognised. With the final compiler asm1-asm5, e11 and my combined x11-style cases are 10/10 again; the new autotest contains four such immediates and fails on F0 at exactly that line (prep_hash_space_test.c(152,1): Invalid preprocessor command 'N').

2. **'# x' now compiles to the same wrong strings as '#x' (trailing blank, unexpanded indirect stringify)** (fixed)

   Confirmed: c9_print_strings.c compiles and runs with the fix (0/10 before), c6_c99_hash_hash.c and c7_c99_debug.c go from compile error (before) to emulation -1 (after), and c9b (unspaced '#x') shows the same strings on 4da3147. The stringify defects (Macro::SetString appends ' ', Scanner.cpp:201-223; indirect stringify copies argument text) are pre-existing and not touched here; they are listed under adjacent bugs. What this PR controls was fixed: the PR text now says '# x' behaves exactly like '#x' including its existing defects, and the test asserts strcmp(STR1(hello), STR2(hello)) == 0 (and a tab variant) instead of checking two characters.

3. **Test's '##' and stringify assertions were vacuous; asm path, skipped '# elif', C == 3, branch-selecting '# elif'/'# else' and depth tracking untested (Opus finding 3 / Codex finding 4)** (fixed)

   Confirmed: CAT(a, b) with 'a ## b' passed only because arguments were spelled like the parameters (c11: 'a ## b' with CAT(v, w) gives 'Unknown identifier' on both compilers, 'a##b' works on both); STR was checked at [0] and [4]. Rewritten autotest/prep_hash_space_test.c: c_value = C checked == 3 before '# undef C'; I (spaced '# elif' selects), J (spaced '# else' reached), K ('# elif 1' inside '#if 0', the NextSkipRawToken evaluation path, c5-style); WRONG/DEPTH_OK sentinel where an unspaced #else sits inside a spaced '# if' in a skipped group; strcmp of '#x' vs '# x' and '#\tx'; CAT(v, w) with a##b and int vw; four assembler immediates (object-like '# N5', function-like '# x', argument '# E9' enum and '# N5' macro). Results: base 0/10 (fails at line 4), F0 0/10 (fails at the asm line 152), final 10/10, pinned 0/10. EOF and '# #' cases are must-not-compile or non-observable and were checked as scratch probes instead (x3/c8 rejected by all compilers; x5-x9/e1-e3 no hang).

4. **Blank skip runs past the end of a macro expansion, so a macro expanding to '#' can form a directive (e12)** (fixed)

   Confirmed: e12_expansion_becomes_directive.c (#define HASH # / HASH define X 1) is exit 20 on base and pinned, exit 0 / emulation 0 in 10/10 with F0, because the skip called NextChar(), which pops the expansion. Final code peeks mLine[mOffset] and advances mOffset only within the current text, then keeps the original `while (NextChar() && IsAlpha(mTokenChar))` loop. e12 is rejected again in 10/10 ('error 3006 ... '#''), and e11 (the asm form of the same mechanism) passes.

5. **'# #' scanned as the '##' token (Opus finding 5 / Codex finding 1)** (fixed)

   Confirmed by code reading: with F0 the '##' check ran after blanks were consumed, so '# #' produced TK_PREP_CONCAT. Observable effect is small because TK_PREP_CONCAT is only produced, never consumed (grep: Scanner.cpp lines 1441/1844 only); '##' pasting happens on macro text. Codex's examples checked: STRINGIZE(# #) gives "# #" on base, F0, pinned and final (x2, 10/10 each: argument text is stringified verbatim); '#define TWO_HASHES # #' stringized indirectly fails on all four compilers for the pre-existing indirect-stringify defect (x1), not because of this change; 'a # # b' is rejected by all four (x3/c8, 'Unknown identifier'). Final code records whether blanks were skipped and forms TK_PREP_CONCAT only when `!blanks`, so '# #' stays two '#' tokens exactly as on 4da3147.

6. **Comments, the null directive and form feed / vertical tab between '#' and the name are still rejected** (out-of-scope)

   Confirmed pre-existing: c2_comment_between.c ('#/* c */define'), c12/e1 (null directive '#'), e4 ('#\fdefine', '#\vdefine') fail with error 3006 on base, F0, pinned and final (10/10 each; gcc accepts c2 and the null directive). Not touched by this change; PR title and body say 'spaces and tabs' and list these as not covered. NetHack 3.4.3 has none of these forms in code that matters to the port (one null directive in the Mac-only macconf.h).

7. **PR text issues 1-9 (wrong error line numbers, '56 repro files', false asm claims, '## unchanged', vacuous test claims, stringify wording, standard citations, commit message, missing samples check)** (fixed)

   Re-derived every number: the PR example on 4da3147 fails at (6, 1) error 3006, (6, 9) error 3037, (7, 1) 'BAR' (quoted in the new body); corpus is 159 autotest files + 20 nethack64 repro files = 179 (described as '20 additional test programs'); the asm claims are replaced by a description of what is deliberately unchanged in assembler macro text; '# #' handling stated explicitly; test paragraph describes the real assertions; '#x' defects named; test comment and body cite C89 3.8 / C99 6.10p5; commit message rewritten (no longer claims '##' with a space after '#'); samples check added: 68 files (67 .c + 1 .cpp), -n -O2 and -bc, 136 compilations, 133 byte-identical, 3 fail with both (games/missile.c -bc, memmap/tsr.c both), 0 differ; testint16mul.c -bc -O2 explained by the -ii swap (base with the worktree include gives the new bytes, new with the base include gives the base bytes, include trees identical by diff -rq). The private claude.ai session URL stays because the repo's attribution rule requires it.

8. **Removing the NextChar() success checks introduces an unverified EOF assumption (possible infinite loop)** (rejected)

   Not reproducible, and moot in the final code. NextChar() at end of input (Scanner.cpp:2534-2570) sets mTokenChar = 0 and returns false; 0 is neither ' ', '\t' nor alphabetic, so both loops in the submitted fix terminated. Probes with no trailing newline and EOF right after '#', '# ', '#\t' in a skipped group, a directive name and '#endif' (x5-x9), plus e1-e3, exit promptly on base, F0 and final with identical results (error 3006 for the active-code '#' cases, 0/0 for the skipped and directive cases). The final code keeps the original `while (NextChar() && IsAlpha(mTokenChar))` loop and only pre-skips blanks by peeking mLine[mOffset] within the current text, so the termination check Codex asked to preserve is preserved.

9. **Also test '#/**/define' and a backslash-newline between '#' and the name** (deferred)

   Checked as probes rather than in the autotest: c2 ('#/* c */define X 1') is rejected before and after, a pre-existing gap listed as a limitation (out of scope here). c3 ('#\\\n define Y 2', line splice then blanks) is 0/10 on base and 10/10 on the final compiler, because splicing yields '#  define', which this fix now accepts. Not added to the committed test to avoid re-running the 20-minute autotest after validation; a follow-up could add the splice case.

10. **PR text: narrower claims ('check unchanged so behaviour unchanged', 'group never ends', 'no codegen touched so no runtime change', corpus as universal compatibility, commit message '##' claim)** (fixed)

   The new body describes the actual tokenization change (which '#' readings change, which stay), says a skipped group 'is not closed where it should be', drops the 'no codegen touched' inference, presents corpus/samples/autotest numbers as results on those inputs and configurations, and the commit message no longer claims to test '##' with a space after '#'. Unchanged C++ behaviour is reported as what was measured: cpp1_spaced_directives.cpp 0/10 -> 10/10, the autotest .cpp files in the corpus and samples/memmap/easyflashcall.cpp byte-identical.

</details>

## Last round: final-check findings and what happened to them

Changed in the last round: code. Commit before it: `b0b40809fb82`.

| From | Severity | Finding | Resolution |
|---|---|---|---|
| final-check.md / Codex (gpt-6-astra), medium | medium | Blank skip reaches the end of a macro expansion; NextChar() then pops it and reads the directive name from the caller (HASH()define X 1) | fixed |
| final-check.md / Codex, same item: 'retain the case as a negative regression test' | low | Add HASH()define as a negative (must-fail) autotest | deferred |
| own check during validation (samples byte comparison) | low | samples/games/connectfour.c -bc compiles to different bytes with the before and after compilers | rejected |
| task rule | low | Commit trailers (Co-Authored-By model name, Claude-Session link) and PR placeholder | left-for-jolyon |

<details><summary>Evidence, and what was re-run</summary>

1. **Blank skip reaches the end of a macro expansion; NextChar() then pops it and reads the directive name from the caller (HASH()define X 1)** (fixed)

   Confirmed. Macro::SetString (Scanner.cpp:201-224) appends one blank to every macro body and argument, so a body '#' is stored as "# ". The fix-up's skip consumed that blank, and the following NextChar() popped the expansion with the caller's saved character ('d' of define, since the function-like path calls NextChar() after ')'), so `#define HASH() #` / `HASH()define X 1` compiled and ran (exit 0, emulation 0) with b0b4080 in all 10 configurations, while 4da3147 rejects it (error 3006). The object-like `HASH define` probe only passed because the saved character there is the caller's blank. Fix: the skip now stops at the last character of an expansion text (`&& !(mMacroExpansion && !mLine[mOffset + 1])`) in both NextRawToken and NextSkipRawToken, so NextChar() reads that blank and the '#' stays a bare token, exactly as on the base. After: p1 `HASH()define X 1`, p4 (body `# ` with trailing blank), p2/p3/p5/p6/p7/p8 (object-like with space/tab, `HASH() define`, `ID(#)define`, `HASH()\tdefine`, `HASH()` at end of line) all exit 20 with error 3006 in 10/10 configurations with both compilers; e11 (asm `lda HASH E`), e12, x12, x13, x10, x11, c8, x2 unchanged from the fix-up round. Probes and logs: /home/jolyon/nethack64/build/oscar64-wt/r7-hash-space-scratch/final/.

2. **Add HASH()define as a negative (must-fail) autotest** (deferred)

   autotest has no generic expected-failure mechanism: the only must-fail tests (enum range / c23 enum / warning constraints) each have bespoke subroutines in autotest.bat and bespoke rules in autotest/makefile with expected status and diagnostic text. Adding such a pair for one scanner edge case is out of proportion for this PR and unlike upstream's own PRs. The eight boundary probes are instead recorded in the PR body's validation (rejected with error 3006 before and after, 10 configurations each) and kept in the scratch directory.

3. **samples/games/connectfour.c -bc compiles to different bytes with the before and after compilers** (rejected)

   Reproducible per build (3 identical runs each: base 9f31bcfd..., after d208e490...; .bcs bytecode set differs, code 10 bytes longer) but caused by the include path, not the fix: the after compiler with -ii=~/src/oscar64-base/include gives the base bytes, the base compiler with -ii=<worktree>/include gives the after bytes, and both compilers give identical bytes (9f31bcfd...) from one shared copy of the include tree (the two trees are identical, diff -rq). Same class as the known autotest/testint16mul.c -bc -O2 quirk. Evidence in /home/jolyon/nethack64/build/oscar64-wt/r7-hash-space-scratch/final/cf/.

4. **Commit trailers (Co-Authored-By model name, Claude-Session link) and PR placeholder** (left-for-jolyon)

   Trailers kept exactly as in b0b4080 (Co-Authored-By: Claude Opus 5.5, Claude-Session link). No #NNN placeholder appears in this commit message or PR text.

**Re-validation.** Rebuilt bin/oscar64 (make -C make -j6 compiler, 10:54; make check relinked it unchanged). Probes, 10 configurations (-ea -g {-bc,-n} x {default,-O2,-O0,-Os,-O3}), base 4da3147 vs 9ffb4fb: p1_fn_adjacent (HASH()define X 1) base 10/10 error 3006, after 10/10 error 3006 (was 10/10 accepted with b0b4080); p2-p8 boundary variants 10/10 rejected with both; e11 asm `lda HASH E` 10/10 ok both; e12 10/10 rejected both; x12 10/10 ok both; x13 (`# define` in a body) rejected before, ok after, as in the fix-up round; x10 stringify `# x` == `#x` 0/10 before, 10/10 after; x11 asm immediates 9/10 both (the -n -O3 failure is the pre-existing -O3 issue, identical before and after); c8 `a # # b` rejected both; x2 ok both; pr_example 0/10 before, 10/10 after; autotest/prep_hash_space_test.c 0/10 before, 10/10 after. Full autotest: make -k -j4 -C make check > r7-hash-space-scratch/autotest-final.log: 1551 emulations (baseline 1541), autotest_diff.py: new failures 0, fixed 0, failing in both 0. corpus_diff.py base vs after --out r7-hash-space-scratch/corpus-final -j4: 184 files x 5 configurations, both compile 845, identical 844, different 1 (autotest/testint16mul.c bc-O2, the known include-path dependence), status changed 10 (prep_hash_space_test.c and r7_space_after_hash.c, error -> ok, all five configurations each). Samples (67 .c, standalone, -n -O2 and -bc): 134 compiles, 131 compile with both (games/missile.c -bc and memmap/tsr.c fail with both), 130 byte-identical, 1 differs (games/connectfour.c -bc) and is shown to be include-path dependent: identical bytes with a shared include tree, swapped bytes with swapped -ii= paths. Branch: one commit 9ffb4fb on 4da3147, worktree clean, trailers unchanged.

</details>

## Final check (Codex, read-only, on the final commit)

<details><summary>SUBMIT AFTER CHANGES</summary>

VERDICT: SUBMIT AFTER CHANGES

1. **Medium — `oscar64/Scanner.cpp:1440,1852`; PR: “a macro body that ends in `#` cannot reach past its expansion.”** The new whitespace loop stays within `mLine`, but the immediately following `NextChar()` can still pop the expansion after that loop consumes its trailing blanks. The reported `HASH define X 1` probe leaves whitespace in the caller, which can mask this remaining boundary case. Check an immediately adjacent name:
   ```c
   #define HASH() #
   HASH()define X 1
   int main(void) { return X - 1; }
   ```
   Based on the described `NextChar()` behaviour, this can consume `define` from the caller where the baseline stopped at the expansion’s trailing blank. Before submission, verify this case against both compilers. Preserve the token boundary when the blank skip reaches the expansion terminator, and retain the case as a negative regression test if confirmed. The existing probe alone does not support marking the expansion-boundary finding fully fixed.

The other earlier fixes are reflected in the diff, and the revised positive regression test meaningfully checks directive handling and assembler compatibility.

</details>

## Check of the last-round commit (Codex, read-only)

<details><summary>SUBMIT AFTER CHANGES</summary>

VERDICT: SUBMIT AFTER CHANGES

1. **[low] `autotest/prep_hash_space_test.c:42` — skipped-group tab coverage is ineffective.** If `NextSkipRawToken` ignores both tabbed inner directives, the unspaced outer `#else` still selects `G == 2`. The test therefore does not establish the PR’s claim that these directives “must be recognised for the group to close.” Add a case where a tabbed `#	endif` must close an unspaced `#if 0`, followed by a definition asserted in `main`.

2. **[low] PR text: “the rest of the file disappears into it.”** This still overstates the skipped-group failure. A later unspaced directive can end skipping at the wrong nesting level. Replace with: “conditional nesting and branch selection can be misinterpreted, causing intended active code to be skipped.”

3. **[low] PR text: “all validation above were checked by running the commands shown.”** Most validation commands and the 26 additional programs are not supplied. Replace “the commands shown” with “the validation runs described above,” or provide the scripts and fixtures needed to reproduce those results.

No code correctness blocker found in the supplied diff. The earlier assembler, expansion-boundary, token-concatenation, and EOF concerns appear resolved; the regression test otherwise meaningfully guards the fix.

</details>

## Before submitting

- Add a case where a tabbed `#\tendif` must close an unspaced `#if 0` (the current skipped-group tab case would pass even if tabbed inner directives were ignored).
- PR text: replace "the rest of the file disappears into it" with "conditional nesting and branch selection can be misinterpreted, causing intended active code to be skipped", and "checked by running the commands shown" with "the validation runs described above".
- Make the AI-assistance line the same in every PR body (some end with a sentence, some with a "Generated with Claude Code" footer), as Jolyon decides.
- Commit trailers: drop the `Claude-Session:` line and use one `Co-Authored-By:` line, as Jolyon decides for all PRs (see OSCAR64-UPSTREAM.md).

## Risks and limitations

(1) In a macro body, "# define X 1" is now scanned as a directive during expansion, like "#define X 1" already was on the base (C says neither is a directive); consistent with "# x behaves like #x", stated in the PR. (2) `# x` stringify inherits the existing #x defects (trailing blank in the string, unexpanded argument in indirect stringify); stated in the PR. (3) Comments between '#' and the name (`# /* c */ define`), the null directive (`#` alone) and form feed / vertical tab remain rejected as before; stated in the PR. (4) The boundary rule relies on Macro::SetString's trailing blank; if that sentinel were ever removed, a body ending in '#' would again reach the caller through NextChar(), which is the base behaviour for any '#' at the very end of an expansion anyway. (5) Only spaced forms change behaviour: corpus and samples byte-identical apart from the two known include-path-dependent files.

## Related bugs found, not fixed here

All pre-existing on 4da3147 (and on pinned v1.32.273 where stated), not fixed here; repro files in /home/jolyon/nethack64/build/oscar64-wt/r7-hash-space-scratch/probes/: (a) -O3 miscompile unrelated to the preprocessor: a global char array written only from inline asm with four or more 'sta r + n' stores and read back in C returns wrong values with -n -O3 (y4_n4.c emulation 1, y5_sum.c sum 6 instead of 15, i.e. r[3], r[4] read as 0); passes with -O0/-O2/-Os and -bc; 3 stores pass; scalar chars pass; same on 4da3147, v1.32.273 and the fixed compiler. (b) Stringify appends a trailing blank ('#x' of hello gives \"hello \") and indirect stringify does not expand arguments (XS(FOO) gives \"x \"); the C99 6.10.3.3 hash_hash example gives \"a \" (c6, c7, c9b, x1). (c) The null directive ('#' alone on a line) is a parse error (c12, e1); NetHack uses one in the Mac-only macconf.h. (d) A comment between '#' and the directive name is rejected (c2), as are '#\\f' and '#\\v' (e4); gcc accepts/warns. (e) A macro body that spells a directive is treated as a directive when expanded ('#define D #define X 1' then 'D' defines X, x12), contrary to C99 6.10.3.4p3. (f) A mid-line '#define' after a declaration is accepted (e10). (g) testint16mul.c -bc -O2 output depends on the include path (-ii swap shows it). (h) Review probes c10/cpp2/cpp1b: a function-like CAT used on a block-scope variable fails with 'Unknown identifier' on both compilers (not investigated).

## Draft pull request

**Title:** Fix spaces and tabs between '#' and a preprocessor directive name

````markdown
C allows spaces and tabs between the `#` and the directive name (C89 3.8, C99 6.10p5), in active code and inside skipped `#if` groups. Oscar64 rejects such lines. This example, which GCC and clang accept, fails to compile:

```c
#include <assert.h>

#ifdef FOO
# define X 1
#else
# ifdef BAR
#  define X 2
# else
#  define X 0
# endif
#endif

int main(void)
{
	assert(X == 0);
	return 0;
}
```

Reproduce with `oscar64 -ea -g -n example.c` (the same with `-bc` and at every optimisation level). Observed on `4da3147`:

```
example.c(6, 1) : error 3006: Declaration starts with invalid token ''#''
example.c(6, 9) : error 3037: Semicolon expected
example.c(7, 1) : error 3005: Identifier not defined 'BAR'
...
```

Expected: the file compiles and the emulation returns 0. This style is common in older code bases (NetHack 3.4.3's headers use `# define` / `#  ifdef` throughout, which is where we found it).

**Root cause.** In `Scanner::NextRawToken` and `Scanner::NextSkipRawToken` (`oscar64/Scanner.cpp`, the `'#'` case) the directive name is collected with `while (NextChar() && IsAlpha(mTokenChar))`, starting at the character right after the `#`. A blank ends the loop at once with an empty name, which falls through to `TK_PREP_IDENT` with an empty identifier; `NextPreToken` turns that into a bare `TK_HASH`. In active code the line is then parsed as C, and in a skipped group `# endif` / `# else` / `# elif` are never recognised, so the group does not end where it should and the rest of the file disappears into it.

**Fix.** In both scanners, skip spaces and tabs after the `#` before collecting the name. Three details keep everything else as it was:

- The skip reads `mLine` directly and stops at the last character of a macro expansion text (every macro body and argument ends in one blank, appended by `Macro::SetString`). That blank is what `NextChar()` then reads, so a macro body ending in `#` still yields a bare `#` and never picks up a directive name from the text that follows the expansion (`#define HASH() #` / `HASH()define X 1` is rejected, as before).
- The skip is not done in assembler macro text, where `# x` is an immediate operand (`#define IMM(x) # x` / `lda IMM(7)`, `LDA(# E9)`).
- `##` is formed only when no blank was skipped, so `# #` remains two tokens.

The keyword table and the `TK_PREP_IDENT` fallback are unchanged. Because the stringify operator takes the same path during macro expansion, `# x` in a macro body now behaves exactly like `#x` (previously a parse error), including the existing quirks of `#x` (a trailing blank in the string, and the argument not expanded in indirect stringify). Likewise `#define D # define X 1` / `D` now acts like the unspaced form already did on the base. Not covered, and rejected as before: a comment between the `#` and the name (`# /* c */ define`), the null directive (`#` alone), and form feed or vertical tab after the `#`.

**Test.** `autotest/prep_hash_space_test.c`, registered in `autotest.bat` (picked up by `autotest/makefile`). It covers `# include`, `# define` / `#\tdefine` / `  #  define`, nested `# ifdef` / `# else` / `# endif` in active and skipped groups (including an `#if 0` group with tab-indented directives that must be recognised for the group to close, and an unspaced `#else` that belongs to an inner `# if`), `# if defined(A) && defined(B)` / `# elif` / `# else` in active and skipped groups, `# undef`, `# x` and `#\tx` giving the same string as `#x`, `a##b`, and `#` immediates in assembler macro text (object-like and function-like macros, and `# x` as a macro argument). Before: fails to compile in all ten `-ea -g {-bc,-n} x {default,-O0,-O2,-O3,-Os}` configurations. After: passes all ten.

**Validation** against `main` 4da3147 on Linux (x86-64), C64 target:

- New test and the minimal example: 10 configurations each, 0/10 before, 10/10 after.
- Full autotest (`make -k -j4 -C make check`): 1541 successful emulations on the baseline, 1551 with the patch and the new test; no failures in either run.
- 184 programs (all `autotest/*.c` and `*.cpp` plus 26 small test programs of ours) compiled with both compilers in five configurations (`-n -O0/-O2/-O3/-Os`, `-bc -O2`): 845 compile with both, 844 byte-identical `.prg` files. The only status changes are the two files that use the fixed construct (error -> ok). The one difference (`autotest/testint16mul.c`, `-bc -O2`) is the known dependence of bytecode output on the include path: swapping the include directories with `-ii=` swaps the result, and both compilers produce identical bytes from one shared include tree.
- All 67 `samples/**/*.c` compiled standalone in `-n -O2` and `-bc`: 131 of 134 compile with both (games/missile.c `-bc` and memmap/tsr.c fail with both), 130 byte-identical; `games/connectfour.c -bc` differs for the same include-path reason and is identical with a shared include tree.
- Probes, before and after, 10 configurations each: a macro expanding to `#` followed by a directive name in the caller (`HASH()define X 1`, `HASH define X 1`, `HASH() define X 1`, `ID(#)define X 1`, with spaces, tabs, and a body `# ` with a trailing blank) is rejected with error 3006 by both; `lda HASH E` in assembler text gives 5 with both; `#x` / `# x` strings compare equal; `a # # b` is rejected by both; `#` alone is rejected by both.

This fix was prepared with AI assistance (Claude Code); the root cause analysis, the change and all validation above were checked by running the commands shown.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
````
