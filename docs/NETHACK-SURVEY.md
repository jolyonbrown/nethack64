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

**Correction (2026-11-14):** the harness's stubs let Oscar64 delete every call to an
empty stub and drop arguments nothing read, so the Oscar64 numbers above are about a
quarter too low (cc65 compiles each file on its own, so its numbers were not affected).
With stubs that read their parameters the same 18 files are 120,243 B (9.1 B/line, 0.71
of cc65), and the 52 files both compilers build (45,697 lines) give 8.1 B/line against
cc65's 10.7 (0.76): **Oscar64 ≈ 1.0 MB** for the whole game (±20%). Details in the
section "Oscar64 compile status with stubs that read their parameters" below.

**Measured (2026-11-14, later):** with all 108 files compiling, the total is no longer an
extrapolation: **1,252,234 B** of Oscar64 `-Os` native code for `src/` under the C64
configuration (9.5 B/line over 131,999 lines), without the window port and the runtime.
The files cc65 could compile average 7.9 B/line, the other 49 10.4: the extrapolation's
sample was the easy files. See "Oscar64 compile status with 59 commits".

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

Code ~1.25 MB (measured 2026-11-14; the estimate was ~0.85) + strings ~0.17 MB + tables
~0.05 MB + levels 0.21 MB + text 0.42 MB ≈ **2.1 MB of static content** before compression. An EasyFlash is
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
- **With commits 39-40** (r46): no change; every listing is identical to the 38-commit
  compiler's.

## The host game under a waiting smoke test and AddressSanitizer (2026-11-14)

`tests/host_smoke.py` was rewritten for T1.28: after each command it types `v` and reads
up to the version line, answering --More--, menus, y/n and naming prompts on the way,
and each session must exit by itself with status 0. `tools/smoke_stress.py` runs it many
times on separate install copies, seeding the walk per cycle (the game seeds its dungeon
from the clock). `tools/host-build.sh --sanitize` builds the host game with
AddressSanitizer (recover mode) and UBSan. gcc 13.3.0, Python 3.12.4, pexpect 4.9.0;
port as at `543fcd3`.

- **What the old driver did:** it typed on a fixed 0.1 s clock, so the first --More--
  swallowed the rest of the walk (its keys only beep), the save session always ended at
  the --More-- after "Saving..." and was killed at its 15 s timeout, and in the restore
  session the `q` of `#quit` could land as quaff. It passed on strings alone.
- **CI run 43536929831 (attempt 1):** the restore session printed "Restoring save
  file..." and reached end-of-file with no timeout. The redraw and --More-- that close
  `dorecover()` never came, and no key is read during a restore, so a slow runner cannot
  explain it: the game ended inside `dorecover()` without a message. Not reproduced:
  every restore in the runs below greeted the player.
- **Plain build, 2,400 cycles** (four runs of 6 x 100). In the first run the hero died
  before the save in 20 of 600 games: 11 under a falling-rock trap the walk kept
  stepping on, one by an arrow trap, eight by small monsters (a newt, sewer rats, a
  jackal, foxes, a small mimic, something unseen). The test now plays a new game, in a
  new clock second, when that happens. With that rule, 1,800 of 1,800 passed: 26 needed
  a second game, and in 10 the hero died after the restore had been checked.
