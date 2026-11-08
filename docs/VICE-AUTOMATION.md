# Driving VICE from agents

The goal: an agent can build, boot, play, look and assert without a human
watching the emulator.

## Three levels

1. **Self-test builds (`make test`)** — compile with `-dAUTOTEST`; the program
   runs scripted checks and writes a result byte to `$D7FF`. With
   `-debugcart`, VICE exits with that byte as its exit status. `-limitcycles`
   turns hangs into exit status 1; `-exitscreenshot` saves the final screen.
   `tests/run_selftests.py` runs the matrix (prg/EF x no REU/512 KB/16 MB).
   Cheap, deterministic, CI-friendly. Add a numbered failure code per check.

2. **Interactive driving (`tools/vice.py`)** — launch once, then send keys and
   read state over the binary monitor:

   ```sh
   tools/vice.py launch --crt build/nethack-ef.crt --reu 512 --headless --warp
   tools/vice.py keys "llljj"           # PETSCII into the KERNAL keyboard buffer
   tools/vice.py screen                  # 80x25 text, read from the s80_text label
   tools/vice.py wait-text "staircase" --timeout 10
   tools/vice.py screenshot build/shot.png
   tools/vice.py mem 0xcc00 40           # colour matrix row 0
   tools/vice.py regs
   tools/vice.py quit
   ```

   `screen` finds `s80_text` in the newest `build/*.lbl` (Oscar64 writes VICE
   label files) — pass `--lbl` when several builds exist. Because the game's
   screen has a text shadow, agents read the screen as text instead of
   squinting at screenshots. `--text40` reads the normal `$0400` screen.

3. **Human-in-the-loop** — `make run` opens a VICE window; the binary monitor
   can still be enabled (`tools/vice.py launch` without `--headless`), so an
   agent can type into the same emulator you are watching.

## Protocol facts (VICE >= 3.5, API version 2)

Request: `02 02 <len:u32> <reqid:u32> <cmd:u8> <body>`;
response: `02 02 <len:u32> <type:u8> <err:u8> <reqid:u32> <body>`; events
(stopped/resumed/checkpoint) arrive with reqid `0xFFFFFFFF`. Every command
stops the emulation; send `exit` (0xAA) to resume — `vice.py` does that after
each command unless `--stay-paused`. Commands used: memory get/set (0x01/0x02),
registers (0x31/0x83), keyboard feed (0x72), display get (0x84), palette (0x91),
autostart (0xDD), reset (0xCC), quit (0xBB). Specification: VICE manual,
chapter "Binary monitor" (`doc/vice.texi` in the VICE sources).

## Gotchas

- One VICE per port. Use `--port`/`VICE_PORT` to run several in parallel.
- `keys` feeds the KERNAL buffer in chunks of 8 (it holds 10); programs that
  scan the keyboard matrix directly will not see these keys — another reason
  `src/hal` uses KERNAL `GETIN`.
- Writes to `$D7FF` without `-debugcart` hit a VIC-II mirror register on real
  hardware; only AUTOTEST builds do that.
- Oscar64 labels are prefixed with `.` in `.lbl` files; `vice.py` strips it.
- `-default` (on by default in `vice.py launch`) ignores your personal vicerc
  so runs are reproducible.
