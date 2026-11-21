/* bankslice.c - spike: a slice of code and tables in every bank (T2.12, lever 3).
 *
 * One Oscar64 region, $B000-$BFFF, whose bank set is every code bank (1, 2 and REU 64): the
 * linker writes its objects into each bank's image, and Linker::SectionBank() takes such a
 * section for resident code, so a call into it is a direct JSR from any bank and a call out
 * of it to a bank goes through a resident stub, which maps the caller's bank again after.
 * Banks 1, 2 and 64 end at $B000.  Bank 0 holds the startup and the program's image and
 * has no slice, so resident code calls the slice only with a code bank mapped.  Found on
 * the way: the cartridge's startup leaves $01 = $36, which hides ROML (tests/spikes/loram.c),
 * so the bank call routine sets $37 whenever it maps an EasyFlash bank.  Checks (bits of spike_result[0], run ones in [1]):
 *   0  resident code calls a slice function (bank 1 mapped)
 *   1  bank 1 calls it directly
 *   2  REU bank 64 calls it directly
 *   3  a slice table and a slice literal read from bank 2 and from bank 64
 *   4  bank 1 -> slice -> bank 2 and back: bank 1 mapped again (its own table reads right)
 *   5  REU 64 -> slice -> EasyFlash 1 and back: bank 64 in the window again
 *   6  the slice's bytes the same in banks 1, 2 and 64
 *   7  a slice function's address called from resident code, bank 2 mapped
 * tests/spikes/run_bankslice.py builds it, moves bank 64 into an REU image, runs it in VICE. */
#include <c64/easyflash.h>
#include <c64/memmap.h>
#include <string.h>

#pragma region( main, 0x0900, 0x8000, , , { code, data, bss, heap, stack } )

#pragma section( bcode1, 0 )
#pragma section( bdata1, 0 )
#pragma region( bank1, 0x8000, 0xb000, , 1, { bcode1, bdata1 } )
#pragma section( bcode2, 0 )
#pragma section( bdata2, 0 )
#pragma region( bank2, 0x8000, 0xb000, , 2, { bcode2, bdata2 } )
#pragma section( bcode64, 0 )
#pragma section( bdata64, 0 )
#pragma region( bank64, 0x8000, 0xb000, , 64, { bcode64, bdata64 } )
#pragma section( nhslice, 0 )
#pragma region( nhslice_r, 0xb000, 0xc000, , { 1, 2, 64 }, { nhslice } )

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

/* Maps bank A: an EasyFlash bank (below 64) with the cartridge on, or an REU bank, fetched
 * into $8000-$BFFF if the window holds another, with the cartridge and BASIC off. Changes
 * only A and the flags: the bank call routine keeps its index in Y meanwhile. Writes the
 * REU's registers and never reads them ($DF00-$DFFF, docs/HARDWARE.md). */
__asm nh_map
{
		sta nh_bank
		cmp #64
		bcs reu
		sta $de00
		lda nh_cartoff
		beq ef
		lda #0
		sta nh_cartoff
		lda #$87
		sta $de02
ef:		lda #$37			/* ROML too: the cartridge startup leaves $36 (tests/spikes/bankslice.c) */
		sta $01
on:		rts
reu:	cmp nh_window
		beq off
		sta nh_window
		lda #$04
		sta $de02
		lda #$36
		sta $01
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
off:	lda nh_cartoff
		bne on
		lda #1
		sta nh_cartoff
		lda #$04
		sta $de02
		lda #$36
		sta $01
		rts
}

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

volatile unsigned passed, ran;		/* volatile: read by the runner if the program hangs */

int b1_twice(int x);
int b2_mul(int a, int b);
int b64_entry(int x);
int b1_add3(int x);

/* ---- the slice ---- */
#pragma code( nhslice )
#pragma data( nhslice )

const char s_table[8] = { 'T', 'A', 'B', 'L', 'E', 0, 0, 0 };

