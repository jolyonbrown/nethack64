# 14. Fix string literal to char * conversion in C

| | |
|---|---|
| Branch | `fix/r13-string-literal` in `~/src/oscar64-dev`, commit `5c850251d03b`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/14-r13-string-literal.patch`](../../tools/oscar64-upstream/patches/main/14-r13-string-literal.patch) |
| Kind | rejects valid C (by design upstream) |
| Since | v1.32.273 and main; the maintainer closed the same request as "As expected" (issue #90, 2024) |
| NetHack | Compat #17 (repro r13): `mail.c` `static char *junk[] = { "..." }`. Workaround: `const char *` (T1.12), one line. |
| Reviews | Opus (round 1, ran probes): submit-after-changes, 0 high, 1 medium, 3 low; Codex (read the diff): submit after changes; fix-up: ready; final Codex check: submit after changes |
| Recommendation | **Do not open as a PR now. The maintainer has already said this is intended, and our workaround is one line. If you want to argue it, comment on #90 with the C standard reference and offer the patch.** |

## In plain words

NetHack's mail.c has a table of quoted strings declared as plain `char *`, which every C compiler accepts because in C a quoted string is just an array of char. Oscar64 applied the C++ rule (array of const char) and rejected the table, local `char *p = "x"` variables, assignments and arguments. The fix makes the parser type literal characters as char when compiling C and leaves C++ alone; the string data is still stored as constant. The final check found two overstatements in the PR text, not in the code: one claimed byte-identical output for every program that compiled before (we only measured our corpus of 179 files, the 68 samples and the probes, so the text now says exactly that), and one said the only diagnostic lost was for writing into a string, when three other sloppy forms (unsigned char * from a literal, const-dropping ?:, and pointer-to-array mismatches) also slip through now because Oscar64 already accepted them for ordinary char arrays. The PR text now lists all of them honestly. The code, test and commit are unchanged; the branch is ready if Jolyon decides to open it, though the lead still recommends not to.

## The fix

No source change this round. oscar64/Parser.cpp, TK_STRING case in Parser::ParseSimpleExpression: the literal's element type is TheCharTypeDeclaration unless COPT_CPLUSPLUS is set, in which case it stays TheConstCharTypeDeclaration; the array type keeps DTF_CONST so the data is still emitted as constant data (LOBJF_CONST). Four code lines plus a three-line comment replacing one line. This round only rewrote the PR body: scoped the byte-identity claim to the measured corpus/samples/probe counts, replaced the 'only diagnostic lost' sentence with a full list of what C now accepts (literal writes, unsigned char *, the ?: qualifier laxity, the pointer-to-array laxity) with each attributed to UB or a pre-existing laxity, and corrected the example's observed output, corpus composition and line count as the earlier reviews asked.

## Regression test

autotest/stringliteralcharptrtest.c (new, 111 lines, assert-based, registered in autotest/autotest.bat after constlocaltest.c and picked up by the autotest makefile wildcard). Covers static, local and designated char * aggregates, a struct aggregate, a char *const table, file-scope and local scalars, assignment, argument passing, concatenation, the conditional operator with a volatile selector so both arms execute, pointer arithmetic, &"lit" as char (*)[4], volatile char *, return, a writable char array copy, and that const char * and void * still accept a literal. Before (4da3147 and pinned v1.32.273): error 3008 in all 10 configurations; after: Emulation result 0 in all 10, plus -O1, -O2 -Oo/-Ox/-xz -Oz and -strict; -pp still rejects it. C++ rejection is covered by 10 scratch .cpp probes, not an automated test (disclosed in the PR body).

## Evidence

**Repro matrix.** All in /home/jolyon/nethack64/build/oscar64-wt/r13-string-literal-scratch/fixup (matrix.py, out/, matrix-c-probes.txt, matrix-cpp-probes.txt, matrix-newtest.txt). Ten configurations = -ea -g x {-bc,-n} x {default,-O2,-O0,-Os,-O3}. Case tests/oscar64-repros/r13_string_in_charptr_aggregate.c: before 0/10 (E3008), pinned 0/10, after 10/10. New test: before 0/10, pinned 0/10, after 10/10 (also -strict 10/10; -pp E3008 before and after). PR example pr_example.c: before 2x error 3008 (3,29)/(3,35) only; after Emulation result 0. Positive probes newly passing 10/10 (all E3008/E3012 before): p01 local array, p02 local struct, p03 qualified pointers, p04 typedef, p06 string prefixes, p07 &"abc" as char (*)[4], p08 compound literal, p12 expressions, p15 void/unsigned char *, q05c __FILE__ etc., q09 designated, q10b fnptr table, q11d static ?:/parenthesised, r01 union/2-D/extern, r03 NetHack-shaped tables, r04 issue #439 as char *const, n16 volatile char *, k_autotest/k_r13/k_striped char versions. Already working before and unchanged: pr_already_work (const char *, cast, return), pr_return_only, p16 libcalls, q15a void *. Negative controls unchanged before/after: n01 const char * -> char * (value used) E3012 10/10; n02 long * E3012; n03 signed char * E3012; n04 local int * E3012; n05 file-scope int * E3012 at default/-O0, accepted at -O2/-Os/-O3; n09 assign to literal E3012/3014; n10 char ** param; n11 too-long char array E3008; n12/n13 int/struct from literal E3012; n15 return const char * as char * E3018 at default/-O0, accepted at -O2+. Newly accepted invalid C via pre-existing laxities: n06/n06b ?: with const char * (E3012 -> ok), n07 char ** = &"abc" (E3012 -> ok), n08 char (*)[5] = &"abc" (E3012 -> ok); controls n06c/n07b/n08b with a char array already ok before. Newly compiling UB: n14 direct write (E3014 -> ok), n17 write via char * (E3012 -> ok), u01 saw written values. C++ probes c01-c10: identical before/after (c01/c07 E3012, c02 E3008, c06/c09 E3014, others ok). Pre-existing failures identical before/after: p05/q05a/q05b/q05d/q05e stringify, p09 nested designator E3006, p10/q10a E3011, p11/q11a/b/c non-constant static address initialisers E3008, p13 char a[8] = {"de"} E3008, p14/q14 sizeof concatenation E3007, r02 K&R, k_pool E3007, k_striped -bc E3007. Byte identity: k_newtest/k_autotest/k_r13/k_striped/k_pool char-after vs const-before 10/10 each identical; z_read_literal before vs after 10/10 identical.

**Autotest.** make -k -j4 -C /home/jolyon/nethack64/build/oscar64-wt/r13-string-literal/make check > /home/jolyon/nethack64/build/oscar64-wt/r13-string-literal-scratch/autotest-fixup.log 2>&1 on the final commit (started with nohup, waited in the foreground, completed normally). autotest_diff.py /home/jolyon/nethack64/build/oscar64-wt/autotest-base-4da3147.log autotest-fixup.log: emulations base 1541, new 1551 (+10 = the new test's ten steps); new failures 0; fixed 0; failing in both 0; exit 0. stringliteralcharptrtest appears 10 times in the log. The testint16mul.c -bc quirk did not appear.

**Corpus.** corpus_diff.py ~/src/oscar64-base/bin/oscar64 (4da3147) vs /home/jolyon/nethack64/build/oscar64-wt/r13-string-literal/bin/oscar64 --out .../r13-string-literal-scratch/corpus-fixup -j4, run alone after make check had finished and relinked: 179 files (159 autotest: 124 .c + 35 .cpp with the 6 multi-file helpers excluded; plus 20 nethack64 tests/oscar64-repros r1-r20; r21/r22 appeared in that directory during the run and are not included) x 5 configurations (n-O2, n-Os, n-O0, n-O3, bc-O2) = 895 comparisons. Both compile: 830, identical: 830, different: 0. Status changed: 10 = autotest/stringliteralcharptrtest.c and oscar64-repros/r13_string_in_charptr_aggregate.c in all five configurations, error -> ok (expected). Both fail: 55 = 11 repro files x 5 (r2_nested_ternary, r3_sizeof_no_parens, r5_tag_vs_identifier, r6_func_and_tag_same_name, r7_space_after_hash, r8_multiline_comment_on_define, r10_register_keyword, r11_kr_definition, r12_braced_scalar_initializer, r15_union_ptr_to_const, r16_fnptr_compare_function), each rejected by both compilers with the same error codes (verified individually with -n -O2). Samples (scratch copy of samples/, 68 sources x 5 configurations, samples_cmp.sh): 333 identical, 0 different, 7 both-fail (hires_func3d.c and hiresmc_func3d.c at -O0 and memmap_tsr.c in all five: placement errors 3034 identical on both), 0 status changes.

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| opus | medium | PR does not mention upstream issue #90, closed by the owner as 'As expected' | fixed |
| opus | low | Invalid C newly accepted through pre-existing laxities (?: with const char *, char ** / char (*)[5] from &"abc") | out-of-scope |
| opus | low | Regression test misses paths the fix opens; nothing checks that C++ still rejects | fixed |
| opus | low | Factual errors in the draft PR text (example output, corpus size, line count, gcc comparison, thin validation) | fixed |
| opus | low | Author's internal report misstatements (void * newly accepted; error 3001 cascade; file-scope int * always accepted) | fixed |
| codex | medium | Pointer-to-array conversion `char (*p)[4] = &"abc"` untested; the array's DTF_CONST might leak into the qualifier check | fixed |
| codex | low | `unsigned char *u = "abc"` is not valid standard C and must not be listed as a positive change | fixed |
| codex | low | Negative-control summary overstates rejection ('still reject') and tests the wrong thing | fixed |
| codex | medium | Generated-code claim broader than evidence; corpus counts conflict (179 vs 179+2; 55 unaccounted comparisons) | fixed |
| codex | low | Test weaknesses: constant selector (`i` always 1), pick() foldable, no writable-copy check, C++ only in scratch | fixed |
| both | low | Writing through a string literal in C now compiles (3014/3012 before) | deferred |

<details><summary>Evidence for each finding</summary>

1. **PR does not mention upstream issue #90, closed by the owner as 'As expected'** (fixed)

   Confirmed with `gh issue view 90 --repo drmortalwombat/oscar64 --comments`: ClaudioDaffra's `char *DescriptionOfDirection[] = {"north", ...}` gave error 3008 eleven times; owner replied 'try "const char *"', then 'As expected', closed 2024-09-04. Same construct and same error as the PR example (probes/pr_example.c: 2x error 3008 on 4da3147 in 10/10 configurations). The PR body now has a paragraph that names #90 and argues the case (C89/C99 type, existing C sources, C++ untouched, no byte changes, only the UB-write diagnostic lost, offer of a warning as an alternative).

2. **Invalid C newly accepted through pre-existing laxities (?: with const char *, char ** / char (*)[5] from &"abc")** (out-of-scope)

   Reproduced in 10/10 configurations: n06/n06b (`char *q = c ? "lit" : cp` with cp const char *) before E3012, after ok; n07 (`char **pp = &"abc"`) before E3012, after ok; n08 (`char (*pa)[5] = &"abc"`) before E3012, after ok. gcc -std=c99 -pedantic-errors rejects all three. The same forms with a `char arr[4]` instead of a literal (n06c, n07b, n08b) were already accepted by 4da3147 in 10/10, so the causes are pre-existing (EX_CONDITIONAL keeps the less-qualified pointee; IsSubType at Declaration.cpp:2812-2814 compares pointer/array pointees by element only, ignoring array size). The literal's const mismatch merely hid them. Not fixed here; disclosed in the PR's negative-controls paragraph and listed in adjacent_bugs.

3. **Regression test misses paths the fix opens; nothing checks that C++ still rejects** (fixed)

   Test extended with a local automatic `char *local[]`, a local `struct Named one = {"local", 7}`, a designated `static char *sparse[4] = {[2] = "z", [0] = "y"}`, `volatile char *vp = "volatile"`, issue #439's table as `static char *const fixed[]`, and `char (*pa)[4] = &"abc"`. Each of these fails on 4da3147 (p01/p02/q09/n16/r04/p07 probes: E3008 or E3012 10/10) and passes after. The new test: before 0/10 (E3008), pinned v1.32.273 0/10, after 10/10; also -strict 10/10 after, -pp still E3008. C++ negative checks cannot live in autotest (no generic expected-failure mechanism; the makefile's constraint targets are bespoke per test), so they stay scratch probes: c01 (char * local) E3012, c02 (aggregate) E3008, c06/c09 (write) E3014, c07 (char * argument) E3012, identical before and after in 10/10; c03/c04/c05/c08/c10 pass identically.

4. **Factual errors in the draft PR text (example output, corpus size, line count, gcc comparison, thin validation)** (fixed)

   (1) Confirmed: the PR example on 4da3147 `-ea -g -n` prints only `(3, 29) : error 3008` and `(3, 35) : error 3008`; the 3012 appears only without the array (`error 3012: Cannot assign incompatible types 'u8*' != 'const const u8[]'` x3 for pr_local_assign_arg.c). PR now says so. (2) Corpus is 159 autotest programs (124 .c + 35 .cpp, 6 helpers excluded) + 20 nethack64 repro files = 179; PR corrected. (3) `git diff` shows Parser.cpp +7/-1 (4 code lines + 3 comment lines replacing 1); PR says 'a four-line change'. (4) gcc 13.3 -std=c99 warns 'assignment of read-only location' for `"abc"[0] = 'x'` and is silent for a write through a char *; PR says so. (5) Added validation I re-ran myself: samples 333 identical / 0 different / 7 both-fail / 0 status change; char * build byte-identical to const char * build on 4da3147 (10/10 for the new test, the repro, a pooling probe and a __striped table); -strict, -pp, -O1, -O2 -Oo, -O2 -Ox, -O2 -xz -Oz.

5. **Author's internal report misstatements (void * newly accepted; error 3001 cascade; file-scope int * always accepted)** (fixed)

   Confirmed all three: q15a (void * from a literal: local, global, aggregate, argument) is ok 10/10 on 4da3147, so it was not changed by the fix; the case file and test fail before with error 3008 only (no 3001 in any of the 10 logs); n05 `int *p = "abc"` at file scope gives 3012 at default/-O0 and is accepted at -O2/-Os/-O3, identically before and after. This report and the PR text use the corrected statements; void * is now described as a side-effect check that already worked.

6. **Pointer-to-array conversion `char (*p)[4] = &"abc"` untested; the array's DTF_CONST might leak into the qualifier check** (fixed)

   Hypothesis tested: p07 (`char (*pa)[4] = &"abc"; (*pa)[1] == 'b' && sizeof(*pa) == 4`) is E3012 on 4da3147 and ok 10/10 after the fix, so the array-level DTF_CONST does not leak into CanAssign (IsSubType for pointer/array pointees recurses on mBase, the element type, Declaration.cpp:2812-2814). Added to the regression test. Side note (pre-existing): the same path accepts a wrong-sized `char (*pa)[5] = &"abc"` and `char **pp = &"abc"`, because the pointee comparison ignores array size; already true for `&arr` (n08b, n07b ok before and after).

7. **`unsigned char *u = "abc"` is not valid standard C and must not be listed as a positive change** (fixed)

   Confirmed: gcc -std=c99 -pedantic-errors rejects it ('pointer targets ... differ in signedness [-Wpointer-sign]'). Oscar64 accepts it after the fix (p15: before E3012, after ok 10/10, also under -strict) because TheCharTypeDeclaration == TheUnsignedCharTypeDeclaration (Declaration.cpp:3548), a pre-existing conflation of char and unsigned char that `unsigned char *u = arr;` already slipped through. PR and report now describe it as an existing limitation exposed by the fix, not as conforming C. The conflation itself is out of scope (adjacent_bugs).

8. **Negative-control summary overstates rejection ('still reject') and tests the wrong thing** (fixed)

   Confirmed. n05 (file-scope `int *p = "abc"`) and n15 (returning a const char * as char *) are accepted at -O2/-Os/-O3 and rejected at default/-O0, identically before and after; n01 (const char * -> char * with the value used, Codex's 'observable use' form) is E3012 in 10/10 before and after; n02 long *, n03 signed char *, n04 local int *, n09 assignment to a literal, n10, n11, n12, n13 all unchanged. PR wording now says 'unchanged before and after' and names the optimisation-level acceptances.

9. **Generated-code claim broader than evidence; corpus counts conflict (179 vs 179+2; 55 unaccounted comparisons)** (fixed)

   Re-ran corpus_diff on the final compiler: 179 files (159 autotest + 20 repros, r1-r20; r21/r22 were created in the nethack64 tree by someone else after the run started and are not in it) x 5 configurations = 895 comparisons: 830 both compile and are byte-identical, 0 different, 10 status changes (the two files that use the construct, error -> ok), 55 both-fail = 11 nethack64 repro files (r2, r3, r5, r6, r7, r8, r10, r11, r12, r15, r16) x 5, each rejected by both compilers with identical error codes (checked individually). Codex's `return "abc"[i & 3]` probe (z_read_literal.c) is byte-identical before/after in 10/10. The PR now states the measured claim ('every program in the corpus that both compilers accept builds byte for byte the same') instead of an unconditional one.

10. **Test weaknesses: constant selector (`i` always 1), pick() foldable, no writable-copy check, C++ only in scratch** (fixed)

   Test now uses `volatile int t = 1; int f = t - 1;` so both arms of `t ? ... : ...` / `f ? ... : ...` and both `pick(t)` / `pick(f)` run at runtime; added `char copy[] = "copy"; copy[0] = 'C';` and `void *v = "void"` as side-effect checks that already worked before (stated as such in the PR). C++ rejection remains scratch-probe coverage (c01/c02/c06/c07/c09 identical before/after) because autotest has no general expected-failure mechanism; noted as a limitation in the PR. The point that a whole-file baseline failure does not prove each construct failed is acknowledged: the PR names the constructs that already worked (return, const char *, void *, char array init).

11. **Writing through a string literal in C now compiles (3014/3012 before)** (deferred)

   n14 (`"abc"[0] = 'x'`) before E3014, after ok 10/10; n17 (write via char *) before E3012, after ok 10/10; u01 saw the written value at all levels but the data is still LOBJF_CONST so that is not guaranteed. This is undefined behaviour that the standard allows a compiler to accept (gcc accepts; it warns only for a direct write). Both reviewers agree it is not a regression. A warning for a direct write would need a new check in the code generator; offered in the PR as an option for the maintainer rather than widening this fix.

</details>

## Last round: final-check findings and what happened to them

Changed in the last round: text-only. Commit before it: `9c0bcf682c88`.

| From | Severity | Finding | Resolution |
|---|---|---|---|
| final-check Codex #1 | medium | PR text claims 'no generated byte changes for any program that compiled before' (universal claim beyond the evidence) | fixed |
| final-check Codex #2 | low | PR text says 'The only diagnostic lost is for writing into a literal', contradicting the later disclosure of other newly accepted forms | fixed |
| final-check Codex (verdict text) | low | No implementation blocker; C++ negative test absence disclosed | rejected |

<details><summary>Evidence, and what was re-run</summary>

1. **PR text claims 'no generated byte changes for any program that compiled before' (universal claim beyond the evidence)** (fixed)

   The claim is not in the commit (9c0bcf6's message already says 'every program in the autotest and samples corpus that both compilers accept builds byte for byte the same'); it came from the #90 paragraph the fix-up round added to the PR body. Rewritten PR body scopes every code-generation statement to what was measured: corpus 179 files x 5 configurations = 895 compiles, 830 outputs both compilers produce byte-identical (corpus-fixup.log, re-counted: base 831 .prg incl. one non-zero-exit build, new 841, only-in-new = the 10 status changes), 55 fail identically; samples 68 sources x 5 configurations, 333 byte-identical, 0 different, 7 fail identically with the same diagnostics (re-cmp'd the fix-up's samples-out pairs today); patched char * builds vs base const char * builds 22/22 identical (re-run today, 10 configs + -n -tf=crt for the test and the repro). No universal wording remains.

2. **PR text says 'The only diagnostic lost is for writing into a literal', contradicting the later disclosure of other newly accepted forms** (fixed)

   fixup/matrix-c-probes.txt (10 configurations, before 4da3147 vs patched): n14 direct write and n17 write via char * E3014/E3012 -> ok; p15 unsigned char *u = "abc" E3012 -> ok (gcc -std=c99 -pedantic: -Wpointer-sign warning, re-run today); n06/n06b conditional with const char * operand E3012 -> ok while n06c (no literal) was ok before; n07 char **pp = &"abc" and n08 char (*pa)[5] = &"abc" E3012 -> ok while n07b/n08b (&arr) were ok before. The sentence is replaced by a dedicated 'What becomes accepted in C besides the fix' section listing all four, each marked UB or pre-existing laxity, with C++ unchanged (10 .cpp probes identical before/after).

3. **No implementation blocker; C++ negative test absence disclosed** (rejected)

   Not a defect to fix: confirmed the test is valid C99 (gcc -std=c99 -pedantic -Wall -Wextra clean, runs 0 on host today) and that -pp on the test still gives 11 x error 3008 with the patched compiler; the PR body states that C++ coverage is probe-based, not an automated test.

**Re-validation.** Text-only change (PR body); nothing rebuilt, commit untouched (9c0bcf682c88 on 4da3147, 3 files: oscar64/Parser.cpp +7/-1, autotest/stringliteralcharptrtest.c +111, autotest/autotest.bat +3; worktree clean; bin/oscar64 06:14 newer than Parser.cpp 02:39). Re-verified today every number quoted in the new body: (1) PR example on 4da3147 -ea -g -n: exactly two 'error 3008: Incompatible constant initializer' at (3,29) and (3,35); patched: Emulation result 0; pr_local_assign_arg.c on 4da3147: 3 x error 3012 'u8*' != 'const const u8[]'. (2) New test with patched compiler: Emulation result 0 for -n -O1, -bc -O1, -n -O2 -Oo, -n -O2 -Ox, -n -O2 -xz -Oz, -n -strict, -bc -strict, -n -O2 -strict, -n -Os -strict; -pp still 11 x error 3008. (3) autotest_diff.py baseline vs autotest-fixup.log: emulations base 1541, new 1551, new failures 0, fixed 0, failing in both 0. (4) corpus-fixup.log: 179 files x 5 configurations, both compile 830, identical 830, different 0, status changed 10 (the two construct files); re-counted outputs: 10 only-in-new, 0 only-in-base, 55 both-fail. (5) samples-out pairs re-compared: identical 333, different 0, 7 before/after log pairs with errors, 0 with differing error text, 68 sources. (6) patched char * vs base const char * builds: 22/22 byte-identical (k_r13 and k_autotest, 10 configs + -n -tf=crt). (7) Fix-up probe matrices (10 configs) re-read: 10 C++ probes identical before/after; negative probes n01-n05, n09-n13, n15 unchanged; newly accepted n06/n06b/n07/n08/n14/n16/n17/p15. (8) gcc -std=c99 -pedantic -Wall -Wextra on the test: no warnings, host run exit 0; unsigned char * probe: -Wpointer-sign warning.

</details>

## Final check (Codex, read-only, on the final commit)

<details><summary>SUBMIT AFTER CHANGES</summary>

VERDICT: SUBMIT AFTER CHANGES

1. **Medium — PR text: “no generated byte changes for any program that compiled before.”** This universal claim remains despite the earlier finding being marked fixed. The reported comparisons support only the tested corpus. Replace with: “All tested programs accepted by both compilers produced byte-identical outputs.” The commit message already scopes this appropriately.

2. **Low — PR text: “The only diagnostic lost is for writing into a literal.”** This contradicts the later disclosure that qualifier-dropping conditionals, incompatible pointer-to-array conversions, and `unsigned char *` initialisation also become accepted. Replace with: “Writes into literals now compile, and several pre-existing type-checking laxities become observable with literals, as detailed below.”

No implementation blocker is apparent in the supplied diff. The regression test is valid C99, exercises the reported failure, and intentionally fails as C++; the absence of an automated C++ negative test is disclosed.

</details>

## Before submitting

- Done 2026-11-12 (Jolyon's decision): the commit ends with one `Co-Authored-By: Claude <noreply@anthropic.com>` line and no session link (message only; the tree is the one validated, commit `9c0bcf682c88` before), and the PR text ends with the same AI-assistance sentence as every other PR.

## Risks and limitations

(1) Maintainer stance: issue #90 was closed 'As expected' with the const char * advice; the body now argues from the standard and from existing C sources but the owner may still decline, and the lead's current recommendation is not to open the PR. nethack64's fallback (const char * in mail.c) stays valid. (2) In C, writes into a literal now compile (UB; data stays LOBJF_CONST in the code section so a later read may be folded). (3) unsigned char * from a literal compiles because Oscar64 conflates char with unsigned char; pre-existing but newly observable. (4) Two pre-existing checker laxities (?: dropping const, pointer-to-array converting to char ** or wrong-size array pointer) now reach literals; not fixed here, offered as separate issues. (5) Not tested: real hardware, non-C64 targets, Windows build (plain C++ change, no platform code).

## Related bugs found, not fixed here

All pre-existing, identical on 4da3147 and the fix, not fixed here: (a) sizeof("ab" "cd") == 3: the concatenation loop in the same TK_STRING block updates dec->mSize but never dec->mBase->mSize (p14/q14 E3007 before and after; a one-line fix, but a separate change). (b) `#define XSTR(x) STR(x)` stringifies the parameter name instead of its value (q05a/d/e E3007). (c) `char a[8] = { "de" };` rejected with 3008 (p13). (d) `static const char *a = "abc" + 2;` and `= &"abc"[3]` give 3008 non-constant initializer (p11, q11a/b/c). (e) nested designator `.in.m[1] =` rejected E3006 (p09). (f) `ops[0].f(ops[0].name)` gives 3011 'Not a simple type' (p10, q10a). (g) K&R definitions unsupported (r02). (h) `__striped const char *names[3]` table fails at runtime under -bc, result 1 (k_striped). (i) Invalid declarations whose dead local or value is optimised away are accepted at -O2/-Os/-O3 and rejected only at default/-O0 (n05 file-scope `int *p = "abc"`, n15 return const char * as char *). (j) ?: keeps the less-qualified pointee: `char *q = c ? p : cp;` with cp const char * accepted (n06c). (k) IsSubType compares pointer/array pointees by element only: `char **pp = &arr;` and `char (*pa)[5] = &arr;` with char arr[4] accepted (n07b, n08b). (l) char and unsigned char are the same type (Declaration.cpp:3548), so `unsigned char *u = arr;` / `= "abc"` is accepted. (m) Two identical literals in one function are not always pooled: k_pool returns 18 (p != q for two local "dup") with both compilers and both const/char forms; informational.

