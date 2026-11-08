# Oscar64 compatibility log

Pinned compiler: **Oscar64 v1.32.273** (tag on github.com/drmortalwombat/oscar64).
Each row has a minimal repro in `tests/oscar64-repros/`; `make repros` reports
which still fail. When an upgrade fixes one, retire its workaround and update
this table. The author is responsive and the project releases often: file
upstream issues using the repro files verbatim (they are self-contained).

## Known gaps hit by NetHack 3.4.3

| # | Behaviour | NetHack impact | Workaround (where) | Repro |
|---|---|---|---|---|
| 1 | K&R function definitions not accepted (by design, C99 compiler) | all 2,352 definitions | `tools/kr2ansi.py` + `tools/ansi_manual_fixes.py` | r11 |
| 2 | `register` storage class not accepted | thousands of locals/params | `-dregister=` on the command line | r10 |
| 3 | `# define` (space after `#`) not recognised in active code | most headers | `tools/oscar_normalize.py` moves the space before `#` | r7 |
| 4 | `/* comment */` starting on a `#define` line and continuing to the next line is parsed as code | `global.h`, `mkroom.h`, ... | `oscar_normalize.py` folds the comment onto one line | r8 |
| 5 | Struct tags share the ordinary identifier namespace (C++ style): `struct obj *obj` makes a later `struct obj *otmp` in scope fail; `struct attack` + function `attack()` is a duplicate | 369 `struct obj *obj`, 40 `struct trap *trap`, ~40 other tags | `oscar_normalize.py` renames colliding tags `X` -> `X_s` (tags only) | r5, r6 |
| 6 | `sizeof expr` without parentheses | 117 sites | `oscar_normalize.py` adds parentheses | r3 |
| 7 | Cast binds tighter than `->`: `(char *)(p)->f` | `ONAME()`, `NAME()` macros and others | `oscar_normalize.py` rewrites to `(char *)((p)->f)` | r1 |
| 8 | Cast to function-pointer type with abstract declarator: `(int (*)(T *))0` | ~20 sites (`FDECL((*),...)` casts of 0) | `oscar_normalize.py` drops casts of literal `0` | r4 |
| 9 | Unparenthesised nested `?:` in the middle operand | `pray.c` and a few more | open: add parentheses by hand | r2 |
| 10 | `-Os` segfaults the compiler on a switch-based helper called with an inline-asm result | found in our `src/hal/sys.c` | table lookup instead of `switch`; `-O2` also works | r9 |
| 11 | Compiler does not terminate on `makemon.c` (> 150 s at 100% CPU, killed) | `makemon.c` | open: bisect the file, make a repro | — |
| 11b | Compiler aborts (`mhitm.c`, SIGABRT) or segfaults (`shknam.c`) with no error message, with or without `-rmp` | `mhitm.c`, `shknam.c` | open: bisect each file, make repros | — |
| 12 | Comments inside the very long multi-line `MON(...)` / `OBJECT(...)` macro invocations break expansion ("Invalid define expansion closing argument") | `monst.c`, `objects.c` | measurement strips comments from those two files (`gcc -fpreprocessed -dD -E -P`); simple cases do not reproduce — needs a real repro | — |
| 13 | `-tf=crt` default "main" region runs to `$A000`, under the EasyFlash ROM window | our cartridge build | `#pragma region(main, 0x0900, 0x8000, ...)` in `src/main.c` (as in Oscar64's own EasyFlash sample) | — (usage, not a bug) |
| 14 | Header `-csub` writes the CRT sub-type byte but leaves CRT version 1.0 (sub-type field is 1.1) | REU-aware EasyFlash flag | `tools/crtinfo.py` sets version 1.1 | — |
| 15 | `-rmp` (write error map on link failure) segfaults when the compilation also had ordinary errors | measurement tooling only | `tools/measure` reports such files as compile-error | — |

## Remaining error classes (baseline: 68 files with compile errors)

From `tools/measure/measure_oscar64.py` on the normalised tree. First error per
file only, so counts shift as fixes land. To triage: run the tool on one
file, read the error, reduce to a repro, decide: compiler bug (repro +
upstream issue + workaround) or genuine portability problem (fix in `port/`).

| Class | Example | Likely cause |
|---|---|---|
| "Term starts with invalid token 'else'" (artifact, bones, detect, hack, mklev, shk, sp_lev ...) | `if (x) MACRO(...); else` | a macro expanding to a `{...}` block or ending in `;` before `else`; check each |
| "Pointer expected" at column 227 (display, invent, pickup, zap, mthrowu ...) | long macro expansions (`glyph_is_*`, `canspotmon`) | probably another precedence/cast case like #7 |
| "Incompatible pointer types" / "Incompatible conditional types" (dig, do_wear, eat, lock, dog, mhitu, muse, polyself, rect, track) | `cond ? ptr : 0`, `const` mismatches | stricter type checking than C89 compilers; fix in `port/` |
| "Cannot assign incompatible types 'const union any_s*'" (apply, spell) | `const anything *` vs `anything *` | const-correctness, fix in `port/` |
| "Undefined variable type for X" (botl `hu_stat`, light `circle_data`, rip `killed_by_prefix`, wizard `monstr`, mcastu, do_name) | `extern const char *x[];` then definition with a size | incomplete array declarations completed later; possibly an Oscar64 gap — make a repro |
| "Declaration starts with invalid token 'static'" (version, weapon) | `STATIC_OVL` / `STATIC_DCL` placement | check the macro expansion |
| "Ambiguous function call" (mkroom `mkshop`) | `STATIC_DCL` vs `STATIC_OVL` mismatch produces two declarations | Oscar64 overloads (C++ feature) where C would merge |
| "Too many arguments for function call" (fountain) | | check prototype vs call |
| libc gaps: `SIG_IGN`, `srand48/lrand48`, `clearerr`, `fseek`, `getuid`, `time`, `close` | | expected — these belong to the C64 system layer, not compiler bugs |
| "Cannot place stack section" | file + base data exceed 64 KB in the measurement harness | not an error for the port; sizes are still measured |

## Notes on using Oscar64 for this project

- Whole-program compiler: there is no separate link step, and only code
  reachable from `main` is emitted. The measurement harness relies on a
  table of function pointers to keep a file's functions alive.
- The `-tf=crt` EasyFlash format copies bank 0 into RAM at boot; other banks
  are addressed with `#pragma region(name, 0x8000, 0xc000, , bank, {...})`.
  Cross-bank calls are manual (switch `$DE00`, call) or via the C++ helper
  `EF_CALL` in `<c64/easyflash.h>`. A common area can be placed at the top of
  each bank (`samples/memmap/easyflashshared.c`).
- `.d64` builds turn the same banked regions into disk overlays loaded with
  `krnio_load` and called as normal functions (`samples/memmap/overlay.c`).
- Zero page `$02-$8F` belongs to Oscar64; the KERNAL keeps `$90-$FF`, so KERNAL
  calls (keyboard, disk) remain usable.
- Unnamed parameters in definitions are accepted (C23/C++ style) — handy for stubs.
- `<c64/reu.h>` has REU DMA helpers. Mark buffers that DMA writes `volatile`:
  the optimiser otherwise keeps values it believes it already knows (this bit
  `src/hal/sys.c`).
