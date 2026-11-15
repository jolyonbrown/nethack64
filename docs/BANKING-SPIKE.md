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
  it by 2,750 procedures here), which nothing reads once its procedure is optimized. An
  experiment that frees them (no change in any of 1,017 corpus programs) let **the whole
  game compile in one run** on the desktop: 619 s, peak 13.2 GB, through native code
  generation, until the linker stopped on "Cannot place stack section" because the data
  does not fit yet (T2.3).
- **Bank sizes.** That map has 1.31 MB in the 84 banks, median 16,380 of 16,384 B,
  against a plan of about 8 KB of code each, and the listing check is not reliable on a
  partial link (unplaced objects): both still to understand (T2.8).

Two measurement caveats follow. The harness's `nh_refs[]` takes the address of every
function a file defines, and Oscar64 gives every address-taken function stack
parameters, so the 1.19 MB of code was measured with stack calls throughout: probably
high. And the whole game, compiled together, has the 279-function recursive cycle that
no single-file compile has, which costs stack calls in the other direction.

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
