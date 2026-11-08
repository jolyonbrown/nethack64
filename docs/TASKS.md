# Tasks — next up

Small, verifiable tasks for the next sessions. Take the top unclaimed one,
put your agent name and date next to it, tick it when its check passes.
Add new tasks at the bottom of the right section.

## Setup (first session on a new machine)

- [ ] T0.1 Run `tools/setup-arch.sh` (or `setup-ubuntu.sh`), then `make && make test` → 5/5 PASS
- [ ] T0.2 `make repros` → 11 repros, all BROKEN on v1.32.273 (baseline)
- [x] T0.3 Commit the bundle — github.com/jolyonbrown/nethack64 (old 2020 import kept as tag `upstream-3.4.3`), 2026-11-08 Claude
- [x] T0.4 `make port-tree`, `tools/host-build.sh`, `tests/host_smoke.py` → all ok;
      `port/` committed as the baseline, 2026-11-08 Claude

## Phase 1 — compile everything

- [ ] T1.1 Create `port/include/c64conf.h` + hook in `global.h`/`config1.h` (model:
      `pcconf.h`). Define away signals, fork, uids, `TTY_GRAPHICS`; pick
      options off by default (MAIL, NEWS, SHELL, SUSPEND, COMPRESS, WIZARD?).
      Check: host build still works with `UNIX` (the C64 config is opt-in).
- [ ] T1.2 Re-run `python3 tools/measure/measure_oscar64.py` with the C64 config; record
      the new baseline in NETHACK-SURVEY.md (dated section).
- [ ] T1.3 Error class "Term starts with invalid token 'else'": find the macro,
      repro or fix, re-measure.
- [ ] T1.4 Error class "Pointer expected" (column 227): reduce one instance to a repro.
- [ ] T1.5 "Undefined variable type" for incomplete extern arrays: repro.
- [ ] T1.6 `makemon.c` compiler hang, `mhitm.c` abort, `shknam.c` segfault: bisect by
      deleting functions until each compiles; repro; upstream issue.
- [ ] T1.7 Parenthesise the nested `?:` sites (r2) — list them with a grep first.
- [ ] T1.8 Const-correctness fixes (`const anything *`) in `port/`.
- [ ] T1.9 File upstream Oscar64 issues for r1-r10 (one per issue, repro attached);
      record issue numbers in OSCAR64-COMPAT.md.

## Phase 2 — spikes (after Phase 1 is mostly green)

- [ ] T2.1 Banking spike A (EF execute-in-place, trampolines) with hack.c + apply.c + zap.c
- [ ] T2.2 Banking spike B (REU overlays) with the same files
- [ ] T2.3 RAM map for dynamic state; BUFSZ policy ADR
- [ ] T2.4 REU RAM-disk file layer with an AUTOTEST
- [ ] T2.5 Compress `data`/`quest.dat`/`rumors` three ways; table of ratios + decode speed

## Housekeeping

- [ ] H1 CI green on GitHub Actions (`.github/workflows/ci.yml`)
- [ ] H2 Decide repo visibility/licensing note (NetHack GPL-like licence applies to port/)
