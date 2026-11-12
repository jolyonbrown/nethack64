# 03. Fix merging of identical functions whose address is taken

| | |
|---|---|
| Branch | `fix/dropped-init-fn` in `~/src/oscar64-dev`, commit `904c0400f093`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/03-dropped-init-fn.patch`](../../tools/oscar64-upstream/patches/main/03-dropped-init-fn.patch) |
| Kind | wrong code (silent) |
| Since | Linker::CombineSameConst since 3a9cd85 (2023-08); on v1.32.273 and main |
| NetHack | Two different functions with identical machine code get one address when the program stores their addresses, so pointers to them compare equal. NetHack keeps function pointers in tables (`cmdlist[]`, `windowprocs`) and compares them (`occupation == dig`, `win_raw_print == def_raw_print`). Not reduced to a nethack64 repro yet; exposure not counted. Part of the proposed patched pin. |
| Reviews | Opus (round 2, ran probes): submit-after-changes, 0 high, 2 medium, 1 low; Codex (read the diff): submit after changes; fix-up: ready; final Codex check: submit |
| Recommendation | **Submit.** |

## In plain words

Oscar64's linker saves space by keeping only one copy of any two "constant" objects with identical bytes, and it treated function bodies as constants, so two small functions that happened to compile to the same code were silently fused even when the program stored their addresses: pointers to different functions compared equal and tables like NetHack's window-procs held the same entry twice. The fix tells the linker which functions have their address used as a value (the compiler already tracked this) and keeps those out of the merge, while functions that are only ever called are merged as before. The reviews found two more holes that the first version missed: a function whose address was only turned into a plain number (the C64 way of installing an interrupt vector) was never marked as address-taken at all, which also gave it the wrong calling convention when called through that number, and a function consisting of a single jump to another function could be glued onto its target at the same address; both are now closed with one extra line each, and the test was rewritten so that every check really runs at every optimisation level and fails on the unfixed compiler in all ten configurations. Everything else we compiled came out byte-for-byte identical except for the test, one artificial autotest full of identical stubs that grew by about 460 bytes, and one sample whose output was shown to depend on the compiler's memory layout even before this change. What could still go wrong: programs with many identical address-taken functions get slightly bigger, identical constant data tables are still merged (left out on purpose and said so in the PR), and the maintainer may prefer his own variant of the fix, which is how he has treated earlier PRs.

## The fix

Final diff (9 insertions, 3 deletions in oscar64/): Linker.h adds LOBJF_FUNC_VARIABLE (0x10000000); InterCodeGenerator::TranslateProcedure sets it on proc->mLinkerObject where DTF_FUNC_VARIABLE is copied to mFuncVariable; Linker::CombineSameConst excludes flagged objects from both sides of a match; GlobalAnalyzer::Analyze case EX_TYPECAST now calls RegisterProc(ldec) so functions used only through integer casts are flagged (also fixes their fastcall/indirect-call layout mismatch); Linker::Forwards no longer appends a flagged object that is a bare 3-byte JMP to its target. The two extensions are the Opus reviewer's, verified independently and adopted unchanged in substance. Branch is one commit (904c040) on 4da3147, amended with --no-gpg-sign, trailers kept. Files: /home/jolyon/nethack64/build/oscar64-wt/dropped-init-fn/oscar64/{Linker.h,Linker.cpp,GlobalAnalyzer.cpp,InterCodeGenerator.cpp}, autotest/funcptrmergetest.c, autotest/autotest.bat.

## Regression test

/home/jolyon/nethack64/build/oscar64-wt/dropped-init-fn/autotest/funcptrmergetest.c (90 lines, registered in autotest.bat). Groups: volatile global 'gp = fa' vs local fb (dead-store identical bodies; seen never read); run-time indexed table and struct via volatile pointer with identity checks tab[i]==wp->init and tab[i+1]==g (g = gb) plus calls (count==4); ja/jb used only as (unsigned) with a call through the integer (count==5); __noinline ha / hb (bare tail call) through a volatile pointer table (count==6); __noinline k called directly with 5 and indirectly through (ifn)(unsigned)k with 7. Results, 10 configurations -ea -g {-bc|-n} x {default,-O2,-O0,-Os,-O3}: 4da3147 0/10 pass, v1.32.273 2/10 (-O0 only), fix 10/10. Per group on 4da3147: A 2/10, B 2/10, C 2/10, D 7/10, E 0/10; each 10/10 after. Host sanity: gcc -std=c99 -pedantic -Wall of a copy with unsigned long compiles and passes. Negative probes (must not compile, cannot live in autotest): i01 invalid initializer and i02 assignment to a function give identical errors before and after; i01 at -O2 is accepted by both 4da3147 and v1.32.273 (pre-existing, listed under adjacent bugs). All 10 funcptrmergetest emulations in autotest-fixup2.log return 0 (the log has 1551 'Emulation result 0' lines and no non-zero result).

## Evidence

**Repro matrix.** Pass counts out of 10 (-ea -g {-bc|-n} x {default,-O2,-O0,-Os,-O3}), BEFORE 4da3147 / PINNED v1.32.273 / fix-only 249a4a1 / FINAL 904c040. cases/fn_only_in_global_initializer.c 8/8/10/10 (fails -bc and -n default before). funcptrmergetest.c (final) 0/2/-/10. r16 v13b 8/8/10/10. Opus probes fixed by the original part: p03,p04,p05,p06,p08,p10,p12,p13,p14,p16,p19,p21,p22,v01,c01 2/2/10/10; p07,p11 6/6/10/10. Integer-cast group: p02 2/6/2/10, p20 2/2/2/10, p25 2/2/2/10, p24 6/6/6/10, p26 0/4/0/10. Tail call p29 7/7/7/10. Codex example 1 (with 'volatile F') 9/9/-/10; codex example 3 size 154 -> 155 bytes. Substitution probe x04 2/2/-/10. Unchanged (pre-existing): p27 2/2/2/2; p17, p28, p15, x05 10/10/10/10; c04, c05 4/4/4/4; p09, p18, p23 rejected by all. -v2 on the new test at -n -O2 before: Match fb:fa, gb:ga, gb:ja, gb:jb, gb:ha, Direct hb -> gb; after: none for user functions. Scratch: /home/jolyon/nethack64/build/oscar64-wt/dropped-init-fn-scratch/matrix.sh, p/, v/ (per-group variants), probes-bulk.txt.

**Autotest.** make -k -j4 -C /home/jolyon/nethack64/build/oscar64-wt/dropped-init-fn/make check > /home/jolyon/nethack64/build/oscar64-wt/dropped-init-fn-scratch/autotest-fixup2.log (run after the final source and test, binary relinked by make check at 06:59). autotest_diff.py autotest-base-4da3147.log autotest-fixup2.log: emulations base 1541, new 1551; new failures 0; fixed 0; failing in both 0. No non-zero 'Emulation result' in the log. corpus_diff was started only after make check finished.

**Corpus.** corpus_diff.py ~/src/oscar64-base/bin/oscar64 <wt>/bin/oscar64 --out <scratch>/corpus-fixup2 -j4: 181 files (159 autotest programs incl. the new test, 22 tests/oscar64-repros) x 5 configurations = 905 pairs; both compile 845; identical 836; different 9; both fail 60 (the 12 reproducers 4da3147 rejects, all 5 configs); status changed 0. Differences: autotest/funcptrmergetest.c n-O2 662->734, n-Os 756->829, n-O0 934->943 (the -O0 one is k's calling convention), n-O3 634->698, bc-O2 1609->1755 (new test, expected); autotest/funcvaropt.c n-O2 3070->3530, n-Os 3313->3772, n-O3 3064->3523, bc-O2 2981->3939; -v2 shows 60 merges before and 22 after, no casts in that file, so the typecast change did not add to the author's numbers; funcvaropt passes in autotest. Samples run (--src samples/*/, <scratch>/corpus-samples2): 146 files x 5 = 730 pairs; both compile 333; identical 332; different 1; status changed 0. The one difference, hires/splitscreen.c bc-O2 (14399 vs 14469 bytes, nformf's bytecode differs in size), is a pre-existing heap-layout dependence of the compiler, not the fix: with MALLOC_PERTURB_=85 both compilers give 7db37006/14471, with MALLOC_TOP_PAD_=4000000 or MALLOC_MMAP_THRESHOLD_=1024 both give 2e9b65be/14451 (the same output -v/-v2 produce for both), and only the default layout separates them (f36fd674 vs 06ed79b4, stable across cwd, env size and taskset -c 0); v1.32.273 also changes output under MALLOC_PERTURB_. Opus's two private builds give my binary's variant. tsr.c with its own flags (-n -dNOFLOAT -dNOLONG), which does (unsigned)tsr, is byte-identical (1615 bytes).

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| opus | medium | Function whose address is used only through an integer cast is not flagged and is still merged | fixed |
| opus | medium | Bare tail call: Linker::Forwards places an address-taken JMP-only function at its target's address | fixed |
| opus | low | Distinct named const objects with identical contents are merged and compare equal (p27) | out-of-scope |
| opus | low | PR text: 'front end already records those functions' overstated; 'merged exactly as before'; 'only stops being folded into' contradiction; '20 external repro files' | fixed |
| opus | low | Commit trailer names Claude Fable 5.1 rather than the string the earlier task asked for | rejected |
| codex | medium | Completeness of DTF_FUNC_VARIABLE coverage unestablished (return/argument/&f example) | fixed |
| codex | medium | Regression test does not force the identity checks to survive optimisation; count==4 cannot detect ga/gb substitution | fixed |
| codex | low | Size can grow in programs that never compare addresses; 'ordinary programs see no size change' unsupported | fixed |
| codex | low | Validation accounting mixes corpora and accepted inputs | fixed |
| codex | low | Test uses C99 syntax (declaration after statement); C++ paths not validated | rejected |
| other-review | medium | r16 reviewer's v13b: identical bodies, pointers compare equal at the default level | fixed |

<details><summary>Evidence for each finding</summary>

1. **Function whose address is used only through an integer cast is not flagged and is still merged** (fixed)

   Reproduced with the fix-only binary (249a4a1): p02_cast_to_uint 2/10, p20 2/10, p25 2/10, p24 6/10, p26 0/10, identical to 4da3147 (v1.32.273: p02 6/10, p26 4/10). Cause confirmed in GlobalAnalyzer::Analyze case EX_TYPECAST, which never calls RegisterProc; Expression::ConstantFold folds pointer casts of a function back to EX_CONSTANT but leaves integer casts. Adopted the one-line RegisterProc(ldec) from review-extension.patch after checking it is a no-op unless the operand is DT_CONST_FUNCTION (Analyze returns mDecValue for EX_CONSTANT, a variable decl otherwise). After: p02, p20, p24, p25, p26 all 10/10. p26's -O0 failure is a fastcall layout mismatch (k takes its parameter in A/X while the indirect call pushes it on the stack; seen in the -O0 asm), also cured by the flag. A new test group (ja/jb used only as integers, and k) covers it.

2. **Bare tail call: Linker::Forwards places an address-taken JMP-only function at its target's address** (fixed)

   p29_tailcall_alias fails at -n -O2/-Os/-O3 (7/10) on 4da3147, v1.32.273 and the fix-only binary; -v2 shows 'Direct fb -> fa' and the map gives fb size 0 at fa's address. Adopted the Forwards guard !(pobj->mSize == 3 && (pobj->mFlags & LOBJF_FUNC_VARIABLE)): only a flagged object that is nothing but the JMP can alias, and the flag is never set in programs that take no function addresses, so their output cannot change. After: p29 10/10; test group D (ha/hb through a volatile pointer table) fails 3/10 before, passes 10/10 after. -v2 on the new test before shows 'Direct hb -> gb'; after, no Direct line for user functions.

3. **Distinct named const objects with identical contents are merged and compare equal (p27)** (out-of-scope)

   p27_const_data 2/10 (passes only -O0) on 4da3147, v1.32.273 and the final fix, 'Match ca : cb' with -v2. Same pass, data side; deliberately not changed. The PR now says so explicitly instead of implying const merging is fine.

4. **PR text: 'front end already records those functions' overstated; 'merged exactly as before'; 'only stops being folded into' contradiction; '20 external repro files'** (fixed)

   All reworded. With the EX_TYPECAST change the front end claim is now true for integer casts, and the PR describes the previous gap. 'Exactly' dropped and the pstruct_a_set : pstruct_d_set case (a called-only pair that loses its merge because its bodies reference address-taken functions) is described as correct behaviour. Both sides of the match are now described consistently. Repro files are described as '22 small reproducers from our project', with the 12 rejected by main stated.

5. **Commit trailer names Claude Fable 5.1 rather than the string the earlier task asked for** (rejected)

   The trailer is the model that did the work; this task says to keep the existing trailer lines as they are, so they were kept. No claude.ai link appears in the PR body.

6. **Completeness of DTF_FUNC_VARIABLE coverage unestablished (return/argument/&f example)** (fixed)

   Codex's example as written fails to parse on all three compilers ('F volatile p' is a pre-existing parser limitation, error 3006); with 'volatile F' it fails on 4da3147 and v1.32.273 at -bc default (9/10, -v2 'Match a : b') and passes 10/10 with the fix, so return and argument paths are covered. Audit of RegisterProc call sites (initialisers, assignments, arguments, returns, EX_CONSTANT DT_CONST_POINTER for &f, and now EX_TYPECAST) found exactly one gap, integer casts, which is the Opus finding above and is fixed. GlobalAnalyzer runs before TranslateProcedure (procedure linker objects are created there), and the new bit is only read in CombineSameConst, Forwards and the exact-flags compare in IsSameConst (LOT_DATA only).

7. **Regression test does not force the identity checks to survive optimisation; count==4 cannot detect ga/gb substitution** (fixed)

   gp is now 'volatile fop' and wp 'struct procs * volatile'; added assert(tab[i + 1] == g) with g = gb to detect substitution. Each group was compiled on its own against 4da3147: A (volatile gp) fails 8/10, B (table/struct) 8/10, C (integer casts) 8/10, D (tail call) 3/10, E (k direct+indirect) 10/10; the full test fails 10/10 on 4da3147 (8/10 on v1.32.273) and passes 10/10 with the fix. A first draft that read 'seen' made fa/fb non-identical and silently turned group C into a non-test; caught by the per-group run and corrected (seen is never read).

8. **Size can grow in programs that never compare addresses; 'ordinary programs see no size change' unsupported** (fixed)

   Codex's two-stub example grows from 154 to 155 bytes (-n -Os and -n -O2) with the fix. PR now states only observed numbers (samples byte-identical except one explained case, funcvaropt +459/460 native, +958 bytecode) and names the growth as a known limitation.

9. **Validation accounting mixes corpora and accepted inputs** (fixed)

   Re-run from scratch: 159 autotest programs + 22 reproducers = 181 files x 5 = 905 pairs; 845 both compile, 836 identical, 9 different, 60 both fail (12 reproducers x 5). Samples reported separately: 146 files, 333 both compile, 332 identical, 1 explained. Stated as such in the PR.

10. **Test uses C99 syntax (declaration after statement); C++ paths not validated** (rejected)

   autotest is compiled only by oscar64, which accepts mixed declarations, and many existing autotests do the same. C++: c01 (static members) 2/10 -> 10/10; c02 goes 2/10 -> 4/10 where the remaining failures are the pre-existing virtual-call-through-base-array bug (c04/c05 fail identically at -O2+ on 4da3147, v1.32.273 and the fix). The PR claims nothing about C++ beyond the unchanged virtual exclusion.

11. **r16 reviewer's v13b: identical bodies, pointers compare equal at the default level** (fixed)

   /home/jolyon/nethack64/build/oscar64-wt/r16-fnptr-compare-review/p/v13b_identical_bodies_ptrs_only.c: 4da3147 and v1.32.273 8/10 (fail at -bc and -n default; -O2+ pass by folding), fix 10/10. Same bug (CombineSameConst), covered by the original part of the fix; included in validation.

</details>

## Final check (Codex, read-only, on the final commit)

<details><summary>SUBMIT</summary>

VERDICT: SUBMIT

No findings. The diff addresses the reported merge, integer-cast, and bare-tail-call failures. The regression test forces runtime identity checks, and the supplied baseline/patched results support its effectiveness. Earlier findings are adequately resolved or explicitly scoped out; no blocking overclaims remain.

</details>

## Before submitting

- Make the AI-assistance line the same in every PR body (some end with a sentence, some with a "Generated with Claude Code" footer), as Jolyon decides.
- Commit trailers: drop the `Claude-Session:` line and use one `Co-Authored-By:` line, as Jolyon decides for all PRs (see OSCAR64-UPSTREAM.md).

## Risks and limitations

Programs storing addresses of several byte-identical functions keep one copy per function (two-stub example +1 byte; funcvaropt +459/+958); a '(void)f;' statement or any other cast of a function designator now marks f as a function variable, which also disables const-parameter propagation and may change its fastcall layout for that function (correct, slightly larger code). The Forwards guard only affects flagged 3-byte objects, so programs without function-address uses are unaffected by construction. Not covered: C++ virtual functions (RegisterProc excludes them as before), named const data merging (out of scope), targets other than the C64 .prg default, -Oo/-Ox/-xz combinations beyond autotest.bat, real hardware. The compiler's heap-layout-dependent output (splitscreen) means byte-for-byte comparisons on other machines may show that file differing for reasons unrelated to this patch. Trailer lines kept as instructed (Co-Authored-By: Claude Fable 5.1, Claude-Session), so Jolyon should decide whether they stay before pushing; the PR body carries no session link.

## Related bugs found, not fixed here

1) Named const objects with identical contents are merged, pointers compare equal: review probes/p27_const_data.c, 2/10 on 4da3147 and v1.32.273. 2) C++ virtual call through an array of base pointers wrong at -O2/-Os/-O3 even with distinct bodies: probes/c04_cpp_virtual_only.cpp, c05_cpp_virtual_distinct.cpp, 4/10 on 4da3147 and v1.32.273. 3) Incompatible function pointer initializer accepted at -O2 (rejected at default): probes/i01_invalid_assign.c -O2 compiles and runs on 4da3147 and v1.32.273 (warning 2009 only). 4) 'typedef-name volatile x' rejected (error 3006 ';' expected): scratch p/x06_typedef_volatile.c, 4da3147, v1.32.273 and the fix. 5) Prototyped function assigned to 'int (*)()' rejected: probes/p18_cast_kr_fnptr.c, both compilers. 6) '(void *)fa != (void *)fb' gives 'Not a numeric or pointer type': probes/p23_cast_compare_direct.c, both compilers (r16's area). 7) Scalar global 'unsigned ua = (unsigned)fa;' is 'Non constant initializer' (probes/p09_global_uint_init.c; gcc rejects it too, so arguably not a bug). 8) Compiler output depends on heap layout: samples/hires/splitscreen.c -bc -O2 changes with MALLOC_PERTURB_/MALLOC_TOP_PAD_ on 4da3147 and v1.32.273 (nformf bytecode size varies), likely an uninitialised read or pointer-order dependence in the bytecode optimiser. 9) p26-style fastcall mismatch at -O0 is a regression of main vs v1.32.273 (pinned passes -O0/default), fixed here as a side effect of the typecast change.

## Draft pull request

**Title:** Fix merging of identical functions whose address is taken

````markdown
Two functions that compile to identical code are merged by the linker even when the program takes their addresses, so pointers to different functions compare equal and function pointer tables hold the same entry twice. With the default optimisation level this example fails its assert:

```c
#include <assert.h>

