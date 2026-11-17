#include "sys.h"
#include <c64/reu.h>

void sys_init(void)
{
	/* RAMTAS normally sets these; we skip RAMTAS (it clears zero page). */
	*(volatile char *)0x0281 = 0x00;	/* bottom of memory lo */
	*(volatile char *)0x0282 = 0x08;	/* bottom of memory hi */
	*(volatile char *)0x0283 = 0x00;	/* top of memory lo */
	*(volatile char *)0x0284 = 0xa0;	/* top of memory hi */
	*(volatile char *)0x0288 = 0x04;	/* screen editor page */

	__asm {
		sei
		jsr $fda3		/* IOINIT: CIAs, SID, VIC, IRQ timer */
		jsr $fd15		/* RESTOR: KERNAL vectors */
		jsr $ff5b		/* CINT:   screen editor + VIC */
		cli
	}
}

/* PETSCII control/cursor codes and what the game should see instead.
 * (A table rather than a switch: Oscar64 v1.32.273 -Os segfaults on the
 * switch version - see tests/oscar64-repros/r9_os_switch_asm_segv.c.) */
static const char key_from[] = { 13,   20, 3,  95, 17,  145, 29,  157, 0 };
static const char key_to[]   = { '\n', 8,  27, 27, 'j', 'k', 'l', 'h' };

static char petscii_to_ascii(char c)
{
	for (char i = 0; key_from[i]; i++)
		if (key_from[i] == c)
			return key_to[i];
	if (c >= 65 && c <= 90)		/* unshifted letters -> lower case */
		return c + 32;
	if (c >= 193 && c <= 218)	/* shifted letters -> upper case */
		return c - 128;
	if (c >= 97 && c <= 122)	/* shifted letters (alt. code) */
		return c - 32;
	return c;
}

char sys_getkey(void)
{
	char c = __asm {
		jsr $ffe4
		sta accu
	};
	if (!c)
		return 0;
	return petscii_to_ascii(c);
}

char sys_waitkey(void)
{
	char c;
	while (!(c = sys_getkey()))
		;
	return c;
}

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

bool sys_on_easyflash(void)
{
#ifdef OSCAR_TARGET_CRT_EASYFLASH
	return true;
#else
	return false;
#endif
}

void sys_debug_exit(char code)
{
	*(volatile char *)0xd7ff = code;
	for (;;)
		;
}
