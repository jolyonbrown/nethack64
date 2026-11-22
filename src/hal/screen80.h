/*
 * screen80.h - software 80x25 text screen on the VIC-II hires bitmap.
 *
 * Layout (VIC bank 3, so none of it costs main RAM below $C000):
 *   $CC00-$CFE7  colour matrix (fg/bg per 8x8 cell = per PAIR of columns)
 *   $E000-$FF3F  bitmap, under the KERNAL ROM (CPU writes go to RAM)
 *
 * Every character written is also kept in s80_text[], an 80x25 ASCII shadow
 * buffer.  Rendering never reads the bitmap (so the KERNAL can stay mapped),
 * and tools/vice.py reads s80_text through the VICE binary monitor to show
 * the screen as plain text - that is how agents "see" the 80-column display.
 *
 * Colour is per cell pair, a VIC-II hires limitation: two adjacent columns
 * share one foreground colour.  The NetHack window port will have to live
 * with (or cleverly exploit) that.
 */
#ifndef HAL_SCREEN80_H
#define HAL_SCREEN80_H

/* No includes: NetHack's sys/c64/video.c includes this, and mkstubs.py reads it through
 * gcc -E, where Oscar64's headers are not on the path. */

#define S80_COLS 80
#define S80_ROWS 25

#define S80_BITMAP   ((char *)0xe000)
#define S80_COLORMAP ((char *)0xcc00)

/* exported so the VICE harness can find it by label (s80_text) */
extern char s80_text[S80_ROWS * S80_COLS];
extern char s80_cx, s80_cy;		/* cursor position */

void s80_init(char fg, char bg);	/* switch VIC to the bitmap and clear */
void s80_clear(void);
void s80_putc_at(char x, char y, char c);
void s80_puts_at(char x, char y, const char *s);
void s80_gotoxy(char x, char y);
void s80_putc(char c);			/* teletype style, '\n' and wrap */
void s80_puts(const char *s);
void s80_clear_eol(void);
void s80_color_cells(char x, char y, char w, char fg);	/* w in columns */
void s80_invert(char x, char y);	/* toggle reverse video of one column */

/* A character and its attribute at once, for the window port's terminal layer: attr is a
 * colour (as s80_color_cells takes it) in bits 0-3, plus S80_REVERSE. On the C64 the colour
 * is the pair's (the VIC-II's limit), so it changes the neighbour's colour too. */
#define S80_REVERSE	0x80
void s80_putca(char x, char y, char c, char attr);

#endif
