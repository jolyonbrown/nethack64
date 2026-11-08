#!/usr/bin/env bash
# setup-arch.sh - toolchain for Arch Linux (incl. Omarchy/Hyprland desktops).
#
# Installs: VICE (extra), build deps, xvfb-run (headless VICE for agents),
# cc65 (AUR, optional), and builds Oscar64 from a pinned tag into ~/.local.
#
#   tools/setup-arch.sh            # everything
#   OSCAR64_TAG=v1.32.273 tools/setup-arch.sh
set -euo pipefail

OSCAR64_TAG=${OSCAR64_TAG:-v1.32.273}     # the version every finding in docs/ was verified against
PREFIX=${PREFIX:-$HOME/.local}

sudo pacman -S --needed --noconfirm base-devel git python python-pip vice \
  xorg-server-xvfb ncurses bison flex

# cc65 is only used for comparisons/measurements; it lives in the AUR.
if ! command -v cl65 >/dev/null; then
  if command -v yay >/dev/null; then yay -S --needed --noconfirm cc65
  elif command -v paru >/dev/null; then paru -S --needed --noconfirm cc65
  else echo "note: install cc65 from the AUR if you want the cc65 comparison builds"; fi
fi

# pexpect drives the host (Linux tty) build in tests/host_smoke.py
python3 -m pip install --user --break-system-packages pexpect 2>/dev/null || \
  echo "note: install python-pexpect (pacman) or pexpect (pip) for tests/host_smoke.py"

# Oscar64 from source, pinned
SRC=${OSCAR64_SRC:-$HOME/src/oscar64}
if [ ! -d "$SRC/.git" ]; then
  git clone https://github.com/drmortalwombat/oscar64 "$SRC"
fi
git -C "$SRC" fetch --tags --quiet
git -C "$SRC" checkout --quiet "$OSCAR64_TAG"
make -C "$SRC/make" -j"$(nproc)" compiler
mkdir -p "$PREFIX/bin"
ln -sf "$SRC/bin/oscar64" "$PREFIX/bin/oscar64"

echo
echo "oscar64 -> $PREFIX/bin/oscar64 ($OSCAR64_TAG); make sure $PREFIX/bin is on PATH"
echo "VICE: $(command -v x64sc)"
echo "next: make && make test"
