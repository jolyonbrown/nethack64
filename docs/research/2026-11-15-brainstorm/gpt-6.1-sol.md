**Evidence key:** **M** = measurements supplied in the brief; **S** = linked sources; **E** = my calculations, estimates or proposed targets. I performed no new hardware measurements. Unless stated otherwise, these ideas preserve game semantics through compiler changes, window-port code or guarded mechanical transforms.

1. **Long list**

   1. **Constant-stride lookup:** replace `126*x` with split low/high tables; eliminate most of its 250 cycles. Costs table space; test one compiled accessor.
   2. **128-byte columns:** pad each 126-byte column by two bytes: **160 bytes total**. Simplifies indexing and page boundaries; test layout and serialization.
   3. **Squares table:** replace bounded coordinate squaring with lookup. Potentially saves approximately **0.15 s/turn**; prove bounds and compare exhaustively.
   4. **Range propagation:** improve Oscar64’s treatment of coordinate arguments and integer promotions. Saves wide operations; test generated assembly against boundary cases.
   5. **Reuse cell addresses:** calculate a candidate square once across terrain predicates. Avoid repeated arithmetic/translations; aliasing limits reuse. Start inside `mfndpos`.
   6. **Selective speed optimization:** compile hot functions for speed while retaining `-Os` elsewhere. Costs ROM; compare cycles and resulting bank crossings.
   7. **Quarter-square runtime:** accelerate remaining byte multiplication with approximately 2 KB of tables. Competes with cache RAM; benchmark actual operand distributions.
   8. **Profile-guided zero page:** prioritize frequently accessed pointers and scalars. Saves cycles and instruction bytes; measure spill costs before reserving globals.
   9. **Compiler-native far operations:** represent translation and its clobbers in compiler IR. Enables safe reuse; significant compiler work. Begin with one load/store primitive.
   10. **Hybrid near/far placement:** keep hot globals near, cold frames/tables far. Saves translations; memory pressure remains. Replay traces with candidate placements.
   11. **Virtual-page coloring:** distribute simultaneously hot pages across page-byte indices. Reduces tag conflicts without more RAM; test against the actual translation design.
   12. **Specialized fault handler:** fixed 256-byte transfers, resident assembly and register shadows. Targets hundreds of cycles saved per fault; benchmark eviction separately.
   13. **Separate immutable/mutable table fields:** ROM constants plus mutable sidecars. Reduces dirty traffic; generated accessors and save compatibility require care.
   14. **Far-aware string ABI:** remove copying wrappers where pointers can remain far. Could reclaim much of **26 KB**; test nested calls, varargs and returned-buffer lifetimes.
   15. **Inline direct bank calls:** move six-byte call payloads into ROM callsites; retain resident stubs for address-taken functions. Trade ROM growth for RAM.
   16. **Dirty paired-glyph rendering:** compose neighboring characters and redraw changed pairs. Costs shadow storage; benchmark a normal turn and full redraw.
   17. **Specialized decimal formatting:** optimize constant formats and decimal conversion. Preserve widths, signs and longs; compare output bytes against gcc.
   18. **REU bulk operations:** fill grids, exchange workspaces, retain screen images. Setup dominates short operations; benchmark crossover lengths.
   19. **RAM-oriented overlays:** bank out KERNAL; evaluate smaller executable windows and REU-loaded cold code. Gains RAM but adds refill latency; trace code misses.
   20. **Hardware tiers:** test Ultimate turbo and native C128/VDC separately. Large potential gains; requires platform work and measured compatibility.

