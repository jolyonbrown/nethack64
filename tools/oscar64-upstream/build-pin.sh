#!/bin/sh
# Build the compiler proposed in ADR-0007: Oscar64 release v1.32.273 plus
# tools/oscar64-upstream/patches/pin/*.patch, in DIR (default ~/src/oscar64-pin).
# It does not touch ~/src/oscar64 or PATH; use it as  make OSCAR64=DIR/bin/oscar64.
# OSCAR64_REPO overrides the upstream URL (e.g. a local clone).
set -eu
here=$(cd "$(dirname "$0")" && pwd)
dir=${1:-$HOME/src/oscar64-pin}
repo=${OSCAR64_REPO:-https://github.com/drmortalwombat/oscar64}
tag=v1.32.273
[ -d "$dir/.git" ] || git clone -q "$repo" "$dir"
git -C "$dir" fetch -q --tags "$repo"
git -C "$dir" checkout -q -B nethack64-pin "$tag"
git -C "$dir" -c user.name=nethack64 -c user.email=nethack64@invalid -c commit.gpgsign=false \
    am -q "$here"/patches/pin/*.patch
make -C "$dir/make" -j"$(nproc)" compiler > "$dir/build.log" 2>&1 || { tail -20 "$dir/build.log"; exit 1; }
n=$(git -C "$dir" rev-list --count "$tag"..HEAD)
echo "$dir/bin/oscar64: $tag + $n patches ($(git -C "$dir" rev-parse --short HEAD))"
