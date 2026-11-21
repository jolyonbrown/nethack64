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
| `mons[]` | 21.1 KB (24.5 KB padded, since 2026-11-16) | constant table, read through `struct permonst *` everywhere (the `mondata.h` macros expand in every bank) |
| `objects[]` | 11.3 KB (13.9 KB padded, since 2026-11-16) | mostly constant; a few fields change in play |
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
  before T2.10); past it, the KERNAL's IRQ changes them on the real machine. With all four
  types far, `mfndpos()` needs $90 without reuse, one byte too many (the emulator does not
  touch $90, so the 13% stands, but that code would not run on a C64 as it is), and $88 with
  it (below). `tools/check_listing.py` checks a listing; the pin warns past $8F (2025).

## Measured: translation reuse (2026-11-16, T2.11)

`farify.py --reuse` rewrites the functions as a compiler that translates a pointer once a value
would: the bodies macro-expanded first (`--expand`, so that `mondata.h`'s accessors are spelled
in the function), then every far pointer variable defined once (a parameter, or a local set in
one place, like `mfndpos`'s `mon`, `mdat` and the trap of each position) gets a shadow holding
its translation, set at that definition, and its accesses go through the shadow. Pointers that
are not variables, and variables set in several places (a list walk's cursor), keep a
translation at every access; `--reuse-all` shadows those too. Same checksums as the host build,
no faults, all pages mapped (`calibrate.py --far-reuse`, `docs/data/speed-far-reuse-2026-11-16.txt`):

| `mfndpos`, cycles a call | Far | Highest temporary |
|---|---|---|
| near | 12,025 | $80 |
| `mons[]` far, no reuse / reuse | 12,469 (+3.7%) / 12,431 (+3.4%) | $87 / $85 |
| all four far, no reuse | 13,632 (+13.4%) | $90 |
| all four far, reuse (one definition) | 13,066 (+8.7%) | $88 |
| all four far, reuse everywhere | 13,352 (+11.0%) | $88 |

Where the far cost goes (all four types, cycles a call, `calibrate.py` prints it by function):

| Function | No reuse | Reuse | Reuse everywhere |
|---|---|---|---|
| `mfndpos` | +1,020 | +401 | +405 |
| `t_at` | +553 | +553 | +826 |
| `bad_rock` | +2 | +71 | +72 |
| `onscary`, `sobj_at` and the rest | +33 | +17 | +24 |

- **Reuse takes 60% of `mfndpos`'s own far cost away**: about 70 translations a call become 51
  (counted with `-dNH_FAR_COUNT`; 45 of them `t_at()`'s, and 28 in all with reuse everywhere),
  and with fewer intermediate results `mfndpos` needs less zero page ($88, back inside
  Oscar64's area).
- **A translation at each definition is not what a compiler would do everywhere.** `t_at()`
  walks the trap list, reading `tx` and `ntrap` of each trap (and `ty` when `tx` matches): two
  translations a step without reuse, one with it, but the shadow's null test and copies cost
  more than the translation saved (+826). `bad_rock()` translates its `mdat` at entry and
  reads it only when the square is rock (+71). Translating at the first access on each path,
  and reusing it where that access dominates, needs neither: estimated, `t_at` at one
  translation a step (about +280) and `bad_rock` as without reuse, all four far comes to
  about **+700 cycles, 6%** (ADR-0009 said 4-5%). The measured 8.7% is the bound.
- **One translation for all of an object's fields assumes the object is in one page.** It is
  for the heap's monsters (80 bytes, three to a page) and objects (48, five to a page) from a
  slab allocator, as the spike laid its list out; not for the tables: `mons[]` has 55-byte
  entries and `objects[]` 26-byte ones, which cross pages. The experiment maps every page
  contiguously, so it cannot show this. A table that goes far needs entries that keep to a
  page: `struct permonst` padded to 64 bytes (24.4 KB instead of 21.0 KB of REU, four to a
  page; `ptr - mons` then a shift, where `monsndx()` divides by 55 today), `objects[]` to 32
  (13.9 instead of 11.3 KB), or a translation of the field's own address at each access.
  Done in the C64 build (2026-11-16, Jolyon: "go ahead with the padding"): `permonst.h` and
  `objclass.h` pad the structs under `#ifdef C64`, and a `static_assert` checks the sizes
  (Oscar64 accepts a negative array size, compat #75). Every named field of both tables
  hashes the same as before in Oscar64's emulator, and `p - &mons[0]` is each entry's index.
  Near, today, the padding is a speed change too: a `mons[]` index costs about 30 cycles
  instead of 230, an `objects[]` index 39 instead of 185, and `ptr - mons` 66 instead of 300
  (a 300-call loop in the emulator, -Os). In the per-file measurement, the files' own
  functions lost 320 calls of `mul16by8` (201 by 26, 119 by 55) and 88 bytes of code in all
  (106 files, 1,187,649 -> 1,187,561 bytes); the tables grow by 6,051 bytes (383 and 434
  entries), and a save by 2,604 (`savenames()` writes `objects[]` whole).
- **The cache for the first far set** (`mons[]`, `objects[]` and the heap: run C, with
  `nh_trace.c`'s `NH_TRACE_FAR` counting everything else as near,
  `docs/data/fardata-trace-runC-far3-2026-11-16.txt`; the bot stayed on level 1): a turn
  touches 36 pages at the median (49 at p90, 63 at most; 38 over ten turns), and CLOCK with 64
  pages takes no fault a turn at the median or at p90 (4 at most); with 32 pages, 21 and 77.
  What is left is the translations: 5,655 far accesses a turn at the median, at most 121 ms at
  21 cycles each (228 ms at p90) before any reuse, where all data far cost 314 ms (run A). A
  deeper game keeps more monsters and objects on the heap (run B), so 64 pages is where to
  start, not a bound.

## Built: far spaces in the compiler (2026-11-17, T2.12, first version)

The fork's `feature/far-spaces` (`tools/oscar64-upstream/patches/far-spaces/`, on the pin of 80
commits; not in the pin yet):

- `#pragma farspace(n, tag, ...)` puts struct types in far space n (1-8): a pointer to one is a
  16-bit address in the space. `#pragma farsection(section, n)` puts a section's objects there.
  The source stays C for gcc (the pragmas go under `#ifdef __OSCAR64C__`).
- The front end tags every load, store, struct copy and built-in `memcpy`/`memset`/`strcpy`
  with the space of the memory it reaches: a dereference of a pointer to a far type, a member
  or element of far data, an object in a far section. A pointer value keeps the space it points
  into, so `EPRI(mon)`, `(struct epri *) &mon->mextra[0]`, stays in the monsters' space.
- A late pass, after every pass that moves instructions, puts `t = FARXLAT(address)` right
  before each far access, so nothing that could fault and evict a page comes between the
  translation and its use, except in a copy between two far objects, whose two translations
  follow each other; the fault handler keeps the page translated last. Known near objects (a
  global elsewhere, a local) are not translated even when their type is far; a near object
  reached through a pointer is, through the identity entries of the space's table.
- Native code calls the program's `farxlN` (page in X, RAM page back in A, Y kept) or `farxoN`
  (address in A and X plus an offset under 256 in Y, the RAM address back in A and X): the
  exact address is translated, since a pointer to one object may carry the offset of the next.
- Warning 2026 where a far pointer leaves its space (converted to `void *`, `char *` or
  another type, the address of a far member taken as a near pointer) and where a built-in copy
  or fill of far data may span pages: the places to look at by hand. Far data in byte code is
  an error.

Checked: `autotest/farspacetest.c` (the far section linked at $8000, its pages mapped to a copy
at $9000 and $8000 filled with garbage, so a missed translation fails; -O0 to -O3; without the
type pragma the pointer checks fail), the fork's autotest 1,626/1,626, the corpus byte-identical
to the pin's (1,084 of 1,085; the other is compat #67, which `MALLOC_PERTURB_` shows);
`tests/spikes/run_farspace.py` in VICE with a 1 MB REU (512 far nodes over 64 pages through a
16-page cache: a list built, walked, changed and copied far to far under eviction, 1,393 faults
and 1,377 write-backs, 9 of 9 checks); and NetHack's own code in the speed harness
(`calibrate.py --far-cc`, `docs/data/speed-farcc-2026-11-17.txt`): the same checksums as the
host, no faults, zero page up to $82.

| Far (compiler, every access translated) | `mfndpos`, cycles a call |
|---|---|
| nothing | 11,250.7 |
| `mons[]` | 11,620.8 (+3%) |
| `mons[]`, monsters, objects, traps | 14,900.3 (+32%) |

**Groups** (2026-11-17, the fork's third commit): accesses in a block through one pointer to a
far struct object, inside the object, share one translation of the pointer's page, which
pins it in one of four slots (`farpins`) that the fault handler does not evict; a call or a
new value of the pointer ends the group. In VICE (`run_farspace.py`, 10 checks): three
objects' fields interleaved under eviction pass with the pins and run away without them; the
list walk costs 31 cycles a node more than near (102 translating every access). The
harness: `mfndpos` +2.6% with `mons[]` far, +30% with all four types (+3% and +32% before):
blocks are short (each `&&` and `||` of `mondata.h`'s macros starts one), so groups across
blocks come next (`t_at()`'s loop still translates three times a step).

**Groups across blocks** (the fork's fourth commit): a group still open at the end of a block
goes on into a later block that uses it, which takes it over when every block leading into it
passes on the same translation in the same slot (all of them before it, so not over a loop's
way back): every path from the translation keeps the slot, with no call and no new value of
the pointer. `t_at()` now translates once a step. VICE 10/10; the harness: `mfndpos` +2.3%
with `mons[]` far (11,504.5), +17% with all four types (13,203.1).
`farify.py`'s reuse model reached 8.7%; what is left is mostly translations again after calls
(a callee takes the slots too), which per-function pin slots would remove. Code: all of
port/src with the `mons[]` types far is still 49 KB bigger (+4.2%): most uses of the macros
are single accesses between calls, so the size is the translation calls themselves.

The whole of port/src with `struct permonst` and `struct attack_s` far (`-dNH_FAR_SPACES`,
`permonst.h`; `measure_oscar64.py` with `MEASURE_DEFS`/`MEASURE_EXTRA`,
`docs/data/measure-c64-farmons-2026-11-17.txt`): no warning 2026 in the game's own files, so no
`mons[]` pointer leaves its space; 52 KB more code (+4.4%, 1,187,381 to 1,239,676 bytes), every
`mondata.h` macro translating on its own. Reuse would cut both the code and the cycles, so it
comes before the inline hit path, which would add code.

**`objects[]` and the squares too** (2026-11-17, `docs/data/measure-c64-far3-2026-11-17.txt`):
`struct objclass` in space 2 and `struct rm_s` in space 3 as well (`objclass.h`, `rm.h`, under
`NH_FAR_SPACES`). Of the 273 warnings 2026, 270 are in the generated stubs and 3 in the game:
`save.c` 494 and 504 hand a square of `levl` to `bwrite` as `void *` (real: those need a copy
through a near buffer), and `restore.c` 742 reads into a local `struct rm_s` (near, harmless).
Code 1,248,332 bytes (+5.1% over near, 8.7 KB more than `mons[]` alone); this undercounts,
since `objects[]` and `level` stay near in the measurement and a known near object is not
translated: in the build `levl[x][y]` and `objects[i]` will be.

**`mons[]`, `objects[]` and `level` in far sections** (2026-11-17,
`docs/data/measure-c64-far6-2026-11-17.txt`): not only the types but the objects themselves,
each at `$8000-$FFFF` of its space, in a region of bank 106, 110 or 114: bank 64 + 4n + 2 puts
the space's address A at REU n × 64 KB + A (`crt_split.py`, which now takes a far bank's `$C000`
and `$E000` halves and refuses overlaps). The externs in `permonst.h`, `objclass.h` and `rm.h`
sit under `#pragma data/bss` of the section, so a file compiled alone still knows the object is
far; the definitions in `monst.c`, `objects.c` and `decl.c` sit in the same section. No near
object of the three types is reached through a pointer (`mklev.c`'s `zerorm` and `restore.c`'s
local are used by name), so every page outside `$8000-$FFFF` can be an identity page.

- `struct rm_s` is 8 bytes in this build (6 before): with 6, a square could cross a page, and
  the compiler translates a whole access or group once (ADR-0009 point 5; found by Codex's
  review). 3.4 KB more in the REU, none near.
- `NH_OBJS`/`NH_MONS` index `level.objects`/`level.monsters` directly: the column tables hold
  `struct obj_s **` and `struct monst_s **`, near pointers that would reach the far grids
  untranslated. (A far-typed column struct would give the speed back; later.)
- The 15 sites warning 2026 found in the game are rewritten under `NH_FAR_LEVEL`/`NH_FAR_OBJS`,
  each the same behaviour: list heads (`fobj`, `fmon`, a square's objects, the buried list) go
  through a near copy of the head in `replace_object`, `remove_object`, `obj_extract_self` and
  `dmonsfree`; block moves go through `nh_farfill3`, `nh_farbwrite2/3` and `nh_farmread2/3`
  (`decl.c`, a byte at a time through a 64-byte buffer; a short read leaves the rest as it was,
  as a direct one does); `docall` uses `objects[otyp].oc_uname` instead of a `char **` into it.
  The far level needs `RLECOMP` (an `#error` says so): the other save path passes the squares
  as one near pointer. Left: `restore.c` 742, a read into a near local, harmless.
- Code 1,263,772 bytes, +6.4% over near; 36 files now fit on their own in the measurement
  (none before), with 55 KB of data out of near RAM. The host build: Codex compared gcc's
  assembly before and after for the ten changed files, identical; `host_smoke.py` passes.

**The whole game with them** (2026-11-18, `docs/data/wholegame-far-2026-11-18.txt`, one compile
on the desktop, same plan as the near build of 2026-11-17): the three sections place
(58.6 KB), and the resident data left unplaced falls from 128.6 KB to 73.2 KB. The bank
checks pass (no listing call crosses a bank, highest temporary $8E). But the banked code and
its literals grow 5.0% (79.8 KB), so 33 banks overflow by 36 KB in all, and two functions
outgrow a bank: `dokick` (17,005 B with its inlined helpers, which `planfix.py --oversized`
handles) and `seffects` (16,473 B, nothing inlined to take out). So the far accesses have to
get denser in the compiler before the plan can be repaired: `planfix.py` now takes new
banks (`--add-banks`; 104-105, 108-109, 112-113 and 116-117 are free in the REU) and moves by
best fit. What is still near is the vision and level tables (`gbuf`, `rooms`, `could_see`,
`viz_clear`, `Map`, 15 KB), 15.5 KB of anonymous literals, `roles`, `u`, `artilist`,
`mvitals`.

**Denser far accesses** (2026-11-18, fork commit 5, dac0840;
`docs/data/measure-c64-far7-2026-11-18.txt`). Two changes to the call sequence. An access in a
group that got no pin slot now translates its page (`farxlN`) and not its address (`farxoN`,
13 bytes and `LDY #0`). And when the program defines `farxzN`, a page translation is
`LDX #reg; JSR farxzN`: the runtime reads the pointer from zero page at X and leaves its RAM
address in `ADDR`, through which the access goes, 5 bytes. The optimizer has to be told the call
reads only 2 bytes of zero page (a new flag, `NCIF_ZP_16`): with the 4 its flag for X implies, it
saved more temporaries, and twelve heavy files grew (+10.5% over near, against +9.8% before);
with it, +8.0%. All of `port/src`: +5.4% over near (was +6.4%), so 17% of the far code is gone.
The whole game: banked code and literals 1,650,361 B, +4.3% over near (was +5.0%), and
`seffects` 16,374 B fits a bank with 10 bytes to spare (so `planfix.py` can repair the plan
only with its slack per bank cut from 256 bytes to 8). The spike's `farxz1` puts its hit path inline: a walk of 8 far nodes costs
36.9 cycles a node against 31 with `farxl1` (two more stores to `ADDR`). What is left is about
5 bytes a translation; the next lever is fewer of them (reuse across calls).

With that, the plan repairs (`docs/data/bankplan-2026-11-18-far.json`, two rounds of
`planfix.py` and three links on the desktop, `docs/data/wholegame-far-2026-11-18.txt`): 58 of
1,940 functions change bank, banks 104 and 105 (REU) are new, and `dokick`'s two helpers stay
out of line. Every banked object places: 105 banks, 1,636,008 B, no call across a bank without
a trampoline. `planfix.py` now keeps its slack in each bank except where the bank's biggest
function leaves less (`seffects`' bank keeps 10 bytes). What does not fit is resident: 47.7 KB
of code and 73.2 KB of data, against 46.7 KB and 128.6 KB near.

`farify.py`'s rewrite (T2.11) cost +13% for all four: about 70 translations of some 22 cycles,
inline. The compiler translates every access, `youmonst` and the `mondata.h` macros included,
through a `jsr` (about 34 cycles for a page, 50 with an offset). Next: the hit path inline (a
`jsr` only on a miss), then reuse with pinning (ADR-0009 point 4), which took `farify.py`'s
13.4% to 8.7%.

**The resident side, first the glue** (2026-11-19, `docs/data/wholegame-far-2026-11-19b.txt`).
What the far game still wants resident, from far12's map: 65.1 KB of code and 95 KB of data
(73.3 KB of it unplaced, 37.7 KB literals), against the 21-28 KB the RAM in view leaves beside
the far page cache (16 KB) and the stack. Of the code, 44 KB was glue between banks: 2,076
resident bank call stubs (12.5 KB), 264 resident string trampolines (24.5 KB) and 1,025 proxies
(8.9 KB, constant-argument entries, 608 of them of resident functions such as `rn2`).
- A call from code in a bank now goes through a stub in that bank (fork commit 6, c0c33b1):
  resident stubs only for resident callers and addresses; `nh_bankcall` reads the whole stub
  before it maps the callee's bank. Resident code 65.1 -> 55.3 KB; 5,883 stubs in banks (35 KB).
- With the linker switching banks, a string trampoline only has to copy strings while the right
  bank is mapped, so bankgen.py splits it: `f__tA` in each calling bank copies the arguments onto
  a stack it releases when the call returns (a result inside what it releases moves to
  `nh_stash`'s four buffers), `f__xN` in f's bank copies a string result; the resident `f` stays
  for resident callers and pointers. 14 of 264 trampolines are needed resident (1.1 KB).
  Resident code 29.6 KB (far16). `vpline` and `vraw_printf` stay resident: they format `%s`
  arguments, which may be literals of the caller's bank.
- The cost is banked: 7,815 stubs (47 KB), 1,127 caller wrappers (60 KB), 117 result wrappers
  (11 KB), and a repaired plan (351 moves, banks 108-121) still 63 KB over, because planfix.py
  sized moves without the stubs and wrappers they bring. Code and data in banks now come to
  1.79 MB: about 110 of the 121 banks a 1 MB EasyFlash and a 1 MB REU leave beside the far
  data, before the far heap spaces (the REU minimum is now 2 MB, ADR-0008).
- 2026-11-20: the wrappers' window tests became calls (caller wrappers 104 -> 68 B each), and
  planfix.py --glue counts the stubs and wrappers a move brings. Three links later every banked
  object places (far19: 116 banks, 1.75 MB); `seffects`' bank keeps resident glue (fork commit
  7, section flag 4), since its code, literals and stubs alone exceed 16 KB. Resident code is
  31.4 KB, resident data 72.1 KB: the data is next.

**The resident side, the data** (2026-11-20, `docs/data/wholegame-far-2026-11-20.txt`). Counted
with each static frame once (they overlay: 3.3 KB), far19 kept 99.6 KB of data resident: 37.5
KB of literals, 58.8 KB of named objects. Three changes so far:
- *Read-only tables into their bank* (far20): a file-scope table no code writes and only one
  bank's code reads goes into that bank with its literals (bankgen.py `bank_data`, from
  `tools/bank/tables.py`), crossing banks as the bank's own literals do. 104 of 202 tables;
  the rest are read from several banks, are named by another table, or are not const with
  their address taken (`u_init.c`'s `ini_inv()` writes through one). -11.3 KB.
- *The names far* (far21): `mons[]`'s and `obj_descr[]`'s names (12.2 KB) in sections at
  `$E000-$FFFF` of far spaces 1 and 2, read through `NH_MNAME()`/`NH_ONAME()` into a ring of
  eight near buffers (ADR-0009, amended); the object names fill 8,187 of the 8,192 bytes.
  The fork's commit 8 puts the proxies of resident functions in the calling banks: resident
  code 31.4 -> 25.4 KB, the banks 13.7 KB fuller. -11.9 KB of data.
- *Far space 4* (far22-23): `rooms` (64-byte entries), `gbuf` and `mvitals` (padded to 4) in
  far space 4 (`c64conf.h`, bank 130: REU 64 KB bank 16, past the code), `obj_descr` with
  `objects[]` in space 2. Two places moved rooms through near pointers and are rewritten:
  `sort_rooms()` (an insertion sort by `lx` for `qsort()`) and `remove_room()` (a struct
  copy for `memcpy()`). -11.3 KB in far22 (`mvitals` was left in near bss; far23 fixes it).

What is left, far22 (65.1 KB of data, 25.9 KB of code): 17.0 KB of literals (`options.c` 4.2,
`shknam.c` 2.8, `role.c` 2.5 KB, tables read from several banks, and resident code's own);
10.1 KB of vision grids (`could_see`, `viz_clear`, `left_ptrs`, `right_ptrs`, `Map`), reached as
`char *` rows; 6.4 KB of scalar tables (`objnam.c`'s `bufs` 3 KB, `disco`, `monstr`); 6.3 KB of
struct tables (`artilist`, which holds `struct attack_s` of space 1, `dungeons`, whose names are
`char` arrays, `level_info`); 4.6 KB and more of `char` buffers; 3.5 KB of read-only struct
tables (`roles`, `races`, `defsyms`, `shtypes`); 2.4 KB of the bank glue's buffers; `u`, `flags`
2.3 KB; 3.3 KB of frames. Against a budget of about 21 KB for code and data (34 KB in view,
less a 8-16 KB page cache, the stack and a near heap), the far sections that are still
straightforward leave roughly 50 KB: the rest needs a smaller page cache, which costs faults,
or strings and `char` data in far memory, which `char *` makes hard.

**How small the page cache can be** (2026-11-20, `docs/data/fardata-trace-cache-2026-11-20.txt`;
`nh_trace.c`'s `NH_TRACE_CACHES`; a 6,000-key bot game on level 1, the far set of far23 and the
heap; 600 cycles a fault, 21 a translation):

| Cache (CLOCK) | Faults a turn, median / p90 | Far cost a turn, median / p90 |
|---|---|---|
| 64 pages, 16 KB | 1 / 19 | 69 / 151 ms |
| 32 pages, 8 KB | 50 / 79 | 100 / 183 ms |
| 16 pages, 4 KB | 89 / 144 | 125 / 220 ms |
| 8 pages, 2 KB | 187 / 303 | 185 / 315 ms |

With the vision grids far too, 16 pages cost 152 / 273 ms. A fault is cheap next to a
human's turn, so the cache is the budget's best lever: 4 KB instead of 16 gives the resident
side 12 KB for about 55 ms a turn (less with a fault handler in assembler, about 350 cycles).

**Later the same day** (`docs/data/wholegame-far-2026-11-20.txt`, far24-27): the vision grids
far (rows of `struct vrow_s`), nine more tables far by name, the shopkeeper names in their
bank, role and race strings far (`NH_RNAME()`), and name lookups off the ring: resident data
about 47 KB, resident code 26 KB. A far default for the rest (`#pragma fardefault`, the
fork's commit 9, `docs/data/fardefault-trial-2026-11-20.txt`) would move only about 4.6 KB:
of the 27 KB of named objects left, 15.8 KB are `char` arrays or have their address handed
on as a near pointer, and 3 KB are touched every turn. The bulk left is strings and `char`
data, read through `char *`: far strings in the compiler come next (Jolyon agreed), and the
far default after them.

**The ledger and the levers** (2026-11-21, `docs/data/wholegame-far-2026-11-21.txt`). Far
strings as ADR-0010 proposed them cap at about 16 KB (its review), so the resident side was
counted whole: far27 keeps 68.7 KB (42.6 KB data, 26.1 KB code) against about 25 KB, with the
platform code still to come. Jolyon chose the order: code trims (1), the 8 KB under the
window (2), a slice of code in every bank (3).
- *Lever 1, the trims* (far29, plan far27 warmed plus 13 placements): NetHack's six scanf
  calls go to `port/sys/c64/c64scanf.c` (integers, characters, strings and scan sets;
  `tests/scanf/`, against glibc on the host and under Oscar64), whose worker is banked
  (a plan's `va_list_banked`: its `va_list` holds only pointers to near variables), instead
  of Oscar64's `fpscanf` and the float routines it brings (3.2 KB); the far I/O helpers,
  `clear_cs_rows()`, `clear_glyph_buffer()` and `hack_artifacts()` in banks (bankgen.py had
  not seen what `NH_FAR_SPACES` selects: `build_c64.py --far` now gives it the define);
  `panic()` formats its message and leaves the rest to a banked `panic_tail()`. Resident
  code 26,097 -> 22,271 B; resident in all 68,652 -> 64,755 B. Bank checks clean; 234 B of
  banked code left for the next plan repair. far30 adds `-dNOFLOAT` (Oscar64's printf
  without `%f`, which NetHack never formats): resident code 20,286 B, in all 62,602 B.
- *Lever 2, RAM under ROML*: the hardware does it (`docs/HARDWARE.md`, `tests/spikes/loram.c`):
  with `$01 = $36` in 16K mode, `$8000-$9FFF` is RAM while ROMH stays at `$A000`. But a
  window of 8 KB at `$A000` for every bank would leave 16 functions without a bank (they are
  larger: `seffects` 14.2 KB, `readobjnam` 12.9, `hmon_hitmon` 12.8, `hitmu`, `dokick`,
  `mdamagem`, `domove`, `moveloop`, `m_move`, `enlightenment`, `parseoptions`, `dochug`,
  `load_maze`, `dotrap`, `use_defensive`, `mintrap`), and keeping 16 KB banks makes the RAM
  there hidden whenever an EasyFlash bank runs and overwritten whenever an REU bank does.
  Code there may then take no string that can be a literal of its caller's bank (the
  caller's ROML is hidden while it runs), so neither libc nor the message functions nor the
  glue qualify: what is left is the hot set (7.9 KB), called about 1,500 times a key from
  EasyFlash code through a stub, about 0.2 s a key. Not taken for now.
- *Lever 3, a slice in every bank*: Oscar64 already has what it takes. A region may name
  several banks (`#pragma region(r, start, end, , { 1, 2, 64 }, { s })`): the linker writes
  its objects, relocated, into each bank's image, and `Linker::SectionBank()` takes such a
  section for resident code, so a call into it from any bank is a direct `JSR`, a call out of
  it goes through a resident stub, and the stub maps whichever bank was in. `bankgen.py`
  takes a plan's `"slice": {"start", "functions", "tables"}`. `tests/spikes/bankslice.c`
  (VICE, EasyFlash + REU): 8 checks pass, EasyFlash and REU callers, a call from the slice
  into a bank and back to an EasyFlash or an REU caller, a slice table and literal read
  from both, the same bytes in every bank. Bank 0 (the startup and the program's image) can
  hold no slice, so the startup must map a code bank before slice code runs. Found on the
  way: the cartridge's startup leaves `$01 = $36`, so ROML is hidden until the first call
  into an REU bank comes back; the bank call routine now sets `$37` whenever it maps an
  EasyFlash bank (+10 cycles a call, `run_bankreu.py`). What stops the slice is the banks
  it would shrink: in far29, 106 of 116 banks hold more than 14 KB, and `seffects`' bank
  (16,369 B with its literals) and `readobjnam`'s (16,310 B) cannot give up even 1 KB. A
  bank left out of the slice would need its calls into the slice sent through stubs that
  map a bank holding it, and resident code could then no longer call the slice directly
  (a bank without it may be mapped: `seffects` -> `pline` -> slice), and a string or format
  passed from such a bank would not be in view: the slice would be numeric code reached
  through stubs, lever 2 again. It works without that only if the largest functions are
  split in the source (`seffects`, `readobjnam`, then those over 12 KB with their literals
  for a 4 KB slice), at about 150 KB of bank space for each KB of slice.

## Measured: zero page saves (2026-11-16, T1.49)

After the padding (ADR-0009 point 5), what is left of Oscar64's multiply routine is small: 0.2%
of the `mfndpos` workload. The emulator's profile by address (`-ep` lists the busiest
instructions besides the functions) points elsewhere: the busiest code in that workload is a
loop at `mfndpos`'s entry that copies 46 bytes of zero page into its frame, and the same loop
the other way at its exit, 1,244 cycles a call, 10% of its time. Oscar64 keeps a function's
temporaries in zero page, $43-$52 for its caller to keep, $53-$8F for the function itself:
whatever of those it uses it copies away on entry and back on return, about 33 cycles a byte
through the software stack (27 with a static frame). Over the whole game, by its listing and
the bot game's call counts (`build/profile-arcs.json`, 9,273 turns), that is about 277,000
cycles a turn: `m_move` (57 bytes, 29 calls a turn) 55,000, `mfndpos` (48, 29) 46,000,
`newsym` (22, 46) 33,000, `dochug` (32, 29) 31,000.

A function only has to keep the bytes a caller still needs after the call. The pin's commit 79
(`-Ot`, part of `-Os`) works that out once the whole program is compiled, from the bytes each
caller reads after each call, and from what the caller's own callers need of bytes the caller
leaves alone; a function then saves only those (in up to three runs). A function whose address
is taken is a callee of every call through a pointer. `main` would keep all of BASIC's zero page
for the startup code, which returns to BASIC; our programs never do, and say so (`-xb`).

Results (`docs/data/oscar64-pin80-tempsaves-2026-11-16.txt`,
`docs/data/speed-calibration-t149-2026-11-16.txt`):

- the speed harness: `mfndpos` 12,072.5 -> 11,250.7 cycles a call (-6.8%; it saves 16 bytes,
  the ones `main` keeps over the call, instead of 46), the host's checksums;
- the whole game: 686 of the 1,375 functions that save are narrowed, 7,161 of 10,104 bytes
  kept; by the call counts, saves and restores take 242,709 cycles a turn instead of 276,936
  (-12%, about 35 ms a turn); one range a function would leave 252,906, the needed bytes alone
  237,162. Banked code 3,710 bytes smaller, resident code 9 bytes bigger, every bank and
  zero-page check clean; the listing against the same sources with `-Ot-` differs only in
  saves and restores, addresses, and where the assembler now copies a shorter epilogue;
- what stays: much of it is real (`m_move` keeps 33 bytes over its call of `mfndpos`, so
  `mfndpos` keeps 37 of 48), but most of the rest comes from functions whose address is taken
  (the command handlers, callbacks): they keep everything, and what they keep their callees
  owe them, so `m_move` keeps 55 of 57 bytes for callers (`attack`, `u_entered_shop`) reached
  from commands, where `dochug` itself needs 8. One node for all calls through a pointer does
  not help (it gathers everything; tried and dropped); grouping those calls by the function's
  type might, with care for casts of function pointers. Next for T1.49.
- Tried the same day (Jolyon: "carry on with the pointer-call grouping"): calls through
  pointers grouped by the called type (result and parameter sizes; the call's type is kept on
  the intermediate code), the casts not yet followed, so only to measure. No change at all:
  17 types, and every one ends up needing the whole area, as do the busiest functions. Nothing
  escapes and nothing is opaque; the cause is the unions: the pass is context-insensitive, so a
  function or a type reached from many call sites (dozens to 178 here) needs what any of them
  keeps, and over that many the union is everything. Getting more would take saves that
  depend on the call site (a caller saving around its own call) or a context-sensitive
  analysis, both far bigger changes. Dropped; the experiment is on the compiler clone's branch
  `scratch` (not in the pin).
