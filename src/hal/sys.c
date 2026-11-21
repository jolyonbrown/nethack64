#include "sys.h"

/* sys_reu_banks() is in reuprobe.c, shared with the C128 build (sys128.c) */

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
