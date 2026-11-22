/* OSCAR64 REPRO r83 - AN INITIALISED VOLATILE GLOBAL THAT NO C CODE WRITES IS FOLDED.
 * `volatile unsigned char x = 5;`, written only by assembler, read in C: the read becomes
 * the constant 5, so the C code never sees the 7 the assembler stored (main below compiles
 * to "return 1"). C89 3.5.3: every access to a volatile object is performed as the abstract
 * machine says, so the load must stay. The same global without an initialiser (bss) is
 * read from memory and is right, so is one that C code writes too. -O2, -Os and -O3 (our
 * builds use -Os); right at -O0 and -O1. Seen on the pin (87 commits) and the far fork
 * (887e4bd), 2026-11-22; upstream main not built.
 * NetHack: none known. The two initialised volatiles in port/ (mail.c's VMS-only
 * `broadcasts`, wintty.c's `nesting`) are written in C. Ours that only assembler writes
 * (nhbank.h's `nh_bank`, the far runtime's `nh_faults`, `nh_writebacks`, `nh_rpage`) have
 * no initialiser.
 * Found 2026-11-22, writing a test for initializer literals that had to defeat folding.
 * Expect when fixed: "Emulation result 0".
 * Workaround: no initialiser on a volatile that only assembler writes (set it at run time
 * if it needs a first value).
 * FLAGS: -e -Os
 */
volatile unsigned char x = 5;

__asm setx
{
		lda #7
		sta x
		rts
}

#pragma noinline(callset)
void callset(void)
{
	__asm { jsr setx }
}

int main(void)
{
	callset();
	return x == 7 ? 0 : 1;
}
