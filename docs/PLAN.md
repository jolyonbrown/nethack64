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

## Phase 1 — The whole game compiles with Oscar64 ✅ (2026-11-14, C64 config)

Goal: every file in `port/src` compiles under Oscar64 (link/placement aside).

- [x] Commit `port/` as generated (baseline commit, so every later diff is ours) — `daa1621`, 2026-11-08
- [x] Add a `C64` platform config (`c64conf.h`, modelled on `pcconf.h`):
      no signals/fork/uid — 2026-11-09, ADR-0006 (the file layer and fixed
      options come with T2.4 and the Phase 3 system layer)
- [x] Work down the error classes in OSCAR64-COMPAT.md; each compiler bug gets
      a repro + workaround, each real portability issue a fix in `port/` — 2026-11-14:
      59 repros; fixes in the ADR-0007 compiler (59 commits) or workarounds in `port/`;
      2026-11-15: 65 repros, the compiler at 73 commits, all 108 C64 files compile;
      2026-11-16: 71 repros, 78 commits (a zero-page warning, two copy-loop fixes)
- [x] Solve the `makemon.c` hang and the `mhitm.c`/`shknam.c` crashes (bisect -> repro -> upstream issue)
      — fixed in the ADR-0007 compiler (r27, r28 and the exponential walks)
- [x] `tools/check_ansi.sh` and `tests/host_smoke.py` stay green throughout (and CI checks both)

Exit: `tools/measure/measure_oscar64.py` reports 107/107 files measured;
full code-size figure replaces the estimate in NETHACK-SURVEY.md.
Met 2026-11-14 under the C64 config: 108/108 files (with the generated `monstr.c`) compile
to placement, 106 place code (`dlb.c` and `vis_tab.c` hold none there), 1,252,234 B in all,
which replaces the estimate. Still open from this phase's work: the wrong-code rows T1.15,
T1.18 and T1.19, and the UNIX reference config's last 11 files. Corrected the same night:
with `__noinline` stubs the code is ≈ 1.19 MB, and `mhitm.c` aborts the compiler (T1.45), so
107/108 until that is fixed.

## Phase 2 — Memory architecture spikes (decide, don't build everything)

- [ ] Banking spike: EF execute-in-place vs REU overlays with 3 real files
      (ARCHITECTURE.md "Code: banking") -> ADR
- [ ] Partition: map OVL0/1/2/3/B + call graph to banks; trampolines for
      `trampoli.h` functions; resident set fits under `$8000`
      — 2026-11-15: the whole game's code and literals fit 103 banks of 16 KB (a plan from
      its own sizes, BANKING-SPIKE.md); with the linker's bank call stubs (in the pin since
      2026-11-15, T2.9) the resident code is 65 KB, not 156 KB. Resident data, 155 KB, is next.
- [ ] RAM plan for dynamic state (~45-60 KB vs 30 KB resident): what goes
      under the cart window / I/O / KERNAL; BUFSZ policy (ADR)
      — 2026-11-15 (RAM-PLAN.md): the data needs far pointers; Jolyon chose to explore far
      data in the compiler. Measured: a far access, the working set a turn (28-31 KB), and
      the game's speed before any of it (about 1.8 s a turn for the bot's crowded level 1;
      far data would add 15-30%). Next: the far-data design ADR.
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
- [ ] Long games by a NetHack-playing AI agent (Jolyon's suggestion, 2026-11-13: one
      such agent has reportedly ascended), driving VICE through `tools/vice.py`; and the
      same games recorded on the host build and replayed seed for seed on the C64 build,
      where any screen that differs is a port bug (needs T2.7's exact RNG). Model:
      Antithesis's deterministic NetHack fuzzer (blog "Beating the frontier on
      NetHack", 2026-11-13, on 3.6.x; harness not released): one seeded RNG, runs
      branched from saved states (VICE snapshots here), inputs limited to keys valid
      at the prompt, a score over depth/XP/coverage to steer, crashes and assertions
      as the oracle. It reports a path to victory within 5 minutes on nearly 80% of
      seeds, and real bugs found on the way

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
2. **Code size vs 1 MB flash** (~1.2 MB code, measured 2026-11-14, + data) — compression, REU (docs/BANKING-SPIKE.md).
3. **Oscar64 maturity on 130K lines** — repros, upstream issues, pinned version.
   Not only compile errors: r18 (2026-11-10) is silent wrong code, so game
   code needs run-time checks, not just a clean compile. By 2026-11-13, 22 of
   the 45 repros are silent wrong code, most of them found while reviewing
   fixes for others, and each round of review has found more; one (r45) is exposed
   by an upstream fix the pin carries. Pinned: v1.32.273 plus the commits
   ADR-0007 lists (eight accepted 2026-11-12, more added since); the build uses it
   since 2026-11-13 (T1.20).
4. **EF + REU bus conflict on real hardware** — sub-type 1 on Ultimate; REU-only fallback.
5. **Speed** — NetHack waits for input; vision recalculation and level
   creation are the hot spots to profile (Oscar64 `-ep` profiler, VICE).
