/*	c64scanf.c	NetHack 3.4.3 for the Commodore 64 (Oscar64)	*/
/* NetHack may be freely redistributed.  See license for details. */

/*
 * sscanf() and fscanf() for the C64 build (c64conf.h renames NetHack's calls to these).
 *
 * Oscar64's own (stdio.c's fpscanf) also parses floats, and with the float routines it
 * brings is about 3.2 KB of resident code (T2.12, docs/RAM-PLAN.md); NetHack reads only
 * integers, characters, strings and scan sets: the record file (topten.c), the rumour,
 * oracle and help indexes (rumors.c, pager.c), a bribe and a level number typed in
 * (minion.c, cmd.c).  This does what ISO C says for the conversions those use: %d, %u
 * and %x with h or l, %c, %s, %[...] and %[^...], each with a width and *, %%, literal
 * characters, and white space, which matches any amount of white space.  Unlike
 * fpscanf it does not read a character past what it matched: one it only looked at goes
 * back with ungetc(), so consecutive fscanf() calls see every character (topten.c reads
 * a record with three).
 */

#include <stdio.h>
#include <stdarg.h>

#ifndef EOF
#define EOF (-1)
#endif

int nh_sscanf(const char *, const char *, ...);
int nh_fscanf(FILE *, const char *, ...);
static int sc_scan(const char *, const char *, FILE *, va_list);
#ifdef __OSCAR64C__
int ungetc(int, FILE *);	/* Oscar64's stdio.h has none: the file layer's */
#endif

static FILE *sc_fp;		/* reading this file, or */
static const char *sc_str;	/* this string */
static int sc_c;		/* the character looked at, EOF at the end */
static char sc_have;		/* sc_c is looked at, not yet taken */

static int
sc_peek(void)
{
	if (!sc_have) {
		sc_have = 1;
		if (sc_fp)
			sc_c = fgetc(sc_fp);
		else if (*sc_str)
			sc_c = (unsigned char) *sc_str++;
		else
			sc_c = EOF;
	}
	return sc_c;
}

static int
sc_space(int c)
{
	return c == ' ' || (c >= '\t' && c <= '\r');
}

static void
sc_skipspace(void)
{
	while (sc_space(sc_peek()))
		sc_have = 0;
}

/* In a bank (the plan's "va_list_banked", bankgen.py): what ap holds are pointers to the
 * caller's variables, in near RAM, and fmt and str come through the trampoline, which
 * copies them out of the caller's bank. */
static int
sc_scan(const char *fmt, const char *str, FILE *fp, va_list ap)
{
	int n = 0, c;
	char f, eof = 0;

	sc_fp = fp;
	sc_str = str;
	sc_have = 0;
	while ((f = *fmt++) != 0) {
		char skip = 0, size = 0, neg = 0, any = 0;
		unsigned width = 0;
		const char *set = 0, *end = 0;

		if (sc_space(f)) {
			sc_skipspace();
			continue;
		}
		if (f != '%' || (f = *fmt++) == '%') {
			if (sc_peek() != (unsigned char) f) {
				eof = sc_c == EOF;
				break;
			}
			sc_have = 0;
			continue;
		}
		if (f == '*') {
			skip = 1;
			f = *fmt++;
		}
		while (f >= '0' && f <= '9') {
			width = width * 10 + (f - '0');
			f = *fmt++;
		}
		if (f == 'h' || f == 'l') {
			size = f;
			f = *fmt++;
		}
		if (!width)
			width = f == 'c' ? 1 : 0xffff;
		if (f == 'd' || f == 'u' || f == 'x') {
			unsigned long v = 0;
			unsigned char base = f == 'x' ? 16 : 10;

			sc_skipspace();
			c = sc_peek();
			if (c == '-' || c == '+') {
				neg = c == '-';
				any = 2;	/* taken, but not yet a number */
				sc_have = 0;
				width--;
			}
			for (; width; width--) {
				c = sc_peek();
				if (c >= '0' && c <= '9')
					c -= '0';
				else if (base == 16 && (c | 0x20) >= 'a' && (c | 0x20) <= 'f')
					c = (c | 0x20) - 'a' + 10;
				else
					break;
				v = v * base + c;
				any = 1;
				sc_have = 0;
			}
			if (any != 1) {
				eof = !any && sc_c == EOF;
				break;
			}
			if (neg)
				v = -v;
			if (!skip) {
				if (size == 'l')
					*va_arg(ap, long *) = (long) v;
				else if (size == 'h')
					*va_arg(ap, short *) = (short) v;
				else
					*va_arg(ap, int *) = (int) v;
				n++;
			}
		} else if (f == 'c' || f == 's' || f == '[') {
			char *p = skip ? 0 : va_arg(ap, char *);

			if (f == 's')
				sc_skipspace();
			else if (f == '[') {
				if (*fmt == '^') {
					neg = 1;
					fmt++;
				}
				set = fmt;
				if (*fmt == ']')
					fmt++;	/* a ']' first is in the set */
				while (*fmt && *fmt != ']')
					fmt++;
				end = fmt;
				if (*fmt)
					fmt++;
			}
			for (; width; width--) {
				c = sc_peek();
				if (c == EOF || (f == 's' && sc_space(c)))
					break;
				if (set) {
					const char *q = set;

					while (q < end && (unsigned char) *q != c)
						q++;
					if ((q < end) == neg)
						break;
				}
				if (p)
					*p++ = (char) c;
				any = 1;
				sc_have = 0;
			}
			if (!any) {
				eof = sc_c == EOF;
				break;
			}
			if (p) {
				if (f != 'c')
					*p = 0;
				n++;
			}
		} else
			break;		/* a conversion NetHack does not use */
	}
	if (sc_have && sc_c != EOF && sc_fp)
		ungetc(sc_c, sc_fp);
	if (!n && eof)
		return EOF;	/* the input ended before the first conversion */
	return n;
}

int
nh_sscanf(const char *str, const char *fmt, ...)
{
	va_list ap;
	int r;

	va_start(ap, fmt);
	r = sc_scan(fmt, str, 0, ap);
	va_end(ap);
	return r;
}

int
nh_fscanf(FILE *fp, const char *fmt, ...)
{
	va_list ap;
	int r;

	va_start(ap, fmt);
	r = sc_scan(fmt, "", fp, ap);
	va_end(ap);
	return r;
}
