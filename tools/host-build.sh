#!/usr/bin/env bash
# host-build.sh - build the port/ tree as ordinary Unix tty NetHack with gcc.
#
# Why: every mechanical or hand change to the game source should leave its
# behaviour unchanged.  The host build is fast, debuggable with gdb, and
# tests/host_smoke.py drives it (play, save, restore) as a regression check.
# It also runs NetHack's host-side generators (makedefs, dgn_comp, lev_comp,
# dlb) whose outputs the C64 build packs into the cartridge.
#
#   tools/host-build.sh                  full build + install to build/host-install
#   tools/host-build.sh --generate-only  just makedefs -> port/include/{pm,onames,date,vis_tab}.h,
#                                        port/src/vis_tab.c
#
# Needs: gcc, make, ncurses headers, bison/yacc, flex/lex.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
[ -d port ] || { echo "no port/ tree; run tools/prepare-port-tree.sh" >&2; exit 1; }

H=build/host
rm -rf "$H"; mkdir -p "$H"
cp -r port/. "$H"/
cd "$H"
sh sys/unix/setup.sh > /dev/null

# compiler flags: the converted source is ANSI; keep prototypes narrow like
# the C64 build (UNWIDENED_PROTOTYPES), silence 1990s-era warnings.
sed -i 's|^CFLAGS = -O -I../include|CFLAGS = -O -g -std=gnu89 -w -DUNWIDENED_PROTOTYPES -I../include|' src/Makefile
sed -i 's|^CFLAGS = -O -I../include|CFLAGS = -O -g -std=gnu89 -w -I../include|' util/Makefile
sed -i 's|^WINTTYLIB = -ltermlib|WINTTYLIB = -lncurses|' src/Makefile
# modern ncurses declares tparm() with a prototype
sed -i 's|^extern char \*tparm();|/* tparm() comes from <term.h> */|' win/tty/termcap.c

if [ "${1:-}" = "--generate-only" ]; then
  make -C util makedefs > ../host-gen.log 2>&1 || { tail -20 ../host-gen.log; exit 1; }
  (cd util && ./makedefs -o && ./makedefs -p && ./makedefs -v && ./makedefs -z)
  cp include/onames.h include/pm.h include/date.h include/vis_tab.h "$ROOT/port/include/"
  cp src/vis_tab.c "$ROOT/port/src/"
  echo "generated headers copied into port/"
  exit 0
fi

make -C src -j"$(nproc)" > ../host-build.log 2>&1 || { tail -30 ../host-build.log; exit 1; }
I="$ROOT/build/host-install"
rm -rf "$I"
make install PREFIX="$I" GAMEDIR="$I/nethackdir" SHELLDIR="$I/bin" \
  CHOWN=true CHGRP=true >> ../host-build.log 2>&1 || { tail -30 ../host-build.log; exit 1; }
echo "host NetHack installed: $I/nethackdir/nethack  (run with -d $I/nethackdir)"
