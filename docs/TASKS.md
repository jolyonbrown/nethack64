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
- [ ] T1.8 Work around r15 (`union T *` does not convert to `const union T *`), which
      stops every `add_menu(..., &any, ...)`: NetHack is const-correct here, so this is a
      compiler workaround, not const-correctness fixes. One cast in `winprocs.h`'s
      `add_menu` macro would cover all 87 calls (the 2026-11-09 review saw `apply.c`,
      `pager.c` and `spell.c` reach placement with it in a scratch copy). check_ansi +
      host_smoke; re-measure.
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
- [ ] T1.10 Measurement harness fixes, then re-measure both configs and re-baseline both:
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
- [ ] T1.11 `files.c` (C64 config) segfaults Oscar64 at `-Os` once `close()` is stubbed
      (`-O0` places it): bisect by deleting functions; repro; upstream issue. Same for
      `questpgr.c` (C64 config), which crashes Oscar64 once the r14 stubs get a body
      (scratch harness, 2026-11-10). — 2026-11-12 Claude: the shknam-crash agent saw
      `files.c` crash the patched pin in `NativeCodeBasicBlock::SplitAt` (native code
      generator), not in any of the r27-r35 paths; no log was kept, not re-checked.
- [ ] T1.12 Work around r12 (`decl.c` `occtxt = DUMMY` → `= 0`) and r13 (`mail.c`
      `junk[]` → `const char *`) in `port/`; check_ansi + host_smoke; re-measure.
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
- [ ] T1.14 Work around r16 (`windows.c:113` function pointer `==` function name) and r17
      (`do.c:688` `?:` over two functions), with repro-backed changes in `port/`. The
      obvious r17 workaround, a pointer variable, runs into r18 for `boolean` functions,
      so do it after T1.13. (r17 is fixed on upstream main, c8da6bd; r16 has a fix
      branch, PR #6 in OSCAR64-UPSTREAM.md. Both stay port-side work while we build
      with v1.32.273.)
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
- [ ] T1.17 r31 (OSCAR64-COMPAT.md #33): at `-Os` Oscar64 aborts (assertion, SIGABRT) in
      `BlockSizeCopyReduction`, which builds `LDY #-1` for the same value stored to three
      or more bytes from offset 0 through a pointer. Hit by `invent.c` `display_pickinv()`
      once `invent.c` gets past its first error (T1.4). Not fixed anywhere: write the fix
      (probably `(mIns[si + 0].mAddress - 1) & 0xff` where the `LDY` is built) for upstream
      main and the pin, with an autotest, or work around it in `invent.c`.
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
- [ ] T1.21 Heap-dependent output and two wrong-code bugs (OSCAR64-COMPAT.md #40, #41;
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
- [ ] T1.23 r37 and its sibling (OSCAR64-COMPAT.md #39, #46; r37, r44). r37: the native
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
      probe turns wrong at `-O0` (a separate bug it hid): reduce it before the fix is
      offered.
- [ ] T1.24 Wrong code at the default optimisation level only, native code (mutual
      recursion; a local's address passed on is taken at the wrong stack offset): on
      v1.32.273, the pin and main; right at `-O0`, `-O2`, `-Os`, `-O3`, so nethack64's
      `-Os` build is not affected as tested. Unreduced:
      `tools/oscar64-upstream/cases/default_level_mutual_recursion_local_address.c`.
      Reduce, find the cause, report upstream when PRs resume.
- [ ] T1.25 Decide what joins the pin (Jolyon, on the decision page; each then goes
      through ADR-0007's checks and a new patch export). Ready: `nethack64/pin-shknam-crash`
      (r27), `pin-makemon-hang` (r28), `pin-walks-display` (r29), `pin-r30` (r30),
      `pin-1ae3216` (r32), `pin-charidx` (r33): built on c2f5cab, validated alone and
      together (`review/pin-candidates-all`: autotest 1,311, none failing; repros 14 of
      35); each rebases onto f001eba without conflicts (`git rebase --onto f001eba
      c2f5cab`). `pin-shknam-crash` without `pin-1ae3216` turns one loop shape from a
      crash into wrong code (OSCAR64-COMPAT.md #11b). Before adding: drop the
      `Co-Authored-By` trailer from c5ac062 (upstream's commit) and reword b52c9fe's
      message. New on 2026-11-13: the heap-initialisation commits (T1.21) and our r36
      and r37 fixes (T1.22, T1.23).

## Phase 2 — spikes (after Phase 1 is mostly green)

- [ ] T2.1 Banking spike A (EF execute-in-place, trampolines) with hack.c + apply.c + zap.c
- [ ] T2.2 Banking spike B (REU overlays) with the same files
- [ ] T2.3 RAM map for dynamic state; BUFSZ policy ADR
- [ ] T2.4 REU RAM-disk file layer with an AUTOTEST
- [ ] T2.5 Compress `data`/`quest.dat`/`rumors` three ways; table of ratios + decode speed
- [ ] T2.6 Host build variant with `COMPRESS` off, so `host_smoke` exercises the
      RLECOMP/ZEROCOMP save code the C64 uses (ADR-0006); before Phase 5 saves
- [ ] T2.7 RNG + clock ADR before Phase 3 first light: which generator implements
      `lrand48`/`srand48` (exact, for seed-for-seed replays vs the host, or faster), seed
      width, clock source for seeding, moon phase, Friday 13th and `night()`/`midnight()`

## Housekeeping

- [x] H1 CI green on GitHub Actions (`.github/workflows/ci.yml`) — first run on master
      green (run 42530155008, 2026-11-08), checked 2026-11-09 Claude
- [ ] H2 Decide repo visibility/licensing note (NetHack GPL-like licence applies to port/)
