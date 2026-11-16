/* OSCAR64 REPRO r70 - WRONG CODE: at -Os, a run of 4-byte copies from absolute addresses into
 * zero page (here 26 longs read from a volatile array into locals) is folded into one loop
 * over the four bytes, LDX #3 / LDA abs,x / STA zp,x ... / DEX / BPL, five bytes a copy.
 * With 26 copies the BPL has to go back 133 bytes, beyond a branch's reach (128), and its
 * offset is written truncated: $7B, 123 bytes forward, into the middle of other code.  With
 * 25 copies (128 back) it works.  The listing prints the wrong target ("BPL $09c5 ; (main.s14
 * + 1)"), and tools/check_listing.py finds such a branch: its target is not an instruction.
 * v1.32.273 and the pin.  NetHack: none (no branch in the whole game's listing of
 * 2026-11-15, 96,428 of them, lands outside an instruction); found 2026-11-16 making r69.
 * Expect when fixed: exit 0 (a JMP back, or no fold of more than 25).
 * Workaround: none needed; tools/check_listing.py would show one.
 * -xz turns the emulator's jiffy clock off (and lowers the temporaries), so that only this
 * bug can change the result, not r69's.
 * FLAGS: -Os -xz -e
 */
volatile unsigned long src[26];
volatile unsigned char sink;

#define V(i)	unsigned long v##i = src[i]
#define BAD(i)	(v##i != (i) * 0x01010101UL)

int main(void)
{
	unsigned i;

	for (i = 0; i < 26; i++)
		src[i] = i * 0x01010101UL;
	{
		V(0); V(1); V(2); V(3); V(4); V(5); V(6); V(7); V(8); V(9); V(10); V(11); V(12);
		V(13); V(14); V(15); V(16); V(17); V(18); V(19); V(20); V(21); V(22); V(23); V(24);
		V(25);

		for (i = 0; i < 10000; i++)
			sink++;
		if (BAD(0) || BAD(1) || BAD(2) || BAD(3) || BAD(4) || BAD(5) || BAD(6) || BAD(7) ||
		    BAD(8) || BAD(9) || BAD(10) || BAD(11) || BAD(12) || BAD(13) || BAD(14) ||
		    BAD(15) || BAD(16) || BAD(17) || BAD(18) || BAD(19) || BAD(20) || BAD(21) ||
		    BAD(22) || BAD(23) || BAD(24) || BAD(25))
			return 1;
	}
	return 0;
}
