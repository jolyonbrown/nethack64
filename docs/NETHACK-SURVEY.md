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
  (2026-11-09: the script also passed `-w`, which silences warnings even when
  `-Werror=` promotes them, so its three `-Werror=` checks could not fail; hard
  errors such as a prototype conflict still did. Without `-w` all 107 files
  still pass: the claim holds.)

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

## Oscar64 compile status under the C64 configuration (2026-11-09)

T1.1 added the C64 platform configuration (`port/include/c64conf.h`, selected
with `-dC64`; ADR-0006). `tools/measure/measure_oscar64.py --config c64`
measures the tree under it:
- Oscar64 gets only `-dC64 -dregister=`;
- `stub/` supplies only `errno.h`;
- `tools/measure/c64meas-c64.h` stands in for the Phase 2/3 file and system
  layers (time, file descriptors, `errno`, `getenv`, `qsort`, `fseek`).

Tools: Oscar64 v1.32.273, gcc 13.3.0; port and harness at `7812bf8`. Per-file
results are in `docs/data/oscar64-c64conf-2026-11-09.json`. Re-run 2026-11-10
at `16b7ca7`, after the review fixes (uncommitted edits: comments only): both
configurations reproduce their recorded files, 0 of 107 records differ in
each (`tools/measure/compare_reports.py`).

| Result | UNIX config (baseline) | C64 config |
|---|---|---|
| compile through to placement | 36 (220,535 B) | **41 (230,622 B)** |
| stop on a compile error | 68 | 63 |
| crash the compiler (`mhitm.c`, `shknam.c`) | 2 | 2 |
| hang the compiler (`makemon.c`, killed after 150 s) | 1 | 1 |

- **Control:** the default `--config unix` run on the same tree reproduces
  `docs/data/oscar64-baseline-2026-11-08.json` record for record, struct
  sizes included (`tools/measure/compare_reports.py`: 0 of 107 records differ).
- **Unchanged:** the 36 files that placed before have identical records
  (status, code bytes, functions). Oscar64's struct sizes match the UNIX
  configuration's (the table further up).
