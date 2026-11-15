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
#                                        port/src/vis_tab.c, port/src/monstr.c
#   tools/host-build.sh --sanitize       full build with AddressSanitizer + UBSan, installed to
#                                        build/host-asan-install (known reports: NETHACK-SURVEY.md)
#   tools/host-build.sh --profile        full build for gprof (-pg, no inlining, no sibling
#                                        calls, so every call is an arc), installed to
#                                        build/host-prof-install (tools/profile_play.py)
#   tools/host-build.sh --banked PLAN    full build of src/ as tools/bank/bankgen.py rewrites it
#                                        for the bank plan PLAN (bankpart.py --plan-out), installed
#                                        to build/host-banked-install: the rewrite must not change
#                                        what the game does (docs/BANKING-SPIKE.md)
#
# Needs: gcc, make, ncurses headers, bison/yacc, flex/lex.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
[ -d port ] || { echo "no port/ tree; run tools/prepare-port-tree.sh" >&2; exit 1; }

H=build/host; INSTALL=host-install; SAN=
if [ "${1:-}" = "--sanitize" ]; then
  H=build/host-asan; INSTALL=host-asan-install
  SAN="-fsanitize=address,undefined -fsanitize-recover=address -fno-omit-frame-pointer"
elif [ "${1:-}" = "--profile" ]; then
  # the banking spike needs call counts per caller and callee (BANKING-SPIKE.md)
  H=build/host-prof; INSTALL=host-prof-install
  SAN="-pg -fno-inline -fno-inline-functions-called-once -fno-optimize-sibling-calls"
elif [ "${1:-}" = "--banked" ]; then
  H=build/host-banked; INSTALL=host-banked-install
  PLAN=$(realpath "${2:?--banked needs a plan file}")
fi
rm -rf "$H"; mkdir -p "$H"
cp -r port/. "$H"/
cd "$H"
sh sys/unix/setup.sh > /dev/null
if [ -n "${PLAN:-}" ]; then
  # make runs makedefs again for monstr.c and vis_tab.c, so a rewrite of those would be lost
  (cd src && python3 "$ROOT/tools/bank/bankgen.py" --plan "$PLAN" --dir . --inc ../include \
      --cpp=-DUNWIDENED_PROTOTYPES --report ../bankgen-report.json \
      $(ls *.c | grep -v -x -e monstr.c -e vis_tab.c))
fi

# compiler flags: the converted source is ANSI; keep prototypes narrow like
# the C64 build (UNWIDENED_PROTOTYPES), silence 1990s-era warnings.
sed -i "s|^CFLAGS = -O -I../include|CFLAGS = -O -g $SAN -std=gnu89 -w -DUNWIDENED_PROTOTYPES -I../include|" src/Makefile
# util/ links some of src/'s objects, so it needs the sanitizer (or profiling) runtime too
[ -z "$SAN" ] || sed -i "s|^LFLAGS =.*|LFLAGS = $SAN|" src/Makefile util/Makefile
sed -i 's|^CFLAGS = -O -I../include|CFLAGS = -O -g -std=gnu89 -w -I../include|' util/Makefile
sed -i 's|^WINTTYLIB = -ltermlib|WINTTYLIB = -lncurses|' src/Makefile
# modern ncurses declares tparm() with a prototype
sed -i 's|^extern char \*tparm();|/* tparm() comes from <term.h> */|' win/tty/termcap.c

if [ "${1:-}" = "--generate-only" ]; then
  make -C util makedefs > ../host-gen.log 2>&1 || { tail -20 ../host-gen.log; exit 1; }
  (cd util && ./makedefs -o && ./makedefs -p && ./makedefs -v && ./makedefs -z && ./makedefs -m)
  cp include/onames.h include/pm.h include/date.h include/vis_tab.h "$ROOT/port/include/"
  cp src/vis_tab.c src/monstr.c "$ROOT/port/src/"
  echo "generated headers copied into port/"
  exit 0
fi

# util's makedefs rule compiles ../src/monst.o and ../src/objects.o itself.  Run in
# parallel with src's own compile of the same two objects, the writes can collide
# (2026-11-14: "ld: ../src/monst.o: error adding symbols"), so build makedefs first,
# in the order a serial build takes.
make -C util makedefs > ../host-build.log 2>&1 || { tail -30 ../host-build.log; exit 1; }
make -C src -j"$(nproc)" >> ../host-build.log 2>&1 || { tail -30 ../host-build.log; exit 1; }
I="$ROOT/build/$INSTALL"
rm -rf "$I"
make install PREFIX="$I" GAMEDIR="$I/nethackdir" SHELLDIR="$I/bin" \
  CHOWN=true CHGRP=true >> ../host-build.log 2>&1 || { tail -30 ../host-build.log; exit 1; }
echo "host NetHack installed: $I/nethackdir/nethack  (run with -d $I/nethackdir)"
