# Brief: making NetHack 3.4.3 fit and run acceptably on a Commodore 64

You are one of several independent researchers asked for ideas. Work from the facts below,
research where facts matter, and say clearly what is measured, what is sourced (give URLs)
and what is your own inference.

## The project

- Goal: the real NetHack 3.4.3, compiled from its own C source, running on a Commodore 64.
  Primary target: an **EasyFlash** cartridge (1 MB flash, banked into a 16 KB window at
  `$8000-$BFFF`, bank register at `$DE00`) plus an **REU** (17xx RAM Expansion Unit,
  512 KB to 16 MB, DMA at about one byte per cycle), in VICE and on real hardware (the
  Ultimate family: Ultimate 64, C64 Ultimate, 1541 Ultimate II+). Fallbacks: a C128, then
  (stretch) a stock C64. The aim is real hardware; buying cartridges or expansions is fine.
- **Port, don't rewrite**: the game logic stays NetHack's code. Our work is making it fit:
  compiler compatibility, banking, memory, I/O, an 80-column window port. Changes to game
  behaviour (cutting features, shrinking buffers, changing RNG use) need a decision record
  first. The modified source must stay buildable by gcc as ordinary Unix NetHack too (a host
  build that plays, saves and restores is the regression test), so C64-specific changes sit
  behind `#ifdef` or in macros. Mechanical, scripted transforms are preferred to hand edits
  across many files.
- **Compiler: Oscar64** (a C/C++ compiler for the 6502 by Dr. Martin Ottmann: native 6502
  code or bytecode, whole-program compilation, 16-bit `int`, static frames for non-recursive
  functions, function parameters in zero page). We use v1.32.273 plus 73 commits of our own
  (bug fixes, and a linker feature that makes bank-call stubs). We can and do change the
  compiler; each addition is reviewed. The game is compiled `-Os` (native code, size first).
- Display: our own soft 80-column screen (a 4x8 font drawn into a 320x200 bitmap), 80x25.
- Hardware rules: never read `$DF00-$DFFF` (shared with the REU); do not use the EasyFlash's
  256 bytes of RAM.
- The lead developer's direction: explore far data in the compiler (below), with attention to
  speed; try zero page and the 6510's undocumented opcodes; avoid needing another CPU (65816 /
  SuperCPU); cutting the game is a last resort. He wrote demos in the scene era and welcomes
  scene tricks, and accepts that some C64/6502-specific code amendments will be needed.

## Where it stands

- All 108 NetHack C files compile with Oscar64. The whole game's code and literals fit 103
  banks of 16 KB (1.58 MB) of the cartridge and REU: execute-in-place banking, with
  linker-made stubs: a banked function called from another bank gets a 6-byte resident stub
  (`jsr bankcall / .byte bank / .word fn`); a switch costs 142 cycles; about 80 crossings a
  turn by a call-graph-driven partition. Resident code is 65 KB today: 26 KB of C trampolines
  for the 295 functions that take or return a `char *` (strings copied out of the bank
  window), 12 KB of stubs, 27 KB of other code (libc, runtime, hot core). It could come down
  to perhaps 15-20 KB.
- **The data does not fit.** What NetHack reaches through plain 16-bit pointers, from code in
  many banks:

| Data | Size on the C64 | Kind |
|---|---|---|
| `mons[]` | 21.1 KB | constant table, read through `struct permonst *` everywhere (macros in every file) |
| `objects[]` | 11.3 KB | mostly constant; a few fields change in play |
| `level` | 16.8 KB | the current level: `struct rm locations[80][21]` (6-byte cells) and object/monster pointer grids |
| display and vision grids | about 13 KB | per-square arrays |
| `rooms[]`, `u`, `mvitals`, `dungeons`, buffers, other globals | about 21 KB | |
| other initialised tables (`obj_descr`, `roles`, `artilist`, options...) | about 22 KB | mostly constant |
| strings in code and file-scope tables | 37.7 KB | constant; 3,288 strings, nearly all under 64 B |
| static frames of non-recursive functions | 11.5 KB | many 256-byte `BUFSZ` buffers |
| heap: the level's monsters and objects, inventory | about 5-15 KB | estimate |
| software stack | about 4-6 KB | estimate |

  In all about 165-175 KB; the mutable part alone about 70-85 KB. The CPU sees about 34 KB of
  RAM in today's layout (EasyFlash 16K mode, KERNAL in), about 44 KB with the KERNAL banked
  out, 51-55 KB with no cartridge at all. NetHack's 16-bit DOS builds used far data
  (Borland's huge model, Microsoft's large model) for the same reason.
- Options considered: (1) far data in the compiler: 3-byte pointers, an REU page cache,
  chosen to explore; (2) restructure the data behind accessors with 16-bit pointers (constant
  tables and strings into banks, read through bank-switching fetches); (3) a CPU with wider
  addresses (65816), to avoid; (4) cut the game, last resort. The C128 was judged no help
  (its second 64 KB bank is not in view at the same time as the first).

## Measured (2026-11-15)

**Far access through the REU** (a spike in VICE: Oscar64 -Os C, REU 512 KB, cycles counted
by CIA timers). Far space = the REU in 256-byte pages cached in up to 64 RAM pages; a far
pointer = 3 bytes in zero page (offset, page, bank); a 256-entry translation table indexed by
the page byte says which bank's page of that number is in RAM, and where.

