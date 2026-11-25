# To be decided

Questions only Jolyon can settle, kept here until he does. Each item gives the evidence,
the options and the agents' recommendation. When one is decided, move it to **Decided**
with the date and the words of the decision, and record it where it belongs (an ADR,
TASKS.md, the pin). Session notes point here rather than repeating the questions.

## Open

### The left-arrow key: ESC or `_` (travel)?
*Raised 2026-11-24 (Claude), playing the C128 build.*

- The keyboard-buffer path maps PETSCII 95, the left-arrow key, to ESC
  (`src/hal/sys.c` and `src/hal/sys128.c`, `key_from[]`, there since the scaffold).
- On the C64, `_` can only be typed as the left-arrow key, so travel (`_`) can't be typed at
  all. The C128's matrix scan (`sys128.c`, `keys_plain[]`) already gives `_` for it, so the
  two machines disagree.
- RUN/STOP is ESC on both, so the left arrow being ESC as well is not needed for ESC.
- Options: (a) the left arrow gives `_` on both (`key_to[]` 27 → `'_'`); (b) leave it as ESC
  and give travel another key; (c) leave it.
- Recommendation: (a). It matches the C128's scan, keeps ESC on RUN/STOP, and is where the
  C64's keyboard puts `_`. It is a key mapping, not game behaviour, so no ADR is needed.

### Pin additions: r86, r87, r89, #95, #96, #97, #99
*Raised 2026-11-23 (Claude); #99 added 2026-11-24.* Compiler fixes that the far-spaces fork
has and the pin (`tools/oscar64-upstream/patches/pin/`, ADR-0007) does not. r86 and r87, #95
and #96 are upstream Oscar64's own fixes; r89, #97 and #99 are ours. #99 (r92, fork commit
28) is the one that made the C128's screen black: the pin and upstream miscompile it too.
#98 is a bug in the far fork's own code, so it goes with the fork, not the pin. Details: `docs/OSCAR64-COMPAT.md`.

### Rebase the far-spaces fork on current upstream?
*Raised 2026-11-23 (Claude).* The fork is upstream Oscar64 to 2026-08-20 plus our 28
commits; upstream has 213 more, which already fix #95 and #96. A rebase would pick up their
fixes but means re-running `make check` and the whole-game link.

### Codex reviews: the packet, or wait for the sandbox fix?
*Raised 2026-11-23 (Claude).* With `-s read-only`, Codex now runs commands unsandboxed here
because bubblewrap still can't start. It wrote `docs/sessions/2026-11-23-codex.md` (left
untracked) and `build/review-splits-*`. Keep the self-contained packet reviews, or wait for
the AppArmor/bubblewrap fix?

### The clock and seeding (T2.7, what is left)
*Open since 2026-11-15.* The generator is settled (bit-exact `lrand48`, `src/hal/rng.c`). The
seed width and the clock source are not, and nor are the moon phase, Friday the 13th and
`night()`/`midnight()`. For now `time()` is fixed, so every game starts the same: useful for
replays and testing, but not true to the game. Changing that is game behaviour, so it needs
an ADR.

## Decided

(None yet.)
