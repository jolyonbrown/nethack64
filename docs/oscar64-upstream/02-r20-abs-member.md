# 02. Fix sign extension when folding loads of signed values from known bytes

| | |
|---|---|
| Branch | `fix/r20-abs-member` in `~/src/oscar64-dev`, commit `e0c8823c9630`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/02-r20-abs-member.patch`](../../tools/oscar64-upstream/patches/main/02-r20-abs-member.patch) |
| Kind | wrong code (silent) |
| Since | v1.32.273 and main; the minimal `?:` form regressed on main at 48f90e2 |
| NetHack | Compat #24, #25, #26 (repros r20, r21, r22): negative numbers in initialised data read back as large positive ones when the optimiser folds the load. Shapes NetHack has: abs-style `?:` on struct members (distance helpers), loops over `schar` tables such as `xdir`/`ydir`. Part of the proposed patched pin. |
| Reviews | Opus (round 2, ran probes): submit-after-changes, 0 high, 3 medium, 3 low; Codex (read the diff): submit after changes; fix-up: ready; final Codex check: submit after changes |
| Recommendation | **Submit.** |

## In plain words

The compiler fix is finished and did not change in this round. The last reviewer pointed out that the write-up talked about numbers like 65533 and -65535 as if the program would see them, when in fact a 16-bit int cannot hold them: they are the wrong values the optimizer keeps internally. I checked what a program actually observes on the unfixed compiler: the stored numbers print correctly (-3, 1), but anything the compiler computes at compile time from the bad internal value goes wrong (s / 3 comes out as 21844 instead of -1, and a comparison with the right answer is decided 'false' before the program runs). The PR text and the commit message now say exactly that, treat the memset case separately (a 0xff fill reads back as 65535 instead of -1), and no longer claim the 32-bit code 'worked through int overflow'. The session-link trailer is left for Jolyon to decide. Nothing else moved: the code and tests are byte-for-byte what the two reviews and the full test runs covered.

## The fix

No code or test change this round: the oscar64/InterCode.cpp and autotest files are byte-identical to 904530b, so the backport of 904530b to v1.32.273 is unaffected (only the commit sha moved to e0c8823 because the message was amended). The fix itself is unchanged: in LoadConstantFold, LoadConstantOperand and the IC_FILL branch of LoadStoreForwarding, sign extend the 8/16/32-bit value assembled from known bytes with ToTypedSigned unless ins->mDst.IsPositive(), and do the 32-bit << 24 as uint32. This round corrected the PR text and one sentence of the commit message so that 65533/-65533/65535 are described as wrong internal folded constants (mIntConst) rather than observable C values, gave the observable failures instead (s / 3 evaluated to 21844 instead of -1; d == 1 folded to false; main collapsing to return 1), stated the memset case separately (fill byte 0xff becomes 65535 instead of -1), and replaced the 'int overflow' sentence about the 32-bit hunk with a statement about the tested builds. The Claude-Session trailer is left as it was, for Jolyon.

## Regression test

autotest/constinitsignedtest.c (unchanged from 904530b), registered in autotest/autotest.bat after globalstoreordertest.c and picked up by the autotest makefile wildcard. Fails (assert, emulation result -1) on 4da3147 in all ten -ea -g {-bc,-n} x {default,-O2,-O0,-Os,-O3} configurations and in -O1, -O2 -Oo, -O2 -Ox, -O2 -xz -Oz, -O2 -strict, -O3 -Op; passes all 22 with the fix, as C and as C++. Blocks: struct member through a pointer and directly (int, signed char, long), full-width signed bitfield, single-member struct copy, loop over a static const int table, load forwarded from memset, signed min/max per width read by widening, unsigned controls at the sign bit and maximum, unsigned char control.

## Evidence

**Repro matrix.** Emulation result per configuration, order bc{def,O2,O0,Os,O3} n{def,O2,O0,Os,O3}; B=4da3147, F=904530b, P=v1.32.273.
abs_member_via_pointer.c: B 0,1,0,1,1 / same; F all 0; P all 0.
abs_member_with_ushort_helper.c, r20_abs_of_member_via_pointer.c, br1.c, br2.c, bf2.c: B 0,1,0,1,1 x2; F all 0; P 0,1,0,1,1 x2.
sc1.c: B returns 3 at O2/Os/O3; F all 0; P as B.
dir2.c: B 1 in all ten; F all 0; P all 0.
loopG.c, loopC.c, loopF.c, r21_const_table_loop_negative.c: B 1,1,0,1,1 x2; c7509de 1,0,0,1,0 x2; F all 0; P 1,1,0,1,1 x2.
fill5.c, r22_memset_then_signed_load.c: B 1 all ten; c7509de same; F all 0; P 1 all ten. fill2.c: B/c7509de 1 all ten, F all 0, P all 0. fill1.c: B/c7509de 0,1,0,1,1 x2, F all 0, P all 0.
constinitsigned_extra.c (reviewer): B -1 all ten; c7509de -1 all ten; F 0 all ten.
constinitsignedtest.c (new): B -1 all ten (+12 extra configs); F 0 all 22; P -1 except -O0.
Unchanged / pre-existing (identical B and F): retA.c B 1 all ten, F 1 only at -O0, P all 0; scu.c 14 at bc def/bc O0 (B and F), P 0; ul2.c and crash/c05.c compiler abort rc134 at bc def, bc O0, n O0 (B and F), P 0; bc14.c 1 at def/O0 both backends (B and F), P 0; cpp4.cpp 1 everywhere on B, F, P; unsigned-only probes bf1, bf3, bf4, scu2, ul1, ch1: 0 everywhere on all three.

**Autotest.** make -k -j4 -C make check with 904530b: /home/jolyon/nethack64/build/oscar64-wt/r20-abs-member-scratch/autotest-fixup2.log; autotest_diff.py vs autotest-base-4da3147.log: emulations base 1541, new 1551 (+10 = the new test), new failures 0, fixed 0, failing in both 0; log ends with make leaving the autotest directory normally.

**Corpus.** corpus_diff.py ~/src/oscar64-base/bin/oscar64 vs 904530b, --out r20-abs-member-scratch/corpus-fixup2: 181 files x 5 configurations (-n -O2/-Os/-O0/-O3, -bc -O2); both compile 845, identical 826, different 19, status changed 0 (both-fail = 905-845 = 60 configurations, same set for both compilers). The 19: autotest/constinitsignedtest.c in all 5 (new test; 874->859, 618->603, 1884->1880, 184->137, 2440->2396 bytes: the folded comparisons are now computed correctly instead of collapsing to an assert); tests/oscar64-repros/r20_abs_of_member_via_pointer.c n-O2/Os/O3 and bc-O2 (139->137, 726->726; wrong -> right); r21_const_table_loop_negative.c n-O2/Os/O3, bc-O2 (139->137, 726 same; wrong -> right, LoadConstantOperand site); r22_memset_then_signed_load.c in all 5 (139->137, 159->157 at -O0, 784 same; wrong -> right, IC_FILL site); autotest/testint16mul.c bc-O2 (5659->5678): include-path quirk, shown directly: the fixed compiler with the base build's include directory produces a .prg byte-identical to the base's, while the same binary with its own include path does not (identical include file contents, different path string). The corpus has 2 more files than the author's run because nethack64 gained r21 and r22 since. Separately, 16 unrelated programs (8 samples/autotests x 8 configurations) and the unsigned-only probes are byte-identical in native code; the only other code change seen is bytecode for scu.c/scu2.c at default and -O0 (an unsigned short read through a single-member struct copy, a load without range): the constant is emitted as #-3 instead of #$fffd (main 4 bytes shorter, interpreter links one more handler, inp_const_n8, net +11 bytes for scu, +2/-5 for scu2), same bits and same emulation results.

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| opus | medium | Same unsigned byte assembly in LoadConstantOperand (compile-time loop evaluation), so programs still miscompile at default and -Os | fixed |
| opus | medium | Same defect in the IC_FILL (memset) load forwarding in LoadStoreForwarding | fixed |
| opus | medium | Regression test only failed before the fix on the int case; 8/32-bit hunks and the unranged-load path untested | fixed |
| opus | low | By-value struct return still fails at -O0 with the fix (separate mechanism) | out-of-scope |
| opus | low | PR claim that 1.32.273 'needs a second helper' is wrong; the trigger is a comparison that feeds an if | fixed |
| opus | low | Unrelated pre-existing bugs found while probing (c05 crash, bc14, cpp4 const-ref abs, limits.h CHAR_MIN) | out-of-scope |
| opus | low | PR text issues 1-10 (passing-control claim, 'every LOAD has a range' overclaim, 'unsigned loads keep their value', root cause names one site, nethack64 jargon, mixed spelling, session URL, extra configurations) | fixed |
| codex | medium | The signedness decision needs an explicit invariant; the fallback (sign-extend when no range) is not inherently conservative | fixed |
| codex | medium | The unsigned 32-bit change lacks a regression that distinguishes old and new behavior | fixed |
| codex | low | The combined regression does not establish independent coverage of each folding case; add boundaries, globals, C++ | fixed |
| codex | low | PR text overstates: 'unsigned loads keep their value', 'undefined-behaviour shift', unsupported testint16mul attribution, bisect-based inference | fixed |

<details><summary>Evidence for each finding</summary>

1. **Same unsigned byte assembly in LoadConstantOperand (compile-time loop evaluation), so programs still miscompile at default and -Os** (fixed)

   Reproduced: p/loopG.c, loopC.c, loopF.c and nethack64 tests/oscar64-repros/r21_const_table_loop_negative.c give Emulation result 1 at default/-O2/-Os/-O3 on 4da3147 and v1.32.273, and 1 at default/-Os with the earlier fix c7509de (both backends). Adopted the reviewer's hunk after checking it: at both call sites (InterCode.cpp ConstInnerLoopOptimization and ConstSingleLoopOptimization) `ins` is the IC_LOAD and `type` is ins->mDst.mType, so `ins->mDst.IsPositive()` is the same signal LoadConstantFold uses. With 904530b all four files return 0 in all ten configurations; the test now has a const-table loop block. Code: r21 139 -> 137 bytes at -n -O2/-Os/-O3.

2. **Same defect in the IC_FILL (memset) load forwarding in LoadStoreForwarding** (fixed)

   Reproduced: p/fill5.c and tests/oscar64-repros/r22_memset_then_signed_load.c return 1 in all ten configurations on 4da3147, c7509de and v1.32.273; fill2 fails all ten on main/c7509de (passes on v1.32.273); fill1 fails -O2/-Os/-O3 on main/c7509de. Adopted the hunk (sign extension restricted to IT_INT8/16/32 and !IsPositive, so bool/pointer/float loads are untouched). With 904530b fill1, fill2, fill5 and r22 return 0 in all ten; a memset block is in the test. r22: 139 -> 137 bytes at -n -O2/-Os/-O3, 159 -> 157 at -O0.

3. **Regression test only failed before the fix on the int case; 8/32-bit hunks and the unranged-load path untested** (fixed)

   Reproduced the probes: dir2 (direct access) fails all ten on main, bf2 (signed 16-bit bitfield) and sc1 (single-member struct copy) fail -O2/-Os/-O3 on main and v1.32.273; all pass with the fix. The test now adds direct access, signed bitfield, struct copy (signed and unsigned), const-table loop, memset, min/max per width read by widening (no abs of INT_MIN), unsigned values at the sign bit and the maximum, a const global unsigned table, and uses unsigned char for the char control. It fails (Emulation result -1) on 4da3147 in all ten -ea -g {-bc,-n} x {default,-O2,-O0,-Os,-O3} configurations and in the 12 extra ones (-O1, -O2 -Oo, -O2 -Ox, -O2 -xz -Oz, -O2 -strict, -O3 -Op, both backends), and passes all 22 with 904530b, compiled as C and as C++. A controls-only variant (the blocks expected to pass before the fix) passes all ten on 4da3147, v1.32.273 and the fix, so the failure is from the intended blocks. The PR states that the 8/32-bit hunks are for consistency, not a failing case.

4. **By-value struct return still fails at -O0 with the fix (separate mechanism)** (out-of-scope)

   Reproduced p/retA.c: 4da3147 returns 1 in all ten; 904530b returns 1 only at -O0 (both backends), 0 elsewhere; v1.32.273 returns 0 in all ten. The reviewer's trace shows the wrong constant comes from forwarding the B_AND R0(L),65535 return-marshalling temp into a 16-bit signed load, not from any of the three patched sites. Listed in adjacent_bugs; the PR is worded as 'folds of loads from known bytes', not as a complete abs fix.

5. **PR claim that 1.32.273 'needs a second helper' is wrong; the trigger is a comparison that feeds an if** (fixed)

   Reproduced p/br1.c (minimal case with `if (ax(&pt) != 3) return 1;`, no helper): v1.32.273 fails at -O2/-Os/-O3 in both backends; br2 likewise. 48f90e2's diff changes SimplifyIntegerRangeRelops from the block's final branch condition to every relational operator (`for (int i = 0; i < sz; i++)`), which is what exposes the ?: form on main. PR text rewritten. The same wrong sentence in nethack64 tests/oscar64-repros/r20_abs_of_member_via_pointer.c is outside my worktree and was NOT changed; the lead should fix that header.

6. **Unrelated pre-existing bugs found while probing (c05 crash, bc14, cpp4 const-ref abs, limits.h CHAR_MIN)** (out-of-scope)

   Reproduced, identical on 4da3147 and 904530b: p/crash/c05.c and p/ul2.c abort the compiler (rc 134) at bc default, bc -O0 and n -O0 (v1.32.273 fine); p/bc14.c and p/scu.c return 1 / 14 at bc default and bc -O0 (v1.32.273 fine); p/cpp4.cpp returns 1 on all three compilers at every level; ch1.c confirms plain char is unsigned while limits.h says CHAR_MIN -128. Listed in adjacent_bugs.

7. **PR text issues 1-10 (passing-control claim, 'every LOAD has a range' overclaim, 'unsigned loads keep their value', root cause names one site, nethack64 jargon, mixed spelling, session URL, extra configurations)** (fixed)

   All applied in the new PR body: headline example is the direct-access case that fails at every level; unranged loads (bitfields, single-member struct copies, return marshalling, inline asm) are named and the sign-extend default stated; the bytecode encoding change for an unranged unsigned load is disclosed (scu2.c MOV P0,#$fffd -> #-3, scu.c links the inp_const_n8 handler, +11 bytes; same bits, same emulation result; native code byte-identical); all three sites named; 'pinned' and nethack64 paths replaced by 'release 1.32.273' and 'small reproducers from our project'; American spelling in commit, test and PR; no session link; 22 configurations and C++ listed.

8. **The signedness decision needs an explicit invariant; the fallback (sign-extend when no range) is not inherently conservative** (fixed)

   The premise is right: loads without a range exist (full-width bitfields, single-member struct copies, short-struct return marshalling, inline-asm operand loads, bool). For those the patch now sign-extends by default, which is a representation choice, not range analysis, so the PR no longer calls it 'conservative' and says exactly what happens. Verified it is bit-preserving in practice: unsigned-only unranged probes bf1, bf3, bf4, scu, scu2, ul1 give identical emulation results before and after in all ten configurations, native code is byte-identical, and the only bytecode difference is the immediate encoding (#$fffd -> #-3). Consumers of an IT_INT16 constant that care about unsignedness already normalize (IA_EXT*U folding casts to uint8/uint16, IA_DIVU/SHR/CMP*U use ToTypedUnsigned, unsigned range simplifications require IsPositive). No code change made for this; declining the fold for unranged loads would regress the signed bitfield and struct-copy cases that the patch fixes.

9. **The unsigned 32-bit change lacks a regression that distinguishes old and new behavior** (fixed)

   Confirmed: no source-level case distinguishes it. ul1.c (0xfffffffdul, 0x80000000ul, >> 31, / 2, casts) is byte-identical before and after in all configurations, and the suggested `p->x > 0x7fffffffUL && (p->x >> 31) == 1UL && p->x / 65536UL == 65535UL` passes on 4da3147 too. Added it and sign-bit/maximum controls to the test as controls, and the PR says plainly that the 32-bit hunk only makes the unsigned bit assembly explicit (the old `int << 24` already produced the right bits through overflow) and fixes no failing case.

10. **The combined regression does not establish independent coverage of each folding case; add boundaries, globals, C++** (fixed)

   Per-block coverage established with separate probe files (dir2, bf2, sc1, loopG, fill5, br1 each fail on 4da3147 alone). Test extended with signed minimum/maximum at 8/16/32 bits read by widening, unsigned at the sign bit and maximum, a static const global table; the test compiled as C++ fails all ten on 4da3147 and passes all ten with the fix.

11. **PR text overstates: 'unsigned loads keep their value', 'undefined-behaviour shift', unsupported testint16mul attribution, bisect-based inference** (fixed)

   Wording corrected. testint16mul -bc -O2 quirk now has evidence: the fixed compiler given the base build's include directory (identical file contents, different path) produces a .prg byte-identical to the base build's (md5 b9c6a49f...), while the same fixed binary with its own include path gives a different one (6f5e7d9b...); the output depends on the include path string, not on the code change. The sentence inferring anything about 48f90e2's correctness from the v1.32.273 experiment was dropped.

</details>

## Last round: final-check findings and what happened to them

Changed in the last round: text-only. Commit before it: `904530b90791`.

| From | Severity | Finding | Resolution |
|---|---|---|---|
| codex final check | low | PR text presents optimizer constants (s is 65533, d is -65535, 'in all three -3 becomes CI:65533') as observable C values; the fill case cannot produce FD FF | fixed |
| codex final check | low | PR text: 'the 32 bit case already produced the right bits through int overflow' overstates the mechanism | fixed |
| codex final check | low | Commit message still carries the Claude-Session trailer | left-for-jolyon |

<details><summary>Evidence, and what was re-run</summary>

1. **PR text presents optimizer constants (s is 65533, d is -65535, 'in all three -3 becomes CI:65533') as observable C values; the fill case cannot produce FD FF** (fixed)

   Confirmed and the old comments were wrong in substance. Probes /home/jolyon/nethack64/build/oscar64-wt/r20-abs-member-scratch/final3/{loopobs,fillobs,ptrobs}.c printed the values on 4da3147 in all ten -ea -g {-bc,-n} x {default,-O2,-O0,-Os,-O3} configurations: loop case s=-3 (bytes FD FF stored correctly) but s / 3 = 21844 at default/-O2/-Os/-O3 (-1 at -O0); memset case a[1]=-1, d=1, yet both d == 1 and d == -1 are folded false at every level (exit 3); pointer case d=3 printed, d == 3 folded false at -O2/-Os/-O3. Fixed compiler: s/3=-1, all comparisons right, exit 0 in all ten. PR body rewritten: the code comments now give the folded consumer as the observable result (s / 3 evaluated to 21844; the comparison with 1 folded false), the root-cause paragraph says the stored bytes are right and names the wrong internal mIntConst values, and the fill case is stated separately (fill byte 0xff becomes 65535 instead of -1). Commit message adjusted the same way (one sentence; trailers untouched; tree identical to 904530b).

2. **PR text: 'the 32 bit case already produced the right bits through int overflow' overstates the mechanism** (fixed)

   Agreed: the old `(int)data[3] << 24` is a signed left shift into the sign bit whose status depends on the host C++ version; what the earlier rounds established is that the bits came out right in the tested builds (ul1.c and the 32-bit controls byte-identical before and after). Sentence replaced with: the previous 32 bit assembly already produced the expected bits in the tested builds; the unsigned shift makes the intent explicit, and no failing 32 bit case is known.

3. **Commit message still carries the Claude-Session trailer** (left-for-jolyon)

   Per the task rules the trailer lines (Co-Authored-By, Claude-Session) are not to be changed in this round; Jolyon decides them for all branches at once. The commit keeps both trailers exactly as before; the PR body carries no claude.ai link.

**Re-validation.** Text-only round: no code or test file changed (git diff --stat 904530b e0c8823 is empty, the tree is identical; worktree clean; bin/oscar64 at 07:00 is newer than InterCode.cpp at 06:49, so the installed compiler matches the commit). Re-ran, on 4da3147 (~/src/oscar64-base), the worktree compiler and v1.32.273 (~/src/oscar64), in the ten -ea -g {-bc,-n} x {default,-O2,-O0,-Os,-O3} configurations: final3/head.c (the PR's headline example) base 1 in all 10, fixed 0 in all 10, v1.32.273 0 in all 10; final3/ptrobs.c (pointer form, if-comparison) base fails at -O2/-Os/-O3 (6 of 10), fixed 0 in all 10, v1.32.273 fails the same 6; p/br1.c on v1.32.273 fails -O2/-Os/-O3 both backends (6 of 10), confirming the 'comparison feeds an if' sentence; final3/loopobs.c base exit 2 (s/3 = 21844) at 8 of 10 (passes -O0), fixed 0 in all 10; final3/fillobs.c base exit 3 in all 10, fixed 0 in all 10. Autotest and corpus were not re-run (unchanged binary): the evidence stands from the fix-up round, autotest-fixup2.log 1551 emulations vs baseline 1541, 0 new failures / 0 fixed / 0 failing in both; corpus-fixup2 181 files x 5 configurations, 845 both compile, 826 identical, 19 differ (new test, r20/r21/r22 reproducers, testint16mul bc-O2 include-path quirk), 0 status changes. Whole PR body and commit message re-read against these numbers.

</details>

## Final check (Codex, read-only, on the final commit)

<details><summary>SUBMIT AFTER CHANGES</summary>

VERDICT: SUBMIT AFTER CHANGES

1. **[low] PR text: “s is 65533”, “d is -65535”, and “In all three, -3 (bytes FD FF) becomes CI:65533”.** Distinguish optimizer constants from observable C values: those numbers cannot be represented by Oscar64’s signed 16-bit `int`. Describe them as incorrect internal `mIntConst` values and give the failing comparison as the observable result. Also separate the fill case: `memset(..., 0xff, ...)` produces `65535` instead of `-1`; a uniform fill cannot produce FD FF.

2. **[low] PR text: “the 32 bit case already produced the right bits through int overflow”.** This overstates the mechanism. The precise signed-shift rules depend on the host C++ language version; the evidence establishes resulting bits, not “int overflow.” Replace with: “The previous 32-bit assembly already produced the expected bits in the tested builds; the unsigned shift makes the assembly explicit, and no failing 32-bit case is known.”

3. **[low] Commit message: `Claude-Session: https://claude.ai/code/session_...`.** The supplied commit still contains the session link despite the earlier cleanup finding being marked resolved. Remove that trailer before submission; retain the intended AI attribution.

