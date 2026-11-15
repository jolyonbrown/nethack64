/* bankcall.c - banking spike prototype (docs/BANKING-SPIKE.md, "Next").
 *
 * EasyFlash build (-tf=crt): cycles per call, with interrupts off, for
 *   [0] a call to a resident function,
 *   [1] a call to a function in the same bank,
 *   [2] a call into another bank through a resident C trampoline (remember the
 *       bank, switch $DE00, call, switch back),
 *   [3] the same loop with the addition done in line, the baseline that [0]-[2]
 *       are measured against.
 * PRG build (-dREUTIME): cycles for REU fetches into $8000, which is RAM with no
 * cartridge: [0] 1 byte, [1] 1 KB, [2] 4 KB, [3] 16 KB.  The REU registers are only
 * written, never read (AGENTS.md).
 *
 * Results are left in spike_result[] with spike_done set; tests/spikes/run_bankcall.py
 * reads them through VICE's monitor.
 */
#include <c64/cia.h>
#include <c64/reu.h>
#ifndef REUTIME
#include <c64/easyflash.h>
#include <c64/memmap.h>
#endif

#define N 64				/* calls per timing */

/* keep the program, its stack and heap below $8000: the bank window (and, in the
 * REU build, the DMA target) is $8000-$BFFF */
#pragma region( main, 0x0900, 0x8000, , , { code, data, bss, heap, stack } )

volatile unsigned spike_result[4];	/* volatile: nothing here reads it, so it would be dropped */
volatile char spike_done;
volatile int sink;

/* CIA 2 timer A counting system clock cycles (the KERNAL does not use it) */
__noinline void timer_start(void)
{
	cia2.cra = 0;
	cia2.ta = 0xffff;
	cia2.cra = 0x11;			/* force load, start, continuous, count phi2 */
}

__noinline unsigned timer_stop(void)
{
	cia2.cra = 0;				/* stop first, so the two bytes are read consistently */
	return 0xffff - cia2.ta;
}

#ifndef REUTIME

#pragma section( bcode1, 0 )
#pragma section( bdata1, 0 )
#pragma region( bank1, 0x8000, 0xc000, , 1, { bcode1, bdata1 } )
#pragma section( bcode2, 0 )
#pragma section( bdata2, 0 )
#pragma region( bank2, 0x8000, 0xc000, , 2, { bcode2, bdata2 } )

volatile char cur_bank;

int r_add(int a, int b);
int t_add1(int a, int b);

#pragma code( bcode1 )
#pragma data( bdata1 )

__noinline int b1_add(int a, int b)
{
	return a + b;
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

__noinline unsigned b2_cross(void)
{
	int i, s = 0;
	timer_start();
	for (i = 0; i < N; i++)
		s = t_add1(s, i);
	sink = s;
	return timer_stop();
}

#pragma code( code )
#pragma data( data )

__noinline int r_add(int a, int b)
{
	return a + b;
}

/* the trampoline a generator would write for b1_add */
__noinline int t_add1(int a, int b)
{
	char old = cur_bank;
	int r;
	cur_bank = 1;
	eflash.bank = 1;
	r = b1_add(a, b);
	cur_bank = old;
	eflash.bank = old;
	return r;
}

__noinline unsigned in_bank1(void)
{
	char old = cur_bank;
	unsigned r;
	cur_bank = 1;
	eflash.bank = 1;
	r = b1_same();
	cur_bank = old;
	eflash.bank = old;
	return r;
}

__noinline unsigned in_bank2(void)
{
	char old = cur_bank;
	unsigned r;
	cur_bank = 2;
	eflash.bank = 2;
	r = b2_cross();
	cur_bank = old;
	eflash.bank = old;
	return r;
}

__noinline unsigned resident_calls(void)
{
	int i, s = 0;
	timer_start();
	for (i = 0; i < N; i++)
		s = r_add(s, i);
	sink = s;
	return timer_stop();
}

__noinline unsigned inline_adds(void)
{
	int i, s = 0;
	timer_start();
	for (i = 0; i < N; i++)
		s = s + i;
	sink = s;
	return timer_stop();
}

int main(void)
{
	/* an Oscar64 EasyFlash program starts with no KERNAL run and the ROMs (the
	 * cartridge's included) not mapped: map them and set the CIAs up */
	mmap_set(MMAP_ROM);
	cia_init();
	__asm { sei }
	spike_result[0] = resident_calls();
	spike_result[1] = in_bank1();
	spike_result[2] = in_bank2();
	spike_result[3] = inline_adds();
	__asm { cli }
	spike_done = 1;
	for (;;)
		;
	return 0;
}

#else

__noinline unsigned fetch(unsigned len)
{
	timer_start();
	reu_load(0x10000ul, (volatile char *)0x8000, len);
	return timer_stop();
}

int main(void)
{
	__asm { sei }
	spike_result[0] = fetch(1);
	spike_result[1] = fetch(1024);
	spike_result[2] = fetch(4096);
	spike_result[3] = fetch(16384);
	__asm { cli }
	spike_done = 1;
	for (;;)
		;
	return 0;
}

#endif
