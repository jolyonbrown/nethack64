# ADR-0003: Primary target EasyFlash + REU, with REU-only as the fallback design

- Status: accepted (revisit after the Phase 2 banking spike); amended 2026-11-15 and 2026-11-21
- Date: 2026-11-08 (confirms the Sept 2026 choice, adds caveats)
- Deciders: Jolyon, Claude

## Context
Static content is ~1.7 MB, dynamic state ~45-60 KB (NETHACK-SURVEY.md).
EasyFlash gives 1 MB of instantly banked code; an REU gives fast DMA RAM.
EasyFlash RAM and REU registers share `$DF00`; real hardware conflicts on
reads; Ultimate firmware offers a REU-aware EasyFlash sub-type; KFF has no
REU; VICE 3.7.1 runs both happily (HARDWARE.md).

## Decision
Keep EF + REU as primary (VICE, Ultimate family, C64 Ultimate). Rules: never
read `$DF00-$DFFF`, never use EF RAM, ship sub-type 1 once verified on an
Ultimate. Keep "REU-only, >= 2 MB, code by DMA overlays" as a designed
fallback, evaluated in the Phase 2 spike. C128 next; stock C64 is a stretch.

## Consequences
Hardware audience: VICE users, Ultimate owners, C64 Ultimate owners. EF3 +
real REU is "might work, test it". Code partitioning into banks is the core
engineering task of Phase 2.

## Evidence / how to re-check
`make test` (5 cases incl. EF + REU 16 MB); `make CRT_SUBTYPE=1` on real hardware.

## Amendment 2026-11-15: the C64 first, the C128 next

Jolyon, after the speed and memory measurements (RAM-PLAN.md): "a C128 conversion is on the
cards I'd say, but after the 64. if the 64 proves just a stretch too far for us then we can
move directly to the 128 albeit with a bit of regret. Ultimate and other systems should run
our code if they do emulation properly and hopefully quicker too, but lets see if the old
beast works first before we take it off the table", and then: "Vice is the first choice for
sure - stock 64 a stretch ... but a stretch I really want to test".

So:
- The primary target stays a C64 with EasyFlash + REU, in VICE first. Speed is judged at the
  C64's 1 MHz, as VICE runs it.
- The Ultimate family and the C64 Ultimate should run the same build by emulation; their
  turbo modes are a bonus, not a design assumption, and get no separate work.
- A C128 conversion comes after the C64, or instead of it if the C64 proves too much:
  designs should not rule it out (its MMU's shared RAM, the VDC's 80 columns, 2 MHz).
- A stock C64, without expansions, stays a stretch, and one to try: where it costs little,
  keep the mechanisms that bring data and code into RAM (far data, overlays) independent of
  the REU behind them, so that a disk-backed experiment stays possible.

## Amendment 2026-11-21: the C128 first to a running game

Status: accepted (Jolyon, 2026-11-21: "Ok go ahead this seems a sensible pragmatic approach
to take"). He had asked whether to get the C128 running first and come back to the C64, or
squeeze the C64 first; the plan below was approved ("That's a great plan - go ahead!") on
the condition that a check of the C128's cartridge came first. This records that check and
the decision.

**Evidence.** The C64's near memory is about 20 KB short after the data steps; the C128's
(about 46 KB in view less platform code, `tests/spikes/c128.c`) about 8 KB short, both
rough (HARDWARE.md, "The C128, measured"). Almost every byte saved, whether by assembly in
the resident runtime and glue or by packing near data, is saved on both: same CPU family, compiler,
source and banking. Only the screen code differs. In VICE's x128 an EasyFlash is not seen in
C128 mode, but a Magic Desk 128 cartridge (1 MB, 64 banks of 16 KB at `$8000-$BFFF`, bank
register `$DE00`, the EasyFlash layout's window) is, with the REU beside it (HARDWARE.md,
"A banked cartridge in C128 mode").

**Decision.**
- Get the whole game running first on a C128 in VICE (x128): Magic Desk 128 for the first
  63 banks, as the EasyFlash holds them on the C64, the REU for the rest and the far data,
  the VDC for 80 columns, 2 MHz.
- The C64 stays the goal: once the game runs, the C64's squeeze follows, guided by
  profiles of real play (where assembly pays) and by same-seed comparisons with the host.
- Keep the C64 build working throughout (`make test` stays green); the C128 is a second
  platform layer, not a fork.
- Game logic stays NetHack's C (ADR-0001). Assembly goes into our runtime and glue;
  replacing a NetHack function needs its own ADR.

**Open, for real hardware later.**
- How an EasyFlash behaves in C128 mode: per its documentation, 8 KB mirrored at `$8000`
  and 8 KB at `$C000`, so a different bank layout; switching through `$DE00` is not stated.
- Whether the REU needs the CPU at 1 MHz during DMA on a real C128.
- Which cartridge to build or buy: real Magic Desk 128 hardware is mentioned but not yet
  found; ytmytm's 32 KB-bank C128 cartridge is buildable but not emulated.
