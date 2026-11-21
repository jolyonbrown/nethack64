#!/bin/sh
# port/sys/c64/c64scanf.c: against the C library on the host (scanf_test.c, gcc), then under
# Oscar64's emulator (oscar_test.c, -e; OSCAR64 or the oscar64 on PATH).  Exit 0 when both pass.
d=$(cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
gcc -std=gnu99 -Wall -Wno-format -o "$tmp/host" "$d/scanf_test.c" || exit 1
"$tmp/host" || exit 1
osc=${OSCAR64:-$(command -v oscar64)}
[ -n "$osc" ] || { echo "no oscar64: skipped the Oscar64 half"; exit 0; }
out=$( (ulimit -v 3000000; cd "$tmp" && "$osc" -Os -e -o="$tmp/t.prg" "$d/oscar_test.c") 2>&1 | tail -1)
echo "oscar64: $out"
[ "$out" = "Emulation result 0" ]
