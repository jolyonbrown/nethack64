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
