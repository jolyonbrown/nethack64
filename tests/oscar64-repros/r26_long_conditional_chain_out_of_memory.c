/* OSCAR64 REPRO r26 - COMPILER OUT OF MEMORY: a long chain of independent conditionals on one
 * arm of a conditional, before the two arms join (here: the latch of a loop)
 * NetHack: explode() in explode.c, whose 3x3 cell loop holds such a chain (140 blocks and
 * 149 million paths between the loop head and its latch).  With upstream bf42402 (PR #440,
 * carried by the patched pin for r25) the compiler's memory grows past 8 GB in 20 s on it;
 * v1.32.273 at -Os gets through explode.c only because it folds explode()'s constant
 * arguments into the body (the r25 wrong code), and runs out of memory at -O0 and -O1.
 * Found 2026-11-12, when the measurement harness was OOM-killed on explode.c.
 * Cause: three recursive walks over the predecessor graph (CollectBlocksToDominator,
 * IsDirectLoopPathBlock, CheckLoopIndexX/YRegisters) keep no visited set, so they visit each
 * block once per path, and the number of paths doubles with every conditional;
 * CollectBlocksToDominator also stores every visit.  Any optimisation level, whenever the
 * conditions are not constant (here the arguments vary, so nothing is folded).
 * Expect when fixed: compiles in about a second, emulation result 0.  Actual (v1.32.273,
 * -Os): std::bad_alloc after a few seconds under run.py's 3 GB cap; uncapped, the compiler
 * grows until the kernel's OOM killer stops it.  Fixed by commit 8 of the patched pin
 * (ADR-0007), proposed upstream as PR #15 in docs/OSCAR64-UPSTREAM.md.
 * Workaround: none applied (the patched pin carries the fix).
 * FLAGS: -e -Os
 */
int acc;

void bump(int v)
{
	acc += v;
}

void f(int x, unsigned long y, int n)
{
	int i;

	for (i = 0; i < n; i++)
	{
		if (x == 0)
			bump(100);
		else
		{
			if (y & 0x1ul) bump(1);
			if (y & 0x2ul) bump(2);
			if (y & 0x4ul) bump(3);
			if (y & 0x8ul) bump(4);
			if (y & 0x10ul) bump(5);
			if (y & 0x20ul) bump(6);
			if (y & 0x40ul) bump(7);
			if (y & 0x80ul) bump(8);
			if (y & 0x100ul) bump(9);
			if (y & 0x200ul) bump(10);
			if (y & 0x400ul) bump(11);
			if (y & 0x800ul) bump(12);
			if (y & 0x1000ul) bump(13);
			if (y & 0x2000ul) bump(14);
			if (y & 0x4000ul) bump(15);
			if (y & 0x8000ul) bump(16);
			if (y & 0x10000ul) bump(17);
			if (y & 0x20000ul) bump(18);
			if (y & 0x40000ul) bump(19);
			if (y & 0x80000ul) bump(20);
			if (y & 0x100000ul) bump(21);
			if (y & 0x200000ul) bump(22);
			if (y & 0x400000ul) bump(23);
			if (y & 0x800000ul) bump(24);
			if (y & 0x1000000ul) bump(25);
			if (y & 0x2000000ul) bump(26);
			if (y & 0x4000000ul) bump(27);
			if (y & 0x8000000ul) bump(28);
		}
	}
}

int main(void)
{
	unsigned long m = 0xfffffffful;
	int i;

	for (i = 0; i < 2; i++)
	{
		f(i, m, 2 - i);
		m = 0x0f0f0f0ful;
	}
	/* 2 x 100, then bits 0-3, 8-11, 16-19 and 24-27 */
	return acc != 200 + (1+2+3+4) + (9+10+11+12) + (17+18+19+20) + (25+26+27+28);
}
