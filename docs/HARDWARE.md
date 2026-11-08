# Hardware notes

## Target matrix

| Tier | Machine | Storage for code/data | Work RAM | 80 columns | Status |
|---|---|---|---|---|---|
| **Primary** | C64 + EasyFlash + REU | 1 MB flash (64 x 16 KB banks) + REU | 64 KB + REU (512 KB-16 MB) | software, VIC-II bitmap | Phase 0 boots in VICE, all REU sizes |
| Alt. primary | C64 + REU only (>= 2 MB) | everything in REU, DMA'd into RAM | 64 KB + REU | software | not started; see ARCHITECTURE option B |
| Fallback | C128 (+ REU) | disk/REU | 128 KB | VDC hardware 80 columns | not started; Oscar64 has `-tm=c128` and `<c128/vdc.h>` |
| Stretch | stock C64 + 1541 | disk overlays | 64 KB | software | probably needs feature cuts; documented, not planned |

Who can run the primary target today: VICE (any OS); Ultimate family —
1541 Ultimate II+, Ultimate 64, and the Commodore 64 Ultimate (all emulate
EasyFlash and REU in one device); a real EasyFlash 3 *plus* a real REU only
with the caveats below. Kung Fu Flash: EasyFlash yes, REU no.

## EasyFlash in one paragraph

64 banks x 16 KB of flash. In 16K mode bank N appears at `$8000-$BFFF`
(ROML+ROMH); bank register `$DE00`, control register `$DE02`; 256 bytes of
cartridge RAM at `$DF00-$DFFF`. Oscar64's `-tf=crt` builds an EasyFlash `.crt`
whose bank 0 holds the startup code and a compressed image of the resident
program, copied to RAM at boot. The flash is writable through EAPI (the
EasyFlash API, normally placed in bank 0 ROMH), which VICE can persist back to
the `.crt` (`-easyflashcrtwrite`). Oscar64's image has no EAPI (VICE logs
"EAPI not found"), so saving to flash would need EAPI added — disk or REU
are simpler for saves.

## The `$DF00` problem (EasyFlash + REU) — read this before touching I/O2

- REU registers live at `$DF00-$DF0A` (mirrored through the page). EasyFlash's
  RAM occupies `$DF00-$DFFF`. Same addresses.
- Real hardware: two devices driving the bus on a **read** of `$DF00-$DFFF`
  is a conflict. Writes are latched by both (harmless to the REU, they just
  scribble EF RAM).
- Kung Fu Flash: its menu runs in EasyFlash mode, the author advises against
  REU + KFF; it does not emulate an REU. ([KFF issue #48](https://github.com/KimJorgensen/KungFuFlash/issues/48))
- The EasyFlash users list: "using an REU and EasyFlash at the same time is out
  of the question due to a conflict". ([easyflash-users](https://groups.google.com/g/easyflash-users/c/8b0NtZ3EGTQ))
- Ultimate family: EasyFlash **sub-type 1, "REU-aware EasyFlash Cart ROM
  ($DF00-$DF1F not used)"**; with standard sub-type 0 the firmware gives
  priority to the cartridge and disables the REU. ([Ultimate docs](https://1541u-documentation.readthedocs.io/en/latest/howto/cartridges.html))
  `make CRT_SUBTYPE=1` writes sub-type 1 and CRT version 1.1 (`tools/crtinfo.py`).
  **Not yet verified on real Ultimate hardware** — first real-hardware task.
- VICE 3.7.1 (verified 2026-11-08): `.crt` EasyFlash + REU 512 KB and 16 MB
  work together; DMA stash/restore passes `make test`; a program that *reads*
  `$DF00`/`$DF02` with both attached runs on with no I/O-collision report.
  VICE is therefore more permissive than hardware: passing in VICE proves
  nothing about the bus conflict.

**Project rules that follow:**
1. Never read `$DF00-$DFFF`. Our REU driver is write-only (start DMA, the CPU
   is halted until it completes, no status polling). Oscar64's `reu_store/
   reu_load` already behave this way.
2. Never use EasyFlash RAM; keep cross-bank state in C64 RAM.
3. Ship the cart as sub-type 1 for Ultimate users once verified.

Alternatives if the conflict bites: cartridges that only use `$DE00`
(GMod2 512 KB, GMod3 up to 16 MB, Magic Desk) coexist with an REU; Oscar64's
`-cid=` sets the CRT type, but each has its own boot/banking rules. Or drop
the cartridge and use REU-only (ARCHITECTURE option B).

## REU

1700 = 128 KB, 1764 = 256 KB, 1750 = 512 KB; modern devices emulate up to
16 MB (VICE `-reusize 16384`, Ultimate family). DMA moves ~1 byte per cycle:
16 KB in ~16 ms. `src/hal/sys.c` detects it by an actual DMA round trip
(robust against anything else answering at `$DF00`) and sizes it by tagging
banks from the top down.

## The 80-column screen

The VIC-II has 40x25 characters; NetHack wants an 80x21 map plus 3 lines.
`src/hal/screen80.c` draws a 4x8-pixel font into a 320x200 hires bitmap:

- bitmap `$E000-$FF3F` under the KERNAL ROM (CPU writes reach RAM; the VIC
  sees RAM), colour matrix `$CC00`. VIC bank 3, so no main RAM is spent.
- the renderer never reads the bitmap: an 80x25 ASCII shadow buffer
  `s80_text` is the truth, each 8x8 cell is recomputed from its two
  characters (`font byte & $F0 | font byte & $0F`, font stored with the
  pattern in both nybbles). Reverse video is a per-column flag.
- colour is per 8x8 cell, i.e. per **pair** of columns — a VIC-II limit. A
  coloured monster next to a grey wall shares one colour. Options for the
  window port: monochrome map (cleanest), or colour only where pairs agree.
- `tools/mkfont4x8.py` holds the glyphs as ASCII art; `-` and `|` are drawn
  edge-to-edge so NetHack walls join.
- cost: 8 KB bitmap + 1 KB colour + 2 KB shadow + 250 B reverse flags.
  Speed: fine for turn-based play; scrolling redraws the screen from the
  shadow (fast enough for messages; the window port should rarely scroll).

C128 alternative: the VDC gives a real 80x25 text mode with per-character
attributes (Oscar64 `<c128/vdc.h>`), at 2 MHz.

## Real hardware test checklist (when the time comes)

- [ ] Ultimate (U2+/U64/C64U): `make CRT_SUBTYPE=1`, REU enabled 512 KB and
      16 MB: `make test`'s AUTOTEST builds should show "AUTOTEST PASS" on screen.
- [ ] Same with CRT_SUBTYPE=0: confirm the REU is reported missing (firmware disables it).
- [ ] EasyFlash 3 + 1750 REU through a port expander: does a read-free
      driver work? (Hypothesis: yes for DMA; record result either way.)
- [ ] Kung Fu Flash: EasyFlash-only build boots; REU absent is handled gracefully.
- [ ] PAL and NTSC machines (timing-sensitive code is none so far, but check).
