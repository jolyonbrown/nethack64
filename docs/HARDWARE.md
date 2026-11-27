# Hardware notes

## Target matrix

| Tier | Machine | Storage for code/data | Work RAM | 80 columns | Status |
|---|---|---|---|---|---|
| **Primary** | C64 + EasyFlash + REU | 1 MB flash (64 x 16 KB banks) + REU | 64 KB + REU (1 MB-16 MB for the whole game, ADR-0008) | software, VIC-II bitmap | Phase 0 boots in VICE, all REU sizes |
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

**RAM under ROML** (2026-11-21, `tests/spikes/loram.c`, `run_loram.py`; VICE, EasyFlash): in
16K mode with LORAM clear (`$01 = $36`) the PLA maps RAM at `$8000-$9FFF` and keeps ROMH at
`$A000-$BFFF`; with `$37` ROML is back and the RAM under it kept. A write to `$8000-$9FFF`
with ROML mapped reaches that RAM, and code copied there runs while ROMH is mapped. To
check on a real EasyFlash 3: that such a write leaves the flash alone (the flash takes
commands only as its unlock sequences, but that is the datasheet, not a test).

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
the cartridge and use REU-only (ARCHITECTURE option B). Checked 2026-11-14
(docs/BANKING-SPIKE.md): `-cid=` takes effect only with `-tf=crt8`, `crt16` and
`crt32` (`-tf=crt` always writes an EasyFlash image); of the emulators, only VICE
runs GMod3; the Ultimate family decodes Magic Desk to 512 KB at most; no
cartridge over 1 MB runs on both VICE and the Ultimate family.

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

## The C128, measured (2026-11-21, `tests/spikes/c128.c`, `run_c128.py`; VICE 3.7.1 x128, 512 KB REU)

