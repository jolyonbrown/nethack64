# Plan

Long-term labour of love: full NetHack 3.4.3 on a Commodore 64. This plan
replaces the first draft (which reimplemented the game system by system)
with a **port** of the real source — see ADR-0001. The feature list from the
first draft survives as the acceptance checklist in `docs/FEATURES.md`.

Each phase has exit criteria that can be checked by running something.

**Where we are (2026-11-26):** the whole game plays on the C128 in x128 (Magic Desk 128 +
REU; first level 2026-11-23, saves and level changes 2026-11-24). Phases 2 and 3 are done
for the C128 apart from the items left open below; Phase 4's play-testing is under way.
The C64 squeeze follows (ADR-0003, amendment of 2026-11-21). The README carries the same
summary; keep the two in step.

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
      2026-11-16: 71 repros, 78 commits (a zero-page warning, two copy-loop fixes); then 72
      repros and 80 commits (T1.49: a function saves only the zero page its callers need)
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

## Phase 2 — Memory architecture spikes (decide, don't build everything) — done for the C128

- [x] Banking spike: EF execute-in-place vs REU overlays with 3 real files
      (ARCHITECTURE.md "Code: banking") -> ADR
      — ADR-0008 (accepted 2026-11-17): the banks entered most in place on the cartridge, the
      rest copied from the REU into the same window; calls go through the linker's 6-byte
      bank call stubs (T2.9)
- [x] Partition: map OVL0/1/2/3/B + call graph to banks; trampolines for
      `trampoli.h` functions; resident set fits under `$8000`
      — 2026-11-15: the whole game's code and literals fit 103 banks of 16 KB (a plan from
      its own sizes, BANKING-SPIKE.md); with the linker's bank call stubs (in the pin since
      2026-11-15, T2.9) the resident code is 65 KB, not 156 KB. Resident data, 155 KB, is next.
      — 2026-11-26: the C128 game (fc50) places every object: 137 banks, 63 on the cartridge
      and 74 in the REU (`docs/data/bankplan-2026-11-26-c128fc50.json`)
- [x] RAM plan for dynamic state (~45-60 KB vs 30 KB resident): what goes
      under the cart window / I/O / KERNAL; BUFSZ policy (ADR)
      — 2026-11-15 (RAM-PLAN.md): the data needs far pointers; Jolyon chose to explore far
      data in the compiler. Measured: a far access, the working set a turn (28-31 KB), and
      the game's speed before any of it (about 1.8 s a turn for the bot's crowded level 1;
      far data would add 15-30%). Next: the far-data design ADR.
      — Done as ADR-0009 (typed far spaces in the REU for structs and the heap, accepted
      2026-11-16) and ADR-0010 (far characters, built 2026-11-21, accepted 2026-11-27). BUFSZ
      stays 256: no game buffer was shrunk. On fc50 the near heap has 1,240 of 2,828 bytes free.
- [ ] REU RAM-disk file layer + dlb over compressed blobs
      — 2026-11-24: the RAM disk works on the C128 (`port/sys/c64/c64sys.c`): saves, and level
      files on the way down and back. Left: its AUTOTEST (T2.4), dlb and compression
- [ ] Text compression measurement on `data`, `quest.dat`, `rumors`

Exit: an ADR for each choice, each backed by a measured spike in VICE.
Met for code (ADR-0008) and data (ADR-0009, ADR-0010) by the running C128 game; text
compression is not measured yet and is needed for the C64.

## Phase 3 — First light: a NetHack level on the C64 — done on the C128 (2026-11-23)

- [x] The window port: NetHack's tty port without termcap on `screen80`
      (putstr, print_glyph, nhgetch, yn, menus, status lines, `--More--`).
      2026-11-22: `port/sys/c64/video.c`, the host's screens matched over it
      (`tests/host_video_compare.py`); the tty port compiles under Oscar64 in
      the C64 configuration and is in the bank plan; `tgetch()` and the
      terminal set-up are the system layer's
      — 2026-11-23 on the C128's VDC; 2026-11-25, fc49: its text no longer black on black (r92)
