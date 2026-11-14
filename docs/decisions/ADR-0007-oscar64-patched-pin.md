# ADR-0007: Build with Oscar64 v1.32.273 plus wrong-code fixes

- Status: accepted by Jolyon on 2026-11-12, on the decision page; used by the build since
  2026-11-13; twenty more commits added on 2026-11-13 and twelve on 2026-11-14 (24 chosen by
  Jolyon on the decision page; the last eight by Claude, under Jolyon's go-ahead of 2026-11-14 ("You go ahead ... push what you need"))
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

Added on 2026-11-13 (Jolyon chose "Add" for ten rows on the decision page): commits 9 to
28, on f001eba in this order, each code change identical to the reviewed branch commit
(`git patch-id`):

9. `7a40c79` upstream 1ae3216 (r32: a pointer read from a `const` table at a constant
   index), and 10. `2ccb958` its regression test;
11. `51729f2` r27 (the `shknam.c` crash); 12. `41a411d` r28 (the `makemon.c` hang);
13. `66bd3eb` r33; 14. `e3995c0` r29 (two exponential walks; `display.c`);
15. `d169009` upstream 3bb084f and 16. `01cfa3a` upstream 1073206 (r30), and
17. `870ac02` our fix for the exponential walk and stack overflow 1073206 brings;
18. to 23. heap initialisation (T1.21): `bf5e1ea` backports upstream fbca293 (r38);
   `14ff554`, `9ce4806`, `05b403a` and `372dc4c` initialise members the compiler read
   before writing them; `2da6d7f` fixes r39 (with `05b403a`);
24. `efd669b` r36; 25. to 27. `a2a42f8`, `f6ef29b`, `2275592` r40 (r36's twin in native
   code); 28. `b4dc4eb` r41.

Their messages were edited on the way, nothing else: no session links, upstream's
1ae3216 without our co-author line, the backport notes of 3bb084f and of `2da6d7f`
corrected. Added on 2026-11-14 (Jolyon chose "Add" on 2026-11-13, to take effect once the reviews were
done): commits 29 to 32, on b4dc4eb:

29. `19aae5f` the CoerceType hunk of upstream 57655c5 (r42), and 30. `fb650c5` our guard to
   integer destinations, without which the hunk zeroes a pointer compared with a pointer
   conditional (NetHack's `m_at(x, y) == mtmp`);
31. `0b7dd30` r43, and 32. `bea5242` its regression test, written by Codex.

Reviews: with and without r42's commits, the library's `sscanf`, `fscanf` and formatting
code and NetHack's `vision_reset()` give the same results in all ten configurations (Codex,
260 runs); three functions of our C64 program change (+11 bytes), and in VICE, with inverse
video poked in for all four cell combinations, its bitmap and colour memory come out
byte-identical. r43's test fails without the fix in four native configurations and passes in
all ten with it (Codex; re-run here). r37 and r44 went back to Jolyon: the `-O0` probe they
were waiting on is r45 (T1.26), a wrong-code bug that commit 3 exposes at `-O2`/`-Os`/`-O3`.

Added on 2026-11-14 by Claude, under Jolyon's go-ahead of 2026-11-14 ("You go ahead ... push what you need"): commits 33 to 38, on bea5242:

33. `360acd3` r45 (found by Codex): `MoveCLCLoadAddZPStoreUp` also checks that nothing it
   moves an add past writes its destination, and 34. `2451a2c` its test (Codex);
35. `6bcee1a` r37 and 36. `55bad7e` its test; 37. `3a1fe75` r44 and 38. `f21d475` its test.

r45's fix goes first: with r44's alone the r45 probe turns wrong at `-O0` too; with all three
it gives 0 in all ten configurations.

Added the same night, also under that go-ahead: 39. `7317f30` r46 (found and fixed by Codex):
every byte of an address-taken register parameter now counts in the function's zero-page
clobber set; and 40. `04b8b6a` its test (Codex).

`tools/oscar64-upstream/build-pin.sh [DIR]` builds it (`JOBS=N` for `make -jN`). Since
2026-11-13 the setup scripts (`tools/setup-ubuntu.sh`, `tools/setup-arch.sh`) build the
release and then this compiler, link this one as `oscar64` (the Makefile takes it from
PATH) and the release as `oscar64-plain`; `OSCAR64_PLAIN=1` keeps the release as the
default. Our C64 program (`src/`) compiled to the same bytes with both until commits 29 and 30 (r42),
which change three of its functions (+11 bytes, same screen memory in VICE). Re-pin to a
plain release once one contains these fixes (or equivalents) and passes the same
checks, and its `-Os` size is understood.

## Consequences

- The six fixed rows above stop being "must be settled before game code runs" once
  the build uses the pin; r18-r23 and r25 pass, and so does r26 (commit 8). r24 stays
  open (T1.15).
- We carry a patch stack until upstream releases: of the 38 commits, five are upstream's
  (1169268, bf42402, 1ae3216, 3bb084f, 1073206), two backport upstream fixes (fbca293 and the
  CoerceType hunk of 57655c5), two are tests for upstream fixes, and thirty-one are ours
  (the r45 and r46 fixes and three tests written by Codex). Most of ours have an upstream form as a
  draft PR in the fork or a local branch on main, on hold (OSCAR64-UPSTREAM.md; nothing
  sent yet), so the stack should shrink. Once
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
  every pre-existing autotest program compiles byte-for-byte as before (below). It has
  happened once: commit 3, upstream bf42402, exposes r45 (T1.26), a dropped `char`
  result, at `-O2`/`-Os`/`-O3`; found on 2026-11-13, after the build switched.

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
make repros OSCAR64=/tmp/pin/bin/oscar64               # 25 of 46 FIXED (run.py caps each compile)
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

Results 2026-11-13 (28 commits, tip b4dc4eb; the compiler `build-pin.sh` builds from the
28 patch files checks out tree 229e43f, the branch's). Compiles under `ulimit -v 3000000`:

- Oscar64 autotest: 1,341 emulations, all result 0, no failing step (1,241 with the
  eight commits; the 100 more are the ten tests the twenty commits add).
- `corpus_diff.py` f001eba against b4dc4eb, over the autotest programs and repros
  r1-r44: 182 files x 5 configurations, 799 compiled by both, 749 byte-identical. The 50
  that differ are the ten new tests, the repros of bugs these commits fix (r30, r32, r33,
  r36, r39, r40) or touch (r43, whose loop pass r40's commits change; still wrong), and
  `opp_streamtest.cpp` at `-n -O3`, whose output depended on the heap. 30 compiles went
  from a crash or time-out to a program: r27, r28, r29, r41 and three of the new tests.
  Every other autotest program compiles byte-for-byte as before.
- Repros: 19 of 45 pass (r18-r23, r25-r30, r32, r33, r36, r38-r41), against 8 with the
  eight commits. r45, found the same day, is wrong on both (T1.26).
- nethack64 today: `make` and `make prg` give a `nethack-ef.crt` and `nethack.prg`
  byte-identical to the eight-commit build's; `make test` 5/5 passed.
- NetHack harness (`measure_oscar64.py`, 3,000 MB and 600 s per file) against the same
  day's eight-commit reports: C64 45 of 107 files measured (all fits-not), 256,349
  bytes; UNIX 40, 245,962. No crash or hang is left: `shknam.c` compiles (2,578 bytes, 3
  of 7 functions placed) and `makemon.c` stops at a known compile error (an `extern`
  array without a size). Code changes in three files, each accounted for: `teleport.c`
  (+11 bytes) and `potion.c` (one more function placed) now get what the eight commits
  gave only under a zero-filled heap (r38: `u_teleport_mon()` keeps its call frame);
  `mkobj.c` +3 bytes in `weight()`, which now reads `obj->otyp` again after its recursive
  loop (r39; the stale copy was harmless there). With every heap block filled with 0xA5
  first (an `LD_PRELOAD` shim), the C64 run gives byte-identical listings, intermediate
  code and maps for all 90 files that reach code generation: the output no longer
  depends on old heap contents.
- `make check` re-links `bin/oscar64` before it starts: run it apart from other uses of
  the same compiler (on 2026-11-13 a corpus run started at the same moment failed with
  "Permission denied" and was run again).

Results 2026-11-14 (32 commits, tip bea5242; the patch files give tree 8c07cca, the branch's):

- Oscar64 autotest: 1,351 emulations, all result 0 (the ten more are r43's test).
- `corpus_diff.py` b4dc4eb against bea5242: 185 files x 5 configurations, 844 compiled by
  both, 671 byte-identical. The 173 that differ (54 programs, every level, both back ends)
  are r42's masks, which sit in the intermediate code, and r43's repro and test; no compile
  status changed.
- Repros: 21 of 46 pass (r42 and r43 added).
- nethack64: code 6,925 to 6,936 bytes (`main`, `try_move`, `draw_pair`; r42); `make test`
  5/5 passed; screen memory identical in VICE (above).
- NetHack harness: C64 45 of 107 files measured, 256,352 bytes; UNIX 40, 245,965. One file
  changes in both: `vision.c` +3 bytes, `vision_reset()`'s masks (reviewed above). Under the
  0xA5 heap fill the C64 listings are still identical.

Results 2026-11-14 (38 commits, tip f21d475; the patch files give tree b16b95d, the branch's):

- Oscar64 autotest: 1,381 emulations, all result 0 (the 30 more are the three new tests).
- `corpus_diff.py` bea5242 against f21d475: 188 files x 5 configurations, 859 compiled by
  both, 830 byte-identical. The 29 that differ are repros r37, r44, r45 and their three
  tests (4 configurations each) and five autotest programs at `-n -O0`, where r44's fix
  changes code; all five pass. No compile status changed.
- Repros: 24 of 46 pass (r37, r44, r45 added). The probe behind T1.23's `-O0` worry gives 0
  in all ten.
- nethack64: `nethack-ef.crt` and `nethack.prg` byte-identical to the 32-commit build's;
  `make test` 5/5 passed.
- NetHack harness: C64 45 of 107 files measured, 256,360 bytes; UNIX 40, 245,972. Four
  functions change, all r44's: `make_hallucinated()` (`potion.c`, +3; it now tests the copy,
  as written), `rigid_role_checks()` (`role.c`, +4; right before and after), and in the C64
  run `getrumor()` (`rumors.c`, +1), which keeps a copy of a value instead of reading the
  global behind `strcat()` again: a harness stub returns that global, and nothing changes it,
  so both versions are right. Under the 0xA5 heap fill the listings are still identical.

Results 2026-11-14 (40 commits, tip 04b8b6a; the patch files give tree e98604b, the branch's):
autotest 1,391 emulations, all 0; corpus 858 of 864 identical (r46's repro and test, and
`structconditionaltest.c` at `-n -O0`, which passes); repros 25 of 46; nethack64 unchanged,
`make test` 5/5; NetHack: every listing, intermediate code and map of the 91 files that reach
code generation identical to the 38-commit compiler's (compiler paths aside).
