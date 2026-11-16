# Banking spike (Phase 2: T2.1, T2.2)

Status 2026-11-14: what has to fit is measured, the coupling and the constant-data problem
are quantified, and the hardware and compiler limits are checked. The experiments
(dynamic call counts, a partition simulation, prototypes in VICE) are next; the decision
goes to an ADR (ADR-0008), which revisits ADR-0003. Options A, B and C are as defined in
ARCHITECTURE.md "Code: banking".

## What has to fit

Measured 2026-11-14, C64 configuration, the 59-commit compiler, with the harness's stubs
`__noinline` (`docs/data/oscar64-pin59n-c64conf-2026-11-14.json`):

| Item | Size | Notes |
|---|---|---|
| Code | **≈ 1.19 MB** | 1,161,881 B in the 107 files that compile, 8.9 B/line, plus 23,380 B for `mhitm.c`, which aborts the compiler (T1.45; measured with the candidate fix, pin commits 60-61): 1,185,261 B in all. 1,964 functions; the largest is `doapply()` at 11,208 B; 10 are over 8 KB, none over 16 KB |
| String literals | 210,562 B | 13,134 literals in the files' own code (`options.c` 9.6 KB, `trap.c` 9.4 KB, `apply.c` 8.6 KB); not merged across functions |
| Named initialised data | ≈ 61 KB | `mons[]` 21,065 B, `objects[]` 11,284 B, `rooms[]` 4,920 B, `obj_descr[]`, `roles[]`, `u`, `artilist[]` |
| Dynamic state | 45-60 KB | T2.3; the current level alone is 16,813 B |

A file and its stubs are compiled alone, so cross-file inlining that a whole-program build
might do is not counted, and the window port and C64 runtime are not included.

## How the code is coupled

From the harness listings (`tools/measure/callgraph.py`; static call sites, not
frequencies):

- 11,010 call sites call another file's function; 2,286 call one in the same file.
- A small resident core absorbs much of that:

| Resident set (by cross-file call sites) | Share of those sites | Code |
|---|---|---|
| top 10 functions | 37% | 4.7 KB |
| top 25 | 51% | 8.7 KB |
| top 50 | 62% | 29 KB |
| top 100 | 74% | 49 KB |
| top 200 | 85% | 93 KB |

- The most called: `rn2` (1,310 sites from 67 files, 36 B), `You` (797), `pline` (597),
  `impossible`, `rnd`, `dist2`, `pline_The`, `newsym` (4,030 B), `eos`, `is_pool`, `Norep`,
  `body_part`. Two big ones are near the top: `newsym` and `makemon` (8,737 B).

## Constant data across banks

