/* bankstub.c - calls between EasyFlash banks through linker stubs (docs/BANKING-SPIKE.md).
 *
 * Needs an Oscar64 with Linker::InsertBankCalls (the pin from commit 72, ADR-0007):
 * because this program names a bank call routine (#pragma runtime(bankcall, ...)), the
 * linker sends every call into a bank from outside it, and every use of a banked
 * function's address, through a 6-byte stub, `jsr nh_bankcall; .byte bank;
 * .word function`: resident, or for a call from another bank in that bank (the far-spaces
 * fork from 2026-11-19; run_bankstub.py checks where each one is).  The functions below call each other by name, with no trampolines.
 *
 * Each check is a bit of spike_result[0], set when it passes; spike_result[1] holds the
 * checks that ran.  After every call that comes back from another bank, the caller reads
 * a volatile tag in its own bank, so a bank left mapped by mistake fails the check.
 * spike_result[2..3]: cycles for N calls of an int (int, int) function in another bank
 * and in the same bank, with interrupts off (CIA 2 timer A); tests/spikes/run_bankstub.py
 * reads them through VICE's monitor.
 */
#include <c64/cia.h>
#include <c64/easyflash.h>
#include <c64/memmap.h>

#define N 64

#pragma region( main, 0x0900, 0x8000, , , { code, data, bss, heap, stack } )

#pragma section( bcode1, 0 )
#pragma section( bdata1, 0 )
#pragma region( bank1, 0x8000, 0xc000, , 1, { bcode1, bdata1 } )
#pragma section( bcode2, 0 )
#pragma section( bdata2, 0 )
#pragma region( bank2, 0x8000, 0xc000, , 2, { bcode2, bdata2 } )

volatile unsigned spike_result[4];
volatile char spike_done;
volatile int sink;

/* the cartridge's bank register is write-only, so the bank selected is kept here */
unsigned char nh_bank;
unsigned char nh_bc_a, nh_bc_x, nh_bc_y;

/* Entered from a stub with the stub's last byte on the stack: reads the function and the
 * bank from the stub (which may be in the caller's bank), then maps the bank and jumps to the function with A, X and Y as
 * the caller left them; the function returns to bret, which maps the caller's bank
 * again and returns to the caller with A, X and Y as the function left them.  The old
 * bank and bret's address wait on the hardware stack.  No zero page is touched.
 * Not re-entrant: an interrupt handler must not call banked code. */
__asm nh_bankcall
{
		sta nh_bc_a
		stx nh_bc_x
		sty nh_bc_y
		pla
		sta l1 + 1
		sta l2 + 1
		sta l3 + 1
		pla
		sta l1 + 2
		sta l2 + 2
		sta l3 + 2
		lda nh_bank
		pha
		lda #>bret
		pha
		lda #<bret
		pha
		ldy #2
l2:		lda $ffff, y
		sta bjmp + 1
		iny
l3:		lda $ffff, y
		sta bjmp + 2
		ldy #1
l1:		lda $ffff, y
		sta nh_bank
		sta $de00
		lda nh_bc_a
		ldx nh_bc_x
		ldy nh_bc_y
bjmp:	jmp $ffff
bret:	nop
		sta nh_bc_a
		pla
		sta nh_bank
		sta $de00
		lda nh_bc_a
		rts
}

#pragma runtime(bankcall, nh_bankcall)

unsigned passed, ran;

__noinline void check(unsigned bit, char ok)
{
	ran |= bit;
	if (ok)
		passed |= bit;
}

/* CIA 2 timer A counting system clock cycles (the KERNAL does not use it) */
__noinline void timer_start(void)
{
	cia2.cra = 0;
	cia2.ta = 0xffff;
	cia2.cra = 0x11;
}

__noinline unsigned timer_stop(void)
{
	cia2.cra = 0;
	return 0xffff - cia2.ta;
}

/* resident */
int r_mix(int a, int b, int c);
int r_mul(int a, int b);
int r_apply(int (*f)(int, int), int a, int b);
int r_call_back(int (*f)(int), int x);

/* bank 1 */
int b1_add(int a, int b);
int b1_fib(int n);
int b1_neg(int x);
int b1_tail(int x);
char b1_mapped(void);
unsigned b1_checks(void);
unsigned b1_same(void);
int b1_proxies(int x);

/* bank 2 */
int b2_sub(int a, int b);
int b2_fib(int n);
char b2_inc(char c);
int b2_twice(int x);
long b2_scale(long a, int b);
char b2_mapped(void);
unsigned b2_checks(void);
unsigned b2_cross(void);
int b2_proxies(int x);

int (* const ops[3])(int, int) = { b1_add, b2_sub, r_mul };

#pragma code( bcode1 )
#pragma data( bdata1 )

static volatile const char b1_tag[2] = { 0xb1, 0x11 };

__noinline char b1_mapped(void)
{
	return b1_tag[0] == 0xb1 && b1_tag[1] == 0x11;
}

__noinline int b1_add(int a, int b)
{
	return a + b;
}

__noinline int b1_neg(int x)
{
	return -x;
}

/* recursion through both banks: stack parameters */
int b1_fib(int n)
{
	if (n < 2)
		return n;
	int r = b2_fib(n - 1) + b2_fib(n - 2);
	return b1_mapped() ? r : -1000;
}

/* a call in tail position (Oscar64 may make it a jump to the stub) */
__noinline int b1_tail(int x)
{
	return b2_twice(x + 1);
}

