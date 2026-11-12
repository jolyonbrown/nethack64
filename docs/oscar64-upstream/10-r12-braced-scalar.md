# 10. Fix braced initializer for scalar variables

| | |
|---|---|
| Branch | `fix/r12-braced-scalar` in `~/src/oscar64-dev`, commit `76841d2efdbf`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/10-r12-braced-scalar.patch`](../../tools/oscar64-upstream/patches/main/10-r12-braced-scalar.patch) |
| Kind | rejects valid C |
| Since | v1.32.273 and main |
| NetHack | Compat #16 (repro r12): `decl.c` `occtxt = DUMMY`, where `DUMMY` is `{ 0 }`. Workaround: `= 0` in `port/` (T1.12). |
| Reviews | Opus (round 1, ran probes): submit-after-changes, 0 high, 1 medium, 5 low; Codex (read the diff): submit after changes; fix-up: ready; final Codex check: submit after changes |
| Recommendation | **Submit.** |

## In plain words

In C you are allowed to write the starting value of a plain variable inside curly braces, `int n = { 3 };` meaning the same as `int n = 3;`. NetHack does this through a macro (`#define DUMMY { 0 }`), so the C64 port hit it immediately. Oscar64 treated the braces as the start of a list for an array or struct and then could not use that list for a simple variable, so it reported a confusing error as soon as the variable was used anywhere. The fix teaches the two places in the parser that read a simple variable's initial value to accept, and discard, one pair of braces around it, to allow the trailing comma C permits, and to give a clear error if more than one value is inside. Two new test programs exercise the C forms and the C++ forms that go through the same code. This last round only corrected wording: the PR's example of a wrong program had a stray semicolon, and the commit message overstated that braced and unbraced forms always compile to exactly the same bytes, which is true for variable declarations but not for two C++ forms that build a temporary.

## The fix

Parser.cpp: the scalar branches of ParseConstInitExpression and ParseVarInitExpression consume an optional `{` before the initializer expression and an optional trailing comma plus `}` after it; more than one expression is reported once as "Too many initializers for scalar" (EERR_CONSTANT_INITIALIZER) with the rest of the list skipped, a missing `}` as "'}' expected". ParseVarInitExpression takes the brace only when no prefix expression was parsed. 26 added lines, nothing removed. This round changed only text: the commit message's generated-code claim is now qualified (declaration forms byte-identical; C++ braced call arguments and functional casts go through a temporary and can differ at low optimization levels), the PR body's negative example is `int x = { 1, 2 };`, and the twin bullet states precisely where the call-argument/functional-cast code differs.

## Regression test

autotest/scalarbraceinittest.c (116 lines: global, static, static-local and local int/char/long/float/pointer scalars with braced initializers, trailing comma, `int a = { (1, 2) }, b = { 3, };`, run-time and side-effecting initializers evaluated once, scalar compound literals, braced scalar members of structs and arrays with and without brace elision) and autotest/scalarbraceinitcpp.cpp (50 lines: default member initializers, member initializer lists, braced call arguments, functional casts, in-class static const, template T x = { v }), both registered in autotest/autotest.bat after ptrinittest.c. Before: 0/13 configurations pass (C: error 3006; C++: 3058/3060). After: 13/13 pass with "Emulation result 0".

## Evidence

