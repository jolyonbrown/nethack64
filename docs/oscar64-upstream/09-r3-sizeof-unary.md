# 09. Fix sizeof applied to a unary expression without parentheses

| | |
|---|---|
| Branch | `fix/r3-sizeof-unary` in `~/src/oscar64-dev`, commit `64ffa3a722eb`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/09-r3-sizeof-unary.patch`](../../tools/oscar64-upstream/patches/main/09-r3-sizeof-unary.patch) |
| Kind | rejects valid C |
| Since | v1.32.273 and main |
| NetHack | Compat #6 (repro r3): `sizeof x` without parentheses, 117 sites. Workaround: `tools/oscar_normalize.py` adds parentheses. |
| Reviews | Opus (round 1, ran probes): submit-after-changes, 0 high, 2 medium, 3 low; Codex (read the diff): submit after changes; fix-up: ready; final Codex check: submit |
| Recommendation | **Submit.** |

## In plain words

C lets you write `sizeof arr` or `sizeof *p` without brackets, and NetHack does this in well over a hundred places; Oscar64 insisted on `sizeof (...)` and stopped with "'(' expected", which we have been papering over with a script that adds brackets. The fix teaches the parser to read one ordinary operand when no bracket follows, and (after the review) also to handle `sizeof (arr)[0]`-style operands, to reject the nonsense `sizeof {1, 2}` that the first version let through as 0, and to point error messages at the right column. The reviews' main catch was that the original test could not tell a correct fix from a plausible wrong one that swallowed too much of the expression; the test was rewritten so that such a wrong compiler fails it (checked with two deliberately broken compilers), and extra cases make sure nothing inside `sizeof` is ever executed or linked. Everything was re-run: the full Oscar64 test suite shows no new failures and every existing program compiles to the identical bytes. What could still go wrong is limited to odd code that was already wrong (sizeof of a function or bit-field is accepted without complaint, as it was before with brackets) and platforms we cannot test (Windows build, real hardware).

## The fix

oscar64/Parser.cpp, Parser::ParseSimpleExpression case TK_SIZEOF (non-ellipsis branch), 15 lines added / 1 removed in one function: (1) if the token after sizeof is not '(', parse the operand with ParsePrefixExpression(false) and reject EX_TYPE or EX_AGGREGATE results with the previous "'(' expected" error, reported at a Location captured before parsing; (2) if it is '(', call ParseParenthesisExpression as before and, when the result is not an EX_TYPE, complete its postfix operators with ParsePostfixExpression(false, rexp), mirroring ParseCastExpression. Changes relative to the reviewed commit 5247448: postfix continuation adopted from the Opus reviewer's M3 after my own evaluation, EX_AGGREGATE rejection (M4), error location fix, test rewritten. autotest/autotest.bat registration unchanged.

## Regression test

/home/jolyon/nethack64/build/oscar64-wt/r3-sizeof-unary/autotest/sizeofunarytest.c (117 lines), registered in autotest.bat. Every comparison writes the constant first or stores the value in i before asserting, so a greedy operand parser cannot pass. Cases: plain objects; arr[0], sa[1], s.b, sa[2].c, sp->c; *p, *sp, &arr, -l, -c, +c, ~c, !l, sizeof sizeof arr; sizeof arr / sizeof arr[0], sizeof buf - 1, sizeof l * 2, sizeof c + sizeof l, sizeof arr == 20 ? 3 : 4; parenthesised operand with postfix: (arr)[0], (s).c, (sp)->c, (arr)/sizeof (arr)[0]; unchanged parenthesised forms (arr), (arr)+1, (int)*3, (struct S), (arr)/(arr[0]); non-evaluation: n++, ++n, arr[n++], (n)++, never_defined() and (never_defined)() with never_defined declared extern and never defined, n == 0 afterwards; array parameter is a pointer; memset(buf, 0x55, sizeof buf) and memset(arr, 0, sizeof arr) with contents checked. Results: 4da3147 0/10 (error 3006 at line 21), v1.32.273 0/10, fix 10/10; also passes -O1 (bc and n), -O2 -xz -Oz, -O2 -Oo -Ofp, -O2 -Ox -Ofp, -pp (n -O2, bc, n -O0), -strict (n, bc -O2). Mutants built from the final source: M1 (ParseExpression) 0/10, M2 (ParseMulExpression) 0/10, control build 10/10; the old committed test passed M1 10/10. A deliberately false assert gives rc=20 / Emulation result -1, so the asserts are live.

## Evidence

**Repro matrix.** Ten configurations = oscar64 -ea -g {-bc|-n} x {default,-O2,-O0,-Os,-O3}. before = ~/src/oscar64-base/bin/oscar64 (4da3147), after = worktree bin/oscar64 (64ffa3a), pinned = ~/src/oscar64/bin/oscar64 (v1.32.273).
- autotest/sizeofunarytest.c: before 0/10 (error 3006 '(' expected), pinned 0/10, after 10/10 Emulation result 0.
- tests/oscar64-repros/r3_sizeof_no_parens.c: after 10/10 (before: error 3006, per corpus status change).
- Review probes, after 10/10 each: valid1.c, valid3.c, nhshapes.c (NetHack contexts), misc1.c, neg/p06.c (parenthesised + postfix, 8 checks), example.c (PR example), incomplete.c, undef.c. Before 0/10 each for valid1/valid3/nhshapes/misc1/p06/example.
- C++: valid2.cpp and pack.cpp (sizeof...(ts) plus sizeof a) pass -n, -n -O2, -bc, -bc -O3 after; both error 3006 before.
- tools/oscar64-upstream/cases/*.c (14 files, -n): status identical before/after; the 4 that compile are byte-identical.
- Code generation: sizeof E vs sizeof (E) for 20 operand forms, plus 5 parenthesised-postfix forms vs fully parenthesised, in -n / -n -O2 / -bc -O2: 75/75 identical .prg. se_u.c (return sizeof lf()) byte-identical to se_none.c (return 4); lf not in the map.
- Negatives (scratch neg/, -e -n, compared with gcc -std=c99 -pedantic): still rejected before and after: sizeof int, unsigned char, struct S, T, int *, void, int x, arr arr, undeclared, (int) n, sizeof;, sizeof = 3, sizeof ), sizeof ,, (T)[0], (int)++. Now rejected after (new): sizeof {1, 2}, {s}, {0} + 1 (error 3006 at the brace). Error column for type-name operands is now 40 (gcc's column) instead of 43. Newly accepted after, matching the pre-existing parenthesised acceptance: sizeof lf (0) and sizeof s.bf (2). No crashes (no rc >= 128) on any negative.

**Autotest.** make -k -j4 -C /home/jolyon/nethack64/build/oscar64-wt/r3-sizeof-unary/make check > /home/jolyon/nethack64/build/oscar64-wt/r3-sizeof-unary-scratch/autotest-fixup.log 2>&1 (run with nohup, waited to completion; log ends normally with no make errors). autotest_diff.py build/oscar64-wt/autotest-base-4da3147.log <log>: emulations base 1541, new 1551; new failures 0; fixed 0; failing in both 0. sizeofunarytest appears 10 times in the log. No testint16mul.c difference appeared.

**Corpus.** corpus_diff.py ~/src/oscar64-base/bin/oscar64 <worktree>/bin/oscar64 --out /home/jolyon/nethack64/build/oscar64-wt/r3-sizeof-unary-scratch/corpus-fixup -j4 (ran ~11 min; waited to completion): 179 files (165 autotest .c/.cpp minus 6 helpers = 159, plus 20 tests/oscar64-repros/*.c; two more repro files than the author's run, r19 and r20) x 5 configurations (n-O2, n-Os, n-O0, n-O3, bc-O2) = 895 compiles. both compile 830, identical 830, different 0. status changed 10, all error -> ok and all expected: autotest/sizeofunarytest.c x5 and oscar64-repros/r3_sizeof_no_parens.c x5, the only two files using sizeof without parentheses. both fail 55 = 11 repro files for other open Oscar64 bugs x 5 configurations (same set as before; the cases/ check above confirms no status change on the fnmember/fnptr/o0 repros). Nothing else changed status or bytes, so the parenthesised path, now with the postfix continuation, still generates identical code for every program the corpus exercises.

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| both | medium | Regression test is vacuous against a too-greedy operand (assert(sizeof x == N) passes as sizeof (x == N)); precedence/"binds tighter" claims unproven | fixed |
| opus | medium | sizeof (expr) followed by a postfix operator (sizeof (arr)[0], sizeof (s).c, sizeof (sp)->c, sizeof (n)++, sizeof (lf)()) still rejected; PR's reason for deferring it was wrong | fixed |
| opus | low | New silent acceptance: sizeof {1, 2} compiles to 0 (EX_AGGREGATE operand) | fixed |
| opus | low | 'sizeof int' error now points after the type name (column drift 40 -> 43) | fixed |
| opus | low | PR text overclaims (precedence coverage, 'cannot exist', wrong deferral reason, omits sizeof {1,2}) and NetHack site count 115 matches no record | fixed |
| opus | low | Internal report misattributed the fixed line to 7af4588/c0152b1 | fixed |
| codex | medium | Unevaluated-operand coverage missing: function calls, a never-defined extern function, arr[n++], ++n | fixed |
| codex | medium | sizeof f (function type) and sizeof b.bit (bit-field) are accepted without a diagnostic | out-of-scope |
| codex | low | Root-cause wording: 'only sizeof (type-name) was implemented' is misleading; 'consumes exactly one unary expression' overstated | fixed |
| codex | low | Compatibility claims too broad ('code that relied on the old behaviour cannot exist') | fixed |

<details><summary>Evidence for each finding</summary>

1. **Regression test is vacuous against a too-greedy operand (assert(sizeof x == N) passes as sizeof (x == N)); precedence/"binds tighter" claims unproven** (fixed)

   Reproduced: the committed test passed 10/10 on the reviewer's mutant M1 (operand parsed with ParseExpression). I rebuilt two mutants from the FINAL source in the scratch dir (M1 = ParseExpression, M2 = ParseMulExpression, plus a control build of the real source): the old test passes M1 10/10; the rewritten autotest/sizeofunarytest.c stores each value before comparing or writes the constant first and fails M1 0/10 and M2 0/10 (Emulation result -1), passes the control 10/10 and the fix 10/10, fails 4da3147 and v1.32.273 0/10 (error 3006). Also added sizeof c + sizeof l, nested sizeof, unary + and ! as Codex asked.

2. **sizeof (expr) followed by a postfix operator (sizeof (arr)[0], sizeof (s).c, sizeof (sp)->c, sizeof (n)++, sizeof (lf)()) still rejected; PR's reason for deferring it was wrong** (fixed)

   Reproduced: review/neg/p06.c fails identically on 4da3147, the first fix and v1.32.273 (3016 'Array expected for indexing', 3013 'Struct expected'). Evaluated the reviewer's M3 myself: ParsePostfixExpression only consumes :: [ ( ++ -- -> . (and { only after EX_TYPE, which is excluded), none of which can validly follow a complete (sizeof (expr)) in C, so every input it changes was a hard error before; '...' is not consumed so sizeof...(pack) and pack expansion are unaffected; it mirrors ParseCastExpression's existing continuation. Adopted (4 lines, EX_TYPE guarded). p06.c 10/10 after; test lines added for (arr)[0], (s).c, (sp)->c, (arr)/sizeof (arr)[0], (n)++ and (never_defined)(); corpus 830/830 byte-identical and autotest 0 new failures with the parenthesised path touched.

3. **New silent acceptance: sizeof {1, 2} compiles to 0 (EX_AGGREGATE operand)** (fixed)

   Reproduced: before and pinned give error 3006 '(' expected + 'Term starts with invalid token {'; first fix rc=0 Emulation result 0. Added || rexp->mType == EX_AGGREGATE to the check. Now sizeof {1, 2}, sizeof {s} and sizeof {0} + 1 all give error 3006 '(' expected at the brace; sizeof ({1, 2}) unchanged (rejected by both).

4. **'sizeof int' error now points after the type name (column drift 40 -> 43)** (fixed)

   Reproduced (sint.c: before @40, first fix @43 and @57). Capture Location loc(mScanner->mLocation) before ParsePrefixExpression and report there. Now sizeof int / unsigned char / struct S / T / int * / void / {1,2} all report at column 40, the column gcc reports.

5. **PR text overclaims (precedence coverage, 'cannot exist', wrong deferral reason, omits sizeof {1,2}) and NetHack site count 115 matches no record** (fixed)

   Recounted from the pristine tarball (extracted to scratch, comments stripped with gcc -fpreprocessed): src/ 113 identifier/prefix-op operands, 119 including 6 string-literal operands; util/ 32; include/ 0; 0 parenthesised-then-postfix sites. Matches the reviewer's 113/119 and 145/151. PR body rewritten with these numbers, the corrected grammar description, bounded compatibility claims, the corpus described honestly (159 autotest sources + 20 nethack64 repro files, 55 both-fail), the example output marked as the first diagnostic, and the limitations stated.

6. **Internal report misattributed the fixed line to 7af4588/c0152b1** (fixed)

   git blame -L 8342,8342 4da3147 gives c674fc9a (2023-09-17, 'Add variadic sizeof...'). Not in the PR text; corrected here.

7. **Unevaluated-operand coverage missing: function calls, a never-defined extern function, arr[n++], ++n** (fixed)

   Coverage gap confirmed, no defect: undef.c (extern long never_defined(void); sizeof never_defined(), sizeof arr[n++], sizeof ++n, n stays 0) passes 10/10 with the fix and links; se_u.c (return sizeof lf()) produces a .prg byte-identical to return 4 with lf absent from the map. All four cases, plus sizeof (n)++ and sizeof (never_defined)(), are now in the autotest.

8. **sizeof f (function type) and sizeof b.bit (bit-field) are accepted without a diagnostic** (out-of-scope)

   Confirmed accepted after the fix (sizeof f == 0, sizeof b.bit == 2; gcc warns/errors). But sizeof (f) == 0 and sizeof (b.bit) == 2 are accepted identically by 4da3147 and v1.32.273 (fnp.c: Emulation result 2 on the before compiler), so the constraint check is missing in the shared code after operand parsing, not introduced here. The patch only makes the unparenthesised spelling reach the same pre-existing behaviour. Listed in adjacent_bugs and stated as a known limitation in the PR.

9. **Root-cause wording: 'only sizeof (type-name) was implemented' is misleading; 'consumes exactly one unary expression' overstated** (fixed)

   PR text now says every operand had to begin with '(' and one routine served both parenthesised expressions and type names; the ParsePrefixExpression description is stated as what it does (reads one prefix/postfix expression and stops at the first binary operator) with the mutant evidence behind it.

10. **Compatibility claims too broad ('code that relied on the old behaviour cannot exist')** (fixed)

   Replaced with the bounded statement: previously accepted operands follow the same parser path (plus postfix continuation that only applies where the old code errored), all 830 mutually successful corpus builds are byte-identical, 75/75 sizeof E vs sizeof (E) pairs identical.

</details>

## Final check (Codex, read-only, on the final commit)

<details><summary>SUBMIT</summary>

VERDICT: SUBMIT

No findings. The diff addresses the earlier actionable findings, the revised test guards against overly greedy operand parsing, and the stated evidence supports the PR’s claims and disclosed limitations.

</details>

## Before submitting

- Make the AI-assistance line the same in every PR body (some end with a sentence, some with a "Generated with Claude Code" footer), as Jolyon decides.
- Commit trailers: drop the `Claude-Session:` line and use one `Co-Authored-By:` line, as Jolyon decides for all PRs (see OSCAR64-UPSTREAM.md).

## Risks and limitations

(1) The parenthesised path is now touched: after sizeof (expr) the parser consumes [ ( . -> ++ -- (and :: in C++) as part of the operand. In C none of these can validly follow a complete (sizeof (expr)), so only previously-erroring inputs change; EX_TYPE results are excluded so sizeof (T){0}, sizeof (int)(3) and sizeof (T) * 3 are untouched; verified by corpus 830/830 identical and autotest 0 new failures. (2) sizeof of a function designator or bit-field is accepted without diagnostic, as the parenthesised forms always were; the unparenthesised spelling now reaches that gap. (3) Bare sizeof; now reports 'Term starts with invalid token' instead of '(' expected (still error 3006). (4) Untested: Windows build (.bat entry follows its neighbours), real hardware, C++ classes with overloaded operators beyond the reviewer's valid2.cpp. (5) The maintainer may rewrite the fix himself; the test is designed to stand alone (it catches ParseExpression- and ParseMulExpression-based operands).

## Related bugs found, not fixed here

Pre-existing on 4da3147 (and v1.32.273 where checked), same in both spellings, not fixed here: sizeof (f) of a function designator is 0 with no diagnostic; sizeof (s.bf) of a bit-field is accepted (gcc: error); sizeof (&lf) is 0; sizeof of an incomplete type silently 0; sizeof ("ab" "cd") is 3 (should be 5); sizeof (struct S){0} and (typedef int) segfault the compiler; k = -int; aborts; fold expression (sizeof (ts) + ...) segfaults; block-scope static_assert trips an assertion at Parser.cpp:12518; binding const T& to an array deduces a pointer type; ParsePostfixExpression consumes a stray :: and does nothing with it. Only the first two were reproduced by me in this pass (fn.c/fnp.c); the rest are the Opus reviewer's observations, listed for follow-up.

## Draft pull request

**Title:** Fix sizeof applied to a unary expression without parentheses

````markdown
`sizeof` only accepts a parenthesised operand. The standard form `sizeof unary-expression` (C89 3.3.3.4, C99 6.5.3) is rejected:

```c
#include <assert.h>
#include <string.h>

