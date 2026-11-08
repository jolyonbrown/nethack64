#!/usr/bin/env bash
# fetch-nethack.sh - put pristine NetHack 3.4.3 source in upstream/nethack-3.4.3
#
# The tarball is committed at upstream/nethack_3.4.3.orig.tar.gz (NetHack's
# licence allows redistribution; see upstream/README.md).  If it is missing,
# it is downloaded.  Either way the checksum is verified before extracting.
#
# The Debian/Ubuntu "orig" tarball is the upstream nethack-343-src.tgz
# repackaged under Debian's name; same contents, checksum below.
set -euo pipefail
cd "$(dirname "$0")/.."

TARBALL=upstream/nethack_3.4.3.orig.tar.gz
SHA256=bb39c3d2a9ee2df4a0c8fdde708fbc63740853a7608d2f4c560b488124866fe4
URLS=(
  "http://archive.ubuntu.com/ubuntu/pool/universe/n/nethack/nethack_3.4.3.orig.tar.gz"
  "https://www.nethack.org/download/3.4.3/nethack-343-src.tgz"
)

mkdir -p upstream
if [ ! -f "$TARBALL" ]; then
  for u in "${URLS[@]}"; do
    echo "fetching $u"
    if curl -fsSL -o "$TARBALL.tmp" "$u"; then mv "$TARBALL.tmp" "$TARBALL"; break; fi
  done
fi
[ -f "$TARBALL" ] || { echo "could not fetch NetHack 3.4.3 source" >&2; exit 1; }

got=$(sha256sum "$TARBALL" | cut -d' ' -f1)
if [ "$got" != "$SHA256" ]; then
  echo "checksum mismatch for $TARBALL" >&2
  echo "  expected $SHA256" >&2
  echo "  got      $got" >&2
  echo "(nethack.org's own nethack-343-src.tgz may differ byte-wise; compare contents before trusting it)" >&2
  exit 1
fi

if [ ! -d upstream/nethack-3.4.3 ]; then
  tar -C upstream -xzf "$TARBALL"
  chmod -R a-w upstream/nethack-3.4.3   # pristine reference: never edit
fi
echo "upstream/nethack-3.4.3 ready ($(find upstream/nethack-3.4.3/src -name '*.c' | wc -l) source files)"