**Repro matrix.** Ten configurations oscar64 -ea -g {-bc|-n} x {default,-O2,-O0,-Os,-O3}; before = ~/src/oscar64-base (4da3147), after = final worktree bin/oscar64 (43616db), pinned = v1.32.273. Harness /home/jolyon/nethack64/build/oscar64-wt/r12-braced-scalar-scratch/fx/run10.sh.
- tests/oscar64-repros/r12_braced_scalar_initializer.c (`const char *p = { 0 }; return p == 0 ? 0 : 1;`): before 10/10 error 3008; after default/-O0 pass (4/10), -O2/-Os/-O3 'Execution failed' (6/10); pinned 10/10 3008. The 6 failures are the separate null-pointer-compare bug: unbraced twins np4 (`p == 0`), np1 (`assert(!p)`), np2 (`return !p ? 0 : 1`) fail the same 6 on before, after and pinned; np3 (`p ? 1 : 0`) passes 10/10 everywhere.
- autotest/scalarbraceinittest.c: before 0/10 (3006), after 10/10, pinned 0/10; +3 extra .bat configurations pass.
- autotest/scalarbraceinitcpp.cpp: before 0/10 (3058/3060), after 10/10, pinned 0/10; +3 extra pass.
- PR example fx/ex2.c: before 10/10 fail (3058+3012 for m, 3008 for p and n; without m: 3008 for p and n), after 10/10, pinned 0/10.
- Codex cases: cx1 `int a = { (1, 2) }, b = { 3, };` 3006 -> 10/10; cx3 `int x = { source++ }` 3058 -> 10/10; cx2 global `struct T t = { 1, 2, { 3 } }` and `struct U u = { { 5 }, 6, 7 }` 3008 -> 10/10; cx2 local `{ 1, 2, { 3 } }` fails before and after, as does its unbraced twin `{ 1, 2, 3 }` on 4da3147 (pre-existing); local fully braced `{ { 1, 2 }, { 3 } }` and `{ 1, { 2 }, 3 }` 3058 -> 10/10; cx4 statics of const char*/long/float 3008 -> 10/10.
- Codex narrowing: nar1 `int b = { 1.5 }` (.cpp) 3058 -> 10/10; nar3 `int c{1.5};` 10/10 on before, after and pinned (no narrowing check exists); nar2 `int a = 1.5;` 10/10 everywhere.
- Opus probes re-run on the final compiler: a01..a06, a07c, a08, k01_constexpr2, k02_prefix, c01, c02, c03, c04, c09, c10, c14, c15, c17: all fail before, 10/10 after. Unchanged before/after: c05 return {3}, c06/w2 reference, c08 auto, c12 new int{5}, c13 int x{} , v1-v4 empty braces, s01 char s[] = {"abc"}, k01_constexpr (its unbraced twin k01u also fails), x1 global reference. Pre-existing and identical to unbraced twins: a07/a07b (local brace elision + DefaultInitExpression), e01/e01b/e02 (__striped in -bc, __zeropage at default/-O0; e01b matches e03_unbraced exactly), c07 (`int g{3}` reads 0 at default/-O0), c11 (`B b = {3}` skips constructor), d07/d11, w1 (3058 -> 3015, same as its unbraced twin).
- Byte identity (final compiler, 10 configurations each): C twin fx/tw1b.c vs tw1u.c identical 10/10; C++ declaration twin tw3b/tw3u identical 10/10; C++ call-arg/functional-cast twin tw4b/tw4u identical 7/10, differs at -bc default, -bc -O0, -n -O0 (temporary built), runs correctly 10/10.

**Autotest.** make -k -j4 -C /home/jolyon/nethack64/build/oscar64-wt/r12-braced-scalar/make check > /home/jolyon/nethack64/build/oscar64-wt/r12-braced-scalar-scratch/autotest-fixup.log (run after the final rebuild, via nohup, waited in the foreground). autotest_diff.py autotest-base-4da3147.log autotest-fixup.log: emulations base 1541, new 1561 (+20 = scalarbraceinittest.c and scalarbraceinitcpp.cpp x 10 configurations, both present 10 times in the log); new failures 0; fixed 0; failing in both 0; 0 non-zero 'Emulation result' lines; no 'make: ***' or ' : error ' line in the log (the exit status itself was not captured because of nohup). testint16mul.c quirk did not appear.

