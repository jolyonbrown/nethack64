/* OSCAR64 REPRO r62 - COMPILER HANG: a call graph with many paths around a cycle.  Each
 * rung's two functions call both functions of the next rung, and the last rung calls
 * back to the first: one cycle through all 48 functions, and 2^24 simple paths around it.
 * GlobalAnalyzer's MarkRecursions and CheckFastcall walk every one: their on-path flag
 * is cleared on the way back, and CheckFastcall remembers a result only for a function
 * that takes fastcall parameters, which a function on a cycle never does.  The time
 * doubles with each rung: 18 rungs take 5 to 13 s on v1.32.273, the pin and upstream main
 * (16acc53), checked 2026-11-15; these 24 more than the repro runner's 120 s.
 * NetHack: the whole game in one compile (the banked build, docs/BANKING-SPIKE.md) did not
 * finish in an hour: its direct calls form one cycle of 279 functions (through panic()
 * and done()), and the graph CheckFastcall walks, which adds calls through pointers, one
 * of 2,694.  A single file's measurement compile has only small cycles.  Found 2026-11-15.
 * Expect when fixed: compiles in about a second, emulation result 0.
 * Workaround: none; fixed by the ADR-0007 compiler (commits 63-65, 2026-11-15):
 * MarkRecursions by Tarjan's search, and CheckFastcall walking each function once and
 * keeping, per strongly connected component, what the repeated walks found.
 * The calls take their argument through a volatile, or the compiler evaluates them at
 * compile time and the functions never reach the call graph.
 * FLAGS: -e -Os
 */
#define RUNG(k, n) \
int a##n(int d); int b##n(int d); \
int a##k(int d) { int x = d + k; if (d <= 0) return k; \
	return ((d & 1) ? a##n(d - 1) : b##n(d - 1)) + (x - d - k); } \
int b##k(int d) { int x = d * 2 + k; if (d <= 0) return k + 100; \
	return ((d & 2) ? a##n(d - 1) : b##n(d - 1)) + (x - d * 2 - k); }

RUNG(0, 1) RUNG(1, 2) RUNG(2, 3) RUNG(3, 4) RUNG(4, 5) RUNG(5, 6) RUNG(6, 7) RUNG(7, 8)
RUNG(8, 9) RUNG(9, 10) RUNG(10, 11) RUNG(11, 12) RUNG(12, 13) RUNG(13, 14) RUNG(14, 15)
RUNG(15, 16) RUNG(16, 17) RUNG(17, 18) RUNG(18, 19) RUNG(19, 20) RUNG(20, 21) RUNG(21, 22)
RUNG(22, 23) RUNG(23, 0)

volatile int depth;

int main(void)
{
	/* 25 and 50 go round the cycle; each function checks its local survived */
	depth = 5;
	if (a0(depth) != 105 || b0(depth) != 105)
		return 1;
	depth = 25;
	if (a0(depth) != 101 || b0(depth) != 101)
		return 2;
	depth = 50;
	if (a0(depth) != 102 || b0(depth) != 102)
		return 3;
	return 0;
}
