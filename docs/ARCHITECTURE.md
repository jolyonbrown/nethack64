# Architecture

Status: **draft, driven by Phase 0 measurements.** The decisions that are
settled have ADRs in `docs/decisions/`; the open ones are marked OPEN and are
Phase 2 spikes.

## Strategy: port the source, don't rewrite the game (ADR-0001)

NetHack's behaviour *is* its 130K lines of C. Re-implementing systems from a
feature list would take longer and never be NetHack. So the game code is the
original `src/`, mechanically converted (ANSI, Oscar64 workarounds) and then
fitted to the machine. Our own code is the platform layer underneath:

```
+---------------------------------------------------------------+
|  NetHack 3.4.3 game code (port/src)        ~0.85 MB 6502 code |
+------------------+--------------------+-----------------------+
| window port      | file/dlb layer     | system layer          |
| (80x25 soft text,| (level files, save,| (RNG, time, getenv,   |
|  menus, status)  |  data files)       |  panic, exit)         |
+------------------+--------------------+-----------------------+
| src/hal: screen80 | keyboard | REU DMA | EasyFlash banking | KERNAL I/O |
+---------------------------------------------------------------+
```

## The budget (from docs/NETHACK-SURVEY.md)

Static content, uncompressed:

| Item | Size | Where it can live |
|---|---|---|
| Game code (Oscar64 -Os, estimate) | ~0.85 MB (0.7-1.0) | EF banks (execute in place) or REU (DMA into RAM) |
| String literals | ~165 KB | with the code that uses them (same bank) |
| `mons[]` + `objects[]` + names | ~45 KB | ROM/REU; the writable bits of `objects[]` (~2 KB) in RAM |
| 113 special levels | 213 KB | compressed in EF/REU, decompressed on level creation |
| Encyclopedia, quest text, rumors, help | 415 KB | compressed (text ~50%), REU or disk |
| **Total** | **~1.7 MB** | EasyFlash holds 1 MB |

Dynamic state while playing (Oscar64 layout):

| Item | Size |
|---|---|
| current level `dlevel_t` | 16.8 KB |
| other globals (`u`, flags, vision arrays, display buffers, ...) | ~15-20 KB |
| heap: objects (48 B + names) and monsters (80 B + extras) on the level + inventory | ~5-15 KB typical |
| software stack (BUFSZ locals!) | 4-6 KB |
| screen: shadow text + flags (bitmap/colour sit in VIC bank 3, not counted) | 2.3 KB |
| **Total** | **~45-60 KB** |

The C64 has 64 KB, of which an EasyFlash program sees `$0900-$7FFF` (30 KB)
as ordinary RAM while the cartridge window is mapped. **RAM, not ROM, is the
tighter constraint.** Every memory decision below follows from these two
tables.

## Memory map — EasyFlash + REU (current Phase 0 layout)

```
$0000-$00FF  zero page: $02-$8F Oscar64, $90-$FF KERNAL
$0100-$01FF  6502 stack
$0200-$03FF  KERNAL work area (keyboard buffer etc.)
$0400-$07FF  (text screen, unused in bitmap mode -> candidate for data)
$0900-$7FFF  resident: common code, globals, heap, Oscar64 stack   (30 KB)
$8000-$BFFF  EasyFlash bank window (code + rodata of the active bank)
$C000-$CBFF  free RAM (3 KB)
$CC00-$CFE7  80-col colour matrix
$D000-$DFFF  I/O  ($DE00 EF bank reg, $DF00 REU regs - never read)
$E000-$FF3F  80-col bitmap (RAM under KERNAL ROM)
```

## Code: banking (OPEN — Phase 2 spike)

Three ways to run ~0.85 MB of code through a 64 KB address space:

**Option A — EasyFlash execute-in-place.** Each 16 KB bank holds a group of
functions + their strings. A call into another bank goes through a trampoline
in resident RAM (save bank, switch `$DE00`, call, restore). Oscar64 supports
bank regions; trampolines are ours (or its C++ `EF_CALL`). Zero copy cost;
but code must be partitioned so hot paths stay in one bank, and ~55 banks of
code use most of the cartridge, leaving little for data.