A banked function's literals and tables can only be read while its bank is mapped. A
source scan (preprocessed, each file's own code) gives the size of the problem:

- **Literals passed to another file's function:** 5,053 of 19,612 cross-file call sites,
  to only 82 functions. `pline` 1,674, `You` 1,043, `pline_The` 276, `impossible` 266,
  `Your` 257, `strncmpi` 197, `You_feel` 196, `verbalize` 119, `You_hear` 111, `panic` 93,
  `You_cant` 77, `losehp` 71 (it keeps the string as `killer`), `otense` 61, `Tobjnam` 60,
  `aobjnam` 50, `yn_function` 46. Safe when the callee is resident and finishes with the
  string before it calls into another bank: true of the message family, which formats into
  a buffer first.
- **Literals returned:** 40 functions, 34 of them called from other files (`align_str`,
  `currency`, `foodword`, `getrumor`, `mbodypart`, ...). A trampoline can copy a returned
  string to a resident buffer when the pointer lies in the bank window.
- **Literals kept in globals:** `nomovemsg` 30 sites, `killer` 27, `digtxt` 12 (447
  `= "..."` sites in all, most of them locals). These need the literal resident or copied.
- **Static tables passed out:** 149 calls (`getobj` 16, `skill_init` 13, `dodoor` 4).

## Mechanisms

- Oscar64 places code in banks with `#pragma region(name, start, end, , bank, {...})` and
  reports a function's bank with `__bankof()`. Its cross-bank call helper `EF_CALL` is C++,
  so C needs generated trampolines.
- Checked 2026-11-14: a banked function's string literals go into its bank, after its code
  (the bank's code section), and a static `const` table into the bank's data section; only
  resident code's literals are copied to RAM at boot. So the constant-data rules below
  apply as stated: nothing moves literals out of a bank by itself.
- Checked 2026-11-14: `__VA_ARGS__` macros work, and a `#define` in one source file does not
  reach the next file of the same compile. So a per-bank wrapper file can
  `#define f(...) f_B(__VA_ARGS__)` and `#include` the unchanged NetHack file: calls inside
  the bank go straight to `f_B`, while calls from other banks, and `&f` (no parenthesis, no
  expansion), reach a resident trampoline `f`.
- **Oscar64's limit: 64 banks**, for cartridges and for disk overlays alike: bank sets are a
  `uint64` mask and the images arrays of 64 (`Linker.h` 87, 319-323). A bank number of 64 or
  more compiles with no diagnostic (checked: a region in bank 64 is accepted silently).
  `-tf=crt` always writes an EasyFlash image (type 32) whatever `-cid=` says; `-tf=crt8`
  and `-tf=crt16` write 8 KB or 16 KB chips for other types. Raising the limit is a pin
  patch: a wider bank set, sparse bank images, every 64 in `Linker.cpp`, `__bankof`'s
  `unsigned char`, the EasyFlash writer's bank field.

## Hardware with more than 1 MB

Research of 2026-11-14 (sources in REFERENCES.md, "Large cartridges"):

| Type | Size | Window | REU too? | Runs on |
|---|---|---|---|---|
| EasyFlash | 1 MB | 16 KB at `$8000` | `$DF00` conflict (HARDWARE.md) | VICE, Ultimate family, KFF, EF3, Sidekick64 |
| GMod3 | up to 16 MB | 8 KB at `$8000` | yes (`$DE00` only) | VICE (3.5+; the image must hold exactly 256, 512, 1024 or 2048 chips); rare hardware, superseded by GMod4 |
| GMod4 | 8 MB | two 8 KB windows | not documented | no emulator yet; iComp production run in 2026 |
| Magic Desk 16 | 2 MB | 16 KB | yes | VICE 3.10 (we have 3.7.1), MiSTer |
| TwoMegabyter | 2 MB | 16 KB | yes | Ultimate firmware 3.15 only |
| REU, no cartridge | up to 16 MB | (DMA) | — | VICE, Ultimate family (with "REU preload" of an image at start-up), C64 Ultimate (16 MB), RAD, Turbo Chameleon, MiSTer |

No cartridge over 1 MB runs on both VICE and the Ultimate family; a large REU does, on
everything we care about. GMod3's 8 KB banks would not take the 10 functions over 8 KB.

## What follows for the options

- **A, EasyFlash only:** does not fit. Code alone is ≈ 1.19 MB, and the literals have to
  travel with it.
- **A larger cartridge:** GMod3 has the room but runs only in VICE and needs functions split;
  the 2 MB types divide the audience between VICE 3.10 and Ultimate 3.15. Each also needs
  Oscar64 past 64 banks.
- **B, REU overlays:** the widest audience for more than 1 MB, and no `$DF00` conflict. The
  cost is DMA time each time an overlay comes in (about 1 ms per KB), so it stands or
  falls with how often hot code crosses overlays. It also needs more than 64 overlays of
  16 KB, or a bigger window.
- **C, EasyFlash for hot code plus REU overlays for the rest:** two mechanisms, and the
  `$DF00` conflict as today.
- **All of them** need the resident core (message family, string helpers, RNG: a few KB) and
  one rule for constant data.

## First simulation (2026-11-14)

Call counts from the host game built for gprof (`tools/host-build.sh --profile`: `-pg`, no
inlining, no sibling calls) and played by `tools/profile_play.py` (6,497 commands in
discover mode: runs, steps, travel to seen down staircases, searching, resting). The game
went 10,510 turns (calls of `movemon()`) and made 26.2 million calls to NetHack functions,
about 2,500 per turn, but stayed on levels 1 and 2: it called 697 of the 1,963 functions,
35% of the code by size. The hottest are monster movement's small helpers (`isok` 3.25
million calls, `dist2`, `distmin`, `is_pool`, `is_lava`, `t_at`, `on_level`).

`tools/measure/bankpart.py` takes those counts and the Oscar64 sizes, picks a resident
core by calls absorbed per byte, clusters the rest by heaviest call first into banks, and
counts the calls that leave their bank:

| Resident core | 16 KB banks | Calls leaving a bank per turn | 8 KB banks | per turn |
|---|---|---|---|---|
| none | 71 | 504 | | |
| 4 KB | 71 | 130 | | |
| 8 KB | 71 | 83 | 140 | 249 |
| 12 KB | 71 | 75 | | |
| 16 KB | 70 | 99 (the greedy clustering is not monotonic) | 139 | 170 |
| 24 KB | 70 | 74 | | |

- **Execute-in-place switching is cheap:** about 80 trampolines per turn, at the order of
  100 cycles each (to be measured), is under 10 ms a turn.
- **An overlay window that reloads on every crossing is not:** at about 1 ms per KB, 80
  crossings of 16 KB overlays would cost seconds a turn. Option B needs a cache of several
  small overlays, and a call trace (not only counts) to size it.
- **The hybrid looks workable:** with the literals spread over their files' functions the
  code needs 84 banks of 16 KB; put the 62 hottest in flash and the coldest 21-22 (about
  350 KB) in REU overlays, and this game never called into the overlays. That says as much
  about the bot as the code: deeper levels, shops, prayer and the endgame would reach some
  of it, so the next profile has to play more of the game.

Caveats: one bot game; the partition is greedy; statics that Oscar64 inlines are folded
into their main caller; a file's literals are spread over its functions by code size.

## What a switch costs (measured in VICE, 2026-11-14)

`tests/spikes/bankcall.c`, run by `tests/spikes/run_bankcall.py` (headless VICE 3.7.1,
EasyFlash and a 512 KB REU, interrupts off, CIA 2 timer A, 64 calls of an `int (int, int)`
function, the in-line loop subtracted):

| What | Cycles |
|---|---|
| call to a resident function | 57 |
| call within a bank | 57 |
| call into another bank through a resident C trampoline (remember the bank, write `$DE00`, call, write it back) | 91, so **34 for the switch** |
| REU fetch into `$8000`, 1 byte (the set-up) | 66 |
| REU fetch, 1 KB / 4 KB / 16 KB | 1,089 / 4,203 / 17,457: about 1,090 per KB |

So execute-in-place costs about 3 ms a turn at the simulated 80 crossings, and an overlay
costs about 1.1 ms per KB each time it is fetched: option B needs overlays that are
rarely fetched, not just rarely crossed. (An Oscar64 EasyFlash program starts with no
KERNAL run and the cartridge not mapped: the prototype maps the ROMs and initialises
the CIAs first, as Oscar64's own sample does.)

The REU times vary from run to run of the same binary (2026-11-15: 1 KB took 1,089 and
1,215 cycles, 16 KB 17,499 and 17,289): the screen is on, so the VIC takes the bus on
its bad lines and the DMA waits, more or fewer times depending on where the raster is.
The call times do not vary.

## The bank generator (2026-11-15)

`tools/bank/bankgen.py` rewrites copies of the source files for a bank plan
(`tools/measure/bankpart.py --plan-out`), with no hand edits to `port/`:

- `#pragma code(nhbank_N)` before each function of bank N, `#pragma code(code)` before
  resident ones; data stays resident, and a function's literals go with its code.
- `#define f(...) f__bN(__VA_ARGS__)` renames the definition and is in force only in the
  file's functions of bank N, so their calls go straight to `f__bN`; calls from elsewhere,
  and `f` used as a pointer, reach `f`, a resident trampoline appended to the file, which
  switches the bank and copies string arguments and results out of the window
  (`nh_stash()`).
- A function the plan does not name (Oscar64 inlined it in the measurement) follows its
  callers into their bank when they all share one: Oscar64 inlines a function called once
  only into a caller in the same section (at `-Os`), so left resident it would stay a
  separate resident function. 260 functions follow this way.
- Variadic functions stay resident (a trampoline cannot pass `...` on): the 13 of the
  message family. So do a name that is also a macro somewhere (4), and `objects.c`, which
  includes itself.
- Oscar64 expands a function-like macro's name even with no `(` after it (r61, compat #63),
  so the definitions are renamed in the text, and a run of code gets no macro for a name
  it uses without `(`, as a struct member (`botl.c`'s `role->rank[i]`) or a function
  pointer: 12 names in this plan, whose calls there go through the trampoline.
- A pointer kept in a global outlives the call that made it: `killer = "falling rock"` in
  a banked function, or `occtxt = txt` given a trampoline's temporary copy. Every
  assignment to a global or file-static `char *` (`killer`, `delayed_killer`,
  `nomovemsg`, `occtxt`, ... and 2 file statics) is wrapped in `NH_KEEP()`, which copies
  a pointer into the bank window or into a temporary copy into that variable's own
  128-byte buffer and leaves any other pointer alone (`nomovemsg == eatmbuf` still
  works); 158 assignments, and the one literal stored in a struct field
  (`options.c`'s `obj_descr[SLIME_MOLD].oc_name = "fruit"`). None of these globals is
  compared as a pointer except that one.

**Checked on the host.** `tools/host-build.sh --banked build/bankplan-8k.json` builds the
whole game from the rewritten source: 2,142 functions in 84 banks of 16 KB around an 8 KB
resident core (the plan from the first simulation, literals spread). On the host each
banked function checks on entry that its bank is the one selected, so a call that
reached another bank's function without its trampoline, which on the C64 would run
whatever the window holds, stops the game. `tests/host_smoke.py` passes on it (play,
save, restore), and so does a 6,000-command bot game (`tools/profile_play.py --install
build/host-banked-install`, levels 1-3) with no check firing. With the bank switch taken
out of the trampolines, makedefs's first banked call stops at its check (`monst_init__b35
(bank 35) entered with bank 0 selected`), so the checks do run. This covers the paths
those games take, not the whole game.

**Not yet:** the Oscar64 build of the rewritten source; the code size of the
trampolines; pointers into a bank kept anywhere but those variables (none found by
these patterns, but they are patterns).

## The whole game in one Oscar64 compile (2026-11-15)

Oscar64 compiles a program in one run, so the banked game is one compile of all 108
files (`tools/bank/build_c64.py`). With the bank-limit patch it parses all of them in
2.4 s, and then did not finish in an hour. Stack samples (gdb, run as the compiler's
parent) put it in `GlobalAnalyzer::MarkCycle`. Two of the global analyses walk every
simple path through the call graph (r62, compat #64), and a single file's measurement
never showed it because its stubs leave only small cycles:

- NetHack's direct calls form **one cycle of 279 functions**, through `panic()` and
  `done()`: `You`, `Monnam`, `alloc`, `addinv` and the rest all reach each other. Every
  function on it is recursive to Oscar64, so it takes its parameters on the stack.
- `CheckFastcall`, which places each function's zero page parameters above its
  callees', also follows calls through pointers to every address-taken function of the
  same type. Its graph has **one cycle of 2,465 functions** with the game's own `main`
  (2,694 with the harness's table of every function), 426 of them on it only through
  such calls.

`MarkRecursions` now uses Tarjan's search, and `CheckFastcall` walks each function once,
keeping per strongly connected component what the old repeated walks found. Both give
exactly the old results (checked by running old and new side by side; candidate pin
commits, T2.8), and the compile gets through the global analysis in seconds. It then
stopped twice more:

- **r63, wrong code.** A call with constant arguments, folded while compiling, took the
  value of the wrong argument when the callee had a parameter it never reads.
  `check_recordfile()`'s `fqname(RECORD, SCOREPREFIX, 0)` folded to 5 and failed to type
  check, and the compiler then crashed writing its error file. The per-file measurements
  cannot show it: their harness takes every function's address, and an address-taken
  function keeps its parameters. Fixed in the interpreter (candidate pin commits, T1.47).
- **Memory.** With that fixed, the compile runs out of a 6 GB address-space cap after
  160 to 220 s, in intermediate code generation, with 2,537 procedures done and native
  code generation still to come: 1.5 GB after parsing and analysis, then 4.3 GB more. A
  few procedures cost far more than the rest (`burn_object` 52 s, `unbless` 13 s,
  `realloc_obj` 305 MB), and they compile quickly in the per-file measurement, so
  whole-program inlining (other files' functions, the bank trampolines) is the first
  suspect. On a 31 GB desktop it ran out of a 16 GB cap the same way. Most of the growth
  is the data flow sets each basic block keeps over all the program's statics (2.7 GB of
  it by 2,750 procedures here), which nothing reads once its procedure is optimized.
  Freeing them (now pin commit 68; no change in any of 1,022 corpus programs) let **the
  whole game compile in one run** on the desktop: 619 s, peak 13.2 GB, through native code
  generation, until the linker stopped on "Cannot place stack section" because the data
  does not fit yet (T2.3).
- **The call check passes.** `build_c64.py` resolves calls into the bank window through the
  map (every bank's code starts at $8000, and the listing names such an address after bank
  1's object) and also checks the intermediate code, which names every callee: no call of
  41,068 in the listing, or of 25,985 direct calls, crosses a bank without a trampoline,
  and no banked function's address is taken.
- **The banks overflow.** The plan packs a median 14 KB of code into each 16 KB bank, but
  the link left 342 KB of banked code and 33 KB of banked literals unplaced: about 1.69 MB
  of banked content against 1.15 MB of planned code. The plan counts no string literals
  (167 KB in all); functions come out 1.24x their per-file size, mostly copying arguments,
  since the harness's table of every function makes every trampoline address-taken and so
  a stack call; trampolines take 73 B each (130 KB in all); and `mhitm.c`, which did not
  compile when the plan was made, stays resident.
- **With the game's own `main()`** (`newgame(); moveloop();` in place of the table, so only
  what the game reaches is compiled and only what it takes the address of is called through
  pointers; 608 s, 13.2 GB): 3,712 functions and **1.55 MB of code**: 1.37 MB banked, 114 KB
  of trampolines (1,638 at 70 B), 66 KB of other resident code, plus 166 KB of literals in
  the banks. Banked functions come out 1.16x their per-file size: the per-file measurement
  calls other files' code through cheap stubs, where the game calls recursive or
  address-taken functions with stack parameters, so the real code is about 30% more than
  its 1.19 MB. Banked content of about 1.54 MB needs some 100 banks of 16 KB, not 84. The
  call checks pass (0 of 36,393 listing calls, 0 of 25,079 direct calls).
- **A plan that fits: 103 banks** (2026-11-15, `docs/data/bankplan-2026-11-15.json`). Sizes
  come from the whole-game build itself (`tools/measure/wholesizes.py`: each function's code
  and the literals the map places after it), not the per-file measurement, and
  `tools/bank/planfix.py` repairs the banks a build overflows instead of re-planning, which
  regroups everything and shifts the sizes again. The steps, each a 650 s build on the
  31 GB desktop: real sizes with per-file literal estimates, 102 banks, 8.4 KB left over;
  literals per function, 1.5 KB; then 103 banks, 1 KB, but `doapply` alone was 16.7 KB with
  the twelve static helpers Oscar64 had inlined into it, which the plan now keeps out of line
  (a `noinline` list that bankgen.py turns into `__noinline`); two repairs later every banked
  object is placed: 1,584,245 B in 103 banks, median 15,530 B each. The same plan's host
  build passes the smoke test and bot games to level 6 with every bank check on, and the
  C64 build's call checks pass. What is left unplaced is all resident: 137 KB of code (most
  of it trampolines, 1,555 of them at 71 B) and 116 KB of data.
- **Resident data: 150 KB** in that build: 61 KB initialised (`mons` 21 KB, `objects` 11 KB,
  `rooms` 5 KB), 45 KB of BSS (`level` 17 KB, the screen and vision buffers), 32 KB of
  resident code's literals, about 10 KB of static stack frames, and 42 KB in 3,676 objects
  under 64 B. That is what the RAM plan (T2.3) has to fit beside a 16 KB bank window.

Two measurement caveats follow. The harness's `nh_refs[]` takes the address of every
function a file defines, and Oscar64 gives every address-taken function stack
parameters, so the 1.19 MB of code was measured with stack calls throughout: probably
high. And the whole game, compiled together, has the 279-function recursive cycle that
no single-file compile has, which costs stack calls in the other direction.

## Bank calls through linker stubs (2026-11-15)

Where the trampolines' bytes go, in the build whose plan fits (1,749 trampolines,
124 KB):

| Trampoline | Number | Bytes | Median |
|---|---|---|---|
| arguments on the stack | 1,099 | 85.9 KB | 75 B |
| on the stack, copying strings | 152 | 19.4 KB | 123 B |
| arguments in zero page | 400 | 11.9 KB | 25 B |
| in zero page, copying strings | 98 | 6.5 KB | 65 B |

A function on the game's big recursive cycle takes its arguments on the stack, and its C
trampoline has to set up a frame, save a register and copy every argument into the new
frame (about 8 bytes of code per byte of argument). A stub that leaves the arguments where
the caller put them, and does not move the software stack pointer, needs no copying. It
cannot be written by hand, though: a stub in assembler would hide its call to the real
function from Oscar64's call graph, from which the compiler decides which functions are
recursive (the others get static frames) and where each function's zero-page parameters
go, and that would be wrong code.

So the linker makes the stubs (the pin's commits 72-73, added 2026-11-15 on Jolyon's
go-ahead). A program that names a bank call routine,
`#pragma runtime(bankcall, nh_bankcall)`, has every call into a bank from outside it, and
every use of a banked function's address, go through a 6-byte resident stub,
`jsr nh_bankcall; .byte bank; .word function`; calls within a bank stay direct. The pass
runs after all of the compiler's analysis, which saw the calls as they are written. The
code at a call was generated for a direct call, so the routine has to leave A, X, Y, the
zero page and the software stack as it found them, on the way in and on the way out:
Oscar64 passes some arguments and results in A and X and keeps values in X or Y across a
call to a function that preserves them (the VICE test has such a loop counter). The
routine keeps the caller's bank and its own return address on the hardware stack (3 bytes
per crossing) and patches its own operands, so it is not re-entrant: no interrupt handler
may call banked code (ours is the KERNAL's). A program without the pragma links exactly as
before: autotest 1,571/1,571, corpus 1,021/1,022 identical, the one difference being
compat #67, an existing read of uninitialised memory in the bytecode generator that the
new compiler's heap exposes.

- **Checked in VICE** (`tests/spikes/bankstub.c`, `run_bankstub.py`): 13 checks pass:
  recursion through two banks with stack parameters, a byte in A and an int in A/X, a loop
  counter kept in Y across calls, `long` results, function pointers handed to resident
  code and kept in const tables, tail calls in both directions, callbacks; after every
  return the caller reads a tag in its own bank. A switch costs **142 cycles** against the
  C trampolines' 34: about 9 ms a turn at the simulated 80 crossings.
- **bankgen.py --linker-stubs:** a banked function keeps its name and is called directly;
  only the 295 that take or return a `char *` keep a renamed twin and a trampoline, which
  copies the strings out of the bank window. The host build of this rewrite passes the
  smoke test and a 6,000-command bot game (levels 1-3); there is no entry check on the
  host in this mode, since nothing there sees the linker's stubs.
- **Strings in file-scope initialisers.** Oscar64 puts a string literal into the code
  section in force where it is written, so `const char *names[] = {"alpha", "beta"}`
  between two banked functions had its strings in a bank, though the table is resident
  data that every bank reads (checked with a small program). This was true of the
  trampoline builds too. bankgen.py now wraps each banked definition in pragmas of its own,
  and the linker warns of any reference to data in another bank ("Reference to data in
  another bank").
- **The whole game with stubs** (one compile on the desktop: 624 s, peak 12.8 GB): every
  check passes. No call of 30,912 in the listing reaches another bank's code directly, no
  direct call of 23,581 reaches a renamed twin from outside its bank, no banked function
  writes the bank register, and nothing refers to data in another bank. The 103 banks hold
  1.58 MB as before: bank 4 overflowed by a few hundred bytes, `planfix.py` moved 8
  functions out over two rounds, and the third build places every banked object
  (`docs/data/bankplan-2026-11-15-stubs.json`). **Resident code: 65.1 KB instead of
  156.4 KB:**

| Resident code | Trampolines | Stubs |
|---|---|---|
| trampolines | 1,749, 123.6 KB | 253, 26.1 KB (string handlers) |
| bank call stubs | — | 2,026, 12.2 KB |
| bank call routine | — | 91 B |
| other: NetHack functions the plan keeps resident | | 11.7 KB |
| other: the Oscar64 runtime and libc (`fpscanf` 2.3 KB, `sformat` 1.9 KB) | | 13.2 KB |
| other: the variadic message family | | 1.8 KB |
| **all** | **156.4 KB** | **65.1 KB** |

  Resident data is 155 KB, 9.3 KB more than before: the strings of file-scope tables, now
  resident (see below). With 64 KB in the machine, the data is now the larger problem
  (T2.3); the 26 KB of string trampolines and the 12 KB of stubs are the next code to look
  at (a stub could live in its caller's bank if the compiler made far calls at the call
  site).
- **Two compiler bugs on the way.** r64 (compat #66): with the callees called directly,
  `PropagateVariableCopy` forwarded `lev_by_name()`'s load of a struct copy to the copy's
  source without its memory base, and the compiler aborted; fixed by the pin's commits
  70-71. And compat #67, bytecode only.

## Next

1. **A wider profile:** a bot that plays more of the game (deeper levels, special levels,
   items, shops), and a call trace for the overlay-cache question.
2. **Refine the partition:** literals placed with the functions that use them, the resident
   core and the cold set for the hybrid, and the overlay cache for B.
3. **Prototypes in VICE:** (a) and (b) done (above); (c) a trampoline that copies a
   returned string when it points into the window; then the generator that writes the
   wrappers and trampolines for real files (hack.c, apply.c, zap.c), as T2.1 asks.
4. **Oscar64 past 64 banks**, as a pin patch, if B or a large cartridge wins.

Then ADR-0008.

**2026-11-16: ADR-0008 proposed.** The whole game is 104 banks; with the bot's new `--wide`
mode (inventory, spells, all 13 roles) only 4 banks go unentered, and keeping the 62 entered
most on the EasyFlash leaves about one entry a turn into the rest, which would run from the REU
through a RAM window under the cartridge (`tools/measure/bankplace.py`,
`docs/data/bankplace-2026-11-16.txt`). Packing the overflow on the cartridge instead (about 2:1)
leaves too few banks unpacked: about 20 unpackings a turn.