- **Sanitizer build, 900 cycles** (three runs of 6 x 50): all passed bar one, which sat
  60 s at "Call a purple-red potion:" (a goblin's potion broke by the pet; the driver
  typed `v` into the name). The driver now cancels naming prompts; the last 300, on the
  final driver, all passed. UBSan reported nothing. ASan reported three over-reads, all
  NetHack 3.4.3's own (fixed by T1.29, below), none on the restore path:
  - `savefruitchn()` (`save.c`) writes the terminating `struct fruit` (48 bytes here)
    from `nul` (40 bytes, `decl.c`): 8 bytes over at every save and checkpoint. Restore
    discards them (the terminator's `nextf`). On the C64 `struct fruit` is 36 bytes.
  - `free_window_info()` (`wintty.c`) compares with `wins[WIN_MESSAGE]` after the
    message window is destroyed, so it reads `wins[-1]`; in `done()`, at each death.
    `wintty.c` is not in the C64 build, whose window port comes in Phase 3.
  - `makeplural()` (`objnam.c`) tests `strcmp(spot-7, "shuriken")` for any name of 5
    letters or more: up to 3 bytes before the string, which can be the start of `bufs`.
    The same code runs on the C64.
- **T1.29's fixes** (same day): `nul` (`decl.c`) is sized to the longest zero record
  `save.c` writes from it: 48 bytes on the host, still 40 under Oscar64 (`struct fruit`
  36, `struct trap` 11, printed by a probe built like `struct_sizes.c`). The C64 assembly
  and map of `decl.c` are unchanged. `free_window_info()` checks `WIN_ERR` first.
  `makeplural()` tests "shuriken" from 8 letters and has a length guard on a fourth
  read found by reading the function, `strcmp(spot-5, "matza")` under `len >= 5`, which
  compares six characters with five and so never matches ("matza" stays "matzas").
  Old and new `makeplural()` give the same plural for 105,034 words (the dictionary and
  every string in `monst.c` and `objects.c`) under seven fills of the 4 bytes before
  the buffer. The exceptions are three: "riken", "uriken" and "huriken" after "shu",
  "sh" and "s", where those bytes decided the old answer. After the fixes the sanitizer
  build ran 300 cycles (11 with a death) with no report, and the plain build 600, all
  passed. NetHack 3.6 moved "shuriken" into a table checked through `BSTRCMPI`, compares
  "matza" at `spot-4` (a behaviour change from 3.4.3) and writes static zero structs;
  it still reads `wins[WIN_MESSAGE]` there.

## Oscar64 compile status after T1.29-T1.32 (2026-11-14, later)

Same harness and caps; the 40-commit pin, whose NetHack listings match the 38-commit
pin's, so what moved is the port: T1.29's over-read fixes, T1.30's `sizeof "literal"`
and r47's goto/else rule (port at `f060c52`). Per-file results:
`docs/data/oscar64-pin40-c64conf-2026-11-14.json` (C64) and
`docs/data/oscar64-pin40-baseline-2026-11-14.json` (UNIX).

| Result | UNIX config | C64 config |
|---|---|---|
| compile through to placement | 41 (256,261 B) | **47 (276,030 B)** |
| stop on a compile error | 66 | 60 |
| crash or hang the compiler | 0 | 0 |

- **New:** `detect.c` in both configurations (10,289 B, 22 of 25 functions placed) and,
  C64 only, `mklev.c` (9,381 B, 22 of 36). No other file's code changed: T1.29's `nul`
  and T1.30's parentheses move nothing.
- **`hack.c`** now generates 23,539 B (30 of 34 functions) and stops at "Static stack
  usage exceeds stack segment", a placement limit the harness counts as a compile error.
- **Further on, still stopped** (r47 was the first error of most): `artifact.c` 237
  ("Pointer expected"), `bones.c` (C64: `extern char bones[]`, the harness's
  extern-array gap; UNIX: `close`), `objnam.c` 891 (compat #20, r16: a function pointer
  compared with `xname`; T1.14), `pline.c` (the harness's own stub for `pline`, T1.10),
  `shk.c` and `sp_lev.c` (`mkmap` is not stubbed).
- **With r48** (parentheses at three sites, measured after this run): `pray.c` stops at
  the harness's missing stub for `pline` instead of line 790, `shk.c` at line 693
  ("Incompatible conditional types"; UNIX: `sleep`) instead of 2669. Totals unchanged.

## Oscar64 compile status with the corrected harness (2026-11-14, T1.10)

T1.10 changed how the harness builds each file's program; the compiler (the 40-commit
pin) and the port did not change. Definitions come from the preprocessed file, stubs keep
the calls a real build keeps, extern arrays are defined from the files that have them,
and every error 3034 counts as "fits-not". Harness and port at `30ac71d`. Per-file
results: `docs/data/oscar64-pin40-t110-c64conf-2026-11-14.json` (C64) and
`docs/data/oscar64-pin40-t110-baseline-2026-11-14.json` (UNIX).

| Result | UNIX config | C64 config |
|---|---|---|
| compile through to placement | 51 (313,597 B) | **61 (363,195 B)** |
| of which place no code | 3 | 3 |
| stop on a compile error | 55 | 43 |
| crash the compiler | 1 | 3 |

- **Sizes are higher, and nearer a real build's.** The files placed both before and now
  grew 4.6% (C64, 264,733 to 276,857 B) and 4.8% (UNIX). The old empty stubs of the
  variadic message functions let Oscar64 delete calls: `potion.c`'s listing held 36
  calls to `pline`, `You` and the like where it now holds 65 (18,230 to 20,811 B).
- **New in the C64 count (15):** `bones.c`, `botl.c`, `do_name.c`, `end.c`, `fountain.c`,
  `hack.c` (its static stack is a fit error), `light.c`, `mcastu.c`, `mkmaze.c`,
  `pline.c`, `rip.c`, `topten.c`, and `dlb.c`, `mkmap.c` and `vis_tab.c`, which place no
  code because the base data does not fit before their functions do.
- **Crashes (T1.11):** `files.c` and `mkobj.c` (11,297 B before the stubs changed) are
  r49, `SplitAt` on a function's exit block, fixed upstream by 46e60d6; with it cherry-
  picked onto the pin both get to placement. `questpgr.c` is r50, a `LoadStoreForwarding`
  segfault after `fopen()`, still on main 16acc53. Under UNIX only `mkobj.c` crashes.
- **Still undefined:** `SAVEF` and the generated `monstr[]` (T1.35).
- **With 42 commits** (upstream 46e60d6 and its test, the same day): `files.c` (3,894 B)
  and `mkobj.c` (11,830 B) reach placement, and every other listing, intermediate code and
  map is identical. C64 63/107 (378,919 B), UNIX 52/107 (325,427 B); `questpgr.c` (r50)
  is the one crash left. Data: `docs/data/oscar64-pin42-c64conf-2026-11-14.json` and
  `docs/data/oscar64-pin42-baseline-2026-11-14.json`.

## Oscar64 compile status with 44 commits and the full harness (2026-11-14, T1.35)

The 44-commit pin (r49's and r50's fixes) and T1.35's harness (the generated `monstr.c`,
`SAVEF` copied from `files.c`). 108 files: `monstr.c`, generated by `makedefs -m` like
`vis_tab.c` is by `-z`, is part of the game and is now counted. Port and harness at
`da9bd7c`. Data: `docs/data/oscar64-pin44-c64conf-2026-11-14.json` and
`docs/data/oscar64-pin44-baseline-2026-11-14.json`.

