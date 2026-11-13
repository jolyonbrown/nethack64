# References

## Compiler and emulator
- Oscar64 — https://github.com/drmortalwombat/oscar64 (manual: `oscar64.md` in the repo;
  EasyFlash samples: `samples/memmap/easyflash*.c`; overlays: `samples/memmap/overlay.c`)
- cc65 — https://github.com/cc65/cc65
- VICE — https://vice-emu.sourceforge.io/ (binary monitor: manual chapter "Binary monitor";
  GitHub mirror with ROMs and docs: https://github.com/VICE-Team/svn-mirror)

## Hardware
- EasyFlash — https://www.c64-wiki.com/wiki/EasyFlash
- Ultimate cartridge emulation & REU-aware EasyFlash sub-type —
  https://1541u-documentation.readthedocs.io/en/latest/howto/cartridges.html
- Kung Fu Flash + REU discussion — https://github.com/KimJorgensen/KungFuFlash/issues/48
- EasyFlash and REU conflict — https://groups.google.com/g/easyflash-users/c/8b0NtZ3EGTQ
- Commodore 64 Ultimate (built on the Ultimate 64) —
  https://www.hackster.io/news/the-commodore-64-returns-as-the-fpga-powered-commodore-64-ultimate-4a8ea04e9dab
- CRT file format — VICE manual, "The CRT cartridge image format"

## Fitting tricks (banking, REU, drives, crunchers)

Collected 2026-11-12 for `docs/FITTING-TOOLBOX.md`, which says what each is
used for. Starting point: the Fairlight docs archive, Jolyon's pointer —
http://www.fairlight.to/docs/ (plain HTTP only). It is a link page from
about 2000 and most of its outbound links are dead; where one was, the entry
below is a mirror that answered on 2026-11-12.

Memory map and banking
- C64 PLA notes (how GAME/EXROM and `$01` select RAM, ROML, ROMH) —
  http://www.zimmers.net/anonftp/pub/cbm/documents/chipdata/c64-pla.txt
