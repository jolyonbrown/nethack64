#!/usr/bin/env bash
# prepare-port-tree.sh - derive the working port tree from pristine upstream.
#
#   upstream/nethack-3.4.3   (read-only reference)
#        |  copy src/ include/ win/tty/ util/ dat/ sys/share/ sys/unix/
#        v
#   port/                     <- where the C64 port is developed
#
# Mechanical, behaviour-preserving steps, in order:
#   1. tools/ansi_manual_fixes.py   4 definitions with #if'd parameter lists
#   2. tools/kr2ansi.py             ~2,350 K&R definitions -> ANSI C
#   3. tools/oscar_normalize.py     Oscar64 preprocessor/namespace workarounds
#   4. host tools (makedefs etc.)   generate pm.h, onames.h, date.h, vis_tab.[ch]
#   5. tools/check_ansi.sh          gcc proves no K&R left and prototypes match
#
# After this, `tools/host-build.sh` builds the converted tree as ordinary
# Unix tty NetHack and tests/host_smoke.py plays/saves/restores a game with it:
# the behavioural reference for every later change.
#
# Refuses to overwrite an existing port/ unless --force is given: once
# porting starts, port/ is hand-edited source under version control.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -d port ] && [ "${1:-}" != "--force" ]; then
  echo "port/ already exists - it is real source now.  Use --force to regenerate (destroys edits)." >&2
  exit 1
fi
[ -d upstream/nethack-3.4.3 ] || tools/fetch-nethack.sh

rm -rf port
mkdir -p port/win port/sys
U=upstream/nethack-3.4.3
cp -r "$U/src" "$U/include" "$U/util" "$U/dat" "$U/doc" port/
cp -r "$U/win/tty" port/win/
cp -r "$U/sys/share" "$U/sys/unix" port/sys/
cp "$U/README" "$U/dat/license" port/ 2>/dev/null || true
chmod -R u+w port

mkdir -p build
echo "== 1. manual ANSI fixes"
python3 tools/ansi_manual_fixes.py port/src

echo "== 2. K&R -> ANSI"
python3 tools/kr2ansi.py --report build/kr2ansi-skipped.txt port/src/*.c port/win/tty/*.c | tail -1 || true

echo "== 3. Oscar64 normalisation"
python3 tools/oscar_normalize.py port/include/*.h port/src/*.c port/win/tty/*.c \
  port/util/*.c port/util/*.y | wc -l | xargs echo "files normalised:"

echo "== 4. host tools + generated headers"
tools/host-build.sh --generate-only

echo "== 5. gcc consistency check"
tools/check_ansi.sh port

echo "port/ ready"
