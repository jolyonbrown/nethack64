# ADR-0007: Build with Oscar64 v1.32.273 plus wrong-code fixes

- Status: proposed (on hold: commit 3, upstream bf42402, makes `explode.c` exhaust memory; see below)
- Date: 2026-11-12
- Deciders: Jolyon (+ Claude, who proposes it)

## Context

The pinned compiler, Oscar64 v1.32.273 (ADR-0002), silently miscompiles code shapes
that NetHack uses, at `-Os`, with no diagnostic. Each has a repro in
`tests/oscar64-repros/` and a row in `docs/OSCAR64-COMPAT.md`:

| Repro (row) | What goes wrong | Where NetHack has the shape |
|---|---|---|
| r18 (#22) | the `char`/`boolean` result of a call through a function pointer is read from the wrong place | every `yn()`; every `boolean` window or callback function |
| r19 (#23) | a pointer initialised to 0 compares as non-null; `!p` as a value is wrong | `pickup.c` `invent != 0` |
| r20-r22 (#24-#26) | negative numbers in initialised data read back as large positive ones when folded | abs-style `?:` on members, `schar` tables such as `xdir`/`ydir` |
| r23 (#27) | a call through a function-pointer member of a global struct is left out of the call graph: the callee's frame overwrites the caller's live locals | every window call, `(*windowprocs.win_*)(...)` |
| r25 (#29) | a function called directly with a constant and also through a pointer gets the constant built in | window-port functions called inside the port with `FALSE` and through `windowprocs` with `TRUE` |
| (no repro; case file) | two different functions with identical code share one address when their addresses are stored | tables of function pointers that are compared (`cmdlist`, `occupation == dig`) |
| r24 (#28) | a pointer test in a side-effect-free helper evaluated at compile time | helpers called with constant addresses; **not fixed by this proposal** |

A reviewer's NetHack-shaped window layer (`build/oscar64-wt/pinned-patched-2-review/p/nh/n01_window_port.c`:
a `windowprocs` table, `char` and `boolean` results, callers with live locals, a port
function also called directly) returns a wrong result with v1.32.273 in nine of the
ten configurations, `-Os` included in both back ends. Game code cannot run reliably
on this compiler.

Fixes exist for all but r24 (`docs/OSCAR64-UPSTREAM.md`): r18 and r25 are fixed on
upstream main (1169268, 2026-09-21; bf42402, PR #440, 2026-10-24); the others are our
fix branches, reviewed twice each and not yet sent upstream. None is in a release:
v1.32.273 (2026-08-20) is still the latest.

Options:

1. **Plain v1.32.273 and port-side workarounds.** Each workaround has to catch every
   instance, and a missed one fails silently. r23 alone means changing how every
   window call is made. Fragile.
2. **Upstream main plus our fixes** (`nethack64/integration-final`, measured
   2026-11-12): 17 more files compile (C64 config), but for the 40 files that compile
   with both, `-Os` code is 13.4% bigger (227,598 to 258,193 bytes), five files crash
   the compiler and three hit the 600 s limit (`explode.c`, which compiles with
   v1.32.273, and `dungeon.c` also crash upstream main without our fixes). The UNIX
   config is the same: 11 more files placed, +13.6% for the 35 placed by both. Our
   fixes are not merged. Not usable yet.
3. **Wait for the next release.** No date, and it would still need our fixes merged and
   the size growth explained.
4. **v1.32.273 plus backported fixes.** Same release, same flags, only the wrong-code
   fixes.

## Decision (proposed)

Option 4. Build nethack64 with v1.32.273 plus the seven commits in
`tools/oscar64-upstream/patches/pin/` (branch `nethack64/v1.32.273-pin` in the local
Oscar64 clone):

1. upstream 1169268 (r18), the maintainer's commit unchanged;
2. its regression test (upstream has none);
3. upstream bf42402 (PR #440, r25), unchanged;
4. r19, 5. r20 (all three sites), 6. merged identical functions, 7. the r23 call edge:
   backports of our fix branches.

`tools/oscar64-upstream/build-pin.sh [DIR]` builds it. If accepted, the setup scripts
apply the patches after checking out `OSCAR64_TAG`, and the docs say "v1.32.273 +
nethack64 patches". Re-pin to a plain release once one contains these fixes (or
equivalents) and passes the same checks, and its `-Os` size is understood.

## Consequences

- The six fixed rows above stop being "must be settled before game code runs";
  r18-r23 and r25 pass. r24 stays open (T1.15).
- We carry a patch stack until upstream releases: two of the seven commits are
  upstream already, four are proposed upstream PRs (#1 to #4 in OSCAR64-UPSTREAM.md)
  and the seventh is a test, so it should shrink. Anyone building must run
  the setup script (or `build-pin.sh`); a stock v1.32.273 builds a subtly broken game.
- Measurements and byte counts taken with v1.32.273 stay valid where the code does not
  hit the bugs. To re-check once the commit list is settled: the NetHack measurement
  with the seven-commit pin was stopped on 2026-11-12 when `explode.c` ran out of
  memory (see the open problem below); an earlier patched compiler with three of the
  fixes changed no file's status and added 84 bytes (C64 config) and 1.2 KB (UNIX
  config, one more function placed in `uhitm.c`).
- The call-edge fix makes callers of `windowprocs` functions non-leaf functions, so
  they get proper frames: slightly larger code there, which is the point.
- Risk: a mistake in a backport could add wrong code of its own. Mitigation: each
  backport was reviewed against its upstream-main version by a second agent
  (`build/oscar64-wt/pinned-patched-2-review`), the full v1.32.273 autotest passes, and
  every pre-existing autotest program compiles byte-for-byte as before (below).

## Open problem (2026-11-12)

Upstream bf42402 (commit 3, PR #440) fixes r25 but makes the compiler's memory grow
without bound on `explode.c`: with the seven commits the compile reaches 8-9 GB in
16-20 s and the kernel kills it, where v1.32.273 needs 0.36 GB. v1.32.273 plus bf42402
alone does the same; the pin without it compiles `explode.c` as v1.32.273 does.
Upstream main has the same problem. Until it is fixed, the choice is between:

- **six commits** (without bf42402): `explode.c` compiles, but r25 (a function called
  directly with a constant and through `windowprocs`) stays wrong code, and the
  call-edge commit then also miscompiles a function declared through a typedef'd
  function type that is called through a struct member (reviewer probe `t01`; NetHack
  declares no function that way);
- **seven commits plus a fix for the runaway**, being investigated
  (`build/oscar64-wt/explode-runaway`, branch `fix/pr440-runaway`).

## Evidence / how to re-check

```sh
tools/oscar64-upstream/build-pin.sh /tmp/pin           # v1.32.273 + patches/pin
make repros OSCAR64=/tmp/pin/bin/oscar64               # r18-r23 and r25 FIXED
make -k -j4 -C /tmp/pin/make check                     # Oscar64's own autotest
python3 tools/oscar64-upstream/corpus_diff.py ~/src/oscar64/bin/oscar64 /tmp/pin/bin/oscar64 --out /tmp/pin-corpus
make OSCAR64=/tmp/pin/bin/oscar64 && make prg OSCAR64=/tmp/pin/bin/oscar64 && make test OSCAR64=/tmp/pin/bin/oscar64
OSCAR64=/tmp/pin/bin/oscar64 MEASURE_TIMEOUT=600 python3 tools/measure/measure_oscar64.py --config c64
```

Results 2026-11-12 (branch tip f0b9ee6; `build-pin.sh` builds the same compiler from
the patch files: identical `.prg` output for r18-r25):

- Tests: the six regression tests and the reviewer's probes (including the
  NetHack-shaped `n01_window_port.c`) pass in all ten configurations (`-ea -g`,
  `-bc`/`-n` x default/`-O0`/`-O2`/`-Os`/`-O3`); with v1.32.273 each fails in some.
- `make repros`: 7 of 25 pass (r18-r23, r25), against 0 with v1.32.273.
- Oscar64 autotest: 1,231 emulations, 0 failing (v1.32.273: 1,171, 0 failing; the 60
  more are the six new tests in ten configurations).
- `corpus_diff.py` against v1.32.273: 152 files x 5 configurations, 680 compiled by
  both, 621 byte-identical, 59 different, all 59 in the six new tests and repros
  r18-r23 and r25; no compile status changed. Every pre-existing autotest program
  compiles byte-for-byte as before.
- nethack64 today: `make` and `make prg` give a `nethack-ef.crt` and `nethack.prg`
  byte-identical to the v1.32.273 build (same memory map: code 6,925, data 894,
  bss 2,399 bytes); `make test` 5/5 passed.
- Independent review of the backport: `build/oscar64-wt/pinned-patched-2-review`
  (verdict "use after changes"; the change it asked for, upstream bf42402, is commit 3).
