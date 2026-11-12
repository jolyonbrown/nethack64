# 07. Fix union pointer to const union pointer conversion

| | |
|---|---|
| Branch | `fix/r15-union-const` in `~/src/oscar64-dev`, commit `702408519721`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/07-r15-union-const.patch`](../../tools/oscar64-upstream/patches/main/07-r15-union-const.patch) |
| Kind | rejects valid C |
| Since | v1.32.273 and main |
| NetHack | Compat #19 (repro r15): every `add_menu(..., &any, ...)`, 87 calls. Workaround: one cast in `winprocs.h` (T1.8). |
| Reviews | Opus (round 1, ran probes): submit-after-changes, 1 high, 3 medium, 2 low; Codex (read the diff): submit after changes; fix-up: ready; final Codex check: submit after changes |
| Recommendation | **Submit.** |

## In plain words

The last reviewer found four small wording and coverage issues, no new bugs. The explanation of why C++ picked the wrong function had drifted: on the original compiler the "right" function simply was not considered at all for a union pointer, so the compiler fell back to the generic one; a half-fix would have made both look equally good (hence "ambiguous"); the full fix makes the right one clearly better. Both the PR text and the commit message now say exactly that. The test file claimed to check "returning a const volatile union pointer" but had no such function; one was added and shown to fail on the old compiler and pass on the new one. A sentence that said "every case fails before the fix" was corrected because the struct sanity check is supposed to pass on both. The private session link is left for Jolyon to decide. The full test suite was re-run: 1561 programs run cleanly, no new failures against the 1541 of the baseline. The branch is one commit on upstream main and ready to submit.

## The fix

Settled the four final-check findings. (1) Corrected the root-cause explanation in both the PR body and the commit message: on the unmodified compiler a const-union-pointer overload is not viable for a union pointer at all (so f(const void*) was chosen); fixing IsSubType alone would make it viable but tied at the IsSubType rank with const void*; the IsSameMutable change gives qualification conversion its proper preference. (2) Added keep_const_volatile (volatile CValue* returning its union Value* parameter) plus an assertion to autotest/unionptrconsttest.c so the const-volatile return claim is backed by the test. (3) Reworded the isolation-check sentence so the struct control is not claimed to fail before the fix. (4) Trailers left as they are for Jolyon. Compiler change unchanged: DT_TYPE_UNION added to the struct branch of Declaration::IsSubType, IsSameMutable and IsConstSame.

## Regression test

autotest/unionptrconsttest.c (C, 160 lines): argument, initialisation, assignment and return forms for const, volatile and const volatile (typedef const union Value CValue; volatile CValue*), including the new keep_const_volatile return; typedef'd union; a pointer with one qualifier gaining the other; ==, !=, <, >, subtraction both ways; volatile == mutable; array of pointers to const; struct control; write through mutable seen through const. autotest/unionptroverloadtest.cpp (C++, 103 lines): f(const U*) vs f(const void*) vs f(const S*), g(const U&) vs g(int) vs g(const S&), h(const U*) vs h(...), const U& binding, cp == mp, union copy constructor. Both registered in autotest.bat. Before (4da3147 and v1.32.273): .c E3012 x10, .cpp E3044 x10; after: P x10 each; each union construct also fails in isolation before (E3012/E3018/E3044 or wrong overload) and passes after; the struct control passes on both.

## Evidence

*These are the fix-up round's results, for commit `f2f7715ca3f8`. The last round changed the test; its re-validation of the final commit is under "Last round" below.*

**Repro matrix.** 10 configs = -ea -g {-bc,-n} x {none,-O2,-O0,-Os,-O3}; P = emulation result 0, R<n> = compiled but result n, E<id> = compile error. Columns: base 4da3147 -> final fix (pinned v1.32.273 equals base unless noted). Core: r15_union_ptr_to_const.c E3012->P; unionptrconsttest.c E3012->P; unionptroverloadtest.cpp E3044->P; h01 PR example E3012->P; h02/i3 return E3018->P; d01/i4 cv typedef E3012->P; cx5/i5 partial qualifier E3012->P; b05 incomplete typedef (NetHack ANY_P style) and probe_incomplete E3012/E3018->P. Comparison/subtraction: a01-a04, a09, i1, i2, i10, cv2 E3012->P (struct controls P both). C++ overloads: f01/i6 R1->P, f02/i8 R1->P, f07/i7 E3044->P, f03, f04, f05, f08, f09, i9 E3012/E3044->P; k07 copy ctor R1->P; k01 E3044->E3012 (still rejected; struct k01s E3012 both); e07 (same-tag unions in two namespaces) E3044->E3045 (struct e07s E3045 both); cx4b P->R1 (struct cx4bs R1 both). Struct-parity laxities now reaching unions (struct/int controls P before and after): e01, e03, e04, e05, e06, i03, cx1, cx3, g01, g01_cpp, g02, g04, a05, a07, cx2 E3012->P. Negatives unchanged: neg_drop_arg/assign/init/volatile, neg_other_union(_cpp), neg_struct_drop, neg_drop_cpp E3012 both; b14, d02, d03, h03, f06 rejected both; d04, c03, a06 E3012->E3014 (write through const now diagnosed as such). Unchanged failures: pos_union_value.c (const union u c = v;) E3012 both; b09 E3012 both (struct P on base); b07/c02 (plain 'const volatile union' spelling) P both, pre-existing parser drop. Crash: k05/k06 (union with default constructor) exit 139 in base, pinned and fix. cx4 as written E3026 everywhere (unnamed union typedef at global level rejected in C++ mode).

**Autotest.** make -k -j4 -C /home/jolyon/nethack64/build/oscar64-wt/r15-union-const/make check, run to completion under nohup with foreground waits; log /home/jolyon/nethack64/build/oscar64-wt/r15-union-const-scratch/autotest-fixup.log. autotest_diff.py autotest-base-4da3147.log autotest-fixup.log: emulations base 1541, new 1561 (+10 unionptrconsttest.c, +10 unionptroverloadtest.cpp); new failures 0; fixed 0; failing in both 0; exit 0.

**Corpus.** corpus_diff.py ~/src/oscar64-base/bin/oscar64 (4da3147) vs worktree bin/oscar64 (f2f7715), -j4, default corpus, out /home/jolyon/nethack64/build/oscar64-wt/r15-union-const-scratch/corpus-fixup, log corpus-fixup.log: 182 files (160 autotest .c/.cpp after the 6 multi-file helpers, incl. the 2 new tests, + 22 tests/oscar64-repros) x 5 configurations (-n -O2/-Os/-O0/-O3, -bc -O2) = 910 attempts; both compile 840, identical 840, different 0; status changed 15 = unionptrconsttest.c, unionptroverloadtest.cpp and r15_union_ptr_to_const.c error->ok in all 5; both fail 55 = 11 repro files x 5 (r2, r3, r5, r6, r7, r8, r10, r11, r12, r13, r16: compatibility repros that fail on upstream by design). The 158 existing autotest programs are byte-identical in all 790 configurations; testint16mul.c showed no difference this time. Second run over samples/ (--src each subdirectory, out corpus-fixup-samples): 68 files x 5 = 340 attempts; both compile 333, identical 332, different 1 (hires/splitscreen.c -bc -O2); status changed 0; both fail 7 (memmap/tsr.c all 5; hires/func3d.c and hiresmc/func3d.c at -n -O0). The splitscreen difference is the known include-path quirk, not the patch: the unmodified 4da3147 built in the review's cb/ directory produces the same bytes (md5 06ed79b4...) as the patched compiler, ca and ce, while oscar64-base differs (f36fd674...) and its .asm shows the include-path strings and shifted addresses; running base from a longer symlinked path still reproduces base's own bytes, so the dependence is on the build/include directory, not argv[0].

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| opus | high | C++: valid overloaded call f(const U*) vs f(const void*) becomes ambiguous (3045); f(...) overload silently changes target; g(const U&) vs g(int) still 3044 | fixed |
| opus | medium | Comparison and subtraction between const union T* and union T* still fail (3013) after the IsSubType-only fix | fixed |
| opus | medium | Test's 'const volatile union' case tests nothing: both qualifiers before a union/struct tag are dropped by the parser | fixed |
| opus | medium | Distinct unions with the same tag or no tag now convert silently; PR said 'two different unions still do not convert' | out-of-scope |
| opus | low | Lax rules that already applied to int and struct pointers now apply to unions (ptr-to-ptr, fn-pointer params, conditional result); incomplete volatile prototype variant still fails | out-of-scope |
| opus | low | Test gaps: no return case, no C++ test, no comparison cases | fixed |
| opus | low | PR text issues (1)-(10): false const-volatile claim, 'two different unions' overclaim, missing comparison gap, wrong overload risk text, 790 = 158x5 not 159, repro corpus count meaningless upstream, 87 add_menu not reproducible, 'about 20 call sites', 'were reviewed', footer style | fixed |
| codex | high | Patch newly accepts distinct union types (tagless or same tag); called a regression | rejected |
| codex | medium | Multilevel qualification: union U** -> const union U** accepted via the recursive pointer comparison | out-of-scope |
| codex | medium | Regression test omits return, cv init/assign, vp = mp, partially qualified sources, shadowed tags, completion-order cases; read_typedef reads an inactive member; no persistent negatives | fixed |
| codex | low | 'Nothing in the generated code' and rejection claims need narrower wording; anonymous-union overload example might change selection | fixed |
| codex | low | PR factual corrections: not every union comparison returned false; 795 attempted vs 790 comparable; remainder of the repro corpus unexplained; separate committed vs scratch coverage | fixed |

<details><summary>Evidence for each finding</summary>

1. **C++: valid overloaded call f(const U*) vs f(const void*) becomes ambiguous (3045); f(...) overload silently changes target; g(const U&) vs g(int) still 3044** (fixed)

   Reproduced: f01_ovl_void.cpp base R1 (compiles, calls f(const void*)), IsSubType-only fix E3045 x10; f02 base R1, f07 base E3044. Cause confirmed at Parser.cpp:8917: IsSameMutable (Declaration.cpp:2908) had a struct-only branch, so unions fell to the +256 IsSubType rank, tying with const void*. Adopted the reviewer's line after evaluating it (DT_TYPE_UNION added to the struct branch of IsSameMutable). Final compiler: f01 P x10, f02 P x10, f07 P x10, isolation probes i6/i7/i8 (R1/E3044/R1 before) P x10; k01 (overload that would drop volatile) still rejected (3012 now, 3044 before; struct control k01s gives 3012 before and after). Pinned by autotest/unionptroverloadtest.cpp.

2. **Comparison and subtraction between const union T* and union T* still fail (3013) after the IsSubType-only fix** (fixed)

   Reproduced: a01-a04 (==, != vs &v, >, -) and a09 (C++ subtraction) base E3012, IsSubType-only fix E3013 x10; struct controls a01s/a04s P throughout. Cause confirmed: IsConstSame (Declaration.cpp:2967) struct-only branch, reached via IsConstRefSame at InterCodeGenerator.cpp:3756 and via :3182 / Declaration.cpp:1124 for subtraction. Added DT_TYPE_UNION to that branch. Final: a01-a04, a09, a08, cv2_order_cmp P x10; isolation i1/i2/i10 E3012 before, P after. Side effect reproduced and pinned: k07 (union with user-declared copy constructor) R1 before (bitwise copy), P after, matching g++; added to the C++ test. Other IsConstSame callers (Parser.cpp:110/112/3447-3468 ctor recognition, :8572 protected access, :8759, ICG:5709 reference binding) reviewed; f05/i9 reference binding E3012 -> P.

3. **Test's 'const volatile union' case tests nothing: both qualifiers before a union/struct tag are dropped by the parser** (fixed)

   Reproduced: b07 (const volatile union u* parameter) P x10 on unmodified 4da3147 and on v1.32.273; c02 (write through it) compiles everywhere. Parser.cpp:830-833 applies exactly one qualifier. The parser bug itself is pre-existing, affects structs too, and is left out of this PR (listed in adjacent_bugs). The test now builds a real cv type: typedef const union Value CValue; volatile CValue* (isolation probe i4: E3012 before, P after x10; d01 E3012 -> P; d02/d03 dropping one qualifier stay E3012; d04 write gives E3014). PR text no longer claims the plain const volatile spelling failed.

4. **Distinct unions with the same tag or no tag now convert silently; PR said 'two different unions still do not convert'** (out-of-scope)

   Reproduced: e01 (two tagless typedef unions), e03/cx3 (block-scope shadowing tag), e04, e05/e06 (namespaces), i03 (class scope), cx1: E3012 -> P x10. Struct equivalents (e01s, e02s, cx1s, cx3s, e05s, i03s) already P on 4da3147 and v1.32.273. This is the existing struct rule (mScope equal, or same unqualified mIdent and same size) now applied to unions. Tightening it (e.g. mQualIdent) is a separate change covering structs; not done here. PR text corrected to state the rule and its consequences. Differently tagged unions (neg_other_union, neg_other_union_cpp) stay E3012.

5. **Lax rules that already applied to int and struct pointers now apply to unions (ptr-to-ptr, fn-pointer params, conditional result); incomplete volatile prototype variant still fails** (out-of-scope)

   Reproduced: g01 (union u** -> const union u**), g02, a07: E3012 -> P x10, with int and struct controls P before and after (g01i, g01s, cx2i, cx2s). b09 (prototype volatile union u* written while incomplete, call after completion) still E3012 after; struct version P on 4da3147 (E3012 on v1.32.273). Cause: mVolatile copy never updated on completion (Parser.cpp:680-681 updates only mConst) plus the size pre-check in IsSubType. No code change; stated as a limitation in the PR; listed in adjacent_bugs.

6. **Test gaps: no return case, no C++ test, no comparison cases** (fixed)

   unionptrconsttest.c now has keep_const/keep_volatile return cases (i3: E3018 before, P after), ==, !=, <, >, subtraction both ways, vp = mp, and partial-qualifier cases (cvp = cp, cvp = vp; i5 E3012 before). New autotest/unionptroverloadtest.cpp (registered in autotest.bat, picked up by the makefile wildcard; name differs from the .c so make's %-rules do not collide) covers f(const U*)/f(const void*)/f(const S*), g(const U&)/g(int)/g(const S&), h(const U*)/h(...), const U& binding, pointer comparison and a union copy constructor. Base: E3044 x10; final P x10. Both tests warning-free under -strict.

7. **PR text issues (1)-(10): false const-volatile claim, 'two different unions' overclaim, missing comparison gap, wrong overload risk text, 790 = 158x5 not 159, repro corpus count meaningless upstream, 87 add_menu not reproducible, 'about 20 call sites', 'were reviewed', footer style** (fixed)

   All applied in the new pr_body: cv claim narrowed to the typedef form; compatibility rule stated; comparison/subtraction now fixed and described; overload changes (f01/f02/cx4b) described as behaviour changes for existing programs; '158 existing autotest programs (790 configurations)'; repro corpus dropped; add_menu count replaced by 'dozens' (grep finds 86 lines in port/src, not 87); call-site count removed (14 outside IsSubType itself by grep, reviewer counted 13); 'reviewed' sentence replaced by a plain AI-assistance statement. Footer: the attribution lines required by this session are kept at the end; Jolyon may delete the private session link before posting.

8. **Patch newly accepts distinct union types (tagless or same tag); called a regression** (rejected)

   Behaviour confirmed (cx1: typedef union{int i;} A, B; const B* from A*: E3012 -> P x10) but it is not a regression relative to how Oscar64 treats structs: cx1s (same code with struct) is P x10 on 4da3147 and v1.32.273. The patch makes unions follow the existing struct identity rule; a stricter rule for both is a separate change. Same conclusion as Opus finding 4. Stated plainly in the PR.

9. **Multilevel qualification: union U** -> const union U** accepted via the recursive pointer comparison** (out-of-scope)

   Reproduced exactly as hypothesised: cx2_multilevel.c E3012 -> P x10. But cx2i (int** -> const int**) and cx2s (struct) are P x10 on 4da3147 and v1.32.273: the recursion in IsSubType (Declaration.cpp:2811-2815) already accepts this for every pointee type. Pre-existing laxity, not introduced by the union change; a fix would belong in the pointer branch for all types. Listed in adjacent_bugs and in the PR's limitations.

10. **Regression test omits return, cv init/assign, vp = mp, partially qualified sources, shadowed tags, completion-order cases; read_typedef reads an inactive member; no persistent negatives** (fixed)

   Return, cv (via typedef) in argument/initialisation/assignment, vp = mp, const->cv and volatile->cv (cx5/i5: E3012 before) added; read_typedef now returns p->i. Shadowed tag (cx3) confirmed accepted after the fix, identical to the struct behaviour (cx3s P before), so it is documented rather than asserted. Completion-order: probe_incomplete (const, completed later) E3018 -> P; b09 (volatile variant) still fails, stated. Negatives cannot use the success-only runners (autotest.bat :test; the makefile's expected-diagnostic rules are bespoke per test), so the 17 negative probes stay as scratch checks and are listed in the PR.

11. **'Nothing in the generated code' and rejection claims need narrower wording; anonymous-union overload example might change selection** (fixed)

   PR now states exact identical-output counts instead of a blanket claim. Codex's choose() example does not parse in Oscar64 C++ (error 3026 'Invalid unnamed struct on global level', for struct and union, all three compilers). The named-namespace variant cx4b (choose(void*) vs choose(N2::U*) called with N1::U*) does change: base P (void*), final R1 (N2::U*), and the struct control cx4bs is R1 before and after, so it is the struct rule reaching unions; described in the PR as a C++ behaviour change.

12. **PR factual corrections: not every union comparison returned false; 795 attempted vs 790 comparable; remainder of the repro corpus unexplained; separate committed vs scratch coverage** (fixed)

   Root-cause wording now says the identity shortcut matched only the same Declaration object; validation lists attempts, both-compile, identical and both-fail counts with the both-fail files named; committed tests and hand-checked negatives are described separately.

</details>

## Last round: final-check findings and what happened to them

Changed in the last round: test. Commit before it: `f2f7715ca3f8`.

| From | Severity | Finding | Resolution |
|---|---|---|---|
| codex final check #1 | low | PR root-cause text ('fell to the IsSubType rank') describes the intermediate IsSubType-only fix, not the baseline; commit message had the same slip | fixed |
| codex final check #2 | low | No const-volatile return function in autotest/unionptrconsttest.c although the PR claims return coverage for const volatile | fixed |
| codex final check #3 | low | PR 'every one fails on the unmodified compiler' wrongly includes the struct control | fixed |
| codex final check #4 | low | Private claude.ai session URL in PR footer and commit Claude-Session trailer | left-for-jolyon |
| codex final check (closing note) | low | Acceptance of distinct same-tag or tagless unions remains a new regression for unions | rejected |

<details><summary>Evidence, and what was re-run</summary>

1. **PR root-cause text ('fell to the IsSubType rank') describes the intermediate IsSubType-only fix, not the baseline; commit message had the same slip** (fixed)

   Parser.cpp:8917-8923: for a U* argument and f(const U*), IsSame, IsSameMutable (struct-only branch) and IsSubType (union returned false) all fail on 4da3147, so the candidate is NOOVERLOAD and f(const void*) (IsSubType rank, +256) is called: review probe f01_ovl_void.cpp base = emulation result 1, fix = 0 (re-run /home/jolyon/nethack64/build/oscar64-wt/r15-union-const-scratch/final). With IsSubType fixed alone the union candidate lands at +256 and ties (E3045, per round-1 evidence). PR root-cause paragraph and commit message now say: not viable at all on the unmodified compiler so f(const void*) is called; fixing IsSubType alone would tie them; the IsSameMutable change gives the qualification conversion its proper rank (+2).

2. **No const-volatile return function in autotest/unionptrconsttest.c although the PR claims return coverage for const volatile** (fixed)

   Added `static volatile CValue* keep_const_volatile(union Value* p) { return p; }` and `assert(keep_const_volatile(&w)->i == 4321);` (+6 lines). Isolation probe /home/jolyon/nethack64/build/oscar64-wt/r15-union-const-scratch/final/i12_cv_return_only.c: E3018 x10 on 4da3147 and v1.32.273, P x10 on the fix. Whole test: E3012 x10 before, P x10 after; warning-free under -strict (-bc and -n). Matrix in /home/jolyon/nethack64/build/oscar64-wt/r15-union-const-scratch/final/matrix.txt.

3. **PR 'every one fails on the unmodified compiler' wrongly includes the struct control** (fixed)

   Struct control (read_struct, probe f01s etc.) passes before and after by design. PR sentence now says each new union construct was checked in isolation and fails before / passes after, and states separately that the struct control passes on both compilers.

4. **Private claude.ai session URL in PR footer and commit Claude-Session trailer** (left-for-jolyon)

   Per the round rules the commit trailers (Co-Authored-By, Claude-Session) were not changed. The PR body returned here carries the AI-assistance sentence and no claude.ai link, as the task asked; Jolyon decides the trailers for all branches at once.

5. **Acceptance of distinct same-tag or tagless unions remains a new regression for unions** (rejected)

   Not re-litigated: struct controls cx1s/e01s/cx3s/e05s pass on 4da3147 and v1.32.273 (round-1 and fix-up evidence), so the patch applies the existing struct identity rule to unions; the PR states this plainly under behaviour changes. Codex itself says the PR adequately discloses it.

**Re-validation.** Only autotest/unionptrconsttest.c changed (+6 lines); oscar64/*.cpp untouched (git diff --stat 4da3147 HEAD: Declaration.cpp 8 +-, same as before). Rebuilt bin/oscar64 with make -C make -j6 compiler. Ten-configuration matrix (-ea -g {-bc,-n} x {default,-O2,-O0,-Os,-O3}) on base 4da3147 / pinned v1.32.273 / fix: unionptrconsttest.c E3012 x10 / E3012 x10 / P x10; unionptroverloadtest.cpp E3044 x10 / E3044 x10 / P x10; new isolation probe i12_cv_return_only.c E3018 x10 / E3018 x10 / P x10. Both tests warning-free under -strict in -bc and -n. Full autotest on the final tree (make -k -j4 -C .../r15-union-const/make check, log /home/jolyon/nethack64/build/oscar64-wt/r15-union-const-scratch/autotest-final.log): autotest_diff.py vs autotest-base-4da3147.log: emulations base 1541, new 1561 (20 from the two new tests), new failures 0, fixed 0, failing in both 0, exit 0. corpus_diff not re-run: no compiler source changed since the fix-up round's run (182 files x 5, 840/840 identical; samples 332/333 identical, the one explained by include-path length). Branch: one commit 7024085 on 4da3147, working tree clean.

</details>

## Final check (Codex, read-only, on the final commit)

<details><summary>SUBMIT AFTER CHANGES</summary>

VERDICT: SUBMIT AFTER CHANGES

1. **[low] PR root-cause explanation: “a union pointer argument fell to the `IsSubType` rank instead.”** This describes the intermediate `IsSubType`-only fix, not the baseline. The supplied evidence says baseline selects `const void *`, whereas the intermediate fix produces ambiguity. Say: “Fixing `IsSubType` alone makes the union overload viable but equally ranked with `const void *`; updating `IsSameMutable` gives qualification conversion its proper preference.” Correct the corresponding commit-message explanation too.

2. **[low] `autotest/unionptrconsttest.c`, return tests; PR: “return forms with … const volatile.”** There is no const-volatile return function. Add a `volatile CValue *` function returning its `union Value *` parameter and assert its result, or narrow the coverage claim to const and volatile returns.

3. **[low] PR: “Each case was also checked on its own: every one fails on the unmodified compiler.”** This includes the explicitly listed struct control, which passes before the fix. Replace “every one” with a precise reference to the isolated union regression probes; distinguish those from control assertions.

4. **[low] PR footer and commit `Claude-Session` trailer.** Remove the private session URL before publication. It provides no accessible evidence to the maintainer; the AI-assistance attribution can remain.

The supplied diff addresses the earlier predicate gaps, and the tests guard them. Acceptance of distinct same-tag or tagless unions remains a **new regression for unions**, even though structs already behave that way. The PR adequately discloses this accepted compatibility tradeoff; the earlier finding was not technically disproved.

</details>

## Before submitting

- Make the AI-assistance line the same in every PR body (some end with a sentence, some with a "Generated with Claude Code" footer), as Jolyon decides.
- Commit trailers: drop the `Claude-Session:` line and use one `Co-Authored-By:` line, as Jolyon decides for all PRs (see OSCAR64-UPSTREAM.md).

## Risks and limitations

Unchanged from the fix-up round: unions now follow the struct compatibility rule (same member scope, or same unqualified tag / both tagless with equal size), so distinct same-tag or tagless unions convert where they were rejected; C++ overload resolution now prefers f(const U*) over f(const void*)/f(...) and a same-named union from another namespace can beat void*; a user-declared union copy constructor is now called. Generated code for all 158 existing autotest programs byte-identical in 790 configurations; samples identical except the known include-path quirk. Pre-existing and not fixed: const union value initialisation, volatile prototype declared while incomplete, 'const volatile union' spelt directly parsed as unqualified, multilevel qualification laxity. The commit trailer still carries the private session link (Jolyon's call).

## Related bugs found, not fixed here

(a) Parser.cpp:830-833 applies only exactly one added qualifier after a struct/union tag: 'const volatile union u *' and 'const volatile struct s *' are parsed as unqualified, so writes through them compile and volatile loads are dropped (b07, c02, c02s, j01); present in v1.32.273; no 'const volatile' in nethack64 src/ or port/. (b) The mVolatile copy of an incomplete struct/union is not updated on completion (Parser.cpp:680-681 updates only mConst): member access through a 'volatile' pointer declared before completion is error 3005 for structs and unions (b01), and the volatile-union prototype case b09 still fails to convert after this fix. (c) IsSubType's pointer recursion lets a pointee gain a qualifier at any depth (int** -> const int**, struct and union alike; g01, cx2), and the conditional operator's result type drops const (a07); pre-existing for all types. (d) Struct compatibility by unqualified tag + size accepts distinct same-tag or tagless structs (e01s, cx1s, cx3s, e05s), now inherited by unions. (e) 'const union u c = v;' aggregate value initialisation errors 3012 (CanAssign struct-only branch ~Declaration.cpp:3290); struct works. (f) A union with a user-declared default constructor 'U() { i = 0; }' crashes the compiler (exit 139) in 4da3147, v1.32.273 and with this fix (k05, k06). (g) IsSameMutable ignores volatile, so an overload taking U*/struct S* is selected for a volatile argument and then fails with 3012 instead of 3044 (k01, k01s). (h) C++ mode rejects a tagless union/struct typedef at file scope with error 3026 (cx4). (i) -bc output embeds include paths, so compilers in different directories produce different bytes for some programs (splitscreen, testint16mul).

## Draft pull request

**Title:** Fix union pointer to const union pointer conversion

````markdown
A pointer to a union cannot gain a qualifier: passing, assigning, returning or initialising a `const union T *` or a `volatile union T *` from a `union T *` is rejected, while the same conversion works for struct and scalar pointers (C89 3.3.16.1 / 3.3.2.2, C99 6.5.16.1 / 6.5.2.2).

```c
union u { int i; char c; };

