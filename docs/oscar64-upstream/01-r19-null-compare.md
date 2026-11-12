# 01. Fix pointer compared with integer constant 0 folding as not equal

| | |
|---|---|
| Branch | `fix/r19-null-compare` in `~/src/oscar64-dev`, commit `8ca779561d21`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/01-r19-null-compare.patch`](../../tools/oscar64-upstream/patches/main/01-r19-null-compare.patch) |
| Kind | wrong code (silent) |
| Since | 6af50f5 (2024-10); on v1.32.273 and main |
| NetHack | Compat #23 (repro r19). `pickup.c:2113/2115` tests `invent != 0` with `invent` initialised to `(struct obj *)0` in `decl.c`: at `-Os` the game would think the inventory is never empty there. `!p` used as a value is wrong too. Part of the proposed patched pin (ADR-0007). |
| Reviews | Opus (round 2, ran probes): submit-after-changes, 0 high, 2 medium, 4 low; Codex (read the diff): submit after changes; fix-up: ready; final Codex check: submit after changes |
| Recommendation | **Submit first. r16 (#6) is stacked on it.** |

## In plain words

The last check found three small wording problems in the pull request text and nothing wrong with the code. First, the text said the compiler still rejects comparing a pointer with an ordinary integer variable; that is true for a variable that could hold anything, but when the variable is set to 0 once and never changed, the optimiser at -O2 and above replaces it by 0 before the check runs, so both the old and the new compiler accept it. The text now says exactly that and notes it is an old quirk this patch does not touch. Second, the text claimed all numbers came from "the commands shown", but most of the test programs behind those numbers live in our project, not in the pull request; the sentence now says how the numbers were obtained without implying they can be rerun from the PR alone. Third, while re-reading I found the text also said pointers that are written somewhere were always fine; in fact a pointer written only inside a function nobody calls was wrong too, because the optimiser removes that function first, so the sentence was tightened (I confirmed with a probe that a store from a function that is called was and is fine). The request to remove the session link from the commit is for Jolyon to decide. Every number in the text was recomputed from the recorded results and matches. No source or test file changed, so the branch is the same single commit as before and the fix stacked on it needs no rebase.

## The fix

Unchanged from the reviewed commit 5a07baa: in the two existing C-only "integer constant 0 compared with a pointer" branches of EX_RELATIONAL in oscar64/InterCodeGenerator.cpp, emit an IC_CONSTANT IT_POINTER IM_ABSOLUTE 0 (the constant CoerceType uses for pointer to bool) and use it as the operand, taking the comparison type from the pointer side when the 0 is on the left; in EX_LOGICAL_NOT mark the zero constant IM_ABSOLUTE when its type is a pointer. New autotest/nullptrcmptest.c registered in autotest.bat. This round changed only the PR text: qualified the `p == x` rejection claim (h13: never-written `int x = 0` accepted at -O2+ by both builds, pre-existing), qualified "pointers that are written somewhere are correct" (a store in a never-called function does not count), and replaced the closing "commands shown" sentence with an accurate statement of how the numbers were obtained.

## Regression test

autotest/nullptrcmptest.c (132 lines, assert based, registered in autotest.bat after ptrarraycmptest.c, picked up by the makefile wildcard). Covers file-scope char*/cast char*/void*/struct*/function pointer and function-scope static initialised to 0; p == 0, p != 0, 0 == p, 0 != p; zero spellings 0L, 0u, 0UL, 0x0, enum ZERO, (2 - 2), (int)0, sizeof(char) - 1; (char *)0 == 0 both orders; z() == 0 and 0 == z(); if / ?: / && / || / while / int r = (p == 0); !p, !(char *)0, !n as values; a pointer initialised with &c in both orders; ordered compares as an extension with hi = (char *)0x8000; run-time pointers through set() and a char * volatile (null, &c, 0xd000). Before (4da3147 and v1.32.273): emulation result -1 in all ten configurations; after: 0 in all ten; ran as 10 steps in make check (1541 -> 1551 emulations). Host gcc build exits 0.

## Evidence

**Repro matrix.** Ten configurations -ea -g {-bc|-n} x {default,-O2,-O0,-Os,-O3}; compilers 4da3147 (~/src/oscar64-base), v1.32.273 (~/src/oscar64), fix 5a07baa. Results in /home/jolyon/nethack64/build/oscar64-wt/r19-null-compare-scratch/fixup2/probes-{base,pinned,fix2}.txt, variants-{base,fix}.txt. Key cases: r19_global_null_pointer_compare.c and cases/global_null_pointer_ne.c: before 1 at -O2/-Os/-O3 (6/10, exit status 20, error 3007 Execution failed '1'), 0 elsewhere; after 0 in 10/10. 107 review probes (adv 64, syn 18, rej 13, ord 5, r16 n05-n08, 2 cases, new test): before 45 programs wrong (284 of 1070 runs); after 13 wrong (78 runs) = b10/c01/c02/c05/c06/d06/d09/k01/k02/k04/k05/m02/m04, all the compile-time interpreter path (-O2/-Os/-O3 only); 32 fully fixed incl. all nine !p probes, d07, a04, g02-g17, o01/o02/o05, n05/n06/n08, h11 C++; 3 partially fixed (b10, d06, k04: -O1 inlining path fixed, -O2+ interpreter path remains); 0 regressions (no run that was 0 before is non-0 after); 0 compile-status changes; 17 programs rejected by both in 10/10 (invalid C h01-h09, C++ h10/h12, pre-existing a06/g15/n01/n02/n07, malformed b13). v1.32.273 equals 4da3147 on every probe except syn/g05 and g13 (enum zero: pinned right, 4da3147 wrong, fix right). Author's variants: 24 of 45 files still exist; 7 wrong before (nb1, nb4, nb8, v13_le 6/10 each, v6_cast_eq0 10/10, plus the two cases), all 0 in 10/10 after. Two new probes fixup2/b13b_noinline_param0.c and b14_noinline_param_addr.c (__noinline helper always called with 0 / with &c, constant parameter propagation): before 2 resp. 4 at -O2/-Os/-O3, after 0 in 10/10. Unique totals used in the PR: 131 programs, 52 wrong before (330 of 1310 runs), 13 wrong after (78 runs).

**Autotest.** make -k -j4 -C /home/jolyon/nethack64/build/oscar64-wt/r19-null-compare/make check > /home/jolyon/nethack64/build/oscar64-wt/r19-null-compare-scratch/autotest-fixup2.log (run on the final sources; make check relinked bin/oscar64 at 06:56 from the same objects). autotest_diff.py autotest-base-4da3147.log autotest-fixup2.log: emulations base 1541, new 1551 (+10 = nullptrcmptest.c in its ten steps, all 'Emulation result 0'), new failures 0, fixed 0, failing in both 0. No testint16mul.c or splitscreen.c quirk appeared.

**Corpus.** corpus_diff.py ~/src/oscar64-base/bin/oscar64 <wt>/bin/oscar64 --out /home/jolyon/nethack64/build/oscar64-wt/r19-null-compare-scratch/corpus-fixup2 -j4 (after make check had finished): 181 files (158 autotest sources from the worktree + 23 tests/oscar64-repros/*.c) x 5 configurations (-n -O0/-O2/-Os/-O3, -bc -O2) = 905 runs; both compile 845; identical 836; different 9; status changed 0, hence both-fail 60 (the 60 runs where neither compiler produces a program, unchanged). The 9 differences are all in the two files that contain the bug: autotest/nullptrcmptest.c bc-O2 1495->1259, n-O0 1096->1036, n-O2 419->317, n-O3 419->317, n-Os 539->505 bytes (before, main folded into failing assert paths; the test is verified correct by make check and the 10-config run), and oscar64-repros/r19_global_null_pointer_compare.c n-O2/n-O3/n-Os 139->137 (main folds to return 0 instead of return 1) and bc-O2 726->726 (same size, constant 1 replaced by 0). Total size of the 845 programs 2146175 -> 2145635 bytes (-540, entirely those two files). Every other program, including the 40 autotests that compare pointers with 0/NULL and the 11 C++ tests using !, is byte-identical, so the pointer-typed constants (EX_RELATIONAL and EX_LOGICAL_NOT) generate the same code as before. Samples: make -C samples all with each compiler (fixup2/samples-base, samples-new): 65 .prg files, all byte-identical, 460937 bytes total, both builds exit 0.

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| opus | medium | #1 Same misfold in EX_LOGICAL_NOT: `!p` used as a value folds to 0 (C and C++) | fixed |
| opus | medium | #2 `p ==/!= 0`, `p == q`, `if (p)` inside a helper evaluated at compile time (ConstexprInterpreter) still wrong at -O2/-Os/-O3 | out-of-scope |
| opus | low | #3 PR text misdescribes `0 == p`: the old integer path folded a non-null pointer equal to 0; the fix corrects that | fixed |
| opus | low | #4 PR counts contradict the author's logs; unmentioned behaviour changes (0 < p signedness, f() == 0, 0L/0u/0x0/(1-1)/enum/sizeof spellings); '179 autotest and repro sources' hides 24 nethack64 files; private session URL in footer | fixed |
| opus | low | #5 Test gaps (0 < p with high address, f() == 0, 0L/enum zero) and two non-ISO lines without comment | fixed |
| opus | low | #6 Pre-existing: null-constant check depends on optimisation level (invalid `p == x` accepted at -O2+), array/function operands and `p == !1` rejected | out-of-scope |
| codex | medium | #1 The `dtype = vr.mType` change (integer-left comparisons take the pointer type) has no targeted regression test, e.g. 0 < hi for hi >= 0x8000 | fixed |
| codex | medium | #2 Run-time coverage not established (set(&c)/set(0) could be constant-folded); other null pointer constant spellings untested | fixed |
| codex | low | #3 Test comment misstates C++ (equality with literal 0 is valid C++); ordered pointer-vs-0 compares are not ISO C | fixed |
| codex | low | #4 Several PR statements exceed the evidence (pointer constants vs pointer typed; 'existing folding is right'; parent-commit claim; 139->137 is program not function size; corpus proves only tested programs) | fixed |
| codex | low | Possible optimisation cost if the dead integer constant is not removed | rejected |
| other-review | low | r16 reviewer: zero-on-left probes n05/n06/n07/n08 should pass with r19 alone | fixed |

<details><summary>Evidence for each finding</summary>

1. **#1 Same misfold in EX_LOGICAL_NOT: `!p` used as a value folds to 0 (C and C++)** (fixed)

   Reproduced with 4da3147, v1.32.273 and the fix as it stood (ffdc631): adv/f02_not_value_castnull.c (`int r = !(char *)0;`) result 1 in 10/10; adv/f01, f05 (`int r = !p;`, p a null global) 1 at -O2/-Os/-O3 (6/10); adv/d01, d11, d12, e03, c04 (inlined `return !p;` called with 0) 1 at default -O1 (2/10); rej/h11_cpp_nullptr.cpp (`bool b = !p;`) 2 at -O2/-Os/-O3. Cause confirmed by reading InterCodeGenerator.cpp EX_LOGICAL_NOT: the zero constant is IT_POINTER with mMemory left at the InterOperand default IM_NONE (InterCode.cpp:4483), while the parser's null pointer (DT_CONST_ADDRESS, InterCodeGenerator.cpp:2396ff) is IM_ABSOLUTE with the same mVarIndex -1 / mLinkerObject null defaults, so only mMemory differs. Adopted the reviewer's two lines (`if (zins->mDst.mType == IT_POINTER) zins->mConst.mMemory = IM_ABSOLUTE;`) after checking them myself: all nine `!p` probes now 0 in 10/10 (probes-fix2.txt), nothing else in the 107 probes changed (diff probes-fix.txt probes-fix2.txt shows exactly those nine lines), autotest no new failures, corpus 836/845 byte-identical, 65 samples identical. Test now has `r = !p; assert(r == 1); r = !(char *)0; assert(r == 1); r = !n; assert(r == 0);`.

2. **#2 `p ==/!= 0`, `p == q`, `if (p)` inside a helper evaluated at compile time (ConstexprInterpreter) still wrong at -O2/-Os/-O3** (out-of-scope)

   Reproduced identically with 4da3147, v1.32.273 and the final fix: adv/k01_constfn_ne_strlit.c, k02, k05, m02, m04, c01, c02, c05, c06, d09 give 1 or 3 at -O2/-Os/-O3 (6/10); k04 (`0 != p`), d06 (`0 == p`), b10 wrong at -O2+ after the fix (and additionally at -O1 before it, which the fix cures: the -O1 path is inlining, the -O2+ path is GlobalOptimizer::ReplaceConstCalls -> Constexpr.cpp EvalRelational, which takes the integer branch when one operand is a pointer). Writing the helper as `p != (struct S *)0` passes 10/10, and `same(&c, &c)` / `if (p)` are wrong too, so it is an interpreter pointer bug, not this fold. Not fixed here (different file and mechanism); listed in adjacent_bugs and in the PR body as a known limitation so the title is not read as covering every pointer-vs-0 compare.

3. **#3 PR text misdescribes `0 == p`: the old integer path folded a non-null pointer equal to 0; the fix corrects that** (fixed)

   Reproduced: adv/d07_zero_left_global_addr.c (`char *n = &c; if (0 == n) return 1;`) result 1 at -O2/-Os/-O3 with 4da3147 and v1.32.273, 0 in 10/10 with the fix; adv/d06 at -O1 (inlined `return 0 == p;` with &c) 1 before, 0 after; r16 probes n05/n06/n08 (`0 != p`, `0 != &x`, `0 != &local`) 1 in 10/10 before, 0 in 10/10 after; new probe b14_noinline_param_addr.c (`__noinline` helper always called with &c, zero on the left) 4 at -O2+ before, 0 after. Commit message, PR body and the test comments now say the zero-on-left form was wrong the other way; the `n` asserts are described as regression checks and `assert(!(0 == n))` was added.

4. **#4 PR counts contradict the author's logs; unmentioned behaviour changes (0 < p signedness, f() == 0, 0L/0u/0x0/(1-1)/enum/sizeof spellings); '179 autotest and repro sources' hides 24 nethack64 files; private session URL in footer** (fixed)

   Could not re-run the author's 45 variants completely: only 24 of the 45 files still exist (21 of the author's scratch files are gone), those 24 give 7 wrong before / 0 after. The PR now uses numbers I produced myself on the final commit: 131 programs (107 review probes + 22 further variants + 2 new noinline probes) in 10 configurations, 52 wrong before (330 of 1310 runs), 13 wrong after (78 runs, all the interpreter path), 0 regressions, 0 compile-status changes. The `0 < p` signedness change is reproduced (ord/o01: run-time `0 < w` with w = 0xd000 result 2 in 10/10 before, 0 after; ord/o05 constant form same) and is stated in the PR and tested (`assert(0 < hi)`, `assert(0 < live)`). a04_return0 (`f() == 0`, inlined return 0) and syn/g02-g17 spellings reproduced wrong at -O2+ before, 0 after; listed in the PR and the test (0L, 0u, 0UL, 0x0, enum ZERO, (2 - 2), (int)0, sizeof(char) - 1). Corpus described as '158 autotest sources plus 23 small reproducers from our project'. Session URL removed from the PR body; the AI-assistance sentence kept.

5. **#5 Test gaps (0 < p with high address, f() == 0, 0L/enum zero) and two non-ISO lines without comment** (fixed)

   Added to autotest/nullptrcmptest.c: `char *hi = (char *)0x8000;` with `hi > 0`, `0 < hi`, `0 <= hi`, `!(0 > hi)`, `!(hi < 0)`; `char *z(void) { return 0; }` with `z() == 0` and `0 == z()`; the eight zero spellings; `char * volatile live` compared in both orders when null, after `live = &c` and after `live = (char *)0xd000`. The ordered compares are under a comment saying they are an extension and that pointers compare unsigned. gcc -std=c99 -pedantic: only -Wpedantic 'ordered comparison of pointer with integer zero' warnings and a gcc quirk on `0u` (-Wpointer-compare); host binary exits 0. Test fails on 4da3147 and v1.32.273 in 10/10 (result -1; at -O2 the trace names line 41 `assert(p == 0)`), passes 10/10 with the fix, and ran as 10 steps in make check.

6. **#6 Pre-existing: null-constant check depends on optimisation level (invalid `p == x` accepted at -O2+), array/function operands and `p == !1` rejected** (out-of-scope)

   Reproduced with both compilers: rej/h13_intvar_zero.c error 3012 at -O0/-O1, accepted at -O2/-Os/-O3 (base then computes 1, fix 0); adv/n01_array_eq0.c (`a == 0`), r16 p/n07_zero_left_string.c (`0 != "abc"`) and adv/n02_fn_eq0.c (`f == 0`) rejected 'error 3013: Not a numeric or pointer type' in 10/10 by 4da3147, v1.32.273 and the fix (the outer EX_RELATIONAL test requires a DT_TYPE_POINTER operand; arrays stay DT_TYPE_ARRAY after Dereference); syn/g15 and rej/h09 (`p == !1`) rejected by all. Unchanged by design; listed in adjacent_bugs. Note for the orchestrator: n07 therefore cannot pass with this fix alone; it is the same array-operand rejection as n01, not the r19 folding bug (n05, n06, n08 do pass 10/10 with the fix alone).

7. **#1 The `dtype = vr.mType` change (integer-left comparisons take the pointer type) has no targeted regression test, e.g. 0 < hi for hi >= 0x8000** (fixed)

   Confirmed the gap: the old test had only `0 == p` / `0 != p`. Reproduced the behaviour change with ord/o05 (`0 < (char *)0xd000` false in 10/10 before, true after) and ord/o01 (run-time). Test now has the suggested block: `hi = (char *)0x8000` with `0 != hi` (via `0 != n`/`0 != w` for addresses and) `0 < hi`, `0 <= hi`, `!(0 > hi)`, `!(hi < 0)`, `hi > 0`, plus run-time `live = (char *)0xd000; assert(0 < live); assert(!(0 >= live));`. `assert(0 < hi)` and `assert(0 < live)` fail on the before compiler at every level (signed int16 compare), so the dtype change is now guarded.

8. **#2 Run-time coverage not established (set(&c)/set(0) could be constant-folded); other null pointer constant spellings untested** (fixed)

   Added `char * volatile live = 0;` compared in both orders and with both operators when null, non-null and high. The `set()` lines are kept and now also test the zero-on-left forms. Spellings: `0L`, `0u`, `0UL == p`, `0x0`, enum `ZERO`, `(2 - 2)`, `(int)0`, `sizeof(char) - 1` all reach the patched branches (parser folds them to EX_CONSTANT 0): each compiles with the fix and the corresponding syn/g02-g17 probes were wrong at -O2/-Os/-O3 on 4da3147 and are 0 in 10/10 after, so they do exercise the fix. (Observation: the enum spellings g05/g13 are wrong on 4da3147 but right on v1.32.273; the fix makes them right on both.)

9. **#3 Test comment misstates C++ (equality with literal 0 is valid C++); ordered pointer-vs-0 compares are not ISO C** (fixed)

   Correct: ISO C++ allows `p == 0`; it is Oscar64 that rejects it (rej/h10_cpp_eq0.cpp: error 3012 'Cannot compare integer and pointer' in 10/10 with base and fix). Test comment now reads 'Oscar64 rejects the comparison in C++ mode, so this is a C only test'. The ordered compares carry a comment calling them an extension; the PR body says ISO C only permits the equality operators and describes the signedness change as a behaviour change of an extension, not a standard-conformance fix.

10. **#4 Several PR statements exceed the evidence (pointer constants vs pointer typed; 'existing folding is right'; parent-commit claim; 139->137 is program not function size; corpus proves only tested programs)** (fixed)

   PR body now says 'pointer typed', limits the folding claim to 'the memory class test in the folding compares like with like', says the 139->137 bytes are the `-O2` program, states that byte-identity holds for the compiled programs listed, and reduces the history claim to the verified facts: `git show 6af50f5` adds the four `op1.mType == IT_POINTER` branches, first tag v1.31.254, parent 62ab925 (verified). I did not rebuild 62ab925, so the PR no longer claims the parent 'compiles all reduced cases correctly'.

11. **Possible optimisation cost if the dead integer constant is not removed** (rejected)

   Not observed: every corpus program other than the two that contained the bug is byte-identical at -n -O0/-O2/-Os/-O3 and -bc -O2 (836 of 845, including the 40 autotests that compare pointers with 0/NULL, e.g. strchrtest.c, recursiontest.c, stdlibtest.c), and the new test's -O0 program is smaller than the base compiler's (1096 -> 1036 bytes). Mentioned in risks as a theoretical shape outside the corpus.

12. **r16 reviewer: zero-on-left probes n05/n06/n07/n08 should pass with r19 alone** (fixed)

   n05_zero_left_fnptr_var.c, n06_zero_left_global_addr.c, n08_zero_left_local_addr.c: result 1 in 10/10 with 4da3147 and v1.32.273, 0 in 10/10 with the fix. n07_zero_left_string.c (`0 != "abc"`) is rejected with 'error 3013: Not a numeric or pointer type' in 10/10 by base, pinned and fix alike: an array operand (string literal) never reaches the patched branch (same pre-existing rejection as adv/n01 `a == 0`), so it is not a zero-on-left folding case and is listed in adjacent_bugs rather than fixed here.

</details>

## Last round: final-check findings and what happened to them

Changed in the last round: text-only. Commit before it: `5a07baaf6672`.

| From | Severity | Finding | Resolution |
|---|---|---|---|
| codex final check #1 | low | PR text: 'p == x (an int variable) ... still rejected' is too broad; a zero-valued never-written int variable is accepted at -O2 and above by both builds | fixed |
| codex final check #2 | low | Commit message still carries the Claude-Session URL trailer | left-for-jolyon |
| codex final check #3 | low | PR text: 'all numbers above come from running the commands shown' overstates what the PR shows (probe corpus and most commands are absent) | fixed |
| self (re-read of PR body against evidence) | low | PR text: 'pointers that are written somewhere are correct' is too strong; a store in a function that is never called does not count | fixed |
| self (number check) | low | All counts in the PR body re-verified against the recorded evidence | fixed |

<details><summary>Evidence, and what was re-run</summary>

1. **PR text: 'p == x (an int variable) ... still rejected' is too broad; a zero-valued never-written int variable is accepted at -O2 and above by both builds** (fixed)

   Reproduced from the recorded probe runs: rej/h02_var.c (`int x;`) is rejected 'error 3012: Cannot compare integer and pointer' in 10/10 by base and fix (probes-base.txt / probes-fix2.txt). rej/h13_intvar_zero.c (`int x = 0`, never written) is rejected only at default and -O0 and accepted at -O2/-Os/-O3 by both (review/out/h13_intvar_zero/*/log.txt: base 'Emulation result 1', fix 0). Mechanism: GlobalOptimizer::ReplaceGlobalConst runs only under COPT_OPTIMIZE_GLOBAL (Compiler.cpp:987, set by -O2 and above) and substitutes x by its initializer before the EX_CONSTANT check in EX_RELATIONAL sees the expression; pre-existing, unchanged by this patch, and h13 is one of the 52 'wrong before' programs. PR validation bullet now says `x` an int variable without a constant initializer, states the h13 behaviour and that it is counted among the 52, and that it is unchanged.

2. **Commit message still carries the Claude-Session URL trailer** (left-for-jolyon)

   Per the round's rules the trailer lines (Co-Authored-By, Claude-Session) are not to be changed here; Jolyon decides them for all branches at once. Commit 5a07baa left untouched.

3. **PR text: 'all numbers above come from running the commands shown' overstates what the PR shows (probe corpus and most commands are absent)** (fixed)

   The PR shows only the example command, the ten/five configuration lists and `make -k -C make check`; the 131 probe programs and the scripts (review/run10.sh, cmp2.sh, corpus_diff.py) are in the nethack64 scratch directories, not in the PR. Closing sentence now says the numbers were obtained by building main 4da3147 and this patch and running both on the autotest suite, the samples and the small programs described, and that the probe programs are not part of the PR.

4. **PR text: 'pointers that are written somewhere are correct' is too strong; a store in a function that is never called does not count** (fixed)

   Variant nb1_written.c (`char *p = 0; void f(char *q) { p = q; } int main(void) { return p == 0 ? 0 : 1; }`, f never called) is wrong at -O2/-Os/-O3 with 4da3147 (variants-base.txt and re-run today) and 0 in 10/10 with the fix. New probe final/nb1b_written_called.c (main calls f(0)) is 0 in 10/10 with both compilers (scratch/final/nb1-probe.txt). PR now says pointers written by code the optimizer keeps are correct and that a store in a never-called function does not count.

5. **All counts in the PR body re-verified against the recorded evidence** (fixed)

   Recomputed from fixup2/probes-base.txt, probes-fix2.txt, variants-base.txt, variants-fix.txt: 129 unique programs, 50 wrong before (318 runs), 13 wrong after (78 runs: b10, c01, c02, c05, c06, d06, d09, k01, k02, k04, k05, m02, m04), 0 regressions, 0 compile-status changes; plus b13b/b14 (6 wrong runs each before, 0 after) gives the PR's 131 / 52 / 330 of 1310 / 13 / 78. autotest_diff.py: base 1541, new 1551, new failures 0. corpus-fixup2.log: 181 files x 5, both compile 845, identical 836, different 9 (nullptrcmptest.c x5, r19 repro x4), status changed 0; sizes 139->137 (n-O2/-Os/-O3), 726->726 (bc-O2), 1096->1036 (n-O0). Samples: 65 .prg files, 460937 bytes each build, diff -rq identical. New test: -1 in 10/10 before, 0 in 10/10 after (probes files). No correction to the numbers was needed; 'fixed' here means confirmed and kept.

**Re-validation.** Text-only round: nothing rebuilt, no source or test file changed, branch left at 5a07baaf667257473e2f01f4f3e8ca0a825fb5f3 (one commit on 4da3147, `git status` clean). Re-verified on the recorded evidence of that commit: autotest_diff.py autotest-base-4da3147.log autotest-fixup2.log -> emulations base 1541, new 1551, new failures 0, fixed 0, failing in both 0. corpus-fixup2.log -> 181 files x 5 configurations, both compile 845, identical 836, different 9 (autotest/nullptrcmptest.c in 5 configurations, oscar64-repros/r19_global_null_pointer_compare.c in 4), status changed 0; r19 repro 139->137 bytes at n-O2/-Os/-O3, 726->726 at bc-O2; nullptrcmptest 1495->1259, 1096->1036, 419->317, 419->317, 539->505. Samples: find -name '*.prg' | wc -l = 65 in each tree, 460937 bytes each, diff -rq identical. Probe tallies recomputed from the result files: 129 programs 50 wrong before / 318 runs, 13 after / 78 runs, 0 regressions, 0 status changes; plus 2 noinline probes = 131 / 52 / 330 of 1310 / 13 / 78 as the PR states. New probes run today with ~/src/oscar64-base/bin/oscar64 and the worktree's bin/oscar64 in the ten configurations: nb1_written 1 at -O2/-Os/-O3 (6/10) before, 0 in 10/10 after; nb1b_written_called 0 in 10/10 with both (scratch/final/nb1-probe.txt). h13_intvar_zero logs re-read: error 3012 at default/-O0, accepted at -O2/-Os/-O3 by both (base 1, fix 0).

</details>

## Final check (Codex, read-only, on the final commit)

<details><summary>SUBMIT AFTER CHANGES</summary>

VERDICT: SUBMIT AFTER CHANGES

1. **Low — PR text: “`p == x` (an int variable) … still rejected.”** This is too broad: the supplied `h13_intvar_zero.c` evidence says a zero-valued integer variable is accepted at `-O2` and above by both builds. Qualify this as the tested **nonconstant** integer-variable case, and acknowledge the unchanged optimisation-dependent acceptance.

2. **Low — commit message: `Claude-Session: https://claude.ai/code/session_…`.** The session URL remains in the commit despite the earlier privacy cleanup. Remove that trailer before publishing; retain the AI attribution if desired.

