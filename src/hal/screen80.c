#include "screen80.h"
#include "font4x8.h"
#include <c64/vic.h>
#include <string.h>

char s80_text[S80_ROWS * S80_COLS];
char s80_cx, s80_cy;

/* inverse-video flags, one bit per column, so the shadow stays pure text */
static char s80_inv[S80_ROWS * S80_COLS / 8];

/* row start offsets into the bitmap (row * 320) */
static unsigned s80_rowofs[S80_ROWS];

static const char *glyph(char c)
{
	if (c < 32 || c > 127)
		c = '?';
	return font4x8 + ((unsigned)(c - 32) << 3);
}

static bool is_inv(unsigned i)
{
	return (s80_inv[i >> 3] & (1 << (i & 7))) != 0;
}

/* Re-render the 8x8 cell holding columns 2*cx and 2*cx+1 of row y. */
static void draw_pair(char cx, char y)
{
	unsigned i = (unsigned)y * S80_COLS + (cx << 1);
	const char *l = glyph(s80_text[i]);
	const char *r = glyph(s80_text[i + 1]);
	char lm = is_inv(i) ? 0xf0 : 0x00;
	char rm = is_inv(i + 1) ? 0x0f : 0x00;
	char *dst = S80_BITMAP + s80_rowofs[y] + ((unsigned)cx << 3);

	for (char k = 0; k < 8; k++)
		dst[k] = (((l[k] & 0xf0) | (r[k] & 0x0f)) ^ (lm | rm));
}

void s80_init(char fg, char bg)
{
	for (char y = 0; y < S80_ROWS; y++)
		s80_rowofs[y] = (unsigned)y * 320;

	memset(S80_COLORMAP, (fg << 4) | bg, 1000);
	vic_setmode(VICM_HIRES, S80_COLORMAP, S80_BITMAP);
	vic.color_border = bg;
	s80_clear();
}

void s80_clear(void)
{
	memset(s80_text, ' ', sizeof(s80_text));
	memset(s80_inv, 0, sizeof(s80_inv));
	memset(S80_BITMAP, 0, 8000);
	s80_cx = s80_cy = 0;
}

void s80_putc_at(char x, char y, char c)
{
	if (x >= S80_COLS || y >= S80_ROWS)
		return;
	s80_text[(unsigned)y * S80_COLS + x] = c;
	draw_pair(x >> 1, y);
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

static void scroll_up(void)
{
	memmove(s80_text, s80_text + S80_COLS, (S80_ROWS - 1) * S80_COLS);
	memset(s80_text + (S80_ROWS - 1) * S80_COLS, ' ', S80_COLS);
	memmove(s80_inv, s80_inv + S80_COLS / 8, (S80_ROWS - 1) * S80_COLS / 8);
	memset(s80_inv + (S80_ROWS - 1) * S80_COLS / 8, 0, S80_COLS / 8);
	/* the bitmap is write-only from our side: redraw everything */
	for (char y = 0; y < S80_ROWS; y++)
		for (char cx = 0; cx < S80_COLS / 2; cx++)
			draw_pair(cx, y);
}

void s80_putc(char c)
{
	if (c == '\n')
	{
		s80_cx = 0;
		if (++s80_cy == S80_ROWS)
		{
			scroll_up();
			s80_cy = S80_ROWS - 1;
		}
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
		s80_putc_at(x, s80_cy, ' ');
}

void s80_color_cells(char x, char y, char w, char fg)
{
	char *cm = S80_COLORMAP + (unsigned)y * 40 + (x >> 1);
	char n = (w + (x & 1) + 1) >> 1;
	for (char i = 0; i < n; i++)
		cm[i] = (cm[i] & 0x0f) | (fg << 4);
}

void s80_invert(char x, char y)
{
	unsigned i = (unsigned)y * S80_COLS + x;
	s80_inv[i >> 3] ^= 1 << (i & 7);
	draw_pair(x >> 1, y);
}