No blocking code or regression-test defect is apparent from the supplied diff and evidence. The two additional folding paths are addressed, the independently reported probes establish baseline failures, and the unranged-load representation risk is now explicitly disclosed rather than claimed to be inherently safe.

</details>

## Before submitting

- Make the AI-assistance line the same in every PR body (some end with a sentence, some with a "Generated with Claude Code" footer), as Jolyon decides.
- Commit trailers: drop the `Claude-Session:` line and use one `Co-Authored-By:` line, as Jolyon decides for all PRs (see OSCAR64-UPSTREAM.md).

## Risks and limitations

Unchanged from the fix-up round: (1) loads without a range (full-width bitfields, single-member struct copies, short-struct return marshalling, inline-asm operands) are now sign extended by default; for unsigned data this changes the 64-bit representation of the constant, not its bits, and every unsigned consumer checked normalizes; only a bytecode immediate encoding changed in probes (#$fffd -> #-3). (2) The 32-bit hunks change unsigned long constants >= 2^31 from a negative to a positive mIntConst with no observable difference found. (3) retA.c (by-value struct return at -O0) is still wrong on main after this fix, a separate mechanism, disclosed in the PR. (4) Not tested: real hardware, the nethack64 port build. (5) The Claude-Session trailer remains in the commit message pending Jolyon's decision.

## Related bugs found, not fixed here

All identical on 4da3147 and the fix unless noted; probe files under /home/jolyon/nethack64/build/oscar64-wt/r20-abs-member-review/p/ unless noted.
1. retA.c: by-value struct return `struct p4 b = mk4(); d = b.x < 0 ? -b.x : b.x;` returns 1 at -O0 (both backends) with the fix, 1 in all ten on 4da3147, 0 in all ten on v1.32.273. Load/store forwarding of the B_AND R0(L),65535 return-marshalling temp into a 16-bit signed load. Main-only regression.
2. crash/c05.c and ul2.c: `(gi(&s) < 0 ? -(long)gi(&s) : (long)gi(&s)) != 32768l` aborts the compiler (Array.h:244 GrowingArray assertion, rc 134) at bc default, bc -O0 and n -O0 on 4da3147; v1.32.273 fine. Main-only regression.
3. bc14.c and scu.c (return 14): `(int)(v - 65530u) * 2 != 6` with unsigned short v returns 1 at bytecode default and -O0 on 4da3147; v1.32.273 fine. Main-only regression.
4. cpp4.cpp: `static int rabs(const int & v) { return v < 0 ? -v : v; }` returns 0 for -3 on 4da3147, the fix and v1.32.273 at every level (cpp8.cpp, copying to a local first, is fine).
5. include/limits.h defines CHAR_MIN as -128 while plain char is unsigned (ch1.c passes `(char)253 > 100` on all three compilers).
6. New, scratch fx/neg/n3.c: initializing a variable of an undeclared struct type (`struct point pt = {-3, 4};` with no struct point) reports error 3006 then segfaults the compiler (rc 139) on 4da3147, the fix and v1.32.273.
7. nethack64 tests/oscar64-repros/r20_abs_of_member_via_pointer.c header still says 1.32.273 needs the second helper; it fails without one when the comparison feeds an if (br1.c). Outside my worktree, not changed.

## Draft pull request

**Title:** Fix sign extension when folding loads of signed values from known bytes

````markdown
An abs()-style conditional on a signed struct member whose value the optimizer can see in the initializer is miscompiled. With the current main (4da3147) this program returns 1 instead of 0 at every optimization level, `-O0` included:

```c
struct point { int x, y; };
int main(void)
{
	struct point pt = {-3, 4};
	int d = pt.x < 0 ? -pt.x : pt.x;
	return d == 3 ? 0 : 1;
}
```

Reproduce with `oscar64 -ea -g -n example.c` (also fails with `-bc`, and at `-O0`, `-O2`, `-Os` and `-O3`): the compiler reports `error 3007: Execution failed '1'`. The same happens when the member is read through a pointer (`static int ax(struct point * pt) { return pt->x < 0 ? -pt->x : pt->x; }`), there at `-O2`, `-Os` and `-O3`. Release 1.32.273 has the same defect: it fails the pointer form at `-O2`/`-Os`/`-O3` when the comparison feeds an `if` (`if (ax(&pt) != 3) return 1;`); 48f90e2 extended the range-based simplification of relational operators to comparisons used as values, so on main the `?:` form fails as well.

Two more constructs fail the same way:

```c
static const int tab[4] = {-3, 5, -7, 2};
int s = 0;
for (char i = 0; i < 4; i++) s += tab[i];
if (s / 3 != -1) return 1;   /* taken at default, -O2, -Os, -O3: s / 3 is evaluated at compile time to 21844 */
```

```c
int a[4];
memset(a, 0xff, sizeof(a));
int d = a[1] < 0 ? -a[1] : a[1];
if (d != 1) return 1;        /* taken at every level: the comparison is folded to true */
```

Root cause: three places in `oscar64/InterCode.cpp` turn a load from known bytes into an `IC_CONSTANT` and assemble the bytes of an 8 or 16 bit value as an unsigned number. `LoadConstantFold` folds a load from constant initializer data (reached from the peephole pass once `CopyLocalSingleAssignedConstants` has redirected the load of a never-rewritten local to its initializer, and from constant propagation). `LoadConstantOperand` does the same for the compile-time evaluation of loops (`ConstInnerLoopOptimization`, `ConstSingleLoopOptimization`). The `IC_FILL` case of `LoadStoreForwarding` builds the value of a load from the `memset` fill byte. In the first two, the `int` member or table entry `-3` (bytes FD FF) becomes the internal constant `mIntConst = 65533` in a temp whose range is [-32768..32767]; in the fill case the `0xff` fill byte becomes `65535` instead of `-1`. These are not values a 16 bit `int` can hold, and the stored bytes themselves are right: a program that prints `s` or `d` on the unfixed compiler sees -3 and 1. What goes wrong is everything computed from the constant at compile time, because the constant folding and value range analysis take `mIntConst` as the mathematical value: the range becomes the impossible [65533..32767], `-pt->x` folds to -65533, the range-limited relational simplification decides `== 3` is always false, `s / 3` is evaluated to 21844, and `main` collapses to `return 1`.

The fix sign extends the assembled value with `ToTypedSigned` unless the destination operand is known to be non-negative (`mDst.IsPositive()`, the signal the loop range analysis already uses to tell signed from unsigned loads of constant data). The front end gives loads of C integer types a range from the type, so unsigned loads are unaffected. Loads without a range (full-width bitfields, single-member struct copies, short-struct return marshalling, inline assembler operands) are now sign extended by default; for signed data that is the fix (a signed `int x : 16` member and a `struct { short v; }` copy are both wrong today), for unsigned data it changes only the 64-bit representation of the constant, not its bits, and every consumer I checked normalizes unsigned operations with `ToTypedUnsigned` or a `uint` cast. The 8 and 32 bit cases get the same treatment for consistency, and the `<< 24` is done as `uint32` so the unsigned bit assembly is explicit; the previous 32 bit assembly already produced the expected bits in the tested builds, so this only makes the intent explicit, and no failing 32 bit case is known. No optimization is disabled. 16 lines added, 2 changed.

The regression test `autotest/constinitsignedtest.c` covers a struct member read through a pointer and directly (`int`, `signed char`, `long`), a full-width signed bitfield, a single-member struct copy, a loop over a `static const int` table, a load forwarded from `memset`, signed minimum and maximum at each width (read by widening), and unsigned controls at the sign bit and the maximum. It is discovered by the autotest makefile and registered in `autotest.bat`. Before the fix it fails (assert, emulation result -1) in all ten `-ea -g {-bc,-n} x {default,-O2,-O0,-Os,-O3}` configurations and in `-O1`, `-O2 -Oo`, `-O2 -Ox`, `-O2 -xz -Oz`, `-O2 -strict` and `-O3 -Op`; after the fix it passes all 22, as C and as C++. Only the `int` through-pointer, direct access, bitfield, struct copy, loop and `memset` blocks fail before the fix; the `signed char` and `long` blocks and the unsigned controls pass before and after.

Validation against main 4da3147 on Linux:

- Full autotest: 1541 successful emulations on the baseline, 1551 with the patch and the new test, 0 failing steps in both runs.
- 181 sources (the autotest directory plus small reproducers from our project) compiled with the unmodified and the patched compiler in five configurations (`-n -O2/-Os/-O0/-O3`, `-bc -O2`): 845 compile with both, 826 are byte-identical, no file changes between compiling and failing. The 19 differences are the new test and three of our reproducers that contain the constructs above (all now compute the right value, each 2 bytes smaller at `-O2`/`-Os`/`-O3`), plus `testint16mul.c -bc -O2`, whose bytecode depends on the include path string of the compiler build (the patched binary pointed at the baseline's include directory produces the baseline's bytes).
- Sixteen samples and autotests that do not use the construct, in eight configurations each, are byte-identical in native code. The one code generation change outside the failing constructs is in bytecode for an `unsigned short` read through a single-member struct copy, where the constant is now emitted as the sign-extended immediate `#-3` instead of `#$fffd`: same value, same results.
- Five invalid or warning programs (including a constant index out of bounds through the loop path) give identical diagnostics before and after.

Known limitation: a by-value struct return (`struct p4 b = mk4(); d = b.x < 0 ? -b.x : b.x;`) is still wrong at `-O0` on main after this change (correct in 1.32.273); the wrong constant there comes from forwarding the 32 bit return-marshalling temp into a 16 bit load, a separate mechanism I have not touched.

This fix was prepared with AI assistance (Claude Code); the analysis, the intermediate code dumps and all numbers above come from runs of the actual compilers.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
````
