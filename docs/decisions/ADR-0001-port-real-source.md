# ADR-0001: Port NetHack's own source; do not reimplement the game

- Status: accepted
- Date: 2026-11-08
- Deciders: Jolyon, Claude

## Context
The first plan (Sept 2026) phased the work as building systems (dungeon
generator, combat, items...) one by one. NetHack 3.4.3's behaviour lives in
~132K lines of C with countless interactions; a reimplementation would never
be NetHack and would take far longer. Phase 0 showed the source can be
converted mechanically to ANSI C (2,352 definitions, verified by a gcc build
that plays, saves and restores) and that a large part already compiles with
Oscar64 after a handful of scripted workarounds.

## Decision
Compile the original `src/` for the C64. Our code is the platform layer
(window port, file layer, system layer, banking, HAL). Game-logic edits are
allowed only to make it fit (memory, compiler gaps), each behaviour-affecting
one backed by an ADR.

## Consequences
- Feature completeness comes "for free"; the work is fitting it (code size,
  RAM, banking). docs/FEATURES.md becomes an acceptance checklist.
- We depend on Oscar64 handling a large 1990s codebase (ADR-0002, OSCAR64-COMPAT.md).
- Every change to `port/` must keep the host build working (regression oracle).

## Evidence / how to re-check
`make port-tree && tools/host-build.sh && tests/host_smoke.py`
