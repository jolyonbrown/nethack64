/* OSCAR64 REPRO r66 - WRONG CODE, no diagnostic: an __asm block whose first line is a
 * comment (either kind) loses the first digit of the first instruction's immediate
 * operand: `lda #11` assembles as LDA #$01, `ldx #11` as LDX #$01, `#123` as 23, `#200`
 * as 0.  A blank first line, a comment later in the block or after the operand are fine;
 * so is an address operand.  The scanner takes a `#` at the start of a line in assembler
 * mode for a preprocessor directive (Scanner.cpp), and a leading comment leaves it
 * thinking it is there.  v1.32.273 and the pin, -O0 and -Os.
 * NetHack: none (no inline assembler); found 2026-11-15 in our own src/hal/rng.c, whose
 * lrand48() added 1 instead of 11, so the second number after a seed was wrong.
 * Oscar64's own library starts some blocks with a comment, none with an immediate next.
 * Expect when fixed: v == 11.
 * Workaround: do not open an __asm block with a comment; put it above the block.
 * FLAGS: -e
 */
unsigned char v;

__noinline void f(void)
{
	__asm
	{
		/* a comment first */
		lda #11
		sta v
	}
}

int main(void)
{
	f();
	return v == 11 ? 0 : 1;
}
