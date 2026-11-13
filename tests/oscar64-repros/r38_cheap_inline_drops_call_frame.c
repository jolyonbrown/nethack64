/* OSCAR64 REPRO r38 - WRONG CODE, AT RANDOM: a caller that gets a one-call wrapper copied in
 * loses the stack frame for that call's arguments, depending on old contents of the
 * compiler's own heap
 * NetHack: port/src/teleport.c u_teleport_mon, which gets enexto() (one call, to
 * enexto_core) copied in: harness compiles with no heap fill (2026-11-12, again 11-13)
 * have POPF 8 with no PUSHF 8, so the stack pointer rises by 10 bytes per call.  Any
 * caller of such a wrapper is exposed; same source, different code per run.
 * Cause: InterInstruction's constructor does not set mRemove.  CheapInlining
 * (InterCode.cpp) puts a new IC_PUSH_FRAME and a new IC_POP_FRAME round the copied call,
 * then deletes every instruction of the block that has mRemove set, having cleared the flag
 * only on the instructions that were there before.  Each of the two survives or not
 * according to what its heap block held.  Both lost: no frame, the arguments go over the
 * callers' saved registers and locals (here).  Push lost, pop kept: the stack pointer rises
 * by the frame size on each call (teleport.c).
 * A fresh heap is zero, so a compile this small is right unless the heap is filled: ENV
 * below makes glibc fill each allocation with 0xaa.  v1.32.273 and the eight-commit patched
 * pin (ADR-0007): default level, -Os, -O2; not -O0, not -O3 (the front end inlines first),
 * not bytecode.
 * Fixed upstream by fbca293 (2026-10-18), one line; main 4da3147 passes.  Backported as
 * scratch/heap-init-pin 03a460a, a candidate for the patched pin (TASKS T1.21).
 * Expect when fixed: emulation result 0, with and without ENV.  Actual: result 2 with ENV
 * (main's copy of the stack pointer, saved by caller(), is overwritten); 0 without.
 * Workaround: none in source that is practical; the fix is the pin commit.
 * FLAGS: -e -Os
 * ENV: MALLOC_PERTURB_=85
 */
char depth;

__noinline void set(char d)
{
	depth = d;
}

/* deep() recurses, so its arguments go on the stack and not in zero page */
int deep(char n, int a, int b, int c)
{
	if (n > 0)
		return deep(n - 1, a, b, c) + 1;
	return a + b + c;
}

/* One call and one return, and too costly for the front end to inline at -Os: the
 * "cheap inlining" pass copies it into each caller.  It may only read its parameters. */
int wrap(char n, int a)
{
	return deep(n, a + a, 5, 0) + a;
}

__noinline void fill(char * p)
{
	p[0] = 11; p[1] = 22; p[2] = 33; p[3] = 44; p[4] = 55; p[5] = 66; p[6] = 77; p[7] = 88;
}

__noinline char sum(const char * p)
{
	return p[0] ^ p[1] ^ p[2] ^ p[3] ^ p[4] ^ p[5] ^ p[6] ^ p[7];
}

/* no stack arguments of its own: the only frame it needs is the one for the copied call */
__noinline int caller(int x)
{
	char	buf[8];
	int		r;

	fill(buf);
	r = wrap(depth, x);
	if (sum(buf) != (11 ^ 22 ^ 33 ^ 44 ^ 55 ^ 66 ^ 77 ^ 88))
		return -1;
	return r;
}

/* more callers, so that the front end does not inline wrap() itself */
__noinline int other(int x)
{
	return wrap(depth, x + 1) + wrap(depth, 1) + wrap(1, x);
}

int main(void)
{
	unsigned	sp0, sp1;
	int			r, q = 0;

	set(2);
	sp0 = *(unsigned *)0x23;	/* Oscar64's software stack pointer */
	r = caller(3);
	sp1 = *(unsigned *)0x23;
	if (r != 3 * 3 + 5 + 2) q |= 1;
	if (sp0 != sp1) q |= 2;
	if (other(4) != (15 + 5 + 2) + (3 + 5 + 2) + (12 + 5 + 1)) q |= 4;
	return q;
}
