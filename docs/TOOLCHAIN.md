# Toolchain

| Tool | Version verified | Role | Install |
|---|---|---|---|
| Oscar64 | v1.32.273 plus `tools/oscar64-upstream/patches/pin/` (ADR-0007) | the C compiler for everything on the C64 | built from source by `tools/setup-*.sh`: `oscar64` is the patched compiler, `oscar64-plain` the release |
| VICE | 3.7.1 verified; 3.10 is current | emulator: `x64sc` (C64), `x128` | Arch: `pacman -S vice`; Ubuntu: `apt install vice` + ROMs (see below) |
| xvfb-run | any | headless VICE for agents/CI | Arch: `xorg-server-xvfb`; Ubuntu: `xvfb` |
| Python 3 | 3.10+ | all tools; `pexpect` for the host smoke test | |
| gcc, make, ncurses, bison, flex | any recent | host build of NetHack and its generators | |
| cc65 | 2.19 | comparison/measurement only (not used to build) | Arch: AUR `cc65`; Ubuntu: `apt install cc65` |

## Install

```sh
tools/setup-arch.sh        # Arch / Omarchy
tools/setup-ubuntu.sh      # Debian/Ubuntu, CI, cloud sandboxes
export PATH=$HOME/.local/bin:$PATH
make && make test
```

Why pinned: every compatibility finding and every byte count in `docs/`
was taken with v1.32.273 or with the patched compiler built on it. The
patches are silent wrong-code fixes (ADR-0007): since 2026-11-13 the setup
scripts build v1.32.273 plus `tools/oscar64-upstream/patches/pin/` with
`tools/oscar64-upstream/build-pin.sh` and link it as `oscar64`, and link the
plain release as `oscar64-plain` for comparisons (`OSCAR64_PLAIN=1` makes the
release the default instead; `JOBS=N` sets `make -jN`). Our C64 program
compiles to the same bytes with both (2026-11-13). Upgrade deliberately: a
new release needs the patch stack re-checked against it, then `make repros`,
`make test` and `tools/measure/measure_oscar64.py`; record what changed in
`docs/OSCAR64-COMPAT.md` and ADR-0007, then commit the bump.

Oscar64 finds its own headers relative to the real path of the binary, so a
symlink in `~/.local/bin` is fine. It has no separate link step: list every
`.c` on one command line (the Makefile does).

## VICE notes

- Debian/Ubuntu ship VICE as `+dfsg` without the C64 ROMs; `setup-ubuntu.sh`
  sparse-checks-out `vice/data/{C64,C128,DRIVES}` from the VICE GitHub mirror
  and copies them into `/usr/share/vice/`. Arch's package includes them.
- Options this project relies on (all in 3.7.1):
  `-cartcrt`, `-reu -reusize N`, `-debugcart` (write to `$D7FF` = exit code),
  `-limitcycles`, `-exitscreenshot`, `-warp`, `-binarymonitor` (`ip4://127.0.0.1:6502`),
  `-autostartprgmode 1` (inject .prg into RAM), `-default` (ignore user config).
- The binary monitor's `keymatrix` command needs VICE 3.11+; we type through
  the KERNAL keyboard buffer instead (`keyboard feed`, 3.5+), which is why
  `src/hal/sys.c` reads keys with KERNAL `GETIN`.
- Wayland/Hyprland: the GTK `x64sc` runs under XWayland fine; for agent runs
  prefer `--headless` (xvfb) so windows do not steal focus. `vice-sdl2` is an
  alternative package.

## Editor

Neovim + clangd works on `src/` if you give clangd the Oscar64 include path;
generate `compile_flags.txt` with:

```sh
printf -- '-I%s\n' src build/gen "$(dirname "$(readlink -f "$(command -v oscar64)")")/../include" \
  > compile_flags.txt
```

(clangd will still complain about Oscar64 extensions like `__asm` blocks and
`#pragma region`; that is expected.)