**Corpus.** corpus_diff.py ~/src/oscar64-base/bin/oscar64 <worktree>/bin/oscar64 --out <scratch>/corpus-fixup -j4, run alone after make check had finished: 180 files x 5 configurations (n-O2, n-Os, n-O0, n-O3, bc-O2) = 900 pairs. both compile: 830, identical: 830, different: 0. status changed: 15, all error -> ok: autotest/scalarbraceinitcpp.cpp (5), autotest/scalarbraceinittest.c (5), oscar64-repros/r12_braced_scalar_initializer.c (5), i.e. only files that use the construct. both fail: 55 = 11 nethack64 repro files for other bugs (r2, r3, r5, r6, r7, r8, r10, r11, r13, r15, r16) x 5. Split: the 158 pre-existing upstream autotest files x 5 = 790 pairs, 790 compile with both, 790 byte-identical, 0 different, 0 status changes; the 20 local repro files: 1 changed (r12), 11 both-fail, 8 identical in all 5. Script exit 1 only because status changes exist. Output: /home/jolyon/nethack64/build/oscar64-wt/r12-braced-scalar-scratch/corpus-fixup.txt. (r21/r22 appeared in tests/oscar64-repros during this session, after the corpus run, and are not counted.)

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| opus | medium | PR text and test understate the scope: compound literals and five C++ paths are also changed | fixed |
| opus | low | Diagnostics: unclosed brace misreported as 'Too many initializers', excess initializers cascade, two error codes for one message | fixed |
| opus | low | The `auto` guard is dead code and the PR credits it for unchanged auto behaviour | fixed |
| opus | low | Numbers and example claims in the PR body do not match the runs (1,549 vs 1,551; `p` unreferenced; 18 private repro files) | fixed |
| both | low | The new test silently works around a separate null-pointer comparison bug and the PR does not disclose it | fixed |
| opus | low | Private claude.ai session URL in commit trailer and PR footer would enter upstream history | deferred |
| opus | low | Negative cases could be an expected-diagnostic autotest target (enumrangeconstraints exists) | deferred |
| codex | medium | C++ list-initialization narrowing rules are not enforced for the newly accepted forms | out-of-scope |
| codex | low | Test misses token-boundary, brace-elision and single-evaluation cases | fixed |
| codex | low | Displayed reproducer never references `p`; static coverage is int-only; byte identity overstated | fixed |

<details><summary>Evidence for each finding</summary>

1. **PR text and test understate the scope: compound literals and five C++ paths are also changed** (fixed)

   Confirmed by reading (all callers of ParseConstInitExpression/ParseVarInitExpression hand the '{' through unconsumed: ParseCastExpression 7798/7829, ParsePostfixExpression 9587, ParseListExpression 11565, BuildMemberInitializer 3031, class members 6962) and by running: p/a01 (local (int){k+1}, &(int){3}) 3058 -> 10/10; p/a02 (file-scope &(int){5}) 3008 -> 10/10; cpp/c02 meminit x{v}, c03 f({3},{4L}), c04 int{k}, c09 NSDMI, c10 template T x = {v}, c14 constexpr, c15 enum class: all 3058/3060/3009 -> 10/10. Added local and file-scope compound literals to autotest/scalarbraceinittest.c and a new autotest/scalarbraceinitcpp.cpp (NSDMI, member initializer list, braced call arguments, functional casts, in-class static const member, template); both 0/10 before, 10/10 after, registered in autotest.bat. PR body now lists these forms and the ones still rejected (return {3}, const int &r = {g}, new int{5}, char s[] = {"abc"}, {} value-init).

2. **Diagnostics: unclosed brace misreported as 'Too many initializers', excess initializers cascade, two error codes for one message** (fixed)

   Reproduced with the original fix: `int g = { 3 ;` gave 3008 'Too many initializers for scalar' (before: 3006 ''}' expected'); `int g = { 1, 2 };` gave 5 errors (before 1); grep shows the other 7 errors in ParseVarInitExpression use EERR_CONSTANT_INITIALIZER, so EERR_INVALID_INITIALIZER did not follow the surrounding code. Evaluated and adopted Opus's alternative (consume comma; if not at '}', report once and skip the remaining expressions with ParseRExpression/ParseExpression; then ConsumeToken(TK_CLOSE_BRACE)), both branches using EERR_CONSTANT_INITIALIZER. Final compiler: {1,2}, {1,2,3,4}, {1,2,} and member/array/compound-literal variants each give exactly 1 error 3008 in both paths (ng1,ng2,ng5,ng7,ng8,ng12,b14,b20,b26,b28,b29); unclosed brace gives 3006 ''}' expected' (ng3,ng4); `{ }` unchanged (2 errors, identical to 4da3147); unreferenced `int g = {1,2};` was silently accepted on 4da3147 and is now rejected. Byte-identity of positive code unchanged (see twins).

