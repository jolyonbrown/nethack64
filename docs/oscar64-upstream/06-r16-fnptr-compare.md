# 06. Fix comparison of function pointer with function name

| | |
|---|---|
| Branch | `fix/r16-fnptr-compare` in `~/src/oscar64-dev`, commit `6e2e67e04920` (stacked on #01) |
| Patch | [`tools/oscar64-upstream/patches/main/06-r16-fnptr-compare.patch`](../../tools/oscar64-upstream/patches/main/06-r16-fnptr-compare.patch) |
| Kind | rejects valid C |
| Since | v1.32.273 and main |
| NetHack | Compat #20 (repro r16): `windows.c:113` `win_raw_print == def_raw_print` and `occupation == dig` in `dig.c`. Workaround planned in `port/` (T1.14) if the pin stays on v1.32.273. |
| Reviews | Opus (round 2, ran probes): submit-after-changes, 1 high, 1 medium, 3 low; Codex (read the diff): submit after changes; fix-up: ready; final Codex check: submit after changes |
| Recommendation | **Submit after #1 is merged (the branch is stacked on #1; without it `0 == f` compiles to the wrong answer).** |

## In plain words

NetHack compares function pointers with function names, as in `if (occupation == dig)`. Oscar64 rejected every such comparison as incompatible pointer types. The fix teaches the comparison code that a function name here means a pointer to the function (as assignment already did), and teaches the whole-program optimiser that comparing with a function counts as using its address, so it no longer strips the return value or parameters of a function nobody appears to call, which had been changing the function's type and causing the same error at -O2 and above. The final reviewer's one substantive point was that the test's 'compared and called' function was also assigned to a pointer, which on its own already protected it from the optimiser, so the test did not prove the optimiser part was needed for that pattern. I added a function that is compared and called directly but never assigned or passed; without the optimiser change it fails at -O2/-Os/-O3, with it the whole test passes in all ten configurations, and the complete Oscar64 test suite shows no new failures. The two remaining low findings (the session trailer in the commit and the '#NNN' PR number) are yours to decide, as agreed for all branches.

## The fix

Two-part compiler fix, unchanged this round: (1) InterCodeGenerator.cpp EX_RELATIONAL converts a DT_TYPE_FUNCTION operand to a pointer to the function before the pointer compatibility checks (5 lines); (2) GlobalOptimizer::Analyze EX_RELATIONAL passes both operands to RegisterProc so a function whose address is only compared keeps OPTF_FUNC_VARIABLE and is not retyped by return-value/parameter removal at -O2 and above (3 lines). This round added to the regression test a function that is compared and called directly but never assigned or passed, which isolates part (2) (fails without it at -O2/-Os/-O3), and corrected the commit message's description of the test. Branch rebased (no-op) onto the final r19 commit 5a07baa.

## Regression test

autotest/funcptrcmptest.c (registered in autotest/autotest.bat after nullptrcmptest.c), 202 lines. Covers == and != in both operand orders against a local, a global, a volatile and a struct member function pointer, &f, two function names, *p, casts (including void *), a function type declared through a typedef, use as an if condition, comparison with 0 in both orders, functions with a return value or a parameter whose address is only compared (fc, fd, static fe, ff), a function compared, assigned and called through the pointer (fh), and, new this round, a function compared and called directly but never assigned or passed (fj). Before: 0/10 on 4da3147 and v1.32.273. After: 10/10. Standalone isolating probe kept in scratch: /home/jolyon/nethack64/build/oscar64-wt/r16-fnptr-compare-scratch/final/fj_called_direct_only.c.

## Evidence

*These are the fix-up round's results, for commit `0042d14962d5`. The last round changed the test; its re-validation of the final commit is under "Last round" below.*

**Repro matrix.** Ten configurations each (-ea -g, -bc/-n x none/-O2/-O0/-Os/-O3). Compilers: base = ~/src/oscar64-base (4da3147), pin = v1.32.273, r19 = r19-null-compare worktree (5a07baaf alone), fix = stacked branch 0042d14.
- tools/oscar64-upstream/cases/fnptr_compare_uncalled_function.c: base 0, pin 0, r19 0 (3013 Incompatible pointer types), fix 10.
- cases/fnptr_var_compare_function.c: base 0, pin 0, r19 0, fix 10.
- tests/oscar64-repros/r16_fnptr_compare_function.c: 0/10 on all four (separate struct member function pointer declarator bug, branch fix/fnptr-member: 3012 'Cannot assign incompatible types w != void(*)(const u8*)' on base/r19/fix, 3013 on pinned).
- tests/oscar64-repros/r19_global_null_pointer_compare.c: base 4, pin 4 (wrong at -O2/-Os/-O3), r19 10, fix 10.
- Review probes n01, n03, n04, n09 (zero on left of function name): base/pin/r19 0/10 (3013 'Not a numeric or pointer type'), fix 10/10.
- All 79 review probes in review/p with fix (full list in /home/jolyon/nethack64/build/oscar64-wt/r16-fnptr-compare-scratch/fixup2/probes-fix.txt): 10/10 for example.c, g01-g03, k01, k02, m01, n01-n06, n08-n13, o01, o02, v01, v01d, v03-v12, v13c, v13e, v13f, v14, w01-w03, c03-c06, c08. Rejected 10/10 as intended: i01-i15 (invalid). Pre-existing, identical on base and pinned: l01 (function as condition, 3012), n07 (0 != "abc", 3013), k03 (3012), v01b/v01c 4/10 (3018 at O2+), v02 family (v02b 7/10, v02c 0/10, v02d 3/10 fix vs 0/10 base), v13/v13b/v13g 8/10 (identical-body merge at -bc/-n; v13 and v13g are 0/10 on base because they did not compile), v13d 9/10 (-bc wrong, base 0/10 did not compile), c01, c02, c07 rejected on all.
- New scratch probes (scratch/fixup2/probes): cx1 *f comparison and cx1b *f assignment: 0/10 on base and fix ('Pointer or array type expected'); cx2 p < q pointer vars: base 10/10; cx2b void* == fn ptr var: base compiles; cx2c p < f: base 3013, fix compiles; cx2d void* == f: base 3013, fix 10/10; cx3 C++ p == 0: base and fix 3012; cx3c C++ nullptr forms: base 0/10, fix 10/10; cx4 compare-only void f(int): base 0, fix 10; cx4b compared and called: base 0, fix 10; cast1 (fop)fa assignment: base 10, fix 10; cast2/cast3/cast4 (casts in comparisons): base 0 (3013), fix 10; cast5 call through cast: 10/10 both.

**Autotest.** make -k -j4 -C /home/jolyon/nethack64/build/oscar64-wt/r16-fnptr-compare/make check > /home/jolyon/nethack64/build/oscar64-wt/r16-fnptr-compare-scratch/autotest-fixup2.log (run after the final rebuild of the stacked branch; sources unchanged since). autotest_diff.py /home/jolyon/nethack64/build/oscar64-wt/autotest-base-4da3147.log autotest-fixup2.log: emulations base 1541, new 1561 (+20 = nullptrcmptest.c and funcptrcmptest.c, ten configurations each); new failures 0; fixed 0; failing in both 0; exit code 0. The testint16mul -bc quirk did not show up (0 differences).

**Corpus.** Two runs, both corpus_diff.py ... -j4, nothing else using bin/oscar64 at the time. (1) Before = ~/src/oscar64-base/bin/oscar64 (4da3147), after = stacked branch, --out scratch/corpus-fixup2: 182 files (160 autotest/*.c,*.cpp including the two new tests, 22 tests/oscar64-repros/*.c) x 5 configurations (n-O0, n-O2, n-Os, n-O3, bc-O2) = 910 attempts; both compile 845; identical 836; different 9: autotest/nullptrcmptest.c in all 5 configurations and oscar64-repros/r19_global_null_pointer_compare.c in n-O2, n-Os, n-O3, bc-O2 (not n-O0, where the folding the r19 commit fixes does not occur) - all 9 are the effect of the underlying r19 commit 5a07baaf, which deliberately changes the code for pointer-vs-0 comparisons; status changed 5: autotest/funcptrcmptest.c error -> ok in all 5 configurations; both fail 60 (910 - 845 - 5). (2) Before = r19 compiler /home/jolyon/nethack64/build/oscar64-wt/r19-null-compare/bin/oscar64, after = stacked branch, --out scratch/corpus-fixup2-vs-r19: 182 x 5 = 910; both compile 845; identical 845; different 0; status changed 5 (same funcptrcmptest.c error -> ok); both fail 60. So this fix on its own changes no program either compiler accepts, byte for byte; the only effect is that funcptrcmptest.c compiles. Samples were not compiled (the reviewer's 67-sample run found only the known splitscreen path-dependence).

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| opus | high | Null pointer constant on the left of a function name (0 != f, 0 == f, 0 != &f) compiles but gives the wrong answer | fixed |
| opus | medium | Parameter declared with function type compared with a function name: wrong code in 7 of 10 configurations | out-of-scope |
| opus | low | Regression test misses the operand orders and spellings most likely to break (zero on left, typedef'd function type, casts) | fixed |
| opus | low | Overlaps the r19 fix in the same EX_RELATIONAL block and the same autotest.bat spot | fixed |
| opus | low | Pre-existing Oscar64 bugs found while probing (typedef type mutated by return removal, identical-body merge, path-dependent splitscreen output, unprototyped pointer, C++ references/overloads) | out-of-scope |
| opus | low | PR text: 'comparison with 0' claim, 10 vs 13 configurations, 179 files wording, private session link, no mention of the r19 overlap; author report wrongly listed const-return replacement among OPTF_FUNC_VARIABLE-gated optimisations | fixed |
| codex | medium | Optimizer fix misses dereferenced function names (p == *f): EX_PREFIX/TK_MUL returns the type, not the declaration | rejected |
| codex | medium | Patch newly accepts invalid C: ordered comparison p < f and void *p == f | rejected |
| codex | low | C++ behaviour affected; f == 0 remains rejected in C++ | out-of-scope |
| codex | low | Regression test weak as a runtime test (statically known values); wants volatile pointer, compared+called function, compare-only void f(int), negative cases, *f cases | fixed |
| codex | low | PR compatibility claims too broad; corpus should be described as attempts with both-fail accounted for | fixed |

<details><summary>Evidence for each finding</summary>

1. **Null pointer constant on the left of a function name (0 != f, 0 == f, 0 != &f) compiles but gives the wrong answer** (fixed)

   Resolved by stacking on r19 5a07baaf. Probes review/p/n01_null_forms.c, n03_zero_left_fn.c, n04_zero_left_fn_eq.c, n09_zero_left_amp_fn.c: base 4da3147 0/10, pinned v1.32.273 0/10 and r19-alone 0/10 (all error 3013 'Not a numeric or pointer type', the form is not accepted without r16), stacked compiler 10/10 each. Added to funcptrcmptest.c: assert(0 != fa); assert(0 != p); assert(!(0 == fa)); assert(0 != &fa). The front-end-only r16 build (52eafe0, review/r16only) fails the new test at -bc/-n/-O0 with 'Emulation result -1' on these asserts, so they guard the dependency; the stacked compiler passes 10/10.

2. **Parameter declared with function type compared with a function name: wrong code in 7 of 10 configurations** (out-of-scope)

   Reproduced: p/v02d_param_fn_only.c base 0/10 and pinned 0/10 (error 3013 at -bc/-n/-O0, 'Emulation result -1' at -O2/-Os/-O3), stacked 3/10 (-bc, -n, -O0 -bc pass; -O0 -n and -O2/-Os/-O3 wrong). Control v02b (call through such a parameter, no comparison) is 7/10 on base, pinned and stacked alike; v02c (copy the parameter into a pointer, compare pointers) is 0/10 on all three. Cause is Parser.cpp parameter adjustment (arrays adjusted to pointers at :1769, function types not), unrelated to this fix. Listed in adjacent_bugs and as a known limitation in the PR.

3. **Regression test misses the operand orders and spellings most likely to break (zero on left, typedef'd function type, casts)** (fixed)

   funcptrcmptest.c now has: zero on the left (4 asserts), a typedef'd function type (typedef int fn_t(void); fn_t fi; fn_t *gt; compared before and after assignment and called), casts ((fop)fa == p, p != (fop)fb, (fop)&fa == p, (void *)fa == (void *)p, (void *)fb != (void *)p), a volatile function pointer, a compare-only void ff(int) with unused parameter, and a compared function that is also called with observed results (fh). Base 0/10, pinned 0/10, r19-alone 0/10 (error 3013 at line 86), stacked 10/10, plus -O2 -xz -Oz/-O2 -Oo/-O2 -Ox 3/3, -Ofp 10/10, -strict 4/4, as C++ with nullptr for 0 10/10. A first draft had a wrong assert ((fop)fa == p while p had been set to fb by the condition block); corrected with p = fa before the cast section.

4. **Overlaps the r19 fix in the same EX_RELATIONAL block and the same autotest.bat spot** (fixed)

   Branch rebased onto 5a07baaf (git rebase --onto). autotest.bat conflict resolved keeping both entries (nullptrcmptest.c first); InterCodeGenerator.cpp merged automatically, both changes present (git diff 5a07baaf HEAD shows only r16's 5 lines). PR text states it builds on the null-comparison PR (#NNN) and must be merged after it. The remark about integration branches is left to the lead as instructed.

5. **Pre-existing Oscar64 bugs found while probing (typedef type mutated by return removal, identical-body merge, path-dependent splitscreen output, unprototyped pointer, C++ references/overloads)** (out-of-scope)

   Confirmed identical on base, pinned and stacked: v01b_typedef_called_ignored.c 4/10 (error 3018 'Function has void return type' at -O2/-Os/-O3); v13b_identical_bodies_ptrs_only.c 8/10 (-bc and -n wrong); k03_unprototyped.c 0/10 (3012); c01_overload.cpp 0/10 (3012); c02_fnref.cpp 0/10 (3015). Not caused by this fix; listed in adjacent_bugs. The splitscreen path-dependence was not re-run here (corpus_diff does not compile samples); reported as the reviewer found it.

6. **PR text: 'comparison with 0' claim, 10 vs 13 configurations, 179 files wording, private session link, no mention of the r19 overlap; author report wrongly listed const-return replacement among OPTF_FUNC_VARIABLE-gated optimisations** (fixed)

   PR body rewritten: comparison with 0 in both orders is now true and tested; the three extra autotest.bat configurations, -Ofp, -strict and C++ are reported; corpus described as 160 autotest programs and 22 small reproducers from our project; session link removed; dependency on the null-comparison PR stated. Checked GlobalOptimizer.cpp: CheckConstReturns is not gated by OPTF_FUNC_VARIABLE; the gated ones are return-value removal, reference-return demotion, unused-parameter removal, reference-to-value parameters and constant-parameter replacement; the risks text says so.

7. **Optimizer fix misses dereferenced function names (p == *f): EX_PREFIX/TK_MUL returns the type, not the declaration** (rejected)

   Not reachable. The parser rejects * applied to a function designator before any of this code runs: probes/cx1_deref_cmp.c (p != *f, *f != p, p != *&f) and cx1b_deref_assign.c (p = *f, no comparison) both give error 3013 'Pointer or array type expected' in 10/10 configurations on base and on the stacked compiler. So the GlobalOptimizer never sees a relational operand of this shape, and the registration gap cannot produce wrong code. The rejection of *f is a pre-existing limitation (adjacent_bugs). The test's existing *p == fa case (dereferencing a pointer variable) compiles and passes; p == *f cases cannot be added because they do not compile.

8. **Patch newly accepts invalid C: ordered comparison p < f and void *p == f** (rejected)

   These are the function-name spellings of forms Oscar64 already accepts for pointer variables: cx2_order_vars.c (int (*p)(void), (*q)(void); p < q) compiles and runs 10/10 on base 4da3147; cx2b_voidp_var.c (void *v == function pointer variable) compiles 10/10 on base. The fix makes the function designator behave exactly like a pointer variable of the same type, which is what C requires of the conversion; the permissive ordering/void* checks are pre-existing extension behaviour, unchanged, and now stated as a known limitation in the PR. The 15 invalid programs i01-i15 (mismatched return/parameter types, int, float, object pointer, struct, etc.) are still rejected 10/10 with the stacked compiler, with both types named in the message.

9. **C++ behaviour affected; f == 0 remains rejected in C++** (out-of-scope)

   Pre-existing C++ design: literal 0 against any pointer is rejected under COPT_CPLUSPLUS. cx3_cpp_var_zero.cpp (plain function pointer variable p == 0) gives 'Cannot compare integer and pointer' 10/10 on base and stacked; cx3b (f == 0) is rejected on both (message changes from 'Not a numeric or pointer type' to 'Cannot compare integer and pointer'). nullptr forms work: cx3c (f == nullptr, p != f, nullptr == p) base 0/10, stacked 10/10; p/c05_nullptr.cpp, c03, c04, c06, c08 10/10. The full test compiled as C++ with nullptr in place of 0 passes 10/10; PR says so and names the 0 limitation.

10. **Regression test weak as a runtime test (statically known values); wants volatile pointer, compared+called function, compare-only void f(int), negative cases, *f cases** (fixed)

   Added volatile fop vp (read and written, compared both orders), int fh(int) compared and called (fh(4) == 12, gr(5) == 15 through the pointer), compare-only void ff(int) against a null void (*gs)(int). Negative cases cannot live in autotest (they must fail to compile); checked as scratch probes p/i01-i15, all rejected 10/10 with the final compiler. *f cases cannot be added (do not compile, see above). The GlobalAnalyzer-unchanged concern: test passes with -Ofp (function-set mode) in all 10 configurations and with -O2 -Oo/-Ox/-xz -Oz.

11. **PR compatibility claims too broad; corpus should be described as attempts with both-fail accounted for** (fixed)

   PR now says: 910 attempts (182 files x 5), 845 accepted by both and byte-identical, 5 status changes (the new test), 60 fail on both; relative to 4da3147 the 9 differing outputs are all nullptrcmptest.c and the r19 reproducer, i.e. the null-comparison commit's own effect (845/845 identical against the r19 compiler). The RegisterProc sentence now says only that it does nothing for a non-function operand, and the code-growth qualification for compared functions is in the PR body. The earlier report's 895 - 830 - 5 = 60 both-fail is the same set.

</details>

## Last round: final-check findings and what happened to them

Changed in the last round: test. Commit before it: `0042d14962d5`.

| From | Severity | Finding | Resolution |
|---|---|---|---|
| final-check.md / Codex #1 | medium | PR text and test: 'compared function that is also called' (fh) is also assigned to gr, so it does not isolate the compared-and-directly-called case | fixed |
| final-check.md / Codex #2 | low | Commit message keeps the Claude-Session trailer | left-for-jolyon |
| final-check.md / Codex #3 | low | PR text '#NNN' placeholder; PR base must present only this commit's changes | left-for-jolyon |
| self-check | low | Rebase onto the final r19 commit | fixed |

<details><summary>Evidence, and what was re-run</summary>

1. **PR text and test: 'compared function that is also called' (fh) is also assigned to gr, so it does not isolate the compared-and-directly-called case** (fixed)

   Correct: `gr = fh` already triggers RegisterProc through EX_ASSIGNMENT, so fh never exercised the new EX_RELATIONAL registration on its own. Added `int fj(int x)` to autotest/funcptrcmptest.c: compared with gr in both orders and called directly with its result checked (`assert(fj(2) == 10)`), never assigned or passed; fh kept, its comment now says 'compared, assigned and called through the pointer'. Isolating probe /home/jolyon/nethack64/build/oscar64-wt/r16-fnptr-compare-scratch/final/fj_called_direct_only.c in the ten configurations: 4da3147 0/10 (error 3013), pinned v1.32.273 0/10, front-end-only r16 build 4/10 (fails -O2/-Os/-O3 both back ends with `'i16(*)(i16)' != 'void(*)(i16)'`), fixed 10/10. At -O2 the direct call is inlined (no `jsr fj` in main's .asm; standalone `fj: ; fj(i16)->i16` emitted), so only the comparison keeps the function's type; the test comment says so. Updated test: base 0/10, pinned 0/10, front-end-only 0/10, fixed 10/10 (results in scratch/final/test-final.txt, probe-fj.txt). Commit message's test paragraph extended accordingly.

2. **Commit message keeps the Claude-Session trailer** (left-for-jolyon)

   Per the round's rules the trailer lines (Co-Authored-By, Claude-Session) are unchanged; Jolyon decides them for all branches at once. The PR body below carries no claude.ai link.

3. **PR text '#NNN' placeholder; PR base must present only this commit's changes** (left-for-jolyon)

   The '#NNN' placeholder stays as instructed until the null-comparison PR exists. The branch is intentionally stacked: 4da3147 -> 5a07baa (r19) -> 97d649d (this fix), two commits, as the round requires. Until the r19 PR is merged upstream, a PR from this branch against main will show both commits; the PR body says so. If Jolyon wants a single-commit PR he would open it after r19 merges (or set the r19 branch as base).

4. **Rebase onto the final r19 commit** (fixed)

   `git rebase --onto 5a07baaf667257473e2f01f4f3e8ca0a825fb5f3 HEAD~1` reported 'Current branch fix/r16-fnptr-compare is up to date': HEAD~1 already was 5a07baa. `git rev-list --count 4da3147..HEAD` = 2; working tree clean; `git diff 0042d14 HEAD -- oscar64/` is empty (no compiler source change this round).

**Re-validation.** Test-only change (autotest/funcptrcmptest.c +16/-2; oscar64/*.cpp identical to the reviewed commit 0042d14, verified with git diff). Compiler binary was up to date before the round (make -n compiler: nothing to compile) and was relinked by make check. Ten configurations (oscar64 -ea -g {-bc|-n} x {none,-O2,-O0,-Os,-O3}): updated funcptrcmptest.c: 4da3147 0/10 (error 3013 'Incompatible pointer types' at line 94), pinned v1.32.273 0/10, front-end-only r16 build 0/10 (-O2/-Os/-O3: error 3013 'i16(*)()' != 'void(*)()'; default/-O0: Emulation result -1 from the 0 == f asserts that need r19), fixed 10/10 (also 10/10 after the make-check relink). Isolating probe fj_called_direct_only.c: base 0/10, pinned 0/10, front-end-only 4/10, fixed 10/10. Recheck of review probes with the final binary: i01_ret_mismatch, i03_param_sign, i07_int_nonzero still rejected 10/10 (3013 with both types named / 3012 'Cannot compare integer and pointer'); n03_zero_left_fn, v01d_typedef_cmp_only, example.c pass 10/10. Full autotest: make -k -j4 -C .../r16-fnptr-compare/make check > .../r16-fnptr-compare-scratch/autotest-final.log; autotest_diff.py vs autotest-base-4da3147.log: emulations base 1541, new 1561 (+10 nullptrcmptest.c from r19, +10 funcptrcmptest.c), new failures 0, fixed 0, failing in both 0, exit 0. Corpus not rerun (no compiler change); the fix-up round's run on identical compiler sources stands: 182 files x 5 configurations, vs the r19-only compiler 845/845 identical, status changes only funcptrcmptest.c error -> ok in all five; vs 4da3147 845 both compile, 836 identical, the 9 differences all in autotest/nullptrcmptest.c and r19_global_null_pointer_compare.c (the stacked null-comparison fix).

</details>

## Final check (Codex, read-only, on the final commit)

<details><summary>SUBMIT AFTER CHANGES</summary>

VERDICT: SUBMIT AFTER CHANGES

1. **Medium — PR text: “a compared function that is also called.”** The `fh` test also assigns `fh` to `gr`, which already triggers `RegisterProc` without this patch. It therefore does not isolate the compared-and-directly-called case cited in the optimizer risk assessment. Add a separate function that is compared and directly called with its result checked, but never assigned or passed as a pointer. Keep `fh` for indirect-call coverage.

2. **Low — Commit message: `Claude-Session: https://claude.ai/code/session_…`.** The private session link was removed from the PR body but remains in the commit being submitted. Remove that trailer; retain the AI-assistance disclosure and coauthor attribution as intended.

3. **Low — PR text: “null-comparison PR (#NNN).”** Replace the placeholder with the actual upstream PR reference before submission, and ensure the PR’s selected base presents only this commit’s changes.

The supplied diff and reported probes support the two-part fix. The earlier rejected findings are convincingly explained as pre-existing limitations or existing pointer-comparison policy. I found no additional concrete correctness defect in the supplied code; execution results are taken from your evidence, not independently reproduced.

</details>

## Before submitting

- Fill in the number of the null-comparison PR (#1) for "#NNN", and open this PR only after #1 is merged (or as a stacked PR that says so).
- Done 2026-11-12 (Jolyon's decision): the commit ends with one `Co-Authored-By: Claude <noreply@anthropic.com>` line and no session link (message only; the tree is the one validated, commit `97d649deddae` before), and the PR text ends with the same AI-assistance sentence as every other PR.

## Risks and limitations

Unchanged from the fix-up round: a function whose address is compared is treated like an assigned or passed one in the GlobalOptimizer and forgoes the optimisations gated by OPTF_FUNC_VARIABLE (return-value removal, unused/constant parameter removal, reference demotions) even if it is also called directly; semantically correct since its address is observable, and no program in the corpus other than the new test changed by a byte. The GlobalAnalyzer's EX_RELATIONAL case is deliberately untouched (its flag governs inlining and calling convention for functions callable through a pointer; a bare comparison does not make a function callable). Pre-existing, out of scope, documented by the reviews: function-typed parameters are not adjusted to pointers (Parser.cpp), identical-body functions merge at -O1 so distinct trivial callbacks can compare equal, typedef-shared function types are mutated by return-value removal. Submission mechanics: the branch is stacked on the r19 null-comparison fix (0 == f depends on it); a PR against main before r19 merges shows both commits, and the '#NNN' reference and the commit trailers are Jolyon's to settle.

## Related bugs found, not fixed here

All reproduced identically with 4da3147 and v1.32.273 unless noted; probes under /home/jolyon/nethack64/build/oscar64-wt/r16-fnptr-compare-review/p (p/) or /home/jolyon/nethack64/build/oscar64-wt/r16-fnptr-compare-scratch/fixup2/probes (probes/).
1. Parameter declared with function type not adjusted to pointer (Parser.cpp ~1769 adjusts arrays only): p/v02d_param_fn_only.c (compare) 0/10 both; p/v02b_param_fn_call.c (call) 7/10 both (-n, -O0 -n, -Os -n wrong); p/v02c_param_fn_assign.c 0/10 both. With this fix v02d becomes 3/10.
2. GlobalOptimizer.cpp:986 func->mBase->mBase = TheVoidTypeDeclaration mutates a function type shared through a typedef: p/v01b_typedef_called_ignored.c 4/10 both, error 3018 at -O2/-Os/-O3.
3. Functions with identical bodies merged at the default level so distinct functions' addresses compare equal: p/v13b_identical_bodies_ptrs_only.c 8/10 both (-bc, -n wrong); with this fix the function-name spelling p/v13d_ptr_vs_other_name.c is 9/10 (-bc wrong) and p/v13g_codes.c 8/10.
4. * applied to a function designator rejected 'Pointer or array type expected' (valid C): probes/cx1_deref_cmp.c, probes/cx1b_deref_assign.c 0/10 both (also stacked).
5. Function designator in a condition / logical operand rejected 'Not a valid condition value': p/l01_logical.c 0/10 both.
6. Integer constant 0 on the left of an array or string literal rejected 'Not a numeric or pointer type': p/n07_zero_left_string.c 0/10 on both and on the stacked branch (r19 covers pointers, not arrays).
7. Unprototyped int (*p)() not compatible with int f(int) for assignment or comparison: p/k03_unprototyped.c 0/10 both.
8. Ordered comparison of function pointers and comparison of void * with a function pointer accepted without diagnostic (C requires one): probes/cx2_order_vars.c, probes/cx2b_voidp_var.c compile on both.
9. C++: literal 0 rejected against any pointer ('Cannot compare integer and pointer'), probes/cx3_cpp_var_zero.cpp 0/10 both (nullptr works) - may be intentional upstream; function references (p/c02_fnref.cpp, 3015) and overload selection by target type (p/c01_overload.cpp, 3012) rejected; pointer-to-member-function declarator int (A::*pm)(void) parse error 3006 (p/c07_member_fnptr.cpp) - all both.
10. Reported by the Opus reviewer, not re-run here: samples/hires/splitscreen.c -bc -O2 output depends on the compiler's install path / alternates between two outputs from the same binary (4da3147).

## Draft pull request

**Title:** Fix comparison of function pointer with function name

````markdown
Comparing a function pointer with a function name is rejected with "Incompatible pointer types":

```c
#include <assert.h>

int (*occupation)(void);
static int dig(void);

int is_digging(void)
{
	return occupation == dig;
}

static int dig(void)
{
	return 0;
}

int main(void)
{
	assert(!is_digging());
	return 0;
}
```

Reproduce with `oscar64 -ea -n -O2 example.c` (also with `-bc`, and at every optimisation level):

```
example.c(8, 20) : error 3013: Incompatible pointer types
```

Expected: the program compiles and the emulation returns 0. C89 3.3.9 allows `==` and `!=` on pointers to compatible types, and a function designator converts to a pointer to the function, so `p == f`, `p != &f` and `f == p` are all valid (`&f` fails the same way because the parser folds it back to `f`). The same comparison against another pointer variable, or against 0, already compiled. The pattern comes from NetHack 3.4.3 (`windows.c`: `windowprocs.win_raw_print == def_raw_print`, `dig.c`: `occupation == dig`). v1.32.273 and current main (4da3147) behave the same.

Two things cause it:

1. `InterCodeGenerator::TranslateExpression`, case `EX_RELATIONAL`: the function operand keeps its `DT_TYPE_FUNCTION` type and reaches the final `else` of the pointer branch, which reports error 3013 without naming the types. Assignment, argument passing and `return` already convert a function to a pointer to it (their `DT_TYPE_ARRAY || DT_TYPE_FUNCTION` cases). The relational case now does the same after both operands are dereferenced (`BuildPointer`; the temp already holds the address), so the existing checks apply unchanged: compatible function types compare, incompatible ones still report error 3013 (now with both types named), and `f == 1` still reports "Cannot compare integer and pointer".

2. With `-O2`, `-Os` or `-O3` the error remained when the function is only compared, never called or assigned in the program (the example above). `GlobalOptimizer::Analyze`, case `EX_RELATIONAL`, did not pass its operands to `RegisterProc`, unlike assignment, call arguments, `return`, comma and `?:`. The function therefore never got `OPTF_FUNC_VARIABLE`, and `GlobalOptimizer::Optimize` removed its unused return value (and unused parameters), turning `int dig(void)` into `void dig(void)`: `Incompatible pointer types 'i16(*)()' != 'void(*)()'`. The same happens to a function that is compared and called directly once the call is inlined. The relational case now registers both operands, so a compared function keeps its type. `RegisterProc` ignores anything that is not a function constant, so other comparisons are untouched.

This builds on the null pointer constant comparison fix (#NNN): with the function operand converted to a pointer, `0 == f` takes the same path as `0 == &x` and needs the 0 emitted as a null pointer constant. The branch is stacked on that commit, so the PR shows both until that one is merged; this fix is the second commit.

The new autotest `funcptrcmptest.c` (registered in `autotest.bat`, picked up by the makefile) covers `==` and `!=` in both operand orders against a local, a global, a volatile and a struct member function pointer, `&f`, two function names, `*p`, casts, a function type declared through a typedef, use as a condition, comparison with 0 in both orders, functions with a return value or a parameter whose address is only compared, and a function that is compared and called directly but never assigned or passed.

Validation against main `4da3147` on Linux, C64 target, ten configurations (`-ea -g`, `-bc` and `-n`, default/`-O0`/`-O2`/`-Os`/`-O3`):

- New regression test: before 0/10 (error 3013 in all). With only the front-end change (1), `-O2`/`-Os`/`-O3` still fail with `'i16(*)()' != 'void(*)()'`. With both changes, on top of the null-comparison fix: 10/10. A reduced probe with a single function that is compared and called directly (never assigned) goes 0/10 before, 4/10 with (1) alone (`'i16(*)(i16)' != 'void(*)(i16)'` at `-O2`/`-Os`/`-O3`), 10/10 with both.
- Incompatible function types (different return type, parameter signedness, count or qualifiers, variadic vs not) and `f == 1` are still rejected in all ten configurations, with both types named.
- Full autotest (`make -k check`): 1541 successful emulations on the baseline, 1561 with the null-comparison fix and this patch (ten configurations of each new test), no new failures.
- 182 autotest, sample-sized and external test programs compiled with both builds in five configurations (`-n -O0/-O2/-Os/-O3`, `-bc -O2`): against the null-comparison fix alone, all 845 programs both builds accept are byte-identical and the only status change is the new test going from error to ok; against plain 4da3147 the only differences are in the null-comparison fix's own test and probe.

Found while porting NetHack 3.4.3 to the C64. Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described.
````