int arr[10];
char buf[32];
struct S { char a; int b; long c; } s, *sp = &s;

int main(void)
{
    assert(sizeof arr == 20);
    assert(sizeof arr / sizeof arr[0] == 10);
    assert(sizeof *sp == sizeof s);
    assert(sizeof s.b == 2);
    memset(buf, 0, sizeof buf);
    return 0;
}
```

Reproduce with `oscar64 -ea -g -n example.c` (also with `-bc`, every optimisation level and `-pp`). The first diagnostic is

```
example.c(10, 19) : error 3006: '(' expected
```

Expected: compiles and prints `Emulation result 0`. Older C code uses this spelling a lot: NetHack 3.4.3 has 113 such sites in `src/` alone (`memset(artiexist, 0, sizeof artiexist)`, `sizeof *p`, `sizeof a / sizeof a[0]`), 119 counting string-literal operands, and 32 more in `util/`.

**Root cause.** In `Parser::ParseSimpleExpression`, `case TK_SIZEOF` always calls `ParseParenthesisExpression()` for the operand (Parser.cpp line 8342 on 4da3147), so every operand had to begin with `(`. One routine serves both `sizeof ( type-name )` and `sizeof ( expression )`, since type names parse as `EX_TYPE` expressions. For the same reason a parenthesised expression followed by postfix operators (`sizeof (arr)[0]`, `sizeof (p)->m`) was rejected as well, with "Array expected for indexing" and the like, because the postfix operators were applied to the `sizeof` result.

**Fix.** When the token after `sizeof` is not `(`, the operand is parsed with `ParsePrefixExpression(false)`, which reads one prefix/postfix expression and stops at the first binary operator: `sizeof *p`, `sizeof -x`, `sizeof a[0]`, `sizeof s.m` and `sizeof p->m` take the whole operand, and `sizeof a / sizeof a[0]` is `(sizeof a) / (sizeof a[0])`. When it is `(`, the operand is parsed as before; if it turns out to be an expression rather than a type, its postfix operators are now completed with `ParsePostfixExpression(false, rexp)`, the way `ParseCastExpression` already completes a cast operand. A bare type (`sizeof int`, `sizeof T`) or a brace list (`sizeof {1, 2}`) after `sizeof` is still rejected with the previous `'(' expected`, now reported at the operand. `sizeof...(pack)`, reference stripping and the deferred `EX_PREFIX`/`TK_SIZEOF` for not-yet-defined types are unchanged. 15 added lines in one function.

**Test.** `autotest/sizeofunarytest.c`, registered in `autotest.bat`. Each value is stored before it is compared, or the constant is written first, because `assert(sizeof x == 20)` on its own would also pass with a parser that let the operand swallow the rest of the expression (`sizeof (x == 20)` is never zero). Two deliberately wrong builds (operand parsed with `ParseExpression`, and with `ParseMulExpression`) fail the test in all ten configurations. It covers plain objects, array elements, members through `.` and `->`, dereferences, `&`, unary `- + ~ !`, nested `sizeof`, precedence against `/ - * +` and `?:`, the parenthesised forms with and without postfix operators (`sizeof (arr) + 1 == 21`, `sizeof (int) * 3`, `sizeof (arr)[0]`, `sizeof (sp)->c`), non-evaluation of the operand (`n++`, `++n`, `arr[n++]`, `(n)++`, and a call of an `extern` function that is never defined, which must neither run nor need linking), an array parameter being a pointer, and the `memset(buf, v, sizeof buf)` idiom. It fails with the unmodified compiler in all ten `:test` configurations (error 3006) and passes with the fix.

**Validation** against main `4da3147`, Linux, targeting C64:

- Example and new test, ten configurations (`-ea -g`, `-bc`/`-n` x default/`-O0`/`-O2`/`-Os`/`-O3`): before 0/10, after 10/10 `Emulation result 0`. The test also passes with `-O1`, `-O2 -xz -Oz`, `-O2 -Oo -Ofp`, `-O2 -Ox -Ofp`, `-strict` and in C++ mode (`-pp`); `sizeof...(ts)` on a parameter pack still works.
- Full autotest (`make -k check`): 1541 successful emulations on the baseline, 1551 with the patch and new test, no new failures, exit 0.
- Byte-for-byte comparison of the 159 autotest sources plus 20 small C files from a NetHack port (repros for other Oscar64 issues), five configurations each (895 compiles): all 830 programs both compilers accept are identical; the only status changes are the 10 for the two files that use `sizeof` without parentheses (error -> ok); the remaining 55 fail on both compilers for unrelated reasons.
- `sizeof E` and `sizeof (E)` give identical programs for 25 operand forms in three configurations (75/75), and a function mentioned only inside `sizeof` is not linked.
- Still rejected, with the error at the operand as gcc reports it: `sizeof int`, `sizeof unsigned char`, `sizeof struct S`, `sizeof T`, `sizeof int *`, `sizeof void`, `sizeof {1, 2}`, `sizeof (int) n`, `sizeof arr arr`, bare `sizeof;`.

Known limitations: `sizeof` of a function designator (`sizeof f`, gives 0) and of a bit-field member (`sizeof s.bf`) are accepted without a diagnostic. Both were already accepted in the parenthesised spelling before this change, so nothing new is admitted, but the unparenthesised spelling now reaches the same gap. The compound-literal form `sizeof (T){0}` is unchanged (a parenthesised type is not continued with postfix operators). Not tested: the Windows build (the `autotest.bat` entry follows its neighbours) and real hardware.

This patch was prepared with AI assistance (Claude Code) while porting NetHack 3.4.3 to the C64, and checked by two further AI review passes; every number above comes from running the commands described.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
````
