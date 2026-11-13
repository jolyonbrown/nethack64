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

# Oscar64 from source, pinned.  The build uses the ADR-0007 compiler: release v1.32.273
# plus the wrong-code fixes in tools/oscar64-upstream/patches/pin/ (oscar64).  The plain
# release stays next to it (oscar64-plain) for comparisons; OSCAR64_PLAIN=1 makes it the
# default instead.  JOBS sets make -j for both compiler builds (default: nproc).
SRC=${OSCAR64_SRC:-$HOME/src/oscar64}
PIN=${OSCAR64_PIN:-$HOME/src/oscar64-pin}
if [ ! -d "$SRC/.git" ]; then
  git clone https://github.com/drmortalwombat/oscar64 "$SRC"
fi
git -C "$SRC" fetch --tags --quiet
git -C "$SRC" checkout --quiet "$OSCAR64_TAG"
make -C "$SRC/make" -j"${JOBS:-$(nproc)}" compiler
mkdir -p "$PREFIX/bin"
ln -sf "$SRC/bin/oscar64" "$PREFIX/bin/oscar64-plain"
if [ "${OSCAR64_PLAIN:-0}" = 1 ]; then
  ln -sf "$SRC/bin/oscar64" "$PREFIX/bin/oscar64"
  which="plain $OSCAR64_TAG, OSCAR64_PLAIN=1"
else
  OSCAR64_REPO="$SRC" JOBS="${JOBS:-$(nproc)}" "$(dirname "$0")/oscar64-upstream/build-pin.sh" "$PIN"
  ln -sf "$PIN/bin/oscar64" "$PREFIX/bin/oscar64"
  which="v1.32.273 + nethack64 patches, ADR-0007; oscar64-plain is $OSCAR64_TAG"
fi

echo
echo "oscar64 -> $PREFIX/bin/oscar64 ($which); make sure $PREFIX/bin is on PATH"
echo "VICE: $(command -v x64sc)"
echo "next: make && make test"
