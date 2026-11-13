#!/usr/bin/env bash
# setup-ubuntu.sh - toolchain for Debian/Ubuntu, CI runners and cloud sandboxes.
#
# Debian/Ubuntu's VICE package is "+dfsg": the C64 KERNAL/BASIC/CHARGEN and
# drive ROMs are stripped, so x64sc cannot boot.  This script fetches only
# the ROM files from the VICE project's own GitHub mirror (sparse checkout)
# and installs them where the packaged VICE looks.  This is exactly how the
# bundle was verified (VICE 3.7.1 on Ubuntu 24.04).
set -euo pipefail

OSCAR64_TAG=${OSCAR64_TAG:-v1.32.273}
PREFIX=${PREFIX:-$HOME/.local}
SUDO=$(command -v sudo || true)

$SUDO apt-get update -qq
DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq \
  build-essential git python3 python3-pip vice xvfb cc65 libncurses-dev bison flex
python3 -m pip install --break-system-packages -q pexpect || true

# ---- VICE ROMs (only needed for the dfsg package) ----------------------------
VICEDATA=/usr/share/vice
if [ ! -f "$VICEDATA/C64/kernal-901227-03.bin" ] && [ ! -f "$VICEDATA/C64/kernal" ]; then
  tmp=$(mktemp -d)
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/VICE-Team/svn-mirror "$tmp/vice"
  git -C "$tmp/vice" sparse-checkout set vice/data/C64 vice/data/C128 vice/data/DRIVES
  for d in C64 C128 DRIVES; do
    $SUDO cp "$tmp/vice/vice/data/$d/"*.bin "$VICEDATA/$d/"
  done
  rm -rf "$tmp"
  echo "VICE ROMs installed into $VICEDATA"
fi

# ---- Oscar64 ---------------------------------------------------------------------
# The build uses the ADR-0007 compiler: release v1.32.273 plus the wrong-code fixes in
# tools/oscar64-upstream/patches/pin/ (oscar64).  The plain release stays next to it
# (oscar64-plain) for comparisons; OSCAR64_PLAIN=1 makes it the default instead.
# JOBS sets make -j for both compiler builds (default: nproc).
SRC=${OSCAR64_SRC:-$HOME/src/oscar64}
PIN=${OSCAR64_PIN:-$HOME/src/oscar64-pin}
if [ ! -d "$SRC/.git" ]; then
  git clone -q https://github.com/drmortalwombat/oscar64 "$SRC"
fi
git -C "$SRC" fetch --tags --quiet
git -C "$SRC" checkout --quiet "$OSCAR64_TAG"
make -C "$SRC/make" -j"${JOBS:-$(nproc)}" compiler
mkdir -p "$PREFIX/bin"
ln -sf "$SRC/bin/oscar64" "$PREFIX/bin/oscar64-plain"
if [ "${OSCAR64_PLAIN:-0}" = 1 ]; then
  ln -sf "$SRC/bin/oscar64" "$PREFIX/bin/oscar64"
  echo "oscar64 -> $PREFIX/bin/oscar64 (plain $OSCAR64_TAG, OSCAR64_PLAIN=1)"
else
  OSCAR64_REPO="$SRC" JOBS="${JOBS:-$(nproc)}" "$(dirname "$0")/oscar64-upstream/build-pin.sh" "$PIN"
  ln -sf "$PIN/bin/oscar64" "$PREFIX/bin/oscar64"
  echo "oscar64 -> $PREFIX/bin/oscar64 (v1.32.273 + nethack64 patches, ADR-0007);" \
       "oscar64-plain -> $OSCAR64_TAG"
fi