static int get(const union u *p)
{
	return p->i;
}

int main(void)
{
	union u v;
	v.i = 0;
	return get(&v);
}
```

Reproduce with `oscar64 -ea -g -n example.c` (same with `-bc` and at every optimisation level). Observed: `error 3012: Cannot assign incompatible types 'const union u*' != 'union u*'`. Expected: compiles and runs, emulation result 0. Assignment and initialisation fail the same way, `return p;` from `union u *` to `const union u *` gives error 3018, and `cp == mp` or `cp - mp` between a `const union u *` and a `union u *` is rejected too. Replacing `union` by `struct` compiles in every case. In C++, `f(&v)` with overloads `f(const U *)` and `f(const void *)` compiles but calls `f(const void *)`, and `g(v)` with `g(const U &)` and `g(int)` is error 3044.

Root cause: `Declaration::IsSubType` returns `false` unconditionally for `DT_TYPE_UNION`. A qualified union type is a separate `Declaration` made by `ToConstType` / `ToVolatileType`, so the `this == dec` shortcut at the top only matches the identical declaration object, and unlike `DT_TYPE_STRUCT` / `DT_TYPE_ENUM` there is no tag/scope comparison to fall back on. `CanAssign` and argument matching reach the pointee through `IsSubType`. `IsSameMutable` and `IsConstSame` have the same gap: their struct branch has no union case, so they fall through to `return false`. `IsConstSame` decides whether two pointers may be compared (C mode) or subtracted and whether a constructor taking `const U &` is the copy constructor. `IsSameMutable` is the rank for a pointer or reference that only gains a qualifier in overload resolution; with it and `IsSubType` both failing, `f(const U *)` is not viable at all for a `U *` argument, so `f(const void *)` is called. Fixing `IsSubType` alone would make the union overload viable but rank it with the `IsSubType` cost, the same as the conversion to `const void *`, and the call would become ambiguous; the `IsSameMutable` change gives the qualification conversion its proper preference.

The fix adds `DT_TYPE_UNION` to the struct branch of these three predicates (three lines changed, the unconditional union `return false` in `IsSubType` removed). The base-class walk in `IsSubType` stays guarded by `mType == DT_TYPE_STRUCT`, and the qualifier check above it still rejects dropping `const` or `volatile`. Unions now follow the struct rule exactly: two union types are compatible when they share the member scope, or when they have the same unqualified tag (or both have none) and the same size.

Tests. `autotest/unionptrconsttest.c` covers the argument, assignment, initialisation and return forms with `const`, `volatile` and const volatile (as `volatile` applied to a `typedef const union`), a typedef'd union, a pointer that already has one qualifier gaining the other, `==`, `!=`, `<`, `>` and subtraction between qualified and unqualified pointers, an array of pointers to const union, and a struct control. `autotest/unionptroverloadtest.cpp` covers overload resolution with a union pointer against `const void *`, an ellipsis and `int`, binding `const U &` to a `U` lvalue, pointer comparison, and a union with a user-declared copy constructor. Both are registered in `autotest.bat` and picked up by the makefile. Each new union construct was also checked in isolation: each one fails on the unmodified compiler (3012, 3018, 3044, or the wrong overload being called) and passes after the fix in all ten `-ea -g {-bc,-n} x {default,-O2,-O0,-Os,-O3}` configurations; the struct control passes before and after. Negative checks, done by hand because they must not compile: `const union u *` to `union u *`, `volatile union u *` to `union u *`, const volatile to either, `union w *` to `const union u *`, a write through the const pointer, and an overload that would drop `volatile`, in C and in C++, all still fail.

Validation against main `4da3147` on Linux, targeting C64:

- Full autotest (`make -k -j4 -C make check`): 1541 successful emulations on the baseline, 1561 with the patch and the two new tests, 0 failures in either.
- The 158 existing single-file autotest programs build byte-identical `.prg` files before and after in `-n -O0/-O2/-O3/-Os` and `-bc -O2` (790 configurations); the two new tests go from error to ok in all five.
- The 68 programs under `samples/` in the same five configurations: 333 build with both compilers, 332 are byte-identical; the one difference (`hires/splitscreen.c`, `-bc -O2`) is the include-path length showing up in the bytecode debug strings, since an unpatched compiler built next to the patched one produces identical bytes. 7 configurations fail with both compilers (`memmap/tsr.c`, and the two `func3d.c` at `-O0`).

Behaviour changes to be aware of, all of them the struct behaviour applied to unions:

- Distinct unions with the same unqualified tag (in another block scope, namespace or class) or with no tag and the same size now convert where they were rejected before. Oscar64 already treats structs this way; a stricter rule would be a separate change for both.
- C++ overload resolution: a `U *` argument now picks `f(const U *)` over `f(const void *)` or `f(...)` where it previously compiled and called the latter, and an overload on a same-named union from another namespace can now be preferred over `void *`.
- A user-declared union copy constructor is now recognised and called; before, the union was copied bitwise.

Not changed by this patch: initialising a `const union` value from a `union` value (`const union u c = v;`) still errors, because `CanAssign` has a struct-only branch for aggregate values; a `volatile union u *` prototype written while the union is incomplete still does not convert after completion (the volatile copy is not updated on completion, which also breaks member access for structs); `const volatile union u *` written directly is parsed as an unqualified pointer (the parser applies only one added qualifier after a struct or union tag; pre-existing, affects structs too); and `union u **` to `const union u **` is accepted, as it already is for `int **` and struct pointers.

Found while porting NetHack 3.4.3 to the C64, which passes `&any` to a `const ANY_P *` parameter in dozens of `add_menu` calls. Prepared with AI assistance (Claude Code); the numbers above come from running the stated commands on this branch.
````
