/* farchar128.c - spike: far characters on a C128 kept in RAM bank 1 (ADR-0010, T2.13).
 *
 * The design under test: a byte pointer whose value lies in $C100-$FBFF is a character-space
 * address, and on a C128 the character space is RAM bank 1 at that same address. Bank 0
 * keeps only code from $C000 up, which no `char *` ever points at, so the range costs no
 * near RAM. A byte access through such a pointer calls a stub in the top 1 KB of RAM,
 * which the MMU makes common to both banks ($FC00-$FFFF, as Oscar64's c128/bank1.h does):
 * the stub saves the configuration register, loads PCR B (bank 1, all RAM) by a write to
 * $FF02, makes the one access and puts the old configuration back. Below $C100 the pointer
 * is used as it is; the compiler's inline test of the base's high byte is modelled below
 * by hand (`LDA p+1; CMP #$C0; BCC near`).
 *
 * spike_result[0]: the checks passed (a bit each, see run_farchar128.py), [1] those run;
 * [2..7]: CIA 2 cycles at 1 MHz for 256 byte reads: plain, tested near, tested far; for a
 *         32-byte string copy far to near; for 256 byte writes tested far; and one call of
 *         the bank-0 code at $C100 that reads its own addresses in bank 1.
 * $DF00-$DFFF is never read (AGENTS.md). */
#include <c128/mmu.h>
#include <c64/cia.h>
#include <string.h>

#pragma region( main, 0x1d00, 0x7e00, , , { code, data, bss, heap, stack } )

/* the stubs: loaded at $7E00 with the program, run at $FC00 (copied there first) */
#pragma section( nhfc, 0 )
#pragma region( nhfc, 0x7e00, 0x7f00, , , { nhfc }, 0xfc00 )

/* bank-0 code in the character range: here only to be overlaid by bank-1 data */
#pragma section( c1code, 0 )
#pragma region( c1, 0xc100, 0xd000, , , { c1code } )

#define FC_LO	0xc100
#define FC_HI	0xfc00		/* the first address past the range */
#define CR_NEAR	0x3e		/* bank 0, all RAM, I/O in */

__zeropage char *nh_fcp, *nh_fcq;
volatile unsigned spike_result[8];
volatile char spike_done;
volatile char fc_val, fc_cr, fc_i;

#pragma code( nhfc )

/* A = the byte at (nh_fcp),Y in bank 1; X is lost */
__asm nh_fcrd
{
		ldx $ff00
		sta $ff02
		lda (nh_fcp), y
		stx $ff00
		rts
}

/* the byte in A to (nh_fcp),Y in bank 1; X is lost */
__asm nh_fcwr
{
		ldx $ff00
		sta $ff02
		sta (nh_fcp), y
		stx $ff00
		rts
}

/* a string of at most 255 bytes from (nh_fcp) in bank 1 to (nh_fcq) in bank 0, its NUL too */
__asm nh_fcstrcpy
{
		ldx $ff00
		ldy #0
l:		sta $ff02
		lda (nh_fcp), y
		stx $ff00
		sta (nh_fcq), y
		beq d
		iny
		bne l
d:		rts
}

#pragma code( c1code )

/* code in bank 0 at $C1xx that reads, through the stub, the bank-1 bytes at its own
 * addresses: the sum of the first 64 */
__noinline unsigned c1_own_sum(void)
{
	unsigned s = 0;
	nh_fcp = (char *)(unsigned)c1_own_sum;
	for (fc_i = 0; fc_i < 64; fc_i++)
	{
		__asm
		{
			ldy fc_i
			jsr nh_fcrd
			sta fc_val
		}
		s += fc_val;
	}
	return s;
}

#pragma code( code )

static char pattern(unsigned a)
{
	return (char)(a ^ (a >> 8) * 7 ^ 0x5a);
}

unsigned passed, ran;

__noinline void check(unsigned bit, char ok)
{
	ran |= bit;
	if (ok)
		passed |= bit;
}

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

__noinline char fc_read(const char *p)
{
	nh_fcp = (char *)p;
	__asm
	{
		ldy #0
		jsr nh_fcrd
		sta fc_val
	}
	return fc_val;
}

__noinline void fc_write(char *p, char c)
{
	nh_fcp = p;
	fc_val = c;
	__asm
	{
		lda fc_val
		ldy #0
		jsr nh_fcwr
	}
}

/* the configuration register after a read with the MMU at cr */
__noinline char cr_after(char cr)
{
	nh_fcp = (char *)0xc200;
	fc_cr = cr;
	__asm
	{
		lda fc_cr
		sta $ff00
		ldy #0
		jsr nh_fcrd
		lda $ff00
		sta fc_cr
		lda #CR_NEAR
		sta $ff00
	}
	return fc_cr;
}

