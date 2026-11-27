/*
 * sys128.c - sys.h on a C128 in its own mode (T2.13, ADR-0003 amendment of 2026-11-21).
 *
 * The program runs with the MMU at $3E (all RAM, I/O in) and interrupts off: no KERNAL ROM
 * is mapped, so nothing of the KERNAL runs. Keys come from two places:
 * - the KERNAL's keyboard buffer (KEYD at $034A, its count NDX at $D0), which nothing here
 *   fills but which VICE's monitor feeds (tools/vice.py keys), read as the KERNAL's GETIN
 *   would, in PETSCII;
 * - a scan of the keyboard matrix through CIA 1 and the VIC's $D02F, the C64's 64 keys and
 *   the C128's 24 more, a key counted when it goes down;
 * - a joystick in port 2.
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
#define CIA1_TBLO	(*(volatile char *)0xdc06)
#define CIA1_TBHI	(*(volatile char *)0xdc07)
#define CIA1_CRB	(*(volatile char *)0xdc0f)
#define VIC_KEYS	(*(volatile char *)0xd02f)	/* the C128's extra keyboard lines K0-K2 */
#define VIC_CLKRATE	(*(volatile char *)0xd030)	/* bit 0: the CPU at 2 MHz */

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
	VIC_KEYS = 0xff;					/* no extra line selected */
	IO_OUT();
}

/* The CPU at 2 MHz (fast != 0) or 1 MHz. The game runs at 2 MHz: it draws on the VDC, so the
 * VIC-II's 40 columns, which show nothing useful at 2 MHz, are not missed; the CIAs' timers
 * count at 1 MHz whatever the CPU's clock (settle()). Each REU transfer drops to 1 MHz for its DMA
 * (tools/bank/bankgen.py, tools/bank/farrt.py, port/sys/c64/c64sys.c): "The C128 MUST be in
 * 1 Mhz (SLOW) mode when a DMA is requested" (1750 clone user's guide, HARDWARE.md). */