**Option B — REU overlays.** All code (and data) lives in a >= 2 MB REU,
loaded once at boot (from disk or a cartridge). A call into a non-resident
group DMAs it into a RAM overlay window (16 KB in ~16 ms). With no cartridge
mapped, `$8000-$BFFF` becomes RAM: 16 KB more for state *or* the overlay
window. One mechanism for code and data; needs a big REU (fine for VICE,
Ultimate, C64U; not for a stock 1750).

**Option C — hybrid (current primary target).** Code executes in place from
EasyFlash banks (A); compressed text/levels and level files live in the REU.
Matches "EF + REU" but inherits the `$DF00` caveats (docs/HARDWARE.md) and
the 30 KB RAM ceiling while a bank is mapped (data can be copied in and out
of the RAM under the window by briefly switching the cartridge off from
resident code).

Inputs to the decision, all already in the tree:
- the `OVL0..OVL3/OVLB` split of 52 files and the Borland overlay schemas
  (`upstream/.../sys/msdos/schema*.BC`) — a call-frequency partition made by
  people who had this problem in 1999;
- `trampoli.h` — the 169 functions reached through pointers, i.e. the
  trampoline list;
- Oscar64's `.map`/`.csz` outputs for per-function sizes once files compile.

Spike plan: put 3 real files (e.g. `hack.c`, `apply.c`, `zap.c`) into separate
banks with trampolines, measure call overhead and resident cost; repeat with
REU overlays; pick. Write ADR-0006.

## Data and files: an REU RAM disk under NetHack's own file layer

NetHack already swaps levels to files: leaving a level calls `savelev()`
into a "level file", arriving calls `getlev()`. Saving, bones and the data
files go through the same small set of calls (`create_levelfile`,
`open_levelfile`, `dlb_fopen`, `read/write/lseek/close`). So:

- implement `open/read/write/lseek/close` over an **REU RAM disk** (a tiny
  allocation table + 256-byte block DMA). Level files, bones and the save
  file live there during play; `save` copies the RAM disk file to real disk
  via the KERNAL.
- implement NetHack's `dlb` (data librarian, `src/dlb.c`) over compressed
  blobs in EF banks or the REU: `data`, `quest.dat`, `rumors`, `oracles`,
  help files and the `*.lev` special levels are all read through it.
- without an REU (EF-only mode): level files go to disk, exactly like the
  floppy-based DOS versions did. Slow, but correct.

## Text compression

415 KB of text files + ~165 KB of in-code strings. Options: LZ (Oscar64 has
`oscar_expand_lzo`), dictionary/word compression (good for NetHack's
repetitive messages), or both. Strings embedded in code are harder (they are
`const char *` everywhere); start with the data files. Measure before
choosing.

## Window port (Phase 3)

NetHack talks to the display only through `struct window_procs`
(`include/winprocs.h`): `putstr`, `print_glyph`, `nhgetch`, menus, `yn_function`,
etc. `win/tty/` (4.5 K lines) is the model. Ours ("c64") draws into
`src/hal/screen80` and reads keys via the KERNAL buffer. Map glyphs come
through `mapglyph()`; colour per column-pair (see HARDWARE.md) suggests a
monochrome map first. Keeping the shadow text buffer as the source of truth
gives agents a text view of the game for free (`tools/vice.py screen`).

## System layer

`random()` -> NetHack's own RNG; time from the CIA TOD clock (or a turn
counter — NetHack only uses it for seeding, moon phase, Friday 13th, and
playtime); `getenv` -> fixed options; `panic`/`exit` -> message + wait + reset.
Signals, `fork`, user ids: compiled out (`#define` the platform as a new
`C64` system in `config.h`/`c64conf.h`, modelled on `pcconf.h`).

## Things we deliberately do not decide yet

- Save-file format compatibility with other ports: not a goal.
- Tiles/graphics: text only.
- Sound: none (maybe later: SID beeps for `--More--`).
