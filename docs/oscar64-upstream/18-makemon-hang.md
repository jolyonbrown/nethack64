# 18. Fix endless loop on a struct copied onto itself

| | |
|---|---|
| Branch | `fix/makemon-hang` in `~/src/oscar64-dev`, commit `487a1420d1c4`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/18-makemon-hang.patch`](../../tools/oscar64-upstream/patches/main/18-makemon-hang.patch) |
| Kind | compiler hang (endless optimiser loop) |
| Since | v1.32.273 and main |
| NetHack | Repro r28. `makemon.c` hangs only in our measurement harness: a separate bug (r34, two reads of a volatile pointer merged) makes `clone_mon()`'s new and old monster the same memory, so `*m2 = *mon` becomes a copy onto itself. With the fix the harness compiles `makemon.c` in about 10 s. r34 and r35 (stale forward after a volatile struct copy) are separate and not fixed; a one-line harness change avoids the hang without any compiler fix. |
| Reviews | Opus (one round, ran probes): use-after-changes, 1 high, 3 medium, 3 low; fix-up: ready; final Codex check (2026-11-13): submit after changes, 1 open item below |
| Recommendation | **Submit; low priority for the game (only the harness's fake allocator reaches it).** |

## In plain words

When a C function copies a struct onto itself through a pointer and then reads it, Oscar64 never finishes compiling: two clean-up steps keep rewriting the later read into exactly what it already was, count that as progress, and repeat for ever. The fix teaches those two steps to ignore a copy of memory onto itself, and deletes such a copy because it does nothing. In NetHack this shows up only in our measurement harness, on makemon.c: a separate compiler bug merges two reads of the fake allocator's volatile pointer, so in clone_mon() the new monster and the old one look like the same memory. This round applied the review's findings: the deletion now also requires that both sides use the very same pointer value, the PR text says exactly what was run on the build without one of the guards, tells the clone_mon story including the volatile merge, and is written impersonally with the agreed trailer and closing paragraph. Because the code changed, both branches were rebuilt and re-validated: Oscar64's full test suite passes on both (1551 and 1251 runs, no failures), every other test program compiles to the same bytes as before apart from one file already known to vary between builds, and makemon.c gets through the harness with the patched-pin branch in about 10 seconds instead of never. The two unrelated compiler bugs the review found are written up as repros r34 and r35 and are not fixed, and there is a one-line harness change that avoids the hang without any compiler fix.

## The fix

oscar64/InterCode.cpp, 18 lines (whole commit: 3 files, +160/-3; the added and removed lines are identical on main and pin).
1. New static IsSelfCopy(ins): IC_COPY with SameMem(mSrc[0], mSrc[1]) and equal strides.
2. PropagateVariableCopy (IC_COPY case): a self copy is not pushed onto ltemps.
3. InterCodeBasicBlock::LoadStoreForwarding: a self copy is not recorded (nins = nullptr).
4. InterInstruction::RemoveUnusedResultInstructions: a non volatile self copy through a temporary is deleted as one of a variable already was. Changed this round: the new arm is `mSrc[0].mTemp == mSrc[1].mTemp && IsSelfCopy(this)`, because SameMem compares temps only for IM_INDIRECT.
Decision on the review's guard finding: the LoadStoreForwarding guard is kept and the PR states exactly what was run without it. Reason: with the narrower deletion the guards are what guarantees termination for any self copy the deletion leaves alone. Measured on scratch builds of the final commit: without the LSF guard, 33 files x 10 configurations all pass (full autotest and corpus not run on it, and the PR says so); with the deletion only (both guards removed), p_t9.c and structselfcopytest.c time out at 10 s in all ten configurations.
Commit message rewritten: impersonal, "when p is not a known address", "SameMem on the two operands and equal strides", equal-temps reason, exactly one trailer "Co-Authored-By: Claude <noreply@anthropic.com>".

## Regression test

autotest/structselfcopytest.c (142 lines, registered in autotest/autotest.bat; identical file on both branches): load after a self copy, two self copies, self copy then copy to another struct, "t = *p; *p = t;" then another copy, two names for one pointer, struct members copied onto themselves, self copy in a loop, memcpy(p, p, n).
Unfixed: all 30 runs (ten configurations on 4da3147, v1.32.273 and pin c2f5cab) stopped by the 10 s timeout, 18-20 MB.
Fixed: 10/10 "Emulation result 0" on main 487a142 (0.03-0.12 s, 28 MB max) and on pin 08964ef (0.03-0.13 s; 0.33 s max in an earlier run on a loaded machine).
The test cannot fail quickly on an unfixed compiler, it hangs; the commit message and PR say so.

## Evidence

**Repro matrix.** All under ulimit -v 2000000 plus timeout. Ten configurations = -ea -g, -n/-bc x default/-O2/-O0/-Os/-O3.

| case | v1.32.273 | pin c2f5cab | main 4da3147 | fixed pin 08964ef | fixed main 487a142 |
|---|---|---|---|---|---|
| PR example (min.c), 10 configs | 10/10 timeout 10 s; -e alone stopped at 60 s, 13 MB | not run | 10/10 timeout; -e alone stopped at 60 s, 13 MB | 10/10 result 0 | 10/10 result 0 |
| structselfcopytest.c, 10 configs | 10/10 timeout | 10/10 timeout | 10/10 timeout | 10/10 result 0 | 10/10 result 0 |
| t9 (t = *p; *p = t; *q = *p), 10 configs | not run | not run | 10/10 timeout | 10/10 result 0 | 10/10 result 0 |
| r28 via run.py logic | BROKEN, compiler hang (120 s) | BROKEN, compiler hang | BROKEN, compiler hang | FIXED, result 0 | FIXED, result 0 |
| r28, 10 configs | 10/10 timeout | 10/10 timeout | not run | 10/10 result 0 | 10/10 result 0 |
| r28 with clone_mon only, -n/-bc x 6 levels | hangs at -O2/-Os/-O3, passes default/-O0/-O1 | same | same | not run | 12/12 result 0 |
| 32 reduced cases x 10 configs | - | - | - | 320/320 rc 0 | 320/320 rc 0 |
| makemon.c in harness (-Os), monstr table added | timeout 60 s, 185 MB | timeout 60 s, 185 MB | timeout 60 s, 188 MB | rc 20 in 9.5 s (placement errors only) | error 3011 in role.c, see other_notes |

a2.c (f called with addresses of two globals) on main: hangs in 8 configurations, compiles at -O3, which is why the texts say "when p is not a known address".

**Autotest.** Run sequentially as (ulimit -v 2000000; make -k -j2 -C <wt>/make check), make rc 0 both times.
Main 487a142: 1551 emulations, all "Emulation result 0"; autotest_diff.py against autotest-base-4da3147.log: base 1541, new 1551, new failures 0, fixed 0, failing in both 0; the ten new ones are structselfcopytest.c. Log: /home/jolyon/nethack64/build/oscar64-wt/f18-scratch/autotest-main-487a142.log
Pin 08964ef: 1251 emulations, all result 0; against pin8-autotest.log: base 1241, new 1251, new failures 0, fixed 0, failing in both 0. Log: /home/jolyon/nethack64/build/oscar64-wt/f18-scratch/autotest-pin-08964ef.log

**Corpus.** corpus_diff.py, -j 1, under the 2 GB cap, structselfcopytest.c left out because the base compilers hang on it; five configurations (-n -O2, -n -Os, -n -O0, -n -O3, -bc -O2).
Main (~/src/oscar64-base/bin/oscar64 against fixed main): 184 files (158 autotest + 26 tests/oscar64-repros), 845 compile with both, 844 byte identical, 1 different (autotest/testint16mul.c bc-O2, the known build-dependent one), status changed 0. Log: /home/jolyon/nethack64/build/oscar64-wt/f18-scratch/corpus-main.log
Pin (pin c2f5cab against fixed pin): 154 files, 690 compile with both, 690 identical, 0 different, status changed 0. Log: /home/jolyon/nethack64/build/oscar64-wt/f18-scratch/corpus-pin.log

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| review | high | Separate from this fix: the pin miscompiles an array index built from a small-range global char | Not part of this PR. Tracked as r33 by another task; nothing changed here. |
| review | medium | PR text overstated the check of the build without the LoadStoreForwarding guard | Guard kept; the PR now states only what was run and says the full autotest was not run on that build. |
| review | medium | The r27 repro hung only because of the volatile-merge bug | The reviewer's improved repro is used, renumbered r28; the header names r34 and PR #18. |
| review | medium | Separate: PropagateVariableCopy keeps invalidated entries after a volatile struct copy | Not folded in. Written up as r35 (verified BROKEN on all five compilers); offered for a separate upstream PR. |
| review | low | Deleting a self copy relied on SameMem, which ignores temps outside IM_INDIRECT | Applied: the deletion also requires mSrc[0].mTemp == mSrc[1].mTemp. Both branches rebuilt and fully re-validated. |
| review | low | Wording: clone_mon story without the volatile merge, 'any optimization level', 'the same test the redirections use', harness workaround wording | Applied in commit message, PR body and repro headers: the PR tells the clone_mon story with the merge, says 'when p is not a known address' (commit) and 'SameMem with equal strides'. |
| review | low | Attribution, closing sentence and first-person claims did not match decision 3 | Applied: both commits end with the single Co-Authored-By: Claude trailer and no session line; the PR body is impersonal and ends with the agreed paragraph. |
| f18 | low | The first r35 draft passed at -O2 and above, so it would have reported FIXED under its own FLAGS | f is now __noinline; the header records that without it the wrong value appears only below -O2. |
| f18 | low | The harness's pointer stubs understate code size | Reported for the lead; the one-line mkstubs.py change removes the effect. |

<details><summary>Evidence for each finding</summary>

1. **Separate from this fix: the pin miscompiles an array index built from a small-range global char** (Not part of this PR. Tracked as r33 by another task; nothing changed here.)

   Review case c1.c; not re-run in this round.

2. **PR text overstated the check of the build without the LoadStoreForwarding guard** (Guard kept; the PR now states only what was run and says the full autotest was not run on that build.)

   Scratch build of the final commit minus the LSF guard: 33 files x 10 configurations all rc 0 (/home/jolyon/nethack64/build/oscar64-wt/f18-scratch/noguard-set.log). Deletion-only build: p_t9.c and structselfcopytest.c time out in all ten configurations (delonly.log).

3. **The r27 repro hung only because of the volatile-merge bug** (The reviewer's improved repro is used, renumbered r28; the header names r34 and PR #18.)

   run.py logic: BROKEN 'compiler hang' after 120 s on v1.32.273, pin c2f5cab and main 4da3147; FIXED 'runs, result 0' on 08964ef and 487a142. Ten configurations: 10/10 timeout on v1.32.273 and pin, 10/10 pass on both fixed builds.

4. **Separate: PropagateVariableCopy keeps invalidated entries after a volatile struct copy** (Not folded in. Written up as r35 (verified BROKEN on all five compilers); offered for a separate upstream PR.)

   r35: result 1 in 12 of 12 configurations on v1.32.273, pin, main, fixed pin and fixed main; run.py logic BROKEN on all five.

5. **Deleting a self copy relied on SameMem, which ignores temps outside IM_INDIRECT** (Applied: the deletion also requires mSrc[0].mTemp == mSrc[1].mTemp. Both branches rebuilt and fully re-validated.)

   Commits 487a142 and 08964ef; autotest 1551 and 1251 with 0 failures; corpus 844/845 and 690/690 identical.

6. **Wording: clone_mon story without the volatile merge, 'any optimization level', 'the same test the redirections use', harness workaround wording** (Applied in commit message, PR body and repro headers: the PR tells the clone_mon story with the merge, says 'when p is not a known address' (commit) and 'SameMem with equal strides'.)

   clone_mon half of r28 alone: hangs at -O2/-Os/-O3 and compiles at default/-O0/-O1 on v1.32.273, pin and main; r34 shows the merge on all three.

7. **Attribution, closing sentence and first-person claims did not match decision 3** (Applied: both commits end with the single Co-Authored-By: Claude trailer and no session line; the PR body is impersonal and ends with the agreed paragraph.)

   git show 487a142 and 08964ef; /home/jolyon/nethack64/build/oscar64-wt/f18-scratch/pr-body.md

8. **The first r35 draft passed at -O2 and above, so it would have reported FIXED under its own FLAGS** (f is now __noinline; the header records that without it the wrong value appears only below -O2.)

   Without __noinline: result 1 at default/-O0/-O1, result 0 at -O2/-Os/-O3 on all five compilers. With it: result 1 in all twelve.

9. **The harness's pointer stubs understate code size** (Reported for the lead; the one-line mkstubs.py change removes the effect.)

   makemon.c on the fixed pin: 14275 bytes with the present stubs, 14458 with the changed line; clone_mon 698 against 768 bytes, one read of nh_vp against three separate reads.

</details>

## Final Codex check (gpt-6-astra, 2026-11-13)

Read-only `codex exec` on a packet of the final PR text, the commit and the earlier findings (as for PRs 1-14). Each finding was then checked by the lead.

| Severity | Finding | Checked | Resolution |
|---|---|---|---|
| medium | The test's `memcpy(p, p, 16)` is undefined behaviour in ISO C (overlapping objects) | True for ISO C. Measured: a file holding only that call hangs v1.32.273 at the default level, `-O2` and `-Os`, native and bytecode (60 s timeouts, all six), and the fix build 487a142 compiles it and returns 0 in all six: Oscar64 compiles a constant-size `memcpy` into the same copy, so the case covers a second way into the bug | Open: keep the case; before submitting, add a test comment and a PR sentence saying that ISO C leaves it undefined and why it is there, so the maintainer can drop it |

## Before submitting

- Upstream may prefer r34 (volatile pointer reads merged) and r35 (stale forward after a volatile struct copy) as issues of their own; the PR mentions the volatile merge in one parenthesis only.
- The build without the equal-temps guard was not put through the full autotest; the PR says so. If the maintainer asks for the guard to go, that run is still to do.
- Done 2026-11-12 (Jolyon's decision): the commit ends with one `Co-Authored-By: Claude <noreply@anthropic.com>` line and no session link (message only; the tree is the one validated), and the PR text ends with the same AI-assistance sentence as every other PR.

## Risks and limitations

- The only intended change in generated code is that a self copy through a pointer is no longer emitted; the corpus shows no other change (844/845 and 690/690 identical).
- The deletion relies on equal temps plus SameMem. A volatile copy is never deleted (!mVolatile).
- The new autotest hangs rather than fails on a compiler without the fix; anyone bisecting across this commit needs a timeout.
- The build without the LoadStoreForwarding guard was checked on 33 small files only, so the guard's necessity is argued, not measured; keeping it is the conservative choice.
- The pin commit sits on c2f5cab; the lead still has to combine it with whatever becomes of commit 8 (nethack64/pin-runaway). The diff touches only InterCode.cpp regions that the other candidate fixes were not seen to touch, but the combination was not built here.

## Related bugs found, not fixed here

Not fixed here, by instruction.
- r34: two reads of a volatile pointer through a pointer cast are merged (v1.32.273, pin, main). Repro written and verified, see other_notes.
- r35: PropagateVariableCopy keeps stale entries after a volatile struct copy, wrong code (v1.32.273, pin, main, with and without this fix). Repro written and verified, see other_notes.
- r33 (another agent's): the pin miscompiles an array index built from a small-range global char; found by this PR's review, not part of it.
- Reported by the investigator and reviewer, not re-measured this round: bytecode wrong code when one temp is both operands of a copy (cases bc/b1.c, b3.c, b5.c, p/t8.c), and -rmp segfaults after ordinary compile errors (Compiler::WriteErrorFile -> InterCodeProcedure::Disassemble). The second was seen again here: makemon.c without the monstr table gives five "error 3010" and then exit 139.
- docs/OSCAR64-COMPAT.md row 11 (makemon.c does not terminate) can be closed once this fix or the harness line is in.

## Draft pull request

**Title:** Fix endless loop on a struct copied onto itself

````markdown
The compiler never finishes on a function that copies a struct onto itself through a pointer and then reads it.

**Example**

```c
struct S { char a[20]; int b; };
struct S k[2];
volatile char vi;

