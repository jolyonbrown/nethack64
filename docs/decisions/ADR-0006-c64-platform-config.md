# ADR-0006: C64 platform configuration — the host game minus Unix services

- Status: accepted
- Date: 2026-11-09
- Deciders: Jolyon (approved the T1.1 plan, 2026-11-09) + Claude Code (proposed;
  cross-checked against an independent Codex gpt-6.1-sol design)

## In short

The C64 build compiles the same game the Linux host build plays: the same
monsters, objects, levels, messages and use of the random number generator. It
leaves out only the Unix services a C64 cannot have: shell escape, suspend,
signals, user ids, lock files, Unix mail, external compression and the termcap
terminal. Nothing selects it except `-DC64`, so the host build is untouched.

## Context

- `port/` builds as Unix tty NetHack (`tools/host-build.sh`). That build is our
  behaviour oracle (`tests/host_smoke.py`). Phase 1 needs a C64 configuration
  so that Oscar64 sees NetHack configured for a C64, not for Unix (T1.1).
- Upstream's small-machine configurations (`pcconf.h`, `amiconf.h`, `tosconf.h`)
  define `MICRO`. MICRO is more than plumbing; it changes behaviour relative to
  the host build:
  - another maze walker (`mkmaze.c:651-736`): the iterative one backtracks
    differently from the recursive one, and a model of both over 20,000 seeds
    gave different 80x21 mazes for ~31% of seeds;
  - no panic save (`end.c:268-290`, `files.c:808-827`);
  - per-name score limits (`topten.c:40`);
  - `color` on by default (`options.c:72-76`);
  - no DEC/IBM graphics (`tcap.h:10-19`);
  - keyboard polling during occupations (`allmain.c:324-350`);
  - 8.3 save names (`files.c:767-789`).
  It would also need extra Oscar64 workarounds: `patchlev.h` via
  SHORT_FILENAMES (`global.h:233-237`), and `gotoxy`/`kbhit` clash with
  Oscar64's `conio.h`.
- Oscar64 has no `-U`, and `-tm=c128` does not define `__C64__`. Detecting the
  platform from the compiler would silently turn the UNIX-config measurement
  (the 2026-11-08 baseline) into a C64 one.
- AGENTS.md: behaviour changes (cutting features, shrinking buffers, changing
  RNG use) need an ADR first.

## Decision

1. **Selection.** Explicit `-DC64` (gcc) or `-dC64` (Oscar64), never
   auto-detected. When C64 is defined, `config1.h` undefines UNIX and sets
   UNWIDENED_PROTOTYPES (ADR-0005). Both settings have to come before the
   `*conf.h` stage, because tradstdc.h and `global.h:87` read them first.
   `global.h` then includes `c64conf.h` after the other platform headers. C64
   names this platform layer, not the machine: a C128 build would define it
   too. `-dC64` defines it empty, so test it only with `#ifdef` or `defined()`.
2. **Host parity.** Where `#ifdef UNIX` chooses game behaviour rather than an
   OS service, the code also tests C64:
   - `rnd.c:11`: the `RND(x) = Rand() % x` formula;
   - `hacklib.c:452`: seeding with `srand48`;
   - `eat.c:1402`: the apple/pear message and its `rnd(100)`;
   - `files.c:2116`: `check_recordfile()` creates the score file `record`
     when it is missing, as every other port does. Without this its body is
     empty under C64, and `topten()` then prints "Cannot open record file!"
     and never keeps a score (`topten.c:361-368`). Added 2026-11-10, after
     review.

   `files.c:1475` and `files.c:2031` take the non-Unix lookup of the config and
   wizkit files, because the Unix branch uses buffers that are declared only
   under UNIX/VMS.
3. **Compiled out (platform plumbing, no gameplay):** signals (`NO_SIGNAL`),
   the shell escape, suspend and job control, external compress, termcap and
   `TTY_GRAPHICS` (the Phase 3 `c64` window port replaces it), user ids
   (`getuid()` is 1), lock files, Unix mail delivery and `system.h`.
