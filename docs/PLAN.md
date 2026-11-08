# Plan

Long-term labour of love: full NetHack 3.4.3 on a Commodore 64. This plan
replaces the first draft (which reimplemented the game system by system)
with a **port** of the real source — see ADR-0001. The feature list from the
first draft survives as the acceptance checklist in `docs/FEATURES.md`.

Each phase has exit criteria that can be checked by running something.

## Phase 0 — Toolchain and proof of platform ✅ (2026-11-08)

- [x] Oscar64 v1.32.273 builds EasyFlash `.crt` and `.prg` targets
- [x] VICE driven headless by agents: `tools/vice.py` (keys in, screen text
      out, screenshots, memory), self-tests via the debug cartridge
- [x] KERNAL brought up from a cartridge start; keyboard works
- [x] Software 80x25 screen with NetHack's layout (msg / 80x21 map / status)
- [x] REU detected by DMA, sized (128 KB-16 MB), level stash/restore works
- [x] EasyFlash + REU together in VICE (caveats: docs/HARDWARE.md)
- [x] NetHack 3.4.3 surveyed and measured (docs/NETHACK-SURVEY.md)
- [x] K&R -> ANSI conversion automated and verified (host build plays/saves/restores)
- [x] Oscar64 gaps catalogued with repros (docs/OSCAR64-COMPAT.md)

Exit evidence: `make test` 5/5; `tools/prepare-port-tree.sh` +
`tools/host-build.sh` + `tests/host_smoke.py` all pass.

## Phase 1 — The whole game compiles with Oscar64

Goal: every file in `port/src` compiles under Oscar64 (link/placement aside).

- [ ] Commit `port/` as generated (baseline commit, so every later diff is ours)
- [ ] Add a `C64` platform config (`c64conf.h`, modelled on `pcconf.h`):
      no signals/fork/uid, our file layer, fixed options
- [ ] Work down the error classes in OSCAR64-COMPAT.md; each compiler bug gets
      a repro + workaround, each real portability issue a fix in `port/`
- [ ] Solve the `makemon.c` hang and the `mhitm.c`/`shknam.c` crashes (bisect -> repro -> upstream issue)
- [ ] `tools/check_ansi.sh` and `tests/host_smoke.py` stay green throughout

Exit: `tools/measure/measure_oscar64.py` reports 107/107 files measured;
full code-size figure replaces the estimate in NETHACK-SURVEY.md.

## Phase 2 — Memory architecture spikes (decide, don't build everything)

- [ ] Banking spike: EF execute-in-place vs REU overlays with 3 real files
      (ARCHITECTURE.md "Code: banking") -> ADR
- [ ] Partition: map OVL0/1/2/3/B + call graph to banks; trampolines for
      `trampoli.h` functions; resident set fits under `$8000`
- [ ] RAM plan for dynamic state (~45-60 KB vs 30 KB resident): what goes
      under the cart window / I/O / KERNAL; BUFSZ policy (ADR)
- [ ] REU RAM-disk file layer + dlb over compressed blobs
- [ ] Text compression measurement on `data`, `quest.dat`, `rumors`

Exit: an ADR for each choice, each backed by a measured spike in VICE.

## Phase 3 — First light: a NetHack level on the C64

- [ ] `c64` window port on `screen80` (putstr, print_glyph, nhgetch, yn,
      menus, status lines, `--More--`)
- [ ] System layer (RNG seeding, time, panic/exit)
- [ ] Boot -> character creation -> Dlvl 1 drawn, @ moves, `i` shows inventory
- [ ] AUTOTEST: scripted keys reach Dlvl 2 via `>`; VICE exit code 0

Exit: `make test` includes a "walk downstairs" test on the real game.

## Phase 4 — Whole game

- [ ] All special levels load (Sokoban, Mines, Oracle, quest, Gehennom, endgame)
- [ ] Level changes via REU RAM disk; EF-only fallback via disk
- [ ] Shops, prayer, polymorph, pets, spells, artifacts: walk FEATURES.md
- [ ] Encyclopedia, rumors, oracles, quest text through dlb
- [ ] Performance: keystroke-to-screen under ~1 s on common commands

Exit: FEATURES.md checklist ticked by scripted or manual play.

## Phase 5 — Persistence and polish

- [ ] Save/restore to disk (D64 in VICE, real 1541/SD2IEC/Ultimate drive)
- [ ] Bones files, high-score list, options file
- [ ] Help screens, `--More--` ergonomics, key mapping on the C64 keyboard
- [ ] Real hardware runs (HARDWARE.md checklist)

## Phase 6 — Distribution

- [ ] One `.crt` (+ `.d64` for saves) with a README; credits and NetHack licence
- [ ] Optional C128 VDC build; stock-C64 feasibility write-up

## Risks, in order

1. **RAM for dynamic state** (45-60 KB needed, 30 KB resident) — Phase 2.
2. **Code size vs 1 MB flash** (~0.85 MB code + data) — compression, REU.
3. **Oscar64 maturity on 130K lines** — repros, upstream issues, pinned version.
4. **EF + REU bus conflict on real hardware** — sub-type 1 on Ultimate; REU-only fallback.
5. **Speed** — NetHack waits for input; vision recalculation and level
   creation are the hot spots to profile (Oscar64 `-ep` profiler, VICE).