## Draft pull request

**Title:** Fix string literal to char * conversion in C

````markdown
In C a string literal has type `char[N]` (C89 3.1.4, C99 6.4.5), so it converts to `char *` without a cast; only C++ makes it `const char[N]`. Oscar64 types every literal `const char[N]`, so this C program is rejected:

```c
#include <assert.h>

static char* junk[] = { "ab", "c" };

int main(void)
{
	char* p = "local";
	assert(junk[0][1] == 'b' && junk[1][0] == 'c' && p[2] == 'c');
	return 0;
}
```

Reproduce with `oscar64 -ea -g -n example.c` (every optimisation level, `-bc` too). Observed: `error 3008: Incompatible constant initializer` once per literal of the array (3:29 and 3:35), even if `junk` is never referenced; the parse error stops compilation there. Without the array, the local gives `error 3012: Cannot assign incompatible types 'u8*' != 'const const u8[]'`, as do an assignment and a `char *` argument. Expected: it compiles and the emulation returns 0. `const char *`, a `(char *)` cast and `return "a";` already work.

This is the error reported in #90, which was closed with the advice to use `const char *`. That is the right type for new code, but the standard gives a literal the type `char[N]`, and existing C sources (#90's program, NetHack's `mail.c`) use `char *` tables that other C compilers accept. The patch changes only C. In C++ the conversion has been ill-formed since C++11; C++ keeps `const char[N]` and its diagnostics are unchanged.

