---
description: Reduce an Oscar64 compiler problem (rejection of valid C, wrong code, crash, hang) to a minimal repro in tests/oscar64-repros, add a workaround and document it.
---

# Oscar64 repro

1. Copy the failing construct into a scratch `.c`; delete everything not needed
   until removing anything else makes the problem disappear. Aim for < 30 lines,
   no NetHack headers.
2. Make it self-checking: `int main(void)` returns 0 when the compiler is right.
3. Save as `tests/oscar64-repros/rNN_<short_name>.c` (next free NN) with the header
   used by the others: what fails, NetHack impact, expected when fixed, workaround,
   `FLAGS:` (usually `-e`), `COMPILE-ONLY` if it is a crash/hang.
4. `make repros` — the new one must show BROKEN.
5. Workaround: scripted in `tools/oscar_normalize.py` if it is a source pattern
   (then `make port-tree` users get it; for an existing port/ run the normaliser on
   the affected files), otherwise a targeted edit with a comment pointing at the repro.
6. Add a row to `docs/OSCAR64-COMPAT.md`. Draft (do not post) an upstream issue
   text in the session note for Jolyon to file.
