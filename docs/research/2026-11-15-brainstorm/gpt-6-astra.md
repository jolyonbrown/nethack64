**Recommendation:** pursue a hybrid near/far design, fix arithmetic first, and qualify Ultimate turbo as an optional acceleration path. Reconsider the C128 seriously.

**Evidence labels:** **M** = measurements supplied in the brief, not independently reproduced; **S** = linked documentation/source; **I** = my inference or proposed experiment. All projected gains below are **I**.

**1. Long list**

1. **Constant-stride lowering:** teach Oscar64 to replace `126*x` with shifts/subtractions or lookup tables. Small compiler change; test generated code and every legal coordinate.
2. **Column-address table:** spend 160 near bytes on 80 column pointers, avoiding the measured 250-cycle multiply. Low-risk macro experiment before compiler work.
3. **Square lookup:** replace bounded coordinate squaring with exact tables; potentially recover much of the estimated 0.2 s/turn. Audit argument ranges; exhaustively compare results.
4. **Selective speed optimisation:** compile hot functions differently from cold code. Costs cartridge space; compare kernel cycles and total bank count.
5. **Near terrain, far bulk:** prioritise frequently consulted map fields and globals over cold tables. Costs placement work; replay traces under alternative allocations.
6. **Record pinning:** translate once, use several fields, then release. **M:** 1.7× versus 3× in the table benchmark; test nested calls and eviction.
7. **Typed 16-bit handles:** encode monster/object arena offsets instead of widening every stored pointer. Saves pointer space; substantial aliasing work; prototype one list.
8. **Split `objects[]`:** retain mutable fields near, bank immutable fields. Unknown saving until field census; mechanically generate accessors and compare host games.
9. **Page colouring:** separate hot allocations sharing the same translation-table index. Low implementation cost; trace conflict misses separately from capacity misses.
10. **Phase overlays:** swap display/menu scratch with computation scratch at explicit boundaries. Saves RAM; callback risks; begin with a modal inventory screen.
11. **Frame lifetime allocation:** overlap buffers only where the call graph proves disjoint lifetimes. Preserve sizes; audit address escapes and indirect calls first.
12. **8 KB cartridge mode:** reclaim one 8 KB CPU window while retaining ROM execution. Requires repartitioning; benchmark one movement cluster.
13. **REU code overlays:** load cold functions into a small RAM execution area. Saves flash capacity; DMA latency and return restoration risks; replay bank traces.
14. **Native C128 backend:** common RAM, banked arenas, VDC text and 2 MHz. Larger platform effort; prototype the two hot kernels first.
15. **Ultimate turbo:** accelerate unchanged native code. Firmware/timing qualification required; run identical checksum workloads at several speeds.
16. **Incremental status formatting:** preserve displayed information while formatting only changed fields. Targets 21% of host instructions; compare exact output sequences.
17. **Zero-page allocation:** prioritise frequently used addresses and counters, with compiler-visible effects. Scarce resource; measure spills before assigning more.
18. **Alternative memory hardware:** GeoRAM or custom banked SRAM could avoid DMA faults. Address conflicts and platform dependence are substantial; prototype the mapping before porting code.

These preserve gameplay when implemented correctly. Layout changes, handles and buffer lifetime changes still need save/restore regression coverage.

**2. Top five**

