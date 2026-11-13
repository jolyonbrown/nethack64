# Oscar64 fixes proposed upstream

Status 2026-11-12: 18 fixes finished. #1-#15 reviewed by Opus and Codex; #16-#18 by
Opus, with a Codex check still to do before any of them goes upstream. Nothing has been
sent upstream: no PR, no issue (17 queued as drafts in the fork, see below). One page per
proposed PR in [`docs/oscar64-upstream/`](oscar64-upstream/), each with a plain
explanation, the evidence, every review finding and what happened to it, the risks,
and the draft PR text. The commits themselves are in
[`tools/oscar64-upstream/patches/main/`](../tools/oscar64-upstream/patches/main/)
(`git am` onto upstream main 4da3147; GPL-3.0, like Oscar64).

## Jolyon's decisions (2026-11-12)

Made on the decision page (claude.ai artifact `9Q2qbWw5XfEB3NQsk1cZuy`, private to
Jolyon), which shows each PR's explanation and records the choice:

1. **Which PRs to open:** none yet. All are **on hold**, except #14
   (`r13-string-literal`): **do not send** (Jolyon: "read the response to issue #90 and
   i guess that's their choice"). It stays a one-line workaround in `port/` (T1.12).
2. **Fork:** yes. Created 2026-11-12: <https://github.com/jolyonbrown/oscar64>
   (public). The finished PRs on hold are queued there as branches `fix/<id>`, one
   commit each on upstream main 4da3147 (#6 sits on #1), each with a **draft PR inside
   the fork** carrying the upstream PR text: fork PRs #1-#13 and #15-#18 are our numbers
   (#6 targets `fix/r19-null-compare` and #16 targets `fix/pr440-runaway`, so each shows
   only its own commit). #14 stays local; the fork's number 14 is a closed placeholder
   issue that keeps the numbers in step. In the local clone the fork is the remote `fork`. Nothing
   is opened upstream, but fork text can still show there: a bare `#N` in a fork PR
   links to upstream's issue or PR of that number. Draft #15 wrote `#440` bare, and
   since 2026-11-12 23:09 upstream PR 440's page lists the draft; putting the numbers in
   code spans on 2026-11-13 did not remove that entry. **In fork text, write upstream
   numbers in code spans** (`` `#440` ``), and never `@`-mention anyone.
   **Never merge a draft into the fork's `main`**: it
   mirrors upstream main, so that each branch stays one clean commit to send.
3. **Attribution:** each commit ends with one `Co-Authored-By: Claude
   <noreply@anthropic.com>` line and no session link; each PR body ends with
   "Prepared with AI assistance (Claude Code); the numbers above come from the
   validation runs described." Applied to #1-#14 by a message-only rewrite (every
   tree identical to the validated one); #15-#18 were finalised with it.
4. **The compiler nethack64 builds with:** [ADR-0007](decisions/ADR-0007-oscar64-patched-pin.md)
   accepted (v1.32.273 plus `tools/oscar64-upstream/patches/pin/`). Adding a further
   fix to it (the `shknam.c` and `makemon.c` ones) is asked for each time.

**Sending a queued PR**, once Jolyon approves it: rebase the branch if upstream main
has moved (still 4da3147 on 2026-11-12) and re-run its evidence, do the "Before
submitting" items on its page, then open the same branch against upstream with the
page's title and body (the part of the fork draft below its line), and close the fork
draft with a link to the upstream PR:

```sh
gh pr create --repo drmortalwombat/oscar64 --base main \
  --head jolyonbrown:fix/<id> --title "<title>" --body-file <body.md>
```

Our own compiler does not depend on any of this: nethack64 builds with v1.32.273 plus
`tools/oscar64-upstream/patches/pin/` (ADR-0007), applied by `build-pin.sh` and the
setup scripts, whatever happens to the PRs.

Suggested order and pace, when the time comes: the four wrong-code fixes first (#1
to #4) and #15 with or right after #4, then #6 once #1 is merged (it is stacked on
#1), then the rest a few at a time. Most outside PRs since August were merged or
closed within a few days; a few took two to five weeks. The maintainer often keeps
the contributor's regression test and writes his own version of the fix ("Picked up
your test but made a slightly different fix", PRs #442, #443, #447), so the tests and
the root-cause write-ups matter as much as the code.

## The proposed PRs

"Wrong code" means the compiler silently produces a program that computes the wrong
answer; "rejects valid C" means it refuses a correct program (nethack64 works around
each of those already).

| # | Proposed PR | Kind | For NetHack (repro, compat row) | Recommendation |
|---|---|---|---|---|
| 1 | [Fix pointer compared with integer constant 0 folding as not equal](oscar64-upstream/01-r19-null-compare.md) | wrong code (silent) | r19 (#23): `invent != 0` | Submit first. |
| 2 | [Fix sign extension when folding loads of signed values from known bytes](oscar64-upstream/02-r20-abs-member.md) | wrong code (silent) | r20-r22 (#24-#26) | Submit. |
| 3 | [Fix merging of identical functions whose address is taken](oscar64-upstream/03-dropped-init-fn.md) | wrong code (silent) | function-pointer tables | Submit. |
| 4 | [Fix function pointer members of global structs](oscar64-upstream/04-fnptr-member.md) | regression on main, plus wrong code on v1.32.273 | all of NetHack on main; r23 (#27) | Submit, high priority: it is a regression on main that breaks any program with function pointers in a global struct. |
| 5 | [Fix wrong exit data set of merged blocks and wrong exit block after value select expansion](oscar64-upstream/05-o0-nested-cond.md) | compiler crash with native code (wrong code once the crash is fixed alone) | none (`-O0` only) | Submit, both fixes in one PR: the first alone turns a compiler crash into wrong code. |
| 6 | [Fix comparison of function pointer with function name](oscar64-upstream/06-r16-fnptr-compare.md) | rejects valid C | r16 (#20): `windows.c`, `dig.c` | Submit after #1 is merged (the branch is stacked on #1; without it `0 == f` compiles to the wrong answer). |
| 7 | [Fix union pointer to const union pointer conversion](oscar64-upstream/07-r15-union-const.md) | rejects valid C | r15 (#19): 87 `add_menu` calls | Submit. |
| 8 | [Fix nested conditional in the middle operand of ?:](oscar64-upstream/08-r2-nested-conditional.md) | rejects valid C | r2 (#9): `pray.c` | Submit. |
| 9 | [Fix sizeof applied to a unary expression without parentheses](oscar64-upstream/09-r3-sizeof-unary.md) | rejects valid C | r3 (#6): 117 sites | Submit. |
| 10 | [Fix braced initializer for scalar variables](oscar64-upstream/10-r12-braced-scalar.md) | rejects valid C | r12 (#16): `decl.c` | Submit. |
| 11 | [Fix register storage class not accepted](oscar64-upstream/11-r10-register.md) | rejects valid C | r10 (#2): thousands | Submit. |
| 12 | [Fix spaces and tabs between '#' and a preprocessor directive name](oscar64-upstream/12-r7-hash-space.md) | rejects valid C (preprocessor) | r7 (#3): most headers | Submit. |
| 13 | [Fix block comment continuing past the end of a #define line](oscar64-upstream/13-r8-define-comment.md) | rejects valid C (preprocessor) | r8 (#4): 16 lines | Submit. |
| 14 | [Fix string literal to char * conversion in C](oscar64-upstream/14-r13-string-literal.md) | rejects valid C (by design upstream) | r13 (#17): `mail.c` | Do not open as a PR now. |
| 15 | [Fix exponential walks over chains of conditionals](oscar64-upstream/15-pr440-runaway.md) | compiler runs out of memory (exposed on main by #440) | r26 (#30): `explode.c` | Submit early, with or right after #4: it fixes an out-of-memory regression that #440 exposed, and main needs #4 before it can compile `explode.c` at all. |
| 16 | [Fix exponential walks and a stack overflow in native code block checks](oscar64-upstream/16-exponential-walks-2.md) | compiler hang (exponential compile time) and a stack-overflow crash, native code | r29: `display.c` | Submit after #15 (stacked on it); also built and validated alone on main (efc9d90), so it can go either way. |
| 17 | [Fix compile time evaluation of loops over constant pointer tables](oscar64-upstream/17-shknam-crash.md) | compiler crash (with a wrong count behind it) | r27 (#11b): `shknam.c` | Submit after #1: on plain main this fix alone turns `0 != names[n]` loops from a crash into a wrong count of 0 until #1 is merged. |
| 18 | [Fix endless loop on a struct copied onto itself](oscar64-upstream/18-makemon-hang.md) | compiler hang (endless optimiser loop) | r28: `makemon.c` (harness only) | Submit; low priority for the game (only the harness's fake allocator reaches it). |

## Upstream state (checked 2026-11-12)

- **Releases.** v1.32.273 (2026-08-20) is still the latest; v1.32.271 and .272 came
  in April and June. Upstream main is 182 commits ahead (4da3147, 2026-11-10).
- **Fixed on main since v1.32.273** (so they need no PR): r1 (160c92b, PR #419),
  r4 (813fe29, PR #437), r9 (46e60d6), r14 (349b10a), r17 (c8da6bd), r18 (1169268,
  2026-09-21, wrong code: it is in the proposed patched pin).
- **Will not be fixed upstream:** r5/r6, struct tags sharing the ordinary namespace
  (issue #438: "design flaw of the language and will not implement"); r11, K&R
  definitions (Oscar64 is a C99 compiler); r13, string literals as `char *` (issue
  #90, closed "As expected"; see #14).
- **Regressions on main that nethack64 would hit:** 349b10a (2026-10-26) rejects
  function-pointer members of global structs, so NetHack compiles 0 of 107 files with
  main (fixed by #4); 48f90e2 (2026-10-04) widened r20 to `?:` comparisons (fixed by #2).
- **Code size on main.** At `-Os`, the NetHack files that compile with both are 10.6%
  (C64 config) and 10.8% (UNIX config) bigger with 25383cb (main just before 349b10a)
  than with v1.32.273, measured 2026-11-12. Not investigated yet; worth an upstream
  issue once bisected.
- **Memory runaway on main from PR #440.** bf42402 (PR #440, 2026-10-24, the fix for
  r25) makes the compiler's memory grow without bound on NetHack's `explode.c`: 8-9 GB
  in 20 seconds, then the kernel's OOM killer. Plain v1.32.273 compiles the file in
  3 s and 0.36 GB; v1.32.273 plus that one commit runs away; so does main (with our
  fixes, which it needs to get that far). Found 2026-11-12; being reduced and fixed.
  The measurement harness reported these kills as "compiler-crash": all 22 OOM kills
  on this machine that day were oscar64 processes at 7 to 9.5 GB.
- **Crashes and hangs on main** with the same NetHack files: `display.c` and `makemon.c`
  hang (600 s timeout, 25383cb); with main plus six of these fixes, `dungeon.c`,
  `questpgr.c` and `explode.c` crash the compiler and `mhitm.c` crashes or hangs.
- **Main plus all our fixes** (`nethack64/integration-final`, 2026-11-12, measured with
  13 of the 14; #5 is `-O0` only): in the C64 config 57 files compile to placement
  against 41 with v1.32.273, but the 40 files placed by both are 13.4% bigger (227,598
  to 258,193 bytes); `explode.c` (placed with v1.32.273) and `dungeon.c` crash it, as
  they crash upstream main itself (25383cb), and `questpgr.c`, `mhitm.c` and `shknam.c`
  crash it too; `display.c`, `invent.c` and `makemon.c` hit the 600 s limit on a busy
  machine. UNIX config: 47 placed against 36, +13.6% for the 35 placed by both. So
  moving nethack64 to main is not an option yet (ADR-0007).

## Other Oscar64 bugs found on the way (not fixed by any branch)

The fix agents and reviewers found dozens of pre-existing bugs while probing. Each
page's "Related bugs" section lists them with probe files. Sorted by what they mean
for nethack64 (C, native code, `-Os`, v1.32.273):

**Can affect our build today.**
- Compile-time evaluation of a pointer test (`return s != 0;` in a side-effect-free
  helper called with a constant address) gives the wrong answer at `-O2`/`-Os`/`-O3`:
  repro r24, compat #28. No fix branch yet; a candidate for the next one.
- Identical `const` data objects are merged, so two distinct tables can compare equal
  (dropped-init-fn review, probe `p27_const_data.c`). Deliberately left out of #3.
- A function-typed parameter (`int is(int g(void))`) is not adjusted to a pointer;
  calls through it are wrong at `-Os` with native code (r16 review, `v02b`).
- Compiler crashes (not wrong code): calling the result of a call, `pick(1)(4)`, and a
  variable-index call through an array member of a global struct, `ap.fn[i](x)`.

**Not at `-Os`:** `for (unsigned char c = 250; c != 4; c++)` loops the wrong number of
times at `-O2`/`-O3`; four or more inline-asm stores into a global array read back
wrong at `-n -O3`.

**Compiler crashes on NetHack files with v1.32.273** (T1.6, T1.11): all three
reduced on 2026-11-12. `shknam.c` segfaults in `InterCodeBasicBlock::LoadConstantOperand`,
called from `ConstSingleLoopOptimization` (the compile-time loop evaluator reading a
constant table): r27, compat #11b, fixed by #17. `mhitm.c` is the memory runaway: r26,
compat #30, fixed by #15. `makemon.c` hangs on a struct copied onto itself, reached only
through the measurement harness's pointer stubs (r34): r28, compat #11, fixed by #18.

**Preprocessor conformance** (`#if` with `?:` or `%`; a character dropped after
`#define F(a)(a+1)`; `#x` stringify adds a trailing blank; `XSTR(x)` does not expand;
comments inside skipped groups): none of these shapes occurs in NetHack's 917
function-like macros or elsewhere in `port/include` and `port/src` (grep, 2026-11-12).

**Reproducible builds.** Some outputs depend on the compiler's install path or heap
layout (`autotest/testint16mul.c` and `samples/hires/splitscreen.c` at `-bc -O2`): two
builds of the same source can differ. `tools/oscar64-upstream/corpus_diff.py` users
should confirm a difference against a second base build before blaming a fix.

**Upstream-main-only regressions** (matter if we ever move to main): a by-value struct
return read through a signed load at `-O0`, an assertion failure on
`(gi(&s) < 0 ? -(long)gi(&s) : (long)gi(&s))`, an unsigned-short subtraction at
bytecode `-O0`, a segfault on keyword-named struct members.

## How the fixes were made and checked

- A clone of upstream (`~/src/oscar64-dev`, remote `upstream`), one branch and worktree
  per fix (`build/oscar64-wt/<id>`), each one commit on main 4da3147.
- Each fix: a regression test in `autotest/` that fails before and passes after in
  ten configurations (`-ea -g`, `-bc`/`-n` x default/`-O0`/`-O2`/`-Os`/`-O3`), the full
  upstream autotest (`make check`, 1541 emulations on 4da3147, 0 failing; compared with
  `tools/oscar64-upstream/autotest_diff.py`), and a byte-for-byte comparison of about
  900 compilations of the autotest sources and our repros
  (`tools/oscar64-upstream/corpus_diff.py`).
- Two independent reviews per fix: Opus with full tools (re-ran the evidence and wrote
  dozens to over a hundred adversarial probe programs per fix) and Codex (gpt-6-astra) on a
  diff packet. Then a fix-up round (Fable) that reproduced every finding, fixed the
  confirmed ones, re-validated from scratch and rewrote the PR text. Then a final
  read-only Codex check of each final commit, a second Opus review of the two fixes
  whose approach changed (#4, #5), and a last round that settled those findings.
- An integration branch (`nethack64/integration-final3`: main plus the final commits of
  all 14 fixes) checks that they work together: the full autotest gives 1,756
  emulations, 0 failing (the 1,541 of 4da3147 plus the new tests), and 21 of the
  25 repros nethack64 had then pass with it
  (the other four: r5, r6 and r11, which upstream will not change, and r24, which has
  no fix yet).

The per-fix scratch directories (probes, logs, reviews) are in
`build/oscar64-wt/<id>-review` and `<id>-scratch`; `build/` is not in git, so the
pages here quote what matters.
