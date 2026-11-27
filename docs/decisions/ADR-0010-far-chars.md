# ADR-0010: Far characters: byte pointers tagged by address range

- Status: accepted as built (Jolyon, 2026-11-27: "Ok that sounds good to me", to the
  recommendation to accept the C128 layout as built); proposed 2026-11-20, on hold after
  review, revised 2026-11-21 (below) and built that night under "you go ahead". The C64's
  layout of the same idea is designed when its squeeze starts.
- Date: 2026-11-20
- Deciders: Jolyon (+ Claude Code, which proposed it; Jolyon agreed to the direction:
  "I agree with your suggestion", 2026-11-20, after options A, B and C in RAM-PLAN.md)

## Context

ADR-0009 put NetHack's struct data in far spaces: a pointer to a far struct type is a
16-bit address in its space, translated through the space's page table at each access.
That has taken the resident data from 99.6 KB to about 47 KB (RAM-PLAN.md, "the
resident side, the data"; `docs/data/wholegame-far-2026-11-20.txt`). What is left is
mostly `char` data that code reads and writes through `char *` (and `void *`), which a
type-based space cannot follow, since every string function takes such pointers:

- 17 KB of string literals of resident code and of tables read from several banks;
- about 16 KB of `char` arrays and other objects whose address is handed on as a near
  pointer (`docs/data/fardefault-trial-2026-11-20.txt`): `killer_buf`, `plname`,
  `toplines`, `msgbuf`, the 256-byte buffers, `bufs`.

The budget for resident code and data is about 25 KB (34 KB in view, less the 4 KB page
cache, the stack and a near heap; ADR-0009 point 6). Resident code is 26 KB on its own,
so the data has to come down to the hot globals and the glue's buffers.

The accessors for names (`NH_MNAME()`, ADR-0009's amendment) show the copy-out approach
works but needs a wrapper at every read site and a ring of copies whose lifetime has to
be checked; it does not reach buffers that code writes.

## Decision (as first proposed; revised below)

1. **A character space.** `#pragma farchars(n, base)` makes far space n the space of
   byte data: an access of one byte (`char`, `signed char`, `unsigned char`, and what a
   `void *` reaches) through a pointer whose target the compiler does not know to be a
   near object is tagged by its address. Addresses from `base` (proposed `$C000`) to
   `$FFFF` are in space n and translated through its page table like any far access;
   below `base` the pointer is used as it is. The test is inline: the pointer's high
   byte compared with `base`, a branch over the translation call (about 6 bytes and 5
   cycles on the near path, beside the far path's 5-byte call).
2. **What lives there.** A far character section in space n holds: the literals of
   resident code and of tables read from several banks (a new `#pragma strings(section)`
   sends the literals of the code that follows to `section` instead of the code section),
   and, by `#pragma fardefault` (the fork's commit 9), the `char` arrays that are now kept
   near only because they are reached through `char *`. Banked code's own literals stay
   in their bank (near, in the window); the hot globals stay near.
3. **No address of near `char` data in the range.** Near RAM, the bank window and the
   80-column bitmap's code keep below `base` or use word-sized accesses; the screen
   driver writes its bitmap (`$E000`) through its own `__asm` or non-byte pointers, and is
   checked for it.
4. **Built-ins and libc.** The compiler's built-in `strcpy`, `memcpy` and `memset` on a
   maybe-far byte pointer become calls of far-aware runtime routines; libc's `string.c`
   routines in assembler (`strcpy`, `strncpy`, `memset`, `memcpy`) get far-aware versions
   (the C versions, which the compiler now translates, or assembler with the same range
   test). `printf`-style formatting is C and needs nothing new.
5. **Across banks.** A far string is the same address in every bank, so the string
   trampolines (`NH_IN_WINDOW`, `$8000-$BFFF`) leave it alone and `nh_keep()` keeps it as
   it is: fewer copies than today, not more.
6. **Pages.** Byte accesses are translated one by one (no groups: a byte is never split
   across pages), so far character data needs no alignment; a built-in block move
   translates per page.

## Consequences

- Easier: strings and `char` buffers can leave resident memory without touching
  NetHack's source; the name accessors could be retired later (the names moved into the
  character space).
- Harder: every byte access through a pointer of unknown target pays the inline test, a
  compiler change in the late translation pass and the native code generator, and a
  check that nothing reaches far character data with a wider access (`*(int *) buf`).
  libc's assembler string routines need far versions.
- Watch: the speed of string-heavy code (formatting a message, `xname()`), measured in
  the speed harness before the whole game; the size of the range (16 KB from `$C000`)
  against what should go there; zero page (the test needs no temporary).

## Evidence / how to re-check

- The resident data by kind: `docs/data/wholegame-far-2026-11-20.txt` (far24-27), and the
  far default's trial, `docs/data/fardefault-trial-2026-11-20.txt`.
- To come: an autotest of the character space (literals, buffers, `strcpy`/`memcpy` both
  ways, a `void *` path, the near path untouched), the speed harness's cost for `xname()`
  and a message, then a whole-game link.

## Review (2026-11-20, gpt-6.2-astra, `docs/sessions/2026-11-20-codex.md`)

Checked by Claude Code where marked. The design is not wrong in principle, but:

- **The range caps the saving.** `$C000-$FFFF` holds 16 KB; far27 has 11.9 KB of resident
  literals (checked: far27's map) and the far default's 15.8 KB are not all `char`. Even
  all of it would leave about 43 KB resident against 25 KB.
- **Ambiguity with the name spaces.** `$E000-$FFFF` already means a name in spaces 1-3 to
  `NH_MNAME()`/`NH_ONAME()`/`NH_RNAME()`; `options.c` stores `"fruit"` into a name field
  (checked: line 603). The range must not overlap them, or the names must move into it.
- **Hardware code uses `char *` on physical addresses** (checked: `screen80.c` writes the
  bitmap through `char *dst` and clears it and the colour map with `memset()`): it needs a
  physical byte access that the test leaves alone.
- **The test must be on the effective address** (pointer plus offset, with carry), not on
  the pointer; `MapLateIntrinsics()` turns some `memcpy()` calls back into `IC_COPY`, a
  second way in; block copies need both pages bounded per chunk and pin slots respected;
  `strcmp()` is assembler too (checked); DMA (`reu_store()`) and saves take raw addresses.
- The near path costs at least 8 cycles, not 5.

What would decide it: a spike with different bytes at the same address in the character
space and a typed space, non-adjacent cache frames and forced eviction; and a ledger of
what each lever saves against the whole budget (RAM-PLAN.md).

## Revised design (2026-11-21)

Measured on far36 (`build/bank-c64-far36`, resident 58,286 B: data 37,850, code 20,436;
`docs/data/wholegame-far-2026-11-21.txt`). "Checked" marks what was read in the far-spaces
fork's source (`build/oscar64-wt/far`, ten commits on pin 85) or in the map and listing.

### What far characters could move

| Near today | Bytes | Objects | Note |
|---|---|---|---|
| Literals of resident code and of resident or shared tables | 11,718 | 965 | all 79 B or less; 5,555 B in literals under 16 B |
| &nbsp;&nbsp;pointed at only by tables | about 7,730 | | 4,420 B of it from tables the failed link left unplaced (their pointer bytes are zero in the listing, so the table is inferred) |
| &nbsp;&nbsp;referred to by banked code, with or without tables | about 3,510 | | 1,613 B only by banked code: 1,045 B by code in a single bank, 568 B by several banks |
| &nbsp;&nbsp;referred to by resident code | about 470 | | |
| `char` arrays (not the glue's) | 8,993 | 122 | 678 B touched every turn (`circle_data`, `colbump`, the `cs_rmin`/`cs_rmax` rows); over a page: `bufs` 3,072, `buf` (several statics) 573, `msgbuf` 512, `toplines` 300; seven `BUFSZ` buffers of 256 B (`outbuf`, `li`, `killer_buf`, `kbuf`, `inbuf`, `altbuf`, ...), `in_line`, `out_line`, `wizkit`, the symbol tables, about 90 short message arrays |
| The glue's buffers | 2,552 | | `nh_args` 1,024, `nh_stash_buf` 512, `nh_name_ring` 384, the `nh_keep_*` copies, `nh_farbuf` 64 |
| Everything else named | 11,452 | | structs and scalars: `u` 1,381, `artilist` 1,330, `dungeons` 768, `compopt` 504, `boolopt` 448, `shtypes` 336, ...: not far characters' business |
| Static frames | 3,135 | | |

How the literals were attributed (`litrefs.py`, a heuristic over the listing): an
immediate low byte followed within six instructions by its high byte is a reference from
that code; the address as a little-endian pair in a `BYT` row is a reference from that data.
The share is reliable to a few hundred bytes. The single-bank literals are a question of
their own (below, point 1).

So far characters could reach about 20.0 KB: 11.7 KB of literals and 8.3 KB of `char`
arrays that aren't touched every turn. The glue's buffers stay near, because they are how a
string crosses a bank. The hot arrays stay near too.

### The review's points

- **The 16 KB cap.** The cap holds: a near `char *` can only be tagged in 16 KB of values,
  and 20.0 KB is wanted. The revised range is `$C100-$FFFF` (16,128 B; why `$C100` is below).
  - What goes in, in this order: all literals of resident code and tables (11,718 B, read
    rarely, never written); then the coldest buffers (`killer_buf`, `wizkit`, `in_line`,
    `out_line`, `li`, `inbuf`, `altbuf`, the symbol tables, the short message arrays), up to
    about 3.9 KB.
  - What stays near: the formatting buffers written for every message, `bufs`, `msgbuf`,
    `toplines` and `buf` (4,457 B).
  - The range holds about 15.6 KB of the 20.0, net of the code the tests add (below).
- **The `$E000-$FFFF` names.** The overlap is safe under one rule: a name field holds only a
  name, a near pointer or a character-space pointer below `$E000`.
  - Checked: `nh_name_into()` in bankgen.py's glue copies out only at `$E000` and above, and
    returns anything below as it is.
  - A character-space pointer from `$C100` to `$DFFF` therefore passes through
    `NH_MNAME()`, `NH_ONAME()` and `NH_RNAME()` untouched. The code that then reads it gets it
    translated by the character space's test.
  - Every name is already read through an accessor, so the compiler's test never sees a raw
    name pointer. Before the accessors, reading one directly would have read the bitmap: it
    was already a bug.
  - The one known non-name in a name field is `options.c` 603, `pl_fruit`. It, and anything
    else stored into a name field, is placed below `$E000` or stays near.
  - The names stay in their own spaces (14.7 KB: `faronames` 8,187, `farmnames` 4,016,
    `farrnames` 2,498), so the character space doesn't have to hold them.
- **Hardware code.** `screen80.c` writes the bitmap through `char *dst` and clears
  `S80_BITMAP` and `S80_COLORMAP` with `memset()` (checked).
  - Platform files are compiled with `#pragma farchars(off)` (new): no test, physical
    addresses.
  - The HAL's entry points take near pointers only. A NetHack caller passes them near data,
    and today none passes a buffer that would move.
- **The effective address.** For `(zp),y` the base in zero page is at or below the effective
  address, and `Y` is at most 255.
  - With the character space starting at `$C100`, a base lowered by the optimiser by up to
    255 bytes still lies at or above `$C001`, while near objects end at `$BFFF`.
  - So a test of the base's high byte (`>= $C0`) is exact for every `(zp),y` access.
  - Absolute `,x`/`,y` accesses reach known objects and are never tested.
  - To check in the native code generator: that no pass lowers a base by more than 255, or
    forms a base from a different object. Where one does, the test falls back to the
    computed address.
- **Copies and the library.** Byte data in the character space is not aligned, so a copy can
  straddle pages.
  - `MapLateIntrinsics()` runs before `LowerFarAccesses()` (checked: `InterCode.cpp` 30579
    and 30820). The late pass already handles `IC_COPY`, `IC_STRCPY` and `IC_FILL` (checked:
    27199-27203), but with one translation per operand: right for typed objects, which keep to
    a page, wrong here.
  - For the character space, a copy, string copy or fill whose operand has no known target
    becomes a call of a far-aware routine. The routine translates a page at a time and bounces
    through a 64-byte near buffer when both sides are far, so only one cache frame is pinned
    at a time (`nh_farbuf`'s pattern).
  - Oscar64's assembler `strcpy`, `strncpy`, `strcmp`, `memcpy` and `memset` (the review
    checked `strcmp`) get versions with the same test per operand, near path first.
- **DMA and saves.** These go through the C64 `read()`/`write()` under `port/sys/c64`.
  - A buffer at `$C100` or above is bounced through `nh_farbuf` in 64-byte chunks, as
    `nh_farbwrite`/`nh_farmread` already do for the typed spaces.
  - `reu_store()`/`reu_load()` are platform calls and take near pointers only (above).
- **The near-path cost.** About 7-8 cycles and 7 bytes inline: `LDA zp+1; CMP #$C0; BCS far`.
  A base not already in zero page costs more.
  - Resident code holds 722 `(zp),y` accesses of all sizes (checked in the listing). If about
    400 are bytes through unknown pointers, inline tests add about 3 KB of resident code;
    calls instead of inline tests add about 1.2 KB.
  - Banked code holds 101,098 `(zp),y` accesses. It grows by perhaps 100-200 KB, that is
    7-13 banks.

### Alternatives considered

- **A pointer qualifier** (`char __far *`). Rejected: NetHack passes `char *` through nearly
  every prototype, so the qualifier would spread through the whole source. Wrapping the read
  sites is mechanical, but it is a rewrite in all but name.
- **A far character section reached by accessors**, `NH_MNAME()` generalised to every string
  field of a table (roles, genders, aligns, artifacts, options, extended commands, shop types,
  spellings, monster explanations).
  - Gain: reaches only the literals that tables point at, about 7.7 KB, with no compiler
    change and no cost on any other access.
  - Cost: a wrapper at every read of those fields, and the ring's lifetime checked at each.
  - It can't reach buffers.
- **Literals placed with their code**, a linker change with no run-time cost.
  - A literal that code in one bank alone refers to belongs in that bank (1,045 B).
  - One that several banks refer to can be copied into each (568 B, for a little bank space).
  - Why the single-bank ones are resident is not known yet: suffix sharing between literals,
    an inlined resident helper, or a heuristic miss. Finding out comes first.

### Step 1 looked into (2026-11-21): no linker fix to make

The 1,613 B of literals that only banked code seemed to use was mostly an artefact of the
attribution, and the cause question has a plain answer (far36's listing, map and generated
sources):
- Oscar64 puts a literal in the code section in force where it is written. bankgen.py wraps
  each banked function in `#pragma code(nhbank_N)`, and the map shows those literals in
  their banks (`DATA:nhbank_N`), so banked code's own literals already go with it.
- The resident literals are those of resident code and those written at file scope,
  which is compiled under `#pragma code(code)`: the strings of tables, and the occasional
  pointer such as pray.c's `Moloch` or trap.c's `A_gush_of_water_hits`.
- Resident code includes the variadic message functions (`You_hear`, `There`, `You_feel`,
  ...), which bankgen.py keeps resident whatever the plan says ("variadic"). Their literals,
  such as "You dream that you hear ", are resident with them.
- `litrefs.py` missed references that load the high byte first (`LDA #hi; LDX #lo`, as in
  `You_hear`) and credited chance pairs of immediates in banked code instead. Counting both
  byte orders, within three instructions of one function, still leaves mostly chance matches
  (monster-class and skill names "used" by unrelated functions). Those literals belong to tables.
- What a linker change could still move is the file-scope pointers that one bank alone
  uses: about 35 such definitions across the sources, 528 B of literal in all (most of them
  locals, already banked), so a few hundred bytes at best. And it has the same escape question as
  banked literals. Not worth a step of its own: the range tag (point 2) takes these
  literals with the rest.

### Recommendation

1. The linker fix for literals placed with their code, first: up to 1.6 KB, no run-time cost.
   Find the cause before the fix.
2. Then the range tag at `$C100-$FFFF`, holding the literals and the cold buffers: about
   15.6 KB of data, less about 1.2-3 KB of resident code, so about 12.5-14.5 KB net.
   - Before building it, the review's spike: the same address with different bytes in the
     character space and a typed space, non-adjacent cache frames, forced eviction.
   - Also before building: the speed harness's cost for `xname()` and a message. The
     formatting buffers stay near, so most writes keep the near path.
   - The character space shares the 16-page cache with the typed spaces: watch the faults.
3. If the speed or the size disappoints: the accessor route for the table literals instead,
   about 7.7 KB.

This nets less than the ledger's "up to about 18 KB" (RAM-PLAN.md): about 13-16 KB with
point 1.

### On a C128 (2026-11-21: laid out and spiked)

The C128 runs the game first (ADR-0003, amendment of 2026-11-21), so far characters are laid
out for it first. The compiler's side is the same on both machines. Only the runtime behind
the far path differs.

- **The character space is RAM bank 1**, at the same addresses: a byte pointer from `$C100` to
  `$FBFF` (15,104 B) reads and writes bank 1 there. That holds the 11.7 KB of literals and about
  3.4 KB of the cold buffers, 0.5 KB less than the C64's range. No page cache and no page tables. A copy
  can't straddle anything, so the review's points on frames, eviction and chunked copies are
  the C64's alone.
- **Bank 0 keeps only code from `$C000` up** (the C128 link's regions `$C000-$CFFF` and
  `$E000-$FBFF`, `docs/data/wholegame-c128-2026-11-21.txt`). No `char *` points at code, so
  the range costs no near RAM.
  - The test of the base's high byte stays `>= $C0`, for the reason given under "The effective
    address".
  - The C64 bitmap at `$E000` doesn't exist on the C128 (the 80-column chip has its own RAM).
- **The stubs live in the top 1 KB, made common to both banks** (`$FC00-$FFFF`, RCR bit 3, as
  Oscar64's `c128/bank1.h` does). An access saves `$FF00`, writes `$FF02` (which loads PCR B:
  bank 1, all RAM), makes the one access and stores the old value back.
  - It keeps whatever configuration it found: the cartridge's `$3A`, all RAM with or without
    the I/O.
  - Zero page and the stack stay in bank 0 (the MMU's P0 and P1 registers), so the pointer in
    zero page works from either bank.
  - An NMI during the access finds bank 0's vectors, in the common 1 KB.
- **The names stay where they are.** The ambiguity rule above (a name field holds a name, a
  near pointer or a character-space pointer below `$E000`) holds unchanged.
- **Which code gets the test.** NetHack's code and our window port, which takes NetHack's
  strings, get it. Only the hardware layer, under `#pragma farchars(off)`, takes near pointers
  alone.

### Step 2's checks (2026-11-21)

Both checks the review asked for before building, done on the C128 layout
(`docs/data/farchar-checks-2026-11-21.txt`).

**The spike** (`tests/spikes/farchar128.c`, `run_farchar128.py`, x128 in C128 mode): 7 of 7.
- Every byte of `$C100-$FBFF` is written in bank 1 and reads back.
- Code compiled at `$C1xx` in bank 0 runs and reads bank 1's bytes at its own addresses.
  Bank 0 still holds the code.
- The stub puts back `$3E`, `$3A` and `$3F` as it found them.
- A string copy far to near runs across `$CFFF/$D000`, and writes to bank 1 under the I/O leave
  the VIC alone.
- The hand-written test of the compiler's shape reads near data near and far data far.

Costs at 1 MHz, a byte access in a loop (CIA cycles, the VIC's bad lines included):

| Access | Cycles | More than a plain `LDA (zp),y` |
|---|---|---|
| plain | 10.4-10.7 | |
| tested, near | 18.4-18.5 | 7.7-8.2 |
| tested, far (a call of the stub) | 48 | about 37.5 |
| a string copied far to near, by a copying stub | 27.5-28.8 a byte | |

The same address with different bytes in the character space and a typed space is the
compiler's test to make (its autotest): a typed space's pointer never reaches the byte test.

**The speed of object names and messages.** Measured on the host game, as an upper bound:
`tools/measure/speed/fcbytes.py` counts the byte loads and stores the game's own code
executes inside each function's calls (callgrind, one game a function, 146 commands, 91 of
them inventory commands).
- The x86 operand's shape stands in for the 6502's: through a pointer with no displacement or
  an index (`*p`, `p[i]`, but also an indexed global array, which the 6502 reaches directly and
  never tests), or with a constant displacement (mostly struct fields, which don't take the
  byte test).
- `xname()`: 3.6 and 8.4 such accesses a call. `doname()`, with the `xname()` it calls: 12.1
  and 23.8. So at most 36 tests, about 290 cycles.
- What the host does in libc is C on Oscar64 (`strncmp`, `strlen`, `strcat`, `strchr`,
  `strncpy` and `sprintf`'s formatter; only `strcpy`, `strcmp`, `memcpy` and `memset` are
  assembler), so it is tested per byte. A `doname()` makes 9.1 `strncmp`, 1.8 `strcat`, 1.2
  `sprintf`, 1.1 `strlen` and 1.1 `strchr` calls over strings of 10-40 characters: about
  200-250 tests, 1,600-2,000 cycles.
- The object's name is a table literal, so it is read far: about 20 characters at 30 cycles
  more, about 600.
- **About 3,000 cycles more for each `doname()`, 3 ms at 1 MHz** (1.5 ms at the C128's 2 MHz).
  Its own cost is not measured yet: 470 host instructions a call at 9.6 cycles each, plus
  Oscar64's libc, would be roughly 10,000-15,000 cycles. Against that, `doname()` would be
  20-30% slower.
- **A message**: the engine's own part of `pline()` is small (`vpline`, `update_topl` and
  `eos`, about 11 such accesses a call). The host's `pline()` time is mostly the tty window
  port, which our port replaces. Oscar64's `vsprintf` and our window port's copy add about
  2-3 tests a character, and a resident caller's format string is read far. That makes about
  2,000 cycles, **2 ms at 1 MHz, for a message of 40 characters**.
- A turn is 1-1.8 s at 1 MHz (RAM-PLAN.md, "the estimate"), so names and messages cost a few
  thousandths of it. Even an inventory of 30 items costs about 90 ms more.
- **The speed doesn't decide against the range tag; the size is its real cost.**

### Built (2026-11-21)

Far characters are in the far-spaces fork as commit 11 (`patches/far-spaces/0011-*`), and the
runtime that pages every far space from the REU is `tools/bank/farrt.py`. Both are checked on
the C128 in x128 (`docs/data/farrt-c128-2026-11-21.txt`). How it differs from the design above:

- **One mechanism on both machines.** The character space is another far space, paged from the
  REU through the cache like the typed ones, chosen by the pointer's value rather than by type.
  The bank-1 access of the C128 note (above) is left for later: the compiler translates a
  pointer and then uses it as a near one, and a bank-1 byte can't be reached that way.
- **The compiler.** `#pragma farchars(n)` makes a one-byte integer type answer far space n in
  `Declaration::FarSpace()`. So a byte reached through a pointer is translated like a typed
  space's, while struct fields keep their struct's space and locals and near globals stay near.
  - The space's routines (`farxlN`, `farxoN`) return an address outside its pages as it is.
  - A volatile byte is hardware's, and is left alone.
  - `#pragma farchars(off)` (a compiler option bit) gives the functions defined after it plain
    addresses. An inlined function takes its caller's setting.
  - A pointer leaving the character space gives no warning 2026, since its address still tells;
    a typed space's pointer entering it still warns.
- **Objects keep to a page.** Every object of a section in the character space is placed so that
  it doesn't cross a page (`LOBJF_NEVER_CROSS`, `Linker::AddObject`), at no cost in alignment.
  - So a built-in `strcpy`, `memcpy` or `memset` within one object is translated once, and no
    page-straddling routines are needed (the review's chunked copies).
  - With a character space, `MapLateIntrinsics()` leaves `memcpy()` calls alone.
- **The literals.** `#pragma strings(code, farchars)` sends the literals written under the
  `code` section, those of resident code and of file scope, to the character space's section.
  Banked code's stay in its bank.
- **The library.** With `-dOSCAR_FARCHARS`, the assembler `strcpy`, `strcmp`, `memcpy` and
  `memset` translate each pointer once, through the program's `farxzc` (declared in `string.h`
  as a C function, as `crt.c` declares `main`). The C routines are translated byte by byte.
  - These routines also translate plain addresses passed from `farchars(off)` code. So hardware
    code (the C64's bitmap clear) copies with its own loops.
- **The names.** `nh_farcopy()` (in `farrt.py`) is `farchars(off)` and goes through the name
  space's own table a page at a time. A name pointer at `$E000` and above is never reached by
  the byte test.
- **The whole game.** `build_c64.py --far --far-chars` (`c64conf.h`'s `NH_FAR_CHARS`: space 6
  at `$C100-$FBFF`, bank 138) makes `bankgen.py`'s C128 regions above the window code-only.
  `far_meas.c` gives the measurement build the space's routines.
  - The first whole-game link waits for the desktop: the compile needs 12.7 GB, more than this
    machine has free.
- **Speed and size.** A far byte in the cache costs about 11.6 cycles more than a tested near
  one in the spike's loop.
  - Per-file code grows 6-13% in string-heavy files (`pline.c`, `hacklib.c`), as estimated.
  - The five-byte `farxzN` lost a pointer's carry in a loop (`while (s[n]) n++` became `INC P0`
    alone before the call): `RemoveSimpleLoopUnusedIndex()` didn't count the zero-page operand
    of such a call as read. Fixed in the fork's commit 13 (the page form, `farxlN`, is 11
    bytes a site). `farrt.py` gives the compiler `farxzN` again; `--no-xz` leaves it out.
  - The whole game: `build_c64.py --far-runtime` writes the runtime from the headers' own
    pragmas (`farrt.py --from-headers`, six spaces) in place of `far_meas.c`. With
    `--target c128` the 4 KB of cache frames go to `$0B00-$1AFF` (low RAM that the KERNAL's
    disk routines leave alone, as bss: they need no clearing). `--io-out` leaves the I/O out by
    default (`bankgen.py --io-out`, `tests/spikes/bankreu128.c -dIO_OUT` 14/14), so one code
    region runs `$C000-$FBFF`. The bank call routine and the runtime, which switch the I/O in,
    stay below `$8000` (section `nhio`).
- **Found on the way:** an upstream optimiser bug that reads a field from the next object of a
  list (`docs/OSCAR64-COMPAT.md` row 81, r78), fixed in the fork's commit 12, which joined
  the pin as commits 86-87 (2026-11-22).

## Accepted (2026-11-27)

The C128 game plays with far characters as revised above: the character space in RAM bank 1
at `$C100-$FBFF` (fc50, `docs/data/bankplan-2026-11-26-c128fc50.json`, `char_space`). Jolyon
accepted it as built on 2026-11-27 (`docs/TO-DECIDE.md`, Decided). The C64 has no second RAM
bank, so its layout is a separate design, made with the C64's squeeze.
