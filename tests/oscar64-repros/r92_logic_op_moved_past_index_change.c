/* OSCAR64 REPRO r92 - A LOGIC OP MOVED ABOVE THE CHANGE OF ITS INDEX REGISTER.
 * NativeCodeBasicBlock::JoinTAXARange(): for "TAX ... TXA; ORA/AND/EOR m" with A dead after
 * the TAX, the logic op moves up to before the TAX, so the TXA has nothing to restore. The
 * check that nothing in between changes the operand (MayBeChangedOnAddress()) looks at
 * memory only, not at an index register: here "TAX; LDA a; AND #$0F; TAY; TXA; ORA tab,y"
 * became "ORA tab,y; TAX; ...", and the table was read with Y never loaded. Every level,
 * -O0 too (the native code optimiser runs at all of them): the pin (v1.32.273 + 87), the
 * far fork to 3b822da and upstream 16acc53 (2026-11-14), 2026-11-24. "a & 0x80 ? 0x40 : 0"
 * puts the 0 or 0x40 in A first, which the TAX ... TXA keeps while Y is computed.
 * NetHack: src/hal/vdc80.c's s80_putca(), rgbi[attr & 15] | (attr & S80_REVERSE ?
 * ATTR_REVERSE : 0): every character the C128's game wrote got the colour rgbi[Y], Y
 * whatever the caller left (0 from xputc(): black), so the 80-column screen was black on
 * black (found 2026-11-24 drawing a screenshot of fc46; reading the screen RAM as text
 * never showed it).
 * Expect when fixed: "Emulation result 0".
 * Workaround: the value first, the bit after ("char a = tab[x & 15]; if (x & 0x80) a |= 0x40;"),
 * as vdc80.c does. Fixed by the pin's commit 98 (2026-11-26, from the far fork: the op does not
 * move past a change of its index register, or at all when it is indexed by X).
 * FLAGS: -e -Os -n
 */
static const char tab[16] = { 0, 15, 8, 7, 10, 4, 2, 13, 12, 12, 9, 1, 14, 5, 3, 14 };
char out;

__noinline void put(char v) { out = v; }

__noinline void f(char a)
{
	put(tab[a & 15] | (a & 0x80 ? 0x40 : 0));
}

int main(void)
{
	f(1);
	if (out != 15)
		return 1;
	f(0x82);
	return out == 0x48 ? 0 : 2;
}
