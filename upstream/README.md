# upstream/

`nethack_3.4.3.orig.tar.gz` is the NetHack 3.4.3 source release (December
2003), as redistributed by Debian/Ubuntu under its orig-tarball name.

- sha256 `bb39c3d2a9ee2df4a0c8fdde708fbc63740853a7608d2f4c560b488124866fe4`
- md5 `21479c95990eefe7650df582426457f9`

NetHack is distributed under the NetHack General Public License
(`nethack-3.4.3/dat/license` after extraction; copyright notices are in the
individual source files). The licence permits
redistribution of the source; anything we distribute that is derived from it
(the `port/` tree, the cartridge image) must follow that licence, including
making our modified source available.

`tools/fetch-nethack.sh` verifies the checksum and extracts a read-only copy
to `upstream/nethack-3.4.3/` (git-ignored). Never edit it — changes go in `port/`.
