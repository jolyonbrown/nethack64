/*	video.c	NetHack 3.4.3 for the Commodore 64 and C128 (Oscar64)	*/
/* NetHack may be freely redistributed.  See license for details. */

/*
 * The tty window port's screen layer without termcap (NO_TERMS), as
 * sys/msdos/video.c is for MS-DOS: wintty.c, topl.c and getline.c draw
 * through these functions, and wintty.h maps their putchar/puts to xputc
 * and xputs.  Underneath is the 80x25 screen of src/hal/screen80.h: the
 * VIC-II bitmap on a C64, the VDC on a C128, and a shadow buffer on the
 * host (tools/host-build.sh --video), where the same code is tested.
 *
 * As on MS-DOS, xputc() writes at the screen's own cursor and moves it on
 * (stopping at the last column), and leaves ttyDisplay->curx to wintty.c,
 * which keeps it itself; cmov() moves both.
 *
 * Attributes: the tty port asks for bold, underline, blink and inverse
 * (term_start_attr) and NetHack's 16 colours (term_start_color).  The
 * screen has 16 colours and reverse video: inverse and standout are
 * reverse, bold, underline and blink are white.  On a C64 two neighbouring
 * columns share a colour (screen80.h).
 */

#include "hack.h"

#if defined(TTY_GRAPHICS) && defined(S80_VIDEO)

#include "wintty.h"
#include "screen80.h"

/* NetHack's colours as the screen's (C64 colour numbers, screen80.h): black
 * is dark grey, so that it shows on the black background */
static const char nh_to_s80[CLR_MAX] = {
	11,	/* CLR_BLACK: dark grey */
	2,	/* CLR_RED */
	5,	/* CLR_GREEN */
	9,	/* CLR_BROWN */
	6,	/* CLR_BLUE */
	4,	/* CLR_MAGENTA: purple */
	3,	/* CLR_CYAN */
	15,	/* CLR_GRAY: light grey */
	15,	/* NO_COLOR */
	8,	/* CLR_ORANGE */
	13,	/* CLR_BRIGHT_GREEN */
	7,	/* CLR_YELLOW */
	14,	/* CLR_BRIGHT_BLUE */
	10,	/* CLR_BRIGHT_MAGENTA: light red */
	3,	/* CLR_BRIGHT_CYAN: cyan, there is no light cyan */
	1	/* CLR_WHITE */
};

#define ATTR_NORMAL	15			/* light grey, as s80_init(15, 0) */
#define ATTR_BRIGHT	1			/* white */

static char attr = ATTR_NORMAL;

void
tty_startup(int *wid, int *hgt)
{
	LI = S80_ROWS;
	CO = S80_COLS;
	*wid = CO;
	*hgt = LI;
	attr = ATTR_NORMAL;
}

void
tty_start_screen(void)
{
	s80_clear();
}

void
tty_end_screen(void)
{
	s80_clear();
}

void
tty_number_pad(int state)
{
	(void) state;
}

void
tty_nhbell(void)
{
	/* no bell yet */
}

void
tty_delay_output(void)
{
	/* the screen is drawn as it is written: nothing to wait for */
}

void
xputc(CHAR_P c)
{
	if (c == '\n')
		return;
	s80_putca(s80_cx, s80_cy, (char) c, attr);
	if (s80_cx < S80_COLS - 1)
		s80_cx++;
}

void
xputs(const char *s)
{
	while (*s)
		xputc(*s++);
}

/* puts() for the tty port's raw prints (tty_raw_print: the start-up and panic messages):
 * the string, then the start of the next row, as C's puts() ends its line; a '\r' or '\n'
 * inside moves the cursor too ("\r\nOops...").  xputc() leaves both to cmov(), as
 * MS-DOS's does, whose raw prints went to the console instead (msmsg): without this every
 * raw print overwrote the last on one row and "\r" showed as a character. */
static void
xnewline(void)
{
	s80_cx = 0;
	if (s80_cy < S80_ROWS - 1)
		s80_cy++;
}

void
xputline(const char *s)
{
	for (; *s; s++) {
		if (*s == '\r')
			s80_cx = 0;
		else if (*s == '\n')
			xnewline();
		else
			xputc(*s);
	}
	xnewline();
}

void
cmov(int x, int y)
{
	ttyDisplay->curx = (uchar) x;
	ttyDisplay->cury = (uchar) y;
	s80_gotoxy((char) x, (char) y);
}

void
nocmov(int x, int y)
{
	s80_gotoxy((char) x, (char) y);
}

void
home(void)
{
	tty_curs(BASE_WINDOW, 1, 0);
	ttyDisplay->curx = ttyDisplay->cury = 0;
	s80_gotoxy(0, 0);
}

void
backsp(void)
{
	if (s80_cx > 0)
		s80_cx--;
}

/* to the end of the line, in the normal attribute */
static void
clear_line_from(char x, char y)
{
	for (; x < S80_COLS; x++)
		s80_putca(x, y, ' ', ATTR_NORMAL);
}

void
cl_end(void)
{
	clear_line_from((char) ttyDisplay->curx, (char) ttyDisplay->cury);
	tty_curs(BASE_WINDOW, (int) ttyDisplay->curx + 1, (int) ttyDisplay->cury);
}

void
cl_eos(void)
{
	char y = (char) ttyDisplay->cury;

	clear_line_from((char) ttyDisplay->curx, y);
	while (++y < S80_ROWS)
		clear_line_from(0, y);
	tty_curs(BASE_WINDOW, (int) ttyDisplay->curx + 1, (int) ttyDisplay->cury);
}

void
clear_screen(void)
{
	s80_clear();
	home();
}

void
standoutbeg(void)
{
	attr |= S80_REVERSE;
}

void
standoutend(void)
{
	attr = ATTR_NORMAL;
}

void
graph_on(void)
{
}

void
graph_off(void)
{
}

void
term_start_attr(int a)
{
	switch (a) {
	case ATR_INVERSE:
		attr |= S80_REVERSE;
		break;
	case ATR_BOLD:
	case ATR_ULINE:
	case ATR_BLINK:
		attr = (attr & S80_REVERSE) | ATTR_BRIGHT;
		break;
	default:
		break;
	}
}

void
term_end_attr(int a)
{
	(void) a;
	attr = ATTR_NORMAL;
}

void
term_start_raw_bold(void)
{
	term_start_attr(ATR_BOLD);
}

void
term_end_raw_bold(void)
{
	attr = ATTR_NORMAL;
}

void
term_start_color(int color)
{
	if (color >= 0 && color < CLR_MAX)
		attr = (attr & S80_REVERSE) | nh_to_s80[color];
}

void
term_end_color(void)
{
	attr = ATTR_NORMAL;
}

int
has_color(int color)
{
	(void) color;
	return 1;
}

#endif /* TTY_GRAPHICS && S80_VIDEO */