3. **The `auto` guard is dead code and the PR credits it for unchanged auto behaviour** (fixed)

   Confirmed by reading: the if-chain has `else if (dtype->mType == DT_TYPE_AUTO || dtype->mType == DT_TYPE_REFERENCE)` at Parser.cpp:2528 before the final else, so the guard can never see DT_TYPE_AUTO. Dropped it. cpp/c08 `auto n = { 4 };` still 3058 before and after; braced/unbraced twins byte-identical 10/10. PR text now attributes auto/reference behaviour to the earlier branch.

4. **Numbers and example claims in the PR body do not match the runs (1,549 vs 1,551; `p` unreferenced; 18 private repro files)** (fixed)

   grep -c 'Emulation result' on the author's log gives 1551 (baseline 1541) and the makefile rule runs 10 configurations; pr/example_nolocal.c on 4da3147 reports only `n` (3008) because `p` is unreferenced. New example (scratch fx/ex2.c) reads p through a local copy: before = 3058+3012 for m, 3008 for p, 3008 for n; without m = 3008 for p and n; after = 10/10 (also pinned 0/10). PR now reports my own re-run (1,541 -> 1,561) and separates the 158 upstream autotest files from the 20 local repro files in the corpus numbers.

5. **The new test silently works around a separate null-pointer comparison bug and the PR does not disclose it** (fixed)

   Reproduced: `const char *p = 0; assert(p == 0);` (fx/np4) fails at -O2/-Os/-O3 on 4da3147, the fix and v1.32.273 alike; so does `!p` (np1/np2), contradicting Opus's note that `!p` is correct; only `p ? 1 : 0` (np3) is right 10/10. The r12 repro therefore still fails 6/10 after the fix for this unrelated reason. Added a comment above `t = gs;` in the test and a 'Known limitation' paragraph in the PR; the example also uses a local copy and says why.

6. **Private claude.ai session URL in commit trailer and PR footer would enter upstream history** (deferred)

   Jolyon's call. The task said to keep the existing trailer lines as they are, so the commit still carries Co-Authored-By and Claude-Session; the PR body keeps the required attribution footer and adds a plain 'prepared with AI assistance (Claude Code)' sentence. Opus is right that no upstream commit carries such trailers; dropping the URL is a one-line edit before opening the PR.

7. **Negative cases could be an expected-diagnostic autotest target (enumrangeconstraints exists)** (deferred)

   True: autotest/makefile and autotest.bat have warningstackconstraints/enumrangeconstraints/c23enumconstraints targets. The task asked for negative cases as scratch probes; adding a two-platform diagnostic target doubles the test surface of a small PR, so it is left as an optional follow-up and the probes are reported here (12 ng*.c plus 6 Opus neg/ files, all exit 20).

8. **C++ list-initialization narrowing rules are not enforced for the newly accepted forms** (out-of-scope)

   Reproduced: `int b = { 1.5 };` compiles after the fix (nar1 10/10). But Oscar64 has no narrowing check anywhere: the untouched direct-brace path `int c{1.5};` (nar3) compiles on 4da3147 and v1.32.273, `int a = 1.5;` compiles with no warning, and struct aggregate `S s = { 1.5, 300 };` is likewise unchecked. The patch gives braced scalars the same conversion as every other initialization path; adding narrowing diagnostics is a separate feature across all list-init paths, and rejecting it here would wrongly reject valid C (nar6_c.c). Disclosed under 'Not changed' in the PR.

9. **Test misses token-boundary, brace-elision and single-evaluation cases** (fixed)

   Added `int lcm = { (1, 2) }, lcm2 = { 3, };`, `volatile int source = 7; int lonce = { source++ }; assert(lonce == 7 && source == 8);`, file-scope `struct T gtt = { 1, 2, { 3 } };` and `struct S gse = { 1, { 2 }, 3 };`, local `struct T ltt = { { 1, 2 }, { 3 } };` and `struct S lse = { 1, { 2 }, 3 };`. Codex's local `struct T lt = { 1, 2, { 3 } };` fails (3006) but so does its unbraced twin `{ 1, 2, 3 }` on 4da3147 (fx/cx2f): a pre-existing local brace-elision bug, listed in adjacent_bugs, not added to the test. Negative checks for both parser paths were run as scratch probes (ng1..ng12): all rejected with exactly one error; unclosed brace now reports ''}' expected'.