Root cause: `Parser::ParseSimpleExpression`, `TK_STRING` case (oscar64/Parser.cpp:8123 on 4da3147), sets the literal's element type to `TheConstCharTypeDeclaration` unconditionally. `Declaration::CanAssign` for a `char *` target then calls `IsSubType` on the element types, which refuses `char <- const char` because of the extra `DTF_CONST`. `CanAssign` works on types alone and cannot tell a literal from any other `const char[N]`, so the literal's type is the one-site fix.

The fix gives the element type `TheCharTypeDeclaration` when `COPT_CPLUSPLUS` is not set and leaves `TheConstCharTypeDeclaration` in C++. The array type itself keeps `DTF_CONST`, which is what `InterCodeGenerator` reads to mark the literal's linker object `LOBJF_CONST`, so placement, string pooling and the constant-data handling are untouched. Four lines of code plus a comment (Parser.cpp +7/-1).

The regression test `autotest/stringliteralcharptrtest.c` covers static, local and designated `char *` aggregates, a struct aggregate, a `char *const` table, a file-scope and a local scalar, assignment, argument passing, adjacent-literal concatenation, the conditional operator with a volatile selector so both arms run, pointer arithmetic, `&"lit"` as a pointer to array, a `volatile char *`, returning a literal, a writable `char` array copy, and that `const char *` and `void *` still accept a literal. It is discovered by the autotest makefile and registered in `autotest.bat`. It is also clean under `gcc -std=c99 -pedantic -Wall -Wextra` and runs on the host.