A spike for the hardware discussion (T2.12: the C64's near memory is about 33 KB short).
Oscar64's C128 target (`-tm=c128`, the pin) runs with the MMU at `$3F`, bank 0 with RAM
everywhere, no ROM and no I/O; code sets `$3E` around each chip access. All seven checks pass:

- **RAM in view:** `$0400-$1BFF`, `$D000-$DFFF` (under the I/O, which `$3E` brings back
  without touching the RAM) and `$E000-$EFFF` (no KERNAL ROM) are RAM. With the program at
  `$1D00`, bank 0 is RAM from `$0400` to `$FBFF`, about 62 KB. `$FC00-$FEFF` is the common
  RAM that `<c128/bank1.h>` uses, and `$FF00` is the MMU. Less a 16 KB code window, that
  leaves about 46 KB for resident code and data, against the C64's 34 KB. Nothing goes on the
  80-column screen: the VDC has its own RAM. If the KERNAL is ever called (disk saves), its
  workspace below `$1C00` must be given back for the call.
- **Bank 1:** it holds other bytes at the same address. `bnk1_readm` copies 256 B in 9,252
  timer ticks (36 a byte; Oscar64's C routine switches the MMU for every byte).
- **REU:** works from bank 0. 16 KB DMA in 17,532 ticks at 1 MHz (1.07 a byte), 16,438 with
  the CPU at 2 MHz. (On a real C128 the REU may need the CPU at 1 MHz during DMA; not checked.)
  2026-11-27: the game runs at 2 MHz and starts each DMA at 1 MHz, putting the clock back
  after (`sys128_speed()` in `src/hal/sys128.c`; the bank call routine, the far runtime and
  the RAM disk). The only written source found: a 1750 clone's guide, "The C128 MUST be in
  1 Mhz (SLOW) mode when a DMA is requested"
  (<https://ar.c64.org/wiki/1750_RAM_Expansion_Clone_Users_Guide_Project64.txt>). A reading
  of the C128's schematics on the Commodore 128 Alive! forum ("REU & 2MHz?", untested) has
  DMA at 1 MHz anyway, since the 2 MHz line does not reach the expansion port. VICE runs the
  REU at either speed, so this is for real hardware. The cartridge's ROM is read at 2 MHz
  too: a Magic Desk 128 needs ROM fast enough for that.
- **VDC:** bytes written to its RAM read back; a screen's 2,000 bytes take 12,669 ticks
  (about 13 ms, 6.3 a byte, through its register port).
- **2 MHz** (`$D030` bit 0): a loop takes 11,479 ticks against 23,419, 2.04 times faster.

Ticks are CIA 1 timer ticks, 1 MHz whatever the CPU's clock. VICE caveat: Arch's VICE 3.7.1
package lacks some of x128's national ROMs (`kernalfi`, `chargen-325167-01.bin`), and x128
will not start without them; `run_c128.py` names the international ROMs in their place.

### A banked cartridge in C128 mode (2026-11-21, `tests/spikes/c128ef.c`, `run_c128ef.py`)

In C128 mode the cartridge port's GAME and EXROM lines do not map memory; the MMU's
configuration register can put "external function ROM" at `$8000-$BFFF` (mid) and
`$C000-$FFFF` (high), read from the cartridge port. The spike tags every byte of each bank's
two 8 KB halves, switches banks through `$DE00` and reads `$8000`, `$A000`, `$C000` and
`$E000` with the MMU at `$2A` (external mid and high, I/O in) and `$3A` (mid only).

- **EasyFlash, VICE 3.7.1 x128:** the C128 starts in C128 mode with VICE's EasyFlash jumper
  option on (`-easyflashjumper`: GAME and EXROM then read high in `$D505`, `$B7`); with it
  off GAME reads low and the program never runs. In C128 mode every read of the external ROM
  is open bus, in every bank and `$DE02` mode: x128 does not show a C64 cartridge as
  external function ROM.
- **Magic Desk 128, VICE 3.7.1 x128** (`-cartmd128`, a 1 MB raw image): every bank tested
  (0, 1, 2, 31, 62, 63) reads its own bytes at `$8000-$BFFF`, the first 8 KB at `$8000`, the
  second at `$A000`, with the MMU at `$2A` or `$3A`; `$C000-$FFFF` reads `$FF` (the cartridge
  drives only the mid range). An REU round trip of 256 B with the cartridge banked in passes.
  That is the C64 EasyFlash layout's window (16 KB at `$8000`, bank register `$DE00`).
- **Real hardware, from documentation only** (not checked): the EasyFlash 1CR page
  (freepascal.org/~daniel/easyflash, a redesign "100% functionally equivalent to the original
  EasyFlash") says a C128 boots an EasyFlash in native mode when its ROM carries the C128
  header, with "the ROML flash ROM ... mirrored two times in the C128's MIDROM region and the
  ROMH flash ROM ... mirrored two times in the C128's HIROM region": 8 KB at `$8000` and 8 KB
  at `$C000`, not 16 KB in one piece, and it does not say whether `$DE00` switches banks in
  C128 mode. github.com/ytmytm/c128-magicdesk-external-rom is a buildable C128 cartridge,
  512 KB (1 MB with two chips), 32 KB banks at `$8000-$FFFF` through `$DE00`, not emulated
  by VICE; its README names "Magic Desk 128 and Gmod2 (128)" as projects that "map only 16K
  at a time".

### Bank calls on a C128 (2026-11-21, `tests/spikes/bankreu128.c`, `run_bankreu128.py`)

bankreu.c's fourteen checks on a C128 in C128 mode (x128, Magic Desk 128 + 1 MB REU), all
pass: the linker's bank call stubs (pin, `Linker::InsertBankCalls`) and the bank call routine
unchanged, `nh_map` alone rewritten. A cartridge bank is `$DE00` written and the MMU set to
`$3A` (external ROM at `$8000-$BFFF`, I/O in); an REU bank is the MMU at `$3E` (RAM there)
and, if the window holds another bank, the 16 KB DMA, as on the C64. The program runs with
the I/O in throughout and interrupts off (no KERNAL ROM, so no interrupt handler yet).

| an `int (int, int)` call, cycles | C64 (EasyFlash) | C128 (Magic Desk 128) |
|---|---|---|
| into a cartridge bank | 309.7 | 330.2 |
| into an REU bank already in the window | 361.4 | 362.2 |
| into an REU bank, a 16 KB fetch | 16,832 | 17,720 |

Both at 1 MHz, the C128's timed with CIA 2. The build is `-tm=c128 -tf=prg` with one
`#pragma overlay( STEM_ovN, N )` per bank: Oscar64 writes each bank as `STEM_ovN.prg` in
the program's directory, and `tools/bank/c128_images.py` makes the cartridge image (VICE's
raw Magic Desk 128 format) and the REU image (`crt_split.py`'s layout) of them. (Oscar64's
`-tf=crt` for the C128 writes an EasyFlash-style boot, the program LZ-compressed in bank 0,
which a C128 in its own mode would not start.)

## Real hardware test checklist (when the time comes)

- [ ] Ultimate (U2+/U64/C64U): `make CRT_SUBTYPE=1`, REU enabled 512 KB and
      16 MB: `make test`'s AUTOTEST builds should show "AUTOTEST PASS" on screen.
- [ ] Same with CRT_SUBTYPE=0: confirm the REU is reported missing (firmware disables it).
- [ ] EasyFlash 3 + 1750 REU through a port expander: does a read-free
      driver work? (Hypothesis: yes for DMA; record result either way.)
- [ ] Kung Fu Flash: EasyFlash-only build boots; REU absent is handled gracefully.
- [ ] PAL and NTSC machines (timing-sensitive code is none so far, but check).