10. **Displayed reproducer never references `p`; static coverage is int-only; byte identity overstated** (fixed)

   Example rewritten (see above). Added `static const char* sgs = { 0 };`, `static long sgl = { 123456L };` and a static-local `long` to the test. Byte identity re-measured on the final compiler: C twin (globals, statics, locals, run-time and side-effecting initializers, struct members) identical 10/10; C++ declaration twin (NSDMI, meminit, static const member, template, global, local) identical 10/10; the C++ call-argument/functional-cast twin differs in 3 of 10 configurations (-bc, -bc -O0, -n -O0: a temporary is built) and runs correctly in all 10. PR states exactly this.

</details>

## Last round: final-check findings and what happened to them

Changed in the last round: text-only. Commit before it: `43616db1557f`.

| From | Severity | Finding | Resolution |
|---|---|---|---|
| final-check Codex #1 | low | PR body example `int x = { 1, 2; }` has a misplaced semicolon and does not give one error | fixed |
| final-check Codex #2 | low | Commit message claim 'The generated code is the same as for the unbraced form' is broader than the evidence | fixed |
| self (this round) | low | PR body said call-argument/functional-cast code differs only 'at -O0 and -bc default' | fixed |
| self (this round) | low | Re-verified the remaining numeric claims in the PR body; no inaccuracy found | rejected |
| task rule | low | Co-Authored-By model name / Claude-Session trailer and claude.ai link in the PR footer | left-for-jolyon |

<details><summary>Evidence, and what was re-run</summary>

1. **PR body example `int x = { 1, 2; }` has a misplaced semicolon and does not give one error** (fixed)

   Reproduced with the branch compiler (-ea -g -n): `int x = { 1, 2; };` gives 3 errors (3008 Too many initializers for scalar, 3006 '}' expected, 3006 Declaration starts with invalid token) at file scope and 5 in a function; `int x = { 1, 2 };` gives exactly one 3008 in both. PR body now reads `int x = { 1, 2 };`, matching the eight negative probes (file scope, local, struct member x2, array member, compound literal, two unclosed), each exactly one error (scratch final/check.log section D).

2. **Commit message claim 'The generated code is the same as for the unbraced form' is broader than the evidence** (fixed)

   Measured on the branch compiler in the ten configurations: declaration twins (global int, local run-time, struct with braced members, C++ NSDMI/member-init-list) are byte-identical 10/10; braced call arguments f({3},{4L}) vs f(3,4L) are identical only 4/10 (differ in all five -bc configurations and at -n -O0); functional casts int{k}/long{7} vs int(k)/long(7) differ at -O0 (both -bc and -n); all run with result 0. Commit message sentence replaced by: 'Braced and unbraced declaration initializers generate identical code (checked byte for byte on the tested forms); C++ braced call arguments and functional casts go through a temporary, as they did before for aggregates, so their code can differ from the plain form at low optimization levels.' Trailer lines unchanged.

3. **PR body said call-argument/functional-cast code differs only 'at -O0 and -bc default'** (fixed)

   Same measurement as above: call arguments differ in every -bc configuration (default, -O0, -O2, -Os, -O3) plus -n -O0, functional casts at -O0 only. Bullet reworded to state exactly that and that all ten run correctly.

4. **Re-verified the remaining numeric claims in the PR body; no inaccuracy found** (rejected)

   Both new tests: before 0/13 pass (E3006; E3058/E3060), after 13/13 in the autotest.bat configurations. autotest_diff.py baseline vs autotest-fixup.log: emulations 1541 -> 1561, new failures 0. Corpus (corpus-fixup): 166 autotest sources minus the 6 multi-file helpers the tool skips = 160 = 158 + 2 new; 158 x 5 = 790 .prg identical, repros 8 x 5 = 40 ok on both, 830 both-compile/830 identical, 15 status changes all error->ok on the construct. '26 added lines, nothing removed' matches git show --stat. Before-compiler messages on the PR example: 3058 then 3012 for the local, 3008 x2 for p and n; unreferenced `int n = { 3 };` compiles on 4da3147. Not-changed cases (int x{}; int x = {}; return {3}; new int{5}; char s[] = {"abc"}; auto x = {3}; const int &r = {g}) give the same error code before and after; int c{1.5} compiles on both, int b = { 1.5 } E3058 -> P as stated.

