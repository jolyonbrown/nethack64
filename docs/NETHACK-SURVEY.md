# NetHack 3.4.3 source survey — measured facts

Everything here was measured on 2026-11-08 with Oscar64 v1.32.273, cc65 2.19,
VICE 3.7.1, gcc 13 (Ubuntu 24.04). Raw numbers: `docs/data/measurements-2026-11-08.json`.
Re-measure with `tools/measure/measure_oscar64.py` as `port/` changes, and add
a dated section rather than overwriting this one.

## Size of the thing

| Part | Files | Lines |
|---|---|---|
| `src/*.c` (game) | 106 (+ generated `vis_tab.c`, `monstr.c`) | 134,313 |
| `include/*.h` | 93 (many platform-specific) | 18,360 |
| `util/` (host tools: makedefs, lev_comp, dgn_comp, dlb) | | 7,707 |
| `win/tty/` (reference window port) | 4 | 4,548 |

Source tarball: `upstream/nethack_3.4.3.orig.tar.gz`, sha256
`bb39c3d2a9ee2df4a0c8fdde708fbc63740853a7608d2f4c560b488124866fe4`
(Ubuntu's orig tarball = upstream `nethack-343-src.tgz` contents).

## Language: K&R C — the first, unavoidable porting step

- Every function (2,352 in `src/`, 2,458 including `win/tty/`) uses a K&R
  definition, paired with ANSI prototypes in `extern.h` built from the
  `FDECL/NDECL` macros and the `CHAR_P/XCHAR_P/BOOLEAN_P` widening scheme.
- **Oscar64 rejects K&R definitions outright** (by design; it targets C99).
- **cc65 accepts K&R in general but rejects NetHack's pattern**: a K&R
  definition with `char`/`xchar`/`boolean` parameters against a prototype is
  "conflicting types" under both widened and unwidened prototypes.
- So the ANSI conversion is needed whichever compiler is used. It is done by
  `tools/ansi_manual_fixes.py` (4 functions whose parameter list is chosen by
  `#if`: `topologize`, `collect_obj_classes`, `query_classes`, `savelev`) then
  `tools/kr2ansi.py` (everything else).
- Build with `UNWIDENED_PROTOTYPES` so prototypes use the narrow types the
  definitions now declare — smaller, faster 6502 code too.
- **Verified**: `tools/check_ansi.sh` (gcc `-Werror=old-style-definition
  -Werror=implicit-function-declaration`, unwidened prototypes, so any type
  mismatch with `extern.h` is an error) passes on all 107 files (106 + `vis_tab.c`), and the
  converted tree builds as Linux tty NetHack that plays, saves and restores a
  game (`tests/host_smoke.py`).

## It was built for small machines once already

- 52 source files carry `#ifdef OVL0 / OVL1 / OVL2 / OVL3 / OVLB` blocks
  (75 / 72 / 27 / 19 / 136 blocks): the 16-bit MS-DOS overlay build's split of
  each file by call frequency. OVL0 = hottest, OVLB = rarely called. That is a
  ready-made first cut for which code is resident vs banked.
- `sys/msdos/schema1.BC` .. `schema3.BC` are Borland overlay schemas assigning
  each split to an overlay. schema1 notes: ~490 KB for the executable plus
  overlay buffer and ~70 KB malloc on a 16-bit x86 — the closest historical
  data point to what we are doing.
- `include/trampoli.h` (169 entries) lists every function that is called
  through a pointer (command table, callbacks). Under overlays/banking each of
  these needs a trampoline in always-resident memory. Same list applies to us.
- 16-bit `int` is supported (the DOS builds used it). `long` is used where 32
  bits matter (gold, turn counter, etc.).

## Stack pressure

- 308 local buffers are declared `[BUFSZ]` (BUFSZ = 256) plus many
  `[QBUFSZ]` (128). Oscar64's default software stack is 4 KB; a deep call
  chain with several BUFSZ locals will overflow it. cc65 refuses functions
  whose locals exceed its frame limit ("Too many local variables").
- Expect to (a) raise the stack size in the resident region, (b) reduce
  BUFSZ where safe (decision record needed — it bounds message and name
  lengths), (c) move some buffers to static storage.

## Data structures as Oscar64 lays them out

Measured by compiling `tools/measure/struct_sizes.c` with Oscar64 and running
it in Oscar64's built-in emulator:

| Struct | Bytes | Notes |
|---|---|---|
| `struct rm` (one map square) | 6 | |
| `dlevel_t` (the current level: 80x21 `rm` + object/monster grids) | **16,813** | resident while playing a level |
| `struct obj` | 48 | + name/extra bytes |
| `struct monst` | 80 | + `mextra` (pet/shopkeeper/priest data) |
| `struct permonst` x 382 (`mons[]`) | 55 x 382 = 21,010 | read-only: can live in ROM/REU |
| `struct objclass` x 433 (`objects[]`) | 26 x 433 = 11,258 | partly written at run time (discoveries, shuffled descriptions) |
| `struct you` | 1,381 | |
| `struct flag` | 127 | |
| int / long / pointer | 2 / 4 / 2 | |

cc65 view of statics (59 files that compiled): `decl.c` 19.6 KB BSS + 8 KB
initialised data; `vision.c` 8.7 KB BSS; `display.c` 5.3 KB BSS.

## Code size estimate

Per-file 6502 code was measured with both compilers (harness: the file plus
stubs for everything else, opaque stub returns so calls are not folded away;
see `tools/measure/`).

| | cc65 2.19 `-O -Os` | Oscar64 `-Os` |
|---|---|---|
| 18 files compiled by both (13,262 lines) | 168,802 B (12.7 B/line) | 89,157 B (6.7 B/line) |
| ratio | 1.00 | **0.53** |

Extrapolated to the ~126K code-bearing lines of `src/` (excluding the data
tables): **cc65 ≈ 1.6 MB, Oscar64 ≈ 0.85 MB of native code** (treat as
±20%: it is a line-count extrapolation, and inlined statics move bytes
between files). The window port and runtime add a few tens of KB.

## Data that ships with the game

| Item | Bytes (uncompressed) |
|---|---|
| String literals in code (cc65 RODATA, ~1.33 B/line) | ~165 KB |
| `mons[]` + `objects[]` tables and names | ~45 KB |
| 113 compiled special levels (`*.lev`) | 213,139 |
| `data` (encyclopedia for `/` and `;`) | 209,153 |
| `quest.dat` | 103,071 |
| `rumors` | 42,816 |
| help files, oracles, etc. | ~60,000 |

## What it adds up to

Code ~0.85 MB + strings ~0.17 MB + tables ~0.05 MB + levels 0.21 MB + text
0.42 MB ≈ **1.7 MB of static content** before compression. An EasyFlash is
1 MB. That single fact drives `docs/ARCHITECTURE.md`: text and level data
must be compressed and/or live in an REU or on disk, and code must be banked.

## Oscar64 compile status of the converted tree (baseline)

After `ansi_manual_fixes` + `kr2ansi` + `oscar_normalize` (and `-dregister=`),
measured with `tools/measure/measure_oscar64.py` on `port/` (107 files =
106 + generated `vis_tab.c`):

| Result | Files |
|---|---|
| compile through to placement (code size measured: 220,535 bytes in total) | 36 |
| stop on a compile error | 68 |
| crash the compiler with no error message (`mhitm.c` abort, `shknam.c` segfault) | 2 |
| hang the compiler (`makemon.c`, killed after 150 s) | 1 |

Per-file results: `docs/data/oscar64-baseline-2026-11-08.json`. The error
classes and their status are tracked in `docs/OSCAR64-COMPAT.md`. Driving
this to 107/107 is Phase 1.
