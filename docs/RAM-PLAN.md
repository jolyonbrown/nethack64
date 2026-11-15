# RAM plan (T2.3): the data does not fit a 64 KB address space

Status 2026-11-15: measured, not decided. The question for Jolyon is at the end.

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
| static frames of non-recursive functions | 11.5 KB | many 256-byte `BUFSZ` buffers |
| heap: monsters and objects of the level, inventory | about 5-15 KB | estimate (ARCHITECTURE.md), not measured yet |
| software stack | about 4-6 KB | estimate |
| resident code | 65.1 KB | could come down to perhaps 15-20 KB (string trampolines, stubs, libc) |

Even leaving out every constant table and string, the mutable data alone (level, grids,
globals, heap, frames, stack) comes to roughly 70-85 KB, while the RAM left beside a minimal
resident code comes to about 25-40 KB. With the constants it is about 165-175 KB (the
measured 155 KB plus the heap and the stack).
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

Not yet known: how fast NetHack itself runs on a C64 before any of this. That is the
baseline everything is a multiple of.