5. **Co-Authored-By model name / Claude-Session trailer and claude.ai link in the PR footer** (left-for-jolyon)

   Trailers kept byte-identical in the amended message. The PR body returned omits the claude.ai link footer as instructed; the AI-assistance sentence stays.

**Re-validation.** Text-only change (commit message and PR body); no rebuild needed and none done (bin/oscar64 from 06:16 is newer than Parser.cpp from 06:05 and matches the committed source, which is unchanged: `git diff --stat 43616db 76841d2` is empty). Re-ran as evidence for the text, all with the frozen base ~/src/oscar64-base/bin/oscar64 and the branch bin/oscar64 (script and log: /home/jolyon/nethack64/build/oscar64-wt/r12-braced-scalar-scratch/final/check.sh, check.log): (A) scalarbraceinittest.c and scalarbraceinitcpp.cpp in the 13 autotest.bat configurations: before 0 pass/13 fail each, after 13 pass/0 fail each. (B) six braced/unbraced twin pairs x 10 configurations: declaration forms 10/10 byte-identical (4 pairs), braced call arguments 4/10 identical (differ bc, O2bc, O0bc, O0n, Osbc, O3bc), functional casts 8/10 (differ O0bc, O0n); all 120 compiles run with result 0. (C) PR example on base: 3058+3012 (local) and 3008 x2; on the branch P in 10/10. (D) eight negative probes: exactly 1 error each (3008 x6, 3006 x2). (E) ten not-changed/narrowing probes: same code before and after except int b = { 1.5 } E3058 -> P, as the PR body states. Recorded evidence re-checked: autotest_diff.py baseline-4da3147 vs autotest-fixup.log = 1541 -> 1561 emulations, 0 new failures, 0 failing in both; corpus-fixup = 180 files x 5, 830 both compile, 830 identical, 0 different, 15 status changes (all error->ok on the two new tests and r12 repro). Full autotest and corpus were not re-run because no source or test file changed.

</details>

## Final check (Codex, read-only, on the final commit)

<details><summary>SUBMIT AFTER CHANGES</summary>

VERDICT: SUBMIT AFTER CHANGES

1. **low — PR body, “More than one expression (`int x = { 1, 2; }` …) is reported once”.** The example also contains a misplaced semicolon, so the patch can report both excess initializers and a missing closing brace. Change it to `int x = { 1, 2 };`, matching the probes actually reported.

2. **low — Commit message, “The generated code is the same as for the unbraced form.”** This is broader than the supplied evidence: C++ braced call arguments and functional casts sometimes generate different code. Qualify it as “The tested braced and unbraced declaration initializers generate identical code,” or include the exception already documented in the PR body.

No blocking code or regression-test issue found in the supplied material. The tests are valid for the stated language modes and exercise both changed paths. The earlier substantive fixes are reflected in the diff; treating narrowing and the independent pointer-comparison bug as separate work is reasonable. The execution results remain supplied evidence, not independently verified by this review.

</details>

## Before submitting

- Make the AI-assistance line the same in every PR body (some end with a sentence, some with a "Generated with Claude Code" footer), as Jolyon decides.
- Commit trailers: drop the `Claude-Session:` line and use one `Co-Authored-By:` line, as Jolyon decides for all PRs (see OSCAR64-UPSTREAM.md).

## Risks and limitations