- **17 files changed.** The last column says why:
  - *config*: the C64 configuration removed a Unix-only dependency or
    declares the interface;
  - *shim*: the C64 shim declares a system-layer function `extern`, so the
    harness stubs it (the UNIX shim's prototypes are not `extern`);
  - *harness*: a measurement artefact (T1.10);
  - *compiler*: an Oscar64 gap with a repro;
  - *port*: needs a portability fix in `port/`.

| File | UNIX first error | C64 result | Why |
|---|---|---|---|
| `hacklib.c` | `srand48` unknown | placed, 2,975 B | config + shim (RNG interface declared; `time()` stubbed) |
| `rnd.c` | `lrand48` unknown | placed, 798 B | config |
| `rumors.c` | `lrand48` unknown | placed, 2,153 B | config + shim (`fseek()`/`ftell()` stubbed) |
| `mapglyph.c` | `has_color()` (tty) | placed, 1,026 B | config (no `TTY_GRAPHICS`) |
| `u_init.c` | `time()` undefined | placed, 3,135 B | shim |
| `allmain.c` | `signal()` parse error | `decl.h(193)` 3008 Non constant initializer | config, then compiler (r12: `occtxt = DUMMY`) |
| `mail.c` | `mail.c(109)`, Unix mailbox code | `mail.c(439)` 3008 Incompatible constant initializer | config, then compiler (r13) |
| `windows.c` | `win_tty_init` (tty) | `windows.c(113)` 3013 Incompatible pointer types | config, then compiler (r16) |
| `do.c` | `close()` undefined | `do.c(688)` 3012 incompatible types | shim, then compiler (r17) |
| `pager.c` | `fseek()` undefined | `pager.c(907)` 3012 `const union any_s *` | shim, then compiler (r15) |
| `questpgr.c` | `fseek()` undefined | `questpgr.c(95)` 3017 Too many arguments | shim, then harness (r14) |
| `topten.c` | `getuid()` undefined | `topten.c(854)` 3017 Too many arguments | config + shim (`rewind()`), then harness (r14) |
| `files.c` | `SIG_IGN` | `close()` not stubbed | config + shim (`creat()`), then harness; with a `close()` stub Oscar64 segfaults at `-Os` (T1.11) |
| `save.c` | `SIG_IGN` | `decl.h(22)` 3010 `SAVEF` | config + shim (`close()`), then harness (the array is defined in `files.c`) |
| `end.c` | `SIG_IGN` | duplicate stub `panic` | config, then harness |
| `cmd.c` | `clearerr` | duplicate stub `get_adjacent_loc` | config, then harness |
| `mkmaze.c` | duplicate stub `waterbody_name` | the same, at another line | harness |

The configuration alone places `rnd.c` and `mapglyph.c` (1,824 B).
`hacklib.c` and `rumors.c` (5,128 B) need both the configuration and the shim;
`u_init.c` (3,135 B) needs only the shim. Checked 2026-11-10 by dropping
`extern` from the shim's `time`, `localtime`, `creat`, `close`, `fseek`,
`ftell` and `rewind`: then only `rnd.c` and `mapglyph.c` place, and
`topten.c`, `save.c` and `files.c` stop on `rewind()`, `close()` and
`creat()`. (The first version of this section, 2026-11-09, credited the
configuration with four of the five.)

**Caveats:**
- Sizes are lower bounds. They depend on the harness's stub bodies and are
  comparable only within one harness version.
- These first errors are harness artefacts in both configurations. The fix is
  T1.10, which re-measures both configurations together:
  - definitions found by a regex on raw source: `files.c` `close()`
    (a compiled-out wrapper), `mon.c` `impossible(`, and the duplicate stubs
    in `cmd.c`, `end.c` and `mkmaze.c`;
  - empty variadic stubs (error 3017: `fountain.c`, `questpgr.c`,
    `topten.c`; repro r14). The stubs need a body with a side effect; with
    `nh_vl = 0;` a scratch harness (2026-11-10) places `fountain.c`
    (4,909 B, both configurations) and `topten.c` (7,929 B, C64), and
    `questpgr.c` crashes Oscar64 (T1.11);
  - arrays defined in files outside the harness (error 3010: `botl.c`,
    `do_name.c`, `light.c`, `mcastu.c`, `rip.c`, `save.c`, `wizard.c`).
    These are not a compiler gap: with the defining file in the program they
    compile;
  - five files that compile but have no referenced code, counted as
    compile-error ("Cannot place"): `dlb.c` (DLB off), `mkmap.c` (its
    `extern.h` prototypes lack `E`, so the harness references nothing), and
    the tables `monst.c`, `objects.c` and `vis_tab.c`.
- Measurement only: nothing here links or runs, and the shim is not the
  system layer.

## Oscar64 compile status with the ADR-0007 compiler (2026-11-13)

The build switched to the patched compiler (ADR-0007; T1.20). Both configurations
measured again with it, `tools/measure/measure_oscar64.py` with and without
`--config c64`. Tools: the pin (`~/src/oscar64-pin`, tree 7de21ef), gcc 13.3.0; port
and harness at `5b0d9a7`. Per-file results: `docs/data/oscar64-pin-baseline-2026-11-13.json`
(UNIX) and `docs/data/oscar64-pin-c64conf-2026-11-13.json` (C64).

| Result | UNIX config | C64 config |
|---|---|---|
| compile through to placement | 39 (241,280 B) | **44 (251,667 B)** |
| stop on a compile error | 66 | 61 |
| crash the compiler (`shknam.c`, SIGSEGV) | 1 | 1 |
| hang the compiler (`makemon.c`, killed after 150 s) | 1 | 1 |

- **New in both, `mhitm.c`:** the release still runs out of memory on it today
  (`compiler-oom` under the 3 GB cap, compat #30); the pin's runaway fix lets it through.
- **New in both, `monst.c` and `objects.c`:** a counting artefact. They are data
  tables whose arrays place under neither compiler ("Could not place object
  'mons'"); the pin places their one small function, so the harness now counts them
  as compiling (T1.10 wants data-only files counted that way anyway).
- **Sizes are not exactly repeatable** without a zero-filled compiler heap:
  `potion.c` places 22 of 24 functions (16,137 B) in this run and 23 (18,227 B) with
  the heap zeroed; `teleport.c` is 11 bytes shorter here, the frame push that #40
  loses. The bytecode comparison (FITTING-TOOLBOX.md #15) used the zeroed heap.

## Oscar64 compile status with the 28-commit pin (2026-11-13, later)

Twenty more commits joined the pin (ADR-0007, T1.25): crash and hang fixes, the heap
initialisation and five wrong-code fixes. Same harness and caps (3,000 MB, 600 s per
file); the compiler built by `build-pin.sh` from the 28 patch files (tree 229e43f), gcc
13.3.0; port and harness as at `c9a4cf6`. Per-file results:
`docs/data/oscar64-pin28-baseline-2026-11-13.json` (UNIX) and
`docs/data/oscar64-pin28-c64conf-2026-11-13.json` (C64).

| Result | UNIX config | C64 config |
|---|---|---|
| compile through to placement | 40 (245,962 B) | **45 (256,349 B)** |
| stop on a compile error | 67 | 62 |
| crash or hang the compiler | 0 | 0 |

- **`shknam.c`** now compiles (2,578 B, 3 of 7 functions placed); **`makemon.c`** stops
  at a known compile error (an `extern` array without a size) instead of hanging.
- **Code changes in three files that compiled before**, the same in both
  configurations: `teleport.c` +11 B and `potion.c` one more function (18,227 B), both
  what the eight-commit pin gave only with its heap zeroed (#40: the frame push is
  kept); `mkobj.c` +3 B, `weight()` reading `obj->otyp` again after its recursive loop
  (#41).
- **Repeatable now:** with every heap block filled with 0xA5 before use, the C64 run
  gives byte-identical listings, intermediate code and maps for the 90 files that reach
  code generation, and the same report.
- **With commits 29-32** (r42, r43; 2026-11-14) one file changes, in both
  configurations: `vision.c` +3 B, `vision_reset()`'s narrowing masks. C64 45 files,
  256,352 B; UNIX 40, 245,965 B.
- **With commits 33-38** (r45, r37, r44; 2026-11-14): four functions change, all from
  r44's fix: `make_hallucinated()` (`potion.c` +3 B), `rigid_role_checks()` (`role.c` +4 B)
  and, C64 only, `getrumor()` (`rumors.c` +1 B). C64 45 files, 256,360 B; UNIX 40,
  245,972 B. Data: `docs/data/oscar64-pin38-c64conf-2026-11-14.json` and
  `docs/data/oscar64-pin38-baseline-2026-11-14.json`.
