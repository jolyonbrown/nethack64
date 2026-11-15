# ADR-0003: Primary target EasyFlash + REU, with REU-only as the fallback design

- Status: accepted (revisit after the Phase 2 banking spike)
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
