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
- [x] T1.47 r63 (compat #65): **wrong code** from a call with constant arguments, evaluated
      while compiling, to a function with a parameter it never reads: the unused parameter is
      renumbered as a local and takes a used parameter's index, so `pick(7, 2)` of
      `int pick(int a, int b) { return a; }` folds to 2 (-O2, -Os, -O3; the pin and upstream
      main alike). Found 2026-11-15 in the banked whole-game compile (`fqname()` folded to
      `SCOREPREFIX`); invisible to the per-file measurement, whose harness takes every
      function's address. Fix and test written here (`fix/r63-unused-param`, 50193ec and
      aaaff45: the interpreter binds nothing for an unused parameter). r63, the fqname-shaped
      variant and the nested-call variant fail on the pin and pass with it in every
      configuration; autotest 1,531/1,531; corpus 985/993 identical, the 8 that differ being
      r63 and the new test where the bug fires (-O2, -Os, -O3, bytecode -O2). In the pin as
      commits 66-67 (2026-11-15, Jolyon's go-ahead; ADR-0007).
- [x] T1.48 r64 (compat #66): `PropagateVariableCopy` forwards a load to a struct copy's
      source without its memory base, so the load claims a local with index -1 and
      `LoadStoreForwarding` aborts at the next call (and alias analysis is misled before
      that). Found 2026-11-15 in the whole-game compile with linker bank stubs
      (`dungeon.c` `lev_by_name()`); the pin, v1.32.273 and upstream main alike. Fix and test
      written here (`fix/r64-copy-memory-base`, 9f46cee and 893f954): autotest 1,581/1,581;
      corpus 1,022/1,022 identical; r64 and the test crash -> ok everywhere; NetHack C64 listings
      324/324 identical. In the pin as commits 70-71 (2026-11-15, Jolyon: "add both to the pin").
- [ ] T1.46 r61 (compat #63): a function-like macro's name with no `(` after it is expanded.
      — 2026-11-15: Codex's fix and test (`fix/r61-macro-name`, 51d2c27 and a6ed6bb; the
      scanner looks past white space and comments for the `(` before treating the name as an
      invocation). Codex: autotest 1,531, no failures; corpus 983 identical, r61 and its test
      fail -> pass; reviewed here (diff and test). Still to do: the NetHack listings with it,
      then a pin candidate for Jolyon. Codex also noticed, not yet checked here: stringizing
      leaves a trailing space, and `##` beside a parameter written with spaces misbehaves.
- [x] T1.45 `mhitm.c` aborts the compiler since the stubs became `__noinline` (T1.42):
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
- [ ] T1.49 Compiler speed for NetHack's idioms, after T2.10 (Jolyon, 2026-11-15: "the compiler
      fixes afterward as you see fit"): constant multiplies by shifts and adds, byte-index
      tables up to 256 entries, division by constants, narrowing of promoted `xchar` loop
      variables (RAM-PLAN.md, the brainstorm); pin additions with an explanation each.
      — 2026-11-16: per-factor multiply routines measured on paper first: 1,551 calls of
      `mul16by8`, 35 factors, 26/126/55/42 = 87%; about 2.5x faster each, but 1-2 KB more
      resident code; the hottest (126, 42) went to column tables in the source instead
      (T2.10). Kept for later, with the resident budget.
      — 2026-11-16: the padding (T2.11, ADR-0009 point 5) made 26 and 55 shifts: 320 calls gone
      from the files' own functions. What is left of `mul16by8` is small (0.2% of `mfndpos`).
      The emulator's profile by address points elsewhere: `mfndpos` saves and restores 46 bytes
      of zero page each call, 1,244 cycles, 10% of its time; over the whole game, by the listing
      and the bot's call counts, about 259,000 cycles a turn go to such saves (`m_move` 55,000,
      `mfndpos` 46,000, `newsym` 33,000, `dochug` 31,000). First T1.49 change: save only what
      the callers need.
      — 2026-11-16: done, pin commits 79-80 (`-Ot` in `-Os`; `-xb`, which our builds now pass,
      for programs that never return to BASIC): `mfndpos` 6.8% faster in the harness; the whole
      game's saves 12% fewer cycles a turn (277,000 -> 243,000), banked code 3.7 KB smaller.
      Most of what stays is owed to address-taken functions (command handlers, callbacks),
      which keep everything; next, group calls through pointers by type (RAM-PLAN.md).
      — 2026-11-16: grouping by type tried, no gain: all 17 types need the whole area, from the
      unions over their many call sites (RAM-PLAN.md). Dropped. Next: the multiply/divide items.
      — 2026-11-16: the other items measured (Oscar64's emulator, -Os, pin 80): `rn2()`'s 32-bit
      modulo 1,354 cycles a call, about 18 calls a turn, 24,000 cycles a turn; a 16-bit division
      or modulo by 10 about 440; multiplies now 0.2% of `mfndpos`. Each is 1-2% of a turn while
      the game cannot run yet, so the rest of T1.49 waits behind ADR-0008 and T2.12. First when
      it resumes: a 32-bit modulo with a 16-bit divisor in the runtime (`rn2`).

- [x] T1.50 Zero page past $8F (compat #72, r69): Oscar64 gives a function the temporaries it
      needs past the end of its area, unchecked, where the KERNAL's IRQ changes them.
      — 2026-11-16: the pin warns (commit 74: warning 2025, with the function and its highest
      address; `#pragma warning(error: 2025)` makes it an error; `make repros` counts r69 as
      diagnosed). `tools/check_listing.py` runs in `build_c64.py` (the whole game: `m_move`'s
      $8B highest, T1.54) and `calibrate.py` (the harness now within $8F,
      re-published). Spilling what does not fit is compiler work for ADR-0009 (with all four
      types far, `mfndpos` needs $90). Upstream's own `mmultest.c` reaches $99/$A0 at -O3.
      The per-file C64 measurement (each file alone, more inlined) puts `m_move` at $9D and
      `dog_move` at $98 (2026-11-16; $9C and $95 before T2.10): T1.54.
- [x] T1.51 A branch out of range in a folded copy loop at -Os (compat #73, r70): fixed in the
      pin, 2026-11-16 (commit 75, test 76): a loop takes the copies that fit in 128 bytes and
      the rest get a loop of their own. None in the game's listing (2026-11-15).
- [x] T1.52 ~~Oscar64 hangs at -Os~~ on a line reducer's candidate of the speed harness
      (`mfndpos` with `wantpool = FALSE; goto nexttry;` inside the position loop): not the
      compiler (2026-11-16). Without `-e` the pin compiles it at -Os in 8.4 s (368 MB, the
      "hang"'s figure) and writes the program; with `-e` that program runs on in the
      emulator, since the loop never ends and writes past `poss[9]` and `info[9]`, undefined
      behaviour that the -O2 build happens to stop on (-1). The reducer's check runs in the
      emulator, so it timed the program, not the compile.
- [x] T1.53 A copy loop's branch one byte short at -Os (compat #74, r71): the folding of #73
      counted an absolute address below 256 as three bytes, which the assembler writes in two
      (a constant pointer into the zero page, the parameter registers), and the BPL landed in
      the `LDX`'s operand. Found by `check_listing.py` in `hmon_hitmon()` of the C64
      measurement's `uhitm.c` listing; none in the whole game's 2026-11-15 listings. Fixed in
      the pin, 2026-11-16 (commit 77, test 78).
- [x] T1.54 The whole game with the pin of 78 commits, after T2.10 (2026-11-16, on the desktop,
      stub mode, the game's own `main()`: 615 s, 12.8 GB): no warning 2025, and
      `build_c64.py --check-only` passes, `check_listing.py` included: highest temporary $8B
      (`m_move`; $8D before T2.10), then `readobjnam` $87, `mfndpos` $82, `dog_move` $80; no
      branch to no instruction; every bank check clean. The per-file listings' $9D is the
      per-file build inlining more, not the game.

## Phase 2 — spikes (after Phase 1 is mostly green)

- [x] T2.1 Banking spike A (EF execute-in-place, trampolines) with hack.c + apply.c + zap.c
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
      function checking its bank on entry. Oscar64 past 64 banks: Codex's patch, in the
      pin as commit 62 (2026-11-15). Next: the
      Oscar64 build of the rewritten source, literals kept by callees (`killer`).
      — 2026-11-16: ADR-0008 proposed: the 63 banks entered most in place on the EasyFlash, the
      rest (40, about 600 KB; first counted as 62 and 42) from a REU of 1 MB or more through a 16 KB window at $8000 with
      the cartridge off; about one window load a turn in a wide profile (`profile_play.py
      --wide`, 13 roles; `tools/measure/bankplace.py`).
      — 2026-11-17: ADR-0008 accepted (Jolyon), with an REU of 1 MB as the minimum. Next: the
      REU window in the bank call routine, and the bank plan re-made from the wide profile.
      — 2026-11-17: the bank call routine fetches REU banks (64 up) into the window, checked in
      VICE (`tests/spikes/bankreu.c`, 14 checks; 361 cycles a call with the bank in the window,
      17.1 ms with a fetch); `bankgen.py` writes it; `tools/bank/crt_split.py` makes the REU
      image; the plan renumbered by the wide profile (`bankplan-2026-11-17-reu.json`); the REU
      size probe no longer overwrites the REU (self-test 7). The whole game from the renumbered
      plan passes every check (desktop, 621 s), 828 B less resident code than before
      (`nh_unstash`). Next: the .crt + REU image once the data fits (T2.12).
      — 2026-11-26: done. The banked game runs on the C128 (fc50): 137 banks, 63 in place on
      the cartridge, 74 from the REU (`docs/data/bankplan-2026-11-26-c128fc50.json`).
- [x] T2.2 Banking spike B (REU overlays) with the same files (BANKING-SPIKE.md)
      — Superseded by ADR-0008 (2026-11-17), which uses both: banks in place on the cartridge
      and REU banks copied into the same window.
- [x] T2.3 RAM map for dynamic state; BUFSZ policy ADR
      — 2026-11-15: measured (docs/RAM-PLAN.md): what NetHack reaches through plain
      pointers is about 155-170 KB (mutable alone 62-77 KB, corrected the same day: Oscar64
      overlays the static frames, 3.2 KB not 11.5; `mons[]`, `objects[]` and
      `level` 49 KB), against 34-55 KB of RAM a C64 can show the CPU. Banking the code does
      not help: the data needs wider pointers (the DOS builds use far data, `-mh`/`/AL`) or a
      restructuring. Direction is Jolyon's to choose.
      — 2026-11-15: Jolyon: explore far data in the compiler (option 1). Measured since
      (RAM-PLAN.md): a far access through an REU page cache costs 21 cycles on a hit, 600 on a
      fault (`tests/spikes/fardata.c`, VICE); a turn touches 28-31 KB of far data, 38-41 KB
      over ten turns (`tools/measure/trace/`); far data would cost 0.25-0.5 s a turn on
      average, against about 1.8 s for the game itself on a C64 (`tools/measure/speed/`:
      about 10 cycles for each x86 instruction of NetHack's code). Two speed wins found:
      `levl[x][y]` multiplies by 126 through `mul16by8` (a third of monster movement's
      cycles), `dist2()` squares through `mul16`. Next: the far-data design (an ADR).
      — Done as ADR-0009 (typed far spaces, accepted 2026-11-16) and ADR-0010 (far characters,
      built 2026-11-21, accepted 2026-11-27). No BUFSZ ADR was needed: BUFSZ stays 256 and no
      game buffer was shrunk. fc50's near heap: 1,240 of 2,828 bytes free on Dlvl 2.
- [ ] T2.4 REU RAM-disk file layer with an AUTOTEST
      — 2026-11-24: built in `port/sys/c64/c64sys.c`; on the C128 it holds the save file
      (17,173 B) and the level files (Dlvl 1 to 2 and back). Left: the AUTOTEST.
- [ ] T2.5 Compress `data`/`quest.dat`/`rumors` three ways; table of ratios + decode speed
- [ ] T2.6 Host build variant with `COMPRESS` off, so `host_smoke` exercises the
      RLECOMP/ZEROCOMP save code the C64 uses (ADR-0006); before Phase 5 saves
- [x] T2.8 Oscar64 compiles the whole game in one run (the banked build has to):
      — 2026-11-15: it did not finish in an hour (`tools/bank/build_c64.py`). Two global
      analyses walk every path through the call graph's cycles (r62, compat #64): NetHack's
      direct calls form one cycle of 279 functions, and with calls through pointers one of
      2,465. (a) `MarkRecursions`: Tarjan's search, exact: the same recursive functions in
      308/308 programs, corpus 983/983 identical, NetHack listings 214/214 identical; commit
      ab12523 on `fix/scc-recursion`, for the pin together with (b) and one test, since the
      two blow up on the same graphs. (b) `CheckFastcall`: done, exact. Each function is
      walked once in the old order; what the old walk read from a stack-parameter function
      after walking it again is found by a search, and kept once its strongly connected
      component is complete (`fix/fastcall-dfs`, d0e133e; test `callcycletest.c`, 2fd059f).
      A temporary check running both walks agreed on every function in 1,088 compiles and in
      1,600 random call graphs; corpus 988/988 byte-identical; autotest 1,531/1,531; 20 rungs
      take 0.77 s (30.1 s with the old walk, 46.6 s on the pin). (A first rewrite,
      `scratch/fastcall-scc-v1`, changed 29 corpus programs and was dropped.) With (a) and (b)
      the whole game gets through the analysis and into code generation; both are in the pin
      as commits 63-65 (2026-11-15). (c) It then stopped on r63 (T1.47) at 136 s and 4.5 GB;
      with that fixed it ran out of a 6 GB cap here, and of 16 GB on Jolyon's 31 GB desktop
      (his suggestion), in intermediate code. Most of it
      was the per-block data flow sets over all statics, kept after each procedure is
      optimized: freeing them (`scratch/whole-game-v2`, f982b52, an experiment; corpus
      1,017/1,017 identical) let **the whole game compile in one run** on the desktop: 619 s,
      peak 13.2 GB, through native code generation, stopping in the linker on "Cannot place
      stack section" (the data does not fit yet, T2.3). The set release is in the pin as
      commits 68-69 (2026-11-15, Jolyon's go-ahead; a test that checks the code depending on
      what is kept, since the saving cannot show at a C64 program's size). (e) The check of
      that build: its 57 "crossings" were trampolines calling their own function at $8000,
      which the listing names after bank 1's object there. `build_c64.py` now resolves a call
      into the window in the caller's bank through the map, and checks the intermediate code
      too, which names every callee: 0 of 41,068 listing calls and 0 of 25,985 direct calls
      cross a bank without a trampoline, no banked function writes the bank register, and no
      banked function's address is taken (722 calls through pointers from banked code can
      only reach resident code). (f) The banks are full by design (the plan packs code to a
      median 14 KB of each 16 KB, `bankplan-8k` meaning an 8 KB resident budget), but the link
      left 342 KB of banked code and 33 KB of banked literals unplaced: the banked content is
      about 1.69 MB against 1.15 MB of planned code. The plan counts no literals (167 KB);
      the functions come out 1.24x their per-file size, mostly argument copying, because the
      harness's table of every function makes every trampoline address-taken and so a stack
      call; trampolines take 73 B each (130 KB); `mhitm.c`'s functions, which did not compile
      when the plan was made, stay resident. (g) With the game's own `main()`: 1.55 MB of code
      (1.37 MB banked, 114 KB of trampolines, 66 KB other resident) plus 166 KB of banked
      literals, so about 100 banks, and 150 KB of resident data (BANKING-SPIKE.md). (h) A plan
      from the whole game's own sizes fits: 103 banks, every banked object placed, checks
      pass, host build plays to level 6 (`docs/data/bankplan-2026-11-15.json`;
      `tools/measure/wholesizes.py`, `tools/bank/planfix.py`, bankgen's `noinline`). Left: the
      resident part, 137 KB of code (trampolines 1,555 x 71 B) and 116 KB of data, for a
      64 KB machine: a smaller trampoline (a shared bank-call routine) and T2.3; then where
      103 banks live (more than EasyFlash's 64: the REU), for an ADR. (d) The harness's `nh_refs[]`
      takes every function's address, which makes Oscar64 give them all stack parameters:
      measure code size with calls instead, since 1.19 MB is probably high.
      — 2026-11-26: done. The C128 game links in one run (fc50: exit 0, peak 13.7 GB, desktop).
- [x] T2.9 Smaller bank calls: the C trampolines took 124 KB of resident code in the whole
      game, 85% of it for functions that take stack arguments, which a trampoline copies.
      — 2026-11-15: the Oscar64 fork's linker makes 6-byte stubs instead
      (in the pin as commits 72-73 since 2026-11-15, Jolyon: "add both to the pin"): a call into
      a bank from outside it, or a banked function's address, goes through
      `jsr nh_bankcall; .byte bank; .word function`. VICE: 13/13 checks
      (`tests/spikes/run_bankstub.py`), 142 cycles a switch. `bankgen.py --linker-stubs`
      keeps trampolines for the 295 string-handling functions only. Whole game: checks pass,
      resident code 65 KB (156 KB with trampolines); host build plays. The stack (r64 + stubs,
      4 commits): autotest 1,591/1,591, corpus identical except the new test and #67.
      Next: the string trampolines (26 KB), stubs in the callers' banks, and T2.3.
      — 2026-11-26: done for now. The C128 game links and runs with the stubs; the string
      trampolines are left for the C64's squeeze.
- [ ] T2.7 RNG + clock ADR before Phase 3 first light: which generator implements
      `lrand48`/`srand48` (exact, for seed-for-seed replays vs the host, or faster), seed
      width, clock source for seeding, moon phase, Friday 13th and `night()`/`midnight()`
      — 2026-11-15: the generator: bit-exact `lrand48` in assembler (Jolyon, with the
      `#ifdef C64` changes, T2.10); in C it would cost about 0.2 s a turn (RAM-PLAN.md).
      Done the same day: `src/hal/rng.c`, 1,178 cycles a call; `tools/check_rng.py` (7 seeds
      x 20,000 numbers agree with glibc 2.39) and a `make test` check. Open: seed width and
      the clock source for seeding, moon phase, Friday 13th, `night()`/`midnight()`.
- [x] T2.10 Speed amendments behind `#ifdef C64` (Jolyon, 2026-11-15: "i love the changes
      behind #ifdef C64 - yes lets make those"): `levl` through a table of column pointers,
      `dist2()` through a table of squares, `isok()` inline; identical results (host build,
      smoke test, the calibration harness's checksums), cycles re-measured.
      — 2026-11-15: done (RAM-PLAN.md): `is_pool`/`is_lava` 2.8x, `mfndpos` 1.4x, `dist2`
      2.1x, `isok` 2.9x faster; all 108 files compile for the C64. Then the object and
      monster grids through column tables too (their macros and `sobj_at()`): `mfndpos` 1.54x.
- [x] T2.11 Far-data experiments: 3-byte far pointers against typed far spaces with 16-bit
      pointers (RAM-PLAN.md, the brainstorm), `mons[]` first; then the far-data ADR.
      — 2026-11-16: `farify.py` + `calibrate.py --far` (RAM-PLAN.md): `mons[]` far costs
      `mfndpos` 4%, `mons[]` and the heap 13%, on a warm cache, without reusing translations;
      typed 16-bit spaces keep the layouts and saves. Next: translation reuse, faults, the ADR.
      — 2026-11-16: ADR-0009 proposed (typed far spaces, identity window for near objects,
      translation at far -> `void *`/`char *`, allocators per space, reuse and pinning).
      — 2026-11-16: compat #72 was zero page, not the optimiser (T1.50): the counting build's
      `main()` had temporaries on the emulator's jiffy clock. Published numbers re-checked
      with the clock off: the same. Then the harness kept within $8F (`setup()`/`touch()` out
      of line, a second call of `mfndpos()`) and re-published
      (`docs/data/speed-far-c72-2026-11-16.txt`): `mfndpos` 12,025, +4% and +13% far, as
      before; with all four types far `mfndpos` itself needs $90. Next: translation reuse,
      faults.
      — 2026-11-16: reuse (`farify.py --expand/--reuse/--reuse-all`, `calibrate.py
      --far-reuse`): all four far 13.4% -> 8.7% (one translation at each single-definition
      variable; `mfndpos`'s own far cost -60%, its zero page back to $88), `mons[]` far 3.7% ->
      3.4%; a list walk (`t_at`) needs a compiler's lazy reuse: about 6% estimated. Faults
      (`nh_trace.c` `NH_TRACE_FAR`, run C): for `mons[]`, `objects[]` and the heap, 36 pages a
      turn (63 at most), CLOCK 64 no faults, 121 ms of translations a turn before reuse. A
      layout rule for ADR-0009: far objects keep to a page (slabs; tables padded, `permonst`
      to 64 bytes). ADR-0009 amended (points 4-6). Next: Jolyon's decision on ADR-0009.
      — 2026-11-16: ADR-0009 accepted (Jolyon: "I've reviewed ADR-0009 and happy to proceed";
      "go ahead with the padding"). Padding done in the C64 build: `struct permonst` 64 bytes,
      `struct objclass` 32 (`static_assert`; Oscar64 accepts a negative array size, compat #75,
      r72): every named field the same, 320 fewer multiply calls, 88 bytes less code, the tables
      6,051 bytes bigger (RAM-PLAN.md). The implementation is T2.12.
- [ ] T2.12 Far data in the compiler, as ADR-0009 decides: a far qualifier on struct types and
      constant tables, translation through the space's page table at each access, reuse and
      pinning, conversions to `void *`/`char *`, allocators per space, the REU page cache and
      its fault handler; `mons[]`, `objects[]` and the heap first. Checked by `farify.py`'s
      checksums, then the game.
      — 2026-11-17: first version on the fork's `feature/far-spaces` (2 commits on the pin,
      `tools/oscar64-upstream/patches/far-spaces/`; RAM-PLAN.md "Built: far spaces"): the
      pragmas, the front end's tags, the late translation pass, `farxlN`/`farxoN`, warning
      2026, built-ins. Autotest 1,626/1,626 with `farspacetest.c`; corpus identical; VICE
      spike with REU faults 9/9 (`run_farspace.py`); the speed harness with the compiler
      translating (`calibrate.py --far-cc`): same checksums, `mfndpos` +3% with `mons[]` far,
      +32% with all four types (every access through a `jsr`). Next: inline hit path, reuse
      with pinning, then the game (`mons[]` first, allocators, the REU image).
      — 2026-11-17: all of port/src with the `mons[]` types far (`NH_FAR_SPACES`, measurement
      only): no warning 2026 in the game's files; +52 KB of code (+4.4%). Reuse first.
      — 2026-11-17: groups within a block, pinned (fork commit 3): VICE 10/10 with a check
      that fails without the pins; harness +2.6% / +30%. Next: groups across blocks.
      — 2026-11-17: groups across blocks (fork commit 4): harness +2.3% / +17%; port/src with
      the `mons[]` types far +49 KB (+4.2%). Next: per-function pin slots (reuse across calls),
      a shorter call sequence; then the game.
      — 2026-11-17: `mons[]`, `objects[]` and `level` in far sections (measurement only,
      `NH_FAR_SPACES`); the 15 game sites warning 2026 found rewritten, `struct rm_s` 8 bytes in
      that build; one harmless warning left; code +6.4%. Next: the whole-game link with them.
      — 2026-11-18: the whole-game link (desktop, `docs/data/wholegame-far-2026-11-18.txt`):
      the three sections place, resident data unplaced 128.6 KB to 73.2 KB, bank checks pass;
      banked code +5.0%, 33 banks overflow (36 KB), `seffects` 16,473 B outgrows a bank.
      `planfix.py`: `--add-banks`, best fit. Next: denser far accesses in the compiler (shorter
      call sequence, per-function pin slots), then repair the plan and link again.
      — 2026-11-18: denser accesses (fork commit 5, dac0840: page form for slotless groups,
      `farxzN` 5-byte calls, `NCIF_ZP_16`): `port/src` +6.4% to +5.4% over near, whole game
      +5.0% to +4.3%, `seffects` 16,374 B. Plan repaired (`bankplan-2026-11-18-far.json`,
      banks 104-105 new, `planfix.py` slack per bank): every banked object places. Next:
      the resident side (47.7 KB code, 73.2 KB data unplaced), reuse across calls.
      — 2026-11-19: the whole game's warnings, first seen (the desktop's log wrapper had
      dropped them): two real cross-bank reads, compat #78 (code inlined into another bank),
      fixed with #77 and warning 2024's detail as pin commits 81-83 (ADR-0007). Plan repaired
      again (`bankplan-2026-11-19-far.json`, 36 moves out of bank 5): every banked object
      places, checks clean (`docs/data/wholegame-far-2026-11-19.txt`). Next: as above.
      — 2026-11-19 (2): the resident side, bank call glue first. Fork commit 6 (c0c33b1): a call
      from a bank goes through a stub in that bank; bankgen.py splits the string trampolines
      (f__tA copies arguments in the calling bank onto a stack it releases, f__xN copies a
      result in the callee's); `vpline`/`vraw_printf` resident (they format `%s` arguments).
      Resident code 65.1 KB -> 29.6 KB; banked code +164 KB, which the repaired plan does not
      yet fit (planfix.py counts no stubs or wrappers). Compat #79 (r76). Codex's review found
      four real defects, all fixed (`tests/spikes/run_bankstr.py`).
      `docs/data/wholegame-far-2026-11-19b.txt`. 2026-11-20: REU minimum 2 MB (ADR-0008);
      smaller wrappers, planfix.py --glue, fork commit 7 (resident glue for seffects' bank):
      every banked object places again (far19, 116 banks), resident code 31.4 KB
      (`bankplan-2026-11-20-far.json`). Next: the resident data (72 KB).
      — 2026-11-20 (2): the resident data (RAM-PLAN.md "the data",
      `docs/data/wholegame-far-2026-11-20.txt`): read-only tables in their readers' bank
      (bankgen.py `bank_data`, `tools/bank/tables.py`); the names of `mons[]` and `obj_descr[]`
      far, read through `NH_MNAME()`/`NH_ONAME()` (`tools/farnames.py`, ADR-0009 amended; the
      host's ring test under AddressSanitizer); fork commit 8 (proxies in the calling banks);
      far space 4 (`rooms`, `gbuf`, `mvitals`) and `obj_descr` with `objects[]`. Resident data
      99.6 -> about 63 KB, code 31.4 -> 25.9 KB. The page cache traced at 8-64 pages: 4 KB costs
      about 125 ms a turn. Next: the cache size into the budget, the vision grids far, the
      hot set and libc out of resident code, then strings.
      — 2026-11-26: the far-spaces series, 22 commits on pin 99
      (`tools/oscar64-upstream/patches/far-spaces/`), builds the C128 game that plays. Left:
      whether and when the series joins the pin.
- [ ] T2.13 The C128 platform (ADR-0003, amendment of 2026-11-21: the whole game runs first on
      a C128 + Magic Desk 128 + REU in x128, the C64 build kept working): a `-tm=c128` build of
      the banked game with its banks on a Magic Desk 128 image (16 KB at `$8000`, `$DE00`) and
      the REU; the VDC for the 80 columns; the keyboard; 2 MHz; `make test` cases for it.
      Evidence so far: `tests/spikes/c128.c`, `c128ef.c` (HARDWARE.md). 2026-11-21: bank calls
      on a C128, `bankreu128.c` 14/14 (`tools/bank/c128_images.py`); `bankgen.py`/`build_c64.py
      --target c128`; the far36 plan links for the C128, every bank placed, 18.6 KB of resident
      data over 36.6 KB of regions (`docs/data/wholegame-c128-2026-11-21.txt`). Far characters
      laid out for the C128 (ADR-0010): the character space in RAM bank 1 at `$C100-$FBFF`,
      under bank 0's code; `tests/spikes/farchar128.c` 7/7; the speed of `doname()` and of a
      message (`tools/measure/speed/fcbytes.py`, `docs/data/farchar-checks-2026-11-21.txt`):
      about 3 ms and 2 ms more at 1 MHz. Built the same night: far characters in the far fork
      (commit 11, `autotest/farcharstest.c` 15/15), the far runtime `tools/bank/farrt.py`
      (REU paging for every space; `tests/spikes/farrt128.c` 7/7 in x128,
      `docs/data/farrt-c128-2026-11-21.txt`), `build_c64.py --far-chars`; and an upstream
      miscompile of list walks (COMPAT row 81, r78), fixed in the fork's commit 12. Next: the
      C128 whole-game link with far characters on the desktop; the pin fix (Jolyon); the farxz
      form's lost carry; the I/O out by default (+4 KB), `$0400-$1BFF` (+6 KB).
      2026-11-22: the C128 hardware layer for Phase 0's demo, `make prg128`: `src/hal/vdc80.c`
      (screen80.h on the VDC, the project's font doubled, `tools/mkfont4x8.py --vdc`),
      `src/hal/sys128.c` (no KERNAL: keys from its buffer, which VICE feeds, and from the
      matrix), `reuprobe.c` shared; `make test` 6/6 with the new `c128-reu512` case (x128).
      Then: the fork's commit 13 (farxzN's lost carry, fixed); `build_c64.py --far-runtime`
      (`farrt.py --from-headers`) and `--io-out` (`bankgen.py --io-out`, bankreu128 -dIO_OUT
      14/14; frames in `$0B00-$1AFF`); `build/bank-c128-fc` generated for the desktop.
      2026-11-22 (later): the C128 link with far characters, 617 objects unplaced
      (`docs/data/wholegame-c128-fc-2026-11-22.txt`); then the resident side fitted step by
      step (`bankgen.py`: the code regions above the window first, the glue's buffers at
      `$0400-$0AFF` and `$1B00-$1BFF`, a plan's `char_space`; planfix for C128 sizes;
      resident functions called from one bank moved into it), in
      `docs/data/wholegame-c128-fit-2026-11-22.txt`. 2026-11-22 (night): more near data far
      (option tables, grownups, doors, artilist, shtypes), the plan repaired (planfix, REU banks
      added, warmplan: 11 REU copies a key), readobjnam() split: fc13 links, every object
      placed (heap 1,144 B, 4 KB stack). First boot in x128 stops at once (BRK near `$0007`).
      Next: that crash, then the boot.
      — 2026-11-23: the first level plays (9c127a4). 2026-11-24: saves, restores, level
      changes (78f6511). 2026-11-25: the VDC's text no longer black on black (r92, fc49).
      2026-11-26: the keypad, ESC, HELP and a joystick in port 2 (fc50). 2026-11-27: 2 MHz,
      each REU DMA at 1 MHz (fc51; self-test check 10; `docs/data/speed-c128-2026-11-27.txt`):
      the first level 1.3 times as fast, the same replay to Dlvl 2. Then fc52: the port's own
      code on cartridge banks (a ring of the C128's bank loads, `bankgen.py --load-log` and
      `tools/measure/trace/loadlog.py`, showed the RAM disk's two REU banks made 77% of them;
      `docs/data/loads-c128fc51d-2026-11-27.txt`): start-up 2.6 s, the first level 29.0 s.
      fc53: the save path and small hot callees as well: 1.9 s, 24.5 s, the Dlvl 2 replay
      408 s (653 on fc50). The plan's "cartridge" list (bankgen.py refuses a plan that puts
      it in the REU; planfix.py and warmplan.py leave it on the cartridge) keeps the host
      profile's blind spot from undoing this. The near heap peaks at 2,344 or more of 2,808
      bytes (`docs/data/heap-c128-2026-11-27.txt`). Left: the loads in play, the near heap's
      margin, a `make test` case for the whole game, the stick on real hardware.
- [x] T2.14 The heap far (ADR-0009 point 7: "`mons[]`, `objects[]` and the heap first"). The
      C128's fc3 link leaves the resident side 2 KB over with no heap, and the near heap peaks
      at 11-24 KB in C64 bytes in host games (`docs/data/heap-peak-2026-11-22.txt`: up to 201
      monsters, 175 objects; a shopkeeper's block is 2,378 B). Monsters and their extensions
      in far space 7, objects in far space 8 (`c64conf.h`, `NH_FAR_HEAP`); allocators per
      space; names in the blocks (`NAME()`, `ONAME()`) read through a copy, as `NH_MNAME()`
      does; `struct bill_x` and `struct fakecorridor` padded so that no entry crosses a page;
      what stays near (windows, message history, quest index, about 3 KB). 2026-11-22: the
      spaces declared for measurement (`far_meas.c` spaces 7-8; `measure_oscar64.py` now
      gives `mkstubs.py` the `MEASURE_DEFS`): 202 warnings 2026, 72 of them harmless
      (`docs/data/farheap-warnings-2026-11-22.txt`). 2026-11-22 (later): built, under
      `NH_FAR_HEAP` (host code unchanged at every site): `sys/c64/c64heap.c` (slabs of
      8-byte classes, larger blocks on whole pages), names through a ring of copies and
      setters, block copies and file transfers a byte at a time (`nh_farmove()`,
      `nh_farbwrite7/8`), the corpse's monster through a near copy, list walks without
      pointers into far blocks, `askchain()`'s proxy, the shopkeeper's strings and the
      extensions' d_levels; `bill_x` and `fakecorridor` padded (static_assert);
      `build_c64.py --far-heap`. Linked in fc13 (T2.13); the quest index far too. Its
      translations grew banked code by about 60 KB (more banks).
      — 2026-11-26: done. Monsters and objects in far spaces 7 and 8, the menu items and the
      message history too (2026-11-24); fc50's near heap has 1,240 of 2,828 bytes free.
- [ ] T2.15 The near heap's peaks, and the special levels (found 2026-11-27). The C128's
      near heap is 2.8 KB, and a failed malloc() is a panic. Measured with
      `tools/measure/trace/loadlog.py record` (it walks Oscar64's free list) and a block
      dump: at rest about 1.5 KB in use, 950 B of it the special levels' and branches' lists
      (`docs/data/heap-c128-2026-11-27.txt`). Found: the long help text ("?", "a") panicked
      (a tty text window keeps its page's lines on the heap); the Oracle's level panicked
      ("cannot get 14 bytes", loading its description). Fixed in fc57: text and menu
      window lines on the far heap (wintty.c, as the menu items and message history were);
      the special levels' and branches' lists on the far heap (`dungeon.h` NH_DGNALLOC,
      far space 8, near copies wherever a d_level or a name was handed on). fc57: at least
      2,036 of 2,768 bytes free over a new game; the whole help file pages through; the
      Oracle (9) and Dlvl 18 load, with 2,100 bytes free at rest. Also: raw prints (the
      panic's lines) each on a row of their own (`video.c` xputline).
      2026-11-28: Medusa's level (24), the first maze-type special level reached, failed
      three ways (a panic, "reading special level with ysize too large"; a `BRK`; MMU in the
      ROMs). Two bugs, found with a canary on `nhio`'s code polled through the monitor, the
      load ring and the listing: (1) compat #100, Oscar64 specialised `nh_farfill4()` for its
      one call (`Map`, 1,680 bytes of far space 4) into a block fill translated once, which
      cleared the RAM after Map's first cache frame (the far runtime, the bank call routine);
      `decl.c`'s far fills now go a page at a time (fc58). (2) `c64scanf.c` called Oscar64's
      own `fgetc()`, which reads through the KERNAL and so maps the C128's ROMs over the game:
      the first `fscanf()` of a file (`tt_oname()`, naming Medusa's statues from the record
      file) crashed; it uses the file layer's `nh_fgetc()` now (fc59), and the heap gained
      176 bytes with Oscar64's I/O gone. fc59: Medusa's level loads (2,308 bytes free). Next:
      the castle (26) panics "create_object: unexpected object class 'a'", with its
      description read right (robjects "%)*[", 59 objects of classes -1 to -4, '(' and '/');
      then Gehennom, the Mines and Sokoban.

## Phase 3 — first light

- [x] T3.1 The window port: NetHack's tty port without termcap (ADR-0006's amendment of
      2026-11-22). 2026-11-22: `port/sys/c64/video.c` over `screen80.h` (`s80_putca()` in
      both screens); `tools/host-build.sh --video` and `tests/host_video_compare.py`, 301
      screens the same as termcap's; `c64conf.h` turns the port on (`NO_TERMS`, `S80_VIDEO`);
      it compiles under Oscar64 (wintty.c 20.5 KB, topl.c 4.8, getline.c 1.6, video.c 0.6;
      r80-r82 worked around); `port/sys/c64/c64tty.c` (gettty, settty, setftty, `tgetch()`
      over `sys_waitkey()`); in the C128 bank plan. Next: run it on the C128.
      — 2026-11-23: runs on the C128 (the first level drawn and played, 9c127a4); menus,
      `--More--`, `^P` and the `O` menu since.
- [ ] T3.2 The system layer's rest: `error()`, `regularize()`, the file layer (T2.4),
      `fflush()`/`perror()`, time and the RNG (T2.7).
      — 2026-11-24: save and restore through the RAM disk (`c64main.c` restores as
      `pcmain.c` does). Open: the clock (`docs/TO-DECIDE.md`).

## Housekeeping

- [x] H1 CI green on GitHub Actions (`.github/workflows/ci.yml`) — first run on master
      green (run 42530155008, 2026-11-08), checked 2026-11-09 Claude
- [ ] H2 Decide repo visibility/licensing note (NetHack GPL-like licence applies to port/)
