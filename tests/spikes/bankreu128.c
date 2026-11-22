/* bankreu128.c - bankreu.c on a C128 in C128 mode (T2.13, ADR-0003 2026-11-21): calls into
 * banks on a Magic Desk 128 cartridge and in the REU, through the linker's stubs.
 *
 * In C128 mode the MMU maps the cartridge: its configuration register ($FF00) at $3A puts
 * "external function ROM" at $8000-$BFFF, where a Magic Desk 128 shows the bank last written
 * to $DE00; at $3E that range is RAM. Both keep the I/O in, which the bank register and the
 * REU need. Banks 1 and 2 are cartridge banks, executed in place; banks 64 and 65 live in the
 * REU (bank b at REU offset (b - 64) * 16 KB, tools/bank/c128_images.py) and are fetched into
 * the RAM at $8000-$BFFF when the window holds another one, as on the C64.
 *
 * Built with -tf=prg and one "#pragma overlay" per bank, so Oscar64 writes each bank as a
 * file of its own beside the program; c128_images.py makes the cartridge's and the REU's
 * images of them. The checks and timings are bankreu.c's (spike_result[0..4]); the last check
 * reads "the cartridge on again" as the MMU back at $3A for bank 1. The timer is CIA 2's at
 * 1 MHz. tests/spikes/run_bankreu128.py reads them through VICE's monitor.
 */
#include <c64/cia.h>

#define N 32

#pragma region( main, 0x1d00, 0x8000, , , { code, data, bss, heap, stack } )

#pragma overlay( bankreu128_ov1, 1 )
#pragma overlay( bankreu128_ov2, 2 )
#pragma overlay( bankreu128_ov64, 64 )
#pragma overlay( bankreu128_ov65, 65 )

#pragma section( bcode1, 0 )
#pragma section( bdata1, 0 )
#pragma region( bank1, 0x8000, 0xc000, , 1, { bcode1, bdata1 } )
#pragma section( bcode2, 0 )
#pragma section( bdata2, 0 )
#pragma region( bank2, 0x8000, 0xc000, , 2, { bcode2, bdata2 } )
#pragma section( bcode64, 0 )
#pragma section( bdata64, 0 )
#pragma region( bank64, 0x8000, 0xc000, , 64, { bcode64, bdata64 } )
#pragma section( bcode65, 0 )
#pragma section( bdata65, 0 )
#pragma region( bank65, 0x8000, 0xc000, , 65, { bcode65, bdata65 } )

volatile unsigned spike_result[5];
volatile char spike_done;
volatile int sink;

/* the bank mapped (the cartridge's bank register is write-only), the REU bank the window
 * holds (0: none, so no initialiser is needed, which compat #76 would fold), and whether the
 * cartridge is switched off; volatile, since only the assembler below writes them and the
 * compiler would otherwise keep their first values across the calls */
volatile unsigned char nh_bank, nh_window, nh_cartoff;
unsigned char nh_bc_a, nh_bc_x, nh_bc_y, nh_bc_t;
volatile unsigned nh_fetches;

/* Maps bank A: a cartridge bank (below 64), the MMU at $3A so that $8000-$BFFF is the
 * cartridge, or an REU bank, the MMU at $3E (RAM there), fetched into $8000-$BFFF if the window
 * holds another. Changes only A and the flags: the bank call routine keeps its index in Y
 * meanwhile. Writes the REU's registers and never reads them, nor $DE00 ($DF00-$DFFF,
 * docs/HARDWARE.md). nh_cartoff: 1 while the MMU is at $3E. */
#ifdef IO_OUT
/* -dIO_OUT: the I/O out by default (bankgen.py --io-out), so that $D000-$DFFF is RAM: the I/O
 * in only to write the bank register or start the REU's DMA, then the MMU at $3B (the
 * cartridge at $8000-$BFFF, RAM at $D000) or $3F (all RAM). This code must not lie at
 * $D000-$DFFF itself. nh_cartoff: 1 while the MMU is at $3F. */
