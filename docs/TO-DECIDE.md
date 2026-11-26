# To be decided

Questions only Jolyon can settle, kept here until he does. Each item gives the evidence,
the options and the agents' recommendation. When one is decided, move it to **Decided**
with the date and the words of the decision, and record it where it belongs (an ADR,
TASKS.md, the pin). Session notes point here rather than repeating the questions.

## Open

### The joystick's fire button, and holding the stick
*Raised 2026-11-25; built 2026-11-26 as recommended, open for Jolyon to change.* The C128's
stick in port 2 (`src/hal/sys128.c`) works as follows:
- fire held with a direction gives the shifted (rush) move, `L`;
- fire on its own gives `s` (search) when it is let go without a move;
- each push counts once, with no repeat.

The alternatives for fire alone were `,` (pick up) or RETURN. Repeat is left out on purpose:
a stick held up-left repeats `y`, and `y` answers "Really attack?" when the hero walks into a
peaceful monster or a shopkeeper. Rush (fire + direction) covers distance instead. The C128's
own keys don't repeat either (a key counts once when it goes down), unlike a terminal
NetHack; that could change, with the same caveat.

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

### The joystick in port 2, and the C128's keypad
*Decided 2026-11-26. Jolyon: "port 2 was a common setup for a lot of c64 games, happy to go
with that"; "the c128 numeric keypad is a good shout indeed for that machine".* Built in
`src/hal/sys128.c` for the C128:
- the stick in port 2 gives the eight moves;
- the keypad gives the moves as on a PC keypad, 5 searching, whatever the game's `number_pad`;
- the C128's ESC key is ESC, HELP is `?`, and the cursor keys above the keypad are moves;
- the keyboard is not scanned while the stick is pushed, so a key held then doesn't ghost.

The self-test checks the decoding (failure 9). The keypad and the separate cursor keys were
also pressed in x128 through a virtual display and moved the hero. The stick could not be
driven in this VICE (3.7.1): neither its monitor's joyport command nor its keypad-as-joystick
changed what `$DC00` reads, even for a five-line test program. So the stick on real hardware,
or in a VICE window with a stick in port 2, is still to be seen. The C64 gets the stick later,
if its resident memory allows.

### Pin additions: r86, r87, r89, #95, #96, #97, #99
*Decided 2026-11-26. Jolyon: "compiler fixes i'm happy with whatever you recommend".* All
seven joined the pin as commits 88-99 (ADR-0007), with a test for each that has a small one.
The far-spaces series moved onto pin 99 (22 commits, the same compiler sources as before).

### Rebasing the far-spaces fork on current upstream: not now
*Decided 2026-11-26 on the same words, as recommended.* The C128 game is linked with the fork
as it is. A rebase onto upstream's 213 newer commits means porting the pin's 99 commits and
the series' 22 onto a moved code base, a new `make check` and corpus run, and a whole-game
relink, with new optimiser code that may bring new bugs of its own. For now, upstream fixes
are taken one at a time when the game hits their bug, as #91, #95 and #96 were. The rebase
goes with the upstream work at the end of the port, when it has to be done anyway.

### The left-arrow key gives `_` (travel) on both machines
*Decided 2026-11-25. Jolyon: "Happy with your recommendations about the key."* Option (a):
the keyboard-buffer path no longer maps PETSCII 95 to ESC (`src/hal/sys.c`,
`src/hal/sys128.c`); RUN/STOP stays ESC. The self-test checks it (`src/main.c`, failure 9).