- [ ] System layer (RNG seeding, time, panic/exit)
      — the RNG is bit-exact `lrand48` (`src/hal/rng.c`); `time()` is fixed for now, so every
      game starts the same (the clock is open in `docs/TO-DECIDE.md`); the rest is T3.2
- [x] Boot -> character creation -> Dlvl 1 drawn, @ moves, `i` shows inventory
      — 2026-11-23 on the C128 (fc29-fc30, commit 9c127a4); the C64 comes with its squeeze
- [ ] AUTOTEST: scripted keys reach Dlvl 2 via `>`; VICE exit code 0
      — a recorded game replays to Dlvl 2 on every new C128 build, driven by hand-run scripts;
      not yet a `make test` case (the whole game needs the desktop's link)

Exit: `make test` includes a "walk downstairs" test on the real game.

## Phase 4 — Whole game

- [ ] All special levels load (Sokoban, Mines, Oracle, quest, Gehennom, endgame)
- [ ] Level changes via REU RAM disk; EF-only fallback via disk
      — 2026-11-24: through the RAM disk on the C128, Dlvl 1 to 2 and back as left
- [ ] Shops, prayer, polymorph, pets, spells, artifacts: walk FEATURES.md
      — played on the C128 by 2026-11-26: fighting, eating, throwing, kicking, `#force`,
      `#loot`, scrolls, potions, a fountain, a wand engraved with and zapped, prayer, the pet
- [ ] Encyclopedia, rumors, oracles, quest text through dlb
- [ ] Performance: keystroke-to-screen under ~1 s on common commands
      — 2026-11-27: the C128 game at 2 MHz (fc51), each REU DMA at 1 MHz: the first level 61.9 s
      against 80.7 s at 1 MHz, the Dlvl 2 replay 577 s against 653 s. Most of what is left is
      REU bank loads, 1,681 of 16 KB for the first level (`docs/data/speed-c128-2026-11-27.txt`)
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
      — 2026-11-24: save and restore work through the REU RAM disk on the C128 (kept across
      runs by VICE's `-reuimagerw`); a real disk is still to do
- [ ] Bones files, high-score list, options file
- [ ] Help screens, `--More--` ergonomics, key mapping on the C64 keyboard
      — 2026-11-26: the left-arrow key gives `_`, RUN/STOP is ESC; the C128's keypad, ESC and
      HELP keys and a joystick in port 2 (`docs/TO-DECIDE.md`)
- [ ] Real hardware runs (HARDWARE.md checklist)

## Phase 6 — Distribution

- [ ] One `.crt` (+ `.d64` for saves) with a README; credits and NetHack licence
- [ ] Both builds: the C128 (Magic Desk 128 + REU, the first to run the game, ADR-0003 2026-11-21) and the C64 (EasyFlash + REU); stock-C64 feasibility write-up

## Risks, in order

1. **RAM for dynamic state** (45-60 KB needed, 30 KB resident) — Phase 2. Solved on the C128
   by far data (ADR-0009, ADR-0010); the C64 has about 12 KB less near memory than that.
2. **Code size vs 1 MB flash** (~1.2 MB code, measured 2026-11-14, + data) — compression, REU (docs/BANKING-SPIKE.md).
   Solved by REU banks (ADR-0008): the C128 game uses 137 banks, 74 of them from the REU.
3. **Oscar64 maturity on 130K lines** — repros, upstream issues, pinned version.
   Not only compile errors: r18 (2026-11-10) is silent wrong code, so game
   code needs run-time checks, not just a clean compile. By 2026-11-13, 22 of
   the 45 repros are silent wrong code, most of them found while reviewing
   fixes for others, and each round of review has found more; one (r45) is exposed
   by an upstream fix the pin carries. Pinned: v1.32.273 plus the commits
   ADR-0007 lists (eight accepted 2026-11-12, more added since); the build uses it
   since 2026-11-13 (T1.20). 2026-11-26: 92 repros, the pin at 99 commits, and the
   far-spaces series 22 more; many of the later bugs were found by playing the game, not compiling it.
4. **EF + REU bus conflict on real hardware** — sub-type 1 on Ultimate; REU-only fallback.
5. **Speed** — NetHack waits for input; vision recalculation and level
   creation are the hot spots to profile (Oscar64 `-ep` profiler, VICE).
