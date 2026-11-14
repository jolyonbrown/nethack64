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
| Code | **≈ 1.19 MB** | 1,161,881 B in the 107 files that compile, 8.9 B/line, plus about 24 KB for `mhitm.c` (a compiler abort, T1.45). 1,964 functions; the largest is `doapply()` at 11,208 B; 10 are over 8 KB, none over 16 KB |
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
into their main caller; a file's literals are spread over its functions by code size;
switch and DMA costs are still estimates.

## Next

1. **A wider profile:** a bot that plays more of the game (deeper levels, special levels,
   items, shops), and a call trace for the overlay-cache question.
2. **Refine the partition:** literals placed with the functions that use them, the resident
   core and the cold set for the hybrid, and the overlay cache for B.
3. **Prototypes in VICE:** (a) an EasyFlash bank switch through a generated trampoline,
   cycles per call; (b) an REU overlay fetched into `$8000-$BFFF` with no cartridge, time
   per KB; (c) a trampoline that copies a returned string when it points into the window.
4. **Oscar64 past 64 banks**, as a pin patch, if B or a large cartridge wins.

Then ADR-0008.
