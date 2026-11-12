# Fixing Oscar64 upstream

How we turn Oscar64 bugs found by the port into fixes that could go upstream
(github.com/drmortalwombat/oscar64). A fix becomes a pull request only after
Jolyon has read its explanation and said yes. Until then, branches stay local.

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
    that fails before the fix and passes after it;
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
