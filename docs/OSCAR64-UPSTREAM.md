# Oscar64 fixes proposed upstream

Status 2026-11-12: 14 fixes, written and reviewed locally, waiting for Jolyon's
decision. Nothing has been sent upstream: no fork, no PR, no issue. One page per
proposed PR in [`docs/oscar64-upstream/`](oscar64-upstream/), each with a plain
explanation, the evidence, every review finding and what happened to it, the risks,
and the draft PR text. The commits themselves are in
[`tools/oscar64-upstream/patches/main/`](../tools/oscar64-upstream/patches/main/)
(`git am` onto upstream main 4da3147; GPL-3.0, like Oscar64).

## What Jolyon needs to decide

1. **Which PRs to open.** The recommendation per PR is in the table below.
2. **Where from.** A PR needs a fork. `gh repo fork drmortalwombat/oscar64` under
   `jolyonbrown` was refused by the agent's permission check (it creates a public
   repository), so it needs your OK, or you run it yourself.
3. **Order and pace.** Suggested: the four wrong-code fixes first (#1 to #4), then #6
   once #1 is merged (it is stacked on #1), then the rest a few at a time. Most
   outside PRs since August were merged or closed within a few days; a few took two
   to five weeks. The maintainer often keeps the
   contributor's regression test and writes his own version of the fix ("Picked up
   your test but made a slightly different fix", PRs #442, #443, #447), so the tests
   and the root-cause write-ups matter as much as the code.
4. **Attribution.** Every commit ends with `Co-Authored-By: Claude ...` and a
   `Claude-Session:` link, and every PR body says it was prepared with AI assistance
   (Claude Code). The session link is private and means nothing upstream; the final
   reviews recommend dropping it. The co-author names are inconsistent (some agents
   wrote "Claude Fable 5.1"). Suggested: one line, `Co-Authored-By: Claude
   <noreply@anthropic.com>`, no session link, keep the sentence in the PR body.
   No upstream PR so far carries any AI attribution, so there is no house style to
   follow.
5. **The compiler nethack64 builds with** (separate from the PRs): see
   [ADR-0007](decisions/ADR-0007-oscar64-patched-pin.md).

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

**Compiler crashes on NetHack files with v1.32.273** (T1.6, T1.11): `shknam.c`
segfaults in `InterCodeBasicBlock::LoadConstantOperand`, called from
`ConstSingleLoopOptimization` (the compile-time loop evaluator reading a constant
table; gdb backtrace 2026-11-12); `mhitm.c` and `makemon.c` did not finish within
900 s under gdb. Not reduced yet.

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
- An integration branch (`nethack64/integration-final2`: main plus the final commits of
  all 14 fixes) checks that they work together: the full autotest gives 1,756
  emulations, 0 failing (the 1,541 of 4da3147 plus the new tests), and 21 of
  nethack64's 25 repros pass with it
  (the other four: r5, r6 and r11, which upstream will not change, and r24, which has
  no fix yet).

The per-fix scratch directories (probes, logs, reviews) are in
`build/oscar64-wt/<id>-review` and `<id>-scratch`; `build/` is not in git, so the
pages here quote what matters.
