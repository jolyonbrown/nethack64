---
description: Take one NetHack source file in port/src through Oscar64 - measure, fix compile errors properly (repro + workaround for compiler bugs, real fixes for portability issues), keep the host build green, record the result.
argument-hint: "<file.c>"
---

# Port one file: $ARGUMENTS

1. Status: `python3 tools/measure/measure_oscar64.py $ARGUMENTS` → status, code bytes, first error.
2. For each error, decide:
   - **Oscar64 gap** (valid C89 rejected, crash, hang): invoke `/oscar64-repro`. Prefer a
     scripted workaround in `tools/oscar_normalize.py` if the pattern repeats across files.
   - **Portability issue** (Unix call, missing libc, real type error): fix in `port/`,
     smallest change, keep it valid for gcc. Platform calls go behind the C64 config
     (`port/include/c64conf.h`), not `#ifdef`s scattered in game code.
3. Re-run step 1 until the file reaches `ok` or `fits-not` (placement only).
4. Regression: `tools/check_ansi.sh && tools/host-build.sh && python3 tests/host_smoke.py`.
5. Record: code size in a dated line in `docs/NETHACK-SURVEY.md` if notable; tick the task
   in `docs/TASKS.md`; new compiler issues in `docs/OSCAR64-COMPAT.md`.

Never change game behaviour to get past a compiler error. If that seems
necessary, stop and write an ADR proposal instead.
