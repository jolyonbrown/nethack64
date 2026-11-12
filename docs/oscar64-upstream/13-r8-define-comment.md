# 13. Fix block comment continuing past the end of a #define line

| | |
|---|---|
| Branch | `fix/r8-define-comment` in `~/src/oscar64-dev`, commit `9dfa87d84165`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/13-r8-define-comment.patch`](../../tools/oscar64-upstream/patches/main/13-r8-define-comment.patch) |
| Kind | rejects valid C (preprocessor) |
| Since | v1.32.273 and main |
| NetHack | Compat #4 (repro r8): a block comment that starts on a `#define` line and ends on the next, 16 lines in `global.h`, `mkroom.h` and others. Workaround: `tools/oscar_normalize.py`. |
| Reviews | Opus (round 1, ran probes): submit-after-changes, 2 high, 2 medium, 2 low; Codex (read the diff): submit after changes; fix-up: ready; final Codex check: submit after changes |
| Recommendation | **Submit.** |

## In plain words

The last check found two sentences in the pull-request description that did not match the code: one said a newline kept inside the macro is what stops a star at the end of one line from pairing with a slash on the next, when in fact the compiler throws away the comment text it has read before pulling in each new line; the other called a comment in test F multi-line when it sits on one line. Both are now worded correctly. The code, the test and the commit message needed no change, so the branch is still the same single commit on top of upstream, and all the earlier evidence (full test suite with no new failures, 830 byte-identical programs, the example and test fixed in every configuration, long comments and unclosed comments behaving sensibly) was re-checked against the binary built from that commit and still holds.

## The fix

No code or test change this round. Both final-check findings were about PR prose and both were right: (1) the sentence saying the newline stays in the body was replaced with the actual mechanism (Scanner.cpp truncates the buffer at the comment opener before each appended line, so a trailing '*' and the newline are discarded; backslash splicing happens in NextLine before this scan, so spliced delimiters still work); (2) the description of test F now says it has a comment inside the body and a trailing comment over three lines. Because the fix-up round's PR body was not on disk, the whole body was rewritten from the pre-fix-up version plus the commit message, carrying the earlier review corrections (real error lines 3005/3037 and 'eleven errors', the corrected #include side note, the 'NextLine already reads continuation lines for splices' wording, the corpus described as 153 autotest sources plus 26 files of our own, the 1,541/1,551 and 830 numbers from the fix-up logs) and now also describing the quote tracking, the discarding of comment text, the unclosed-at-EOF error and the 40 KB/200 KB checks. The commit message was already accurate and is unchanged.

## Regression test

