/*
 * vdc80.c - the screen80.h text screen on the C128's 80-column chip (the VDC, 8563/8568),
 * for the C128 build (T2.13, ADR-0003 amendment of 2026-11-21).
 *
 * The VDC has its own RAM, reached only through two registers at $D600/$D601, so the screen
 * costs no main RAM beyond s80_text[], the same ASCII shadow as the C64's (tools/vice.py
 * reads it). Layout in VDC RAM, as the C128's KERNAL leaves it at reset: characters at
 * $0000, attributes at $0800, the character set at $2000 (16 bytes a glyph, 8 used). The set
 * is replaced by this project's font in ASCII order (tools/mkfont4x8.py --vdc), so a
 * character is its own code and the attributes' alternate-set bit stays clear.
 *
 * Colour is per character here (the C64's is per pair of columns); screen80.h's C64 colour
 * numbers are mapped to the VDC's RGBI ones. Reverse video is the attribute's bit 6.
 * Every register access waits for the VDC's ready bit (bit 7 of $D600), and the I/O must
 * be in (the MMU at $3E or $3A): built with HAL_IO_OUT (the banked game, whose MMU is at
 * $3B) each function switches it in and back (io128.h).
 * Built with S80_NO_SHADOW (the game, whose main RAM is short) there is no s80_text[]: the
 * screen is only in the VDC's RAM, which tools/vice.py reads through the VDC's registers.
 */
#include "screen80.h"
#include "fontvdc.h"
#include "io128.h"
#include <string.h>

#ifndef S80_NO_SHADOW
char s80_text[S80_ROWS * S80_COLS];
#define SHADOW(stmt)	stmt
#else
#define SHADOW(stmt)
#endif
char s80_cx, s80_cy;

#define VDC_REG		(*(volatile char *)0xd600)
#define VDC_DATA	(*(volatile char *)0xd601)

#define VDC_SCREEN	0x0000u
#define VDC_ATTR	0x0800u
#define VDC_CHARS	0x2000u

#define ATTR_REVERSE	0x40

/* the C64's colours as RGBI: black, white, red, cyan, purple, green, blue, yellow, orange,
 * brown, light red, dark grey, grey, light green, light blue, light grey */
static const char rgbi[16] = { 0, 15, 8, 7, 10, 4, 2, 13, 12, 12, 9, 1, 14, 5, 3, 14 };

static char attr_fg = 15;

static void vdc_wr(char r, char v)
{
	VDC_REG = r;
	while (!(VDC_REG & 0x80))
		;
	VDC_DATA = v;
}

static char vdc_rd(char r)
{
	VDC_REG = r;
	while (!(VDC_REG & 0x80))
		;
	return VDC_DATA;
}

/* the update address: the next R31 read or write goes there, and it then moves on */
static void vdc_at(unsigned a)
{
	vdc_wr(18, a >> 8);
	vdc_wr(19, a & 0xff);
}

/* n bytes of v from a: one write, then the VDC's block write for the rest */
static void vdc_fill(unsigned a, char v, unsigned n)
{
	vdc_wr(24, vdc_rd(24) & 0x7f);
	while (n)
	{
		unsigned k = n > 255 ? 255 : n;
		vdc_at(a);
		vdc_wr(31, v);
		if (k > 1)
			vdc_wr(30, (char)(k - 1));
		a += k;
		n -= k;
	}
}

/* n bytes from src to dst, by the VDC's block copy (dst below src) */
static void vdc_copy(unsigned dst, unsigned src, unsigned n)
{
	vdc_wr(24, vdc_rd(24) | 0x80);
	while (n)
	{
		unsigned k = n > 255 ? 255 : n;
		vdc_at(dst);
		vdc_wr(32, src >> 8);
		vdc_wr(33, src & 0xff);
		vdc_wr(30, (char)k);
		dst += k;
		src += k;
		n -= k;
	}
	vdc_wr(24, vdc_rd(24) & 0x7f);
}

void s80_init(char fg, char bg)
{
	IO_IN();
	vdc_wr(12, VDC_SCREEN >> 8);			/* display start */
	vdc_wr(13, VDC_SCREEN & 0xff);
	vdc_wr(20, VDC_ATTR >> 8);			/* attribute start */
	vdc_wr(21, VDC_ATTR & 0xff);
	vdc_wr(28, (vdc_rd(28) & 0x1f) | (VDC_CHARS >> 8));	/* the set at $2000, RAM size kept */
	vdc_wr(25, vdc_rd(25) | 0x40);			/* attributes on */

	/* the font: 256 glyphs of 16 bytes, ASCII 32..127 from fontvdc[], the rest blank */
	vdc_at(VDC_CHARS);
	for (unsigned c = 0; c < 256; c++)
	{
		const char *g = (c >= 32 && c < 128) ? fontvdc + ((c - 32) << 3) : 0;
		for (char r = 0; r < 8; r++)
			vdc_wr(31, g ? g[r] : 0);
		for (char r = 0; r < 8; r++)
			vdc_wr(31, 0);
	}

	attr_fg = rgbi[fg & 15];
	vdc_wr(26, (attr_fg << 4) | rgbi[bg & 15]);	/* foreground (unused with attributes), background */
	s80_clear();
	IO_OUT();
}

