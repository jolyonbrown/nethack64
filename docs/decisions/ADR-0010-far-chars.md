# ADR-0010: Far characters: byte pointers tagged by address range

- Status: proposed; on hold after review (2026-11-20, below), pending Jolyon
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

## Decision (proposed)

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

