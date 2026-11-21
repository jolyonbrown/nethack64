/*
 * reuprobe.c - sys_reu_banks() (sys.h), the REU's presence and size by DMA: the same on the
 * C64 (sys.c) and the C128 (sys128.c), whose REU registers are at $DF00 too.
 */
#include "sys.h"
#include <c64/reu.h>

/* volatile: the DMA changes these behind the optimiser's back */
static volatile char reu_probe[8];
static volatile char reu_check[8];
static volatile char reu_saved[8];

/* Leaves the REU as it found it: the code banks the EasyFlash cannot hold live there from
 * power-on (ADR-0008), REU offset 0 up. */
unsigned sys_reu_banks(void)
{
	unsigned char i, k;
	unsigned n;

	/* Write a pattern to bank 0 via DMA, read it back elsewhere. */
	reu_load(0x000000ul, reu_saved, 8);
	for (i = 0; i < 8; i++)
	{
		reu_probe[i] = 0xa5 ^ (i * 37);
		reu_check[i] = 0;
	}
	reu_store(0x000000ul, reu_probe, 8);
	reu_load(0x000000ul, reu_check, 8);
	reu_store(0x000000ul, reu_saved, 8);
	for (i = 0; i < 8; i++)
		if (reu_check[i] != reu_probe[i])
			return 0;

	/* Size: REUs come in powers of two (128 KB to 16 MB), and a smaller one ignores the
	 * high address bits, so the first 64 KB bank n that reads back as bank 0 is the size.
	 * Bank 0's first byte and bank n's are put back, bank 0's last (they may be one). */
	for (n = 1; n < 256; n <<= 1)
	{
		unsigned long at = (unsigned long)n << 16;
		reu_load(0x000000ul, reu_saved, 1);
		reu_load(at, reu_saved + 1, 1);
		reu_probe[0] = 0x5a;
		reu_store(0x000000ul, reu_probe, 1);
		reu_probe[0] = 0xc3;
		reu_store(at, reu_probe, 1);
		reu_load(0x000000ul, reu_check, 1);
		k = reu_check[0];
		reu_store(at, reu_saved + 1, 1);
		reu_store(0x000000ul, reu_saved, 1);
		if (k == 0xc3)
			return n;
	}
	return 256;
}
