# ADR-0009: Far data as typed far spaces in the compiler

- Status: proposed (for Jolyon)
- Date: 2026-11-16
- Deciders: Jolyon (+ Claude, who proposes it)

## Context
NetHack reaches about 155-170 KB of data through plain pointers, 62-77 KB of it mutable,
and a C64 shows the CPU 34-55 KB (RAM-PLAN.md). Jolyon chose far data in the compiler
(option 1, 2026-11-15). Measured since (RAM-PLAN.md):
- a far access through an REU page cache: 20.9 cycles on a hit, translated in place in zero
  page; a clean fault 603 cycles with a C handler (`tests/spikes/fardata.c`, VICE);
- a turn touches 28-31 KB of far data, 38-41 KB over ten turns (`tools/measure/trace/`);
- on NetHack's own code, with every access through a far pointer translated and every page in
  RAM: `mfndpos` 4% slower with `mons[]` far, 13% with `mons[]` and the heap far, about 70
  translations a call of which most are of pointers that do not change
  (`tools/measure/speed/farify.py`, `calibrate.py --far`);
- the game itself, before far data: about 0.8-0.9 s a turn of NetHack's own code for the
  bot's crowded level 1 after the `#ifdef C64` speed changes (T2.10).

Two forms were compared. **3-byte far pointers** (bank, page, offset) reach any data but
make every far pointer half as big again: the object and monster grids 6.7 -> 10 KB,
`struct monst` and `struct obj` a few bytes each, three bytes moved and compared in every list
walk, the save layout, and every pointer operation in the compiler. **Typed far spaces** keep
pointers at 16 bits: the type of the pointer says which space it is an address in.

## Decision (proposed)
1. **Typed spaces.** A struct type (or a constant table) can be declared far; a pointer to a
   far type is a 16-bit address in that type's own space (up to 64 KB: `mons[]` 21 KB,
   `objects[]` 11 KB, a level's monsters and objects a few KB). Before each access through
   such a pointer the compiler translates it through the space's table of pages, in place, as
   the spike's hit path does. Comparisons, `ptr - mons` and `&mons[PM_X]` need no translation.
2. **Identity window.** Every space's table maps the pages of near RAM to themselves, so a
   near object of a far type (`youmonst`, a local copy, a static) is a valid far pointer.
3. **Conversions.** A far pointer converted to `void *`/`genericptr_t` or `char *` is
   translated (the near pointer is valid while its page is pinned, below); a pointer that
   comes from an allocator is far by construction: `newmonst()`, `newobj()` and the like
   allocate from the type's space (C64 macros in `monst.h`/`obj.h`).
4. **Reuse and pinning.** The compiler translates a pointer once a function when it does not
   change there, once a loop step when it does; pages translated by a function stay pinned
   until it returns (the fault handler does not evict them). Estimated to take `mfndpos`'s
   far cost from 13% to about 4-5%.
5. **Cache.** REU pages under a CLOCK policy, 64 RAM pages (16 KB) to start; the fault
   handler in assembler (about 350 cycles). The cache sits behind one interface, so that a
   C128's second bank, or a disk on a stock C64, could back it instead.
6. **What goes far is decided per type, by measurement**: `mons[]`, `objects[]` and the heap
   first; the level and vision grids stay near while RAM allows.

## Consequences
- Easier: NetHack's source and data layouts stay as they are; saves keep their format; the
  gcc host build is untouched (the qualifier is empty there).
- Harder: compiler work in Oscar64 (a type qualifier, translation at loads and stores through
  qualified pointers, reuse, pinning, conversions, diagnostics for what it cannot do), plus
  the allocators and the fault handler in the runtime. Pointer arithmetic that leaves an
  object, and code that keeps a translated `char *` past a page's pinning, must be found and
  handled: the far build's checksum oracle (`farify.py`) is the first check.
- Open: strings (37.7 KB of literals reached as `char *`, which mixes provenance): keep them
  banked with today's trampolines, or a string space with a range test. Decided separately.
- Zero page: reused and pinned translations stay in zero page, and the game is close to the
  end of Oscar64's area already (`m_move` reaches $8B of $8F, 2026-11-16); in the experiment
  with all four types far, `mfndpos` needs $90 before any reuse (2026-11-16). Oscar64 did
  not check the end (compat #72: past it the KERNAL's IRQ changes the values); the pin now
  warns (2025), and every listing is checked (`tools/check_listing.py`). So the compiler
  work includes temporaries that do not fit: spilled to memory, not only reported.

## Evidence / how to re-check
`python3 tests/spikes/run_fardata.py`; `python3 tools/measure/trace/summary.py TURNS`;
`python3 tools/measure/speed/calibrate.py --far permonst --far monst_s --far obj_s
--far trap_s` (same checksums, cycles a call near and far).
