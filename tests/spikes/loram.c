/* loram.c - spike: RAM at $8000-$9FFF under a 16 KB EasyFlash bank (T2.12, lever 2).
 *
 * In the cartridge's 16K mode ($DE02 = $87) the PLA maps ROML at $8000 and ROMH at $A000
 * while $01 has LORAM and HIRAM set ($37).  With LORAM clear ($36) it should map RAM at
 * $8000-$9FFF and keep ROMH at $A000.  If so, 8 KB of RAM there can hold code that runs
 * while a bank's upper half stays mapped, and is hidden, not lost, while a whole bank is
 * mapped ($37).  Bank 1 holds 'L' at $8000 and 'H' at $A000; RAM below them gets $5A.
 * Checks (bits of spike_result[0], run ones in [1]):
 *   0  cartridge off, $01 = $36: $8000 and $A000 are RAM
 *   1  16K mode, $01 = $37: ROML at $8000, ROMH at $A000
 *   2  16K mode, $01 = $36: RAM at $8000, ROMH at $A000
 *   3  16K mode, $01 = $37: a write to $8000 reaches the RAM under ROML
 *   4  16K mode, $01 = $36: code copied to $8000 runs and returns, reading ROMH at $A000
 *   5  back to $37: bank 1's ROML again, the RAM's code kept under it
 * tests/spikes/run_loram.py builds it, runs it in VICE and reports. */
#include <c64/easyflash.h>
#include <c64/memmap.h>

#pragma region( main, 0x0900, 0x8000, , , { code, data, bss, heap, stack } )

#pragma section( bcode1, 0 )
#pragma section( bdata1, 0 )
#pragma section( bcode1h, 0 )
#pragma section( bdata1h, 0 )
#pragma region( bank1, 0x8000, 0xa000, , 1, { bcode1, bdata1 } )
#pragma region( bank1h, 0xa000, 0xc000, , 1, { bcode1h, bdata1h } )

/* Oscar64 puts const data in the code section */
#pragma code( bcode1 )
#pragma data( bdata1 )
const char roml_mark[4] = { 'L', '1', 'L', '1' };
#pragma code( bcode1h )
#pragma data( bdata1h )
const char romh_mark[4] = { 'H', '1', 'H', '1' };
#pragma code( code )
#pragma data( data )

volatile unsigned spike_result[2];
volatile char spike_done;
volatile char seen[16];

#define P1 (*(volatile char *)0x01)
#define EFBANK (*(volatile char *)0xde00)
#define EFCTL (*(volatile char *)0xde02)
#define LO ((volatile char *)0x8000)
#define HI ((volatile char *)0xa000)

/* LDA $A000; STA $0400; RTS: run from RAM at $8000, it leaves what $A000 shows at $0400
 * (the text screen, unused); Oscar64 returns values in zero page, not in A */
static const char probe[] = { 0xad, 0x00, 0xa0, 0x8d, 0x00, 0x04, 0x60 };

typedef void (*probe_fn)(void);

int main(void)
{
	unsigned pass = 0, ran = 0;
	char a, b;

	/* their addresses, so that the linker keeps the marks (they should be $8000, $A000) */
	seen[8] = (unsigned) roml_mark >> 8;
	seen[9] = (unsigned) romh_mark >> 8;
	__asm { sei }
	/* the cartridge off, BASIC off: all RAM */
	EFCTL = 0x04;
	P1 = 0x36;
	LO[0] = 0x5a; LO[1] = 0x5a;
	HI[0] = 0x5a;
	ran |= 1;
	if (LO[0] == 0x5a && HI[0] == 0x5a) pass |= 1;

	/* 16K mode, bank 1 */
	EFBANK = 1;
	EFCTL = 0x87;
	P1 = 0x37;
	ran |= 2;
	seen[0] = LO[0]; seen[1] = HI[0];
	if (LO[0] == 'L' && HI[0] == 'H') pass |= 2;

	P1 = 0x36;
	ran |= 4;
	seen[2] = LO[0]; seen[3] = HI[0];
	if (LO[0] == 0x5a && HI[0] == 'H') pass |= 4;

	/* a write with ROML mapped */
	P1 = 0x37;
	LO[1] = 0xa5;
	P1 = 0x36;
	ran |= 8;
	seen[4] = LO[1];
	if (LO[1] == 0xa5) pass |= 8;

	/* code in the RAM under ROML */
	for (a = 0; a < sizeof(probe); a++)
		LO[0x10 + a] = probe[a];
	ran |= 16;
	{
		probe_fn f = (probe_fn) 0x8010;
		*(volatile char *)0x0400 = 0;
		f();
		b = *(volatile char *)0x0400;
	}
	seen[5] = b;
	if (b == 'H') pass |= 16;

	P1 = 0x37;
	ran |= 32;
	seen[6] = LO[0];
	a = LO[0];
	P1 = 0x36;
	seen[7] = LO[0x10];
	if (a == 'L' && LO[0x10] == 0xad) pass |= 32;

	/* leave it as the program found it: 16K mode, bank 0 */
	P1 = 0x37;
	EFBANK = 0;
	__asm { cli }
	spike_result[0] = pass;
	spike_result[1] = ran;
	spike_done = 1;
	for (;;) ;
	return 0;
}
