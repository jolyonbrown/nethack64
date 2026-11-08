# ADR-0005: Mechanical K&R -> ANSI conversion with narrow prototypes

- Status: accepted
- Date: 2026-11-08
- Deciders: Jolyon, Claude

## Context
NetHack 3.4.3 defines every function K&R style. Neither Oscar64 nor cc65
accepts NetHack's pattern. Hand conversion of 2,352 definitions is error-prone.

## Decision
`tools/ansi_manual_fixes.py` (4 preprocessor-split definitions) then
`tools/kr2ansi.py` (the rest); build with `UNWIDENED_PROTOTYPES` so the
prototypes in `extern.h` use `char/xchar/boolean`, matching the definitions.
`tools/check_ansi.sh` enforces "no K&R left, prototypes match" with gcc.

## Consequences
Parameters are now passed narrow (smaller 6502 code). The converted tree is
still ordinary C and builds on Linux, giving a regression oracle.

## Evidence / how to re-check
`make port-tree` (prints 2,458 converted incl. tty port), `tools/check_ansi.sh`,
`tools/host-build.sh && tests/host_smoke.py`.
