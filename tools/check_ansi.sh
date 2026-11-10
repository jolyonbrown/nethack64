#!/usr/bin/env bash
# check_ansi.sh - prove a NetHack tree is fully ANSI and self-consistent.
#
# Compiles every src/*.c with gcc in strict-ish C89 mode:
#   -Werror=old-style-definition      no K&R definition left anywhere
#   -Werror=implicit-int              no implicit int
#   -Werror=implicit-function-declaration   every called function is declared
#                                     (old-style `E long lrand48();` in system.h
#                                     counts: this does not prove prototypes)
#   -DUNWIDENED_PROTOTYPES            extern.h prototypes use char/xchar/
#                                     boolean, so any definition whose types
#                                     differ is a hard "conflicting types" error
# No -w: gcc's -w also silences warnings promoted with -Werror=, which made
# all three checks pass vacuously (gcc 13.3: a K&R definition calling an
# undeclared function compiled clean).  gcc's default warnings (~160 in port/src,
# mostly -Wformat-security) are not checked, and a FAIL shows only the errors.
#
# usage: tools/check_ansi.sh [tree]   (default: port)
set -euo pipefail
T=${1:-port}
# generated headers are git-ignored; recreate them after a fresh clone
if [ "$T" = port ] && [ ! -f port/include/pm.h ]; then
  "$(dirname "$0")/host-build.sh" --generate-only
fi
cd "$T/src"
fail=0
for f in *.c; do
  if ! gcc -c -o /dev/null -std=gnu89 \
      -Werror=old-style-definition -Werror=implicit-int \
      -Werror=implicit-function-declaration \
      -DUNWIDENED_PROTOTYPES -I../include "$f" 2> /tmp/check_ansi.$$; then
    echo "FAIL $f"
    grep -m5 -A2 'error:' /tmp/check_ansi.$$ || head -5 /tmp/check_ansi.$$
    fail=$((fail+1))
  fi
done
rm -f /tmp/check_ansi.$$
if [ $fail -ne 0 ]; then echo "$fail file(s) failed"; exit 1; fi
echo "check_ansi: all $(ls *.c | wc -l) files clean"