2. **Top five**

   **1 — Fix affine indexing first.**  
   Put general constant-multiply strength reduction in Oscar64; use a guarded table/accessor as the immediate experiment. Two 80-entry byte tables need **160 bytes before alignment**, plus optionally a 21-byte `6*y` table. **E:** target 25–50 cycles for address formation rather than 250; that implies roughly **1.4× `mfndpos` and 1.7–1.9× terrain-predicate workload speedups**, using the measured fractions—not whole-game gains.

   Padding columns to 128 bytes is another attractive experiment: with a page-aligned base, two columns fit each page and no six-byte cell straddles it. Cost: layout changes and explicit serialization handling. Both approaches retain the original logical grid.

   **2 — Specialize squaring, with a fallback.**  
   Ordinary map coordinates give `|dx|≤79`, `|dy|≤20`, so maximum squared distance is **6,641**. A **512-byte**, split-byte table covering signed-byte differences avoids absolute-value arithmetic. Audit callers for sentinels and exceptional coordinates; retain the original expression outside proven bounds. The original [implementation accepts unrestricted `int` arguments](https://raw.githubusercontent.com/Vanilla-NetHack/NetHack-3.4.3/master/src/hacklib.c).

   **E:** an approximately 80–120-cycle bounded implementation would save around **0.15–0.17 s/turn** against the supplied 0.2-second estimate. Cheapest test: exhaustive valid-coordinate comparison, followed by the existing checksum workload.

   **3 — Reduce translations before enlarging the cache.**  
   Translate once per safely bounded record/page region, then reuse the near address. **E:** removing 8,000 translations saves **168,000 cycles, approximately 170 ms**. Moving from 64 to 128 cache pages saves only roughly **70–90 ms** at the quoted fault rates, while consuming another 16 KB.

   This belongs in compiler far-pointer lowering. Canonical far pointers must survive translation; temporary near addresses need pinning or invalidation across possible eviction. Cross-page fields, aliasing and calls are the main risks. Cheapest experiment: one `mfndpos` loop with compiler-visible translated-region lifetimes.

   **4 — Optimize status formatting and rendering together.**  
   The host status path consumes **20.8%** of instructions, but its C64 cost is unmeasured. NetHack’s [status source](https://raw.githubusercontent.com/Vanilla-NetHack/NetHack-3.4.3/master/src/botl.c) repeatedly appends formatted fragments. Keep an append cursor, specialize common conversions, and let the window port compare completed lines before drawing changed character pairs.

   Preserve displayed content, update timing and long-number support. **E:** a fourfold improvement to a genuinely 20.8% path would reduce total time by **15.6%**; this is a sensitivity calculation. Cheapest experiment: time formatting into RAM, then rendering an already formatted line, independently.

   **5 — Make faults small, predictable and write-aware.**  
   Keep page size, transfer length and low address bytes invariant; maintain software shadows and write only necessary REU registers. A clean fault’s DMA floor is approximately **256 cycles**; **E:** **330–400 cycles total** is a reasonable assembly-handler target, compared with 603 measured.

   That saves only approximately **25–44 ms/turn** at 123–160 faults: worthwhile, but below translation elimination. Dirty eviction requires another transfer. Measure clean, dirty, replacement-scan and interrupt costs separately. REU DMA halts the CPU, so completion polling is unnecessary. [REU programming reference](https://codebase64.c64.org/doku.php?id=base%3Areu_programming)

3. **6502 and scene-technique deep dive**

   **Arithmetic tables.** Quarter squares use  
   `a*b = floor((a+b)²/4) − floor((a−b)²/4)`.  
   [Neil Parker supplies a 2 KB implementation](https://www.llx.com/Neil/a2/mult.html). His published “38 cycles worst case” deserves correction: my instruction count gives **38 cycles without page crossings, up to 42 with them**, excluding **12 cycles for JSR/RTS**, argument setup and initial pointer setup.

   Use this for residual general multiplication after direct squares and stride tables. It is unsigned byte multiplication, not a drop-in signed 16-bit replacement. [Toby Nelson’s exhaustive comparison](https://github.com/TobyLobster/multiply_test) provides implementations and measured cycle/space tradeoffs. Keep arithmetic tables directly accessible; paging them can destroy their advantage.

   **Zero page.** A normal zero-page load/store costs **3 cycles and two instruction bytes**, versus **4 cycles and three bytes** for absolute addressing. The benefit compounds across frequently touched pointer bytes. Account for register spills and IRQ preservation before filling zero page with globals.

   Current [Oscar64 documentation](https://github.com/drmortalwombat/oscar64/blob/main/oscar64.md) already describes automatic global placement (`-Oz`), expanded zero page (`-xz`), and function-level speed/self-modification settings; check availability in your fork. Audit indirect calls and interrupts when overlaying static storage—escaped buffer addresses can outlive their producing functions.

   **Undocumented opcodes.** Useful compiler peepholes include memory-form `LAX` replacing `LDA; TAX` (**two cycles saved**) and zero-page `DCP` replacing `DEC; CMP` (**three saved**, when flags/liveness permit). `SAX` helps suitable masked stores. Reject unstable immediate `LAX`, `XAA` and problematic high-byte stores. Ordinary RAM operations are the appropriate starting point; read-modify-write opcodes have extra bus effects. [Oxyron’s opcode reference](https://www.oxyron.de/html/opcodes02.html)

   None improves the supplied six-instruction translation hit path. Expect local savings, not a new performance tier. Cheapest experiment: count eligible generated instruction patterns, implement one peephole, then verify flags and real hardware behavior.

   **Self-modifying code.** Put reusable kernels in writable resident RAM. Patching an address can replace `(zp),Y` access with absolute indexing, commonly saving **one cycle per access**; patching an immediate operand can eliminate a repeated variable load. Patching costs must be amortized across a loop. ROM code cannot use this directly, and kernels need explicit clobbers and reentrancy rules. [A scene programmer’s worked examples](https://nurpax.github.io/posts/2019-08-18-dirty-tricks-6502-programmers-use.html), [instruction timings](https://www.masswerk.at/6502/6502_instruction_set.html)

   **REU beyond copying.** STASH/FETCH can preserve whole workspaces or prebuilt display backgrounds. A fixed REU source address makes FETCH a fill: **8,000 bytes take about 8.1 ms plus setup and VIC contention**. SWAP takes **two cycles/byte**: exchanging backing-slot ownership can save command setup, but does not halve transfer time and complicates mapping. There is no general REU-to-REU copy command. [Programming reference](https://codebase64.c64.org/doku.php?id=base%3Areu_programming), [register controls](https://codebase64.net/doku.php?id=base%3Areu_registers)

   VERIFY could compare cached pages against backing storage, but reading its normal result requires `$DF00`; **under your literal prohibition, exclude it**.

   **Soft 80 columns.** Pre-shift left/right glyph data and combine pairs. An unrolled scanline body of indexed `LDA`, indexed `ORA`, absolute `STA` costs **12 cycles without page penalties**: **96 cycles/pair** for eight rows. Thus **7.8 ms for 160 status characters**, or **97 ms for 2,000 characters**, are calculated body-only budgets—not complete rendering estimates. Include address setup, attributes, cursor and VIC stalls. A character shadow costs 2 KB; attributes add more.

   **Formatting.** Oscar64’s [integer formatter](https://raw.githubusercontent.com/drmortalwombat/oscar64/main/include/stdio.c) uses division and remainder by a runtime base. Specializing decimal conversion permits shared quotient/remainder work, constant division or subtract-powers-of-ten conversion. A two-digit text table costs **200 bytes**. Test `%ld`, padding, negatives and exceptional strength notation; don’t disable `time` to claim a speed improvement.

   **Prior art.** The closest match is [Shawn Jefferson’s Atari Moria](https://forums.atariage.com/blogs/blog/18-atari-8-bit-moria-port/): C/cc65, banked cartridge plus expanded memory, and specifically lookup tables replacing cave-address multiplication. Some versions changed RNG handling, so borrow engineering selectively.

   [PC Larn’s original distributed documentation](https://groups.google.com/g/comp.sources.amiga/c/qUQTRIaKDGc) describes caching approximately 8 KB levels and swapping older ones. NetHack already externalizes inactive levels; that offers mechanism, not another current-level saving. [Rogue’s preserved C64/CP/M releases](https://britzl.github.io/roguearchive/) are useful comparison artifacts, but do not establish equivalent C-source portability.

   Historical [DOS build machinery](https://raw.githubusercontent.com/Vanilla-NetHack/NetHack-3.4.3/master/sys/msdos/Makefile.MSC) combines large-model compilation and overlays. Official 3.4.3 instead [requires a 386 and 3 MB extended RAM](https://www.nethack.org/v343/ports/download-msdos.html); the [Atari release requires 2 MB free](https://www.nethack.org/v343/ports/download-atari.html). Amiga/ST ports benefited from wider directly addressable memory.

4. **Doubtful or missing assumptions**

   - **RAM budget:** resident 15 KB + cache 16 KB + bitmap 8 KB + hot globals 4 KB + stack 4 KB already totals **47 KB**, before metadata and other near allocations. Establish whether your available-RAM figures already deduct display storage.
   - **Code execution:** REU storage is not execute-in-place. A 16 KB refill costs approximately **16.6 ms** before setup. Distinguish flash bank switches from REU code misses. The 39 banks exceeding EasyFlash alone occupy **624 KB**.
   - **Pointer inflation:** recalculate structures, frames, heap and working-set traces after introducing three-byte pointers. Include dirty/reference tracking, page-straddling accesses and page-byte tag conflicts.
   - **Ultimate configuration:** set CRT subtype **1** for REU-aware EasyFlash; firmware can otherwise disable conflicting REU functionality. [Official documentation](https://1541u-documentation.readthedocs.io/en/latest/howto/cartridges.html)
   - **C128 helps:** it retains banking complexity, but offers native 80-column output and 2 MHz operation. [Commodore’s guide](https://commodore.ca/manuals/128_system_guide/sect-05.htm) contradicts dismissing it entirely.
   - **Turbo is target-specific:** Ultimate 64 supports accelerated 6510 execution; a II+ attached to an ordinary C64 does not confer that CPU acceleration. Benchmark CPU, cartridge and DMA separately. [Official turbo documentation](https://1541u-documentation.readthedocs.io/en/latest/config/turbo_mode.html)
   - **Coverage:** profile division/modulo, signed comparisons, bitfields, string scans, RNG arithmetic and software-stack access next. Preserve RNG results and call order. Add deep-level, inventory-heavy, save/restore and worst-case latency measurements. Clarify the unit of “leaves 57 a turn.”