int seen;
void fa(const char * s) { (void)s; seen = 1; }
void fb(const char * s) { (void)s; seen = 2; }
typedef void (* fop)(const char * s);

fop gp = fa;

int main(void)
{
    fop q = fb;
    assert(gp != q);
    return 0;
}
```

Reproduce with `oscar64 -ea -g -n example.c` (also fails with `-bc`). The unmodified compiler exits with status 20 after an emulation result of -1; `-v2` prints `Match fb : fa`, `fa` is missing from the map file and `gp` is initialised with `fb`'s address. `-O2`, `-Os` and `-O3` pass this particular example only because `gp != q` is folded at compile time; a variant that indexes a table at run time (`fop tab[2] = { fa, fb }; volatile int i = 0; assert(tab[i] != tab[i + 1]);`) fails at `-O1`, `-O2`, `-Os` and `-O3` in both back ends. `-O0` is a passing control. The behaviour is the same on v1.32.273 and on `main` (4da3147).

Cause: `Linker::CombineSameConst` folds linker objects that are `LOBJF_CONST` with identical bytes and references into one, and every procedure's linker object is marked `LOBJF_CONST` (`InterCodeProcedure` constructor). The pass runs under `COPT_OPTIMIZE_BASIC`, i.e. at `-O1` and above. Merging is fine for functions that are only called, but a function whose address is used as a value must keep its own address. The front end records those functions: `GlobalAnalyzer::RegisterProc` sets `DTF_FUNC_VARIABLE` and `InterCodeGenerator::TranslateProcedure` copies it to `proc->mFuncVariable`, but the linker never saw it.

The fix adds a linker object flag `LOBJF_FUNC_VARIABLE`, sets it in `TranslateProcedure` next to `mFuncVariable`, and excludes flagged objects from both sides of the match in `CombineSameConst`: a flagged function is neither folded into another function nor absorbs one. Functions that are only called directly, and constant data, are still merged (a called-only pair can lose its merge when the bodies reference address-taken functions that are no longer merged, which is correct).

Two related ways for distinct functions to end up at one address, found in review, are closed in the same patch:

- A function whose address is only used through a cast to an integer, `(unsigned)f` (the usual way to install a vector), never got `DTF_FUNC_VARIABLE`: `GlobalAnalyzer::Analyze` did not call `RegisterProc` for the operand of `EX_TYPECAST` (pointer casts are folded away earlier and were covered). Besides the merge, this let such a function keep its fastcall parameter layout while an indirect call through the integer uses the stack layout, so `__noinline int k(int x) { return x + 1; }` called directly as `k(5)` and then as `((ifn)(unsigned)k)(7)` returns the wrong value at every level including `-O0` on `main`. One `RegisterProc(ldec)` in the `EX_TYPECAST` case fixes both; it does nothing unless the operand is a function constant.
- `Linker::Forwards` appends a native function that ends in `JMP target` to its target and drops the `JMP`. When the function is nothing but that `JMP` (a bare tail call, `void fb(void) { fa(); }` with both addresses taken) it ends up with size 0 at `fa`'s address at `-n -O2`/`-Os`/`-O3`. A flagged 3-byte object is no longer appended.

9 insertions, 3 deletions in `Linker.h`, `Linker.cpp`, `GlobalAnalyzer.cpp` and `InterCodeGenerator.cpp`.

The regression test `autotest/funcptrmergetest.c` covers a volatile function pointer global initialiser, a run-time indexed function pointer array, a struct of function pointers reached through a volatile pointer (checking that the entries are distinct and are the right functions), addresses used only as integers, a bare tail call pair, and the direct/indirect call of `k` above. It is discovered by the autotest makefile and registered in `autotest.bat`. Each group fails on its own on `main` in the configurations it targets; the whole test fails in all 10 `-bc`/`-n` x default/`-O2`/`-O0`/`-Os`/`-O3` configurations on `main` 4da3147 (8 of 10 on v1.32.273, whose `-O0` has no fastcall mismatch) and passes all 10 with the patch.

Validation against `main` 4da3147 on Linux, targeting C64:

- Full autotest (`make -k -C make check`): 1,541 successful emulations on the baseline, 1,551 with the patch and new test; no failures in either run.
- The 159 autotest programs plus 22 small reproducers from our project, compiled with both compilers in five configurations (`-n -O2`, `-n -Os`, `-n -O0`, `-n -O3`, `-bc -O2`): 845 program/configuration pairs compile with both (12 reproducers are rejected by both), 836 are byte-identical. The 9 differences are the new test and `autotest/funcvaropt.c`, which consists of many trivially identical functions used as function pointers: 38 of its 60 merges are no longer allowed, it grows by 459-460 bytes native and 958 bytes bytecode, and it still passes in every configuration.
- The 146 programs under `samples/` in the same five configurations: 333 pairs compile with those plain flags, 332 are byte-identical. The one difference, `hires/splitscreen.c` at `-bc -O2`, is not caused by the patch: on `main` the output of that program already depends on the compiler's heap layout (it changes with `MALLOC_PERTURB_` or `MALLOC_TOP_PAD_`), and under any such perturbation both compilers produce identical output.

Known limitations: no size change was observed in the samples, but any program that stores the addresses of several functions with identical code now keeps one copy per function (a two-stub example grows from 154 to 155 bytes), and a `(void)f;` statement now counts as a value use of `f`. Named const data with identical contents is still merged (`const int ca[3] = {1,2,3}, cb[3] = {1,2,3};` gives `ca == cb` on `main` and with this patch); that is the same pass applied to data and is deliberately left out of this change. C++ virtual functions are excluded from `RegisterProc` as before.

Prepared with AI assistance (Claude Code) while porting NetHack 3.4.3 to the C64.
````
