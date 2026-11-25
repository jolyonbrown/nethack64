/*
 * sys128.c - sys.h on a C128 in its own mode (T2.13, ADR-0003 amendment of 2026-11-21).
 *
 * The program runs with the MMU at $3E (all RAM, I/O in) and interrupts off: no KERNAL ROM
 * is mapped, so nothing of the KERNAL runs. Keys come from two places:
 * - the KERNAL's keyboard buffer (KEYD at $034A, its count NDX at $D0), which nothing here
 *   fills but which VICE's monitor feeds (tools/vice.py keys), read as the KERNAL's GETIN
 *   would, in PETSCII;
 * - a scan of the keyboard matrix through CIA 1, the 64 keys the C64 has (the C128's extra
 *   keys, on $D02F's lines, are not read yet), a key counted when it goes down.
 * sys_reu_banks() is reuprobe.c's. The debug cartridge's $D7FF is VICE's in C128 mode too.
 * Built with HAL_IO_OUT (the banked game) it leaves the MMU as it finds it and switches the
 * I/O in only around the CIA and $D7FF (io128.h).
 */
#include "sys.h"
#include "io128.h"

#define CIA1_PRA	(*(volatile char *)0xdc00)
#define CIA1_PRB	(*(volatile char *)0xdc01)
#define CIA1_DDRA	(*(volatile char *)0xdc02)
#define CIA1_DDRB	(*(volatile char *)0xdc03)

#define KEYD		((volatile char *)0x034a)
#define NDX			(*(volatile char *)0x00d0)

void sys_init(void)
{
	__asm { sei }
#ifndef HAL_IO_OUT
	*(volatile char *)0xff00 = 0x3e;	/* bank 0, all RAM, I/O in */
#endif
	IO_IN();							/* the game: the MMU as the bank glue set it */
	CIA1_DDRA = 0xff;					/* columns out */
	CIA1_DDRB = 0x00;					/* rows in */
	IO_OUT();
}

/* PETSCII from the buffer: as sys.c's table (cursor keys as vi-keys, RETURN as '\n') */
/* PETSCII 95, the left-arrow key, is not here: it stays '_' (travel), the only way to type
 * '_' on a C64, as the C128's matrix scan gives it; RUN/STOP is ESC (docs/TO-DECIDE.md, 2026-11-25) */
static const char key_from[] = { 13,   20, 3,  17,  145, 29,  157, 0 };
static const char key_to[]   = { '\n', 8,  27, 'j', 'k', 'l', 'h' };

static char petscii_to_ascii(char c)
{
	for (char i = 0; key_from[i]; i++)
		if (key_from[i] == c)
			return key_to[i];
	if (c >= 65 && c <= 90)
		return c + 32;
	if (c >= 193 && c <= 218)
		return c - 128;
	if (c >= 97 && c <= 122)
		return c - 32;
	return c;
}

/* The matrix: column i is selected by a 0 in bit i of $DC00, row j read in bit j of $DC01.
 * Unshifted and shifted ASCII for each key; 0 for none, 1 for the shift keys, 2 for CTRL,
 * 3 for C=. RUN/STOP is ESC; the cursor keys are vi-keys, the shifted ones too. */
static const char keys_plain[64] = {
	8, '\n', 'l', 0, 0, 0, 0, 'j',				/* DEL RETURN CRSR-RT F7 F1 F3 F5 CRSR-DN */
	'3', 'w', 'a', '4', 'z', 's', 'e', 1,		/* LSHIFT */
	'5', 'r', 'd', '6', 'c', 'f', 't', 'x',
	'7', 'y', 'g', '8', 'b', 'h', 'u', 'v',
	'9', 'i', 'j', '0', 'm', 'k', 'o', 'n',
	'+', 'p', 'l', '-', '.', ':', '@', ',',
	'#', '*', ';', 0, 1, '=', '^', '/',			/* pound HOME RSHIFT up-arrow */
	'1', '_', 2, '2', ' ', 3, 'q', 27			/* left-arrow CTRL C= RUN/STOP */
};
static const char keys_shift[64] = {
	8, '\n', 'h', 0, 0, 0, 0, 'k',
	'#', 'W', 'A', '$', 'Z', 'S', 'E', 1,
	'%', 'R', 'D', '&', 'C', 'F', 'T', 'X',
	'\'', 'Y', 'G', '(', 'B', 'H', 'U', 'V',
	')', 'I', 'J', '0', 'M', 'K', 'O', 'N',
	'+', 'P', 'L', '-', '>', '[', '@', '<',
	'#', '*', ']', 0, 1, '=', '^', '?',
	'!', '_', 2, '"', ' ', 3, 'Q', 27
};

static char was_down[8];

static char scan(void)
{
	char down[8], shift = 0, ctrl = 0, hit = 0xff;

	IO_IN();
	for (char i = 0; i < 8; i++)
	{
		CIA1_PRA = ~(1 << i);
		down[i] = ~CIA1_PRB;
	}
	CIA1_PRA = 0xff;
	IO_OUT();
	if (down[1] & 0x80 || down[6] & 0x10)
		shift = 1;
	if (down[7] & 0x04)
		ctrl = 1;
	for (char i = 0; i < 8; i++)
	{
		char fresh = down[i] & ~was_down[i];
		was_down[i] = down[i];
		for (char j = 0; j < 8 && hit == 0xff; j++)
			if (fresh & (1 << j))
			{
				char k = keys_plain[i * 8 + j];
				if (k > 3)
					hit = i * 8 + j;
			}
	}
	if (hit == 0xff)
		return 0;
	char c = (shift ? keys_shift : keys_plain)[hit];
	if (ctrl && c >= 'a' && c <= 'z')
		c -= 'a' - 1;
	return c;
}

char sys_getkey(void)
{
	if (NDX)
	{
		char c = KEYD[0];
		char n = NDX - 1;
		for (char i = 0; i < n; i++)
			KEYD[i] = KEYD[i + 1];
		NDX = n;
		return petscii_to_ascii(c);
	}
	return scan();
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
	return false;
}

void sys_debug_exit(char code)
{
	IO_IN();
	*(volatile char *)0xd7ff = code;
	for (;;)
		;
}