| Primitive | Cycles |
|---|---|
| translation, hit, through a function call | 40.1 |
| translation, hit, inlined, in place (the pointer's page byte becomes the RAM page, so its first two bytes are then a near pointer) | 20.9 |
| page fault, clean (a C handler and one 256-byte REU DMA) | 603 |

| Workload (warm cache) | Near | Far | Slowdown |
|---|---|---|---|
| list of 200 nodes, one translation a node | 12,116 | 20,146 | 1.7x |
| table of 252 records x 55 B, records inside a page, one translation a record | 19,424 | 32,766 | 1.7x |
| the same, a translation for every field | 19,424 | 59,098 | 3.0x |
| 80 x 21 grid of 6-byte cells, read and write each | 98,552 | 194,948 | 2.0x |
| 2,000 random grid reads (index arithmetic dominates) | 2,264,554 | 2,357,452 | 1.0x |
| the table through a 32-page cache, its 55 pages not fitting | 19,424 | 106,363 | 5.5x |

The hit path is six documented instructions (`LDX zp`, `LDA abs,X`, `CMP zp`, `BNE`,
`LDA abs,X`, `STA zp`, 19 cycles); none of the undocumented opcodes shortens it. Inline
assembler is not a safe home for it: Oscar64 does not treat an inline block as reading or
writing the variables it uses.

**The working set a turn** (the host game traced load by load, each access mapped onto the
C64 page it would touch; two 6,000-command games of a bot that explores, rests and descends):
a turn touches 112-124 pages (28-31 KB) of far data, 150-162 pages over ten turns; about
10,000 far accesses a turn (a third of them to globals; keeping 4 KB of hot globals near
leaves 57 a turn); faults a turn with a 64-page CLOCK cache: median 123-160; with 128 pages:
11-19. Priced at 21 cycles an access and 600 a fault: 0.25-0.5 s a turn on average.

**The game's speed before any far data.** The host game under callgrind: 175,786 x86
instructions a turn (mean over 13,896 turns of the bot on a crowded level 1: 26.7 monster
moves a turn). The hottest functions, copied verbatim from the source and run on one test
level both ways (gcc + callgrind; Oscar64 -Os + its emulator, same checksums), cost about
10 6502 cycles for each x86 instruction (7.9-10.3; `dist2()` 32.7). Estimate on a PAL C64
(0.985 MHz): about **1.8 s a turn** for this crowded game, **42 ms per monster move**,
1.26 s of it NetHack's own code; a turn with ten monster moves about 1 s.

| Where the host's instructions go, a turn | x86 instructions |
|---|---|
| monster movement (`movemon`, inclusive) | 115,733 |
| the status line (`bot()`, redrawn every turn because the `time` option is on; mostly `sprintf` and terminal output) | 36,623 |
| the hero's command (`rhack`) | 17,285 |
| messages (`pline`) | 8,052 |
| vision (`vision_recalc`) | 2,319 |

Hottest functions by own instructions: `mfndpos` 18.9%, `m_move` 12.5%, `can_reach_location`
5.8%, `isok` 4.7%, `is_pool` 4.4%, `is_lava` 4.3%, `newsym` 3.7%, `dochug` 3.1%, `dist2`
2.2%, `distfleeck` 2.0%, `gettrack` 1.8%, `attacktype_fordmg` 1.5%, `set_apparxy` 1.5%.

**Two hot spots** found in the 6502 profile (Oscar64's runtime routines show up on their own):
- `levl[x][y]` (`level.locations[x][y]`): a column is 21 rows of 6 bytes = 126 bytes, and
  Oscar64 multiplies `x` by 126 through its general `mul16by8` routine, about 250 cycles per
  access: 35% of all cycles in the `mfndpos` workload, 53% in `is_pool`/`is_lava`.
- `dist2(x0,y0,x1,y1)` = `dx*dx + dy*dy` in `int`: two 16-bit multiplications through `mul16`,
  80% of its cost; 388 calls a turn, about 0.2 s.

## The ask

Brainstorm alternative approaches, narrow and broad:

- **Narrow:** the two hot spots, and the general pattern behind them (Oscar64's code for
  NetHack's idioms). Where should such fixes live: the compiler, the source (behind `#ifdef`),
  the data layout, tables? What else of the same kind is likely hiding in the 12% of code
  measured so far?
- **Broad:** making NetHack fast enough on a C64 and making its data fit: refinements of the
  far-data plan, alternatives to it, hardware options that keep to the constraints, and prior
  art (other ports of NetHack, Hack, Rogue, Moria, Larn and similar to 8-bit or small-memory
  machines; how the DOS, Amiga and Atari ST ports managed; published 6502 techniques).

For each idea: what it is; the expected gain, with numbers where you can (from the
measurements above or from sources); cost and risk; how well it fits the constraints (port,
don't rewrite; Oscar64; real hardware; the host build keeps working); and the cheapest
experiment that would test it.

Deliver, in Markdown, under about 2,000 words:
1. A long list: at least 15 ideas, one or two lines each.
2. Your top 5, each with the fuller treatment above.
3. A deep dive on your focus area (below).
4. Anything in this brief you think is wrong, doubtful or missing.