autotest/prep_define_comment_test.c (registered in autotest/autotest.bat after block_comment_test.c), unchanged this round: 26 macros, A-W plus BS/UNUSED/FLAG/CLOSE, covering continuation onto the next line (also with NetHack's tab layout), closed comment followed by more body, // comment, // inside a closed comment, a second comment running on, F (inner single-line comment plus a three-line trailer), string holding /*, comment-only body, tokens after the closing */ on the second line (J == 17), three-line comment then //, M (star/newline/slash does not close), N and O (splice-formed delimiters), P (quotes inside a comment), Q/R/S/T/BS (character constant, escaped quote, "\"/*", "\\" before comments), UNUSED/FLAG/CLOSE (the silent-swallow case), U/V (directive inside the comment not processed) and W (used in #if). Fails rc 20 x10 on 4da3147, passes rc 0 x10 after; gcc -std=c99 -pedantic -Wall exit 0.

## Evidence

**Repro matrix.** All 77 review probes plus my additions run with 4da3147 (before), the first fixup build and the final compiler in the 10 configurations -ea -g {-bc|-n} x {none,-O2,-O0,-Os,-O3}, 60 s timeout; the final build gives the same result as the first fixup build on every probe. Newly fixed (before 20, final 0 x10; gcc 0): r8 repro, example.c, both test versions, prep_define_comment_extra.c, p_cpp.cpp, p_D.c, p_splice.c, p_tail.c, a01 (the 16 NetHack lines), a07, a09, a10 (before rc 1: V got defined), a11, a13-a18, a20-a24, a25.cpp, c01 CRLF, c02, c03, c04, c05, c08, c12b, c14, c15.cpp, c16, f02, h01, e02 (#repeat). Regressions of ee0e277 now gone (before 0, ee0e277 fail, final 0 x10): a02, a02.cpp, a03, a04, x01; x02 returns 1 with before/final/gcc (ee0e277: 2); x03 rejected by before/final/gcc (ee0e277: accepted). Hang gone: b01/b02/b03 (30 KB/40 KB/200 KB comment) before rc 139 (segfault), ee0e277 b02/b03 rc 124 (hang), final 0 x10. 32 KB line probes y01/y02/y03: final terminates in all (y01 error, y02/y03 run 0). Unchanged and correct both before and after (0 x10): a12, a19, a24b, a24c, f01, p_if, c11, g02. Now an error, was silently accepted (gcc also rejects): p_eof, c13, c06, e01. Pre-existing failures unchanged (20 before and after, gcc 0 unless noted): a05/a05b/a05c/a06/a26 (character after the macro name dropped), c07 (#if 0 group ignores comments), c09/c09b/c10/d01/d02 (nested XSTR/XCAT), g01 and p_include (#include followed by a continued comment), e03 (#for body), a08, c12 (gcc also rejects). In the compiled autotest run the new test passes in all 10 configurations.

**Autotest.** make -k -j4 -C /home/jolyon/nethack64/build/oscar64-wt/r8-define-comment/make check run twice on the final source (once before and once after a structure-only edit of the comment branch; probe results of the two binaries are identical). Final log /home/jolyon/nethack64/build/oscar64-wt/r8-define-comment-scratch/autotest-fixup.log (first run kept as fixup/autotest-fixup-run1.log). autotest_diff.py /home/jolyon/nethack64/build/oscar64-wt/autotest-base-4da3147.log <log>: emulations base 1541, new 1551 (1541 + the 10 configurations of the new test); new failures 0; fixed 0; failing in both 0; exit 0. Both runs end normally. The bin/oscar64 relinked by make check is byte-identical to the binary used for the probes (cmp).

**Corpus.** corpus_diff.py ~/src/oscar64-base/bin/oscar64 (4da3147) vs /home/jolyon/nethack64/build/oscar64-wt/r8-define-comment/bin/oscar64 --out /home/jolyon/nethack64/build/oscar64-wt/r8-define-comment-scratch/corpus-fixup -j4 (log corpus-fixup.log, run after make check had finished): 179 files (159 autotest sources + 20 nethack64 tests/oscar64-repros files) x 5 configurations (n-O2, n-Os, n-O0, n-O3, bc-O2) = 895 compile pairs. Both compile: 830; identical: 830; different: 0. Status changed: 10 = autotest/prep_define_comment_test.c and oscar64-repros/r8_multiline_comment_on_define.c, error -> ok in all 5 configurations each (the two files that use the fixed construct). Both fail: 55 (895 - 830 - 10; autotest's deliberate must-fail sources and the still-open nethack64 repros, same status with both compilers). The testint16mul.c -bc quirk did not appear (0 differences). A first corpus attempt lost its summary when the wrapper shell was detached after 10 minutes under a load average above 20; it was rerun under nohup and the reported numbers are from that complete run.

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| both | high | Naive quote tracking (every '"' toggles, no char constants, no escapes) lets a /* inside a string pull in following source lines: valid code rejected or silently miscompiled (Opus a02/a03/a04; Codex TEXT and UNUSED/FLAG/END examples) | fixed |
| both | high | Infinite loop when a #define's comment does not close within the 32 KB line buffer (Opus b02/b03 confirmed hang; Codex flagged it as an unverified capacity gap); the author's risk note claimed an error is reported | fixed |
| opus | medium | Variants left unfixed by the same root cause: a '"' character constant or an escaped quote before a multi-line comment (c03, c04) | fixed |
| both | medium | Regression test misses the lexical boundary the patch changes (quotes, escapes, directive inside the comment, use in #if, star/newline/slash, splice-formed delimiters, unused macro with a false opener, stringize/paste) and the author counted 13 macros where there were 12 | fixed |
| opus | low | PR body quotes a compiler error the unmodified compiler never prints | fixed |
| opus | low | PR's #include side note states the wrong cause (claims the rest of the include line is discarded) | fixed |
| opus | low | PR wording: 'the same way NextLine joins backslash-spliced lines' is loose; 'local repro sources' is opaque to upstream; all numbers must be re-run | fixed |
| opus | low | Process note: commit trailer names 'Claude Fable 5.1' rather than the attribution text in the original task | out-of-scope |
| codex | medium | Default argument on NextLine preserves ordinary calls but not every out-of-tree use (member-function-pointer types, mangled signature change) | fixed |
| codex | low | Capacity failure should report a size limit rather than describe a closed comment as unclosed | deferred |
| codex | low | Add an automated expected-failure test for an unused macro with a genuinely unterminated comment | deferred |
| codex | medium | Validation only covers programs with real comments; the byte-identical corpus cannot see programs containing "\"/*" with no comment | fixed |

<details><summary>Evidence for each finding</summary>

1. **Naive quote tracking (every '"' toggles, no char constants, no escapes) lets a /* inside a string pull in following source lines: valid code rejected or silently miscompiled (Opus a02/a03/a04; Codex TEXT and UNUSED/FLAG/END examples)** (fixed)

   Reproduced with the ee0e277 compiler: a02_quote_charconst.c error 3006 "')' expected" (before and v1.32.273: run 0); a03 fires its #error; a04 compiles silently and the program returns 1; Codex x01 (#define TEXT "\"/*") error 3006 "Multiline comment not closed"; Codex x02 returns 2 instead of 1 (before: 1); Codex x03 (int broken = ;) accepted. Fix: track both quote kinds with backslash escapes in the body loop, same scheme as the macro-argument collector (Scanner.cpp ~1164-1200). Final compiler: a02/a03/a04/x01 run 0 in all 10 configurations (also a02 as .cpp); x02 returns 1 like before and gcc; x03 rejected with the same error as before. The reviewer's suggested tracker was evaluated and adopted (it is the existing argument-collector logic).

2. **Infinite loop when a #define's comment does not close within the 32 KB line buffer (Opus b02/b03 confirmed hang; Codex flagged it as an unverified capacity gap); the author's risk note claimed an error is reported** (fixed)

   ee0e277: b02_long_comment_40k.c and b03_long_comment_200k.c killed by 60 s timeout (rc 124) in all configurations; before compiler segfaults on them (rc 139, pre-existing). Cause: fgets stores at most 32767 chars, so NextLine(true) at s=32767 returns true without appending and the loop never advances. Fix: before appending, drop the comment text read so far (mPreprocessor->mLine[ctext] = 0; slen = ctext), so the buffer can never fill, and treat 'nothing appended' (!mLine[slen]) as failure as a termination guarantee. Final: b01/b02/b03 compile and run 0 in all 10 configurations. Degenerate case y01 (a 32767-character physical line whose /* ends exactly at the buffer limit) terminates with 'Multiline comment not closed'; y02 (/* a few bytes earlier) compiles; y03 (40000-char line) compiles. I evaluated the reviewer's two variants and took the stronger one (drop text) since it makes comment length unlimited rather than turning the hang into a misleading error.

3. **Variants left unfixed by the same root cause: a '"' character constant or an escaped quote before a multi-line comment (c03, c04)** (fixed)

   Before and ee0e277: c03_charconst_quote_multiline.c and c04_escaped_quote_multiline.c error 3005 ('used' / 'with'), gcc 0. Final compiler: 0 in all 10 configurations. Both patterns are now in the regression test (Q and R).

4. **Regression test misses the lexical boundary the patch changes (quotes, escapes, directive inside the comment, use in #if, star/newline/slash, splice-formed delimiters, unused macro with a false opener, stringize/paste) and the author counted 13 macros where there were 12** (fixed)

   autotest/prep_define_comment_test.c now has 26 macros (A-L kept; added M star-newline-slash, N/O splice-formed closer/opener, P quotes inside the comment plus tail tokens and //, Q '"', R "a\"b", S "\"/*", T(c) with '"' and "/*", BS "\\", UNUSED/FLAG/CLOSE with #ifndef FLAG #error, U with '#define V 2 */' inside the comment and #ifdef V #error, W used in #if). gcc -std=c99 -pedantic -Wall and g++ -std=c++11 accept it with no warning and exit 0. Before compiler: rc 20 x10. ee0e277 binary: fails x10 (rc 1: Q's continuation taken as code, then #error FLAG). Final: 0 x10, also with -strict, -pp and as a .cpp copy. Stringize/paste of comment-bearing macros was probed (c09, c09b, c10, d01, d02) and fails identically before and after, including for single-line comments, so it is a pre-existing XSTR/XCAT bug and not added to the test. Negative cases cannot live in autotest; checked as scratch probes (see regression_test).

5. **PR body quotes a compiler error the unmodified compiler never prints** (fixed)

   Ran 4da3147 on the PR example: 11 errors; first two are '(4, 24) : error 3005: Identifier not defined 'carries'' and '(4, 27) : error 3037: Semicolon expected'. The claimed '(4, 27) error 3006 Declaration starts with invalid token '*'' does not appear. PR text corrected.

6. **PR's #include side note states the wrong cause (claims the rest of the include line is discarded)** (fixed)

   Preprocessor.cpp OpenSource sets mLine[0] = 0 only; the scanner keeps reading from mOffset. Probe g02 ('#include "inc/g1.h" int g2 = 2;') compiles and g2 exists with both compilers; g01 (comment opened after an #include) reports the unclosed comment inside the header. PR note reworded accordingly.

7. **PR wording: 'the same way NextLine joins backslash-spliced lines' is loose; 'local repro sources' is opaque to upstream; all numbers must be re-run** (fixed)

   PR now says the next line is appended to the line buffer and the newline is kept in the body (a splice deletes backslash and newline); the corpus is described as 159 autotest sources plus 20 small repro files from our port; all numbers in the PR come from the final runs (autotest 1,541/1,551, corpus 830/830/0/10).

8. **Process note: commit trailer names 'Claude Fable 5.1' rather than the attribution text in the original task** (out-of-scope)

   Trailer lines kept exactly as they were in ee0e277, as instructed for this step (Co-Authored-By: Claude Fable 5.1, Claude-Session link). The model that ran this and the previous step is Fable 5.1, so the trailer is truthful; Jolyon can change it before pushing if he prefers.

9. **Default argument on NextLine preserves ordinary calls but not every out-of-tree use (member-function-pointer types, mangled signature change)** (fixed)

   True in principle; no in-tree caller is affected (Scanner.cpp 976, 1155, 2561 still call NextLine()). PR text now says 'existing callers are unchanged' rather than claiming all callers are unaffected.

10. **Capacity failure should report a size limit rather than describe a closed comment as unclosed** (deferred)

   With the comment text dropped before each appended line, comment length is no longer limited at all (b03, 200 KB, compiles). The only remaining path to that message is a #define line that is itself at least 32767 characters before the opener (probe y01), where the pre-existing 32 KB physical-line limit already mishandles input for every directive. A new diagnostic for over-long lines belongs in a separate change; noted as a limitation in the PR.

11. **Add an automated expected-failure test for an unused macro with a genuinely unterminated comment** (deferred)

   autotest's :test target only runs must-compile cases, so a must-not-compile case cannot be registered there without a new driver target. Checked as scratch probes instead: p_eof.c, c13_eof_unclosed.c (unused macro, comment never closes), c06_header_unclosed.c (in a header) and e01_for_guard.c (#for body) all report 'error 3006: Multiline comment not closed' with the final compiler; before, the first three were silently accepted.

12. **Validation only covers programs with real comments; the byte-identical corpus cannot see programs containing "\"/*" with no comment** (fixed)

   Correct observation: the quote regression was invisible to the corpus and autotest. Covered now by probes a02/a03/a04/x01/x02/x03 (programs with no block comment) and by S, T, BS, UNUSED/FLAG/CLOSE in the regression test, all passing with the final compiler and all behaving as with gcc and the before compiler.

</details>

## Last round: final-check findings and what happened to them

Changed in the last round: text-only. Commit before it: `9dfa87d84165`.

| From | Severity | Finding | Resolution |
|---|---|---|---|
| final-check Codex #1 | low | PR text: 'The newline stays in the body' misexplains why *+newline+/ cannot close a comment | fixed |
| final-check Codex #2 | low | PR text: F's inner comment is single-line, not multi-line | fixed |
| own re-check | low | PR body had to be reconstructed; all other claims re-verified against code and logs | fixed |
| own re-check (Codex earlier #2 boundary) | low | Physical line of exactly 32767 chars with '/*' at its end gives 'Multiline comment not closed', not a hang | deferred |
| task rules | low | Commit trailers (Co-Authored-By model name, Claude-Session link) | left-for-jolyon |

<details><summary>Evidence, and what was re-run</summary>

1. **PR text: 'The newline stays in the body' misexplains why *+newline+/ cannot close a comment** (fixed)

   Confirmed in oscar64/Scanner.cpp:844-845: before NextLine(true) the buffer is truncated at ctext (just after '/*'), so the comment text read so far, including any trailing '*' and the newline, is discarded; the appended line starts at ctext. Preprocessor::NextLine (Preprocessor.cpp:893-908) performs backslash-newline splicing while reading, before the scanner sees mLine, so splice-formed delimiters still work (tests N, O; probes a12/a13 rc 0 x10). Test M (star at end of line, slash at start of next, M == 11) and probe a11 pass 0 x10 on the current binary. The PR body now says the discarding is what prevents the combination and that splicing happens before this scan. The commit message never made the newline claim, so it is unchanged.

2. **PR text: F's inner comment is single-line, not multi-line** (fixed)

   autotest/prep_define_comment_test.c:16: `#define F(x) ((x) /* inner */ + 1) /* trailer` + two more lines. Only the trailing comment spans lines. PR body now reads 'a function-like macro with a comment inside the body and a trailing comment over three lines'. Test left as is (coverage of a continued comment in the middle of a body with tokens after it is already provided by J).

3. **PR body had to be reconstructed; all other claims re-verified against code and logs** (fixed)

   The fix-up round's PR body was not on disk (only the pre-fix-up one in author-report.md), so the body was rewritten from it plus the commit message, with every number checked: before compiler on example.c prints 11 errors, first two 3005 'carries' and 3037 'Semicolon expected'; gcc -std=c99/-c89 -pedantic and clang 18 accept the example; 16 NetHack 3.4.3 #define lines with a comment left open (counted over the whole pristine tree, includes sys/amiga); 579b72c = 'Fix block comment parsing'; test defines 26 macros (27 #define lines, one of which is inside the U comment); corpus = 179 files = 153 autotest + 26 nethack64 repros, 830 identical, 10 status changes (corpus-fixup.log); autotest 1541 -> 1551 emulations, autotest_diff.py new failures 0 (autotest-fixup.log). The #include side note uses the corrected cause from the Opus review (rest of the include line is scanned as the start of the header).

4. **Physical line of exactly 32767 chars with '/*' at its end gives 'Multiline comment not closed', not a hang** (deferred)

   probes/y01_line_32767_open_at_end.c: rc 20 x10 after (and 20 x10 before), message 'error 3006: Multiline comment not closed' at (1, 9); y02 (32760-char line) and y03 (40000-char line) rc 0 x10 after. The !mLine[slen] check catches the 'nothing appended' case, so there is no loop. Lines over the 32 KB buffer are a pre-existing limit of the reader; a dedicated size-limit message would be a separate change. Mentioned in the PR body as reporting the existing error.

5. **Commit trailers (Co-Authored-By model name, Claude-Session link)** (left-for-jolyon)

   Not touched, per the rules for this round.

**Re-validation.** Text-only round: no source or test change, so nothing rebuilt and the commit was not amended (branch fix/r8-define-comment is one commit 9dfa87d on 4da3147, `git status` clean; bin/oscar64 mtime 05:37 is after Scanner.cpp 05:20 and is the binary make check relinked for autotest-fixup.log). Re-checked on that binary with run10.sh (oscar64 -ea -g {-bc|-n} x {none,-O2,-O0,-Os,-O3}): prep_define_comment_test.c, example.c, r8_multiline_comment_on_define.c, a04_silent_wrong.c, a11_star_nl_slash.c, b02 (40 KB comment), b03 (200 KB), y02, y03, prep_define_comment_test_cpp.cpp all rc 0 in 10/10; p_eof.c, x02_codex_unused.c, y01 (32767-char line) rc 20 in 10/10 with 'Multiline comment not closed' (no hang). Before compiler (~/src/oscar64-base, 4da3147): test, example, repro, y01, y02 rc 20 x10. gcc -std=c99 -pedantic -Wall on the test: compiles, exit 0 (c89 fails only on the // comments, as expected). autotest_diff.py baseline vs autotest-fixup.log: emulations 1541 -> 1551, new failures 0, fixed 0, failing in both 0, exit 0. corpus-fixup.log: 179 files x 5 configs, both compile 830, identical 830, different 0, status changed 10 (the new test and the r8 repro, error -> ok, 5 configs each). Final PR text saved at /home/jolyon/nethack64/build/oscar64-wt/r8-define-comment-scratch/final/pr-title.txt and /home/jolyon/nethack64/build/oscar64-wt/r8-define-comment-scratch/final/pr-body.md.

</details>

## Final check (Codex, read-only, on the final commit)

<details><summary>SUBMIT AFTER CHANGES</summary>

VERDICT: SUBMIT AFTER CHANGES

1. **[low] PR text: “The newline stays in the body …”** — This contradicts `Scanner.cpp:844`: truncating at `ctext` removes all accumulated comment contents, including the newline and any trailing `*`. Replace this explanation with: “Discarding the accumulated comment contents prevents a trailing `*` from combining with `/` on the next physical line. Backslash-newline splicing happens before this scan, so splice-formed delimiters still work.” The code and boundary tests appear consistent; the explanation needs correcting.

2. **[low] PR text: “a function-like macro with inner and trailing multi-line comments”** — In `autotest/prep_define_comment_test.c:16`, F’s inner comment is single-line; only its trailing comment spans lines. Reword that claim, or extend the inner comment across a newline.

No additional code defect identified from the supplied diff. The substantive earlier findings appear addressed, and the regression test exercises both the original failure and the quote-tracking regressions. The supplied validation supports submission once these descriptions are corrected; I have not independently executed it.

</details>

## Before submitting

- Make the AI-assistance line the same in every PR body (some end with a sentence, some with a "Generated with Claude Code" footer), as Jolyon decides.
- Commit trailers: drop the `Claude-Session:` line and use one `Co-Authored-By:` line, as Jolyon decides for all PRs (see OSCAR64-UPSTREAM.md).

## Risks and limitations

Unchanged from the fix-up round: NextLine's signature gains a defaulted parameter (source-compatible for callers, not for member-function-pointer uses, none in tree); a #define whose comment never closes at EOF is now an error (gcc agrees); diagnostics inside a continued directive carry the last physical line read; a single physical line over the 32 KB buffer that opens a comment at its very end reports 'Multiline comment not closed' rather than a size-limit message (pre-existing buffer limit, no hang). Out of scope and stated in the PR: #include followed by a continued comment. Pre-existing and not mentioned: the #for body is still a raw slice; the character right after a macro name without a space is dropped. Process risk: the fix-up round's PR body was not available on disk, so the body returned here is a reconstruction; it was checked claim by claim against the code, logs and fresh compiler runs, but Jolyon may want to diff it against whatever the fix-up round returned.

## Related bugs found, not fixed here

All fail identically before and after, none fixed here: (a) The character right after an object-like macro name or a function-like macro's closing parenthesis is dropped: '#define X/* c */1' and '#define F(a)(a+1)' fail (a05, a05b, a05c, a06, a26). (b) '#if 0' groups do not track block comments, so a directive inside a comment in a skipped group is processed (c07). (c) Nested stringize/paste (XSTR(x) STR(x)) of a macro whose body carries any comment, even a single-line one, gives the wrong string / wrong token (c09, c09b, c10, d01, d02). (d) The rest of an #include line is scanned as the start of the included file because OpenSource only sets mLine[0] = 0, so a comment opened after '#include' runs into the header (g01, p_include) and code after the include is accepted (g02). (e) The Oscar64 #for body collector (Scanner.cpp ~697-713) is the same raw slice the #define collector was, including the every-'"'-toggles quote tracking (e03). (f) Physical lines over 32767 characters are split by fgets and read as two lines (pre-existing, y01/y03 show different behaviour before and after only because of where the opener lands). (g) 4da3147 segfaults (rc 139) on b01/b02/b03 after the cascade of errors from a long split comment; moot with the fix, but the crash path in the before compiler is a separate error-recovery bug. (h) Adjacent string literals in a define body give a spurious out-of-bounds warning (reported by Opus, not re-probed here).

## Draft pull request

**Title:** Fix block comment continuing past the end of a #define line

````markdown
A block comment that starts on a `#define` line and closes on a later line is treated as code from the second line on:

```c
#include <assert.h>

#define Y 0 /* a comment that
               carries on here */

int main(void)
{
    assert(Y == 0);
    return 0;
}
```

Reproduce with `oscar64 -ea -n example.c` (same with `-bc` and at every optimisation level). The unmodified compiler stops with exit status 20 after eleven errors, the first two being:

```
example.c(4, 24) : error 3005: Identifier not defined 'carries'
example.c(4, 27) : error 3037: Semicolon expected
```

Expected: `Y` is `0` and the program compiles and returns 0. Comments are replaced by one space in translation phase 3, before directives are processed in phase 4 (C89 2.1.1.2, C99 5.1.1.2), so the comment belongs to the directive and the directive ends at the end of the line the comment closes on. gcc and clang accept the example. NetHack 3.4.3 has 16 such `#define` lines (`global.h`'s `PL_PSIZ`, `mkroom.h`, `monflag.h`, ...), which is how we found it.

Root cause: in `Scanner::NextPreToken`, the `TK_PREP_DEFINE` branch takes the macro body as a raw slice of the current physical line, stopping only at end of line or at a `//` outside a string, and then skips to the end of the line. It does not know about block comments, so the continuation of the comment is left for the code scanner. The same loop also lets a `//` inside a closed comment end the body early (`#define D 4 /* has // inside */ + 10` becomes `4 /* has `, and on expansion the scanner's comment skip then swallows the code that follows the use of `D` until the next `*/`), and its quote tracking toggles on every `"`, so an escaped quote or a `'"'` character constant leaves it in the wrong state. Commit 579b72c fixed comments inside macro arguments; the body collection was not covered.

The fix is in that body-collecting loop in `Scanner.cpp`, plus a `bool append = false` parameter on `Preprocessor::NextLine`:

- A block comment is skipped as a unit. If it is still open at the end of the line, the next physical line is appended to the line buffer with `NextLine(true)` (`NextLine` already reads continuation lines for backslash splices; append mode keeps what is in the buffer) and scanning continues, so tokens after the closing `*/` stay in the body and a `//` after it still ends the directive.
- Before each line is appended, the comment text read so far is discarded, so the 32 KB line buffer does not limit the length of the comment. Discarding it is also what keeps a `*` at the end of one line from combining with a `/` at the start of the next. Backslash-newline splicing happens in `NextLine` before this scan, so a delimiter formed by a splice still works.
- String and character constants are tracked with their escapes, as the macro argument collector does, so a `/*` or `//` inside `"\"/*"` or after `'"'` is not taken for a comment delimiter. (Without this, the first two changes would make `#define S "\"/*"` pull the following source lines into the body of `S`.)
- If the comment is still open at the end of the file, or the directive is being read from a macro expansion rather than the source buffer, or a single physical line is longer than the buffer, the existing "Multiline comment not closed" error is reported. Before, an unused macro with an unclosed comment was accepted silently. Existing `NextLine()` callers are unchanged.

Regression test `autotest/prep_define_comment_test.c` (registered in `autotest.bat`) defines 26 macros covering: a comment continuing onto the next line (also with the tab layout from NetHack), a comment closed on the line followed by more body, a `//` comment, `//` inside a closed comment, a second comment on the line that runs on, a function-like macro with a comment inside the body and a trailing comment over three lines, a string containing `/*`, a body that is only a multi-line comment, tokens after the closing `*/` on the second line (`#define J 7 /* ...\n ... */ + 10` gives 17), a three-line comment followed by a `//` comment, a `*` at the end of one line and `/` at the start of the next (does not close the comment), opening and closing delimiters formed by a splice (do), quotes inside a comment, a `'"'` constant, an escaped quote and `"\"/*"` in front of a comment, a directive inside the continued comment (must not be processed), and such a macro used in `#if`. gcc `-std=c99 -pedantic -Wall` accepts the test and it exits 0.

Validation against main `4da3147` on Linux:

- The example, the new test and a file with six of NetHack's lines (`PL_PSIZ`, `ROOMOFFSET`, `G_EXTINCT`, ... checked for their values) fail in all 10 autotest configurations (`-ea -g`, `-bc`/`-n`, default/`-O2`/`-O0`/`-Os`/`-O3`) before and pass in all 10 after. A C++ copy of the test passes as well.
- Comments of 40 KB and 200 KB compile; a `#define` whose comment never closes is an error (gcc rejects it too). `#if`, `#ifdef`, `#ifndef` and `#undef` followed by a two-line comment already worked and still do.
- Full autotest (`make -k -j4 -C make check`): 1,541 successful emulations on the baseline, 1,551 with the patch and the new test; no failing step in either run.
- The 153 autotest sources (plus 26 small test files of our own) compiled with both compilers in 5 configurations: all 830 programs accepted by both are byte-identical; the only status changes are the new test and our repro of this bug (error -> ok).

Not addressed here, noted for completeness: `#include <x.h>` followed by a block comment that continues on the next line fails before and after this patch. `Preprocessor::OpenSource` leaves the scanner on the rest of the `#include` line, which is then read as the start of the included file, so a comment opened there runs into the header.

This fix was prepared with AI assistance (Claude Code), including the analysis, the test and the validation runs listed above; the numbers are from those runs.
````