__noinline int s_add(int a, int b)
{
	return a + b + s_table[0];		/* 'T' = 84 */
}

__noinline const char *s_lit(void)
{
	return "slice";
}

/* calls into bank 2 from wherever it was called */
__noinline int s_call2(int a)
{
	return b2_mul(a, 3) + 1;
}

/* calls into EasyFlash bank 1 */
__noinline int s_call1(int a)
{
	return b1_add3(a) * 2;
}

#pragma code( code )
#pragma data( data )

/* ---- bank 1 ---- */
#pragma code( bcode1 )
#pragma data( bdata1 )
const char b1_tag[4] = { 'B', '1', 0, 0 };

__noinline int b1_add3(int x)
{
	return x + 3;
}

/* bit 1 and 4 */
__noinline int b1_twice(int x)
{
	int r = 0;
	if (s_add(x, 1) == x + 85) r |= 1;
	if (s_call2(x) == x * 3 + 1 && b1_tag[0] == 'B' && b1_tag[1] == '1') r |= 2;
	return r;
}

/* ---- bank 2 ---- */
#pragma code( bcode2 )
#pragma data( bdata2 )
const char b2_tag[4] = { 'B', '2', 0, 0 };

__noinline int b2_mul(int a, int b)
{
	return a * b + (b2_tag[1] - '2');
}

__noinline int b2_reads(void)
{
	return s_table[1] == 'A' && !strcmp(s_lit(), "slice");
}

/* ---- REU bank 64 ---- */
#pragma code( bcode64 )
#pragma data( bdata64 )
const char b64_tag[4] = { 'R', '6', '4', 0 };

__noinline int b64_entry(int x)
{
	int r = 0;
	if (s_add(x, 2) == x + 86) r |= 1;
	if (s_table[4] == 'E' && !strcmp(s_lit(), "slice")) r |= 2;
	if (s_call1(x) == (x + 3) * 2 && b64_tag[0] == 'R' && b64_tag[2] == '4') r |= 4;
	return r;
}

/* ---- resident ---- */
#pragma code( code )
#pragma data( data )

#define CHECK(bit, cond) do { ran |= 1u << (bit); if (cond) passed |= 1u << (bit); } while (0)

unsigned char slice_copy[4][16];
typedef int (*sfn)(int, int);
volatile sfn s_ptr = s_add;

__noinline void read_slice(unsigned char k, unsigned char bank)
{
	/* map the bank, copy its slice's first bytes, map bank 1 again */
	__asm {
		lda bank
		jsr nh_map
	}
	memcpy(slice_copy[k], (char *)0xb000, 16);
	__asm {
		lda #1
		jsr nh_map
	}
}

int main(void)
{
	int r;
	/* bank 0 holds the startup and the program's image, and no slice: map a bank first */
	__asm {
		lda #1
		jsr nh_map
	}
	CHECK(0, s_add(5, 6) == 95);
	r = b1_twice(10);
	CHECK(1, r & 1);
	CHECK(4, r & 2);
	r = b64_entry(7);
	CHECK(2, r & 1);
	CHECK(3, (r & 2) && b2_reads());
	CHECK(5, r & 4);
	read_slice(0, 1); read_slice(1, 1); read_slice(2, 2); read_slice(3, 64);
	CHECK(6, !memcmp(slice_copy[0], slice_copy[2], 16) && !memcmp(slice_copy[0], slice_copy[3], 16) &&
		 slice_copy[0][0] != slice_copy[0][1]);
	{
		unsigned char b = 2;
		__asm {
			lda b
			jsr nh_map
		}
		r = s_ptr(1, 2);
		__asm {
			lda #1
			jsr nh_map
		}
		CHECK(7, r == 87);
	}
	spike_result[0] = passed;
	spike_result[1] = ran;
	spike_done = 1;
	for (;;) ;
	return 0;
}