__asm nh_map
{
		sta nh_bank
		lda #$3e
		sta $ff00
		lda nh_bank
		cmp #64
		bcs reu
		sta $de00
		lda #$3b
		sta $ff00
		lda #0
		sta nh_cartoff
		rts
reu:	lda #1
		sta nh_cartoff
		lda nh_bank
		cmp nh_window
		beq on
		sta nh_window
		inc nh_fetches
		bne cnt
		inc nh_fetches + 1
cnt:	lda nh_window
		sec
		sbc #64
		sta nh_bc_t
		asl
		asl
		asl
		asl
		asl
		asl
		sta $df05
		lda nh_bc_t
		lsr
		lsr
		sta $df06
		lda #0
		sta $df04
		sta $df02
		sta $df07
		sta $df0a
		lda #$80
		sta $df03
		lda #$40
		sta $df08
		lda #$91
		sta $df01
on:		lda #$3f
		sta $ff00
		rts
}
#else
__asm nh_map
{
		sta nh_bank
		cmp #64
		bcs reu
		sta $de00
		lda #$3a
		sta $ff00
		lda #0
		sta nh_cartoff
		rts
reu:	lda #$3e
		sta $ff00
		lda #1
		sta nh_cartoff
		lda nh_bank
		cmp nh_window
		beq on
		sta nh_window
		inc nh_fetches
		bne cnt
		inc nh_fetches + 1
cnt:	lda nh_window
		sec
		sbc #64
		sta nh_bc_t
		asl
		asl
		asl
		asl
		asl
		asl
		sta $df05
		lda nh_bc_t
		lsr
		lsr
		sta $df06
		lda #0
		sta $df04
		sta $df02
		sta $df07
		sta $df0a
		lda #$80
		sta $df03
		lda #$40
		sta $df08
		lda #$91
		sta $df01
on:		rts
}
#endif

/* Entered from a stub with the stub's last byte on the stack: reads the function and
 * the bank from the stub (which may be in the caller's bank), then maps the bank and jumps to the function with A, X and Y as
 * the caller left them; the function returns to bret, which maps the caller's bank
 * again (fetching it back into the window if it is an REU bank another call replaced)
 * and returns with A, X and Y as the function left them. Not re-entrant. */
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
		jsr nh_map
		lda nh_bc_a
		ldx nh_bc_x
		ldy nh_bc_y
bjmp:	jmp $ffff
bret:	nop
		sta nh_bc_a
		pla
		jsr nh_map
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
/* the I/O in around the CIA's registers, whatever the MMU was (-dIO_OUT leaves it out) */
__noinline void timer_start(void)
{
	char cr = *(volatile char *)0xff00;
	*(volatile char *)0xff00 = cr & 0xfe;
	cia2.cra = 0;
	cia2.ta = 0xffff;
	cia2.cra = 0x11;
	*(volatile char *)0xff00 = cr;
}

__noinline unsigned timer_stop(void)
{
	char cr = *(volatile char *)0xff00;
	*(volatile char *)0xff00 = cr & 0xfe;
	cia2.cra = 0;
	unsigned t = 0xffff - cia2.ta;
	*(volatile char *)0xff00 = cr;
	return t;
}

/* resident */
int r_apply(int (*f)(int, int), int a, int b);
int r_call_back(int (*f)(int), int x);

/* EasyFlash bank 1 */
int b1_add(int a, int b);
int b1_fib(int n);
char b1_mapped(void);
unsigned b1_checks(void);

/* EasyFlash bank 2 */
char b2_inc(char c);
int b2_twice(int x);
char b2_mapped(void);

/* REU bank 64 */
int u64_add(int a, int b);
int u64_fib(int n);
int u64_efib(int n);
int u64_neg(int x);
int u64_tail(int x);
char u64_mapped(void);
unsigned u64_checks(void);

/* REU bank 65 */
int u65_sub(int a, int b);
int u65_fib(int n);
long u65_scale(long a, int b);
char u65_mapped(void);

int (* const ops[3])(int, int) = { u64_add, u65_sub, b1_add };

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

/* recursion through EasyFlash bank 1 and REU bank 64: stack parameters */
int b1_fib(int n)
{
	if (n < 2)
		return n;
	int r = u64_efib(n - 1) + u64_efib(n - 2);
	return b1_mapped() ? r : -1000;
}

/* bank 1 calls into the REU and back */
__noinline unsigned b1_checks(void)
{
	unsigned ok = 0;
	if (u64_add(40, 2) == 42 && u65_sub(50, 8) == 42 && b1_mapped())
		ok |= 1;
	if (u65_scale(70000L, 3) == 210000L && b1_mapped())
		ok |= 2;
	return ok;
}

#pragma code( bcode2 )
#pragma data( bdata2 )

static volatile const char b2_tag[2] = { 0xb2, 0x22 };

__noinline char b2_mapped(void)
{
	return b2_tag[0] == 0xb2 && b2_tag[1] == 0x22;
}

__noinline char b2_inc(char c)
{
	return b2_mapped() ? c + 1 : 0;
}

__noinline int b2_twice(int x)
{
	return b2_mapped() ? x * 2 : -1;
}

#pragma code( bcode64 )
#pragma data( bdata64 )

static volatile const char u64_tag[2] = { 0x64, 0x46 };

__noinline char u64_mapped(void)
{
	return u64_tag[0] == 0x64 && u64_tag[1] == 0x46;
}

__noinline int u64_add(int a, int b)
{
	return u64_mapped() ? a + b : -100;
}

__noinline int u64_neg(int x)
{
	return -x;
}