Any program that relied on `{` after `=` for a scalar reaching the expression parser: none in autotest or the corpus (790/790 identical). The only acceptance changes are programs using the construct, plus an unreferenced `int g = { 1, 2 };`, silently accepted on main and now correctly rejected. C++: `int b = { 1.5 };` compiles without a narrowing diagnostic, consistent with Oscar64 having no narrowing check on any list-init path (`int c{1.5};` compiles on main). The error-recovery loop consumes a comma per iteration and ConsumeToken does not consume on a missing brace, so it terminates; 18 negative probes, none hangs or crashes. The null-pointer comparison miscompile (nethack64 r19) that hits NetHack's occtxt at -O2/-Os/-O3 is independent of this patch and still present; the test avoids it through a local copy and the PR says it will be reported separately. The pre-existing local brace-elision failure for `struct T lt = { 1, 2, 3 };` inside a function is not touched. Windows autotest.bat itself was not run (its 13 configurations were reproduced by hand on Linux); not tested on real hardware.

## Related bugs found, not fixed here

Pre-existing on 4da3147 (and, where checked, v1.32.273); none fixed here. (a) Null-pointer compare (nethack64 r19): a file-scope pointer initialised to 0 compared with 0, `!p` or `assert(!p)` yields 'not null' at -O2/-Os/-O3 (fx/np1, np2, np4); `p ? 1 : 0` is correct. Hits NetHack's occtxt. Opus's claim that `!p` is unaffected is wrong. (b) Local brace elision of an array or nested-struct member fails: `struct T { int a[2]; int b; }; struct T lt = { 1, 2, 3 };` inside a function gives 3006 'Declaration starts with invalid token' (fx/cx2f; also Opus's `struct O lo = { 4, 1, 2, 3 };`); the global form works. (c) DefaultInitExpression (Parser.cpp:2011) only zero-fills integer members: non-constant local struct initializer omitting a pointer/float/struct member gives 3058 'Invalid initializer' (Opus q1/q2, a07). (d) Anonymous struct members: wrong values for a brace-elided global (Opus h1); compiler segfault at -O2/-Os/-O3 for a local with a run-time value (h4). (e) Initialised __striped arrays read wrong values in -bc (e01/e03). (f) `__zeropage char zp = 5;` not initialised at default/-O0 (e02). (g) C++ `int g{3};` at file scope reads 0 at default/-O0 (c07c); `B b = { 3 };` skips B's constructor (c11). (h) Out-of-class static data member definition `int B::s = 4;` is rejected with 3023 'Duplicate variable declaration' regardless of braces (fx/sm_unbraced.cpp). (i) `char s[] = { "abc" };` (C99 6.7.8p14) rejected with 3008 (s01). (j) `int a[2] = { 1, 2, 3 };` gives the unhelpful ''}' expected' + 'Semicolon expected' rather than a too-many-initializers message. (k) A local declaration accepts trailing tokens / a missing ';' after a braced initializer (Opus u2-u4, t1-t13), also for arrays and structs on 4da3147.

## Draft pull request

**Title:** Fix braced initializer for scalar variables

````markdown
C allows the initializer of a scalar to be a single expression enclosed in braces (C89 3.5.7, C99 6.7.8p11). Oscar64 rejects it as soon as the variable is used:

```c
#include <assert.h>

const char *p = { 0 };
int n = { 3 };

int main(void)
{
	int m = { n + 1 };
	const char *t = p;
	assert(t == 0);
	assert(n == 3);
	assert(m == 4);
	return 0;
}
```

Reproduce with `oscar64 -ea -n example.c` (also with `-bc`, and at every optimisation level). Observed: `error 3058: Unexpected aggregate` (followed by 3012) for the local `m`, and `error 3008: Non constant initializer` for `p` and for `n`. An unreferenced `int n = { 3 };` compiles, which is why the problem only shows up once the variable is used. Expected: compiles, "Emulation result 0". The shape comes from NetHack 3.4.3, where `hack.h` defines `#define DUMMY { 0 }` and `decl.c` has `const char *occtxt = DUMMY;`.

**Root cause.** The scalar branches of `Parser::ParseConstInitExpression` (`Parser.cpp:2867` on 4da3147) and `Parser::ParseVarInitExpression` (`Parser.cpp:2616`) hand the initializer straight to the expression parser. For a `{` that builds an `EX_AGGREGATE` node (added for C++ aggregate initialisation in f0b9b5c), which nothing downstream can consume for a scalar: `InterCodeGenerator::InitGlobalVariable` reports "Non constant initializer" (`InterCodeGenerator.cpp:898`) when the global is emitted, `TranslateExpression` reports "Unexpected aggregate" (`InterCodeGenerator.cpp:6059`) for a local, and a braced scalar member of a struct or array initializer fails in `CopyConstantInitializer` with "Constant initializer expected".

