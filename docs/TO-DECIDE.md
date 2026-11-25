# To be decided

Questions only Jolyon can settle, kept here until he does. Each item gives the evidence,
the options and the agents' recommendation. When one is decided, move it to **Decided**
with the date and the words of the decision, and record it where it belongs (an ADR,
TASKS.md, the pin). Session notes point here rather than repeating the questions.

## Open

### A joystick, and the C128's keypad
*Raised 2026-11-25 (Jolyon: "we might need to consider joystick use").* Nothing reads a
joystick yet. It fits NetHack well: the eight stick directions are the eight moves, and a
stick's diagonals are easier than `y` `u` `b` `n`. It would only produce keys the game
already takes, so it is the port's input, not game behaviour, and needs no ADR. The choices:

- **Which port.** Port 2 (`$DC00`), the usual games port. A stick in port 1 (`$DC01`) is read
  on the keyboard's row lines, so pushing it looks like a key going down in every column of
  that row (up: DEL, 1, 3, 5, 7, 9, +, £). That is C64/C128 hardware behaviour: the KERNAL
  scan on the C64 and our scan on the C128 (`sys128.c`) would both type them. Port 2 shares
  the column lines, so a key pressed while the stick is pushed can ghost, but the stick on
  its own types nothing. Recommendation: port 2 only.
- **What the fire button does.** (a) fire held with a direction = the shifted move (`L`:
  rush), fire alone = `s` (search); (b) fire alone = `,` (pick up); (c) fire alone = RETURN,
  to page through `--More--`. Recommendation: (a), with RETURN left to the keyboard.
- **Repeat.** Holding the stick moves again after a short delay. The C128's own key scan
  does not repeat yet: a key counts once when it goes down, whereas a terminal NetHack
  repeats a held key. Whatever delay the stick gets, held keys should probably get too.
- **Related, C128 only.** The C128's keypad (on `$D02F`'s lines, not read yet) could give the
  moves as on a PC keypad, with the game's `number_pad` option left off.
- Cost: on the C128 a few hundred bytes in its HAL; on the C64 the same, from the resident
  memory we are squeezing, so the C64 could leave it out or have it later.

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

### The left-arrow key gives `_` (travel) on both machines
*Decided 2026-11-25. Jolyon: "Happy with your recommendations about the key."* Option (a):
the keyboard-buffer path no longer maps PETSCII 95 to ESC (`src/hal/sys.c`,
`src/hal/sys128.c`); RUN/STOP stays ESC. The self-test checks it (`src/main.c`, failure 9).