static char nearbuf[256];
static char buf2[64];

/* 256 reads, three ways, from nh_fcp: plain, then with the compiler's test (the near path
 * when nh_fcp is below $C100, the far path above) */
__noinline unsigned time_plain(void)
{
	timer_start();
	__asm
	{
		ldy #0
l:		lda (nh_fcp), y
		iny
		bne l
	}
	return timer_stop();
}

__noinline unsigned time_tested(void)
{
	timer_start();
	__asm
	{
		ldy #0
l:		lda nh_fcp + 1
		cmp #$c0
		bcc n
		jsr nh_fcrd
		jmp d
n:		lda (nh_fcp), y
d:		iny
		bne l
	}
	return timer_stop();
}

__noinline unsigned time_tested_write(void)
{
	timer_start();
	__asm
	{
		ldy #0
l:		tya
		pha
		lda nh_fcp + 1
		cmp #$c0
		pla
		bcc n
		jsr nh_fcwr
		jmp d
n:		sta (nh_fcp), y
d:		iny
		bne l
	}
	return timer_stop();
}

int main(void)
{
	__asm { sei }
	mmu.cr = CR_NEAR;
	cia2.cra = 0;
	xmmu.pcr[1] = 0x7f;			/* PCR B: bank 1, all RAM */
	xmmu.rcr = (xmmu.rcr & 0xf0) | 0x08;	/* the top 1 KB common, nothing at the bottom */
	memcpy((char *)0xfc00, (char *)0x7e00, 0x100);

	/* 1: every byte of the range written in bank 1 reads back */
	unsigned bad = 0;
	for (unsigned a = FC_LO; a < FC_HI; a++)
		fc_write((char *)a, pattern(a));
	for (unsigned a = FC_LO; a < FC_HI; a++)
		bad += fc_read((const char *)a) != pattern(a);
	check(1, bad == 0);

	/* 2: bank 0's code at the same addresses still runs, and reads bank 1 at its own
	 * addresses rather than itself */
	unsigned want = 0;
	for (char i = 0; i < 64; i++)
		want += pattern((unsigned)c1_own_sum + i);
	unsigned own = c1_own_sum();
	check(2, own == want);

	/* 3: bank 0 really holds something else there (the code's first bytes are not the pattern) */
	char same = 0;
	for (char i = 0; i < 16; i++)
		same += ((const char *)(unsigned)c1_own_sum)[i] == pattern((unsigned)c1_own_sum + i);
	check(4, same < 4);

	/* 4: the stub puts back whatever configuration it found: all RAM, the cartridge's
	 * $3A, all RAM without I/O */
	check(8, cr_after(0x3e) == 0x3e && cr_after(0x3a) == 0x3a && cr_after(0x3f) == 0x3f);

	/* 5: a string copy far to near across $CFFF/$D000 (bank 1's RAM under the I/O) */
	for (char i = 0; i < 31; i++)
		fc_write((char *)(0xcff0 + i), 'a' + i);
	fc_write((char *)(0xcff0 + 31), 0);
	nh_fcp = (char *)0xcff0;
	nh_fcq = buf2;
	__asm { jsr nh_fcstrcpy }
	bad = strlen(buf2) != 31;
	for (char i = 0; i < 31; i++)
		bad += buf2[i] != 'a' + i;
	check(16, bad == 0);

	/* 6: the VIC's registers are untouched by the writes under the I/O (border colour) */
	char border = *(volatile char *)0xd020 & 0x0f;
	for (char i = 0; i < 32; i++)
		fc_write((char *)(0xd020 + i), 0x0e);
	check(32, (*(volatile char *)0xd020 & 0x0f) == border && fc_read((const char *)0xd020) == 0x0e);

	/* timings */
	for (unsigned i = 0; i < 256; i++)
		nearbuf[i] = (char)i;
	nh_fcp = nearbuf;
	spike_result[2] = time_plain();
	spike_result[3] = time_tested();
	nh_fcp = (char *)0xc400;
	spike_result[4] = time_tested();
	nh_fcp = (char *)0xcff0;
	nh_fcq = buf2;
	timer_start();
	__asm { jsr nh_fcstrcpy }
	spike_result[5] = timer_stop();
	nh_fcp = (char *)0xe000;
	spike_result[6] = time_tested_write();
	timer_start();
	c1_own_sum();
	spike_result[7] = timer_stop();

	/* 7: the tested near path read the near buffer, the far writes landed in bank 1 */
	bad = 0;
	for (unsigned i = 0; i < 256; i++)
		bad += fc_read((const char *)(0xe000 + i)) != (char)i;
	check(64, bad == 0);

	spike_result[0] = passed;
	spike_result[1] = ran;
	mmu.cr = 0x3f;
	spike_done = 1;
	for (;;)
		;
	return 0;
}
