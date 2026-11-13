# ADR-0007: Build with Oscar64 v1.32.273 plus wrong-code fixes

- Status: accepted by Jolyon on 2026-11-12, on the decision page; used by the build since 2026-11-13
- Date: 2026-11-12 (proposed and accepted); commit ids final 2026-11-13
- Deciders: Jolyon (+ Claude, who proposed it)

## Context

The pinned compiler, Oscar64 v1.32.273 (ADR-0002), silently miscompiles code shapes
that NetHack uses, at `-Os`, with no diagnostic. Each has a repro in
`tests/oscar64-repros/` and a row in `docs/OSCAR64-COMPAT.md`:

| Repro (row) | What goes wrong | Where NetHack has the shape |
|---|---|---|
| r18 (#22) | the `char`/`boolean` result of a call through a function pointer is read from the wrong place | every `yn()`; every `boolean` window or callback function |
| r19 (#23) | a pointer initialised to 0 compares as non-null; `!p` as a value is wrong | `pickup.c` `invent != 0` |
| r20-r22 (#24-#26) | negative numbers in initialised data read back as large positive ones when folded | abs-style `?:` on members, `schar` tables such as `xdir`/`ydir` |
| r23 (#27) | a call through a function-pointer member of a global struct is left out of the call graph: the callee's frame overwrites the caller's live locals | every window call, `(*windowprocs.win_*)(...)` |
| r25 (#29) | a function called directly with a constant and also through a pointer gets the constant built in | window-port functions called inside the port with `FALSE` and through `windowprocs` with `TRUE` |
| (no repro; case file) | two different functions with identical code share one address when their addresses are stored | tables of function pointers that are compared (`cmdlist`, `occupation == dig`) |
| r24 (#28) | a pointer test in a side-effect-free helper evaluated at compile time | helpers called with constant addresses; **not fixed by this proposal** |

A reviewer's NetHack-shaped window layer (`build/oscar64-wt/pinned-patched-2-review/p/nh/n01_window_port.c`:
a `windowprocs` table, `char` and `boolean` results, callers with live locals, a port
function also called directly) returns a wrong result with v1.32.273 in nine of the
ten configurations, `-Os` included in both back ends. Game code cannot run reliably
on this compiler.

Fixes exist for all but r24 (`docs/OSCAR64-UPSTREAM.md`): r18 and r25 are fixed on
upstream main (1169268, 2026-09-21; bf42402, PR #440, 2026-10-24); the others are our
fix branches, reviewed twice each and not yet sent upstream. None is in a release:
v1.32.273 (2026-08-20) is still the latest.

Options:

1. **Plain v1.32.273 and port-side workarounds.** Each workaround has to catch every
   instance, and a missed one fails silently. r23 alone means changing how every
   window call is made. Fragile.
2. **Upstream main plus our fixes** (`nethack64/integration-final`, measured
   2026-11-12): 17 more files compile (C64 config), but for the 40 files that compile
   with both, `-Os` code is 13.4% bigger (227,598 to 258,193 bytes), five files crash
   the compiler and three hit the 600 s limit (`explode.c`, which compiles with
   v1.32.273, and `dungeon.c` also crash upstream main without our fixes). The UNIX
   config is the same: 11 more files placed, +13.6% for the 35 placed by both. Our
   fixes are not merged. Not usable yet.
3. **Wait for the next release.** No date, and it would still need our fixes merged and
   the size growth explained.
4. **v1.32.273 plus backported fixes.** Same release, same flags, only the wrong-code
   fixes.

## Decision (accepted 2026-11-12)

Option 4. Build nethack64 with v1.32.273 plus the eight commits in
`tools/oscar64-upstream/patches/pin/` (branch `nethack64/v1.32.273-pin` in the local
Oscar64 clone; ids as `git log v1.32.273..nethack64/v1.32.273-pin` gives them):

1. `9f59f41` upstream 1169268 (r18), the maintainer's commit unchanged;
2. `37bc126` its regression test (upstream has none);
3. `d2ea285` upstream bf42402 (PR #440, r25), unchanged;
4. `a6fe02b` r19,
5. `3998202` r20 (all three sites),
6. `cd22251` merged identical functions,
7. `f0b9ee6` the r23 call edge: 4 to 7 are backports of our fix branches (#1 to #3
   and the call-graph part of #4 in `docs/OSCAR64-UPSTREAM.md`);
8. `f001eba` the fix for the out-of-memory runaway that commit 3 exposes on
   `explode.c` (r26, our #15; see the open problem below).

Jolyon accepted it on 2026-11-12 on the decision page (the claude.ai artifact named
under "Jolyon's decisions" in `docs/OSCAR64-UPSTREAM.md`), whose pin item then read
"v1.32.273 plus eight commits: two upstream fixes, a test for one of them, and our
fixes #1-#3, #15 and the call-graph part of #4". Commit 8 was then c2f5cab; its final
form f001eba changes only comments and its regression test, not the compiler's code
(Evidence, 2026-11-13).

Not accepted: six further candidates (nine commits on six branches) wait for Jolyon's
decision one at a time (T1.25): `nethack64/pin-1ae3216` (r32), `pin-r30` (r30),
`pin-charidx` (r33), `pin-shknam-crash` (r27), `pin-makemon-hang` (r28) and
`pin-walks-display` (r29). Each was built on c2f5cab and validated alone, and the six
together on `review/pin-candidates-all` (2026-11-13: autotest 1,311 emulations, none
failing; repros 14 of 35). Each rebases onto f001eba without conflicts (`git rebase
--onto f001eba c2f5cab`); a plain merge conflicts in the three files commit 8 touches,
because c2f5cab and f001eba are siblings. Round six (2026-11-13) added more candidates,
also undecided: the heap-initialisation commits (r38, r39; T1.21) and our fixes for r36
and r37 (T1.22, T1.23).

`tools/oscar64-upstream/build-pin.sh [DIR]` builds it (`JOBS=N` for `make -jN`). Since
2026-11-13 the setup scripts (`tools/setup-ubuntu.sh`, `tools/setup-arch.sh`) build the
release and then this compiler, link this one as `oscar64` (the Makefile takes it from
PATH) and the release as `oscar64-plain`; `OSCAR64_PLAIN=1` keeps the release as the
default. Our C64 program (`src/`) compiles to the same bytes with both. Re-pin to a
plain release once one contains these fixes (or equivalents) and passes the same
checks, and its `-Os` size is understood.

## Consequences

- The six fixed rows above stop being "must be settled before game code runs" once
  the build uses the pin; r18-r23 and r25 pass, and so does r26 (commit 8). r24 stays
  open (T1.15).
- We carry a patch stack until upstream releases: two of the eight commits are
  upstream already, five are our fixes, prepared for upstream as draft PRs in the fork
  and on hold (#1 to #3, the call-graph part of #4, and #15 in OSCAR64-UPSTREAM.md;
  nothing sent yet), and one is a test, so it should shrink. Once
  the build switches, anyone building must run the setup script (or `build-pin.sh`); a
  stock v1.32.273 builds a subtly broken game.
- Measurements and byte counts taken with v1.32.273 stay valid where the code does not
  hit the bugs. To re-check now that the commit list is settled: the NetHack measurement
  with the seven-commit pin was stopped on 2026-11-12 when `explode.c` ran out of
  memory (see the open problem below); with the eight commits it runs through
  (Evidence, 2026-11-13). An earlier patched compiler with three of the
  fixes changed no file's status and added 84 bytes (C64 config) and 1.2 KB (UNIX
  config, one more function placed in `uhitm.c`).
- The call-edge fix makes callers of `windowprocs` functions non-leaf functions, so
  they get proper frames: slightly larger code there, which is the point.
- Risk: a mistake in a backport could add wrong code of its own. Mitigation: each
  backport was reviewed against its upstream-main version by a second agent
  (`build/oscar64-wt/pinned-patched-2-review`), the full v1.32.273 autotest passes, and
  every pre-existing autotest program compiles byte-for-byte as before (below).

## Open problem (2026-11-12; resolved by commit 8)

Resolved by commit 8 (`f001eba`, our fix #15): it gives the three walks behind the
runaway a visited set, and `explode.c` compiles with the eight commits (Evidence,
2026-11-13). The problem as it stood when the ADR was proposed:

Upstream bf42402 (commit 3, PR #440) fixes r25 but makes the compiler's memory grow
without bound on `explode.c`: with the seven commits the compile reaches 8-9 GB in
16-20 s and the kernel kills it, where v1.32.273 needs 0.36 GB. v1.32.273 plus bf42402
alone does the same; the pin without it compiles `explode.c` as v1.32.273 does.
Upstream main has the same problem. Until it is fixed, the choice is between:

- **six commits** (without bf42402): `explode.c` compiles, but r25 (a function called
  directly with a constant and through `windowprocs`) stays wrong code, and the
  call-edge commit then also miscompiles a function declared through a typedef'd
  function type that is called through a struct member (reviewer probe `t01`; NetHack
  declares no function that way);
- **seven commits plus a fix for the runaway**, being investigated
  (`build/oscar64-wt/explode-runaway`, branch `fix/pr440-runaway`). This is the option
  taken: the fix is commit 8 (`fix/pr440-runaway` is its form on upstream main, fork
  draft PR #15).

## Evidence / how to re-check

```sh
JOBS=2 tools/oscar64-upstream/build-pin.sh /tmp/pin    # v1.32.273 + patches/pin
make repros OSCAR64=/tmp/pin/bin/oscar64               # r18-r23, r25 and r26 FIXED (run.py caps each compile)
(ulimit -v 3000000; make -k -j2 -C /tmp/pin/make check)  # Oscar64's own autotest
(ulimit -v 3000000; python3 tools/oscar64-upstream/corpus_diff.py ~/src/oscar64/bin/oscar64 /tmp/pin/bin/oscar64 -j 2 --out /tmp/pin-corpus)
make OSCAR64=/tmp/pin/bin/oscar64 && make prg OSCAR64=/tmp/pin/bin/oscar64 && make test OSCAR64=/tmp/pin/bin/oscar64
OSCAR64=/tmp/pin/bin/oscar64 MEASURE_TIMEOUT=600 python3 tools/measure/measure_oscar64.py --config c64
```

Results 2026-11-12 (seven commits, branch tip f0b9ee6; `build-pin.sh` builds the same
compiler from the patch files: identical `.prg` output for r18-r25):

- Tests: the six regression tests and the reviewer's probes (including the
  NetHack-shaped `n01_window_port.c`) pass in all ten configurations (`-ea -g`,
  `-bc`/`-n` x default/`-O0`/`-O2`/`-Os`/`-O3`); with v1.32.273 each fails in some.
- `make repros`: 7 of 25 pass (r18-r23, r25), against 0 with v1.32.273.
- Oscar64 autotest: 1,231 emulations, 0 failing (v1.32.273: 1,171, 0 failing; the 60
  more are the six new tests in ten configurations).
- `corpus_diff.py` against v1.32.273: 152 files x 5 configurations, 680 compiled by
  both, 621 byte-identical, 59 different, all 59 in the six new tests and repros
  r18-r23 and r25; no compile status changed. Every pre-existing autotest program
  compiles byte-for-byte as before.
- nethack64 today: `make` and `make prg` give a `nethack-ef.crt` and `nethack.prg`
  byte-identical to the v1.32.273 build (same memory map: code 6,925, data 894,
  bss 2,399 bytes); `make test` 5/5 passed.
- Independent review of the backport: `build/oscar64-wt/pinned-patched-2-review`
  (verdict "use after changes"; the change it asked for, upstream bf42402, is commit 3).

Results 2026-11-13 (eight commits, branch tip f001eba; commit 8 was c2f5cab when
accepted). Every compile ran under `ulimit -v 2000000`:

- Commit 8's final form: `git diff c2f5cab f001eba` changes comments in
  `InterCode.cpp` and `NativeCodeGenerator.cpp` (both identical once comments are
  stripped) and the regression test `loopconditionpathtest.c` (a third function, `h`,
  for the Y-register walk; the second chain 18 conditionals instead of 20). Built in
  the same worktree, the two compilers differ only in 81 `assert` line numbers (+5 and
  +2, the comment lines added before them).
- Oscar64 autotest with f001eba: 1,241 emulations, all result 0, no failing step; the
  same 1,241 compiles as with c2f5cab (`build/oscar64-wt/pin8-autotest.log`, all
  passing), since the changed test still runs in ten configurations.
- `corpus_diff.py` c2f5cab against f001eba, over the autotest programs, repros r1-r35
  and the c2f5cab version of the changed test: 164 files x 5 configurations, 726
  compiled by both, all 726 byte-identical (both versions of the changed test
  included); no compile status changed.
- Repros r1-r35: 8 pass (r18-r23, r25, r26), against 0 with v1.32.273.
- NetHack harness (`measure_oscar64.py` under a zero-filled heap, 1,953 MB and 90 s per
  file), C64 and UNIX configurations: c2f5cab and f001eba give identical reports
  (107 records, `compare_reports.py`) and identical listings. C64: 44 files measured
  (all fits-not), 253,768 bytes; UNIX: 39, 243,381 bytes. `explode.c` compiles under
  the cap (fits-not, 4,441 bytes, 8 to 13 s); `shknam.c` still crashes and `makemon.c`
  still hangs (r27 and r28: candidates `pin-shknam-crash` and `pin-makemon-hang`).
- From the patch files: `git format-patch --no-signature
  v1.32.273..nethack64/v1.32.273-pin` gives `patches/pin/`, and `JOBS=2
  OSCAR64_REPO=~/src/oscar64-dev tools/oscar64-upstream/build-pin.sh DIR` checks out
  f001eba's tree (7de21ef; each of the eight trees matches the branch) and builds a
  compiler that gives the same `.prg` files as the pin's for the seven regression
  tests the commits add, three other autotest programs and repros r18-r26 in five
  configurations (95 of 95).
