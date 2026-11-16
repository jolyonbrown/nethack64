# RAM plan (T2.3): the data does not fit a 64 KB address space

Status 2026-11-15: measured; Jolyon chose far data in the compiler (option 1), to be designed
from experiments. The direction after the brainstorm is at the end.

## What the CPU can see

The 6502 addresses 64 KB, and NetHack reaches its data through ordinary 16-bit pointers.
Whatever is not in the CPU's view at the moment the code dereferences a pointer does not
exist for it. The RAM a C64 can show the CPU:

| Configuration | RAM in view | Notes |
|---|---|---|
| EasyFlash 16K mode, KERNAL in (today's layout) | about 34 KB | `$0900-$7FFF`, `$C000-$CBFF`, `$0400-$07FF`; the bank window is `$8000-$BFFF`, the 80-column bitmap sits under the KERNAL |
| the same, KERNAL banked out, bitmap moved under the cartridge window | about 44 KB | `$E000-$FFFF` becomes data RAM; our own keyboard and interrupt code |
| no cartridge (all code from the REU, through an overlay window), no KERNAL | about 51-55 KB | minus the overlay window itself |

## What NetHack needs in view

From the whole-game build with the bank-call stubs (round three, every banked object
placed; `build/bank-c64-stubs3`). Everything here is reached by plain pointers from code in
many banks, so it has to be in view whenever that code runs:

| Data | Size | Kind |
|---|---|---|
| `mons[]` | 21.1 KB | constant table, read through `struct permonst *` everywhere (the `mondata.h` macros expand in every bank) |
| `objects[]` | 11.3 KB | mostly constant; a few fields change in play |
| `level` | 16.8 KB | the current level's map and object/monster grids (`levl[x][y]`) |
| display and vision (`gbuf`, `could_see`, `viz_clear`, `left_ptrs`, `right_ptrs`, ...) | about 13 KB | per-square grids |
| `rooms[]`, `u`, `mvitals`, `dungeons`, `bufs`, other globals | about 21 KB | |
| other initialised tables (`obj_descr`, `roles`, `artilist`, options, ...) | about 22 KB | mostly constant |
| strings in resident code and file-scope tables | 37.7 KB | constant; 3,288 objects, nearly all under 64 B |
| static frames of non-recursive functions | 3.2 KB | 2,306 frames, 11.2 KB in sum, many 256-byte `BUFSZ` buffers: Oscar64 already lays frames that are never live together over each other |
| heap: monsters and objects of the level, inventory | about 5-15 KB | estimate (ARCHITECTURE.md), not measured yet |
| software stack | about 4-6 KB | estimate |
| resident code | 65.1 KB | could come down to perhaps 15-20 KB (string trampolines, stubs, libc) |

Even leaving out every constant table and string, the mutable data alone (level, grids,
globals, heap, frames, stack) comes to roughly 62-77 KB, while the RAM left beside a minimal
resident code comes to about 25-40 KB. With the constants it is about 155-170 KB (the map's
155 KB counts each frame on its own, 8 KB more than they take; plus the heap and the stack).
`mons[]`, `objects[]` and `level` together, 49 KB, are more than any configuration above
shows the CPU.

So banking the code, which works (BANKING-SPIKE.md), does not decide whether the game runs:
the data does. NetHack 3.4.3 needs more data than a 16-bit flat address space holds. Its
16-bit DOS builds use far (segment:offset) data pointers for the same reason: Borland's
huge model (`MODEL = h`, `-mh`, `sys/msdos/Makefile.BC`) and Microsoft's large model
(`/AL`, `Makefile.MSC`).

## What could work

1. **A far-data model in the compiler.** Pointers to data become 3 bytes (bank or REU address
   plus offset); loads and stores through them go to resident routines that keep a cache of
   REU pages (or map a cartridge bank, for constant data). This is what the DOS builds did,
   and it needs no restructuring of NetHack's source beyond what the compiler does for it.
   Oscar64 has no far pointers (checked); adding them is a large change to the compiler
   (pointer size, every pointer operation, the libraries), bigger than all the compiler
   work so far. A far access costs about 21 cycles more than a near one when its page is in
   RAM (measured below: 1.7x to 3x in pointer-heavy loops), which a turn-based game may
   bear. It is the only option here that keeps the real data structures on a stock C64 with
   an REU.
2. **Restructure the data behind accessors**, keeping 16-bit pointers: the constant tables
   and strings into banks, read through generated bank-switching fetches (in the spirit of
   the stubs), and the per-type caches that pointer identity allows (`&mons[PM_X]`,
   `ptr - mons`). Mechanical, but touching thousands of sites, and it does not reach far
   enough on its own: the mutable data alone is still two to three times the RAM left.
3. **A CPU with wider addresses.** A 65816 (the SuperCPU, emulated by VICE's `xscpu64`) has
   24-bit addressing in hardware, so far data costs little, but it needs another compiler
   (Oscar64 does not generate 65816 code) and hardware that is rare. The C128 does not
   help: its second 64 KB bank is not in view at the same time as the first. Neither does
   the MEGA65 without far pointers in the compiler.
4. **Cut the game** (the stretch tier): smaller tables or fewer features. Against ADR-0001.

## Jolyon's direction (2026-11-15)

Option 1 is worth exploring, with attention to speed; try zero page and the 6510's
undocumented opcodes first; avoid option 3; option 4 only as a last resort.

## Measured: far access through the REU (2026-11-15)

`tests/spikes/fardata.c`, run by `tests/spikes/run_fardata.py` (headless VICE 3.7.1, REU 512 KB,
interrupts off, CIA 2 timers cascaded; all 16 checks of the far copies pass, writes surviving
eviction included). The far space is the REU in 256-byte pages, cached in up to 64 RAM pages;
a far pointer is three bytes in zero page (offset, page, bank); a translation table of 256
entries indexed by the page byte says which bank's page of that number is in RAM and where.

| Primitive | Cycles |
|---|---|
| translation, hit, through a function call | 40.1 |
| translation, hit, inlined, **in place**: the far pointer's page byte in zero page becomes the RAM page, so its first two bytes are then the near pointer | **20.9** |
| page fault, clean (a C handler and one 256-byte DMA) | 603 |

| Workload (Oscar64 `-Os` C; warm cache) | Near | Far | Slowdown |
|---|---|---|---|
| list of 200 nodes, one translation a node | 12,116 | 20,146 | 1.7x |
| table of 252 x 55 B, records kept inside a page, one translation a record | 19,424 | 32,766 | 1.7x |
| the same table with a translation for every field | 19,424 | 59,098 | 3.0x |
| 80 x 21 grid of 6-byte cells, read and write each | 98,552 | 194,948 | 2.0x |
| 2,000 random grid reads (the index arithmetic dominates) | 2,264,554 | 2,357,452 | 1.0x |
| the table through a 32-page cache, its 55 pages not fitting | 19,424 | 106,363 | 5.5x |

What follows:

- **Zero page matters most.** Both pointers have to be there for `(zp),y`, and translating in
  place halves the cost of a translation. The hit path is then six documented instructions
  (`LDX zp`, `LDA abs,X`, `CMP zp`, `BNE`, `LDA abs,X`, `STA zp`, 19 cycles); none of the
  undocumented ones (LAX, SAX, DCP, ISC, SBX, ANC, ALR, ...) shortens it. They would help the
  compiler's code in general: `LAX (zp),Y` saves the `TAX` of every 16-bit load through a
  pointer, for instance. Oscar64's assembler does not know them; `byt` can emit them.
- **Translating once an object** is what keeps the cost near 1.7x: a far allocator that keeps
  objects inside pages (as the list and the paged table do) and a compiler that reuses a
  translation for the fields it reads next. Translating every access costs about 3x.
- **The working set has to fit the cache.** A fault costs about 600 cycles (a handler in
  assembler would cut it), so even a full reload of 64 pages is only some 38 ms; but a working
  set larger than the cache faults on every pass, 5.5x here. NetHack's per-turn working set
  (the level, the vision grids, the monsters and objects on the level, the `mons[]` entries
  in use) needs measuring before the cache is sized.
- **Two compiler traps on the way**, both about inline assembler: Oscar64 does not take an
  inline block as reading or writing the variables a `jsr`'d routine uses, nor as writing
  the variables it stores to itself, and in both cases reordered or reused values across the
  block. A far-data model has to live in the compiler, not in inline assembler.

## Measured: the working set a turn (2026-11-15)

`tools/host-build.sh --trace` builds the host game with clang reporting every load and store
(`-fsanitize-coverage=trace-loads,trace-stores`) to `tools/measure/trace/nh_trace.c`, which puts
each access on the C64 page it would touch: a global by name at its C64 size (`layout.py`, from
the whole-game build's map), a string literal in the 37.7 KB of resident strings, a heap block in
a slab allocator at C64 sizes (monsters with monsters, objects with objects). Each kind of data
has page-aligned regions of its own, and every access also goes through simulated caches of 32
to 128 RAM pages (FIFO, CLOCK, LRU). `summary.py` prices a turn at the spike's costs: 21 cycles
for each far access (an upper bound: each is counted as a translation) and 600 for each fault.
Two games of `tools/profile_play.py --keys 6000 --seed 64` (the bot's moves are seeded; NetHack
seeds itself from the clock, so the two are different games):

| | Run A: all data far | Run B: 4 KB of globals near |
|---|---|---|
| turns | 13,367 | 10,903 |
| C64 pages touched a turn, median / p90 | 124 / 153 | 112 / 194 |
| pages touched over the last 10 turns, median | 162 | 150 |
| far accesses a turn, median / p90 | 10,050 / 15,530 | 10,723 / 33,838 |
| of them to globals, median | 3,166 | 57 |
| faults a turn, CLOCK with 64 pages, median / p90 | 160 / 243 | 123 / 781 |
| far-data cost a turn, CLOCK 64: median / p90 / mean | 314 / 477 / 327 ms | 306 / 1,194 / 499 ms |
| the same with CLOCK 128: median / mean | 237 / 250 ms | 236 / 374 ms |

Run B keeps near the 140 globals that an earlier run ranked best by accesses per C64 byte: 4,085
bytes, led by `u`, `youmonst`, `utrack`, `dungeon_topology` and `flags`, and 97.7% of run A's
accesses to globals. (The summaries and the list: `docs/data/fardata-trace-*-2026-11-15.txt`.)

- **A turn needs 28-31 KB of far data** (110-125 pages), 38-41 KB over ten turns: a 64-page cache
  holds most of a turn, 128 pages nearly all of it (11 to 19 faults a turn at the median).
- **Translations cost more than faults**: about 10,000 far accesses a turn at 21 cycles is 0.21 s,
  against 0.08 to 0.1 s of faults at 64 pages. The lever is the compiler reusing a translation for the
  next fields of the same object, which the spike measured at 1.7x instead of 3x.
- **Near globals help** as expected: they took a third of the far accesses in run A, and 4 KB
  of them leave 57 a turn. Run B went deeper, with more monsters and objects on the heap, so its
  total is no smaller.

## Measured: how fast NetHack runs on a C64 (2026-11-15)

In two steps: the host game's x86 instructions a turn, then the 6502 cycles that the C64 build
spends for each x86 instruction on the same code.

**Instructions a turn.** callgrind (valgrind 3.22) on the ordinary host build (gcc 13.3 `-O`, as
`tools/host-build.sh` compiles it) playing `tools/profile_play.py --keys 6000 --seed 64`: 13,896
turns, all of them on level 1, and 2.44 billion instructions, which `tools/measure/speed/
cgsummary.py` splits (`docs/data/speed-host-callgrind-2026-11-15.txt`):

| Where | x86 instructions a turn (mean) |
|---|---|
| NetHack's code (`src/`) | 122,962 |
| libc (mostly `printf` for the status line and messages) | 31,847 |
| ncurses' terminal library | 12,375 |
| the tty window port | 7,312 |
| in all | 175,786 |

| What (inclusive of what it calls) | a turn | calls a turn | a call |
|---|---|---|---|
| monsters (`movemon`) | 115,733 | 26.7 monster moves | 4,330 a move |
| the status line (`bot`), redrawn every turn because `time` is on | 36,623 | 1.8 | 20,541 |
| the hero's command (`rhack`) | 17,285 | 1.0 | 17,801 |
| messages (`pline`) | 8,052 | 0.7 | 11,418 |
| vision (`vision_recalc`) | 2,319 | 0.26 | 8,936 |

The bot hardly fights, so level 1 filled up with monsters: 26.7 monster moves a turn is more than
ordinary play.

**Cycles for each instruction.** `tools/measure/speed/calibrate.py` copies hot functions verbatim
out of `port/src` (`extract.py`: `isok`, `dist2`, `is_pool`, `is_lava`, `mfndpos` and the 17
functions `mfndpos` calls, each source file's functions in a file of their own as in the game),
and runs them on one level (five rooms, doors in every state, water, traps, objects, nine
monsters standing about): compiled by gcc as the host build compiles them and counted by
callgrind, and compiled by Oscar64 `-Os` as the C64 build compiles them and timed in Oscar64's
emulator (`-ep`, page crossings counted). Both print the same checksum. (`docs/data/speed-calibration-2026-11-15.json`; pin 73.)

| Workload (a call includes the harness's loop) | x86 instructions a call | 6502 cycles a call | cycles per instruction |
|---|---|---|---|
| `isok` | 16.9 | 133 | 7.9 |
| `is_pool` and `is_lava` | 45.0 | 464 | 10.3 |
| `mfndpos`, with what it calls | 1,942 | 18,543 | 9.6 |
| `dist2` | 15.5 | 509 | 32.7 |

**The estimate**, at 9.6 cycles an instruction (7.9 to 10.3 measured), and 32.7 for the 2,715
instructions a turn in `dist2`, at PAL's 0.985 MHz:

- NetHack's own code: 1.24 million cycles a turn, **1.26 s** (1.05 to 1.35 s).
- One monster's move: about 41,000 cycles, **42 ms**.
- The status line, redrawn every turn: about 0.36 s. Uncalibrated: on the C64 it is Oscar64's
  `printf` and our own window port, not glibc and ncurses, and neither is measured yet.
- In all about **1.8 s a turn** for this crowded game, and about 1 s for a turn with ten monster
  moves. With the screen on, the VIC-II takes about 5% of the cycles on top.

Banking adds little: about 80 bank crossings a turn at 142 cycles, some 10 ms
(BANKING-SPIKE.md). Far data adds 0.25 to 0.5 s a turn on average (the trace above, 64 to 128
pages): 15 to 30% on top of the game.

**Where the cycles go: two cheap wins.** Oscar64's runtime routines have entries of their own
in the emulator's profile:

- **`levl[x][y]`**: a column of the map is 21 rows of 6 bytes, and Oscar64 multiplies `x` by 126
  with its general `mul16by8` routine, about 250 cycles for each access: 35% of all the cycles
  in the `mfndpos` workload and 53% in `is_pool`/`is_lava`'s. A table of the 80 column offsets
  (160 bytes), or a shift-and-subtract for the constant in the compiler, would take a fifth to
  a third off monster movement.
- **`dist2()`**: two 16-bit multiplications, 80% of its cost; the game calls it 388 times a turn
  here, about 0.2 s. A table of squares (`|dx|` and `|dy|` are under 80) would make a call a few
  tens of cycles.

Both change speed only; the game computes the same values.

## The brainstorm and the direction (2026-11-15)

Four models worked from one brief, independently (docs/research/2026-11-15-brainstorm/: Fable
on the compiler and the code, GPT-6 Astra on hardware and prior art, GPT-6.1 Sol on 6502
techniques, Gemini for the widest list). Checked against the code, the docs or a rerun:

- **Map indexing without a multiply** (all four). A table of the 80 column pointers behind
  `levl` (160 bytes) makes the real `is_pool`/`is_lava` 2.0x and `mfndpos` 1.33x faster with
  the same checksums (Fable's run, reproduced). Oscar64 tables a constant multiply only when the
  index is a byte known to be under 16, and inlines only a few factors (3, 5, 7, 9, 25 after
  shifts; `ShortMultiply` in `NativeCodeGenerator.cpp`), so a compiler change would cover every
  stride at once (`level.objects` 42, `mons[]` 55, ...).
- **`dist2()` through a table of squares** (all four), about 0.15-0.2 s a turn.
- **Fewer translations rather than a bigger cache**: 8,000 fewer translations save about 170 ms
  a turn; 128 pages instead of 64 save 70-90 ms for 16 KB more.
- **Typed far spaces with 16-bit pointers** (Fable): each far type gets an address space of its
  own, under 64 KB, so a `struct permonst *` stays two bytes and the type says which translation
  table to use; structures and save files keep their layout. The hard cases are `char *` and
  `genericptr_t`.
- **The RNG is missing from the estimate above** (Fable): `Rand()` is `lrand48()`, not written
  for the C64 yet (T2.7); in C it costs about 4,900 cycles a call, 36 calls a turn, about 0.2 s;
  in assembler about 50 ms.
- Smaller: `isok()` inline (649 calls a turn), `monsndx()` divides by 55, `rn2()` with a
  constant argument at 1,100 of 1,366 sites, 128-byte map columns (two to a page, no cell
  across a page), an assembler fault handler (603 to about 350 cycles, 25-44 ms a turn), a
  status line that formats and draws only what changed. Undocumented opcodes save a cycle here
  and there (`LAX`, `DCP`), not on the translation path.
- **Hardware**: the Ultimate 64 runs its CPU at up to 48 MHz and the Elite-II and C64 Ultimate
  at up to 64 MHz, the cartridge port at 1 MHz (1541u-documentation, "Turbo mode settings"); the
  C128 offers shared RAM between its banks, the VDC's own 80-column memory and 2 MHz. The
  REU-aware EasyFlash sub-type is already in HARDWARE.md.
- **Corrections**: 103 banks of 16 KB are more than a 1 MB EasyFlash and a 512 KB REU, and REU
  memory does not execute, so 39 banks have to be copied in to run (ADR-0008); the static
  frames take 3.2 KB, not 11.5 KB (above); `time` is off by default, so the status line
  measured here is the worst case; the REU's compare command needs a read of `$DF00`.
- **Not taken**: keeping the heap and the level near (they hold 77% of the far accesses, but
  with about 21 KB left beside the code, the stack and the frames, they do not fit); an early
  return for sleeping monsters (`dochug()` has one, `monmove.c` 305 and 314).

Jolyon's direction: make the `#ifdef C64` changes now (the column table, the squares table,
`isok()` inline, a bit-exact `lrand48` in assembler), the compiler fixes after them; run the
far-data experiments comparing 3-byte pointers with typed 16-bit spaces; keep the C128 in view;
the Ultimate family runs the C64 build by emulation; a stock C64 stays a stretch, but one to
test (ADR-0003's amendment).

## Done: the `#ifdef C64` speed changes (2026-11-15, T2.10)

`levl` reads through a table of the 80 columns' addresses (`rm.h`, `decl.c`; `save.c` and
`restore.c` write and read `level.locations` whole), and so do the object and monster grids
through `OBJ_AT`, `MON_AT`, `m_at` and the other macros of `rm.h` and `display.h`, and
`sobj_at()` (21 pointers a column, a stride of 42; 480 bytes for the three tables); `dist2()` looks the squares of differences
under 128 up in a table (`hacklib.c`, the multiplication for the rest, so every input gives the
same answer); `isok()` is inline (`hack.h`, the function stays in `cmd.c`). The host build is
unchanged. All 108 files still compile for the C64, with 2,388 bytes more code in all (0.20%;
`docs/data/oscar64-pin73-c64conf-t210-2026-11-15.json`). `calibrate.py` again, same checksums
on both builds (`docs/data/speed-calibration-t210-2026-11-15.json`):

| Workload (6502 cycles a call, the harness's loop included) | Before | After |
|---|---|---|
| `isok` | 133 | 45 |
| `is_pool` and `is_lava` | 464 | 163 |
| `mfndpos`, with what it calls | 18,543 | 12,005 |
| `dist2` | 509 | 237 |

And the generator (T2.7): `src/hal/rng.c`, `lrand48()` in assembler, the multiply as 14 shifted
adds and subtracts, 1,178 cycles a call in 808 bytes, against about 4,900 for the same in C; at
36 calls a turn, about 44 ms. It gives glibc's numbers: `tools/check_rng.py` runs 20,000 a seed
for seven seeds in Oscar64's emulator, and `make test` checks four in VICE. (On the way, a
compiler bug: an `__asm` block that opens with a comment loses the first digit of its first
immediate operand, compat #69, r66.)

The multiply by a constant elsewhere: the whole-game listing calls `mul16by8` from 1,551
places with 35 different factors, four of them 87% of the calls: 26 (`objects[]`, 465), 126
(`levl`, 421, now the table), 55 (`mons[]`, 239) and 42 (the grids, 227, now the tables). A
routine of shifts and adds for each factor (in canonical signed digits) would take a multiply
from about 250 cycles to about 100, but all 35 would have to be resident, as `mul16by8` is,
some 1-2 KB of the scarcest RAM; the tables do better where it matters most (about 15
cycles). So T1.49 takes the compiler's side later, with the resident cost in view. A rough turn: with about
1,000-1,450 accesses to the level a turn saving some 230 cycles each, `dist2()` 105,000 cycles
and `isok()` 57,000, NetHack's own code comes to about 0.8-0.9 s a turn for the bot's crowded
level 1, from 1.26 s, and the generator adds about 44 ms rather than 0.2 s.

## Measured: far data on NetHack's own code (2026-11-16, T2.11)

`tools/measure/speed/farify.py` rewrites the speed harness's copies of the real functions as a
compiler with typed far spaces would: every access through a pointer to a far struct type goes
through that type's table of pages first (`p->f` becomes `XL_tag(p)->f`, `far_pre.h`; clang
finds the accesses from the types, macro bodies included). The pointers stay 16 bits, an
address in the type's own space, 16 KB from the real one, so an access left untranslated reads
the wrong bytes: with the translation switched off, the `mfndpos` checksum changes. Every page
mapped (a warm cache); the same checksums as the host build, no faults
(`calibrate.py --far`, `docs/data/speed-far-c72-2026-11-16.txt`; the harness as fixed for
compat #72, below):

| Far | Access sites translated | `mfndpos`, cycles a call |
|---|---|---|
| nothing | 0 | 12,025 |
| `mons[]` | 17 (13 in `mondata.h`'s macros) | 12,469 (+4%) |
| `mons[]`, monsters, objects, traps | 86 | 13,632 (+13%) |

- `mons[]` far costs little: its fields are read a few times a call.
- With the heap far as well, monster movement's hottest function is 13% slower on a warm cache,
  about 70 translations a call at some 22 cycles. Oscar64 reused none of them (volatile tables
  cost the same). By the pointers they translate (counted in the rewritten source, an estimate):
  `mon` and `mdat`, which do not change in `mfndpos`, have 14 sites of their own and 18 more in
  `mondata.h`'s macros; the trap the loop looks at has 15 sites in one block; `t_at()` translates
  each trap of its list three times, for `tx`, `ty` and `ntrap`. A compiler that translates a
  pointer once a function when it does not change, and once a loop step when it does, would
  bring the 70 down to perhaps 20-25, the 13% to about 4-5%.
- **Typed 16-bit spaces against 3-byte pointers**: a translation costs the same either way
  (the spike: 20.9 cycles in place). 3-byte pointers make every far pointer half as big again:
  the object and monster grids from 6.7 to 10 KB, `struct monst` (80 bytes, 4 pointers) and
  `struct obj` (48, 3) a few bytes each, three bytes to move and compare in every list walk,
  and every pointer operation in the compiler. Typed spaces keep every layout, the save files,
  `ptr == &mons[PM_X]` and `ptr - mons`, as long as each far type fits 64 KB (`mons[]` 21 KB,
  `objects[]` 11 KB, a level's monsters and objects a few KB). What they need instead: a rule
  for `char *` and `genericptr_t` that point at far data (translate when converting to them);
  allocation from the right space (`newmonst()`, `newobj()`); and near objects of a far type
  (`youmonst`, locals): map the pages of near RAM to themselves in every type's table, so that
  a near address is a far pointer too.
- Two more preprocessor gaps on the way (compat #70, #71: a macro that names itself; `##` on a
  nested macro's parameter). The counting build's wrong results at `-Os` were no optimiser
  bug (compat #72, r69): the harness's `main()`, with everything inlined, needed zero-page
  temporaries up to $AD, Oscar64 does not check that they fit its area ($53-$8F), and the
  emulator's jiffy clock at $A0-$A2 ticked a loop flag. The first numbers (`mfndpos` 12,005,
  12,444 and 13,600, `docs/data/speed-far-2026-11-16.txt`) were right all the same (the same
  cycles with the clock off), but the harness now keeps every temporary within $8F:
  `setup()` and `touch()` out of line, and a second call of `mfndpos()` that never runs, with
  flags known only at run time, so that it is the same function in every workload, as in the
  game (before, workloads 0-3 inlined it into `touch()`). `calibrate.py` checks every listing.
  The host's counts a call are unchanged; on the 6502 `isok` is 43.2 cycles a call (45.3), `dist2`
  237.8 (237.1), `is_pool` and `is_lava` 163.0 (162.9), `mfndpos` 12,025 (12,005).
- **Zero page is the limit to watch.** The whole game's highest temporary (listing of
  2026-11-16, after T2.10, 78 commits) is `m_move`'s $8B, four bytes short of $8F (it was $8D
  before T2.10); past it, the KERNAL's IRQ changes
  them on the real machine. With all four types far, `mfndpos()` itself needs $90 already,
  without any reuse: one byte too many (the emulator does not touch $90, so the 13% stands,
  but that code would not run on a C64 as it is). Translations reused across a function
  (ADR-0009, point 4) keep more pointers there. `tools/check_listing.py` checks a listing.

