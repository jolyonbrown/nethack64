/* OSCAR64 REPRO r71 - WRONG CODE: at -Os a copy of a few bytes is folded into a loop,
 * LDX #3 / LDA a,x / STA b,x / DEX / BPL, and the BPL's offset is worked out from the loop's
 * instructions, three bytes for an operand that is neither a zero page address nor a zero
 * page object.  The assembler writes an absolute address below 256 without a linker object
 * (a constant pointer into the zero page, the fast-call parameter registers) in its two byte
 * zero page form, so the BPL goes back one byte too far, into the operand of the LDX: here
 * "BPL $08b9" for a loop at $08ba.  The loop of one load and two stores also missed zero
 * page objects (`__zeropage` variables).  Only -Os folds copies.
 * v1.32.273 and the pin before commit 77.  NetHack: hmon_hitmon() in the C64 measurement's
 * listing of uhitm.c (a copy from the parameter registers P1-P4, "BPL $22cc" for a loop at
 * $22cd), there since the pin of 2026-11-15 at least; the whole game's listings of
 * 2026-11-15 have none (tools/check_listing.py).  Found 2026-11-16 (compat #74).
 * Expect when fixed: exit 0.  Fixed in the pin (commit 77, T1.53): each operand sized by the
 * assembler's rule.
 * Workaround: none; tools/check_listing.py finds such a branch.
 * FLAGS: -Os -e
 */
__noinline unsigned long rd(void)
{
	return *(unsigned long *)0xfb;
}

int main(void)
{
	*(unsigned long *)0xfb = 0x12345678UL;
	return rd() == 0x12345678UL ? 0 : 1;
}
