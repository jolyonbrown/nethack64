# T1.1 reviews: verdicts and author responses (2026-11-09/10)

Branch `task/T1.1-c64conf` (C64 platform configuration, ADR-0006). Two
independent reviews, as the review gate asks:

- **Codex** (gpt-6-astra, `codex exec -s read-only` on an embedded diff
  packet, 2026-11-09). Verdict: no high-severity defect; 1 medium, 4 low.
- **Claude** (a workflow with three lenses: host, parity and measurement; each
  medium/high finding re-checked by a second agent told to refute it;
  2026-11-09/10). It ran the code rather than reading summaries: host builds
  of master and branch, full UNIX and C64 measurements, makedefs under both
  configurations, compiler probes. Verdict: no high; 6 medium (all survived
  verification), 14 low. Numbers reproduced: UNIX run = 2026-11-08 baseline
  and C64 run = committed JSON (0 of 107 records differ each); host objects
  identical after strip-debug; 0 of 14 repros pass.

## Responses

| # | Sev | Finding | Response |
|---|---|---|---|
| Codex 1 | med | Dropping `-w` from `check_ansi.sh` breaks "verification tools stay unchanged" | **Rejected.** The change was in the approved plan, is its own commit (`7812bf8`), and the tree still passes 107/107. Without it the three `-Werror=` checks could never fail |
| Codex 2 = Claude M6 | low | File-name check accepts `./rnd.c`, absolute and `../` paths, after which `setup()` wipes the last run | Fixed: only existing `port/src/*.c` base names pass |
| Codex 3 | low | Survey says "byte-identical"; only records are compared | Fixed: "identical records (status, code bytes, functions)" |
| Codex 4 = Claude H5 | low | "the old check could not fail" is too strong | Fixed: the three `-Werror=` checks could not fail; hard errors still did |
| Codex 5 = Claude P3 | low | Mail scrolls also come from wishes and bones | Fixed in ADR-0006 (Mail bullet) |
| H1 | low | `check_ansi.sh` FAIL shows `head -5` of the log, now often only warnings | Fixed: prints the error lines. Tested with a K&R definition in `apply.c`, whose 17 warnings used to hide the errors |
| H2 | low | `measure_oscar64.py` crashes on a fresh clone (no generated headers) | Fixed: stops before `setup()` and names `tools/host-build.sh --generate-only` |
| H3 = M7 | low | `_meta.git` records git's error text outside a checkout | Fixed: a failing command records nothing, so the field is "unknown" |
| H4 | low | Commit `bbe8d4b` says "identical"; DWARF line numbers move | Accepted, not rewritten: history stays as it is. ADR-0006 states it precisely (identical after strip-debug) |
| H6 | low | `check_ansi.sh` header: "every call has a prototype" (older than the branch) | Fixed in the comment: every called function is *declared* |
| P1 = M8 | med | `check_recordfile()` is empty under C64, so no `record` is created and no score is ever kept; ADR omits it | Fixed in `port/`: one more `\|\| defined(C64)` (`files.c:2116`), listed in ADR Decision 2. UNIX view byte-identical; `files.c`'s C64 measurement unchanged; host_smoke 4/4 |
| P2 | low | `#version` text (`dat/options`) differs under C64 | Fixed in ADR Watch and the `c64conf.h` comment |
| P4 | low | Bones files use ZEROCOMP/RLECOMP too | Fixed (ADR Decision 6, Files bullet) |
| P5 | low | ARCHITECTURE.md overstates seed-for-seed replay | Fixed: names the conditions |
| M1 | med | `pager.c` "port (T1.8)" is an Oscar64 gap: `union *` → `const union *` | Fixed: repro r15, COMPAT #19, survey label. T1.8 and the older COMPAT class row rewritten (NetHack is const-correct there) |
| M2 | med | `windows.c` and `do.c` "port" are Oscar64 gaps | Fixed: r16 (function pointer `==` function), r17 (`?:` over functions), COMPAT #20/#21, T1.14 |
| M3 | med | r14 and T1.10: a `va_start` body does not help | Fixed: r14, COMPAT #18, T1.10. A side-effecting stub (`nh_vl = 0;`) works in a scratch harness; `questpgr.c` then crashes Oscar64 (T1.11) |
| M4 | med | Survey credits the configuration with 4 of 5 newly placed files; it is 2 | Fixed: table and summary. Reproduced by dropping `extern` from the shim |
| M5 | med | r13 "a scalar `char *q = "a"` works" is wrong | Fixed: r13, COMPAT #17. `gcc -Wwrite-strings` still finds only `mail.c` |
| M9 | low | ADR probe step does not reproduce (needs a `time_t`) | Fixed: probe committed as `tests/c64conf_probe.c`, command in its header |

## The finding that matters most: r18, wrong code

While checking a workaround for r17, the measurement verifier saw a call
through a function pointer return the wrong value. Reduced and confirmed
(2026-11-10, Oscar64 v1.32.273):
- a function returning `char`, `signed char` or `unsigned char` leaves the
  result in the A register;
- the caller of an indirect call reads it from zero-page `ACCU`, which still
  holds the low byte of the function's address.

There is no diagnostic. The bug shows at `-Os`/`-O2` once the target is
unknown at compile time, and at `-O0` always. NetHack's
`(*windowprocs.win_yn_function)(...) == 'y'` is miscompiled in a probe of
that exact shape, and every `boolean` callback is at risk. Our `src/` has no
function pointers, so today's cartridge build is not affected. Repro r18,
COMPAT #22, T1.13: settle it before any game code runs.

## What each review caught

Both found the mail-scroll and "could not fail" wording. Codex checked the
numbers against the committed artefacts and confirmed them, including the
first-error causes. The Claude review re-ran the experiments and found
several of those causes wrong (M1, M2, M4). It also found the empty
`check_recordfile` and, indirectly, r18. Codex alone flagged the scope
question about `check_ansi.sh`.
