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

Added 2026-11-14 on Jolyon's go-ahead ("you go ahead"): 41. `190d72a` upstream 46e60d6
(r49: `SplitAt` followed the null true jump of a function's exit block, crashing on
`mkobj.c` and `files.c` in the corrected harness; r9, compat #10, is the same crash), and
42. `2fded3c` its test, ours.

Added the same day on Jolyon's go-ahead ("add the r50 fix to the pin too"): 43. `36e3794`
r50 (found and fixed by Codex): `SimplifyIntegerNumeric` now copies the memory base along
with the variable index when it folds an address into an indirect store or load, so a
buffer promoted to a global (`fopen()`'s file name) no longer keeps a local tag that
`LoadStoreForwarding` followed into a null entry; and 44. `794954e` its test (Codex).

Added the same day on Jolyon's go-ahead ("yes, add both to the pin"): 45. `2200134`
upstream 160c92b, with its two tests (r1, compat #7: a cast was applied to a parenthesised
operand before its `->`, `.` or `[]`, so `(int) (obj)->corpsenm` in `obj_to_glyph()` failed
with "Pointer expected"); 46. `b24d0c7` r51 (written by Codex): an integer constant
expression of value 0 opposite a pointer in `?:` becomes a null pointer of that type,
with constant folding keeping track of what is a constant expression; and 47. `8cd7d98`
its test (Codex).

Added the same day on Jolyon's go-ahead ("add the r15 fix to the pin too"): 48. `8c24ec2`
r15 (compat #19), our fix of 2026-11-12 for fork draft #7, with its two tests: a pointer
to a union converts to a pointer to a `const` or `volatile` union, as struct pointers do
(unions take the struct branch of `IsSubType`, `IsSameMutable` and `IsConstSame`).

Added the same day on Jolyon's go-ahead ("add all of them to the pin"): 49. `b496c4e` r16
(compat #20), our fix of 2026-11-12 for fork draft #6: a function compared with a
function pointer is converted to a pointer to it first, and the global optimiser counts a
compared function as one whose address is taken; 50. `c092da2` upstream c8da6bd (r17,
compat #21: `c ? f : g` over two functions gets a function pointer type) and 51. `b8be83c`
its test, ours; 52. `e183983` r53 (compat #55): `!` of an integer constant folds, so `!0`
is a constant expression, and 53. `8949cef` its test; 54. `df4e773` r52 (compat #54, wrong
code): `!!x` folds to `x` only when `x` is 0 or 1 already (a relational, `&&`, `||` or `!`)
or of class type, and 55. `1b95989` its test; 56. `d988c5c` r31 (compat #33; found
2026-11-12, fixed by Codex as the repro proposed): `BlockSizeCopyReduction` masks a fill
loop's starting index to a byte, so a fill from offset 0 starts at `LDY #$ff` instead of
aborting, and 57. `ebfdbe6` its test (Codex); 58. `bbc2f32` r59 (compat #61, found and
fixed by Codex): `BinaryAddCarry` loads a constant first addend as an immediate instead of
indexing the temporary table with its `-1`, and 59. `eb5a37d` its test (Codex). Codex
reviewed the first version of commit 54 and found that `!!1` stopped being a constant and
that C++'s `!!obj` through `operator bool` aborted; commit 52 and the class-type case
answer both, and its 29 probes give the same or better results than the 48 commits.

Added on 2026-11-15 on Jolyon's go-ahead ("yes, add both to the pin", then "All four" when
asked which): 60. `7ca5d38` r60 (compat #62, found 2026-11-14, fixed by Codex):
`JoinEntryLoadStoreZP` counts the predecessors it routes through a new block out of the
join's entries, so `mattackm()` (`mhitm.c`) no longer aborts native code generation, and 61.
`40d5ebc` its test; 62. `072bb5a` cartridge banks 0 to 254 (Codex): the first commit that
lifts a limit rather than fixing a fault, wanted by every banking design (NetHack's code
needs about 84 banks of 16 KB, and Oscar64 put bank 64 silently into bank 0); 63. `d3776d0`
r62 (compat #64): `MarkRecursions` by Tarjan's search, and 64. `bf6302e` `CheckFastcall`
walking each function once, with what its old repeated walks read from a function taking
stack parameters found by a search and kept per strongly connected component (the whole
game in one compile had not finished its analysis in an hour), and 65. `8a087e1` their test;
66. `a189c89` r63 (compat #65, wrong code): evaluating a call while compiling binds nothing
for a parameter the optimiser has marked unused and renumbered as a local, and 67.
`28a87b3` its test.

Added the same day on Jolyon's go-ahead ("yes, write the test and add it to the pin"):
68. `b05afde`, ours: `InterCodeProcedure::Close` releases its blocks' data flow sets over
variables, statics and parameters once the procedure is optimized. Those over the statics
are as large as the module's statics (or their bytes), so a big program's intermediate code
grew with its blocks times its static data, and nothing reads them afterwards; NetHack as
one program ran out of 16 GB without it and compiles in 13.2 GB with it. Like 63 and 64 it
changes no generated code; and 69. `e128fb7` its test, which cannot show the saving at a C64
program's size and checks instead the code that depends on what is kept.

Added the same evening on Jolyon's go-ahead ("add both to the pin"): 70. `9f46cee` r64
(compat #66): `PropagateVariableCopy`, forwarding a load to a struct copy's source, takes over
the source's memory base and restrict flag too, so a load that reads through a pointer no
longer claims a local with index -1 (the compiler aborted on `dungeon.c`'s `lev_by_name()`
once calls crossed banks directly, and alias analysis was misled before that), and 71.
`893f954` its test; 72. `7caff8d` bank call stubs, after commit 62 the second commit that adds
rather than fixes: a program that names a bank call routine (`#pragma runtime(bankcall,
...)`) gets every call into a cartridge bank from outside it, and every use of a banked
function's address, through a 6-byte resident stub the linker makes (`jsr bankcall; .byte
bank; .word function`) after all of the compiler's analysis, while a program without the
pragma links as before; with it the whole game's resident code is 65 KB instead of 156 KB
(BANKING-SPIKE.md). And 73. `7cead7f` its test, which checks in the emulator what the linker
made (the emulator has no cartridge; `tests/spikes/run_bankstub.py` makes the calls in VICE).

Added on 2026-11-16 under Jolyon's direction for the compiler fixes ("the compiler fixes
afterward as you see fit", 2026-11-15), each explained to him: 74. `410854c`, ours:
warning 2025 when a function's zero-page temporaries pass the end of their area (compat #72,
r69). Nothing kept them within $53-$8F, and past it the KERNAL's IRQ changes them (and
Oscar64's emulator its jiffy clock); `BC_REG_TMP_END` is $90 in the Commodore machines'
default layout, and there is no check where the end is not known (the Atari, X16, MEGA65 and
NES targets, `-xz`, registers moved by `#pragma register`). `#pragma warning(error: 2025)`
makes it an error; it changes no code. 75. `d54543a` r70 (compat #73): `BlockSizeCopyReduction`
puts into one loop only the copies that fit a branch's 128 bytes, and the next pass folds the
rest into another, and 76. `16a378d` its test; 77. `f950ae1` r71 (compat #74, found by
`tools/check_listing.py` in the C64 measurement's listings): the same function sizes each
operand by the assembler's rule, which writes an absolute address below 256 without a linker
object in two bytes, so a copy loop's BPL no longer lands one byte short, in its `LDX`'s
operand; and 78. `2f9733f` its test.

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
- We carry a patch stack until upstream releases: of the 80 commits (79-80, T1.49's save pass, ours too), eight are upstream's
  (1169268, bf42402, 1ae3216, 3bb084f, 1073206, 46e60d6, 160c92b, c8da6bd), two backport
  upstream fixes (fbca293 and the CoerceType hunk of 57655c5), four are tests for upstream
  fixes, and sixty-four are ours (the r31, r45, r46, r50, r51, r59 and r60 fixes, the bank
  patch and seven tests written by Codex). Most of ours have an upstream form as a
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
make repros OSCAR64=/tmp/pin/bin/oscar64               # 37 of 59 FIXED (run.py caps each compile)
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

Results 2026-11-14 (42 commits, tip 2fded3c; the patch files give tree 946d3ed, the branch's):
autotest 1,401 emulations, all 0 (the new test in all ten configurations; with 40 commits it
crashes the four native ones at the default level, `-O0`, `-O2` and `-Os`); corpus: 872 of
872 compiled by both identical, and five crashes now compile (the new test in three
configurations, r49 and r9); repros 27 of 50 (r49 and r9 now pass); nethack64: `.crt` and
`.prg` byte-identical, `make test` 5/5; NetHack (T1.10 harness): every listing,
intermediate code and map of the 86 (C64) and 85 (UNIX) files both compilers compile is
identical, and `files.c` and `mkobj.c`, which crashed, reach placement: C64 63/107
(378,919 B), UNIX 52/107 (325,427 B).

Results 2026-11-14 (44 commits, tip 794954e; the patch files give tree a4226df, the branch's
and that of the candidate the checks below ran on): autotest 1,411 emulations, all 0 (the
new test in all ten configurations; with 42 commits it crashes the native ones at `-O2`,
`-Os` and `-O3`); corpus against 42 commits: 878 of the 879 programs both compile are
identical, the other is `opp_hashmap.cpp` at `-bc -O2`, where two blocks of a
number-formatting routine change places with the same effect (its test passes). That
layout follows where the compiler is installed, not the fix: one binary copied to other
directories gives either layout (compilers under paths of 28 and 34 characters give one,
47 and more the other), so the file is noise in these comparisons; NetHack's native
listings showed no such dependence. Six crashes now compile (the new test and r50, three configurations each); repros 28 of 51
(r50 now passes); nethack64 `.crt` and `.prg` byte-identical, `make test` 5/5; NetHack:
listings and maps identical, the intermediate code of `files.c` and `rumors.c` now names
`cbmname` where the 42-commit compiler printed `'null'` (the tag the fix corrects), and
`questpgr.c`, which crashed, reaches placement.

Results 2026-11-14 (47 commits, tip 8cd7d98; the patch files give tree 42514ec, the branch's
and that of the candidate the checks ran on): autotest 1,441 emulations, all 0 (160c92b's two
tests and the r51 test in all ten configurations each); corpus with 160c92b against 44
commits: 884 of 885 identical (the other `opp_hashmap.cpp`, the install-path noise above)
and 15 rejections now compile (160c92b's tests and r1); with the r51 fix against that: 900
of 900 identical and 10 rejections now compile (its test and r51); repros 30 of 51 (r1 and
r51 now pass); nethack64 `.crt` and `.prg` byte-identical, `make test` 5/5; NetHack: every
listing, intermediate code and map of the files that compiled before is identical, five
more files reach placement with 160c92b and seven with the r51 fix: C64 80/108
(522,868 B), UNIX 67/108 (461,311 B).

Results 2026-11-14 (48 commits, tip 8c24ec2; the patch files give tree 59ec5f1, the branch's
and the checked candidate's): autotest 1,461 emulations, all 0 (the two union tests in all
ten configurations each); corpus against 47 commits: 910 of 910 identical, and 15 rejections
now compile (the two tests and r15); repros 31 of 51; nethack64 `.crt` and `.prg`
byte-identical, `make test` 5/5; NetHack: every listing, intermediate code and map of the
files that compiled before identical, and `apply.c`, `artifact.c`, `dungeon.c`, `pager.c`
(C64) and `spell.c` reach placement: C64 85/108 (585,948 B), UNIX 71/108 (514,789 B).

Results 2026-11-14 (59 commits, tip eb5a37d; the patch files give tree 45d5c29, the branch's
and the checked candidate's). The NetHack numbers from here on use the harness of TASKS
T1.42, whose stubs read their parameters (code measured about a third larger than before).
Autotest 1,521 emulations, all 0 (the six new tests in all ten configurations each); corpus
against 48 commits: 932 of 932 identical, and 50 rejections or crashes now compile (the six
new tests, r16, r17, r31, r52, r53, r59); repros 37 of 59; nethack64 `.crt` and `.prg`
byte-identical, `make test` 5/5. NetHack: every listing, intermediate code and map of the
files that compiled with 48 commits is identical except in the functions that use `!!`,
whose code now computes 0 or 1 (13 files under C64, 12 under UNIX; one of them,
`castmu()`, kept a truncated `long` in `boolean oldprop = !!Confusion`), and the
intermediate code of `mapglyph()`, where `!((boolean)1)` now folds when parsed (same
machine code). All 108 files reach placement under C64 (1,252,234 B in the 106 that place
code); UNIX 97/108 (1,185,691 B).

Results 2026-11-15 (67 commits, tip 28a87b3; the patch files give tree 803a674, the branch's
and the checked candidate's; each of the five commits of ours cherry-picked onto Codex's
three has the `git patch-id` of its reviewed branch commit, outside `autotest.bat`).
Autotest 1,561 emulations, all 0 (the four new tests in all ten configurations each); corpus
against 59 commits: 991 of 1,004 identical, the other 13 being `bankofhigh.c`, the r63 test
and r63 where the new commits apply, and 13 crashes or time-outs now compile (the r60 test,
r60 and r62); repros 40 of 63; nethack64 `.crt` and `.prg` byte-identical, `make test` 5/5.
NetHack (C64): every listing, intermediate code and map of the 107 files that compiled with
59 commits is identical, and `mhitm.c` compiles (23,380 B): C64 108/108 (1,185,261 B in the
106 that place code), UNIX 97/108 (1,120,579 B in 95), measured with the `__noinline` stubs of
T1.45 (`docs/data/oscar64-pin67-*-2026-11-15.json`).

Results 2026-11-15 (69 commits, tip e128fb7; the patch files give tree 3532056, the
branch's). Autotest 1,571 emulations, all 0; corpus against 67 commits 1,022 of 1,022
identical, no status changed; repros 40 of 63; nethack64 `.crt` and `.prg` byte-identical,
`make test` 5/5; NetHack (C64): all 324 listings, intermediate code and maps identical to
67 commits', C64 108/108 (1,185,261 B); UNIX 97/108, every record identical
(`docs/data/oscar64-pin69-*-2026-11-15.json`). With it the whole game compiled in one run on a
31 GB machine: 619 s, peak 13.2 GB (BANKING-SPIKE.md); without it, out of 16 GB.

Results 2026-11-15 (73 commits, tip 7cead7f; the patch files give tree b613b39, the
branch's). Autotest 1,591 emulations, all 0 (the two new tests in all ten configurations);
corpus against 69 commits 1,022 of 1,027 identical, the five being the stub test in its four
native configurations (it uses the feature) and `opp_vector.cpp` as bytecode at -O2, compat
#67, a read of uninitialised memory in the bytecode generator that a different heap exposes
(identical under `MALLOC_PERTURB_`); ten status changes, r64 and its test going from crash to
ok; repros 41 of 65 (r64 fixed; r65, compat #68, new and open); nethack64 `.crt` and `.prg`
byte-identical, `make test` 5/5; `tests/spikes/run_bankstub.py` 13/13 in VICE; NetHack
(C64): all 324 listings, intermediate code and maps identical to 69 commits', 108/108
(1,185,261 B); UNIX 97/108, every record identical
(`docs/data/oscar64-pin73-*-2026-11-15.json`). The whole game with the stubs
(`bankgen.py --linker-stubs`) passes every bank check, and its resident code is 65.1 KB
instead of 156.4 KB (BANKING-SPIKE.md).

Results 2026-11-16 (78 commits, tip 2f9733f; the patch files give tree 67b839a, the
branch's, and the installed compiler's). Autotest 1,611 emulations, all 0 (the two new tests
in all ten configurations; with 73 commits each fails at `-Os -n`), and warning 2025 twice,
for upstream's own `mmultest.c` at -O3 ($99 native, $A0 byte code: it passes because $A0,
the clock's top byte, changes once in about 18 minutes); corpus against 73 commits: 1,066 of
1,070 identical, the other four being the two new tests and r70 and r71 at `-Os` (native),
no status changes; repros 44 of 71 (r70 and r71 fixed, r69 diagnosed); nethack64 `.crt` and
`.prg` byte-identical, `make test` 5/5; the speed harness's ten programs (near and far)
byte-identical; NetHack (C64): 326 of the 327 listings, intermediate code and maps identical
to 73 commits', the other being `uhitm.c`'s listing, where `hmon_hitmon()`'s copy loop now
branches to $22CD, its first instruction, instead of $22CC; 108/108 (1,187,649 B); UNIX the
same branch, 317 of 318 identical, every record identical, 97/108 (1,120,579 B)
(`docs/data/oscar64-pin78-*-2026-11-16.json`).

Added on 2026-11-16 (commits 79-80, T1.49, under Jolyon's "the compiler fixes afterward as you
see fit" of 2026-11-15 for the speed work): the first speed change, a pass that lets a function
save only the zero page temporaries its callers need. Oscar64 saves every callee-saved temporary
a function uses ($53 up) on entry and restores it on exit, and over the whole game that is about
277,000 cycles a turn (RAM-PLAN.md, "Measured: zero page saves"). Once every function is compiled,
`NativeCodeGenerator::ReduceTempSaves` takes, for each direct call, the bytes the caller reads
after it before writing them (the native data flow sets, plus the reach of copy loops), adds what
the caller's own callers need of bytes the caller does not save, and narrows each function's
save and restore to the result, in up to three runs, in the same frame slots. A function whose
address is taken, that an interrupt reaches or that assembler refers to keeps its full save, and
so does `main` unless the program says it never returns to BASIC (`-xb`, new; our Makefile,
`build_c64.py` and `calibrate.py` pass it). `-Ot` is part of `-O2`, `-O3` and `-Os`; `-Ot-`
turns it off, and with it the compiler is byte-identical to 78 commits'. Commit 80 is its test.

Results 2026-11-16 (80 commits, tip 0d71c3a; the patch files give tree ed539b4, the branch's
and the installed compiler's). Autotest 1,621 emulations, all 0 (the new test in all ten
configurations), and again with `-xb` on every native build (1,621, all 0); with `-Ot-` the
corpus is byte-identical to 78 commits' (1,080 of 1,080: the autotest sources and the repros,
five configurations); repros 44 of 72; nethack64 `make test` 5/5 (built with `-xb`); the speed
harness's checksums the host's, `mfndpos` 6.8% faster; the whole game's checks clean, its
saves and restores 12% fewer cycles a turn (RAM-PLAN.md).

Added on 2026-11-18 (commits 81-83; Jolyon, asked whether they join: "You do what you think is
best"), three fixes made on the far-spaces fork and not far-specific: 81. `555bcab` r74
(compat #77): a function first reached from a branch known to be dead was translated with
warnings held back, and every function first reached from it; each is now translated at the
default level. It changes no code. 82. `6990a68`: warning 2024 ("Reference to data in another
bank", the bank call check of commit 72) gives the data's location, its bank and the bank it is
read from; no code changes. 83. `4f65bc7` r75 (compat #78): five optimisations took a function's
code, or a constant it returns, into a caller in another section, and its literals stayed
behind (the analyzer's automatic inlining, the intermediate code's cheap inlining, the native
code's simple inlining, constant-return extraction, constant-call evaluation); each is now kept
to callers in the callee's section, a constant call's result going into the caller's. In the
banked game this fixes `punish` and `domonability`, which read a message of bank 5's at its
address in their own bank; it changes nothing in a program with one code section.

Results 2026-11-18 (83 commits; the patch files give tree 158d50f, the installed compiler's).
Autotest 1,621 emulations, all 0; corpus against 80 commits: 1,090 of 1,095 identical, the
others r75 (four configurations) and `opp_vector.cpp` at bc-O2 (the known heap-dependent one),
no status changes; repros 46 of 75 (r74, r75 fixed); nethack64 `.crt` and `.prg`
byte-identical, `make test` 5/5; NetHack (C64), per file: all 108 records identical to 80
commits' (1,187,381 B). The whole far game linked by the fork with these commits: no warning
2024 from banked code (79, all resident objects read while the literal's bank is mapped),
banks 6,588 B smaller, resident code 603 B bigger (bank call stubs), bank 5 519 B over until
the plan was repaired (`docs/data/wholegame-far-2026-11-18.txt`). The far-spaces series is
now five commits on these 83.

Added on 2026-11-21 (commits 84-85; Jolyon: "You absolutely can add it to the pin"), an upstream
fix: 84. upstream `9d39d74` ("Fix more assembler global aliasing", 2026-09-26), backported
unchanged, r77 (compat #80): `NativeCodeBasicBlock::GlobalLoadStoreForwarding` took a register
loaded from an address (`LDY ACCU+0`) for a copy of it across a `JSR` to a function that writes
that address and leaves the register, so after `huge[idx(299)] = 1`, `small[idx(2)]` read
`small[43]`; every optimisation level, native code. A call now forgets the copies of addresses it
may change, and the intermediate code's assembler aliasing is made exact to match. Found
writing the far-spaces fork's `fardefaulttest.c`; bisected over 182 upstream commits. 85.
`autotest/callindexforwardtest.c`, which fails in all five native configurations on 83 commits.

Results 2026-11-21 (85 commits; the patch files give tree 86e89ea, the installed compiler's).
Autotest 1,621 emulations, all 0 (the new test in all ten configurations); corpus against 83
commits: 1,097 of 1,110 identical, the others r77 and the new test (four configurations each),
`bankcallstubtest.c` (four: the same bug, X kept across a `JSR`, which the test survived because
the two values share a high byte) and `stripedarraytest.c` at -O0 (one reload fewer: an `INC` of
byte +1 does not change byte +0), no status changes; repros 47 of 77 (r77 fixed); nethack64
`.crt` and `.prg` byte-identical, `make test` 5/5.

Added on 2026-11-22 (commits 86-87; Jolyon: "yes, add the r78 fix to the pin"), our fix of an
upstream bug, from the far-spaces fork (its commit 12): 86. r78 (compat #81):
`PeepholeReplaceOptimization()` sorted two loads through one pointer by offset, checking that the
first does not overwrite the pointer but not that the second does, so in
`for (; o; o = o->nobj) s += o->oclass;` the field was read from the next object (the first
object skipped, the last read through null); -O1 and up, bytecode and native, v1.32.273 and
upstream main 08b01c9. The swap now also needs the second load's destination to be neither the
pointer nor the first load's destination. 87. `autotest/loadordertest.c`, which fails in the
eight configurations above -O0 on 85 commits.

Results 2026-11-22 (87 commits; the patch files give tree 6560d6b, the installed compiler's).
Autotest 1,641 emulations, all 0 (the new test in all ten configurations); corpus against 85
commits: 1,111 of 1,120 identical, the others r78 and the new test (four configurations each) and
`opp_vector.cpp` at -bc -O2, which differs only by install path (85 commits copied to a path as
long as the candidate's give the candidate's file byte for byte), no status changes; repros 48 of
78 (r78 fixed); nethack64 `.crt`, `.prg`, `nethack128.prg` and `test128.prg` byte-identical,
`make test` 6/6. The far-spaces series is now twelve commits on these 87 (its own copy of the fix
dropped); pin + far-spaces on v1.32.273 give the fork's tree 85516a8.

Added on 2026-11-26 (commits 88-99; Jolyon, on the pin additions in `docs/TO-DECIDE.md`:
"compiler fixes i'm happy with whatever you recommend"). Seven fixes from the far-spaces fork
that are not far-specific, each followed by a test where a small one exists:
- 88-89: r86, compat #90. The value of `++`/`--` on a bitfield was its whole storage unit.
  Test: `autotest/bitfieldincdectest.c`.
- 90-91: r87, compat #91. `continue` in a `do`-`while` skipped the condition. The fix is
  upstream's 546b627. Test: `autotest/continuedowhiletest.c`.
- 92-93: r89, compat #93. A global reached only through a pointer in an initializer was
  folded to its initial value. Test: `autotest/initptrglobaltest.c`.
- 94: compat #95. A zero-page copy was shifted in place while still read. The fix is
  upstream's 679546b. No small test.
- 95-96: r91, compat #96. A return on a branch reached a bare `RTS`. The fix is upstream's
  3e2ffb6. Test: `autotest/splitexitreturntest.c`.
- 97: compat #97. Push and pop frame instructions of different sizes were merged. No small
  test.
- 98-99: r92, compat #99. `JoinTAXARange()` moved a logic op past a change of its index
  register. Test: `autotest/jointaxalogictest.c`.

Each new test fails on 87 commits: the first two in all ten configurations, the
initializer's at -O2, -Os and -O3, and the last two in the five native ones.

Results 2026-11-26 (99 commits; the patch files give tree 5fd735f, the installed compiler's):
- Autotest: 1,691 emulations, all 0.
- Corpus against 87 commits, over the autotests and the repros: 1,128 of 1,175 identical,
  no status changes. The other 47 are:
  - 22 builds of the five fixed repros;
  - 22 builds of the five new tests;
  - `opp_vector.cpp` at -bc -O2, which differs only by install path;
  - `opp_hashmap.cpp` and `structreturncontrolflow.c` at -n -O0, both of which pass. In
    `opp_hashmap.cpp` the old code stored a byte shifted left where the new code sign-extends
    it.
- Repros: 53 of 92 (r86, r87, r89, r91 and r92 fixed).
- nethack64: `.crt`, `.prg`, `nethack128.prg`, `test.prg`, `test-ef.crt` and `test128.prg`
  are byte-identical to 87 commits' builds. `make test` 6/6.

The far-spaces series is now 22 commits on these 99. Its 17th keeps only the far part of r86's
fix, the far object in the returned reference. With the pin it gives the compiler and library
sources of the fork's 53e86f0, the compiler the C128 game is linked with (far31), plus the five
new tests.
