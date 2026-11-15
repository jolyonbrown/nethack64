# Tasks — next up

Small, verifiable tasks for the next sessions. Take the top unclaimed one,
put your agent name and date next to it, tick it when its check passes.
Add new tasks at the bottom of the right section.

## Setup (first session on a new machine)

- [x] T0.1 Run `tools/setup-arch.sh` (or `setup-ubuntu.sh`), then `make && make test` → 5/5 PASS
      — 2026-11-09 Claude (toolchain already installed and checked instead: Oscar64 v1.32.273, VICE 3.7.1, gcc 13.3)
- [x] T0.2 `make repros` → 11 repros, all BROKEN on v1.32.273 (baseline) — 2026-11-09 Claude
      (r12-r35 added since: 35, all BROKEN, 2026-11-12; r28 and r29 hang until run.py's
      120 s timeout, so a run now takes about 4 minutes)
- [x] T0.3 Commit the bundle — github.com/jolyonbrown/nethack64 (old 2020 import kept as tag `upstream-3.4.3`), 2026-11-08 Claude
- [x] T0.4 `make port-tree`, `tools/host-build.sh`, `tests/host_smoke.py` → all ok;
      `port/` committed as the baseline, 2026-11-08 Claude

## Phase 1 — compile everything

- [x] T1.1 Create `port/include/c64conf.h` + hook in `global.h`/`config1.h` (model:
      `pcconf.h`). Define away signals, fork, uids, `TTY_GRAPHICS`; compile out the
      Unix-only services (SHELL, SUSPEND, COMPRESS); keep MAIL, NEWS, WIZARD and every
      gameplay option (cutting any of them is an ADR).
      Check: host build still works with `UNIX` (the C64 config is opt-in).
      — 2026-11-09 Claude, ADR-0006 (not MICRO; host-parity RNG and messages)
- [x] T1.2 Re-run `python3 tools/measure/measure_oscar64.py` with the C64 config; record
      the new baseline in NETHACK-SURVEY.md (dated section). — 2026-11-09 Claude:
      `--config c64` 41 placed / 63 error / 2 crash / 1 hang (UNIX 36/68/2/1)
- [ ] T1.3 Error class "Term starts with invalid token 'else'": find the macro,
      repro or fix, re-measure.
- [ ] T1.4 Error class "Pointer expected" (column 227): reduce one instance to a repro.
- [x] T1.5 "Undefined variable type" for incomplete extern arrays: repro. — 2026-11-09 Claude:
      not a compiler gap; the defining file is missing from the harness (compiles when
      present). Harness fix in T1.10.
- [x] T1.6 `makemon.c` compiler hang, `mhitm.c` abort, `shknam.c` segfault: bisect by
      deleting functions until each compiles; repro; upstream issue. — 2026-11-12
      Claude: gdb on v1.32.273 puts the `shknam.c` segfault in
      `InterCodeBasicBlock::LoadConstantOperand` from `ConstSingleLoopOptimization`
      (compile-time evaluation of a loop over a constant table); start the reduction
      from the file's loops over `shtypes[]` and friends. The ADR-0007 compiler does
      not change it. — 2026-11-12 Claude: all three reduced. `mhitm.c`
      is r26 (#30, fixed by pin commit 8); `shknam.c` is r27 (#11b), the `shkgeneral`
      count in `nameshk()`; `makemon.c` is r28 (#11), a struct copied onto itself, reached
      only through the harness's pointer stubs (r34). Fixes: fork PRs #17 and #18 (T1.9)
      and the pin candidates `pin-shknam-crash` and `pin-makemon-hang` (T1.25).
- [ ] T1.7 Parenthesise the nested `?:` sites (r2) — list them with a grep first.
- [x] T1.8 Work around r15 (`union T *` does not convert to `const union T *`), which
      stops every `add_menu(..., &any, ...)`: NetHack is const-correct here, so this is a
      compiler workaround, not const-correctness fixes. One cast in `winprocs.h`'s
      `add_menu` macro would cover all 87 calls (the 2026-11-09 review saw `apply.c`,
      `pager.c` and `spell.c` reach placement with it in a scratch copy). check_ansi +
      host_smoke; re-measure.
      — 2026-11-14: not needed: the compiler is fixed instead (pin commit 48, T1.40);
      `apply.c`, `artifact.c`, `dungeon.c`, `pager.c` and `spell.c` reach placement.
- [ ] T1.9 Upstream Oscar64 fixes. — 2026-11-12 Claude: instead of issues, 14 fixes
      were written on a local clone of upstream main, reviewed twice each and revised;
      they wait for Jolyon's per-PR decision (`docs/OSCAR64-UPSTREAM.md`, one page per PR
      in `docs/oscar64-upstream/`, patches in `tools/oscar64-upstream/patches/main/`).
      Already fixed on main: r1, r4, r9, r14, r17, r18. Not wanted upstream: r5/r6
      (#438), r11, r13 (#90). — 2026-11-12 Jolyon's decisions (decision page; recorded
      in OSCAR64-UPSTREAM.md): every PR on hold, #14 (r13) not to be sent; fork created
      (github.com/jolyonbrown/oscar64), #1-#13 queued there as `fix/<id>` branches;
      attribution one `Co-Authored-By: Claude` line, no session link. #15-#18 (repros
      r26, r29, r27, r28) are queued there too. Next: when Jolyon approves a PR, rebase
      if upstream moved, do its page's "Before submitting" items, open it, record its
      number in OSCAR64-COMPAT.md.
