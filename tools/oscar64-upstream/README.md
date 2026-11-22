# Fixing Oscar64 upstream

How we turn Oscar64 bugs found by the port into fixes that could go upstream
(github.com/drmortalwombat/oscar64). A fix becomes a pull request only after
Jolyon has read its explanation and said yes. Until then, branches stay local.

- **Memory.** Run every compile of a NetHack file, reduction or probe under
  a cap, `(ulimit -v 3000000; ...)`: some Oscar64 bugs make the compiler grow
  without bound (compat #30), and on a 15 GB machine the kernel's OOM killer
  then stops it, or something else. Under the cap a runaway ends in seconds in
  `std::bad_alloc`. `tools/measure/measure_oscar64.py` and `make repros` cap
  their compiles themselves (`MEASURE_MEMORY_MB`, `REPRO_MEMORY_MB`).
- **Clones.** `~/src/oscar64` is the pinned compiler (v1.32.273) that every
  nethack64 build uses; never rebuild it for this work. `~/src/oscar64-dev`
  tracks upstream `main` (remote `upstream`). `~/src/oscar64-base` is a frozen
  build of that `main`, the "before" compiler; its `COMMIT` file names the
  commit.
- **One worktree and branch per fix**, under the ignored `build/`:
  `git -C ~/src/oscar64-dev worktree add $PWD/build/oscar64-wt/<id> -b fix/<id> <base>`,
  then `make -C build/oscar64-wt/<id>/make -j8 compiler`. A compiler finds its
  headers relative to its own binary, so each worktree uses its own `include/`.
  `make clean` deletes `build/`. Commits survive in `~/src/oscar64-dev`, but
  uncommitted work in a worktree does not.
- **Evidence for each fix:**
  - the case passes in all ten autotest configurations, `-ea -g` with
    `-bc`/`-n` × default/`-O2`/`-O0`/`-Os`/`-O3`;
  - a new `autotest/<name>.c` with `assert`s, registered in `autotest.bat`,
    that fails before the fix and passes after it (for a compile-time or
    memory blow-up: a test that makes the unfixed compiler slow or large but
    lets it finish, since a test that exhausts memory would hurt whoever
    runs the suite; #15 is the example);
  - `make -k -j4 -C make check > LOG 2>&1`, then
    `autotest_diff.py BASE.log LOG` shows no new failures;
  - `corpus_diff.py BEFORE AFTER --out DIR` shows every program both
    compilers accept still compiles byte for byte the same, or each
    difference is explained.
- **Upstream's PR style** (merged PR #440, for example): a minimal example
  with the command that reproduces it, observed vs expected output, the root
  cause, a small fix, the regression test, and validation numbers. The
  maintainer often takes the test and writes his own fix (PRs #443, #447).
  He will not split struct tags into their own namespace (issue #438), so r5
  and r6 stay local workarounds.
- **`cases/`** holds inputs that are not nethack64 repros, such as the
  function-pointer-member regression on upstream `main` (2026-11-12), which
  v1.32.273 compiles.
- **`patches/main/`** holds the finished fixes as `git format-patch` files, one
  commit each on upstream main 4da3147, numbered in the proposed submission
  order (`git -C <clone> am patches/main/NN-<id>.patch`; #06 applies on top of
  #01). They are what `docs/OSCAR64-UPSTREAM.md` and `docs/oscar64-upstream/`
  describe, kept here because the branches exist only in a local clone until
  there is a fork. **`patches/pin/`** holds the same fixes backported to
  v1.32.273 for the patched compiler accepted in ADR-0007. Both are Oscar64
  changes and so GPL-3.0, like Oscar64.
- **`patches/far-spaces/`** is T2.12's work in progress, far data in the compiler as
  ADR-0009 decides (`#pragma farspace`, `#pragma farsection`, warning 2026), on top of
  the pin (`git am` after `patches/pin/`; the fork's `feature/far-spaces`). Not in the
  pin: Jolyon decides that. `autotest/farspacetest.c` and
  `tests/spikes/run_farspace.py --oscar64 PATH` check it. (Its three commits that were
  not far-specific joined the pin on 2026-11-18 as 81-83; the series is five commits on
  pin 83, and a sixth, 2026-11-19: a call from code in a bank goes through a stub in that bank;
  `tests/spikes/run_bankstub.py --banked-stubs 8` checks it; a seventh, 2026-11-20: section
  flag 4 keeps a section's calls on the resident stubs; an eighth, the same day: the proxy
  of a resident function called from a bank goes into that bank, `run_bankstub.py
  --banked-proxies 2`; a ninth: `#pragma fardefault(section)` and `#pragma near(name, ...)`,
  `autotest/fardefaulttest.c`; a tenth, 2026-11-21: a far default object keeps to one page,
  aligned to the power of two at or above its size, one larger than a page staying near. On
  2026-11-21 the ten moved onto pin 85, which adds upstream's fix of r77. An eleventh, the
  same day: far characters, `#pragma farchars` and `#pragma strings` (ADR-0010),
  `autotest/farcharstest.c`, with `-dOSCAR_FARCHARS` for the library's assembler string
  routines. A twelfth fixes r78, which is not far-specific: two loads through one pointer
  sorted by offset even when the second loads the pointer; `autotest/loadordertest.c`.
  Proposed for the pin too: it applies there as it is. A thirteenth: a loop pass counts the
  zero-page operand of a runtime call (`farxzN`) as read, so a far pointer stepped in a loop
  keeps its carry; `autotest/farcharstest.c`'s page-crossing string. Upstream has the same
  pass, but its 32-bit calls don't reach it in a one-block loop that was tried.)
- **Reproducible output.** v1.32.273 and the eight-commit pin read several
  members of their own data structures before anything has written them, so what
  they emit can depend on what the compiler's heap held: the install path, the
  environment, or nothing you can see. Measured 2026-11-13:
  `samples/hires/splitscreen.c` at `-bc -O2` differs between two install paths;
  `autotest/opp_streamtest.cpp` at `-n -O3` compiles to two different programs of
  the same size (both run correctly); for NetHack files that do not fit, the
  listing, the map and the measured size change (`potion.c`: 16,137, 13,257 or
  18,227 bytes), and the code can be wrong (OSCAR64-COMPAT #40, #41). The six
  commits on the local branch `scratch/heap-init-pin` (four on
  `scratch/heap-init-main`) initialise those members; with them the corpus is
  byte-identical between two install paths (735 of 735 builds). To test a compiler
  for this, compile the same source with `MALLOC_PERTURB_=85` and with
  `MALLOC_PERTURB_=170` (glibc fills each new allocation with the complement of that
  byte) and compare every output file. On a compiler without those commits, compare
  two builds of the base before blaming a fix for a `corpus_diff.py` difference.
  Keep install and output paths short: Oscar64's output path buffers are 200 bytes
  (`Compiler.cpp`), and a longer path aborts the compile ("buffer overflow
  detected"), which `corpus_diff.py` then reports as a crash. Leave r26, r28 and
  r29 out of `--src`: they hang or run out of memory, at 180 s per configuration.