void sys128_speed(char fast)
{
	IO_IN();
	VIC_CLKRATE = fast ? 0x01 : 0x00;
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
static const char keys_plain[88] = {
	8, '\n', 'l', 0, 0, 0, 0, 'j',				/* DEL RETURN CRSR-RT F7 F1 F3 F5 CRSR-DN */
	'3', 'w', 'a', '4', 'z', 's', 'e', 1,		/* LSHIFT */
	'5', 'r', 'd', '6', 'c', 'f', 't', 'x',
	'7', 'y', 'g', '8', 'b', 'h', 'u', 'v',
	'9', 'i', 'j', '0', 'm', 'k', 'o', 'n',
	'+', 'p', 'l', '-', '.', ':', '@', ',',
	'#', '*', ';', 0, 1, '=', '^', '/',			/* pound HOME RSHIFT up-arrow */
	'1', '_', 2, '2', ' ', 3, 'q', 27,			/* left-arrow CTRL C= RUN/STOP */
	/* the C128's extra keys as columns 8-10, selected by bits 0-2 of $D02F (VICE's
	 * C128/gtk3_sym.vkm). The keypad moves as a PC keypad does, whatever the game's
	 * number_pad option, 5 searching; ESC is ESC, HELP '?', the cursor keys above the
	 * keypad as the C64's; ALT and NO SCROLL nothing */
	'?', 'k', 's', '\t', 'j', 'h', 'y', 'b',		/* HELP KP8 KP5 TAB KP2 KP4 KP7 KP1 */
	27, '+', '-', '\n', '\n', 'l', 'u', 'n',		/* ESC KP+ KP- LINEFEED ENTER KP6 KP9 KP3 */
	0, '0', '.', 'k', 'j', 'h', 'l', 0			/* ALT KP0 KP. UP DOWN LEFT RIGHT NOSCROLL */
};
static const char keys_shift[88] = {
	8, '\n', 'h', 0, 0, 0, 0, 'k',
	'#', 'W', 'A', '$', 'Z', 'S', 'E', 1,
	'%', 'R', 'D', '&', 'C', 'F', 'T', 'X',
	'\'', 'Y', 'G', '(', 'B', 'H', 'U', 'V',
	')', 'I', 'J', '0', 'M', 'K', 'O', 'N',
	'+', 'P', 'L', '-', '>', '[', '@', '<',
	'#', '*', ']', 0, 1, '=', '^', '?',
	'!', '_', 2, '"', ' ', 3, 'Q', 27,
	/* shifted, a move is the shifted (rush) one; KP5 still 's', not 'S' (save) */
	'?', 'K', 's', '\t', 'J', 'H', 'Y', 'B',
	27, '+', '-', '\n', '\n', 'L', 'U', 'N',
	0, '0', '.', 'K', 'J', 'H', 'L', 0
};

/* A joystick in port 2 (Jolyon, 2026-11-26: the usual games port; a stick in port 1 is on the
 * keyboard's row lines and types keys). Its eight directions are the eight moves; fire held
 * with a direction gives the shifted (rush) move, and fire on its own 's' (search) when it is
 * let go without a move. A push counts once: no repeat, since a stick held up-left would
 * answer a "Really attack?" with 'y'. Indexed by up, down, left, right in bits 0-3. */
static const char joy_keys[16] = { 0, 'k', 'j', 0, 'h', 'y', 'b', 0, 'l', 'u', 'n', 0, 0, 0, 0, 0 };

static char was_down[11], joy_was, fire_moved;

/* What a scan gives: down[] the matrix's eleven columns (a bit for each key down), joy port
 * 2's five lines (1 = pushed or pressed). The keyboard is skipped while the stick is pushed or
 * fire pressed: it pulls column lines low, so keys held then read in the wrong columns. */
static char decode(const char *down, char joy)
{
	if (joy != joy_was)
	{
		char c = 0, dir = joy & 15;
		if (joy & 16 && !(joy_was & 16))
			fire_moved = 0;
		if (dir && dir != (joy_was & 15))
		{
			c = joy_keys[dir];
			if (joy & 16)
			{
				fire_moved = 1;
				if (c)
					c -= 'a' - 'A';
			}
		}
		else if (!dir && !(joy & 16) && joy_was & 16 && !fire_moved)
			c = 's';
		joy_was = joy;
		if (c)
			return c;
	}
	if (joy)
		return 0;

	char shift = 0, ctrl = 0, hit = 0xff;
	if (down[1] & 0x80 || down[6] & 0x10)
		shift = 1;
	if (down[7] & 0x04)
		ctrl = 1;
	for (char i = 0; i < 11; i++)
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

/* about 30 ms on CIA 1's timer B, one shot (nothing else uses it: no KERNAL runs), for a
 * stick's contacts to settle: up-left closes up and left a moment apart */
static void settle(void)
{
	CIA1_TBLO = 0x30;
	CIA1_TBHI = 0x75;
	CIA1_CRB = 0x19;					/* force load, one shot, start */
	while (CIA1_CRB & 1)
		;
}

static char scan(void)
{
	char down[11], joy;

	IO_IN();
	CIA1_PRA = 0xff;					/* no column: the port's own lines */
	joy = ~CIA1_PRA & 0x1f;
	if (joy != joy_was)
	{
		settle();
		joy = ~CIA1_PRA & 0x1f;
	}
	for (char i = 0; i < 8; i++)
	{
		CIA1_PRA = ~(1 << i);
		down[i] = ~CIA1_PRB;
	}
	CIA1_PRA = 0xff;
	for (char i = 0; i < 3; i++)
	{
		VIC_KEYS = ~(1 << i);
		down[8 + i] = ~CIA1_PRB;
	}
	VIC_KEYS = 0xff;
	IO_OUT();
	return decode(down, joy);
}

#ifdef AUTOTEST
char sys128_decode(const char *down, char joy)	/* src/main.c's self-test */
{
	return decode(down, joy);
}
#endif

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