- [x] T1.10 Measurement harness fixes, then re-measure both configs and re-baseline both:
      find definitions in preprocessed text (`files.c` `close()`, `mon.c` `impossible(`,
      duplicate stubs in `cmd.c`/`end.c`/`mkmaze.c`); variadic stubs with a body that has a
      side effect, e.g. `nh_vl = 0;` (r14: an empty or `va_start`/`va_end`-only body still
      fails); definitions for referenced extern arrays (error 3010); count files that compile
      without referenced code (`dlb.c`, `mkmap.c`, data tables) as compiled, not as errors.
      — 2026-11-12 Claude: also run each compile under a memory cap and report a kill by
      signal 9 (or `std::bad_alloc`) as "compiler-oom", not "compiler-crash": Oscar64 can
      grow without bound (PR #440 on `explode.c`), and on this 15 GB machine the kernel's
      OOM killer then picks the compiler, or something else. — 2026-11-12 Claude: also
      the pointer stubs. `return (T)nh_vp;` (`mkstubs.py` line 58) is not opaque: Oscar64
      merges two such reads (r34), which is what hangs `makemon.c` (r28).
      `return (T)(unsigned)nh_vl;` keeps every read; `makemon.c` then gets through
      v1.32.273 and the pin (fits-not, once a `monstr` table is defined) and measures
      about 1.3% bigger, so the present stubs understate sizes a little. — 2026-11-13
      Claude: three more. (a) The map regex (`measure_oscar64.py`, the `NATIVE_CODE`
      line) takes only four-digit addresses and silently skips a function whose map
      line holds garbage (`fffffffe - 0828 : dodip` in `potion.c`); an unparsable
      `NATIVE_CODE` line should be an error. (b) v1.32.273 and the eight-commit pin
      emit heap-dependent listings and sizes for files that do not fit (#40, #41's
      cause: `potion.c` measures 16,137, 13,257 or 18,227 bytes), so until the T1.21
      commits are in, measure under a zero-filled compiler heap (an `LD_PRELOAD` shim
      that zero-fills each allocation; the round-six runs used one) and compare
      reports only between runs made that way. (c) The `vault.c` "compiler-crash" of
      2026-11-12 (1 in 77 runs) is most likely not the compiler: at 14:06:39Z another
      agent ran `pkill -INT -f "pin/bin/oscar64 -rmp -Os"`, which matches the
      harness's own compile command, while `vault.c` was being compiled
      (reconstructed from timings; the signal was not recorded then). 190 runs since,
      with and without heap fills, never crashed. The harness now records the signal
      of a crash; agents must not `pkill` by a pattern that matches other compiles.
      — 2026-11-14 Claude: done, but for two arrays (T1.35). Definitions come from the
      preprocessed file (`name ( ... ) {` at file scope, in its own lines), and
      `measure_oscar64.py` counts exactly those functions' code. Variadic void stubs
      have a body (r14) and pointer stubs return `(T)(unsigned)nh_vl` (r34): the old
      empty stubs let Oscar64 delete calls, so sizes were low (+4.6% for the files
      placed both times, C64). Unsized extern arrays a file uses are defined from the
      file that has them. Every error 3034 counts as fits-not (also `dlb.c`, `mkmap.c`,
      `vis_tab.c`, and `hack.c`'s static stack); a malformed map line is a map-error.
      The heap-fill item is moot: T1.21's commits are in the pin. C64 61/107, UNIX
      51/107; three files crash the compiler (T1.11).
- [x] T1.11 `files.c` (C64 config) segfaults Oscar64 at `-Os` once `close()` is stubbed
      (`-O0` places it): bisect by deleting functions; repro; upstream issue. Same for
      `questpgr.c` (C64 config), which crashes Oscar64 once the r14 stubs get a body
      (scratch harness, 2026-11-10). — 2026-11-12 Claude: the shknam-crash agent saw
      `files.c` crash the patched pin in `NativeCodeBasicBlock::SplitAt` (native code
      generator), not in any of the r27-r35 paths; no log was kept, not re-checked.
      — 2026-11-14 Claude: both reduced. `files.c` `get_uchars()`, and `mkobj.c`
      `dealloc_obj()` once T1.10's stubs keep calls, are r49 (`SplitAt` on a function's
      exit block), fixed upstream by 46e60d6 (T1.34). `questpgr.c` `load_qtlist()` is
      r50, a `LoadStoreForwarding` crash still on main 16acc53 (T1.33).
- [x] T1.12 Work around r12 (`decl.c` `occtxt = DUMMY` → `= 0`) and r13 (`mail.c`
      `junk[]` → `const char *`) in `port/`; check_ansi + host_smoke; re-measure.
      — 2026-11-14: done, each with a comment naming its repro; check_ansi 108 clean,
      host build and smoke pass. `allmain.c` and `mail.c` compile; `cmd.c` met r12 as
      its second error.
- [x] T1.13 **r18, wrong code:** Oscar64 reads the `char`/`boolean` result of a call
      through a function pointer from `ACCU` while the callee leaves it in A, with no
      diagnostic: at `-Os`/`-O2` once the target is unknown at compile time, at `-O0`
      always. Every `yn(...) == 'y'` (`win_yn_function` returns `char`) and every
      `boolean` callback is at risk. Before game code runs: file upstream (T1.9), check
      whether a newer Oscar64 fixes it, then decide between a fixed or patched compiler
      and a port-side workaround (an ADR if it changes window-proc signatures).
      — 2026-11-12 Claude: fixed on upstream main by 1169268 (2026-09-21), not in a
      release; the ADR-0007 compiler (accepted 2026-11-12) carries it, and the build
      uses that compiler since 2026-11-13 (T1.20). Settled: no port-side workaround.
- [x] T1.14 Work around r16 (`windows.c:113` function pointer `==` function name) and r17
      (`do.c:688` `?:` over two functions), with repro-backed changes in `port/`. The
      obvious r17 workaround, a pointer variable, runs into r18 for `boolean` functions,
      so do it after T1.13. (r17 is fixed on upstream main, c8da6bd; r16 has a fix
      branch, PR #6 in OSCAR64-UPSTREAM.md. Both stay port-side work while we build
      with v1.32.273.)
      — 2026-11-14: r18 is fixed in the pin, and both fixes are pin candidates instead
      (T1.43): r16 is the first error of eight files, r17 of two. No `port/` change.
      Both are in the pin since 2026-11-14 (commits 49-51).
- [ ] T1.15 **Wrong code to settle before game code runs** (OSCAR64-COMPAT.md #22-#28):
      r19 (`p == 0` on a pointer initialised to 0), r20-r22 (negative initialised data
      read as unsigned), r23 (a call through `windowprocs.win_*` overwrites the
      caller's locals), identical functions with stored addresses merged, and r24
      (compile-time evaluation of a pointer test, no fix yet). The ADR-0007 compiler fixes
      all but r24, and the build uses it since 2026-11-13 (T1.20). Then: count NetHack's exposure to each (which files change code with
      each fix; read those diffs), and fix or work around r24. — 2026-11-12 Claude: three
      more (OSCAR64-COMPAT.md #32, #34, #35): r30 (an array element forwarded past an
      overwrite; NetHack not searched), r32 (`t[k]` of a `const` pointer table points 2k
      bytes too far: `sounds.c:83` `throne_msg[2]`, `pager.c:680`) and r33 (`k[c + n]`
      with 2c + 1 elements; no site found). Each has a candidate pin commit (`pin-r30`,
      `pin-1ae3216`, `pin-charidx`; T1.25). r34 and r35 (#36, #37) do not reach game
      code: T1.18, T1.19.
- [x] T1.16 Decide the compiler nethack64 builds with: ADR-0007 (v1.32.273 plus five
      backported wrong-code fixes) or another option it lists. Jolyon. — 2026-11-12
      Jolyon (decision page): ADR-0007 accepted, v1.32.273 plus eight commits.
      — 2026-11-13 Claude: the pin is final. `nethack64/v1.32.273-pin` is at f001eba,
      commit 8's final form, which changes only comments and its test (built in one
      worktree, the c2f5cab and f001eba compilers differ only in 81 `assert` line
      numbers). `tools/oscar64-upstream/patches/pin/` was regenerated with `git
      format-patch --no-signature` (8 patches), and `build-pin.sh` (now `JOBS=N`)
      reproduces f001eba's tree. With f001eba: autotest 1,241 emulations, none failing;
      `corpus_diff` against c2f5cab 726/726 identical; repros r1-r35: 8 pass
      (v1.32.273: 0); NetHack harness: identical reports and listings in both configs.
      Checked again by a second agent. Using it in the build is T1.20; the further
      candidates are T1.25.
- [x] T1.17 r31 (OSCAR64-COMPAT.md #33): at `-Os` Oscar64 aborts (assertion, SIGABRT) in
      `BlockSizeCopyReduction`, which builds `LDY #-1` for the same value stored to three
      or more bytes from offset 0 through a pointer. Hit by `invent.c` `display_pickinv()`
      once `invent.c` gets past its first error (T1.4). Not fixed anywhere: write the fix
      (probably `(mIns[si + 0].mAddress - 1) & 0xff` where the `LDY` is built) for upstream
      main and the pin, with an autotest, or work around it in `invent.c`.
      — 2026-11-14: Codex wrote that fix and a test (`indirectfilltest.c`): r31 and an
      11-line reduction of `display_pickinv` pass in all ten configurations, autotest 1,501
      runs all 0, corpus 960 of 960 identical. In the pin as commits 56-57 (T1.43);
      `invent.c` compiles.
- [ ] T1.18 r34 (#36): two reads of a `volatile` pointer through a pointer cast are merged
      (wrong code on v1.32.273, the pin and main). No game code reads a volatile pointer
      through a cast; the harness's pointer stubs do (the stub change is in T1.10). Write
      the fix for upstream (the pointer-to-pointer `EX_TYPECAST` branch in
      `InterCodeGenerator.cpp` drops `DTF_VOLATILE`) with an autotest.
- [ ] T1.19 r35 (#37): `PropagateVariableCopy` keeps a stale struct copy after a `volatile`
      struct copy (wrong code on every version). NetHack is not exposed (no volatile
      struct copies), so low priority: put the review's trial fix (move
      `ltemps.SetSize(j)` in front of `if (!ins->mVolatile)`) through the autotest and the
      corpus, with an autotest of its own, for upstream.
- [x] T1.20 Switch the build to the ADR-0007 compiler. `tools/setup-ubuntu.sh` and
      `tools/setup-arch.sh` build it with `build-pin.sh` (`JOBS` for the `make -j`, and a
      way to get the plain release for comparisons); the Makefile, AGENTS.md ("pinned:
      v1.32.273"), TOOLCHAIN.md, README and OSCAR64-COMPAT.md's header say "v1.32.273 +
      nethack64 patches (ADR-0007)". Then `make`, `make prg`, `make test`, `make repros`
      (r1-r35: 8 pass) with it, re-baseline the measurements (T1.10) and update the
      workaround column of the rows it fixes.
      — 2026-11-13 Claude: done. Both setup scripts tested on scratch copies (both modes).
      Here `oscar64` -> `~/src/oscar64-pin` (tree 7de21ef), `oscar64-plain` -> the
      release. `make -B`: `nethack-ef.crt` byte-identical to the release build
      (sha256 fbc83167...); `make prg`; `make test` 5/5; `make repros` 8 of 44 pass
      (r18-r23, r25, r26; r40-r44 broken as recorded). Re-baselined both configurations
      (NETHACK-SURVEY.md, 2026-11-13 section): 44 of 107 (C64) and 39 (UNIX) reach
      placement. Rows #22-#27, #29, #30 updated.
- [x] T1.21 Heap-dependent output and two wrong-code bugs (OSCAR64-COMPAT.md #40, #41;
      r38, r39). v1.32.273 and the pin read members nothing has set: `LinkerObject`
      addresses of objects never placed, `LinkerSection` start/end,
      `InterInstruction::mRemove` (r38: a caller loses its call frame; `teleport.c`
      `u_teleport_mon`), `NativeRegisterData::mFlags`, `IntegerValueRange` min/max,
      `InterCodeBasicBlock` entry counts and `InterCodeProcedure::mStoresIndirect` (r39).
      Six commits on the local branch `scratch/heap-init-pin` (on f001eba): 03a460a
      (upstream fbca293, `mRemove`), d7c9e1b, 3fe242d, c9589f6, 8286734 (the
      `DestroyingMem` test upstream got in 4969258), 11ef264. Measured 2026-11-13 and
      checked by a second agent: autotest 1,241/1,241; corpus against the pin 729 of 735
      byte-identical (the six: `opp_streamtest.cpp` `-n -O3`, whose output on the pin
      itself depends on the heap, and r39, which the commits fix); 45 non-fitting
      NetHack files identical under six heap fills; r38 and r39 FIXED. Before they can
      be offered: 8286734's message and its patch credit 963b29c (2026-09-28) where
      4969258 (2026-10-18) is right (963b29c added `ModifiesIndirect()`; 4969258 made
      this test use it), and all ten commits on the two branches carry a
      `Claude-Session` trailer, which upstream-bound commits must not. Reword them
      when the T1.25 candidates are finalised, so their ids change once. Candidates
      for the pin (T1.25). For upstream: the
      four commits on `scratch/heap-init-main` (on 4da3147; autotest 1,541/1,541).
      — 2026-11-13 Claude: in the pin as commits 18-23, reworded as above (ADR-0007).
      With them the C64 measurement gives identical listings with the heap filled with
      0xA5 (NETHACK-SURVEY.md). The four commits for main wait with the other PRs (T1.9);
      their messages still need the same rewording.
- [ ] T1.22 r36 and its family (OSCAR64-COMPAT.md #38, #42-#45; r36, r40-r43). r36: `InnerLoopOptimization` moves a loop-invariant
      assignment in front of a loop that reads the old value first (wrong code at every
      level but `-O0` on v1.32.273, the pin and main). No NetHack site: an instrumented
      pin logged none in the 44 files that reach code generation nor in `src/`; 63 files
      do not compile yet and were only searched by hand, so measure again as they start
      to compile. Our fix with an autotest: `scratch/r36-fix-pin` 26a9c12 (pin autotest
      1,251 emulations, none failing), `scratch/r36-fix-main` 550e9a3 (full autotest not
      run on main). The same work found, each with a repro, its own row and a local fix
      (2026-11-13; repro claims re-measured by Codex, headers corrected):
      r40, the native-code twin (5997864 on the pin, 3ac93dd on main; 2bede01, 8cae5da
      and 7a4f9ff on top of 5997864 cure a parameter form it leaves wrong, and r43);
      r41, a compiler abort in `SingleBlockLoopOptimisation` (e5b8d38, 8affaca); r42, an
      unsigned char read back unwrapped behind a loop (`scratch/r42-backport-pin`:
      upstream 57655c5's hunk plus a guard: upstream's hunk alone zeroes a pointer
      compared with a pointer conditional, which main 4da3147 does, NetHack's
      `known_hitum()` included); r43, a native pointer form (67d2908, 6f811e3, or
      7a4f9ff). No NetHack site for any of them in the files that compile. Open: an
      autotest for the r43 fix; full autotests of the main builds; signed narrowing
      (`gs = 126 + (i & 3)`) wrong everywhere, no repro yet; which join the pin (T1.25).
      Also seen, not exposed: a `long` accumulated in a loop is wrong in bytecode at
      `-O2`/`-Os`/`-O3` on v1.32.273 and the pin (main right; NetHack is native code).
      — 2026-11-13 Claude: r36, r40 and r41 are in the pin (commits 24-28); r42 and r43
      joined on 2026-11-14 (commits 29-32). Still open: signed narrowing (no repro yet)
      and full autotests of the main builds.
- [x] T1.23 r37 and its sibling (OSCAR64-COMPAT.md #39, #46; r37, r44). r37: the native
      peephole pass forwards a stored byte past a call that overwrites the register it
      came from, so the low byte of the call's result is read from the stored byte
      (v1.32.273, the pin and main). No NetHack site in the files that reach code
      generation (also with `__noinline` stubs); `mhitm.c` and `mkobj.c` unchecked. Our
      fix (17 lines) and autotest `callresultforwardtest.c`: `scratch/r37-backport-pin`
      (c9f86f6, 3eef9b8; autotest 1,251/1,251), `scratch/r37-fix-main` (feff01f; full
      autotest not run on main). r44, found by its verifier: the walk also passes a
      callee that writes the global through a pointer (`STA (zp),y` is not counted as
      a store), native code, v1.32.273, the pin and main. In the harness's listings
      `make_hallucinated()` (`potion.c:248`) tests `old` as `HHallucination` behind
      `set_itimeout(&HHallucination, xtime)`; without the harness's address-taking the
      pin inlines `set_itimeout` there and gets it right, so check the game build's
      listing once `potion.c` links. Our fix and autotest: `scratch/r44-fix-pin`
      (8890301, cf8dd6f; autotest 1,261, none failing; verified by a second agent).
      Not covered: calls through a function pointer (`JSR bcexec`); with the fix one
      probe turns wrong at `-O0`: that is r45 (T1.26), which the pin already gets wrong
      at `-O2`/`-Os`/`-O3`. — 2026-11-14 Claude, under Jolyon's go-ahead: in the pin as
      commits 35-38, after r45's fix (33, 34); together the `-O0` probe gives 0 in all ten.
      The main-branch form (`scratch/r37-fix-main`) waits with the other PRs (T1.9).
- [ ] T1.24 Wrong code at the default optimisation level only, native code (mutual
      recursion; a local's address passed on is taken at the wrong stack offset): on
      v1.32.273, the pin and main; right at `-O0`, `-O2`, `-Os`, `-O3`, so nethack64's
      `-Os` build is not affected as tested. Unreduced:
      `tools/oscar64-upstream/cases/default_level_mutual_recursion_local_address.c`.
      Reduce, find the cause, report upstream when PRs resume.
- [x] T1.25 Decide what joins the pin (Jolyon, on the decision page; each then goes
      through ADR-0007's checks and a new patch export). — 2026-11-13 Jolyon: "Add" on
      ten rows; Claude: they are commits 9-28 of the pin (ADR-0007): the six candidates
      (`nethack64/pin-1ae3216`, `pin-shknam-crash`, `pin-makemon-hang`, `pin-charidx`,
      `pin-walks-display`, `pin-r30`), the heap-initialisation commits (T1.21) and our
      fixes for r36, r40 and r41 (T1.22). Messages as planned: no session links,
      upstream's c5ac062 without our trailer, b52c9fe and 8286734 corrected. Five of the
      first eight patches keep their session links: rewording them would change every
      commit id from commit 2 on. r42 and r43 joined on 2026-11-14 as commits 29-32, once
      their reviews were done (ADR-0007). r37+r44 went back to Jolyon (its `-O0` probe was r45,
      T1.26); on 2026-11-14 Claude added r45's fix with r37+r44 as commits 33-38, under
      Jolyon's go-ahead ("You go ahead ... push what you need"). No candidate is left;
      new ones get tasks of their own.
- [x] T1.26 r45 (OSCAR64-COMPAT.md #47): a `char` result made from two values read
      before a direct call to an address-taken function is never computed (native code;
      the pin and main at the default level, `-O2`, `-Os` and `-O3`; v1.32.273 at the
      default level only). The pin's commit 3, upstream bf42402 (the r25 fix), exposes
      it; the r44 fix extends it to `-O0`. Find the cause in the native back end, fix it
      (ours first; upstream when PRs resume), and search NetHack for the shape with an
      instrumented build, as for r36. Until then: the repro's workarounds. Then decide
      r37+r44 (T1.25).
      — 2026-11-14: cause found by Codex and checked by Claude (OSCAR64-COMPAT.md #47):
      `MoveCLCLoadAddZPStoreUp` moves an add and its store into `$1b` above a call that
      writes `$1b`. Fix and autotest on `codex/r45-fix` (e8207f5, b7d5ea1): 0 in all ten,
      autotest 1,351 with no failure; no NetHack site in the 45 files that compile.
      In the pin as commits 33-34 (2026-11-14), with r37+r44 (T1.25).
- [x] T1.27 r46 (OSCAR64-COMPAT.md #48): a pointer argument kept in a parameter
      register is reused after a call whose callee advanced it through its address
      (`sscanf` then `strcmp` with the same literal; native code at `-Os` only, on
      v1.32.273, the pin and main). Found by Codex reviewing r42. Find the cause and
      search NetHack for callees that advance a pointer parameter through its address.
      — 2026-11-14: cause found and fixed by Codex, checked by Claude (OSCAR64-COMPAT.md
      #48); in the pin as commits 39-40 under Jolyon's go-ahead. No NetHack site goes wrong.
- [x] T1.28 `tests/host_smoke.py` types keys on a fixed 0.1 s clock and never waits for the
      game: on 2026-11-14 a CI runner missed the restore greeting (run 43536929831, green
      on re-run, nothing host-related changed). Wait for each screen with pexpect instead.
      — 2026-11-14: rewritten. After each command the driver types `v` and reads up to the
      version line, answering --More--, menus, y/n and naming prompts on the way; both
      sessions must then exit by themselves with status 0, so a crash shows as a signal.
      0.6 s; the old test took 47-109 s (three timed runs). Its fixed clock let the first
      --More-- swallow the rest of the walk and, at times, the scripted quit. That CI
      failure was not a slow runner: no key is read during a restore, and its restore
      ended inside `dorecover()` with no message. Not reproduced (NETHACK-SURVEY.md:
      `tools/smoke_stress.py`, and `tools/host-build.sh --sanitize`). CI now uploads the
      transcripts when the job fails.
- [x] T1.29 The sanitizer host build reports three over-reads, all in NetHack 3.4.3 itself
      (NETHACK-SURVEY.md). `savefruitchn()` writes its 48-byte terminator from the
      40-byte `nul`, and `free_window_info()` reads `wins[WIN_MESSAGE]` once the message
      window is gone (`wins[-1]`, at each death): host-only (`struct fruit` is 36 bytes
      on the C64, and `wintty.c` is not in the C64 build). `makeplural()` tests
      `strcmp(spot-7, "shuriken")` for names of 5 letters or more, so it reads up to 3
      bytes before `bufs[0]`: on the C64 too, harmless unless `bufs` follows the
      `$DF00-$DFFF` page. Fix all three in `port/`; no fix changes behaviour.
      — 2026-11-14: fixed, with a fourth read found by checking every `spot-N` in
      `makeplural()`: `strcmp(spot-5, "matza")` under `len >= 5`, which can never match
      (six characters against five). `nul` is sized to the longest record save.c
      writes from it (48 bytes on the host; still 40 under Oscar64, `struct fruit` 36,
      `struct trap` 11), `free_window_info()` checks `WIN_ERR`, and both plural tests
      have length guards. Old and new `makeplural()` agree on 105,034 words under 7
      fills of the 4 bytes before the buffer, except where those bytes decided the old
      answer ("riken", "uriken", "huriken" after "shu", "sh", "s"). C64 assembly and
      map of `decl.c` unchanged.
- [x] T1.35 Harness arrays still undefined: `SAVEF` (its size, `SAVESIZE`, is defined
      only in `files.c`; `save.c`'s first error) and the generated `monstr[]` (`makemon.c`,
      `wizard.c`, `pray.c`, `muse.c`): have `--generate-only` run `makedefs -m` as it does
      for `vis_tab.c`, and give the harness `SAVESIZE`.
      — 2026-11-14: done. `monstr.c` is generated into `port/src` (108 files measured);
      array definitions are copied from the defining file's preprocessed text, so
      `SAVEF[(32 + 13)]`. With 44 commits: C64 68/108, UNIX 55/108, no compiler crash.
- [x] T1.34 Jolyon: add upstream 46e60d6 (r49's fix) to the pin? On the decision page
      since 2026-11-14. If added: ADR-0007's checks, as for the earlier rounds.
      — 2026-11-14: added on his go-ahead ("you go ahead") as commits 41-42; ADR-0007's
      checks passed (results there). It fixes r9 as well.
- [ ] T1.46 r61 (compat #63): a function-like macro's name with no `(` after it is expanded.
      — 2026-11-15: Codex's fix and test (`fix/r61-macro-name`, 51d2c27 and a6ed6bb; the
      scanner looks past white space and comments for the `(` before treating the name as an
      invocation). Codex: autotest 1,531, no failures; corpus 983 identical, r61 and its test
      fail -> pass; reviewed here (diff and test). Still to do: the NetHack listings with it,
      then a pin candidate for Jolyon. Codex also noticed, not yet checked here: stringizing
      leaves a trailing space, and `##` beside a parameter written with spaces misbehaves.
- [ ] T1.45 `mhitm.c` aborts the compiler since the stubs became `__noinline` (T1.42):
      "mIndex == 1000 || mNumEntries == mEntryBlocks.Size()" in
      `NativeCodeBasicBlock::RemoveUnusedResultInstructions`, compiling `mattackm()`, with
      the 59-commit compiler. Codex found the cause (`codex/r60-mattackm`, uncommitted):
      `JoinEntryLoadStoreZP` moves an entry block to a new block without decrementing
      `mNumEntries`; with `mNumEntries--;` added, `mhitm.c` compiles and 911 autotest runs
      pass. Its run was then cut off by the service ("flagged for possible cybersecurity
      risk") before a minimal repro, the full autotest or a test. Finish those, then a pin
      candidate for Jolyon.
      — 2026-11-14, later: a second Codex run committed the fix (b2a7090 on
      `codex/r60-mattackm`) and was cut off the same way while reducing `mattackm()`, which
      may itself be what the filter dislikes (monster combat code). Repro, test and checks
      left to Claude.
      — 2026-11-15: done, as pin candidate commits 60-61 (branch `codex/r60-mattackm`, 85030a2;
      Codex's fix, Claude's test `joinentryzptest.c`), for Jolyon's decision. Repro r60 (34
      lines; compat #62) aborts on v1.32.273, the pin and upstream main (7a37b06) at every
      native level. With the fix: autotest 1,531 emulations, none failing (1,521 before, plus
      the new test's 10); corpus 984 of 984 programs identical, the new test and repro crash
      -> ok; the other 107 NetHack files' listings, maps and labels identical; `mhitm.c`
      compiles (23,380 B); `.crt` 875297a7 and `.prg` 2a6c8dfd unchanged; `make test` 5/5.
- [x] T1.44 Two compiler aborts left in the C64 run, both in the native code generator
      at `-Os`: `muse.c` (`rnd_defensive_item`: an index assertion in
      `NativeCodeBasicBlock::BinaryAddCarry`, with the 48 commits; it showed once the
      stubs kept the calls' arguments, T1.42) and `invent.c` (`display_pickinv`, once
      T1.43's candidates let it compile that far): r31, known since 2026-11-12 (T1.17).
      Codex is reducing the first and writing a fix and a test (`build/oscar64-wt/r60-fix`);
      then a repro, a compat row, and a pin candidate if the fix holds.
      — 2026-11-14: r31 fixed by Codex (`codex/r59-fix`), as T1.17 proposed. The `muse.c`
      abort is r59 (compat #61): a byte constant plus booleans,
      `rn2(8 + (difficulty > 3) + ...)`, at every native level; Codex found the cause and
      fixed it (`codex/r60-fix`). Both fixes and their tests are pin commits 56-59 (T1.43).
- [x] T1.43 Jolyon: add seven commits to the pin as 49-55? Our r16 fix (fork draft #6,
      compat #20), upstream's c8da6bd for r17 (compat #21) with our test, our fold of
      `!` on constants (r53, compat #55) with a test, and our r52 fix (`!!x` folded to
      `x`, wrong code, compat #54) with a test. Branch `nethack64/pin-cand-49c`
      (`build/oscar64-wt/pin-c49c`); ADR-0007's checks are running. With them 11 of the 12
      remaining C64 files compile; `invent.c` then aborts (T1.44).
      — 2026-11-14: added as commits 49-55 on his go-ahead ("add all of them to the pin"),
      with T1.44's two fixes as 56-59; ADR-0007's checks passed (results there). C64
      108/108 (1,252,234 B), UNIX 97/108. r53's `options.c` workaround is undone.
- [x] T1.42 The harness's stubs (T1.10) let `-Os` delete every call to an empty void stub
      and drop arguments nothing read, so each file's code was under-counted; a `?:`
      argument for such a parameter also hit r58 (`timeout.c`, `do.c`). Make stubs read
      their parameters; also stub `extern.h`'s two prototypes without `E` and functions a
      file declares itself (`sp_lev.c`), reference non-static functions no header declares
      (`mkmap.c`), and copy the static arrays a copied array names (`shk.c`).
      — 2026-11-14: done. Code measured ×1.33 for the same files (C64; UNIX ×1.34), and the
      code-size estimate is ≈ 1.0 MB, not ≈ 0.85 MB (NETHACK-SURVEY.md, ARCHITECTURE.md).
      With 48 commits: C64 95/108, UNIX 86/108; `muse.c` now aborts the compiler (T1.44).
      — 2026-11-14, later: and the stubs are `__noinline`: Oscar64 had inlined the smallest,
      so their stores were measured in place of calls, and the calls were missing from the
      listings. Code ×0.947 (≈ 1.19 MB in all); `mhitm.c` now aborts the compiler (T1.45).
- [x] T1.41 The first errors of the 23 C64 files left with 48 commits, sorted out: r16 (8
      files) and r17 (2) have fixes (T1.43); new repros r52 (`!!x`, wrong code), r53 (`!`
      of a constant in an initializer), r54 (comma expression as a condition), r55 (`const
      static`), r56 (`default:` in a nested block), r57 (several function declarators in
      one declaration), r58 (harness only; T1.42), compat #54-#60; and harness gaps in
      `shk.c` and `sp_lev.c` (T1.42).
      — 2026-11-14: r53-r57 worked round in `port/` (the normaliser for r54 and r55, one
      commented edit each in `options.c`, `trap.c`, `mkroom.c`), and r12/r13 (T1.12).
      check_ansi 108 clean, host build and smoke pass, `make test` 5/5 with the `.crt` and
      `.prg` unchanged. All seven are on upstream main (16acc53) too; issue texts drafted
      in the session note.
- [x] T1.40 Jolyon: add our r15 fix (a8ecf65, fork draft #7; compat #19) to the pin as
      commit 48? On the decision page since 2026-11-14, checked on top of the 47 commits
      (`build/oscar64-wt/pin-r15`): autotest 1,461, corpus 910/910 identical, NetHack
      unchanged where it compiled; C64 85/108, UNIX 71/108.
      — 2026-11-14: added as commit 48 on his go-ahead ("add the r15 fix to the pin too").
- [x] T1.39 Codex's r51 work found two more compiler bugs, not yet reduced into repros:
      calling a conditional function-pointer expression directly crashes the compiler
      (also with an explicitly cast null), and taking the address of a scalar `const
      int` is rejected (`build/oscar64-wt/r51-fix/r51-evidence/existing-*`). Reduce, check
      NetHack for the shapes, file as repros.
      — 2026-11-14: Codex's reductions are already minimal (4 and 2 lines). NetHack has
      neither shape (no direct call of a `?:`; no address taken of a file-scope `const`
      scalar), so they are recorded in OSCAR64-UPSTREAM.md's list of bugs found on the
      way, not as repros.
- [x] T1.38 Jolyon: add upstream 160c92b (r1, the cast before `->`: the "Pointer expected"
      class) and the r51 fix as commits 45-47? On the decision page since 2026-11-14,
      checked as a stack on top of the 44 commits (`build/oscar64-wt/pin-cast`): C64
      73/108 with 160c92b, 80/108 with both.
      — 2026-11-14: added as commits 45-47 on his go-ahead ("yes, add both to the pin").
- [x] T1.37 r51 (OSCAR64-COMPAT.md #53): `c ? p : 0` is rejected ("Incompatible
      conditional types"), the null pointer constant not being taken for a pointer; the
      first error of `pray.c`, `muse.c`, `shk.c`, `mon.c`. A compiler fix (Codex, own
      worktree `codex/r51-fix`), then a pin decision for Jolyon; a `port/` workaround
      would mean a cast at every site.
      — 2026-11-14: Codex's fix (`codex/r51-fix` ffa7192, test c41f07e) turns an integer
      constant expression of value 0 opposite a pointer into a typed null, in
      `ParseConditionalExpression`, and keeps a flag through constant folding so `const`
      variables and float zeros do not qualify. Checked by Claude (enum/macro/sizeof
      zeros accepted; `const int` 0, 1 rejected). Decision: T1.38.
- [x] T1.36 Jolyon: add the r50 fix (T1.33) to the pin as commits 43-44? On the decision
      page since 2026-11-14, checked on top of commits 41-42.
      — 2026-11-14: added on his go-ahead ("add the r50 fix to the pin too").
- [x] T1.33 r50 (OSCAR64-COMPAT.md #52): Oscar64 segfaults in `LoadStoreForwarding` on
      `g = fopen(...); f("x");` (`f` storing to a global) at `-Os`/`-O2`/`-O3`:
      `questpgr.c` `load_qtlist()` under the C64 configuration. Release, pin and main
      16acc53 alike. Find the cause and a fix on a branch (a pin decision for Jolyon).
      No port-side workaround yet: it needs Oscar64's own `fopen()`, which the C64
      file layer (T2.4) may replace.
      — 2026-11-14: cause found by Codex, checked by Claude. `SimplifyIntegerNumeric`
      copied a folded address's variable index into an indirect store or load but not
      its memory base; once `fopen()`'s filename buffer is promoted to a global, a store
      keeps `IM_LOCAL` with the global's index and `LoadStoreForwarding` reads a null
      `mLocalVars` entry. Two-line fix and a test on `codex/r50-fix` (cf729e1, 44421bb),
      cherry-picked as candidate commits 43-44 (`build/oscar64-wt/pin-r50`): autotest
      1,411 all 0; corpus 878 of 879 identical, the other a block reordering with the
      same result (`opp_hashmap.cpp`, `-bc -O2`); NetHack listings and maps unchanged,
      `questpgr.c` compiles; repros 28 of 50. Decision: T1.36.
- [x] T1.32 r48 (OSCAR64-COMPAT.md #50): `a ? b ? x : y : z` is rejected ("':' expected"),
      `pray.c`'s first compile error. — 2026-11-14: the middle operand is parsed as a
      logical-OR expression (also on upstream main). Parentheses at the 3 sites a token
      scan of `port/` finds (`pray.c` 789 and 791, `shk.c` 2668). Issue text drafted.
- [x] T1.31 r47 (OSCAR64-COMPAT.md #49): an `else` after a braceless `if (c) goto L;` is
      rejected; it was the first compile error in seven files (artifact, bones, detect,
      hack, mklev, shk, sp_lev). — 2026-11-14: the `TK_GOTO` case of
      `Parser::ParseStatement` leaves its `;` (also on upstream main). `oscar_normalize.py`
      wraps such a goto in braces: 10 sites. Issue text drafted in the session note.
      `detect.c` (both configs) and `mklev.c` (C64) now reach placement: C64 47/107,
      UNIX 41/107 (NETHACK-SURVEY.md).
- [x] T1.30 `tools/oscar_normalize.py` parenthesizes `sizeof x` (compat #6) but not
      `sizeof` of a string literal: five sites (`invent.c` 2553, `objnam.c` 1166 and
      1190, `options.c` 303, `pline.c` 196). It is the first compile error in `objnam.c`
      and `pline.c`. Extend `SIZEOF_RE`, re-run it on `port/`, re-measure.
      — 2026-11-14: done; r3 now covers the literal too. The re-run changed those five
      sites and a comment in `you.h`; a second pass changes nothing. Both configs:
      `objnam.c` now stops at line 2146 instead of 1166 (`else` after a braceless
      `if (...) goto x;`, a new compiler gap), `pline.c` only at the harness's own stub
      for `pline` (defined through `VA_DECL`, T1.10), `invent.c` and `options.c` at
      their earlier errors as before. Totals unchanged: C64 45/107, UNIX 40/107.

## Phase 2 — spikes (after Phase 1 is mostly green)

- [ ] T2.1 Banking spike A (EF execute-in-place, trampolines) with hack.c + apply.c + zap.c
      — 2026-11-14: measurements, coupling, constant data, hardware and Oscar64's 64-bank
      limit in docs/BANKING-SPIKE.md; a first simulation from gprof call counts
      (`tools/profile_play.py`, `tools/measure/bankpart.py`): about 80 calls a turn leave
      their bank with an 8 KB resident core; next a wider profile, prototypes, ADR-0008.
      — 2026-11-14: VICE prototype `tests/spikes/bankcall.c`: a bank switch through a C
      trampoline costs 34 cycles; an REU fetch about 1,090 cycles per KB.
      — 2026-11-15: `tools/bank/bankgen.py` rewrites the source for a bank plan (pragmas,
      a renaming macro for calls within a bank, resident trampolines); the whole game
      built from it on the host (`tools/host-build.sh --banked`, 2,142 functions in 84
      banks) passes the smoke test and a 6,000-command bot game with every banked
      function checking its bank on entry. Oscar64 past 64 banks: Codex's patch
      (`fix/banks-past-64`, 75d6b73), checked, a pin candidate for Jolyon. Next: the
      Oscar64 build of the rewritten source, literals kept by callees (`killer`).
- [ ] T2.2 Banking spike B (REU overlays) with the same files (BANKING-SPIKE.md)
- [ ] T2.3 RAM map for dynamic state; BUFSZ policy ADR
- [ ] T2.4 REU RAM-disk file layer with an AUTOTEST
- [ ] T2.5 Compress `data`/`quest.dat`/`rumors` three ways; table of ratios + decode speed
- [ ] T2.6 Host build variant with `COMPRESS` off, so `host_smoke` exercises the
      RLECOMP/ZEROCOMP save code the C64 uses (ADR-0006); before Phase 5 saves
- [ ] T2.8 Oscar64 compiles the whole game in one run (the banked build has to):
      — 2026-11-15: it did not finish in an hour (`tools/bank/build_c64.py`). Two global
      analyses walk every path through the call graph's cycles (r62, compat #64): NetHack's
      direct calls form one cycle of 279 functions, and with calls through pointers one of
      2,465. (a) `MarkRecursions`: Tarjan's search, exact (308/308 programs), candidate pin
      commit ab12523 on `fix/scc-recursion`. (b) `CheckFastcall`: open. A first rewrite that
      gives every member of a cycle stack parameters (`scratch/fastcall-scc-v1`) gets past the
      analysis in 31 s, but changes 29 of 983 corpus programs: the old walk cuts a cycle
      through a pointer call where its path meets itself, and keeps fastcall parameters for
      the 426 functions on such cycles in NetHack. Next design: true recursion (direct
      cycles) as one unit with the largest area reachable, pointer back edges cut as before,
      every function worked out once. (c) Then the compile needs more than 3 GB
      (`std::bad_alloc` under the cap; `BANK_MEMORY_MB`). (d) The harness's `nh_refs[]`
      takes every function's address, which makes Oscar64 give them all stack parameters:
      measure code size with calls instead, since 1.19 MB is probably high.
- [ ] T2.7 RNG + clock ADR before Phase 3 first light: which generator implements
      `lrand48`/`srand48` (exact, for seed-for-seed replays vs the host, or faster), seed
      width, clock source for seeding, moon phase, Friday 13th and `night()`/`midnight()`

## Housekeeping

- [x] H1 CI green on GitHub Actions (`.github/workflows/ci.yml`) — first run on master
      green (run 42530155008, 2026-11-08), checked 2026-11-09 Claude
- [ ] H2 Decide repo visibility/licensing note (NetHack GPL-like licence applies to port/)
