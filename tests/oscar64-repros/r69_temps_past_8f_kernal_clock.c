/* OSCAR64 REPRO r69 - WRONG CODE, silently: when a function needs more zero-page temporaries
 * than the callee-saved area holds ($53-$8F, oscar64.md "Zero page usage"), the rest go on
 * past $8F, into the KERNAL's zero page, with no diagnostic (oscar64.md: "No check for
 * running out of temporary registers").  There the KERNAL's IRQ changes them: the jiffy
 * clock at $A0-$A2 every 1/60 s (Oscar64's emulator ticks it too, every 16,667 cycles),
 * STKEY $91, the keyboard and cursor bytes.  Here 25 longs are live across a loop of about
 * 110,000 cycles; the 25th gets $9F-$A2 and the clock ticks its top three bytes.  24 longs
 * (up to $9E) pass, and so does this program with the emulator's clock off (the same bytes,
 * from a scratch build with Emulator::mJiffies false, or -xz).
 * v1.32.273 and the pin.  NetHack: not in the game yet (the whole game's highest temporary,
 * 2026-11-15, is m_move's $8D: two bytes to spare); the speed harness's main(), which
 * inlines its workloads, reached $A2-$AD (compat #72, found 2026-11-16 in its far build).
 * Expect when fixed: exit 0 (temporaries kept to $53-$8F, the rest spilled to memory), or
 * a diagnostic that says the function needs more.  The pin (commit 74, T1.50) warns:
 * "warning 2025: Zero page temporaries up to $a2, past the end of their area at $8f, in
 * 'main'" (#pragma warning(error: 2025) makes it an error); run.py counts that as fixed.
 * Workaround: functions that need less (__noinline on a big single-call function), and
 * tools/check_listing.py on every listing (no temporary past $8F).
 * FLAGS: -Os -e
 * DIAGNOSTIC: 2025
 */
volatile unsigned long src[25];
volatile unsigned char sink;

/* an add, so that r70's copy loop cannot fold the loads */
#define V(i)	unsigned long v##i = src[i] + (i + 1)
#define BAD(i)	(v##i != (i) * 0x01010101UL + (i + 1))

int main(void)
{
	unsigned i;

	for (i = 0; i < 25; i++)
		src[i] = i * 0x01010101UL;
	{
		V(0); V(1); V(2); V(3); V(4); V(5); V(6); V(7); V(8); V(9); V(10); V(11); V(12);
		V(13); V(14); V(15); V(16); V(17); V(18); V(19); V(20); V(21); V(22); V(23); V(24);

		for (i = 0; i < 10000; i++)
			sink++;
		if (BAD(0) || BAD(1) || BAD(2) || BAD(3) || BAD(4) || BAD(5) || BAD(6) || BAD(7) ||
		    BAD(8) || BAD(9) || BAD(10) || BAD(11) || BAD(12) || BAD(13) || BAD(14) ||
		    BAD(15) || BAD(16) || BAD(17) || BAD(18) || BAD(19) || BAD(20) || BAD(21) ||
		    BAD(22) || BAD(23) || BAD(24))
			return 1;
	}
	return 0;
}