void s80_clear(void)
{
	IO_IN();
	vdc_fill(VDC_SCREEN, ' ', S80_ROWS * S80_COLS);
	vdc_fill(VDC_ATTR, attr_fg, S80_ROWS * S80_COLS);
	IO_OUT();
	SHADOW(memset(s80_text, ' ', S80_ROWS * S80_COLS));
	s80_cx = s80_cy = 0;
}

void s80_putc_at(char x, char y, char c)
{
	unsigned i = (unsigned)y * S80_COLS + x;
	SHADOW(s80_text[i] = c);
	IO_IN();
	vdc_at(VDC_SCREEN + i);
	vdc_wr(31, c);
	IO_OUT();
}

void s80_puts_at(char x, char y, const char *s)
{
	unsigned i = (unsigned)y * S80_COLS + x;
	IO_IN();
	vdc_at(VDC_SCREEN + i);
	while (*s && i < S80_ROWS * S80_COLS)
	{
		SHADOW(s80_text[i] = *s);
		i++;
		vdc_wr(31, *s++);
	}
	IO_OUT();
}

void s80_gotoxy(char x, char y)
{
	s80_cx = x;
	s80_cy = y;
}

static void scroll(void)
{
	IO_IN();
	vdc_copy(VDC_SCREEN, VDC_SCREEN + S80_COLS, (S80_ROWS - 1) * S80_COLS);
	vdc_copy(VDC_ATTR, VDC_ATTR + S80_COLS, (S80_ROWS - 1) * S80_COLS);
	vdc_fill(VDC_SCREEN + (S80_ROWS - 1) * S80_COLS, ' ', S80_COLS);
	vdc_fill(VDC_ATTR + (S80_ROWS - 1) * S80_COLS, attr_fg, S80_COLS);
	IO_OUT();
	SHADOW(memmove(s80_text, s80_text + S80_COLS, (S80_ROWS - 1) * S80_COLS));
	SHADOW(memset(s80_text + (S80_ROWS - 1) * S80_COLS, ' ', S80_COLS));
}

static void newline(void)
{
	s80_cx = 0;
	if (++s80_cy >= S80_ROWS)
	{
		s80_cy = S80_ROWS - 1;
		scroll();
	}
}

void s80_putc(char c)
{
	if (c == '\n')
	{
		newline();
		return;
	}
	s80_putc_at(s80_cx, s80_cy, c);
	if (++s80_cx >= S80_COLS)
		newline();
}

void s80_puts(const char *s)
{
	while (*s)
		s80_putc(*s++);
}

void s80_clear_eol(void)
{
	unsigned i = (unsigned)s80_cy * S80_COLS + s80_cx;
	char n = S80_COLS - s80_cx;
	SHADOW(memset(s80_text + i, ' ', n));
	IO_IN();
	vdc_fill(VDC_SCREEN + i, ' ', n);
	IO_OUT();
}

void s80_color_cells(char x, char y, char w, char fg)
{
	if (w)
	{
		IO_IN();
		vdc_fill(VDC_ATTR + (unsigned)y * S80_COLS + x, rgbi[fg & 15], w);
		IO_OUT();
	}
}

void s80_invert(char x, char y)
{
	unsigned a = VDC_ATTR + (unsigned)y * S80_COLS + x;
	IO_IN();
	vdc_at(a);
	char v = vdc_rd(31);
	vdc_at(a);
	vdc_wr(31, v ^ ATTR_REVERSE);
	IO_OUT();
}

void s80_putca(char x, char y, char c, char attr)
{
	if (x >= S80_COLS || y >= S80_ROWS)
		return;
	unsigned i = (unsigned)y * S80_COLS + x;
	SHADOW(s80_text[i] = c);
	IO_IN();
	vdc_at(VDC_SCREEN + i);
	vdc_wr(31, c);
	vdc_at(VDC_ATTR + i);
	vdc_wr(31, rgbi[attr & 15] | (attr & S80_REVERSE ? ATTR_REVERSE : 0));
	IO_OUT();
}
