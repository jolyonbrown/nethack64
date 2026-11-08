# 2026-11-08 — bootstrap (Claude, claude.ai session)

## Changed
- Created the repository: Phase 0 platform code (`src/`), tools, tests, docs.
- Replaced the Sept 2026 "rebuild the game system by system" plan with a port
  of the real source (ADR-0001).

## Verified
- Oscar64 v1.32.273 built from source; VICE 3.7.1 (Ubuntu + ROMs from the
  VICE mirror), headless via xvfb.
- `make test`: prg, prg+REU 512K, EF, EF+REU 512K, EF+REU 16M — 5/5 PASS.
- `tools/vice.py`: launch, keys, screen (text), screenshot, mem, regs, quit — used live.
- `make port-tree`: 4 manual + 2,458 automatic ANSI conversions; `check_ansi`
  clean on 107 files; host build plays/saves/restores (`tests/host_smoke.py`).
- `make repros`: 11/11 Oscar64 repros reproduce on v1.32.273.

## Measured
- Oscar64 code = 0.53 x cc65 on 18 common files; whole game est. ~0.85 MB code.
- `dlevel_t` 16.8 KB, `obj` 48 B, `monst` 80 B, `mons[]` 21 KB, `objects[]` 11 KB.
- Static content ~1.7 MB; dynamic state ~45-60 KB vs 30 KB resident RAM.
- Oscar64 compiles 36/107 files after normalisation (220 KB of code measured);
  68 stop on errors, `mhitm.c`/`shknam.c` crash it, `makemon.c` hangs it.

## Repository
- Pushed to github.com/jolyonbrown/nethack64 (default branch `master`). The 2020
  "Initial commit" was an exact copy of NetHack 3.4.3 and is tagged `upstream-3.4.3`;
  the scaffold and the converted `port/` baseline are separate commits on top.

## Next
- TASKS.md T0.1-T0.2 on Jolyon's machine (toolchain + `make test`), then T1.1 (C64 platform config).

## Questions for Jolyon
- No Ultimate or real REU yet (Jolyon, 2026-11-08): VICE is the only target until one is bought.
- Oscar64 upstream issues: Jolyon is deciding.
- CI runs on GitHub Actions from the first push; check the first run.
