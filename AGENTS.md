# AGENTS.md — NetHack 3.4.3 for the Commodore 64

Shared instructions for every coding agent on this repo (Claude Code reads
this through `CLAUDE.md`; Codex reads it directly). Keep it short and true.
Details live in `docs/`.

## What we are building

The real NetHack 3.4.3, compiled from its own C source, running on a
Commodore 64. Primary target: **EasyFlash cartridge + REU** (VICE and the
Ultimate family / C64 Ultimate). Fallbacks: C128, then (stretch) stock C64.
We **port**, we do not rewrite: game logic stays NetHack's code. Our work is
making it fit: compiler compatibility, banking, memory, I/O, an 80-column
window port.

Read before any substantial change: `docs/PLAN.md` (where we are),
`docs/ARCHITECTURE.md` (how it fits), `docs/TASKS.md` (what is next).

## Repo map

| Path | What |
|---|---|
| `src/` | C64 platform code (Oscar64). `src/hal/` = hardware layer: KERNAL bring-up, keyboard, REU, soft 80-column screen |
| `upstream/` | Pristine NetHack 3.4.3 tarball + extracted read-only tree. **Never edit.** |
| `port/` | The NetHack source we modify (created by `make port-tree`, then committed and hand-edited) |
| `tools/` | Converters, VICE driver (`vice.py`), measurement harness, setup scripts |
| `tests/` | VICE self-tests, Oscar64 compatibility repros, host smoke test |
| `docs/` | Plan, architecture, hardware notes, findings, decisions (`docs/decisions/`) |

## Commands

```sh
make                 # EasyFlash cartridge -> build/nethack-ef.crt
make prg             # plain .prg (fast iteration)
make test            # headless VICE self-tests across prg/EF x REU sizes (must stay green)
make run             # VICE window, cart + 512KB REU
make repros          # which Oscar64 compatibility repros are still broken
make port-tree       # regenerate port/ from upstream (refuses if port/ exists)
tools/check_ansi.sh  # port/ is ANSI-clean and prototypes match (gcc)
tools/host-build.sh && tests/host_smoke.py   # port/ still plays/saves/restores as Linux NetHack
python3 tools/measure/measure_oscar64.py     # per-file Oscar64 compile status + code size
python3 tools/vice.py --help                 # drive a running VICE (keys, screen text, screenshots)
```

## The verification loop (do this, every change)

1. Build: `make` (and `make prg` if you touched `src/`).
2. Self-test: `make test`. Exit codes: 0 pass, 1 hung, 2+ numbered failure.
3. Look at it: `tools/vice.py launch --crt build/nethack-ef.crt --reu 512 --headless --warp`,
   then `tools/vice.py keys "..."`, `tools/vice.py screen` (80x25 **as text**),
   `tools/vice.py screenshot build/shot.png` if layout/colour matters. `tools/vice.py quit` when done.
4. If you touched `port/`: `tools/check_ansi.sh`, `tools/host-build.sh`, `tests/host_smoke.py`.
5. Memory: `make memmap` — note any growth of the resident region in your summary.

Never claim something works on the C64 without running it in VICE.
VICE passing is necessary, not sufficient: real-hardware caveats are in `docs/HARDWARE.md`.

## Ground rules

- **Oscar64 is the compiler** (pinned: v1.32.273 plus the wrong-code fixes in
  `tools/oscar64-upstream/patches/pin/`, ADR-0007; `oscar64-plain` is the
  release). It has known gaps with 1990s C; see `docs/OSCAR64-COMPAT.md`.
  When you hit a new one: reduce it to a tiny file in `tests/oscar64-repros/`
  (header says expected vs actual and the workaround), add the workaround, note
  it in the compat doc. Do not silently rewrite game code around a compiler bug.
- `upstream/` is read-only reference. All game changes go in `port/` and must
  stay buildable by gcc (host build) as well as Oscar64.
- Prefer mechanical, scripted transforms (in `tools/`) over hand edits for
  anything that touches many files; keep them idempotent and re-runnable.
- Behaviour changes to the game (cutting features, shrinking buffers, changing
  RNG use) need a decision record in `docs/decisions/` first.
- Code density beats speed (`-Os`); NetHack waits for input anyway.
- Run Oscar64 on NetHack files under a memory cap, `(ulimit -v 3000000; ...)`: some
  of its bugs make it grow without bound (compat #30). The measurement harness and
  `make repros` cap their own compiles.
- Stop only processes you started, by PID. A `pkill -f` pattern also matches other
  agents' compiles: on 2026-11-12 one interrupted a measurement run, which then
  reported a compiler crash.
- Never read `$DF00-$DFFF` and never use EasyFlash's 256-byte RAM: that I/O
  page is shared with the REU (see `docs/HARDWARE.md`).
- Keep `make test` green. Add an AUTOTEST check for anything new in `src/`.
- Comments explain *why* (hardware quirks, compiler workarounds), not what.
- British or American spelling — either, consistently within a file.

## Recording what you learn

- Measured facts → `docs/NETHACK-SURVEY.md` or `docs/OSCAR64-COMPAT.md` (with date + tool versions).
- Decisions → new `docs/decisions/ADR-NNNN-*.md` from `docs/decisions/TEMPLATE.md`.
- Progress → tick `docs/TASKS.md`; phase status → `docs/PLAN.md`.
- End each working session with a short handoff note in `docs/sessions/YYYY-MM-DD-<agent>.md`:
  what changed, what was verified (commands + results), what is next, open questions.
- Story-worthy moments (a milestone, a surprise, a hard-won fix) → an entry in the
  development diary, `docs/diary/` (conventions in its README). Entries become public
  blog posts: facts checkable, failures told too, no time estimates. Jolyon reviews
  each entry before anything is published.

## Working with the other agent

Claude Code leads implementation; Codex is used for independent review and
second opinions (see `docs/AGENT-WORKFLOW.md`). When reviewing, check claims
against the code and by running the commands above, not by reading summaries.