| Result | UNIX config | C64 config |
|---|---|---|
| compile through to placement | 55 (342,766 B) | **68 (404,323 B)** |
| of which place no code | 3 | 3 |
| stop on a compile error | 53 | 40 |
| crash the compiler | 0 | **0** |

- **New since the 42-commit data:** `makemon.c` (14,490 B), `wizard.c` (2,848 B) and
  `monstr.c` (its one function, `monstr_init`, is 1 byte) in both configurations; under C64
  also `save.c` (4,960 B) and `questpgr.c` (3,105 B, r50's fix). No file crashes the
  compiler in either configuration.
- **What stops the 40 C64 files** (first error only): "Pointer expected" 10 (`artifact`,
  `display`, `dothrow`, `dungeon`, `invent`, `mthrowu`, `pickup`, `priest`, `region`, ...);
  "Incompatible conditional types" 8 (`dog`, `mhitu`, `mon`, `muse`, `polyself`, `pray`,
  `rect`, `track`: r51's `c ? p : 0` at least in four, T1.37); "Incompatible pointer
  types" 6 (`dig`, `do_wear`, `eat`, `lock`, `objnam`, `windows`; r16 in two, T1.14);
  `const union any` assignments 5 (`apply`, `cmd`, `do`, `pager`, `spell`: compat #19);
  `static` where a declaration starts 2 (`version`, `weapon`); one each for `allmain`,
  `mail`, `mkroom`, `options`, `restore`, `shk`, `sp_lev`, `timeout`, `trap`.

## Oscar64 compile status with 47 commits (2026-11-14, later still)

The 47-commit pin: commit 45 backports upstream 160c92b (compat #7, r1: a cast applied
before its operand's `->`, `.` or `[]`), and commits 46-47 are Codex's fix and test for
r51 (`c ? p : 0`). Harness and port as for the 44-commit run. Measured with the candidate
whose tree the patch files reproduce. Data: `docs/data/oscar64-pin47-c64conf-2026-11-14.json`
and `docs/data/oscar64-pin47-baseline-2026-11-14.json`.

| Result | UNIX config | C64 config |
|---|---|---|
| compile through to placement | 67 (461,311 B) | **80 (522,868 B)** |
| of which place no code | 3 | 3 |
| stop on a compile error | 41 | 28 |
| crash the compiler | 0 | 0 |

- **New with 160c92b** (both configurations): `display.c` (16,933 B), `dothrow.c`
  (10,763 B), `mthrowu.c` (9,822 B), `region.c` (6,030 B), `priest.c` (5,742 B).
- **New with the r51 fix** (both): `mhitu.c` (21,953 B), `muse.c` (19,861 B), `polyself.c`
  (9,636 B), `pray.c` (8,825 B), `dog.c` (7,147 B), `rect.c` (1,496 B), `track.c` (337 B).
- Every file that compiled with 44 commits gives an identical listing, intermediate code
  and map.
- **What stops the 28 C64 files** (first error only): incompatible assignments 9 (`apply`,
  `artifact`, `cmd`, `do`, `dungeon`, `pager`, `pickup`, `spell`, `zap`; most of them
  compat #19's `const union any`); "Incompatible pointer types" 7 (`dig`, `do_wear`, `eat`,
  `invent`, `lock`, `objnam`, `windows`; r16 in two, T1.14); "Incompatible conditional
  types" 2 (`mon`, `timeout`); `static` where a declaration starts 2 (`version`,
  `weapon`); one each for `allmain`, `mail`, `mkroom`, `options`, `restore`, `shk`,
  `sp_lev`, `trap`.

## Oscar64 compile status with 48 commits (2026-11-14, evening)

Commit 48 is our r15 fix (compat #19: a `union T *` now converts to a `const union T *`,
which every `add_menu(..., &any, ...)` needs). Measured with the candidate whose tree the
patch files reproduce. Data: `docs/data/oscar64-pin48-c64conf-2026-11-14.json` and
`docs/data/oscar64-pin48-baseline-2026-11-14.json`.

| Result | UNIX config | C64 config |
|---|---|---|
| compile through to placement | 71 (514,789 B) | **85 (585,948 B)** |
| of which place no code | 3 | 3 |
| stop on a compile error | 37 | 23 |
| crash the compiler | 0 | 0 |

- **New:** `apply.c` (23,486 B), `dungeon.c` (12,254 B), `artifact.c` (11,545 B), `spell.c`
  (6,193 B), and under C64 `pager.c` (9,602 B). Every file that compiled with 47 commits
  gives an identical listing, intermediate code and map.
- **What stops the 23 C64 files** (first error only): "Incompatible pointer types" 8 (`cmd`,
  `dig`, `do_wear`, `eat`, `invent`, `lock`, `objnam`, `windows`; r16, the function pointer
  compared with a function, in two: T1.14); incompatible assignments 3 (`do`, `pickup`,
  `zap`); "Incompatible conditional types" 2 (`mon`, `timeout`); `static` where a
  declaration starts 2 (`version`, `weapon`); one each for `allmain`, `mail`, `mkroom`,
  `options`, `restore`, `shk`, `sp_lev`, `trap`.

## Oscar64 compile status with stubs that read their parameters (2026-11-14, night)

The same 48-commit compiler as the previous section; the harness and `port/` changed.

- **The harness under-counted every file's code.** Void stubs had empty bodies and
  the other stubs ignored their parameters, so at `-Os` Oscar64 deleted every call to an
  empty void stub, arguments and all, and dropped argument code nothing read. A
  three-call test function: 1 byte with empty stubs, 77 with stubs that read each
  parameter, 136 with stubs that take each parameter's address (which changes how the
  arguments are passed). Variadic arguments were never dropped. The stubs now read each
  parameter's value (`tools/measure/mkstubs.py`: pointers into `nh_vp`, scalars into
  `nh_vl`, typedefs followed through `hack.h`). For the 81 C64 files that place code
  with both: 566,087 B → 755,006 B (×1.33; per file ×1.00 to ×1.82, `bones.c`); UNIX
  ×1.34. The same 18 files as the 2026-11-08 comparison: 89,157 → 120,243 B.
- **Other harness gaps closed:** prototypes that `extern.h` writes without `E`
  (`flood_fill_rm`, `remove_rooms`) and functions a file declares itself (`sp_lev.c`'s
  `extern void mkmap(lev_init *)`) get stubs, with the file's own headers included for
  their types; a non-static function that no header declares (`mkmap()` in `mkmap.c`)
  is referenced, so it and the static functions it calls are kept (`mkmap.c`: 0 →
  5,068 B); and static arrays named by a copied array's initializer are copied with it
  (`shk.c`: `shtypes[]` names `shkgeneral` and nine more). `MEASURE_OUT` lets two
  compilers be measured at once.
- **`port/` works round** r12 and r13 (T1.12) and r53-r57 (compat #55-#59). `timeout.c`
  and `do.c` also met r58 (compat #60), which only the empty stubs provoked.

| Result | UNIX config | C64 config |
|---|---|---|
| compile through to placement | 86 (915,572 B) | **95 (954,832 B)** |
| of which place no code | 2 | 2 |
| stop on a compile error | 21 | 12 |
| crash the compiler | 1 | 1 |

- **New under C64:** `allmain`, `mail`, `mkroom`, `options`, `restore`, `shk`, `sp_lev`,
  `timeout`, `trap`, `version`, `weapon`. **Lost:** `muse.c` now aborts the compiler (an
  index assertion in `NativeCodeBasicBlock::BinaryAddCarry`, in `rnd_defensive_item`):
  with its calls' arguments kept, the native code generator meets a case it
  mishandles. Being reduced.
- **What stops the other 12 C64 files:** r16, a function pointer compared with a
  function, 8 (`cmd`, `dig`, `do_wear`, `eat`, `invent`, `lock`, `objnam`, `windows`);
  r17, `?:` over two functions, 2 (`do`, `pickup`); r52, `!!p`, 2 (`mon`, `zap`).
  Each has a fix among the next pin candidates (T1.43); with them `invent.c` reaches r31
  (compat #33), whose fix is a candidate too.
- **Code size, re-estimated:** over the 52 files both cc65 (2026-11-08) and Oscar64
  compile under the UNIX config, 45,697 lines: cc65 10.7 B/line, Oscar64 8.1 B/line, a
  ratio of 0.76 (0.53 on the 18 files before). At 8.0 B/line over all compiled files
  with a line count, NetHack's ~126K code-bearing lines need **≈ 1.0 MB** of Oscar64
  code (was ≈ 0.85 MB), ±20% as before.

Data: `docs/data/oscar64-pin48h-c64conf-2026-11-14.json` and
`docs/data/oscar64-pin48h-baseline-2026-11-14.json`.

## Oscar64 compile status with 59 commits (2026-11-14, night)

Commits 49-59 (ADR-0007): our r16 fix, upstream c8da6bd (r17), our fold of `!` on constants
(r53) and r52 fix (`!!x`), and Codex's fixes for r31 and r59, each with a test. Measured with
the candidate whose tree the patch files reproduce (45d5c29), harness as in the previous
section. Data: `docs/data/oscar64-pin59-c64conf-2026-11-14.json` and
`docs/data/oscar64-pin59-baseline-2026-11-14.json`.

| Result | UNIX config | C64 config |
|---|---|---|
| compile through to placement | 97 (1,185,691 B) | **108 (1,252,234 B)** |
| of which place no code | 2 | 2 |
| stop on a compile error | 11 | 0 |
| crash the compiler | 0 | 0 |

- **Every C64 file compiles** (to placement: a file with the five base files and its
  stubs does not fit one 64 KB program, which the banked build will not ask of it). New:
  `cmd`, `dig`, `do`, `do_wear`, `eat`, `invent`, `lock`, `mon`, `muse`, `objnam`,
  `pickup`, `windows`, `zap`.
- **Files that compiled with 48 commits** give identical listings, intermediate code and
  maps, except in the functions of 13 files (C64) that use `!!`, which now compute 0 or 1
  (`castmu()`'s `boolean oldprop = !!Confusion` had kept only the low byte of a `long`),
  and the intermediate code of `mapglyph()`, where r53's fold takes `!((boolean)1)` when
  parsing (same machine code).
- **The 11 UNIX files:** libc gaps that belong to a Unix system layer (`SIG_IGN` in `end`,
  `files`, `save`; `srand48`/`lrand48` in `hacklib`, `rnd`, `rumors`; `clearerr` in `cmd`),
  `wintty.h` prototypes the harness does not stub yet (`mapglyph`, `windows`), and
  Unix-only code in `allmain` (507) and `mail` (109), not looked at yet.
- **Code size, measured:** 1,252,234 B over the 106 C64 files that place code, 9.5 B/line
  of `src/`; the largest are `zap.c` 49,682, `trap.c` 48,149, `shk.c` 46,187, `apply.c`
  36,933 and `uhitm.c` 35,172. Files cc65 compiled average 7.9 B/line and the rest 10.4,
  which is why the line-count estimates (0.85, then 1.0 MB) came out low. Not included:
  the window port, the C64 runtime and libc, and string literals (counted with the data).