**A. Remove general multiplication from spatial access.**  
Put constant multiplication strength reduction in Oscar64; put domain-specific square tables behind a portable helper. An 80-entry, 16-bit square table needs 160 bytes and covers valid map-coordinate differences, but sentinel and non-coordinate callers require auditing or a general fallback. Published [6502 multiplication techniques](https://www.lysator.liu.se/~nisse/misc/6502-mul.html) support the general table approach.

If address generation falls from 250 to 50 cycles, the measured multiply shares imply approximately **28% fewer cycles in `mfndpos`** and **42% fewer in `is_pool`/`is_lava`**, not whole-game reductions. Squaring has roughly 0.16 s/turn of multiplication cost available to attack. Cheapest experiment: two standalone replacements, exhaustive coordinate checks, then identical movement traces. No RNG or game changes.

**B. Make far data selective and translations reusable.**  
Keep frequently used globals and selected terrain data near; put immutable tables, strings and colder mutable state behind compiler-supported far accesses. Support short-lived pinned mappings, including multi-page records, rather than returning unprotected cache pointers.

**M:** 10,000 translations at 21 cycles already cost approximately **0.21 s/turn**. Halving translations saves about 0.11 s even without reducing faults. Compiler work is substantial: aliasing, nested calls, writeback and page crossings must be explicit. Cheapest experiment: trace-driven placement plus one compiled monster-record access path; retain ordinary pointers/macros in gcc builds.

**C. Reopen the C128 option.**  
Its MMU offers common RAM and relocatable zero/stack pages; the VDC has separate display memory. Native 80-column output permits sustained 2 MHz computation with the VIC display disabled. These are documented facilities, not simultaneous flat access to 128 KB. See the [Commodore reference guide](https://www.pagetable.com/docs/Commodore%20128%20Programmer%27s%20Reference%20Guide.pdf).

A common resident core accessing banked data arenas avoids copying data merely to switch banks. The ideal CPU-bound improvement approaches 2×, while replacing the C64 bitmap releases roughly 8 KB of main RAM. Costs: a native C128 runtime/window backend, banking discipline and cartridge bootstrap changes. Cheapest experiment: `mfndpos` with terrain in the other bank, common code, VDC output and CIA timing.

**D. Exploit Ultimate acceleration without making it mandatory.**  
Ultimate documentation specifies up to **48 MHz on U64**, **64 MHz on U64 Elite-II/C64U-class hardware**; external-bus accesses remain at 1 MHz. Internal memory placement therefore matters. The 1541 Ultimate II+ cartridge does **not** accelerate an original C64’s CPU. [Turbo documentation](https://1541u-documentation.readthedocs.io/en/latest/config/turbo_mode.html).

At an effective 8× CPU speed, the brief’s 1.8 s CPU estimate becomes approximately **225 ms**, before DMA and I/O. This is a target, not a measured result. Cheapest experiment: the existing far-access benchmark with internal EasyFlash emulation, REU enabled, and checksums at 1×/4×/8×. Keep timing-sensitive I/O under explicit control.

**E. Compare ROM windows against REU execution overlays quantitatively.**  
EasyFlash supports 8 KB and 16 KB modes. The former releases 8 KB of address space, but exposes only ROML during normal execution. [Programmer’s guide](https://skoe.de/easyflash/files/devdocs/EasyFlash-ProgRef.pdf).

Alternatively, small REU-loaded code overlays let the cartridge disappear during computation. A 4 KB transfer costs roughly **4.2 ms** at PAL speed; a 16 KB transfer roughly **16.6 ms**, excluding setup/contention. Eighty 16 KB loads would add about **1.33 s**. Thus retain hot code and overlay cold phases; do not blindly replace bank switches with DMA. Cheapest experiment: simulate overlay residency from actual call/return traces before changing the linker.

**3. Hardware, memory architecture and prior art**

| Platform | Documented offer and practical consequence |
|---|---|
| **EasyFlash** | 1 MiB, 64 paired banks, selectable 8K/16K/Ultimax/invisible modes. ROML and ROMH share the bank selection. Useful execution storage; no extra writable game memory under your rules. [Guide](https://skoe.de/easyflash/files/devdocs/EasyFlash-ProgRef.pdf) |
| **EasyFlash 3** | Seven selectable 1 MiB EasyFlash slots, KERNAL replacement and USB. This is not automatically a contiguous 7 MiB EasyFlash address space. Slot switching needs a separately validated EF3-specific backend. [Designer’s documentation](https://www.skoe.de/easyflash/ef3intro/) |
| **REU** | Stash copies C64→REU; fetch reverses it; swap exchanges bytes; compare checks equality. CPU execution stops during DMA. Copy/compare approach one byte/cycle; swap takes roughly twice as long. Larger implementations extend capacity, not CPU addressing. [Hardware implementer’s manual, §§8.5.1–3](https://www.syntiac.com/pdf/chameleon_progmanual_beta9.pdf) |
| **Ultimate family** | EasyFlash/REU coexistence has an explicit CRT convention: type 32, subtype **1**, header offset `$1A`, denotes REU-aware EasyFlash. Set it and test each firmware. [Cartridge documentation](https://1541u-documentation.readthedocs.io/en/latest/howto/cartridges.html) |
| **GeoRAM** | A directly accessible 256-byte window at `$DE00–$DEFF`, selected through `$DFFE/$DFFF`; no DMA. This collides with EasyFlash’s control area. Attractive for a different memory backend, unsuitable as a transparent addition. [Manufacturer’s design](https://gglabs.us/node/2034) |
| **Kung Fu Flash** | Distinguish the original from KFF2. The published KFF2 implementation supports EasyFlash and a 1 MiB REU, but disables REU while emulating CRTs. It therefore does not establish your required combination; later firmware needs verification. [Implementation README](https://github.com/Sgw32/KungFuFlash2-USBC/) |

**REU refinements.** Use software dirty bits and stash dirty victims before fetching replacements. Swap is useful for exchanging fixed arenas, but an ordinary cache eviction has *different* old-page and incoming-page backing addresses: one swap does not implement it automatically. Compare is a poor dirty-detection strategy here because reading its result at `$DF00` violates the explicit no-read rule. Use write-only DMA setup, software register shadows and IRQ-disabled transfers.

More REU capacity can hold code, serialized levels and large arenas; it does **not** enlarge the CPU-side cache. Test wraparound boundaries on each implementation. Ultimate firmware 3.15 specifically fixes stale-data hazards when REU transfers start under turbo, demonstrating why joint qualification matters. [Release notes](https://1541u-documentation.readthedocs.io/en/latest/howto/release_3.15.html). C64 Ultimate has its own firmware/version stream; do not assume fixes transfer automatically. [Commodore changelog](https://downloads.commodore-international.com/documentation/changelog-1.1.0.txt).

**Beyond per-access far pointers.** The most promising alternatives are banked typed arenas, compiler-managed region mappings, and phase-specific overlays. Keep stable identities separate from temporary CPU addresses. Retain NetHack’s serializer for inactive levels: `goto_level()` already saves and frees the departing level. Thus “one level resident” is existing architecture, not a new solution to the current-level shortfall. [3.4.3 source](https://raw.githubusercontent.com/Vanilla-NetHack/NetHack-3.4.3/master/src/do.c).

**Prior art gives useful boundaries:**

- **DOS NetHack:** Borland uses huge model plus VROOMM code overlays; its makefile budgets **526–607 KB**, including 115 KB heap and 30 KB overlay buffer. Microsoft uses `/AL`. This supports combining far data with overlays, but not expecting comparable results inside 64 KB. [Borland](https://raw.githubusercontent.com/Vanilla-NetHack/NetHack-3.4.3/master/sys/msdos/Makefile.BC), [Microsoft](https://raw.githubusercontent.com/Vanilla-NetHack/NetHack-3.4.3/master/sys/msdos/Makefile.MSC).
- **Amiga/ST:** 3.4-era Amiga instructions require at least **3 MB**; official ST 3.4.3 requires **2 MB free**. Their broad directly addressed memory makes them portability precedents, not demonstrations of C64-scale memory management. [Amiga](https://github.com/Vanilla-NetHack/NetHack-3.4.3/blob/master/sys/amiga/Install.ami), [Atari](https://www.nethack.org/v343/ports/download-atari.html).
- **Atari 8-bit Moria:** Shawn Jefferson used cc65, banked cartridge code, VBXE memory and lookup tables eliminating cave-index multiplication. This is the closest practical precedent. His reported generation speed also involved an RNG replacement, which your rules would prohibit without a decision. [Author’s development log](https://forums.atariage.com/blogs/blog/18-atari-8-bit-moria-port/).
- **Larn:** PC Larn’s documented `ramlevels` option retains 1–14 levels, approximately 8 KB each, swapping older levels to disk. This directly supports coarse lifetime-based storage. [Original distribution](https://groups.google.com/g/comp.sources.amiga/c/qUQTRIaKDGc).
- **Small-machine claims need qualification:** contemporary C64 **Moria8** is assembly, not compilation of the original C. Historical CP/M Rogue availability alone proves neither NetHack fidelity nor its memory architecture. [Moria8 source](https://github.com/dcgibbons/moria8), [contemporary TPUG catalogue](https://www.tpug.ca/tpug-media/catalogs/CPM%20Catalog.pdf).

**4. Doubtful or missing points**

- **Capacity:** 103 full 16 KiB banks total **1,648 KiB**. EasyFlash plus 512 KiB REU provides **1,536 KiB**—112 KiB short before data. Distinguish occupied bytes from allocated banks.
- **Execution:** REU memory cannot execute in place. The 142-cycle switch figure needs a separate cost for REU-backed code loads and caller restoration.
- **Cache feasibility:** a 128-page cache consumes 32 KiB, leaving only 12 KiB of the stated 44 KiB for everything else—less than the proposed resident code alone.
- **Pointer growth:** recount grids, heap nodes, static frames and alignment after widening pointers. The existing footprint is not necessarily the far-build footprint.
- **Unmeasured tails:** dirty faults, cross-page fields, allocation, level generation, crowded late-game levels and bitmap output need measurements. After fixing arithmetic, remeasure: far-access overhead becomes proportionally larger.
- **Compiler priorities:** inspect promotions, signed comparisons, division/modulo, repeated bitfield extraction and missed common address calculations. Undocumented opcodes are secondary to removing entire runtime calls.
