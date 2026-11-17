/* OSCAR64 REPRO r73 - WRONG CODE: a `volatile` global with an initialiser that no C code
 * writes is read as its initial value.  Here `w` is set by assembler (as it could be by
 * DMA or by hardware), but `w == 64` compiles to a constant false, with no load; `z`, the
 * same without an initialiser, is loaded.  The C standard requires every read of a
 * volatile object to access it.  -O2 and -Os; -O0 and -O1 load it.  v1.32.273 and the pin
 * (80 commits).
 * NetHack: none in the game's code; hit 2026-11-17 by the REU bank call spike
 * (tests/spikes/bankreu.c, ADR-0008), whose bank call routine keeps the REU bank the
 * window holds in `nh_window = 0xff` (compat #76).
 * Expect when fixed: exit 0.
 * Workaround: no initialiser; set the variable at start-up.
 * FLAGS: -Os -e
 */
volatile unsigned char w = 0xff;
volatile unsigned char z;

__asm setw
{
		lda #64
		sta w
		sta z
		rts
}

int main(void)
{
	__asm { jsr setw }
	return (w == 64 ? 0 : 1) + (z == 64 ? 0 : 2);
}