int f(struct S *p)
{
	*p = *p;
	return p->b;
}

int main(void)
{
	k[0].b = 7; k[1].b = 8;
	return f(&k[vi]) == 7 ? 0 : 1;
}
```

`oscar64 -e min.c`

Observed (4da3147 and v1.32.273): no output; the compiler runs at 100% CPU and constant memory (13 MB) until it is stopped, here after 60 s. The same happens with `-n` and `-bc` at default, `-O0`, `-O2`, `-Os` and `-O3`.

Expected: `Emulation result 0`.

The copy does not have to be written as a self copy. `struct S t = *p; *p = t; *q = *p; return p->b;` hangs the same way, and so does `*m3 = *m2` once `m3` and `m2` turn out to be the same value. The second form is how this was found, in NetHack's `clone_mon()` compiled against stub functions. The stubbed allocator is `return (long *)vp;` with `void * volatile vp`, and at `-O2`, `-Os` and `-O3` the two inlined reads of `vp` become one value, so `*m3 = *m2` is a copy onto itself. (The two reads are merged although `vp` is volatile. That is a separate problem, which this PR does not touch.)

**Cause**

Two passes record each `IC_COPY` and redirect a later read of its destination to its source: `InterCodeBasicBlock::LoadStoreForwarding` redirects a load, `PropagateVariableCopy` a load or the source of another copy. When source and destination are the same memory, the redirected operand is what it was before, but both passes report a change, and their callers (`InterCodeProcedure::LoadStoreForwarding` and the `PropagateVariableCopy` loops in `Close`) repeat until nothing changes.

`RemoveUnusedResultInstructions` already deletes a copy of a variable onto itself, so `g = g` was not affected, but it did not look at copies through a temporary. `PropagateVariableCopy` can also create such a copy inside its own loop (`t = *p; *p = t;`), where no cleanup runs before the next pass.

**Fix**

`IsSelfCopy(ins)`: an `IC_COPY` whose two operands are the same memory (`SameMem`) with equal strides. With it:

- `PropagateVariableCopy` and `LoadStoreForwarding` do not record a self copy. It says only that a block of memory equals itself, so no forwarding is lost.
- `RemoveUnusedResultInstructions` deletes a non volatile self copy through a temporary, as it already does for one of a variable. Here both operands must also use the same temp: `SameMem` compares temps only for `IM_INDIRECT`, and a copy should not be removed on a comparison that did not look at them.

Code that compiled before is only affected if it contains such a copy: the copy is no longer emitted.

The two guards do not depend on the deletion, and the deletion alone is not enough: a build with only the deletion still does not finish on the `t = *p; *p = t;` case or on the new test. The guard in `LoadStoreForwarding` is there so that the pass terminates without relying on the cleanup having run first. A build without that guard also passes the example, the new test and 31 further reduced cases in all ten configurations; the full autotest was not run on that build.

**Test**

`autotest/structselfcopytest.c`, registered in `autotest.bat`: a load after a self copy, two self copies, a self copy followed by a copy to another struct, `t = *p; *p = t;` followed by another copy, two names for one pointer, struct members copied onto themselves, a self copy in a loop, and `memcpy(p, p, n)`.

Without the fix the compiler does not finish compiling it in any of the ten autotest configurations (stopped after 10 s each, at 18 to 20 MB of memory). The loop has no bounded form, so the test cannot be made to fail quickly instead: an unfixed compiler has to be stopped. With the fix each configuration takes 0.03 to 0.12 s.

**Validation** (Linux, on 4da3147)

- The example above and the new test pass in all ten configurations (`-ea -g`, `-n`/`-bc`, default/`-O2`/`-O0`/`-Os`/`-O3`).
- `make -k -j2 -C make check`: 1551 emulations, 0 failing. Before the change: 1541, 0 failing; the ten new ones are the new test.
- 184 programs (the autotest sources except the new test, plus 26 small test files from the NetHack port), each compiled with `-n -O2`, `-n -Os`, `-n -O0`, `-n -O3` and `-bc -O2` before and after: 845 compile with both compilers, 844 give a byte identical .prg, and none changes between compiling and not compiling. The one that differs is `autotest/testint16mul.c` at `-bc -O2`, whose output has also been seen to differ between two builds of the same compiler source.

Found while porting NetHack 3.4.3 to the C64. Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described.
````
