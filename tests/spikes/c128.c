/* c128.c - spike: what a C128 (+ REU) gives the port (T2.12, the hardware discussion).
 *
 * Oscar64's C128 target (-tm=c128) runs with the MMU at $3F: bank 0, RAM everywhere, no ROM
 * and no I/O (its program region is $1D00-$FE00); code switches I/O in ($3E) to reach a chip.
 * This checks the RAM that leaves in view, the second 64 KB bank, the REU, the VDC (the
 * 80-column chip, with its own RAM) and 2 MHz, and times what the port would do with them.
 * Checks (bits of spike_result[0], run ones in [1]):
 *   0  $0400-$1BFF is RAM (6 KB below the program, the KERNAL never called)
 *   1  $D000-$DFFF is RAM at $3F; at $3E the I/O is there (the raster moves), and back at
 *      $3F the RAM kept its bytes
 *   2  $E000-$EFFF is RAM (no KERNAL ROM)
 *   3  bank 1 holds other bytes than bank 0 at $8000 (bnk1_writem/bnk1_readm)
 *   4  the REU: 16 KB stored from bank 0's $8000 and loaded to $4000 match bank 0's bytes
 *   5  the VDC: 10 bytes written to its RAM read back the same
 *   6  2 MHz: the same loop takes fewer 1 MHz timer ticks with $D030 bit 0 set
 * Timings (spike_val[], CIA 1 timer ticks, 1 MHz whatever the CPU clock):
 *   0 bank 1 -> bank 0, 256 bytes (bnk1_readm)   1 REU -> bank 0, 16 KB
 *   2 VDC, 2,000 bytes written (a screen)       3 loop at 1 MHz   4 the same loop at 2 MHz
 *   5 REU -> bank 0, 16 KB at 2 MHz
 * tests/spikes/run_c128.py builds it, runs it in headless x128 and reports. */
#include <c128/mmu.h>
#include <c128/bank1.h>
#include <c128/vdc.h>
#include <c64/reu.h>
#include <string.h>

/* the program below $4000, so that $4000-$EFFF is free for the tests */
#pragma region( main, 0x1d00, 0x4000, , , { code, data, bss, heap, stack } )

volatile unsigned spike_result[2];
volatile unsigned spike_val[6];
volatile char spike_done;

static void io_on(void) { mmu.cr = 0x3e; }
static void io_off(void) { mmu.cr = 0x3f; }

/* CIA 1 timer A free-running from $FFFF; I/O must be in */
static void timer_start(void)
{
	*(volatile char *)0xdc0e = 0x00;
	*(volatile char *)0xdc04 = 0xff;
	*(volatile char *)0xdc05 = 0xff;
	*(volatile char *)0xdc0e = 0x11;
}

static unsigned timer_read(void)
{
	char lo = *(volatile char *)0xdc04;
	char hi = *(volatile char *)0xdc05;
	char lo2 = *(volatile char *)0xdc04;
	if (lo2 > lo)	/* the high byte moved between the reads */
		hi = *(volatile char *)0xdc05;
	return 0xffff - (((unsigned)hi << 8) | lo2);
}

static void pass(char bit, bool ok)
{
	spike_result[1] |= 1u << bit;
	if (ok)
		spike_result[0] |= 1u << bit;
}

static bool pattern_ok(volatile char * p, unsigned n, char seed)
{
	for (unsigned i = 0; i < n; i++)
		p[i] = (char)(i * 7 + seed);
	for (unsigned i = 0; i < n; i++)
		if (p[i] != (char)(i * 7 + seed))
			return false;
	return true;
}

static volatile char sink;

static unsigned busy_loop(void)
{
	timer_start();
	for (unsigned i = 0; i < 2000; i++)
		sink++;
	return timer_read();
}

static char buf[256];

int main(void)
{
	__asm { sei }
	io_off();

	/* 0: below the program */
	pass(0, pattern_ok((volatile char *)0x0400, 0x1800, 1));

	/* 1: RAM under I/O, then the I/O over it, then the RAM again */
	{
		bool ok = pattern_ok((volatile char *)0xd000, 0x1000, 2);
		io_on();
		char r0 = *(volatile char *)0xd012, moved = 0;
		for (unsigned i = 0; i < 2000 && !moved; i++)
			moved = *(volatile char *)0xd012 != r0;
		io_off();
		volatile char * p = (volatile char *)0xd000;
		for (unsigned i = 0; i < 0x1000; i++)
			if (p[i] != (char)(i * 7 + 2))
				ok = false;
		pass(1, ok && moved);
	}

	/* 2: RAM where the KERNAL ROM was */
	pass(2, pattern_ok((volatile char *)0xe000, 0x1000, 3));

	/* 3: bank 1 against bank 0, and a 256-byte copy out of bank 1 timed */
	bnk1_init();
	{
		char * b0 = (char *)0x8000;
		for (unsigned i = 0; i < 256; i++)
		{
			b0[i] = 0xa5;
			buf[i] = (char)(i ^ 0x3c);
		}
		bnk1_writem((volatile char *)0x8000, buf, 256);
		memset(buf, 0, 256);
		io_on(); timer_start(); io_off();
		bnk1_readm(buf, (volatile char *)0x8000, 256);
		io_on(); spike_val[0] = timer_read(); io_off();
		bool ok = true;
		for (unsigned i = 0; i < 256; i++)
			if (buf[i] != (char)(i ^ 0x3c) || b0[i] != (char)0xa5)
				ok = false;
		pass(3, ok);
	}

	/* 4: the REU, 16 KB from bank 0 and back to $4000, timed */
	{
		volatile char * src = (volatile char *)0x8000, * dst = (volatile char *)0x4000;
		for (unsigned i = 0; i < 0x4000; i++)
		{
			src[i] = (char)(i * 13 + 5);
			dst[i] = 0;
		}
		io_on();
		reu_store(0x10000ul, src, 0x4000);
		timer_start();
		reu_load(0x10000ul, dst, 0x4000);
		spike_val[1] = timer_read();
		io_off();
		bool ok = true;
		for (unsigned i = 0; i < 0x4000; i++)
			if (dst[i] != (char)(i * 13 + 5))
				ok = false;
		pass(4, ok);
	}

	/* 5: the VDC's own RAM, and a screen's worth of bytes timed */
	{
		static const char msg[10] = { 'N', 'E', 'T', 'H', 'A', 'C', 'K', '1', '2', '8' };
		char back[10];
		io_on();
		vdc_mem_write_buffer(0x0000, msg, 10);
		vdc_mem_read_buffer(0x0000, back, 10);
		timer_start();
		vdc_mem_addr(0x0000);
		for (unsigned i = 0; i < 2000; i++)
			vdc_mem_write((char)(i & 0x7f));
		spike_val[2] = timer_read();
		io_off();
		pass(5, memcmp(msg, back, 10) == 0);
	}

	/* 6: 2 MHz ($D030 bit 0; the VIC shows nothing useful meanwhile, the VDC is unaffected) */
	{
		io_on();
		spike_val[3] = busy_loop();
		*(volatile char *)0xd030 = 0x01;
		spike_val[4] = busy_loop();
		volatile char * dst = (volatile char *)0x4000;
		timer_start();
		reu_load(0x10000ul, dst, 0x4000);
		spike_val[5] = timer_read();
		*(volatile char *)0xd030 = 0x00;
		io_off();
		pass(6, spike_val[4] < spike_val[3]);
	}

	spike_done = 1;
	for (;;)
		;
	return 0;
}