Validation against main `4da3147` on Linux, targeting the C64:

- Case and new test, 10 configurations each (`-ea -g`, `-bc`/`-n`, default/`-O0`/`-O2`/`-O3`/`-Os`): before 0/10 (error 3008), after 10/10 with emulation result 0. The test also passes with `-O1`, `-O2 -Oo`, `-O2 -Ox`, `-O2 -xz -Oz` and `-strict` (`-n`, `-bc`, `-O2`, `-Os`). Compiled as C++ with `-pp` it is still rejected (error 3008), as intended.
- Full autotest (`make -k -j4 check`): 1541 successful emulations on the baseline, 1551 with the patch and new test (+10 = the new test's steps), no failures in either.
- Corpus: 159 autotest programs plus 20 small C repro files of ours (179 files), 5 configurations each (895 compiles). The 830 outputs that both compilers produce are byte-identical; the 10 status changes (error -> ok) are exactly the two files that use the construct; the remaining 55 fail identically on both compilers.
- All 68 sources in `samples/`, 5 configurations: 333 outputs byte-identical, 7 fail identically on both compilers with the same diagnostics.
- The `char *` versions of the test and the example built by the patched compiler are byte-identical to their `const char *` versions built by unpatched main in all 10 configurations and with `-tf=crt` (22/22).
- Negative probes unchanged in all 10 configurations: a `const char *` variable to `char *` (destination used), `long *`, `signed char *`, local `int *`, `int` and struct from a literal, a `char **` parameter, assignment to a literal, a too-long `char` array; this includes the pre-existing acceptance of some unused invalid declarations at `-O2`/`-Os`/`-O3`. Ten C++ probes (local, aggregate, argument, writes, overloads, `auto`, templates, `constexpr`, `?:`) are identical before and after.

What becomes accepted in C besides the fix:

- Writing into a literal, directly (`"abc"[0] = 'x';`) or through a `char *` that points to one, now compiles instead of giving error 3014/3012. It is undefined behaviour; gcc compiles both and warns by default only on the direct write. C++ still rejects it. If you would rather keep a diagnostic for the direct write, a warning could be added.
- `unsigned char *u = "abc";` compiles, because Oscar64's `char` is the unsigned char type (`TheCharTypeDeclaration` is `TheUnsignedCharTypeDeclaration`). Standard C requires a diagnostic here (gcc warns with `-Wpointer-sign`); the conflation predates this patch and only becomes observable with literals.
- Two pre-existing laxities that the const mismatch used to mask now apply to literals exactly as they already applied to `char` arrays: `?:` keeps the less-qualified pointee, so `char *q = c ? "lit" : cp;` with `const char *cp` is accepted (as `c ? p : cp` already was), and a pointer to an array converts to a pointer to a pointer or to a pointer to an array of another size, so `char **pp = &"abc";` and `char (*pa)[5] = &"abc";` are accepted (as `&arr` already was). This patch does not change those checks; I can file them separately.

Found while porting NetHack 3.4.3 to the C64 (`mail.c`'s `static char *junk[]`). Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described.
````