**Fix.** Both scalar branches now consume an optional `{` before the expression, then an optional trailing comma and the `}`. More than one expression (`int x = { 1, 2 };`, a constraint violation) is reported once as "Too many initializers for scalar" and the rest of the list is skipped; a missing `}` is reported as "'}' expected". 26 added lines, nothing removed. `auto` and reference types take an earlier branch of `ParseVarInitExpression` and are not affected (`auto x = { 3 };` and `const int &r = { g };` are still rejected, as before).

Because the same two functions are reached from other places, scalar compound literals `(int){ 3 }` (local and file scope) and the C++ braced scalar forms that go through them now compile as well: default member initializers `int x = { 3 };`, member initializer lists `: x{v}`, braced call arguments `f({3})`, functional casts `int{k}`, in-class `static const int s = { 4 };` and `T x = { v };` in templates.

**Tests.** `autotest/scalarbraceinittest.c` covers file-scope, static, static-local and local `int`, `char`, `long`, `float` and pointer variables (statics of `int`, `long` and `const char *`), a trailing comma, `int a = { (1, 2) }, b = { 3, };`, a run-time initializer, an initializer with a side effect evaluated exactly once, scalar compound literals, and braced scalar members of structs and arrays, with and without brace elision around them. `autotest/scalarbraceinitcpp.cpp` covers the C++ forms listed above. Both are registered in `autotest.bat` (the makefile picks them up by itself). gcc `-std=c99 -pedantic` and g++ `-std=c++11 -pedantic` compile and run them. Negative cases (`int x = { 1, 2 };` at file scope, in a function, as a struct or array member and in a compound literal; `int x = { 3 ;`) were checked by hand: each gives exactly one error.

**Validation** against main 4da3147 on Linux, targeting C64, ten configurations (`-ea -g`, `-bc`/`-n` x default/`-O0`/`-O2`/`-Os`/`-O3`) plus the three extra ones in `autotest.bat` (`-O2 -xz -Oz`, `-O2 -Oo`, `-O2 -Ox`):

- `scalarbraceinittest.c`: before 0 pass / 13 fail, after 13 pass. `scalarbraceinitcpp.cpp`: before 0 / 13, after 13 / 13.
- Full autotest (`make -k -j4 -C make check`): 1,541 emulations on the baseline, 1,561 with the patch and the two new tests (10 configurations each); no failing step in either run.
- Every other `autotest/*.c` and `*.cpp` (158 files x 5 configurations: `-n` at `-O0`/`-O2`/`-Os`/`-O3` and `-bc -O2`): all 790 accepted by both compilers and all 790 `.prg` files byte-identical.
- Braced and unbraced twins of the declaration forms in the tests (C and C++) produce byte-identical `.prg` files in all ten configurations. C++ braced call arguments and functional casts build a temporary, as they did before for aggregates, so they are not byte-identical to the plain forms everywhere (call arguments differ in every `-bc` configuration and at `-O0`, functional casts at `-O0`); they run correctly in all ten.

**Known limitation.** The test compares the null-initialised pointers through a local copy (`t = gs; assert(t == 0);`). Comparing a file-scope pointer initialised to 0 directly with 0 (`p == 0`, `!p`) is miscompiled at `-O2`/`-Os`/`-O3` on main independently of this patch; the original NetHack repro still fails there for that reason. I will report that separately.

**Not changed.** C++ `int x{};` / `int x = {};` (value-initialisation), `return { 3 };`, `new int{ 5 }` and C99 6.7.8p14 `char s[] = { "abc" };` are still rejected as before. The C++ direct-brace path `int g{3};` goes through `ParseVariableInit` and is untouched. Oscar64 does not check list-initialisation narrowing on any path (`int c{1.5};` already compiles on main), so `int b = { 1.5 };` compiles too.

This change was prepared with AI assistance (Claude Code); all numbers above come from runs on the patched tree.
````