4. **Kept as on the host:**
   - MAIL and TEXTCOLOR, re-stated in `c64conf.h` because they came from
     `unixconf.h`. Dropping MAIL would renumber `pm.h` and `onames.h`;
   - WIZARD, NEWS, LOGFILE, PANICLOG and INSURANCE;
   - every gameplay switch;
   - the DECgraphics and IBMgraphics options (TERMLIB/ASCIIGRAPH);
   - TEXT_TOMBSTONE;
   - all buffer sizes. `FILENAME` is `PL_NSIZ + 13`, so `SAVEF` keeps the
     host's 45 bytes.
5. **RNG contract:** `Rand()` is `lrand48()`, seeded by
   `srand48((long) time)`, exactly as on the host. `c64conf.h` declares both
   functions; the Phase 3 system layer implements them. Which generator
   implements them, and the seed and clock source, are for a later ADR, due
   before Phase 3 first light. `RANDOM` is not used: it would switch the game
   to `random()` and to a 16-bit `srandom((unsigned) time)` seed.
6. **Save format:** INTERNAL_COMP is on (RLECOMP + ZEROCOMP), as on every
   non-Unix port. It is lossless and changes only the save, level and bones
   file formats (VERSION_FEATURES bits 27 and 28).
7. **System-layer interface:** `c64conf.h` does not declare file descriptor
   I/O, `errno`, `time_t`/`struct tm`, `getenv`, `qsort`, `fseek` or the
   like. That interface belongs to the Phase 2 file layer and the Phase 3
   system layer; until then `tools/measure/c64meas-c64.h` stands in for it in
   measurements.

## Consequences

**What differs from the host build.** A `gcc -E` diff of every `port/src`
file, UNIX view against C64 view, keeping each file's own lines, finds
differences in 15 files. All of them are platform plumbing:

- **Commands:** `!` (shell) and ^Z (suspend) are gone (`cmd.c`). There are no
  SIGINT/SIGHUP/SIGQUIT handlers and no hang-up save (`allmain.c`, `end.c`,
  `save.c`), no end-of-input handling on stdin (`cmd.c`), and no terminal
  interrupt toggling (`pager.c`).
- **Wizard mode:** no "Dump core?" prompt, and no `abort()` on panic
  (`end.c`).
- **Files:** the config file is `NetHack.cnf` through the generic lookup.
  A config or wizkit file that cannot be opened is skipped silently: there is
  no setuid `access()` check, and none of the host's "Couldn't open ... file"
  messages (`files.c:1448-1469`, `1523-1536`, `2007-2027`, `2051-2057`).
  There are no lock files (`files.c`, `decl.c`) and no external compression
  (`files.c`). Saves, levels and bones go through the ZEROCOMP buffering
  (`save.c`, `restore.c`, `bones.c`).
- **tty only:**
  - the TERM-based graphics auto-detect is gone (`options.c`);
  - `msg_window` and `extmenu` become config-file no-ops;
  - the extended-command menu is gone (`cmd.c`);
  - `has_color()` becomes TRUE in `mapglyph.c`, so the window port decides;
  - the tty window procs are gone (`windows.c`).
- **Scores:** the uid is 1 for everyone, so the limit of 3 entries per role
  (PERSMAX) applies to the whole machine (`topten.c`).
- **Timing:** no `sleep(1)` in `shk.c`.
- **Mail:** in normal play no mail ever arrives, because `mustgetmail` stays
  -1. Mail scrolls from wishes or bones (`spe` 1) show the same fixed message
  on both builds (`read.c:642`). Only a scroll dropped by a killed mail daemon
  (`spe` 0), which only wizard mode can create, reaches `readmail()`. There
  the C64 shows a junk line (one `rn2`, `mail.c:452`) where the host would run
  `$MAILREADER`.
- **`mklev.c`:** only the argument cast of `qsort` differs.

**What does not differ:**
- `objects[]` and `mons[]`: a `makedefs -DC64` gives byte-identical `pm.h`,
  `onames.h`, `vis_tab.*` and `monstr.c`;
- struct sizes under Oscar64;
- buffer sizes;
- the sequence of RNG calls in normal play.

**Watch:**
- `-DC64` must reach every tool that should see the C64 configuration.
  Oscar64 fails loudly without it (`system.h` wants `<sys/types.h>`); gcc
  silently gives the UNIX view.