- Bank switching summary — https://www.c64-wiki.com/wiki/Bank_Switching
- C64 memory maps (Marko Mäkelä's collection, via Fairlight) —
  http://www.zimmers.net/anonftp/pub/cbm/maps/ ; RAM and I/O maps at
  http://web.archive.org/web/20050206090624/http://www.hut.fi:80/Misc/cbm/docs/c64-ram.html
  and http://web.archive.org/web/20050206090434/http://www.hut.fi:80/Misc/cbm/docs/c64-io.html
- ROM listings and CPU reference for KERNAL-free code — AAY64,
  http://unusedino.de/ec64/technical/aay/c64/ ; `64doc`,
  http://www.zimmers.net/anonftp/pub/cbm/documents/chipdata/64doc
- VIC-II article by Christian Bauer (hosted by Fairlight) —
  http://www.fairlight.to/docs/text/vic.txt
- EasyFlash programmer's reference (registers, modes, EAPI) —
  https://skoe.de/easyflash/files/devdocs/EasyFlash-ProgRef.pdf
- Programmer's Reference Guide —
  https://www.devili.iki.fi/Computers/Commodore/C64/Programmers_Reference/

REU and GeoRAM
- 17xx REU programming reference (Richard Hable; DMA commands, the `$FF00`
  trigger, transfer speed; via Fairlight) —
  http://www.zimmers.net/anonftp/pub/cbm/documents/chipdata/programming.reu
- 17xx REU registers (via Fairlight) —
  http://www.zimmers.net/anonftp/pub/cbm/documents/chipdata/reu.registers
- REU expansions beyond 512 KB —
  http://www.zimmers.net/anonftp/pub/cbm/documents/projects/memory/reu/
- VICE REU and GeoRAM options (`-reusize`, `-reuimage`, `-reuimagerw`) —
  https://vice-emu.sourceforge.io/vice_7.html
- Ultimate 64 manual (REU size and preload settings) —
  https://1541u-documentation.readthedocs.io/en/latest/ultimate64-manual.html
- GeoRAM — https://www.c64-wiki.com/wiki/GeoRAM

Pi-based cartridges and other large-REU devices
- RAD Expansion Unit (Pi 3A+/3B+/Zero 2; REU up to 16 MB, GeoRAM up to 4 MB;
  no EasyFlash) — https://github.com/frntc/RAD ; review,
  https://c64os.com/post/radreview
- Sidekick64 (same author; EasyFlash and GeoRAM, no REU) —
  https://github.com/frntc/Sidekick64
- Turbo Chameleon 64 — https://www.c64-wiki.com/wiki/Turbo_Chameleon_64
- Kung Fu Flash (moved to Codeberg) — https://codeberg.org/KimJorgensen/KungFuFlash

Disk drives: drive code and loaders
- 1541 tricks (the `&` utility loader; via Fairlight) —
  http://www.zimmers.net/anonftp/pub/cbm/documents/disk-drives/1541-tricks.txt
- Drive ROM and serial bus — AAY1541, http://unusedino.de/ec64/technical/aay/c1541/ ;
  http://www.zimmers.net/anonftp/pub/cbm/documents/programming/serial-bus.pdf
- The drive as a second CPU (article and costed comments) — https://www.pagetable.com/?p=55
- Mandelbrot Construction Set, 64'er 10/1991 —
  https://www.c64-wiki.de/wiki/Mandelbrot-Construction-Set
- Panta Rhei — https://csdb.dk/release/?id=15745 ; Freespin —
  https://hackaday.com/2021/07/08/c64-demo-no-c64/
- Krill's loader — https://csdb.dk/release/?id=226124 ;
  https://plus4world.powweb.com/tools/Krills_Loader
- Which devices run drive code: Ultimate drive emulation,
  https://1541u-documentation.readthedocs.io/en/latest/howto/mm_drive.html ;
  SD2IEC (does not), https://www.c64-wiki.com/wiki/sd2iec_(firmware)

Crunchers
- Codebase64 compression benchmark (2016 corpus) —
  https://codebase.c64.org/doku.php?id=base:compression_benchmarks
  (`codebase64.org` now redirects to an unrelated site; do not link it)
- Exomizer 3.1 — https://bitbucket.org/magli143/exomizer/raw/master/exo31info.txt
- ZX0 — https://github.com/einar-saukas/ZX0 ; ZX02 (6502) — https://github.com/dmsc/zx02 ;
  salvador (fast ZX0 packer) — https://github.com/emmanuel-marty/salvador ;
  Dali, in Bitfire — https://github.com/bboxy/bitfire
- TSCrunch — https://github.com/tonysavon/TSCrunch
- LZSA — https://github.com/emmanuel-marty/lzsa
- ByteBoozer 2 — https://github.com/luigidifraia/ByteBoozer2
- upkr — https://github.com/exoticorn/upkr ; 6502 unpacker —
  https://github.com/pfusik/upkr6502
- pucrunch — https://a1bert.kapsi.fi/Dev/pucrunch/
- Subsizer — https://csdb.dk/release/?id=154516 ; Doynamite —
  https://csdb.dk/release/?id=129574
- X-terminator 2, the FairLight packer and linker (historical; hosted by
  Fairlight) — http://www.fairlight.to/docs/bin/x-terminator2.lnx

File formats
- Peter Schepers' C64 file formats (CRT, D64, ...) —
  https://ist.uwaterloo.ca/~schepers/formats.html

## NetHack
- NetHack 3.4.3 — https://www.nethack.org/v343/ (source also in `upstream/`)
- NetHack General Public License — `upstream/nethack-3.4.3/dat/license`
- MS-DOS overlay build (historic precedent): `upstream/nethack-3.4.3/sys/msdos/`
  (`Makefile.BC`, `schema*.BC`, `ovlinit.c`) and `include/trampoli.h`

## Agents
- Claude Code memory files and `@AGENTS.md` imports — https://code.claude.com/docs/en/memory
- Claude Code project files (`.claude/`, skills, plugins) — https://code.claude.com/docs/en/claude-directory
- Codex plugin for Claude Code (`/codex:review`, `/codex:rescue`, ...) — https://github.com/openai/codex-plugin-cc
- `codex mcp-server` deprecated 2026-08, removed in Codex CLI 0.154.0 —
  https://codex.danielvaughan.com/2026/08/30/codex-mcp-server-deprecated-migration-app-server-agents-sdk/
- Codex's Linux sandbox (bubblewrap from PATH, user namespaces) —
  https://github.com/openai/codex/blob/main/codex-rs/linux-sandbox/README.md
