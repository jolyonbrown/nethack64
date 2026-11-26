/* OSCAR64 REPRO r86 - THE VALUE OF ++ OR -- ON A BITFIELD IS READ AS THE WHOLE STORAGE UNIT.
 * `if (--p->q)` with q an `unsigned q : 6` reached through a pointer: the decrement is
 * stored right, but the expression's value is read back without the bitfield's shift and
 * width (InterCodeGenerator's EX_PREINCDEC returned its reference with bits 0, shift 0), so
 * the test sees the word holding q and its neighbours. C89 3.3.3.1: the result is the new
 * value of the operand. Here count() should return 3 and loops to its guard, 100. The pin
 * (87 commits) and the far fork to aba11e5, 2026-11-22.
 * NetHack: u_init.c's ini_inv(), "if (--trop->trquan) continue;": the starting inventory's
 * loop never ended (the C128 game: "Object space full" before the first turn); and any
 * other ++/-- of a Bitfield whose value is used.
 * Expect when fixed: "Emulation result 0".
 * Workaround: decrement, then test the field in its own statement. Fixed by the pin's commit 88
 * (2026-11-26, from the far fork's commit 17; the fork keeps the far object part).
 * FLAGS: -e -n
 */
struct t { short a; char b; char c; unsigned q : 6; unsigned r : 2; };
struct t tab[2] = { { 1, 0, 'x', 3, 1 }, { 0, 0, 0, 0, 0 } };

__noinline int count(struct t * p)
{
	int n = 0;
	while (p->c && n < 100)
	{
		n++;
		if (--p->q)
			continue;
		p++;
	}
	return n;
}

int main(void)
{
	return count(tab) == 3 && tab[0].r == 1 ? 0 : 1;
}