- `makedefs -DC64` output that differs from the host's:
  - `date.h`: VERSION_FEATURES `0x181e0cc6` and VERSION_ID "C64 NetHack";
  - `dat/options`, the `#version` text: it drops data file compression,
    shell, suspend, terminal info and tty graphics, and adds zero-compressed
    save files. It lists no window system yet still says "with a default of
    tty".

  The C64 build needs both from a C64 `makedefs` before it saves anything or
  shows `#version` (Phase 3). `pm.h`, `onames.h`, `vis_tab.*` and `monstr.c`
  can stay shared. The c64 window port must add itself to makedefs'
  `window_opts` and set DEFAULT_WINDOW_SYS.
- `host_smoke` never runs the ZEROCOMP/RLECOMP save code, because the host
  uses COMPRESS. A COMPRESS-off host variant is needed before Phase 5 saves.
- Host tools built with `-DC64` against glibc: in flex output
  (`lev_lex.c`, `dgn_lex.c`), `#define getuid() 1` collides with
  `<unistd.h>`. A C64-config `lev_comp`/`dgn_comp` (Phase 4) needs a guard.
- The recursive `walkfrom` (`mkmaze.c:702`) nests about 260 calls deep on an
  80x21 maze, too deep for the 6502 stack. Phase 4 needs an explicit-stack
  version that is identical seed for seed to the host's, not MICRO's walker.
- Seed-for-seed parity also needs a `qsort` with the host's tie order
  (`mklev.c` `do_comp` ties on equal `lx`).

**Open, each for its own ADR:**
- the RNG generator, seed width and clock source. `night()`/`midnight()`,
  moon phase and Friday 13th all read the clock;
- feature cuts, if space forces them (MAIL, NEWS, WIZARD, ...);
- score keeping, per uid or per name;
- an occupation interrupt key (RUN/STOP).

## Evidence / how to re-check

Measured 2026-11-09 with gcc 13.3.0 and Oscar64 v1.32.273, on branch
`task/T1.1-c64conf`. Rechecked 2026-11-10 after the two reviews (Codex and
Claude), which added the `check_recordfile` edit and the `dat/options`,
bones and config-file points.

- **The UNIX build is unchanged.**
  - Extract the master tree with `git archive master port`. For every
    `port/src` file, the util tools, `sys/unix` and `win/tty`, take
    `gcc -E -P` and sorted `gcc -E -dM` under the check_ansi, host-build and
    util flag sets: 354 combinations, all identical. With `-DC64`, all 354
    macro sets change.
  - Run `tools/host-build.sh` on master and on the branch. Once both use the
    same `date.h` timestamp, all 126 objects are identical after
    `objcopy --strip-debug`, and `nethack`, `makedefs`, `lev_comp`,
    `dgn_comp` and `recover` are identical after
    `strip -s -R .note.gnu.build-id`.
  - `tests/host_smoke.py`: 4/4 ok. `tools/check_ansi.sh`: 107 clean.
- **What Oscar64 sees.**
  - `tests/c64conf_probe.c` includes the measurement shim (for `time_t`),
    `hack.h` and `tcap.h`. It `#error`s if a Unix-only option such as UNIX,
    MICRO, COMPRESS, TTY_GRAPHICS, SHELL, SUSPEND, RANDOM or TERMINFO is
    defined, if an expected one such as C64, UNWIDENED_PROTOTYPES,
    NO_SIGNAL, MAIL, TEXTCOLOR, WIZARD, ZEROCOMP, RLECOMP or ASCIIGRAPH is
    missing, or if `FILENAME != 45`. The command is in its header; it
    gives 0 errors and emulation result 0.
  - A gcc type-check of all 107 files against Oscar64's own headers, with
    `-DC64` and the measurement shim, passes 107/107. Without the `files.c`
    edit it fails at `files.c:1505` ('envp' undeclared).
- **Parity:** the `gcc -E` diff described under Consequences. The only RNG
  call in it is the wizard-only `mail.c:452`.
- **Measurement:**
  `python3 tools/measure/measure_oscar64.py --config c64`, recorded in
  NETHACK-SURVEY.md (2026-11-09 section).