3. **Low — PR text: “all numbers above come from running the commands shown.”** Most validation commands and the probe corpus are absent from the PR. Replace this with “The validation results above were obtained by running both compiler builds,” or provide the scripts and probe sources needed to reproduce those totals.

No code correctness blocker found in the supplied diff. The test guards the changed paths, including logical-not folding and integer-left comparison signedness. The dead-constant concern is reasonably dismissed as a blocker by the stated evidence, and the separate constexpr defect is appropriately disclosed.

</details>

## Before submitting

- Done 2026-11-12 (Jolyon's decision): the commit ends with one `Co-Authored-By: Claude <noreply@anthropic.com>` line and no session link (message only; the tree is the one validated, commit `5a07baaf6672` before), and the PR text ends with the same AI-assistance sentence as every other PR.

## Risks and limitations

(1) Every C `p ==/!= 0` and every `!p` on a pointer now carries an IM_ABSOLUTE pointer constant instead of an IM_NONE one; 836 corpus programs and 65 samples are byte-identical, but a shape outside the corpus could meet a back-end path that treats IM_ABSOLUTE pointer constants differently. (2) Behaviour change: `0 < p`, `0 <= p` etc. (an extension) change from signed int16 to unsigned pointer compares at every level. (3) The dead integer CONST left behind in EX_RELATIONAL is removed at every level in the corpus; a shape where it is not would cost a few bytes. (4) Not fixed: pointer-vs-0, p == q and if (p) inside helpers the constexpr interpreter evaluates at compile time (-O2/-Os/-O3), disclosed in the PR. (5) Pre-existing and unchanged: the null pointer constant check runs after the global optimizer, so invalid `p == x` with a never-written `int x = 0` is accepted at -O2 and above (now stated in the PR). (6) Not tested: real hardware, non-C64 targets, the full NetHack port with this compiler. (7) r16 is stacked on 5a07baa, which is unchanged by this round, so no rebase is needed for it.

## Related bugs found, not fixed here

(1) ConstexprInterpreter pointer comparisons (Constexpr.cpp EvalRelational takes the integer branch when one operand is a pointer; also wrong for p == q and if (p)): helpers evaluated at compile time via GlobalOptimizer::ReplaceConstCalls at -O2/-Os/-O3 (-O1 -Og suffices). Probes /home/jolyon/nethack64/build/oscar64-wt/r19-null-compare-review/adv/k01_constfn_ne_strlit.c, k02, k03 (passes: cast null), k04, k05, m01-m04, c01, c02, c05, c06, d06, d09, b10 -- wrong at -O2/-Os/-O3 with 4da3147, v1.32.273 and the fix. Needs a new nethack64 repro and an upstream issue. (2) Array operand (incl. string literal) compared with 0 rejected 'error 3013: Not a numeric or pointer type': review/adv/n01_array_eq0.c (`a == 0`), /home/jolyon/nethack64/build/oscar64-wt/r16-fnptr-compare-review/p/n07_zero_left_string.c (`0 != \"abc\"`); 4da3147, v1.32.273 and fix, 10/10. Function designator `f == 0` (adv/n02_fn_eq0.c) same message; addressed by r16. (3) `sel ? &c : 0` rejected 'error 3013: Incompatible conditional types' (review/adv/a06_cond0.c), all three compilers. (4) `p == !1` rejected (review/syn/g15_not1.c, rej/h09_not1.c), all three compilers, gcc accepts. (5) Null-constant check runs after ReplaceGlobalConst, so invalid `p == x` with `int x = 0` is rejected at -O0/-O1 but accepted at -O2/-Os/-O3 (review/rej/h13_intvar_zero.c), all three compilers. (6) Observation, not a bug after the fix: enum constant 0 compared with a pointer (review/syn/g05_enum.c, g13_ne_enum.c) is wrong at -O2+ on 4da3147 but right on v1.32.273; something between the two changed the enum path; the fix makes both right.

## Draft pull request

**Title:** Fix pointer compared with integer constant 0 folding as not equal

````markdown
A file scope (or static) pointer initialised to 0 and never written compares as non-null with `-O2`, `-Os` and `-O3`; `(char *)0 == 0` is false at every optimisation level. This example returns 1 instead of 0:

```c
char *p = 0;

int main(void)
{
	if (p == 0)
		return 0;
	return 1;
}
```

Reproduce with `oscar64 -ea -n -O2 example.c` (also with `-bc`, `-Os` and `-O3`): the emulation result is 1 and the compiler exits with status 20 after `error 3007: Execution failed '1'`; `-O0` and `-O1` are passing controls. The same happens for `= (char *)0`, `= (void *)0`, a function scope `static`, a struct pointer and a function pointer, for `p != 0` and `p <= 0`, for the other spellings of a null pointer constant (`0L`, `0u`, `0x0`, `(2 - 2)`, an enum constant with value 0, `sizeof(char) - 1`), for a call of an inlined function that returns 0 (`f() == 0`), for a function always called with 0 (constant parameter), and for `!p` used as a value (`int r = !p;` at `-O2` and above, `int r = !(char *)0;` at every level). With the 0 on the left the result is wrong the other way round: `0 == n` for `char *n = &c;` is true at `-O2` and above. `if (p)`, `if (!p)`, `p == NULL` and pointers that are written by code the optimizer keeps are correct (a store in a function that is never called does not count: the optimizer removes the function first and then treats the pointer as never written). The code came out of porting NetHack 3.4.3, which tests pointers like `invent != 0` all over.

In C a pointer may be compared with the integer constant 0. `TranslateExpression` (`EX_RELATIONAL`, InterCodeGenerator.cpp) checks for exactly that case but then uses the integer temporary as the pointer operand of the comparison, so the intermediate code is

```
CONST R0(P) <- CA0(-1:0 '')   ; p, substituted by the global optimizer
CONST R1(I) <- CI:0           ; the literal 0, integer constant, IM_NONE
R_EQ  R2(B) <- R0(P), R1(P)
```

`OperandConstantFolding` (InterCode.cpp, `IA_CMPEQ`/`IA_CMPNE` for `IT_POINTER`, used by `EarlyBranchElimination`) treats two pointer constants as equal only when `mMemory`, `mVarIndex`, `mIntConst` and `mLinkerObject` all match. A null pointer constant is `IM_ABSOLUTE` 0, the mistyped integer is `IM_NONE` 0, so `p == 0` folds to false. The fold only fires when both operands are constants: with `-O2` and above because `GlobalOptimizer::ReplaceGlobalConst` substitutes a never-written global by its initializer (inlining and constant parameters have the same effect), and at every level for `(char *)0 == 0`. With the 0 on the left the comparison type is the integer type, so the fold takes the integer path and compares only `mIntConst`, which is why `0 == &c` folds to true. `EX_LOGICAL_NOT` builds the zero it compares a pointer with in the same way (`IT_POINTER` with `mMemory` left at `IM_NONE`), so `!p` as a value has the same problem. The pointer branches of `OperandConstantFolding` were added in 6af50f5 (v1.31.254).

The fix: in the two existing C-only "integer constant 0 compared with a pointer" branches of the `EX_RELATIONAL` translation, emit a null pointer constant (`IC_CONSTANT`, `IT_POINTER`, `IM_ABSOLUTE`, 0, the same constant `CoerceType` emits for pointer to bool) and use it as the operand; when the 0 is on the left the comparison type is taken from the pointer side. In `EX_LOGICAL_NOT` the zero constant is marked `IM_ABSOLUTE` when its type is a pointer. Both operands of a pointer comparison are now pointer typed, so the memory class test in the folding compares like with like, and a pointer initialised with the address of an object still folds to non-null. C++ mode, which rejects `p == 0`, is unchanged; the `EX_LOGICAL_NOT` change applies to C++ as well and fixes `bool b = !p;` for `char *p = nullptr;` at `-O2`.

One behaviour change to be aware of: `0 < p`, `0 <= p` and the like are an extension (ISO C allows only the equality operators with a null pointer constant). They were compiled as signed 16 bit integer compares and are now unsigned pointer compares, like `p > 0` already was, so `0 < (char *)0xd000` is true.

Not fixed here: `p != 0`, `p == q` and `if (p)` inside a small helper that the constexpr interpreter evaluates at compile time (for example `static int has(const char *s) { return s != 0; }` called as `has("abc")`) are still wrong at `-O2` and above. That is a separate problem in `Constexpr.cpp`, where a pointer compared with an integer takes the integer path; I will report it separately.

The regression test `autotest/nullptrcmptest.c` covers the pointer kinds, spellings of zero and expression forms above, `!p` as a value, both operand orders for a null and for a non-null pointer, the ordered compares with an address at or above 0x8000, and pointers written at run time (through a function and through a `volatile`). It is picked up by the makefile and registered in `autotest.bat`. Before: emulation result -1 in all ten configurations (`-bc`/`-n` x default/`-O0`/`-O2`/`-Os`/`-O3`); after: 0 in all ten. Built with gcc on the host it exits 0.

Validation against main 4da3147 on Linux, C64 target:

- 131 small programs (the reduced cases, review probes and variants) in the ten configurations: 52 were wrong before (330 of 1310 runs); after the patch 13 remain wrong (78 runs), all of them the compile-time interpreter case above. No program that was right before is wrong after, and no program changes between compiling and not compiling: `p == 1`, `p == x` (`x` an `int` variable without a constant initializer), `p < 1`, `p == 1.0` and `p == 0` in C++ are still rejected with the same messages at every level. One pre-existing gap is unchanged: `p == x` with a never-written `int x = 0` is rejected at `-O0` and `-O1` but accepted at `-O2` and above by both builds, because the global optimizer substitutes the initializer before the null pointer constant check sees the expression (it is one of the 52: the old build computed 1 for it, the patched build 0).
- Full autotest (`make -k -C make check`): 1541 successful emulations on the baseline, 1551 with the patch and new test, no new failures.
- All 158 autotest sources plus 23 small reproducers from our project, in five configurations (`-n` `-O0`/`-O2`/`-Os`/`-O3`, `-bc -O2`): 845 programs compile with both builds, 836 are byte-identical; the 9 that differ are the new test and the example above, which now compute the right answer (the example's `-O2` program shrinks from 139 to 137 bytes; its `-bc -O2` program has the same size with the constant 1 replaced by 0).
- All 65 `.prg` files built by the samples makefile are byte-identical before and after (460937 bytes in total, both builds exit 0).

Found while porting NetHack 3.4.3 to the C64. Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described. The probe programs are not part of this PR and can be supplied on request.
````
