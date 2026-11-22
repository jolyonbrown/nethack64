/*
 * host-s80.c - src/hal/screen80.h on the host, for tools/host-build.sh --video: the host
 * game draws through port/sys/c64/video.c, the C64's tty screen layer, and this keeps the
 * same 80x25 shadow (s80_text) the C64 has and mirrors each write to the terminal as ANSI
 * escapes, so tests/host_smoke.py can play the game through it as through termcap.
 */
#include <stdio.h>
#include <string.h>
#include "screen80.h"

char s80_text[S80_ROWS * S80_COLS];
char s80_cx, s80_cy;

static char s80_attr[S80_ROWS * S80_COLS];

/* the C64's colours as ANSI SGR codes (screen80.h's numbers) */
static const char *const ansi_fg[16] = {
	"30", "97", "31", "36", "35", "32", "34", "93",
	"33", "33", "91", "90", "37", "92", "94", "37"
};

/* where the terminal's cursor is and its colour, so that escapes go out only for a change and
 * text the game writes in a row reaches the terminal as one string (host_smoke.py matches
 * "--More--" and prompts in the output); tx < 0: not known */
static int tx = -1, ty, tattr = -1;

static void move(char x, char y)
{
	if (tx != x || ty != y)
		printf("\033[%d;%dH", y + 1, x + 1);
	tx = x;
	ty = y;
}

void s80_init(char fg, char bg)
{
	(void) fg;
	(void) bg;
	s80_clear();
}

void s80_clear(void)
{
	memset(s80_text, ' ', sizeof(s80_text));
	memset(s80_attr, 15, sizeof(s80_attr));
	s80_cx = s80_cy = 0;
	printf("\033[0m\033[2J\033[H");
	tx = ty = 0;
	tattr = 15;
}

void s80_putca(char x, char y, char c, char attr)
{
	if (x < 0 || x >= S80_COLS || y < 0 || y >= S80_ROWS)
		return;
	unsigned i = (unsigned) y * S80_COLS + x;
	s80_text[i] = c;
	s80_attr[i] = attr;
	move(x, y);
	if (tattr != attr)
		printf("\033[0;%s%sm", attr & S80_REVERSE ? "7;" : "", ansi_fg[attr & 15]);
	tattr = attr;
	putchar(c);
	tx = x + 1 < S80_COLS ? x + 1 : -1;	/* past the last column a terminal may wrap */
}

void s80_putc_at(char x, char y, char c)
{
	if (x < 0 || x >= S80_COLS || y < 0 || y >= S80_ROWS)
		return;
	s80_putca(x, y, c, s80_attr[(unsigned) y * S80_COLS + x]);
}

void s80_puts_at(char x, char y, const char *s)
{
	while (*s && x < S80_COLS)
		s80_putc_at(x++, y, *s++);
}

void s80_gotoxy(char x, char y)
{
	s80_cx = x;
	s80_cy = y;
}

void s80_putc(char c)
{
	if (c == '\n') {
		s80_cx = 0;
		if (s80_cy < S80_ROWS - 1)
			s80_cy++;
		return;
	}
	s80_putc_at(s80_cx, s80_cy, c);
	if (++s80_cx == S80_COLS)
		s80_putc('\n');
}

void s80_puts(const char *s)
{
	while (*s)
		s80_putc(*s++);
}

void s80_clear_eol(void)
{
	for (char x = s80_cx; x < S80_COLS; x++)
		s80_putca(x, s80_cy, ' ', 15);
}

void s80_color_cells(char x, char y, char w, char fg)
{
	for (; w > 0 && x < S80_COLS; x++, w--) {
		unsigned i = (unsigned) y * S80_COLS + x;
		s80_putca(x, y, s80_text[i], (s80_attr[i] & S80_REVERSE) | (fg & 15));
	}
}

void s80_invert(char x, char y)
{
	unsigned i = (unsigned) y * S80_COLS + x;
	s80_putca(x, y, s80_text[i], s80_attr[i] ^ S80_REVERSE);
}