/* recursion through REU banks 64 and 65: a fetch at every call and return */
int u64_fib(int n)
{
	if (n < 2)
		return n;
	int r = u65_fib(n - 1) + u65_fib(n - 2);
	return u64_mapped() ? r : -3000;
}

int u64_efib(int n)
{
	if (n < 2)
		return n;
	int r = b1_fib(n - 1) + b1_fib(n - 2);
	return u64_mapped() ? r : -4000;
}

__noinline int u64_tail(int x)
{
	return u65_sub(x, 1);
}

__noinline unsigned u64_checks(void)
{
	unsigned ok = 0;
	int s = 0;
	char c = 0;

	for (char i = 0; i < 10; i++)
	{
		c = b2_inc(c);		/* into EasyFlash bank 2: a byte in A */
		s += b2_twice(i);	/* an int in A and X; the loop counter may stay in Y */
	}
	if (c == 10 && s == 90 && u64_mapped())
		ok |= 1;
	if (r_call_back(u64_neg, 5) == -5 && u64_mapped())
		ok |= 2;
	if (r_apply(u65_sub, 9, 4) == 5 && r_apply(ops[2], 2, 3) == 5 && u64_mapped())
		ok |= 4;
	if (u65_scale(100000L, 3) == 300000L && u64_mapped())
		ok |= 8;
	if (u64_tail(10) == 9 && ops[1](7, 2) == 5 && u64_mapped())
		ok |= 16;
	return ok;
}

#pragma code( bcode65 )
#pragma data( bdata65 )

static volatile const char u65_tag[2] = { 0x65, 0x56 };

__noinline char u65_mapped(void)
{
	return u65_tag[0] == 0x65 && u65_tag[1] == 0x56;
}

__noinline int u65_sub(int a, int b)
{
	return u65_mapped() ? a - b : -200;
}

int u65_fib(int n)
{
	if (n < 2)
		return n;
	int r = u64_fib(n - 1) + u64_fib(n - 2);
	return u65_mapped() ? r : -5000;
}

__noinline long u65_scale(long a, int b)
{
	return u65_mapped() ? a * b : 0;
}

#pragma code( code )
#pragma data( data )

__noinline int r_apply(int (*f)(int, int), int a, int b)
{
	return f(a, b);
}

__noinline int r_call_back(int (*f)(int), int x)
{
	return f(x);
}

__noinline unsigned time_calls(char which)
{
	int i, s = 0;
	timer_start();
	if (which == 0)
		for (i = 0; i < N; i++)
			s = u64_add(s, i);
	else if (which == 1)
		for (i = 0; i < N; i++)
			s = b1_add(s, i);
	else
	{
		/* the window holds bank 64: three fetches, about 16 K cycles each, which is as
		 * many as the 16-bit timer can count */
		s = u65_sub(s, 1);
		s = u64_add(s, 1);
		s = u65_sub(s, 1);
	}
	sink = s;
	return timer_stop();
}

int main(void)
{
	/* Oscar64's C128 start leaves the MMU at $3F (RAM everywhere, no I/O): the I/O in, and
	 * the KERNAL's interrupt handler gone with its ROM, so interrupts stay off */
	__asm { sei }
	*(volatile char *)0xff00 = 0x3e;
	nh_cartoff = 1;
	cia2.cra = 0;

	check(0x0001, u64_add(2, 3) == 5 && nh_bank == 0 && nh_window == 64);
	check(0x0002, u64_fib(8) == 21 && nh_bank == 0);
	check(0x0004, u65_fib(7) == 13 && nh_bank == 0);
	check(0x0008, b1_fib(12) == 144 && nh_bank == 0);
	unsigned k = u64_checks();
	check(0x0010, k & 1);
	check(0x0020, k & 2);
	check(0x0040, k & 4);
	check(0x0080, k & 8);
	check(0x0100, k & 16);
	k = b1_checks();
	check(0x0200, k & 1);
	check(0x0400, k & 2);
	check(0x0800, ops[0](20, 22) == 42 && ops[1](20, 22) == -2 && ops[2](1, 2) == 3 && nh_bank == 0);
	/* the cartridge back in after REU calls: bank 1 reads its own tag, the MMU at $3A ($3B
	 * with the I/O out) */
	check(0x1000, u65_sub(3, 1) == 2 && b1_add(1, 1) == 2 && nh_cartoff == 0
#ifdef IO_OUT
		&& *(volatile char *)0xff00 == 0x3b
#endif
		);

	__asm { sei }
	u64_add(0, 0);
	spike_result[2] = time_calls(0);
	spike_result[3] = time_calls(1);
	unsigned f = nh_fetches;
	spike_result[4] = time_calls(2);
	check(0x2000, nh_bank == 0 && nh_fetches - f == 3);

	spike_result[0] = passed;
	spike_result[1] = ran;
	spike_done = 1;
	for (;;)
		;
	return 0;
}
