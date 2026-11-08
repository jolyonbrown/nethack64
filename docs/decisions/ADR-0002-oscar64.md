# ADR-0002: Oscar64 as the compiler (pinned v1.32.273)

- Status: accepted
- Date: 2026-11-08
- Deciders: Jolyon, Claude

## Context
Candidates: cc65 2.19 and Oscar64. Measured on 18 NetHack files both could
compile (13,262 lines): Oscar64 -Os code is 53% of cc65 -Os (89 KB vs 169 KB).
At ~0.85 MB vs ~1.6 MB for the whole game, cc65's output could not fit an
EasyFlash. Oscar64 also has EasyFlash `.crt` output, bank regions, disk
overlays, REU helpers and active maintenance. cc65 has K&R support, but it
rejects NetHack's K&R+narrow-prototype pattern anyway, so conversion is needed
either way. cc65 also refuses functions whose locals exceed its frame limit,
which NetHack's 256-byte buffers hit often.

## Decision
Oscar64, pinned to v1.32.273; upgrades are deliberate (TOOLCHAIN.md).
cc65 stays installed for comparison only.

## Consequences
- We carry workarounds for Oscar64 gaps (OSCAR64-COMPAT.md), each with a repro
  so it can be retired when fixed upstream.
- Single-maintainer compiler risk: mitigated by repros + upstream issues +
  pinning. Escape hatch: the ANSI tree also builds with gcc and (mostly) cc65.

## Evidence / how to re-check
`python3 tools/measure/measure_oscar64.py`; cc65 numbers in
`docs/data/measurements-2026-11-08.json`.
