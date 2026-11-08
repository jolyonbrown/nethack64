---
description: Build the C64 program, boot it in headless VICE, drive it with keys and read the 80-column screen as text. Use whenever you need to see or test behaviour on the C64.
argument-hint: "[crt|prg] [reu-KB] [keys...]"
---

# Run it on the C64 (VICE)

1. Build: `make` (EasyFlash `.crt`) or `make prg`. Fix any compiler error first.
2. Quick automated check: `make test` — must print `5/5 passed`. If a case fails,
   its exit code names the check (see `tests/run_selftests.py`), and
   `build/test-<case>.png` shows the final screen: Read it.
3. Interactive look (default: cart + 512 KB REU):
   ```sh
   python3 tools/vice.py launch --crt build/nethack-ef.crt --reu 512 --headless --warp
   python3 tools/vice.py screen            # 80x25 as text (label s80_text from build/*.lbl)
   python3 tools/vice.py keys "llljj"      # vi-keys; \n = RETURN
   python3 tools/vice.py screen
   python3 tools/vice.py screenshot build/shot.png   # only when colour/pixels matter
   python3 tools/vice.py quit              # ALWAYS, or port 6502 stays busy
   ```
   For a `.prg`: `--prg build/nethack.prg`. Several builds in build/? pass `--lbl build/<name>.lbl`.
4. Report what you saw as text (paste the relevant screen rows), not "it worked".

Arguments: $ARGUMENTS (e.g. `prg 0 lljj` = prg build, no REU, then type lljj).

If VICE will not start: `x64sc -version` (installed?), ROMs present (docs/TOOLCHAIN.md),
port 6502 free (`tools/vice.py quit`, or `VICE_PORT=6503`).
