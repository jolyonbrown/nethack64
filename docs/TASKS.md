# Tasks — next up

Small, verifiable tasks for the next sessions. Take the top unclaimed one,
put your agent name and date next to it, tick it when its check passes.
Add new tasks at the bottom of the right section.

## Setup (first session on a new machine)

- [x] T0.1 Run `tools/setup-arch.sh` (or `setup-ubuntu.sh`), then `make && make test` → 5/5 PASS
      — 2026-11-09 Claude (toolchain already installed and checked instead: Oscar64 v1.32.273, VICE 3.7.1, gcc 13.3)
- [x] T0.2 `make repros` → 11 repros, all BROKEN on v1.32.273 (baseline) — 2026-11-09 Claude
      (r12-r14 added since: 14, all BROKEN)
- [x] T0.3 Commit the bundle — github.com/jolyonbrown/nethack64 (old 2020 import kept as tag `upstream-3.4.3`), 2026-11-08 Claude
- [x] T0.4 `make port-tree`, `tools/host-build.sh`, `tests/host_smoke.py` → all ok;
      `port/` committed as the baseline, 2026-11-08 Claude

## Phase 1 — compile everything

- [x] T1.1 Create `port/include/c64conf.h` + hook in `global.h`/`config1.h` (model:
      `pcconf.h`). Define away signals, fork, uids, `TTY_GRAPHICS`; compile out the
      Unix-only services (SHELL, SUSPEND, COMPRESS); keep MAIL, NEWS, WIZARD and every
      gameplay option (cutting any of them is an ADR).
      Check: host build still works with `UNIX` (the C64 config is opt-in).
      — 2026-11-09 Claude, ADR-0006 (not MICRO; host-parity RNG and messages)
- [x] T1.2 Re-run `python3 tools/measure/measure_oscar64.py` with the C64 config; record
      the new baseline in NETHACK-SURVEY.md (dated section). — 2026-11-09 Claude:
      `--config c64` 41 placed / 63 error / 2 crash / 1 hang (UNIX 36/68/2/1)
- [ ] T1.3 Error class "Term starts with invalid token 'else'": find the macro,
      repro or fix, re-measure.
- [ ] T1.4 Error class "Pointer expected" (column 227): reduce one instance to a repro.
- [x] T1.5 "Undefined variable type" for incomplete extern arrays: repro. — 2026-11-09 Claude:
      not a compiler gap; the defining file is missing from the harness (compiles when
      present). Harness fix in T1.10.
- [ ] T1.6 `makemon.c` compiler hang, `mhitm.c` abort, `shknam.c` segfault: bisect by
      deleting functions until each compiles; repro; upstream issue.
- [ ] T1.7 Parenthesise the nested `?:` sites (r2) — list them with a grep first.
- [ ] T1.8 Const-correctness fixes (`const anything *`) in `port/`.
- [ ] T1.9 File upstream Oscar64 issues for r1-r10 (one per issue, repro attached);
      record issue numbers in OSCAR64-COMPAT.md. (Now also r12-r14.)
- [ ] T1.10 Measurement harness fixes, then re-measure both configs and re-baseline both:
      find definitions in preprocessed text (`files.c` `close()`, `mon.c` `impossible(`,
      duplicate stubs in `cmd.c`/`end.c`/`mkmaze.c`); variadic stubs with a `va_start` body
      (r14); definitions for referenced extern arrays (error 3010); count files that compile
      without referenced code (`dlb.c`, `mkmap.c`, data tables) as compiled, not as errors.
- [ ] T1.11 `files.c` (C64 config) segfaults Oscar64 at `-Os` once `close()` is stubbed
      (`-O0` places it): bisect by deleting functions; repro; upstream issue.
- [ ] T1.12 Work around r12 (`decl.c` `occtxt = DUMMY` → `= 0`) and r13 (`mail.c`
      `junk[]` → `const char *`) in `port/`; check_ansi + host_smoke; re-measure.

## Phase 2 — spikes (after Phase 1 is mostly green)

- [ ] T2.1 Banking spike A (EF execute-in-place, trampolines) with hack.c + apply.c + zap.c
- [ ] T2.2 Banking spike B (REU overlays) with the same files
- [ ] T2.3 RAM map for dynamic state; BUFSZ policy ADR
- [ ] T2.4 REU RAM-disk file layer with an AUTOTEST
- [ ] T2.5 Compress `data`/`quest.dat`/`rumors` three ways; table of ratios + decode speed
- [ ] T2.6 Host build variant with `COMPRESS` off, so `host_smoke` exercises the
      RLECOMP/ZEROCOMP save code the C64 uses (ADR-0006); before Phase 5 saves
- [ ] T2.7 RNG + clock ADR before Phase 3 first light: which generator implements
      `lrand48`/`srand48` (exact, for seed-for-seed replays vs the host, or faster), seed
      width, clock source for seeding, moon phase, Friday 13th and `night()`/`midnight()`

## Housekeeping

- [x] H1 CI green on GitHub Actions (`.github/workflows/ci.yml`) — first run on master
      green (run 42530155008, 2026-11-08), checked 2026-11-09 Claude
- [ ] H2 Decide repo visibility/licensing note (NetHack GPL-like licence applies to port/)
