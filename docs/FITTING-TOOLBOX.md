# The fitting toolbox (Phase 2)

Status: **ideas with evidence, not decisions.** Each choice becomes an ADR
backed by a spike in VICE (PLAN.md, Phase 2 exit). Nothing in this file has
been run on a C64 or in VICE unless it says so.

Compiled 2026-11-12 from two research passes that followed Jolyon's pointers:
the Fairlight docs archive (http://www.fairlight.to/docs/), Raspberry Pi
cartridges that offer a 16 MB REU, disk drives used as co-processors, and the
crunchers that demo and game coders used. Links are collected in
`docs/REFERENCES.md`.

How to read the evidence tags:

| Tag | Meaning |
|---|---|
| [sourced] | Stated by the cited document; we did not run it |
| [derived] | Our reasoning from cited documents; a hypothesis until a spike confirms it |
| [arithmetic] | Our own sums from sourced figures |
| [simulated] | Computed on the host from NetHack save data re-encoded in the C64 layout |
| [recorded] | Already measured in this repo (file named) |

The problem being solved, from ARCHITECTURE.md and PLAN.md "Risks" (the
risk numbers below are PLAN.md's and are used throughout):

| Risk | What |
|---|---|
| 1 | RAM for dynamic state: 45-60 KB wanted, 30 KB resident (`$0900-$7FFF`) |
| 2 | Code and data against 1 MB of flash: about 1.7 MB of static content |
| 4 | EasyFlash + REU bus conflict on real hardware |
| 5 | Speed |

Banking options A (EasyFlash execute-in-place), B (REU overlays, no
cartridge) and C (hybrid, current primary target) are defined in
ARCHITECTURE.md "Code: banking".

## Verdicts at a glance

| # | Technique | Buys | Verdict |
|---|---|---|---|
| 1 | Half-window mode (`$01=$36`) | +8 KB resident RAM while code runs from flash | Try in Phase 2 |
| 2 | Hide the cartridge with `$01=$35`; the 16 KB under the window | 16 KB of data RAM for A/C with no EasyFlash register touched | Try in Phase 2 |
| 3 | Run without the KERNAL | About 50 KB contiguous RAM, option B only | Keep in reserve (a point for B in the banking ADR) |
| 4 | RAM under I/O with the REU `$FF00` trigger | 4 KB, usable as a DMA target only | Keep in reserve |
| 5 | Small pockets and zero page | About 4 KB in pieces; denser hot code | Try in Phase 2 (part of T2.3) |
| 6 | REU as swap and overlay store | A whole level in about 17 ms | Try in Phase 2 (already the design, T2.4) |
| 7 | REU DMA straight from flash, and into the RAM under the window | 1 MB flash to REU in about a second; no cartridge switching for copies | Try in Phase 2 |
| 8 | REU-only build from a `.reu` image; Pi cartridges (RAD) | Wider hardware audience; no `$DF00` conflict | Try in Phase 2 (it is option B, T2.2) |
| 9 | GeoRAM paging | Nothing we lack | Not for us |
| 10 | Disk drive as co-processor | Nothing: CPU time is not the shortage | Not for us |
| 11 | Custom IRQ loader with on-the-fly decrunch | 10-20x disk speed, stretch tier only | Keep in reserve |
| 12 | Host-side crunchers for read-only data | Roughly half the size of text and levels in flash | Try in Phase 2 (T2.5) |
| 13 | NetHack's own RLECOMP + ZEROCOMP for level files | Map 10,080 bytes down to 1.9-3.4 KB on samples | Try in Phase 2 (already enabled; T2.6 first) |
| 14 | A better level codec (planes, palette, predictive, LZ) | A further 30-43% on the map, up to about 3x in principle | Keep in reserve; needs an ADR |
| 15 | Oscar64 bytecode for code that need not be fast | 11-12.5% less code on the files measured, for a 3 KB resident interpreter and slower code | Keep in reserve |

---

## Memory map tricks

Sources for this group: the PLA notes
(http://www.zimmers.net/anonftp/pub/cbm/documents/chipdata/c64-pla.txt), the
C64-Wiki bank switching page (https://www.c64-wiki.com/wiki/Bank_Switching),
and the EasyFlash programmer's reference
(https://skoe.de/easyflash/files/devdocs/EasyFlash-ProgRef.pdf, pp. 5-12).
The specific PLA rows used below were not re-read in full during the
research, so every mapping claim here is [derived] and is the first thing
its spike must confirm.

Two mappings are already spent and need no section: the RAM under BASIC
(`$A000-$BFFF`) is the upper half of the EasyFlash window, and the RAM under
the KERNAL (`$E000-$FF3F`) holds the 80-column bitmap. `$FF40-$FFF9` (186
bytes) is spare [arithmetic].

### 1. Half-window mode (`$01=$36`)

- **What it is.** Clear LORAM and leave HIRAM set. In 16K cartridge mode the
  PLA should then show RAM at `$8000-$9FFF` while ROMH at `$A000-$BFFF` and
  the KERNAL stay mapped [derived].
- **Buys.** Resident RAM goes from 30 KB to about 38 KB while code is still
  executing from flash [arithmetic].
- **Costs and risks.** Code banks shrink to 8 KB (ROMH only). The ROML half
  of every bank (512 KB in total) is then reachable only by setting LORAM
  again, so it suits data better than code. Oscar64 bank regions must be laid
  out for `$A000`. Smaller banks mean more cross-bank calls.
- **Where it works.** Expected on VICE, the Ultimate family and a real
  EasyFlash, since only `$01` and the PLA are involved; unverified on all of
  them. Not applicable to the RAD (no cartridge ROM).
- **Options and risks.** Options A and C. Eases risk 1 at the price of
  risk 2 (code must fit in the ROMH halves, or pay a LORAM flip to reach the
  ROML halves).
- **Verdict: try in Phase 2.** It is the only trick found that adds RAM
  *while flash code is running*, and the spike is one AUTOTEST.

### 2. Hide the cartridge with `$01=$35`; the 16 KB under the window

- **What it is.** There is ordinary RAM at `$8000-$BFFF` underneath the
  cartridge window. CPU writes reach it even with the ROM mapped (8K and 16K
  modes); CPU reads need the ROM hidden. Clearing HIRAM (`$01=$35`) should
  hide ROML and ROMH together without writing EasyFlash's `$DE02` [derived].
- **Buys.** 16 KB of data RAM for options A and C. ARCHITECTURE.md already
  plans to reach it by "briefly switching the cartridge off"; doing it with
  `$01` is cheaper and touches no EasyFlash register.
- **Costs and risks.** `$01=$35` also removes the KERNAL, so IRQ and NMI
  vectors come from RAM at `$FFFA-$FFFF`: install vectors or mask
  interrupts. Only resident code may run while the window is hidden. In
  Ultimax mode there is no RAM there at all, so never leave resident code in
  that range.
- **Where it works.** The RAM under the window is standard on all C64s. The
  `$01=$35` route is expected on VICE, the Ultimate family and real hardware;
  unverified.
- **Options and risks.** Options A and C; this is the mechanism behind
  option C's "data under the window". Eases risk 1, but only for data that
  can tolerate being reached through a resident accessor.
- **Verdict: try in Phase 2.** The RAM plan (T2.3) cannot be drawn without
  knowing whether this 16 KB is cheap to reach.

### 3. Run without the KERNAL

- **What it is.** Keep `$01=$35` permanently and supply our own keyboard scan
  and interrupt handler.
- **Buys.** In a build with no cartridge mapped, `$0900-$CFFF` becomes 50,944
  bytes of contiguous RAM against today's 30 KB [arithmetic]; 1,000 of those
  bytes are the colour matrix at `$CC00` today. Zero page `$90-$FF` and
  `$0200-$03FF` also come free if the KERNAL is never called.
- **Costs and risks.** Our own keyboard and IRQ code. The KERNAL must be
  banked back in for disk saves, and KERNAL calls corrupt anything we put in
  `$90-$FF`. **With a cartridge, clearing HIRAM also unmaps ROML and ROMH
  [derived], so code cannot execute from flash while the KERNAL is out.**
- **Where it works.** Any C64; the mapping is plain `$01` banking.
- **Options and risks.** Option B only. It is a constraint ARCHITECTURE.md
  does not yet state: executing from an EasyFlash bank implies the KERNAL is
  mapped. That is a point for B in the banking ADR. Eases risk 1.
- **Verdict: keep in reserve.** Worth measuring only if spike B (T2.2) goes
  ahead; record the constraint in the banking ADR either way.

### 4. RAM under I/O, and the REU `$FF00` trigger

- **What it is.** 4 KB of RAM at `$D000-$DFFF`, visible only in all-RAM
  mode. The REU can reach it: a command written with bit 4 clear is deferred
  until any write to `$FF00`, so the program can switch to all-RAM mode
  between arming the transfer and triggering it. The REU uses "the memory
  configuration existing during writing to the command register" otherwise.
  [sourced: REU programming reference,
  http://www.zimmers.net/anonftp/pub/cbm/documents/chipdata/programming.reu]
- **Buys.** 4 KB.
- **Costs and risks.** Interrupts off and no I/O while it is visible, which
  is awkward for C code; it is realistic only as a DMA parking area. `$FF00`
  lies inside our bitmap, so the trigger must be `lda $ff00 : sta $ff00` in
  all-RAM mode (the reference's own idiom) to leave the pixel byte
  unchanged. The FF00 option clears itself after each use [sourced].
- **Where it works.** The trigger is write-only, so it fits the rule against
  reading `$DF00-$DFFF`. Expected on VICE and the Ultimate family;
  unverified. Needs an REU.
- **Options and risks.** Any option with an REU. Eases risk 1 slightly.
- **Verdict: keep in reserve.** 4 KB that can only be used through DMA is
  the last place to look. Spike it if T2.3 comes up short.

### 5. Small pockets and zero page

- **What it is.** Unused corners of the current map: `$0400-$07FF` (1 KB,
  the text screen, unused in bitmap mode), `$C000-$CBFF` (3 KB), the tape
  buffer `$033C-$03FB` (192 bytes). Zero page saves a byte and a cycle on
  each access to whatever lives there; Oscar64 already owns `$02-$8F`.
- **Buys.** About 4.2 KB in three pieces [arithmetic]: suited to fixed
  tables and buffers, not to the heap.
- **Costs and risks.** The tape buffer belongs to the KERNAL if tape is ever
  used. `$90-$FF` frees up only in a KERNAL-free build (technique 3).
- **Where it works.** Everywhere.
- **Options and risks.** All options. Eases risk 1 a little.
- **Verdict: try in Phase 2**, as lines in the T2.3 RAM map. No spike
  needed.

---

## REU tricks

Sources: REU programming reference and register list
(http://www.zimmers.net/anonftp/pub/cbm/documents/chipdata/programming.reu,
http://www.zimmers.net/anonftp/pub/cbm/documents/chipdata/reu.registers).
Both came to us through the Fairlight page, whose own links to them are
dead.

### 6. REU as swap and overlay store

- **What it is.** DMA between C64 RAM and the REU: stash, fetch and swap.
- **Buys.** One byte per cycle, 985,248 per second on PAL with the screen
  off; slightly less with the screen on [sourced]. So 16 KB in about 17 ms,
  the 16,813-byte `dlevel_t` in about 17 ms, a 256-byte RAM-disk block in
  about 0.3 ms plus register set-up [arithmetic]. Swap runs at half speed
  [sourced].
- **Costs and risks.** The `$DF00` rules in HARDWARE.md. The CPU is halted
  during a transfer, so no end-of-block polling is needed [sourced], which
  is what makes a write-only driver possible.
- **Where it works.** VICE (in `make test` today). Ultimate family needs CRT
  sub-type 1 alongside EasyFlash, still unverified on hardware. A real
  EasyFlash with a real REU is a bus conflict on reads (HARDWARE.md). The
  RAD emulates the REU side alone (technique 8).
- **Options and risks.** The core of B; the data half of C. Eases risks 1
  and 5; carries risk 4 under option C.
- **Verdict: try in Phase 2.** It is already the design (T2.4); the figures
  above are the budget to check the RAM disk against.

### 7. REU DMA straight from flash, and into the RAM under the window

- **What it is.** Two hypotheses [derived]. (a) A stash from `$8000-$BFFF`
  with a bank mapped copies flash to the REU at DMA speed. (b) A fetch into
  `$8000-$BFFF` lands in the RAM under the window without unmapping the
  cartridge, as a CPU write would.
- **Buys.** (a) All 64 banks into the REU in roughly a second [arithmetic],
  against a CPU copy loop: option C's "compressed text and levels live in
  the REU" becomes nearly free at start-up. (b) Level and overlay data moved
  under the window with no banking at all.
- **Costs and risks.** Depends on how each device resolves a DMA read of an
  emulated cartridge ROM; nothing we read documents it.
- **Where it works.** Unverified everywhere. Cheap to test in VICE; VICE
  passing would still need an Ultimate check.
- **Options and risks.** Option C (and a cartridge-booted B). Eases risk 2
  (flash becomes a boot medium for REU content) and risk 5.
- **Verdict: try in Phase 2.** Two small AUTOTESTs decide it.

### 8. REU-only build from a `.reu` image, and the Pi cartridges

- **What it is.** Option B shipped as a REU image plus a small launcher
  program, with no cartridge. The new information is who could run it:
  - **RAD Expansion Unit** (https://github.com/frntc/RAD): a cartridge
    carrying a Raspberry Pi 3A+, 3B+ or Zero 2 that emulates an REU up to
    16 MB and GeoRAM/NeoRAM up to 4 MB. This is almost certainly the "Pi
    Zero cartridge with 16 MB" Jolyon saw. Its menu mounts REU images from
    SD and can save the current expansion memory back. It emulates no
    EasyFlash or other cartridge [sourced: readme].
  - **VICE**: `-reuimage` preloads an image and `-reuimagerw` writes it back
    (https://vice-emu.sourceforge.io/vice_7.html).
  - **Ultimate family**: settings named "REU Preload", "REU Preload Image"
    and "REU Preload Offset" exist
    (https://1541u-documentation.readthedocs.io/en/latest/ultimate64-manual.html);
    we did not find their semantics documented.
  - **Turbo Chameleon 64**: REU up to 16 MB
    (https://www.c64-wiki.com/wiki/Turbo_Chameleon_64).
- **Buys.** A wider audience than the EasyFlash + REU cartridge, and no
  `$DF00` conflict because there is no EasyFlash. It also unlocks
  technique 3.
- **Costs and risks.** Needs an REU of 2 MB or more, so not a stock 1750.
  On the RAD: an external power supply is "strongly" recommended, bus
  timings are tunable and the author reports glitches on one board revision
  fixed by tuning, and the Pi is overclocked [sourced: readme]. How faithful
  its REU timing is against a real 17xx is the author's claim; we have not
  seen one run.
- **Where it does not help.** The primary target is unchanged: no Pi
  cartridge provides EasyFlash and REU together. **Sidekick64**
  (https://github.com/frntc/Sidekick64, same author) emulates EasyFlash
  "with simplified EAPI support" and GeoRAM but no REU. Stacking a RAD with
  a real EasyFlash is advised against by the author, and the Sidekick64
  readme warns that pairing with an EasyFlash 3 "will very likely destroy
  the EF3's CPLD".
- **Options and risks.** Option B. Removes risk 4 outright; eases risk 1
  (with technique 3) and risk 2 (a 16 MB REU holds everything uncompressed).
- **Verdict: try in Phase 2.** It is spike B (T2.2) with a stronger case
  than before; record the device list as an input to the banking ADR.
  Suggested follow-up for HARDWARE.md: RAD and Turbo Chameleon 64 rows for
  the alt-primary tier.

### 9. GeoRAM paging

- **What it is.** A 256-byte window at `$DE00-$DEFF` onto expansion RAM,
  with the page chosen by writes to `$DFFE/$DFFF`
  (https://www.c64-wiki.com/wiki/GeoRAM). Data is addressable in place; no
  DMA halt.
- **Buys.** Nothing an REU does not do better. A CPU copy at about 14 cycles
  per byte moves 16 KB in about 0.23 s against 17 ms by DMA [arithmetic].
- **Costs and risks.** Its window sits on EasyFlash's `$DE00/$DE02`
  registers and its page registers sit in EasyFlash's `$DF00` RAM page
  [derived from the two register maps], so it cannot back up the cartridge
  build.
- **Where it works.** VICE (512 KB-4 MB), RAD, Sidekick64, Turbo Chameleon
  64. Not alongside EasyFlash.
- **Options and risks.** None of A, B or C as written.
- **Verdict: not for us.** The one thing it would add is a Sidekick64
  audience, at the cost of a second memory driver 13 times slower than the
  first.

---

## The disk drive

### 10. Disk drive as co-processor

- **What it is.** A 1541 is a second 6502 at 1 MHz with 2 KB of RAM (1571:
  2 KB; 1581: 8 KB). Code is uploaded with `M-W` and started with `M-E`, or
  loaded by the drive itself with the undocumented `&` utility-loader
  command
  (http://www.zimmers.net/anonftp/pub/cbm/documents/disk-drives/1541-tricks.txt).
  Documented uses beyond fast loading:
  - *Mandelbrot Construction Set* (64'er 10/1991) used the drive's CPU to
    assist the calculation
    (https://www.c64-wiki.de/wiki/Mandelbrot-Construction-Set).
  - *Panta Rhei* (2004): the drive computes `$D018` values for an effect
    (comments at https://www.pagetable.com/?p=55;
    https://csdb.dk/release/?id=15745).
  - *Freespin* (2021): a demo that runs entirely on the 1541
    (https://hackaday.com/2021/07/08/c64-demo-no-c64/).
- **Buys.** For workloads that split cleanly, the pagetable article's
  figure is up to double the system's performance. A commenter there costed
  the other side: about 32 cycles to move a byte, no room for lookup tables
  in 2 KB, so a multiply takes about 216 cycles in the drive against about
  40 on the C64 with tables.
- **Costs and risks.** Hand-written 6502 for a second machine with its own
  test matrix. NetHack offers nothing to hand over: level generation,
  monster movement and vision need `dlevel_t` (16.8 KB) and far more code
  than fits; the game is turn-based and single-threaded, so the C64 has
  nothing to do in parallel; and the serial link is orders of magnitude
  slower than DMA.
- **Where it works.** Real drives, VICE with true drive emulation, the
  Ultimate family's drive emulation
  (https://1541u-documentation.readthedocs.io/en/latest/howto/mm_drive.html)
  and Pi1541. Not SD2IEC, which "cannot emulate a complete 1541"
  (https://www.c64-wiki.com/wiki/sd2iec_(firmware)).
- **Options and risks.** None. Our shortage is RAM and code space (risks 1
  and 2), not CPU.
- **Verdict: not for us.** A good story for the diary, with the reason we
  pass.

### 11. Custom IRQ loader with on-the-fly decrunch

- **What it is.** Drive-side code replacing the stock serial protocol, with
  the C64 decrunching as bytes arrive. Krill's loader is the current
  reference (https://csdb.dk/release/?id=226124).
- **Buys.** Stock KERNAL serial is about 400 bytes/s
  (https://en.wikipedia.org/wiki/Fast_loader). Krill's loader states up to
  4.0 kB/s raw and about 8.5 kB/s effective with decompression
  (https://plus4world.powweb.com/tools/Krills_Loader).
- **Costs and risks.** Needs a drive that runs uploaded code, so it excludes
  SD2IEC, among the commonest modern "drives". Per-drive variants.
- **Where it works.** As technique 10.
- **Options and risks.** Only the stretch tier (stock C64 + 1541, disk
  overlays). Would ease risk 5 there. For every other tier, flash and DMA
  are faster by two to three orders of magnitude.
- **Verdict: keep in reserve**, as an option beside plain KERNAL loading if
  the stretch tier is ever attempted. Saves to disk stay on KERNAL I/O so
  SD2IEC keeps working.

---

## Crunchers

### 12. Host-side crunchers for read-only data

- **What it is.** The modern descendants of the "compaction programs" Jolyon
  used. The packer runs on the PC and searches for the best encoding; only a
  small decruncher runs on the C64. (The Fairlight page still hosts one of
  the originals: X-terminator 2, the FairLight packer and linker.)
- **Buys.** The Codebase64 benchmark
  (https://codebase.c64.org/doku.php?id=base:compression_benchmarks; nine
  files, mostly measured in 2016, sizes exclude the decruncher):

  | Cruncher | Avg size (% of original) | Avg output speed (kB/s) |
  |---|---|---|
  | Subsizer 0.5 | 44.9 | 11.5 (preliminary) |
  | Exomizer (mem) | 45.1 | 7.2 |
  | Doynamite 1.1 | 48.1 | 17.4 |
  | NuCrunch 0.1 | 48.1 | 20.3 |
  | ByteBoozer 2.0 | 48.4 | 18.4 |
  | pucrunch (fast) | 53.7 | 7.0 |
  | TinyCrunch | 61.3 | 30.3 |
  | plain RLE | 80.9 | 47.8 |

  That benchmark predates Exomizer 3, ZX0, TSCrunch, LZSA and upkr, and we
  found no single benchmark covering them all. What their own documents
  state:
  - **Exomizer 3.1**: its streaming decruncher (`exodecrs/exodecrunch.s`)
    pulls input through a `get_crunched_byte` callback, which is what
    reading from a flash bank or the REU needs; the decrunch table is 156
    bytes; several files can share one encoding table
    (https://bitbucket.org/magli143/exomizer/raw/master/exo31info.txt).
  - **ZX02** (a 6502-oriented ZX0 variant): decoder of 108-166 bytes, usable
    from ROM, 8 bytes of zero page; a shared dictionary prefix (`-p`) and a
    bounded offset (`-m`) for windowed use; aimed at data up to about 16 KB
    (https://github.com/dmsc/zx02).
  - **TSCrunch 1.3**: built for speed, with in-place decrunching. Its
    author's chart (one file, not independent) gives about twice the
    throughput of ByteBoozer 2 and Dali for a few points less reduction
    (https://github.com/tonysavon/TSCrunch).
  - **upkr**: ratio "on par with Shrinkler"; the 6502 unpacker is 218 bytes
    of code plus 319 bytes of tables and needs a multiply
    (https://github.com/exoticorn/upkr, https://github.com/pfusik/upkr6502).
  - Oscar64 ships `oscar_expand_lzo` (ARCHITECTURE.md); the research did
    not examine its format or ratio.
- **Applied to us** [arithmetic from ARCHITECTURE.md's budget]: 415 KB of
  text and 213 KB of special levels at roughly 45-50% would save on the
  order of 300 KB of flash. Our own files are not the benchmark corpus; T2.5
  measures them.
- **Costs and risks.** A decoder in resident RAM or in each bank. A
  streaming decoder needs its back-references to stay inside RAM we still
  hold, so the output buffer is a RAM cost. These are **host-side optimal
  parsers: they cannot compress level files, which the C64 itself writes**
  (see "Level data"). Strings embedded in code remain the harder problem
  (ARCHITECTURE.md "Text compression").
- **Where it works.** Everywhere; it is plain 6502 code.
- **Options and risks.** All options; directly attacks risk 2. Under B with
  a large REU, compression matters less (the REU holds everything) except
  for load time from disk.
- **Verdict: try in Phase 2.** Make T2.5's "three ways" Exomizer 3.1, ZX02
  and TSCrunch, with `oscar_expand_lzo` as the baseline already in the
  toolchain. Measure ratio on `data`, `quest.dat`, `rumors` and the `.lev`
  files, plus decoder size and decode time in VICE.

---

## Level data

This is the "new level coding method" question. Short answer: NetHack
already has one, it is already switched on for the C64, it has never been
run in this project, and the samples suggest about 3x headroom beyond it.
**Everything below about sizes is [simulated] on five lightly explored
dungeon-level-1 maps. Every candidate codec is an untested sketch.**

### 13. What NetHack 3.4.3 already does

- `COMPRESS` (`config.h`, under `#ifdef UNIX`) is an external program run on
  save files. It is not a codec inside the game.
- Without `COMPRESS`, `config.h` defines `INTERNAL_COMP`, and `global.h`
  then defines both:
  - **RLECOMP**: run-length coding of the `levl` map only, in `savelev()`
    (`port/src/save.c` lines 462-509; reader in `port/src/restore.c`
    723-751). It walks the map row by row, compares every field of
    consecutive cells, and writes (count byte, whole struct) pairs with a
    count of at most 254.
  - **ZEROCOMP**: zero-run coding of every byte written to save, level and
    bones files, inside `bwrite`/`mread` (`save.c` 548-766, `restore.c`
    973-1060). A run of zeros becomes `0x00, n`. It buffers `BUFSZ` (256)
    bytes.
- **The C64 configuration has both on**: `port/include/config1.h` undefines
  `UNIX` under `C64`, and ADR-0006 item 6 records the save format.
- **The host build has neither**: it is `UNIX`, so it uses `COMPRESS`, and
  `tests/host_smoke.py` never executes the RLECOMP or ZEROCOMP paths. T2.6
  (a host variant with `COMPRESS` off) is open and should come before any
  codec work.

`struct rm`, one map square (`port/include/rm.h`; 6 bytes under Oscar64
[recorded: NETHACK-SURVEY.md], 8 on the x86-64 host):

| Field | Type | Meaning |
|---|---|---|
| `glyph` | int | What the hero remembers seeing there |
| `typ` | schar | Terrain type |
| `seenv` | uchar | Which angles the square has been seen from |
| `flags` | 5 bits | Terrain-specific flags (door state, non-diggable, ...) |
| `horizontal` | 1 bit | Wall or door orientation |
| `lit` | 1 bit | Lit |
| `waslit` | 1 bit | Remembered as lit |
| `roomno` | 6 bits | Room number |
| `edge` | 1 bit | Room edge marker |

The map is `levl[80][21]`: 1,680 cells, 10,080 bytes on the C64. A run of
one cell costs 7 bytes under RLECOMP, so its worst case is 11,760 bytes,
larger than the raw map [arithmetic].

After the map, `savelev()` writes the stairs and level flags, the door
table (always 120 entries), rooms, timers, light sources, the monster chain
with inventories, worm segments, traps, three object chains, engravings,
wall damage and regions. The object and monster location grids are not
saved; they are rebuilt on load. Recorded Oscar64 sizes: `struct obj` 48
bytes, `struct monst` 80.

Map size on the five samples [simulated]:

| Coding of the 10,080-byte map | Range (bytes) |
|---|---|
| ZEROCOMP alone | 8,988-9,581 |
| RLECOMP alone | 1,876-3,458 |
| **RLECOMP + ZEROCOMP (the stock C64 coding)** | **1,877-3,443** |
| Reference: zlib -9 | 557-1,103 |
| Reference: xz | 492-981 |

- ZEROCOMP adds almost nothing to the map on top of RLECOMP, and little on
  its own, because the remembered glyph for unexplored stone is not zero.
  Its value is in the rest of the file, which is largely zeros.
- 60-72% of sampled squares are stone, and a sample has 97-207 distinct cell
  values.
- The samples flatter every codec. Well-explored levels and mazes will be
  worse; how much worse is not measured.

**Verdict: try in Phase 2.** It costs nothing to adopt, since it is the
configured format. Do T2.6 first so the path is tested on the host, then
measure real level files (below).

### 14. Candidate level codecs (all untested)

| Candidate | Idea | Map size on samples (bytes) | Against stock | 6502 cost |
|---|---|---|---|---|
| Stock | RLECOMP + ZEROCOMP | 1,877-3,443 | baseline | In the source already |
| A. Field planes | Split the map into six byte planes and byte-RLE each | 1,308-2,368 | 30-35% smaller | One RLE routine run six times; no extra buffer if streamed plane by plane |
| B. Cell palette | Per-level table of distinct 6-byte cells, then RLE of one-byte indices | 1,118-2,230 | 35-43% smaller | A lookup while encoding, and a fallback for levels with more than 256 distinct cells |
| C. Predictive | Store terrain compactly; derive the remembered glyph from terrain and store only the exceptions; likewise `seenv` | not measured | unknown | Most code; reaches into display logic, so the highest risk of subtle bugs |
| D. LZ at the file layer | Leave NetHack's writer alone and pass the `bwrite` stream through a greedy LZ | not measured (zlib reference 557-1,103) | up to about 3x in principle | A run-time *compressor* on the 6502: match search plus a window buffer |

- **A** keeps the data model untouched. The `typ` plane dominates what is
  left.
- **B**'s palette grows with exploration, which is the direction real levels
  move in.
- **C** rests on two sample observations: only 57-142 squares have a glyph
  that differs from the commonest glyph for their terrain, and `seenv` is
  non-zero on only 60-614 squares. "Everything defaults to plain stone" is
  not enough, because boundary stone carries the non-diggable flag.
- **D** is the only one that also covers monsters, objects and the fixed
  tables. A and D do not stack: planes followed by zlib gave 603-1,119
  bytes, no better than zlib alone. The crunchers of technique 12 cannot do
  this job, because their packers are host tools.
- Regenerating levels from a seed instead of storing them would change game
  behaviour; it is not on the table.

Common to all four:

- **Costs and risks.** A save-format change is lossless but touches game
  files, so it needs a decision record before any edit (AGENTS.md).
  Encoder and decoder code occupy the bank space they are meant to save.
- **Where it works.** Everywhere; plain C.
- **Options and risks.** With an REU of 512 KB or more, level files are
  small against the space available, so this matters little for B and C. It
  matters for the EasyFlash-only and disk-only tiers, where level files go
  to disk, and for save-to-disk time on every tier (risk 5).
- **Verdict: keep in reserve.** Measure first: real level files from the
  stock coding, from deep and fully explored levels (mazes, Minetown, the
  big room), on the T2.6 host build. If a codec is still wanted, A is the
  cheapest to try and compare in `tests/host_smoke.py`.

---

## Code density

### 15. Oscar64 bytecode for code that need not be fast

- **What it is.** Oscar64 can compile a function to a compact bytecode that
  an interpreter in its runtime executes, instead of 6502 machine code: `-bc`
  for a whole program, and in such a program `#pragma native(f)` or the
  `__native` specifier keeps chosen functions as machine code (Oscar64's
  manual, `oscar64.md`: "-bc" and "#pragma native") [sourced]. NetHack spends
  most of its time waiting for a key, so most of its code need not be fast.
- **Buys.** [recorded] Measured 2026-11-13 with the ADR-0007 compiler at
  `-Os`, C64 configuration, under a zero-filled compiler heap (otherwise its
  output depends on old heap contents: OSCAR64-COMPAT.md #40, #41), on the 44
  files that reach code generation: `tools/measure/measure_oscar64.py --config c64`
  with and without `MEASURE_BC=1`; data in
  `docs/data/oscar64-pin-c64-native-2026-11-13.json` and
  `docs/data/oscar64-pin-c64-bytecode-2026-11-13.json`. On the 39 files that
  place the same functions both ways (left out: the three data files, and
  `ball.c` and `hacklib.c`, which place one function more in bytecode): native
  246,478 bytes, bytecode 219,274 (0.89). Bytecode is smaller in 34 files,
  down to 0.62 (`rnd.c`), 0.64 (`o_init.c`) and 0.65 (`exper.c`); of the big
  files, `vision.c` is 0.66 and `mkobj.c` 0.70. It is bigger in five:
  `quest.c` 1.32, `sounds.c` 1.18, `sit.c` 1.16, `mhitm.c` 1.10, `drawing.c`
  1.02. Picking the smaller form file by file gives 215,783 (0.875), 30,695
  bytes less over these 39 files. Oscar64's manual expects the opposite ("the
  native code is not only significantly faster than the interpreted one, but
  also smaller in most cases"; Dhrystone: bytecode 10,993 bytes, native 8,952)
  [sourced]; on NetHack's code at `-Os` it is not so.
- **Costs and risks.** Speed: the manual's Dhrystone figures, 94 iterations
  per second in bytecode against 442 native, make bytecode about 4.7 times
  slower [arithmetic]; not measured on NetHack. The interpreter is native code
  that every bank running bytecode needs within reach, so in practice it is
  resident [derived]. Its size [recorded], from the link maps of the same 44
  compiles (add `MEASURE_KEEP=1`): one file links 80 to 94 of its routines
  (2,246 to 2,667 bytes); all 44 together use 101 (97 `inp_*` handlers and
  four branch and compare helpers), 2,873 bytes, plus a 256-byte table of
  handler addresses at `$0900`: about 3.1 KB. The runtime defines 112 `inp_*`
  handlers (`include/crt.c`), so the 63 files that do not compile yet can add
  at most 15. The bugs differ: several of this week's wrong-code bugs are
  native-only (r37 is right in bytecode) and at least one was seen in bytecode
  alone (a `long` summed in a loop, TASKS T1.22) [recorded], so a mixed build
  needs its repros run in both modes.
- **Options and risks.** Any option. Risk 2 (code and data against flash):
  11% less code on these files, 12.5% picking file by file, less the
  interpreter. Risk 1 (resident RAM): the interpreter costs about 3 KB of it.
  Risk 5 (speed): worse.
- **Verdict: keep in reserve.** A real but modest saving, smaller than the
  crunchers' on data (technique 12). Worth a spike only if code still does not
  fit once banking is designed: keep hot code (vision, movement, monster turns)
  `__native`, then measure size per function, and speed in VICE.

---

## Rule check (AGENTS.md)

The two hardware rules are: never read `$DF00-$DFFF`; never use EasyFlash's
256 bytes of RAM. How the toolbox stands against them:

| Technique | Rule status |
|---|---|
| REU **verify** command, and any status or address read-back | **Conflicts.** The result is the FAULT bit of the status register at `$DF00`, which must be read [sourced: REU register list]. Compare by fetching and comparing in C64 RAM instead. |
| Any REU transfer whose C64-side range covers `$DF00-$DFFF` while I/O is mapped | **Conflicts** [derived]: the REU uses the memory configuration in force, so a stash would read the I/O page. Use the `$FF00` trigger in all-RAM mode (technique 4), or keep transfers out of `$D000-$DFFF`. |
| GeoRAM (technique 9) | No read of `$DF00-$DFFF`, but its page registers at `$DFFE/$DFFF` and window at `$DE00` sit on EasyFlash's RAM and registers. Incompatible with the cartridge build. |
| RAM under I/O (technique 4) | Compliant only while I/O is banked out: then `$DF00-$DFFF` is plain RAM. A read through that range with I/O mapped breaks rule 1. |
| REU `$FF00` trigger | Compliant: write-only. |
| `$01` banking (techniques 1-3) | Compliant: no I/O2 access and no EasyFlash register. |
| Stacking a Pi cartridge with a real EasyFlash | Outside the rules but warned against by the cartridge author (technique 8). |

## Suggested spikes

Each is a small AUTOTEST in `src/` (AGENTS.md: "Add an AUTOTEST check for
anything new in `src/`"). None changes game behaviour, so none needs an ADR
to try; the banking decision they feed is already slated for one.

1. `$01=$36`: write and read back `$8000-$9FFF` while calling a function in
   ROMH (technique 1).
2. `$01=$35` round trip from resident code with RAM vectors installed
   (technique 2).
3. REU stash of a flash bank, checked against the `.crt` contents
   (technique 7a).
4. REU fetch into `$8000-$BFFF` with the cartridge mapped, read back with it
   hidden (technique 7b).
5. If T2.3 comes up short: `$FF00`-triggered DMA into `$D000-$DFFF`
   (technique 4).

Measurements wanted, none needing new C64 code:

- T2.6, then stock-coded level files from deep and explored levels
  (techniques 13, 14).
- T2.5 with the cruncher shortlist (technique 12).
- Only if code still does not fit after the banking spikes (T2.1, T2.2) and
  the RAM map (T2.3): bytecode size per function with hot code kept
  `__native`, then its speed in VICE (technique 15).

## Left out because the research could not verify it

- Decruncher code sizes for most crunchers, and in-place or streaming
  support beyond what technique 12 states.
- Whether RAD, Sidekick64 or the Turbo Chameleon 64 can present an
  EasyFlash and an REU together; whether the RAD can auto-mount an image at
  power-on; what Sidekick64's "simplified EAPI" omits.
- Any speed-up figure for the drive-assisted Mandelbrot program, and other
  second-hand reports of drive-side computation.
- Whole-level-file sizes on the C64. Only the map was simulated; the rest
  is unmeasured.
- Most outbound links on the Fairlight page are dead. REFERENCES.md points
  at mirrors that answered on 2026-11-12; we did not check they are
  byte-identical to what Fairlight linked.
- `codebase64.org` now redirects to an unrelated domain. Use
  `codebase.c64.org` or `codebase64.net`.
