# ADR-0004: Software 80 columns on a VIC-II bitmap with a text shadow buffer

- Status: accepted
- Date: 2026-11-08
- Deciders: Jolyon, Claude

## Context
NetHack's map is 80x21. The VIC-II text mode is 40 columns. Existing soft-80
drivers exist (e.g. cc65's soft80) but we need Oscar64 code, control over
memory placement, and a way for agents to read the screen.

## Decision
`src/hal/screen80.c`: 4x8 font (ours, `tools/mkfont4x8.py`), bitmap at `$E000`
under the KERNAL, colour at `$CC00` (VIC bank 3, no main RAM), write-only
rendering from an 80x25 ASCII shadow buffer `s80_text`, which `tools/vice.py`
reads to give agents the screen as text.

## Consequences
- Colour granularity is a column pair; plan a monochrome map first.
- 2.3 KB of main RAM (shadow + reverse flags); 9 KB of RAM above `$C000`.
- Scrolling redraws from the shadow; acceptable for a turn-based game.
- A C128 build would swap this module for VDC text mode.
