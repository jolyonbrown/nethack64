# 04. Fix function pointer members of global structs

| | |
|---|---|
| Branch | `fix/fnptr-member` in `~/src/oscar64-dev`, commit `335f4563639f`, one commit on upstream main 4da3147 |
| Patch | [`tools/oscar64-upstream/patches/main/04-fnptr-member.patch`](../../tools/oscar64-upstream/patches/main/04-fnptr-member.patch) |
| Kind | regression on main, plus wrong code on v1.32.273 |
| Since | regression: 349b10a (main only); call edge: v1.32.273 and older |
| NetHack | Upstream main (since 349b10a, 2026-10-26) rejects assignments to and calls through function-pointer members of global structs, so NetHack compiles 0 of 107 files with main: every window call goes through `windowprocs`. The same fix also adds the missing call-graph edge for such calls, which is wrong code on our pinned v1.32.273 today (compat #27, repro r23: the callee's frame overwrites the caller's live locals, native code, every level). The call-edge part is in the proposed patched pin. |
| Reviews | Opus (round 1, ran probes): do-not-submit, 2 high, 3 medium, 1 low; Codex (read the diff): submit after changes; fix-up: ready; final Codex check: submit after changes; final Opus re-review: submit-after-changes |
| Recommendation | **Submit, high priority: it is a regression on main that breaks any program with function pointers in a global struct.** |

## In plain words

Oscar64's current development version broke a common C pattern: a struct of function pointers kept in a global variable, assigned and called as w.fn = f; w.fn(1). NetHack's whole window interface works like that. The compiler had started looking up the function pointer's type through a shortcut that, for a member of a global struct, pointed at the struct variable itself, so it reported bogus type errors, crashed with -Ofp, and, older than that, forgot to record that the call happens at all, which let the called function overwrite the caller's live variables in native code. The fix adds a small helper that walks from the struct variable to the actual member at the byte offset and uses it in the three places that need the member rather than the variable. This final round made the call-graph part complete (members in anonymous unions and calls through a variable index into an array member were still missed), kept the volatile qualifier like const, strengthened the tests so each part of the fix is guarded by a test that fails without it (bit fields, const assignments, inherited members, no reliance on integer overflow), and rewrote the PR text to be shorter and accurate about what -Ofp still gets wrong.

## The fix

The fix (unchanged core from 3efe094): Declaration::RefDeclaration() resolves the member a DT_VARIABLE_REF into a global aggregate designates (arrays, nested structs, bit fields spanning their bits, C++ base classes; nullptr in a union). The code generator uses it for the function pointer type (all array levels stripped) and re-applies the expression's const and now also volatile qualifier; FunctionSets::Analyze returns the member slot for -Ofp. Changed in this round, and the part nethack64 carries on v1.32.273 (self-contained, GlobalAnalyzer.cpp, EX_VARIABLE case of GlobalAnalyzer::Analyze, just before 'return vdec'): when exp->mDecValue is a DT_VARIABLE_REF and exp->mDecType with its array levels stripped is a function type (IsFunctionType: function or pointer to function), do not return the root variable. Compute the expression's array depth; if RefDeclaration() resolves a member whose type is an array-of-function-pointer or function pointer, strip array levels from the member's type until its depth equals the expression's and return that type (so w.fn returns the pointer type, w.fn[i] returns the array type and EX_INDEX returns the element type, the depth check protects against mismatches); otherwise return exp->mDecType. RegisterCall then registers the call for members of structs, arrays, anonymous unions, constant and variable indices into array members and into plain global arrays. On a tree without RefDeclaration (v1.32.273), the same block reduced to 'if (exp->mDecValue->mType == DT_VARIABLE_REF) { strip arrays from exp->mDecType; if function type return exp->mDecType; }' gives the call edge without the -Ofp-rewritten type, which v1.32.273 does not have. Other changes: ToVolatileType() beside the two ToConstType() calls in InterCodeGenerator.cpp; tests as described.

## Regression test

autotest/funcptrmembertest.c (15 configurations incl. -Ofp): bit field case now a:3, b:5 so the member starts inside the first bit field's storage unit (guards the extent rule; mut-bf crashes); call-edge harness with bounded arithmetic; new caller_varidx(i, x, y) calling cwa.fn[i](x, y) with live locals. autotest/funcptrmemberaddrtest.c (10 configurations, no -Ofp): new caller_union (function pointer in an anonymous union of a global struct) and caller_2d (cw2.fn[i][1 - i](x, y)) with live locals; fails on 3efe094 at -n -O0. autotest/funcptrmemberconsttest.c + makefile rule funcptrmemberconstconstraints (in all:) + autotest.bat labels: valid program by default, 7 -dFUNCPTR_CONST_* selectors each expect exit 20 and 'error 3014: Cannot assign to const type' in -n and -bc; passes on fix and v1.32.273, fails on 4da3147 and 349b10a. autotest/funcptrmemberbasetest.cpp (10 configurations): member inherited through two base classes, assigned via Base* and via the global, called with live locals; fails on 4da3147 (compile) and v1.32.273 (-n wrong result). All registered in autotest.bat; the .c/.cpp files are picked up by the makefile wildcard.

## Evidence

*These are the fix-up round's results, for commit `3efe094c8e94`. The last round changed the code; its re-validation of the final commit is under "Last round" below.*

**Repro matrix.** Columns: -bc {none,-O2,-O0,-Os,-O3} | -n {same}; P = exit 0 and 'Emulation result 0', F = error or wrong result, S = crash. Full log: /home/jolyon/nethack64/build/oscar64-wt/fnptr-member-scratch/fixup/final-probes.log (134 programs x 3 compilers x 10 configurations, plus -Ofp x 5 for 4da3147 and the fix).
Case files fnmember_{global,static_global,global_init,assign,assign_decl_with_var,call_winprocs}.c: 4da3147 FFFFF FFFFF -> fix PPPPP PPPPP (v1.32.273 P); -Ofp F -> P. fnmember_local_ok.c control P everywhere.
autotest/funcptrmembertest.c: FFFFF FFFFF -> PPPPP PPPPP; -Ofp SSSSS -> PPPPP; autotest.bat extras 6/6 P. autotest/funcptrmemberaddrtest.c: FFFFF FFFFF -> PPPPP PPPPP (not -Ofp: crashes before and after, see o01/o03).
Opus wrong-code probes w01/w02/w03/w05/w06/w07: FFFFF -> PPPPP (earlier fix: PFPFF); -Ofp F -> P. Controls w04/w08/w09/w10 P -> P.
Rejected-initialiser probes s11/s12/s13/s14/s15: P -> P (earlier fix: F). s23/s24 static local: FFFFF -> PPPPP. s21/s22 F on all three (invalid).
Const probes i01/i01a/i01d/i01n/i02: F -> F (now error 3014, was bogus 3012); i01l/i01p: 4da3147 P (accepted) -> F (3014, like v1.32.273). i03-i10 negative: unchanged, same diagnostics as v1.32.273.
Call-edge probes cg01/cg03/cg05/cg07: F -> P (v1.32.273 PPPPP FFFFF); cg04 PPPPP PPFPP -> PPPPP PPPPP; cg06 S -> P; cg02 P -> P. All P with -Ofp.
Variants v01 S->P, v02 F->P, v03 F->P (-Ofp still F, pre-existing one-level limitation, local v03b/v03c also F with -Ofp on 4da3147), v04 F->P (-Ofp F, same), v05 P->P, v06-v09 F->P, v10 S->P, v11 F->P, v13 F->P, v14 P->P, v15 F->P, v16/v17 F->P, v18 P->P, q01 F->P, cq01 F->P, example.c F->P, t_nocrash F->P.
C++: c01, c04, fnmember_global.cpp, w01.cpp, funcptrmembertest.cpp (unnamed struct tagged), funcptrmemberaddrtest.cpp, inherit.cpp, staticmem.cpp: F -> P (and -Ofp P); c03 P->P; constmethod.cpp P->P; constmethod_bad.cpp P (accepted!) -> F (3014); i01.cpp F->F; c02 lambda probes F on all three (unsupported).
My probes: bf_before/bf_after/bf_mix/bf_nobits_nocall/bf_plain_ofp F->P incl. -Ofp; arrstruct_init S->P; anonunion.c and anonunion_ptr.c F->P without -Ofp, F with -Ofp (anonunion_local.c crashes with -Ofp on 4da3147 and after).
Unchanged pre-existing: r1/r2 (struct member) S -> PFPFF/PFPPF, matching the data-pointer analogues r1_dataptr_member/plain PFPFF on 4da3147 and after, and r3/r6 plain PFPPF on both; v12/v12b/v12c compare probes fail on 4da3147 (S/F) and after (F); r4*/r7/x01/n01 identical before and after; o01/o02/o03 identical.
Code size: __noinline callm (return w.fn(x)) is 37 bytes at -n -O2 with v1.32.273 and with the fix (.map); calla/callg 47 -> 37 is a main-vs-v1.32.273 difference present for the plain global too.

**Autotest.** make -k -j4 -C make check on the final commit (log /home/jolyon/nethack64/build/oscar64-wt/fnptr-member-scratch/autotest-fixup.log): autotest_diff.py autotest-base-4da3147.log autotest-fixup.log -> emulations: base 1541, new 1566 (+25 = funcptrmembertest 15 configurations + funcptrmemberaddrtest 10); new failures: 0; fixed: 0; failing in both: 0; no 'Emulation result -' and no make error lines. The run was repeated three times during the work (after each compiler change); the reported numbers are from the final one.

**Corpus.** corpus_diff.py ~/src/oscar64-base/bin/oscar64 <worktree>/bin/oscar64 --out .../fnptr-member-scratch/corpus-fixup -j4 on the final commit: 182 files (160 autotest sources + 22 nethack64 tests/oscar64-repros/*.c; the repro directory grew by 2 files during the day, the earlier report said 178/20) x 5 configurations (-n -O2, -n -Os, -n -O0, -n -O3, -bc -O2) = 910 compilations. Both compile: 840; byte-identical: 839; different: 1; status changed: 10; both fail: 60. The 10 status changes are funcptrmembertest.c and funcptrmemberaddrtest.c going error -> ok in all 5 configurations (the fix). The 1 difference is autotest/testint16mul.c at -bc -O2 (md5 base b9c6a49f, new 6f5e7d9b), the known include-path quirk, re-verified with the final binary: 4da3147's compiler with -ii=<worktree>/include produces 6f5e7d9b and the patched compiler with -ii=~/src/oscar64-base/include produces b9c6a49f; the two include directories are identical (diff -rq empty). So every program both compilers accept compiles to the same bytes.

## Review findings and what happened to them

| From | Severity | Finding | Resolution |
|---|---|---|---|
| opus | high | New silent wrong code: write to a function-pointer member of an initialised global/static struct deleted at -O2/-Os/-O3 (w01/w03/w06) | fixed |
| both | high | Rejects valid static initialisers: &ap.fn[1], ap.fn (decay), ap.fn + 1, &w.fn[1][0], static local &lw.arr[1] (s11-s14, s23; Codex finding 1) | fixed |
| opus | medium | Assignment to a function-pointer member of a const global struct silently accepted (i01, i01n; i01l/i01p already on 4da3147) | fixed |
| opus | medium | Test does not cover the wrong-code half (missing call edge); a type-lookup-only re-implementation would pass it | fixed |
| opus | medium | Same-class variants remain: 2-D global function-pointer arrays rejected (v04); constant-index global array calls get no call edge (cg04) | fixed |
| opus | low | -Ofp: 2-D function-pointer array members go from rejected to wrong code (v03) | out-of-scope |
| opus | low | PR text issues 1-10 (3 of 5 errors shown, exit status, 'main' ambiguity, call edge omitted, vacuous byte-identical claim, corpus counts wrong, -Ofp exclusion reason, line numbers, bisect inconclusive, length) | fixed |
| codex | medium | Array tests do not exercise initialised members or non-zero member offsets; add initialised array member, objects[1].fn, block-scope static struct, multi-dimensional member array | fixed |
| codex | medium | Validation paragraph counts and configurations need reconciling (178 vs 178+20, 820/819 vs two configurations) | fixed |
| codex | low | Negative controls: const aggregate assignment must be rejected; &b.bit should be rejected; C++ and unrelated-code claims should stay limited to what was tested | fixed |
| opus | medium | (found during re-validation) Bit fields before the member made the offset walker pick the wrong member under -Ofp | fixed |
| opus | medium | (found during re-validation) C++ base-class members and anonymous unions are not in the struct's member list | fixed |

<details><summary>Evidence for each finding</summary>

1. **New silent wrong code: write to a function-pointer member of an initialised global/static struct deleted at -O2/-Os/-O3 (w01/w03/w06)** (fixed)

   Reproduced on the earlier fix (156921f): w01, w03, w06 all PFPFF PFPFF (ten configurations -bc/-n x none,-O2,-O0,-Os,-O3), 4da3147 FFFFF, v1.32.273 PPPPP. Root cause confirmed as the EX_QUALIFY approach (GlobalOptimizer EX_QUALIFY analyses the base with ANAFL_RHS only). Fixed by changing approach: the DT_VARIABLE_REF fold is kept unchanged, so writes keep going through EX_VARIABLE with LHS flags as in v1.32.273; the three consumers resolve the ref to its member instead (Declaration::RefDeclaration). After: w01-w07 PPPPP PPPPP and PPPPP with -Ofp; w04/w08/w09/w10 controls unchanged. The shape (initialised global, static and nested struct and array member, reassigned in one __noinline function, called from another) is now in autotest/funcptrmembertest.c.

2. **Rejects valid static initialisers: &ap.fn[1], ap.fn (decay), ap.fn + 1, &w.fn[1][0], static local &lw.arr[1] (s11-s14, s23; Codex finding 1)** (fixed)

   Reproduced: s11-s14 FFFFF FFFFF on 156921f ('error 3008: Non constant initializer'), PPPPP on 4da3147 and v1.32.273. With the fold kept these are no longer touched: s11-s15 PPPPP PPPPP after. s23/s24 (static local struct) were FFFFF on 4da3147 itself (same 349b10a bug; static locals are folded too) and are PPPPP after. All four address shapes plus &gp.arr (pointer to array), the static local and the 2-D element address are in autotest/funcptrmemberaddrtest.c.

3. **Assignment to a function-pointer member of a const global struct silently accepted (i01, i01n; i01l/i01p already on 4da3147)** (fixed)

   Reproduced: i01 and i01n compiled on 156921f; i01l (local const struct) and i01p (const struct pointer) compiled on 4da3147 too; v1.32.273 rejects all with 3014. Cause confirmed: 349b10a reads the type from the declaration and drops the DTF_CONST the parser put on exp->mDecType (Parser.cpp:8589). Fixed at both InterCodeGenerator sites (EX_VARIABLE :2673 and EX_QUALIFY :3073 of 4da3147) with ToConstType() when exp->mDecType is const. After: i01, i01a, i01d, i01l, i01n, i01p, i02 and a C++ const member function writing fn all give 'error 3014: Cannot assign to const type', identical to v1.32.273; const reads/calls (v07, v08, constmethod.cpp, cq01 callc/callca) still pass, also with -Ofp. Negative cases cannot live in autotest; checked as scratch probes.

4. **Test does not cover the wrong-code half (missing call edge); a type-lookup-only re-implementation would pass it** (fixed)

   Reproduced: t_nocrash.c (the old test minus the variable-index line) passes on v1.32.273 in all ten configurations, while cg01 fails on v1.32.273 at -n (PPPPP FFFFF). Added the cg01 shape (caller keeps four locals live across cw.fn(x,y); callee calls a helper with its own locals) and the cg04 shape (carr[1](x,y)) to funcptrmembertest.c. Check: the new test minus the two variable-index lines fails on v1.32.273 at -n in all five levels (PPPPP FFFFF, assert at the caller/ref_caller line), so the GlobalAnalyzer part of the fix is guarded.

5. **Same-class variants remain: 2-D global function-pointer arrays rejected (v04); constant-index global array calls get no call edge (cg04)** (fixed)

   Reproduced: v04 FFFFF FFFFF on 4da3147 and 156921f ('i16(*)(i16)*[]' != ...), cg04 PPPPP PPFPP on both (fails -n -O0). Same root cause (the ref is unwrapped to the root variable; the old special case strips one array level). RefDeclaration walks all array levels and the consumers strip all array levels of the slot type: after, v04 PPPPP PPPPP, cg04 PPPPP PPPPP (also -Ofp PPPPP, before PPFPP). tab[2][2] is in funcptrmemberaddrtest.c, carr[1] in funcptrmembertest.c.

6. **-Ofp: 2-D function-pointer array members go from rejected to wrong code (v03)** (out-of-scope)

   Confirmed: with -Ofp v03 (global member), v04 (global 2-D array) are FFFFF after (run-time assert, were compile errors before); v03b (local struct) and v03c (through pointer) are FFFFF with -Ofp on 4da3147 itself. FunctionSets::CompleteAnalyze/Unify/AnalyzeInit handle one array level (FunctionSets.cpp:46, 173, 234); fixing that is a FunctionSets change outside this fix. Without -Ofp all 2-D cases pass; they live in funcptrmemberaddrtest.c, which is not run with -Ofp, and the PR names the limitation.

7. **PR text issues 1-10 (3 of 5 errors shown, exit status, 'main' ambiguity, call edge omitted, vacuous byte-identical claim, corpus counts wrong, -Ofp exclusion reason, line numbers, bisect inconclusive, length)** (fixed)

   Rewritten PR body: all five diagnostics and exit status 20 shown; 'current main (4da3147)'; the dropped call edge is described as a second effect and fixed; code-size claim replaced by the __noinline accessor callm (37 bytes with v1.32.273 and with the patch at -n -O2, taken from the .map files); corpus accounting with exact populations; the -Ofp exclusion reason is the (*pp)(...) crash at FunctionSets.cpp:370 (reproduced: o01/o03/s11-s15/v05 crash before and after with -Ofp); line numbers marked as 4da3147's; attribution to 349b10a stated as confirmed by reading (git show 349b10a adds the IsFunctionType branches at InterCodeGenerator.cpp:2673/3073 and the DT_VARIABLE_REF array special case); text shortened.

8. **Array tests do not exercise initialised members or non-zero member offsets; add initialised array member, objects[1].fn, block-scope static struct, multi-dimensional member array** (fixed)

   Added to funcptrmembertest.c: struct arrinit { int pad; int (*fn[2])(int); } ai = { 123, { add1, add2 } } called with constant and variable index and ai.pad checked; struct item objects[3] with initialisers and a struct holding an array of structs (tb.it[1].fn), called with constant and variable index and reassigned; a block-scope static struct with initialiser reassigned between calls; bit fields around the member. The 2-D member array w2.fn[2][2] is in funcptrmemberaddrtest.c because -Ofp miscompiles 2-D arrays on main (see the Opus low finding). All pass in the ten configurations, funcptrmembertest.c also in the five -Ofp and the autotest.bat extra configurations (-O2 -xz -Oz, -O2 -Oo, -O2 -Ox, with and without -Ofp).

9. **Validation paragraph counts and configurations need reconciling (178 vs 178+20, 820/819 vs two configurations)** (fixed)

   Final corpus run on the final commit: 182 source files = 160 autotest sources (autotest/*.c and *.cpp minus the 6 multi-file helpers) + 22 nethack64 repro files, 5 configurations each (-n -O0, -n -O2, -n -Os, -n -O3, -bc -O2) = 910 compilations; 840 compiled by both compilers, 839 byte-identical, 1 different (autotest/testint16mul.c at -bc -O2), 10 status changes (the two new tests, error -> ok, 5 each), 60 rejected by both. The one difference was re-verified as the include-path quirk by crossover: 4da3147 binary + patched tree's include dir gives the 'new' bytes (md5 6f5e7d9b), patched binary + 4da3147's include dir gives the 'base' bytes (b9c6a49f); the two include directories are identical (diff -rq). No mechanism beyond that is claimed.

10. **Negative controls: const aggregate assignment must be rejected; &b.bit should be rejected; C++ and unrelated-code claims should stay limited to what was tested** (fixed)

   c.fn = f on a const struct: now error 3014 (was accepted by 156921f, bogus 3012 on 4da3147). &b.bit (i09): accepted without error by 4da3147, v1.32.273 and the patch alike, unchanged (pre-existing, not touched; the earlier fix's extra & folding rule is gone). C++: c01 (template, ctor init, default member init, reference, namespace, static member fn), c03 (virtual), c04 (member fn in global ctor), single and two-level inheritance with members in the base (inherit.cpp), static data members, const member functions, and .cpp copies of both tests pass in all ten configurations and with -Ofp; i01.cpp and constmethod_bad.cpp are rejected. The PR limits C++ claims to these.

11. **(found during re-validation) Bit fields before the member made the offset walker pick the wrong member under -Ofp** (fixed)

   My first walker matched members by [mOffset, mOffset+mSize); bit fields a:3, b:5 sit at offset 0 with mSize 2, so offset 1 (the function pointer) resolved to 'a' and v15/bf_* were FFFFF with -Ofp (correct without). Fixed by spanning a bit field over its bits ((mShift+mBits+7)/8 bytes). After: v15, bf_before, bf_after, bf_mix (3-, 12-, 20-, 9-bit fields, nested struct, array member) PPPPP with and without -Ofp. v15 shape added to funcptrmembertest.c.

12. **(found during re-validation) C++ base-class members and anonymous unions are not in the struct's member list** (fixed)

   inherit.cpp (fn in base class B of global D/E) was wrong code with -Ofp with the first walker (local variant passed on 4da3147); fixed by descending the DT_BASECLASS chain (type->mBase, as Parser::MemberLookup does): inherit.cpp PPPPP with -Ofp. For a member of an anonymous union the parser clones the member out of mParams, so RefDeclaration returns nullptr and each consumer keeps its previous behaviour (expression type / root variable): anonunion.c compiles and runs correctly without -Ofp (4da3147: rejected; v1.32.273: no anonymous unions in C), with -Ofp it is miscompiled as 4da3147 already crashes or miscompiles the local-struct case (anonunion_local.c -Ofp: PSPSS on 4da3147 and after). An earlier variant that fell back to the expression type whenever the slot type was not a function type turned r4f (function returning NULL, -Ofp) into a type error because -Ofp rewrites both sides to void** on main; dropped, r4f PPPPP again.

</details>

## Last round: final-check findings and what happened to them

Changed in the last round: code. Commit before it: `3efe094c8e94`.

| From | Severity | Finding | Resolution |
|---|---|---|---|
| codex-1 / opus-1 | high | Function pointer in an anonymous union of a global struct gets no call edge (wrong code at -n -O0) | fixed |
| opus-2 | medium | Variable-index calls through an array member of a global struct register no call edge | fixed |
| codex-2 | medium | Call-edge regression test relies on signed int overflow | fixed |
| codex-3 / opus-4 | medium | Bit-field case does not guard the bit-field extent rule; 'v15 shape added' claim inaccurate | fixed |
| opus-5 | medium | Const restoration has no regression test; 'cannot live in autotest' was wrong | fixed |
| opus-3 | medium | -Ofp: anonymous-struct members reached through both the global and a pointer are miscompiled | deferred |
| opus-6 | low | -Ofp: initialized array member reassigned to a function with a different fastcall layout runs wrong | deferred |
| opus-7 | low | -Ofp drops volatile on function pointer members; fix restores const but not volatile | fixed |
| codex-4 / opus PR-text 1-7 | low | PR text: contradictory negative-test claims, false 'Without -Ofp these compile correctly', callm bullet, segfault on arrays of structs, attribution, cg04/corpus wording, report claims | fixed |
| opus PR-text 8 (style) | low | PR body length (about 1,070 words vs #440's 350), title prefix, trailer link | fixed |
| opus (trailer) | low | Trailer's claude.ai session URL and model name | left-for-jolyon |
| opus (adjacent) | low | Adjacent pre-existing bugs: v1.32.273 miscompiles nh01_windowprocs_shape.c at -Os; 4da3147 bit-field regression x01; 4da3147 -Ofp static/const global function pointer (cg/q1, q2); const forward declaration e01 | out-of-scope |

<details><summary>Evidence, and what was re-run</summary>

1. **Function pointer in an anonymous union of a global struct gets no call edge (wrong code at -n -O0)** (fixed)

   Reproduced with the previous commit's binary: p/a01_anonunion_calledge.c and a01d PPPPP PPRPP. Adopted the reviewer's GlobalAnalyzer::Analyze replacement (rewritten in my words, same logic): for a DT_VARIABLE_REF whose type, with array levels stripped, is a function type, return the resolved member's type (with as many array levels as the expression still has), else fall back to exp->mDecType, never the aggregate. After: a01, a01d PPPPP PPPPP; a01b/a01c controls unchanged. Regression: caller_union in autotest/funcptrmemberaddrtest.c (not -Ofp: anonymous unions untracked there), which fails on commit 3efe094 at -n -O0 (PPPPP PPRPP) and passes now.

2. **Variable-index calls through an array member of a global struct register no call edge** (fixed)

   Before: a04, a04g, a04d (2-D), a04f PPPPP PPRPP. After the same GlobalAnalyzer change (EX_INDEX now receives the member's array type and returns the element type): a04, a04g PPPPP PPPPP also with -Ofp; a04d, a04f PPPPP PPPPP without -Ofp (RRRRR with -Ofp: 2-D arrays and initialized arrays are listed -Ofp limitations). Controls a04b/a04c/a04e unchanged. Regression: caller_varidx (w.fn[i](x, y)) in funcptrmembertest.c (15 configurations incl. -Ofp) and caller_2d in funcptrmemberaddrtest.c; mut-ga (no GlobalAnalyzer hunk) fails both files at -n -O0.

3. **Call-edge regression test relies on signed int overflow** (fixed)

   Changed +100/+200 to +10/+20 in callee and ref_caller (max intermediate about 3600, no overflow at 16 bit) in funcptrmembertest.c and the same harness in the two new files. The reduced test still catches the bug: the reviewer's mut-ga build gives funcptrmembertest.c PPPPP PPRPP, funcptrmemberaddrtest.c PPPPP PPRPP, funcptrmemberbasetest.cpp PPPPP PPRPP; v1.32.273 crashes on funcptrmembertest.c (SSSSS SSSSS) and fails funcptrmemberbasetest.cpp at -n (PPPPP RRRRR).

4. **Bit-field case does not guard the bit-field extent rule; 'v15 shape added' claim inaccurate** (fixed)

   struct bits now uses a:3, b:5 (fn starts in byte 1, inside a's 2-byte storage unit) with bf.b = 21. The reviewer's mut-bf build (naive extent rule) now crashes on funcptrmembertest.c in all 10 configurations and with -Ofp (SSSSS SSSSS); the fix passes. Also added funcptrmemberbasetest.cpp (member inherited through two base classes, with live caller locals) so the DT_BASECLASS walk is exercised; it fails on 4da3147 (CCCCC) and v1.32.273 (PPPPP RRRRR) and passes with the fix. The inaccurate claim is gone from the PR text.

5. **Const restoration has no regression test; 'cannot live in autotest' was wrong** (fixed)

   Added autotest/funcptrmemberconsttest.c (valid program by default, FUNCPTR_CONST_{GLOBAL,LOCAL,STATIC_LOCAL,POINTER,ARRAY,NESTED,ARRAY_OF_STRUCTS} each add one invalid assignment) and the makefile rule funcptrmemberconstconstraints (in all:, c23enumconstraints style, -n and -bc, expects exit 20 and 'error 3014: Cannot assign to const type') plus the autotest.bat labels :testfuncptrmemberconstconstraints / :testfuncptrmemberconstinvalid. The rule passes with the fix (also all 7 selectors with -n -Ofp) and with v1.32.273, fails with 4da3147 and the reviewer's 349b10a build.

6. **-Ofp: anonymous-struct members reached through both the global and a pointer are miscompiled** (deferred)

   Confirmed: a02 fix -Ofp RRRRR RRRRR, without -Ofp PPPPP PPPPP; local a02g passes on base with -Ofp, so this is specific to the newly accepted global path. Cause as the reviewer says (two slots per member: the original in the anonymous type via RefDeclaration, the clone in the outer scope via EX_QUALIFY). A fix would have to map RefDeclaration's result to the outer-scope clone and change AnalyzeInit the same way, which is not a small, safe change for this PR. Listed in the PR's known limitations as -Ofp only, with the mechanism and the Parser::AddAnonymousStructMembers reference.

7. **-Ofp: initialized array member reassigned to a function with a different fastcall layout runs wrong** (deferred)

   Confirmed pre-existing: a03 fix -Ofp RRRRR; a03b (plain global array) on 4da3147 -Ofp RRRRR. Listed in the PR's known limitations; the 'same declaration AnalyzeInit unifies' sentence was removed (it holds for scalar members only).

8. **-Ofp drops volatile on function pointer members; fix restores const but not volatile** (fixed)

   Added 'if (exp->mDecType->mFlags & DTF_VOLATILE) ftype = ftype->ToVolatileType();' beside the two ToConstType() sites in InterCodeGenerator.cpp. v04_volatile_member_compare.c at -n -O2 -Ofp: before, w.fn was loaded once into T1 before the loop; after, it is reloaded (LDA w.fn / ORA w.fn+1) inside the loop. Without -Ofp the declared type already carries volatile, so this is a no-op there (corpus byte-identical). The p->fn path (v06, pre-existing on 4da3147) is not touched by this PR.

9. **PR text: contradictory negative-test claims, false 'Without -Ofp these compile correctly', callm bullet, segfault on arrays of structs, attribution, cg04/corpus wording, report claims** (fixed)

   PR body rewritten: known limitations are -Ofp only and complete (2-D arrays, anonymous unions and mixed anonymous structs, initialized array reassignment, wrong signature); the callm bullet is dropped; arrays of structs 'the compiler then also segfaults'; the corpus paragraph states exact counts, the status changes and that it has no -Ofp configuration; the const restoration is stated as a tested fact. The anonymous-union call-edge limitation no longer exists (fixed).

10. **PR body length (about 1,070 words vs #440's 350), title prefix, trailer link** (fixed)

   Body cut to about 600 words of prose (plus the example and its five diagnostics); title now 'fix: function pointer members of global structs'. The commit trailers (Co-Authored-By, Claude-Session) are unchanged as instructed.

11. **Trailer's claude.ai session URL and model name** (left-for-jolyon)

   Not changed, per the task rules; the PR body carries only the one-line AI-assistance disclosure and no claude.ai link.

12. **Adjacent pre-existing bugs: v1.32.273 miscompiles nh01_windowprocs_shape.c at -Os; 4da3147 bit-field regression x01; 4da3147 -Ofp static/const global function pointer (cg/q1, q2); const forward declaration e01** (out-of-scope)

   Not caused by this fix and not in its scope. nh01 is the call-edge bug on the pinned compiler, which nethack64's v1.32.273-patched-2 branch addresses by carrying the GlobalAnalyzer part of this change.

**Re-validation.** On the final commit 66975d6 (binary md5 c56ca1f6...): (1) Rebuilt with make -C make -j6 compiler. (2) Ten-configuration matrices (oscar64 -ea -g {-bc|-n} {none,-O2,-O0,-Os,-O3}; P pass, C compile error, R wrong result, S crash): funcptrmembertest.c fix PPPPP PPPPP (also PPPPP PPPPP with -Ofp), 4da3147 CCCCC CCCCC, v1.32.273 SSSSS SSSSS, mut-ga PPPPP PPRPP, mut-bf SSSSS SSSSS; funcptrmemberaddrtest.c fix PPPPP PPPPP, previous commit 3efe094 PPPPP PPRPP, 4da3147 and v1.32.273 CCCCC; funcptrmemberconsttest.c fix PPPPP PPPPP (and with -Ofp), 4da3147 CCCCC, v1.32.273 PPPPP; funcptrmemberbasetest.cpp fix PPPPP PPPPP, 4da3147 CCCCC, v1.32.273 PPPPP RRRRR, mut-ga PPPPP PPRPP. make funcptrmemberconstconstraints: passes with the fix and v1.32.273, fails with 4da3147 and 349b10a. Probes: a01, a01d, a04, a04g, a04d, a04f, c06, a01b, a01c, a04b, a04c, a04e, a02 all PPPPP PPPPP without -Ofp (before: a01/a01d/a04/a04g/a04d/a04f PPPPP PPRPP); with -Ofp a01, a01d, a04d, a04f, a02 RRRRR (documented limitations), a04, a04g, c06 PPPPP. v04 at -n -O2 -Ofp now reloads the volatile member inside the loop. The 7 fnmember_* case files: 6 go CCCCC -> PPPPP, fnmember_local_ok PPPPP on both; the 8 other cases in tools/oscar64-upstream/cases give identical matrices on base and fix. (3) Full autotest: make -k -j4 -C make check > fnptr-member-scratch/autotest-final.log: 1586 emulations (baseline 1541, +45 = 15 funcptrmembertest + 10 each for the three new files), 0 nonzero results, 0 make errors; autotest_diff.py: new failures 0, fixed 0, failing in both 0. (4) corpus_diff.py base vs fix --out fnptr-member-scratch/corpus-final -j4: 187 files x 5 configurations = 935 compilations; both compile 845, identical 844, different 1 (autotest/testint16mul.c bc-O2, the known quirk: crossover with -ii= shows base compiler + worktree include gives the 'new' md5 6f5e7d9b and fix compiler + base include gives the 'base' md5 b9c6a49f; include dirs identical by diff -rq), status changed 30 (the four new tests plus tests/oscar64-repros r23 and r25, error -> ok in all 5 configurations; both use function pointer members of global structs), both fail 60. (5) git: one commit on 4da3147 (rev-list count 1), worktree clean, only oscar64/*.cpp, *.h and autotest files staged.

</details>

## Final check (Codex, read-only, on the final commit)

<details><summary>SUBMIT AFTER CHANGES</summary>

VERDICT: SUBMIT AFTER CHANGES

1. **[high] `oscar64/GlobalAnalyzer.cpp:1050` — unresolved refs still lose the call edge.** For the documented global anonymous-union member case, `RefDeclaration()` returns `nullptr`; this branch then returns the root struct variable. Code generation now accepts the call using the expression type, but call registration retains the same fastcall-clobber risk this PR fixes elsewhere. Use the expression’s function-pointer type as the fallback when no resolved function type is available. Add an anonymous-union variant of the caller-locals regression without `-Ofp`. The reported simple union probes do not establish correct preservation of caller locals.

2. **[medium] `autotest/funcptrmembertest.c:148` and `:176` — the call-edge regression relies on signed overflow.** With 16-bit `int`, the first iteration computes `s = 100 * 201`, then `s * 7 = 140700`. Both the tested implementation and its oracle overflow; their equality is not guaranteed by standard C/C++. Use bounded arithmetic—for example, change the offsets to `+10` and `+20` in both implementations—and verify that the reduced test still fails on v1.32.273 or a type-lookup-only fix.

3. **[medium] `autotest/funcptrmembertest.c:98` — the committed bit-field case misses the demonstrated walker regression.** The earlier failure involved `a:3, b:5`, placing the function pointer at byte 1 inside the old, incorrect two-byte extent. The committed `a:3, b:12` case does not reproduce that overlap. Add the exact `3+5` case and run it with `-Ofp`; ideally confirm that reverting just the bit-field extent calculation makes it fail.

4. **[low] PR validation text — contradictory negative-test claims.** “In the ten configurations and with `-Ofp`” followed by “wrong signature … are rejected” conflicts with the acknowledged acceptance of wrong-signature assignments under `-Ofp`. Separate the negative-test results by configuration and state the exception explicitly. Also replace “Without `-Ofp` these compile correctly” with wording that distinguishes valid array/union programs from invalid assignments, which should be rejected.

</details>

## Check of the last-round commit (Codex, read-only)

<details><summary>SUBMIT AFTER CHANGES</summary>

VERDICT: SUBMIT AFTER CHANGES

1. **High — PR: “An initialized array member later reassigned to a function with a different fastcall layout runs wrong.”** This is a central, one-dimensional member case newly accepted by this patch. The analogous pre-existing bug for plain arrays does not make the newly enabled silent miscompilation safe. The `ra` test uses `add1` and `add2`, which misses the reported layout mismatch. Make initializer and assignment analysis track the same slot, or diagnose the unsupported case under `-Ofp`. Retain a regression using callees with different fastcall layouts.

2. **Medium — PR validation: “162 autotest sources plus 22 reduced NetHack files … five configurations.”** That is **920** compilations, but **845 + 30 + 60 = 935** reported outcomes. The earlier evidence supplies a different, internally consistent population; it does not substantiate these final numbers. Reconcile the final manifest and results, and update the accepted/identical counts together. Include the invocation or a results artifact supporting the final accounting.

3. **Medium — `autotest/autotest.bat:30`, inherited-member test registration.** `funcptrmemberbasetest.cpp` is only registered with `:test`; the makefile likewise supplies no explicit `-Ofp` run for it. Consequently, it does not guard the inheritance-specific failure reported during review: without base-class resolution, the expression-type fallback can still make ordinary compilation pass. Add `:testf` and corresponding native `-Ofp` makefile configurations for this test.

The supplied diff otherwise addresses the earlier folding, static-initializer, const, and call-edge findings convincingly. This assessment is based solely on the supplied code and evidence; I ran no commands.

</details>

## Final check (Opus, re-ran the evidence)

**submit-after-changes.** The fix takes the right approach and does what it says for NetHack's window table. Everything the author reported reproduced, and it leaves the compiled output of other programs unchanged. But one shape it newly accepts, a function pointer kept in an unnamed union inside a global struct, compiles into a program that gives wrong answers. A second shape that was already broken before (calling an entry of a function-pointer array inside a global struct with a variable index) is still broken, a small extra change I built and tested fixes both, and the PR's "known limitations" paragraph needs correcting before it goes upstream. Separately, the compiler nethack64 pins today miscompiles NetHack's own `(*windowprocs.win_x)()` call pattern with the project's `-Os` flags (probe: /home/jolyon/nethack64/build/oscar64-wt/fnptr-member-final-review/p/nh01_windowprocs_shape.c), so the port may already be affected.

- [high] New silent wrong code: calls through a function pointer in an anonymous union of a global struct get no call edge: In GlobalAnalyzer::Analyze EX_VARIABLE, fall back to the expression type: for a function-typed DT_VARIABLE_REF, return the resolved slot type when RefDeclaration() gives a function slot, else `return exp->mDecType;`, never vdec. I built this, together with the array extension from the next finding, as /home/jolyon/nethack64/build/oscar64-wt/fnptr-member-final-review/sugg (GlobalAnalyzer.cpp only). a01 and a01d then give PPPPP PPPPP, and all 160 autotest sources are byte-identical to the fix at -n -O2, -n -O0, -bc -O2 and -n -O2 -Ofp. Add a01's shape to funcptrmembertest.c (cg01 harness; anonymous unions are accepted in C mode on main).
- [medium] Variable-index calls through an array member of a global struct still register no call edge (pre-existing variant, not covered): Extend the GlobalAnalyzer block to DT_VARIABLE_REFs whose type is a (multi-dimensional) array of function pointers. Return the member's type with the same array depth as exp->mDecType, falling back to exp->mDecType, so EX_INDEX returns the element type. A tested 25-line replacement for :1050-1063 is in /home/jolyon/nethack64/build/oscar64-wt/fnptr-member-final-review/sugg/oscar64/GlobalAnalyzer.cpp. With it, a04 and a04g give PPPPP PPPPP also with -Ofp, a04f and a04d pass without -Ofp, and the existing tests stay byte-identical. Add a `caller_varidx(i, x, y)` using `w.fn[i](x, y)` with live locals to funcptrmembertest.c. If not fixed, name it in the PR.
- [medium] -Ofp: anonymous-struct members reached through both the global and a pointer are miscompiled (newly compiled): Either list 'members of anonymous structs and unions' under the -Ofp known limitations with a02 as the repro, or have RefDeclaration return the outer-scope clone when the walk passes through a DTF_INLINE anonymous element, e.g. Lookup of the member's ident in the nearest named struct's mScope. Note that AnalyzeInit keeps using the original, so initialised globals would then need the same mapping.
- [medium] Regression test does not guard the bit-field extent rule; report's 'v15 shape added' is inaccurate: Change `b : 12` to `b : 5` in struct bits, or add v15's struct, so fn sits inside the first bit field's declared storage. Fix the report's claim. Consider a C++ copy of the inheritance case (fn in a base class of a global derived object, p/c06_base_member_calledge.cpp passes on the fix and fails on v1.32.273 at -n), because no autotest exercises the DT_BASECLASS walk.
- [medium] Const restoration (a 349b10a accepts-invalid regression) has no regression test; the 'cannot live in autotest' claim is wrong: Add a `funcptrmemberconstconstraints` rule plus an autotest.bat label in the c23enumconstraints style. Use one source with -d selectors (global const struct, local const struct, `const struct procs *p`, const array member, nested const member), each expecting exit 20 and 'error 3014: Cannot assign to const type'.
- [low] -Ofp: initialised array member later reassigned to a function with a different fastcall layout runs wrong (pre-existing for plain arrays; test cannot see it): Add this to the -Ofp known limitations, as pre-existing on main for plain global arrays, and reword the Fix sentence to 'for scalar members'. No code change needed in this PR.
- [low] -Ofp drops volatile on function-pointer members; the fix restores const from the expression type but not volatile: Next to the ToConstType() lines at InterCodeGenerator.cpp:2684 and :3085, also apply `if (exp->mDecType->mFlags & DTF_VOLATILE) ftype = ftype->ToVolatileType();`, or list it as an -Ofp limitation.

## Before submitting

- Codex (second check) rates the `-Ofp` limitation "an initialised array member later reassigned to a function with a different fastcall layout runs wrong" as high: the patch makes such programs compile, and with `-Ofp` they then run wrong, as plain global arrays already do on main. Without `-Ofp` they are right. Either fix the `-Ofp` slot tracking for members (`AnalyzeInit` and assignments must use the same slot) or keep it as a stated limitation and let the maintainer decide; the PR states it.
- Reconcile the corpus numbers in the PR body (Codex: 920 compilations described, 935 outcomes reported).
- Register `funcptrmemberbasetest.cpp` with `:testf` (and an `-Ofp` makefile run) as well as `:test`.
- Done 2026-11-12 (Jolyon's decision): the commit ends with one `Co-Authored-By: Claude <noreply@anthropic.com>` line and no session link (message only; the tree is the one validated, commit `66975d6f0ecb` before), and the PR text ends with the same AI-assistance sentence as every other PR.

## Risks and limitations

(1) GlobalAnalyzer::Analyze now returns a type instead of the variable for every function-typed or array-of-function-pointer DT_VARIABLE_REF, including array-typed refs passed as arguments or used outside calls; RegisterProc and the argument loop tolerate a type (they only act on DT_CONST_FUNCTION / use pex->mDecValue directly), and the corpus is byte-identical for all 844 programs both compilers accept, but the -Ofp paths are only covered by funcvaropt.c and funcptrmembertest.c. (2) Preferring the resolved member's (possibly -Ofp-rewritten) type over exp->mDecType keeps -Ofp consistent; when RefDeclaration fails (union) the unrewritten type is registered, which is fine because such slots are not tracked by -Ofp anyway (and -Ofp miscompiles them, documented). (3) ToVolatileType() creates a volatile clone of the (possibly rewritten) pointer type for -Ofp; it is a no-op without -Ofp. The p->fn path keeps dropping volatile under -Ofp (pre-existing on main). (4) -Ofp known limitations now reachable for global members (2-D arrays, anonymous unions, mixed anonymous structs, initialized array reassigned, wrong signature accepted) are stated in the PR but not fixed. (5) The const-constraints rule depends on the exact diagnostic text 'error 3014: Cannot assign to const type'. (6) Not run: samples/ build, Windows autotest.bat, real hardware.

## Related bugs found, not fixed here

Pre-existing, not fixed here (all reproduced): (1) v1.32.273 (nethack64's pinned compiler) registers no call edge for a call through a function pointer member of a global struct or a constant-index global array, so in native code the callee can overwrite parameter slots the caller still needs: cg01, cg04, cg05, cg06, cg07 PPPPP FFFFF on v1.32.273. This affects the NetHack port today ((*windowprocs.win_x)() calls in native code) and deserves its own check; the pinned compiler also crashes on a variable-index call through an array member of a global struct (ap.fn[i](x), v03, funcptrmembertest.c) and on getf()(1) (v10b/v10c). (2) 4da3147 compares a global pointer against its later-assigned value after assert(!p) at -O2/-O3 (r3 fn ptr, r6 data ptr; struct-member versions r1/r2 and data-pointer analogues r1_dataptr_* show the same PFPFF pattern): a GlobalOptimizer/constant-propagation issue independent of this fix; the v12* '==' / '!' comparison probes fail on all three compilers in some configurations (!p on a known-null pointer folds to 0 in value context: r4n/r4m/r4k). (3) -Ofp on main: &g followed by (*pp)(...) crashes in FunctionSets.cpp:370 (o01, o03, s11-s15, s23, v05); writes through int(**)(int) give wrong results (o02); only one array level is tracked, so 2-D arrays of function pointers are miscompiled (v03b/v03c locals on 4da3147, v03/v04 globals after this fix); a function pointer returning NULL gets its type rewritten to void** on both sides (r4f, works by accident); a function of the wrong signature assigned to a function pointer is accepted (i04_plain/i04_local on 4da3147); members of anonymous unions are cloned out of the member list so -Ofp cannot track them (anonunion_local.c crashes with -Ofp on 4da3147); assigning a lambda crashes after error 3012 (lambda_plain/lambda_local on 4da3147). (4) Taking the address of a bit field (&b.bit, i09) is accepted by all three compilers. (5) The -bc -O2/-O3 output of autotest/testint16mul.c depends on the include directory's path string on 4da3147. (6) Declaration::ConstCast's existing DT_VARIABLE_REF walker (Declaration.cpp:1643) compares the full ref offset with member offsets without subtracting for nested structs; not touched.

## Draft pull request

**Title:** Fix function pointer members of global structs

````markdown
Since 349b10a (function pointer optimizations, `-Ofp`), a function pointer member of a global struct variable can neither be assigned nor called. v1.32.273 accepts this program; current main (4da3147) does not:

```c
static int f(int x) { return x + 1; }
struct procs { int (*fn)(int x); };
struct procs w;
int main(void) { w.fn = f; return w.fn(1) == 2 ? 0 : 1; }
```

`oscar64 -ea -g -n example.c` (also `-bc`, every `-O` level) exits with status 20:

```
example.c(4, 23) : error 3012: Cannot assign incompatible types 'w' != 'i16(*)(i16)'
example.c(4, 40) : error 3011: Not a simple type
example.c(4, 40) : error 3017: Too many arguments for function call
example.c(4, 43) : error 3011: Not a simple type
example.c(4, 43) : error 3013: Not a numeric or pointer type
```

Expected: compiles, `Emulation result 0`. Static and initialized globals, static locals, nested and array members, arrays of structs (the compiler then also segfaults) and `tab[0][0](1)` fail the same way; local structs, `p->fn` and plain global function pointers work. With `-Ofp` the compiler crashes. NetHack's window interface is a global struct of function pointers called as `(*windowprocs.win_askname)()`.

**Root cause.** `Expression::ConstantFold` folds a member of a global struct variable, and a constant index into a global array, into an `EX_VARIABLE` whose `DT_VARIABLE_REF` keeps only the root variable and a byte offset. Since 349b10a the code generator takes a function pointer's type from its declaration, so that the type rewritten by `FunctionSets::CompleteAnalyze` is seen (InterCodeGenerator.cpp:2673 on 4da3147, with a special case for a ref into an array but none into a struct); for a ref into a struct that "type" is the variable `w`. `FunctionSets::Analyze` and `GlobalAnalyzer::Analyze` unwrap the ref to the root variable too, so `-Ofp` unified the struct instead of the member, and `RegisterCall` saw a struct and registered no call edge. The missing call edge is older than 349b10a: with native code a caller that keeps locals live across `w.fn(x, y)` can have them overwritten by the callee's fastcall arguments (v1.32.273 at `-O0`); the same for `w.fn[i](x, y)` and `garr[1](x, y)`.

**Fix.** `Declaration::RefDeclaration()` finds the member a `DT_VARIABLE_REF` designates by walking the root variable's type to the offset, through arrays, struct members (bit fields span their bits) and C++ base classes; it returns `nullptr` when the offset ends in a union. The code generator takes the function pointer type from the resolved declaration with all array levels stripped (replacing the one-level special case), keeping the `const` and `volatile` qualifiers of the expression's type, so assigning to a member of a `const` struct is rejected again with error 3014 (since 349b10a it was accepted for local structs and `p->fn` as well). `FunctionSets::Analyze` returns the member slot. `GlobalAnalyzer::Analyze` returns the function pointer type of a function-typed ref, or the array type for an array member (`EX_INDEX` takes the element type), falling back to the expression's type when the member is in a union, so the call is registered in every case. Constant folding, `GlobalOptimizer` and initializers are unchanged.

**Tests**, all failing on 4da3147 in the ten `-bc`/`-n` × `-O` configurations and passing with the fix:
- `funcptrmembertest.c` (`:test`, `:testf`): assignment and calls through `s.m()`, `(*s.m)()` and `p->m()` for global, static and initialized structs, nested structs, array members with constant and variable index, arrays of structs, bit field neighbours (the member starts inside the first bit field's storage unit), a static local, a member reassigned in one function and called from another, and calls with live caller locals through a member, a constant array index and a variable index.
- `funcptrmemberaddrtest.c` (`:test`): `&w.fn`, `&w.arr[1]`, `w.arr + 1` as static initializers, two-dimensional arrays and an anonymous union member with live caller locals. Not run with `-Ofp`, which tracks one array level, does not track anonymous unions, and crashes on `(*pp)(...)` on main already.
- `funcptrmemberconsttest.c` with the `funcptrmemberconstconstraints` rule (like `c23enumconstraints`): seven invalid assignments to const members (global, local, static local, through `const struct *`, array member, nested, array of structs) each exit 20 with error 3014.
- `funcptrmemberbasetest.cpp`: a member inherited through two base classes.

**Validation** against 4da3147 (Linux, C64 target). Full autotest: 1586 emulations, none failing, no new failures against the baseline's 1541. 162 autotest sources plus 22 reduced NetHack files compiled by both compilers in five configurations (`-n -O0`, `-O2`, `-Os`, `-O3`, `-bc -O2`): 845 accepted by both, 844 byte-identical, 30 status changes (the four new tests and two NetHack files using the construct, error to ok), 60 rejected by both. The one difference, `testint16mul.c` at `-bc -O2`, is independent of the patch: each compiler produces the other's bytes when pointed at the other tree's identical `include/` with `-ii=`. The corpus has no `-Ofp` configuration; `funcvaropt.c` and `funcptrmembertest.c` cover it in autotest.

**Known limitations**, `-Ofp` only; without `-Ofp` these programs compile correctly. Two-dimensional arrays of function pointers are miscompiled (one array level is tracked, as for local structs on main). Members of anonymous unions in a global struct, and members of anonymous structs reached both through the global and through a pointer, are unified wrongly (an anonymous struct's members exist twice, in the anonymous type and as clones in the outer scope, see `Parser::AddAnonymousStructMembers`). An initialized array member later reassigned to a function with a different fastcall layout runs wrong (`AnalyzeInit` unifies the canonical element type, assignments the member; the same on main for plain global arrays). A function of the wrong signature assigned to a function pointer is accepted after unification (on main too, for plain globals and local structs).

Found while porting NetHack 3.4.3 to the C64. Prepared with AI assistance (Claude Code); the numbers above come from the validation runs described.
````