/* the address of a function of this bank, called through a resident function */
__noinline unsigned b1_checks(void)
{
	unsigned ok = 0;
	int s = 0;
	char c = 0;

	for (char i = 0; i < 10; i++)
	{
		c = b2_inc(c);		/* a byte argument and result, in A */
		s += b2_twice(i);	/* an int argument in A and X */
	}
	if (c == 10 && s == 90 && b1_mapped())
		ok |= 1;
	if (r_call_back(b1_neg, 5) == -5 && b1_mapped())
		ok |= 2;
	if (r_apply(b2_sub, 9, 4) == 5 && r_apply(ops[0], 2, 3) == 5 && b1_mapped())
		ok |= 4;
	if (ops[1](7, 2) == 5 && ops[2](3, 4) == 12 && b1_mapped())
		ok |= 8;
	if (b2_scale(100000L, 3) == 300000L && b1_mapped())
		ok |= 16;
	return ok;
}

/* calls of a resident function with the same constant arguments from several places:
 * Oscar64 gives them one entry that loads the constants (a proxy); for a resident
 * callee the far-spaces fork puts it in the calling bank (run_bankstub.py checks) */
__noinline int b1_pa(int x) { return r_mix(3, 5, x); }
__noinline int b1_pb(int x) { return r_mix(3, 5, x) + 1; }
__noinline int b1_pc(int x) { return r_mix(3, 5, x) + 2; }

__noinline int b1_proxies(int x)
{
	int s = b1_pa(x) + b1_pb(sink) + b1_pc(x);
	return b1_mapped() ? s : -1;
}

__noinline unsigned b1_same(void)
{
	int i, s = 0;
	timer_start();
	for (i = 0; i < N; i++)
		s = b1_add(s, i);
	sink = s;
	return timer_stop();
}

#pragma code( bcode2 )
#pragma data( bdata2 )

static volatile const char b2_tag[2] = { 0xb2, 0x22 };

__noinline char b2_mapped(void)
{
	return b2_tag[0] == 0xb2 && b2_tag[1] == 0x22;
}

__noinline int b2_sub(int a, int b)
{
	return a - b;
}

int b2_fib(int n)
{
	if (n < 2)
		return n;
	int r = b1_fib(n - 1) + b1_fib(n - 2);
	return b2_mapped() ? r : -2000;
}

__noinline char b2_inc(char c)
{
	return c + 1;
}

__noinline int b2_twice(int x)
{
	return x * 2;
}

__noinline long b2_scale(long a, int b)
{
	return a * b;
}

__noinline unsigned b2_checks(void)
{
	unsigned ok = 0;
	if (b1_tail(4) == 10 && b2_mapped())
		ok |= 1;
	if (b1_fib(12) == 144 && b2_mapped())
		ok |= 2;
	return ok;
}

__noinline int b2_pa(int x) { return r_mix(7, 1, x); }
__noinline int b2_pb(int x) { return r_mix(7, 1, x) + 1; }
__noinline int b2_pc(int x) { return r_mix(7, 1, x) + 2; }

__noinline int b2_proxies(int x)
{
	int s = b2_pa(x) + b2_pb(sink) + b2_pc(x) + b1_proxies(x);
	return b2_mapped() ? s : -1;
}

__noinline unsigned b2_cross(void)
{
	int i, s = 0;
	timer_start();
	for (i = 0; i < N; i++)
		s = b1_add(s, i);
	sink = s;
	return timer_stop();
}

#pragma code( code )
#pragma data( data )

__noinline int r_mix(int a, int b, int c)
{
	return a * 100 + b * 10 + c;
}

__noinline int r_mul(int a, int b)
{
	return a * b;
}

__noinline int r_apply(int (*f)(int, int), int a, int b)
{
	return f(a, b);
}

__noinline int r_call_back(int (*f)(int), int x)
{
	return f(x);
}

int main(void)
{
	/* an Oscar64 EasyFlash program starts with no KERNAL run and the ROMs (the
	 * cartridge's included) not mapped: map them and set the CIAs up */
	mmap_set(MMAP_ROM);
	cia_init();

	check(0x0001, b1_add(2, 3) == 5 && nh_bank == 0);
	check(0x0002, b1_fib(15) == 610 && nh_bank == 0);
	check(0x0004, b2_fib(10) == 55 && nh_bank == 0);
	unsigned k = b1_checks();
	check(0x0008, k & 1);
	check(0x0010, k & 2);
	check(0x0020, k & 4);
	check(0x0040, k & 8);
	check(0x0080, k & 16);
	k = b2_checks();
	check(0x0100, k & 1);
	check(0x0200, k & 2);
	check(0x0400, ops[0](20, 22) == 42 && ops[1](20, 22) == -2 && nh_bank == 0);
	check(0x0800, b1_tail(1) == 4 && b2_inc(41) == 42 && nh_bank == 0);
	/* 354 + (354 + 1) + (354 + 2); 714 + 715 + 716 and bank 1's; 351 + 352 */
	sink = 4;
	check(0x2000, b1_proxies(4) == 1065 && b2_proxies(4) == 2145 + 1065 &&
		r_mix(3, 5, 1) + r_mix(3, 5, sink) == 705 && nh_bank == 0);

	__asm { sei }
	spike_result[2] = b2_cross();
	spike_result[3] = b1_same();
	__asm { cli }
	check(0x1000, nh_bank == 0);

	spike_result[0] = passed;
	spike_result[1] = ran;
	spike_done = 1;
	for (;;)
		;
	return 0;
}
