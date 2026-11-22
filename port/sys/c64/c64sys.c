/*	c64sys.c	NetHack 3.4.3 for the Commodore 64 and C128 (Oscar64)	*/
/* NetHack may be freely redistributed.  See license for details. */

/*
 * The system layer the game links against (T3.2), in its first-light form: what
 * tools/measure/c64meas-c64.h declares (the measurement shim, which a whole-game build
 * includes as c64meas.h) and the stdio calls c64conf.h sends here (NH_PORT_SYS).
 *
 * Oscar64's own stdio reaches files and the screen through the KERNAL, which the banked game
 * keeps mapped out, so none of it may run: every file call fails cleanly here (errno ENOENT),
 * so that NetHack takes its "no such file" paths, and stdout/stderr go to the 80-column
 * screen. T2.4's REU RAM disk replaces the file half.
 *
 * Provisional until T2.7's clock decision (an open question for Jolyon): time() is a fixed
 * date, 2026-11-22 12:00, so the moon's phase, Friday the 13th, night() and the RNG's seed
 * (setrandom() seeds from time()) are the same at every start.
 */
#include "hack.h"

#if defined(__OSCAR64C__) && defined(NH_PORT_SYS)
#include "screen80.h"

/* errno's values (the measurement's errno.h is empty) */
#define ENOENT	2
#define EBADF	9

extern void sys_debug_exit(char);	/* src/hal/sys128.c */

static int nh_errno;

int *
c64m_errno(void)
{
	return &nh_errno;
}

/* ---- the clock (provisional, see above) ---- */

#define NH_FIXED_TIME	1795348800L	/* 2026-11-22 12:00:00 UTC */

time_t
time(time_t *t)
{
	if (t)
		*t = NH_FIXED_TIME;
	return NH_FIXED_TIME;
}

struct tm *
localtime(const time_t *t)
{
	static struct tm tm;

	(void) t;
	tm.tm_sec = 0, tm.tm_min = 0, tm.tm_hour = 12;
	tm.tm_mday = 22, tm.tm_mon = 10, tm.tm_year = 126;
	tm.tm_wday = 0, tm.tm_yday = 325, tm.tm_isdst = 0;
	return &tm;
}

/* ---- the environment: none ---- */

char *
getenv(const char *name)
{
	(void) name;
	return (char *) 0;
}

/* ---- files: none yet (T2.4) ---- */

int
open(const char *name, int flags, int mode)
{
	(void) name, (void) flags, (void) mode;
	nh_errno = ENOENT;
	return -1;
}

int
creat(const char *name, int mode)
{
	(void) name, (void) mode;
	nh_errno = ENOENT;
	return -1;
}

int
close(int fd)
{
	(void) fd;
	return 0;
}

int
read(int fd, void *buf, unsigned n)
{
	(void) fd, (void) buf, (void) n;
	nh_errno = EBADF;
	return -1;
}

int
write(int fd, const void *buf, unsigned n)
{
	(void) fd, (void) buf, (void) n;
	nh_errno = EBADF;
	return -1;
}

long
lseek(int fd, long off, int whence)
{
	(void) fd, (void) off, (void) whence;
	nh_errno = EBADF;
	return -1L;
}

int
unlink(const char *name)
{
	(void) name;
	nh_errno = ENOENT;
	return -1;
}

int
rename(const char *from, const char *to)
{
	(void) from, (void) to;
	nh_errno = ENOENT;
	return -1;
}

/* No file stream exists yet (nh_fopen() always fails), so every stream a write reaches is
 * the console's: stdout, or the stderr of the game's debugging code (Oscar64 has none). */

FILE *
nh_fopen(const char *name, const char *mode)
{
	(void) name, (void) mode;
	nh_errno = ENOENT;
	return (FILE *) 0;
}

FILE *
nh_freopen(const char *name, const char *mode, FILE *f)
{
	(void) name, (void) mode, (void) f;
	nh_errno = ENOENT;
	return (FILE *) 0;
}

int
nh_fclose(FILE *f)
{
	(void) f;
	return 0;
}

int
nh_fgetc(FILE *f)
{
	(void) f;
	return EOF;
}

char *
nh_fgets(char *s, int n, FILE *f)
{
	(void) s, (void) n, (void) f;
	return (char *) 0;
}

int
nh_feof(FILE *f)
{
	(void) f;
	return 1;
}

unsigned
nh_fread(void *buf, unsigned size, unsigned n, FILE *f)
{
	(void) buf, (void) size, (void) n, (void) f;
	return 0;
}

int
fseek(FILE *f, long off, int whence)
{
	(void) f, (void) off, (void) whence;
	return -1;
}

long
ftell(FILE *f)
{
	(void) f;
	return -1L;
}

void
rewind(FILE *f)
{
	(void) f;
}

int
ungetc(int c, FILE *f)
{
	(void) c, (void) f;
	return EOF;
}

/* ---- the console: stdout and stderr on the 80-column screen ---- */

int
nh_fputc(int c, FILE *f)
{
	(void) f;
	s80_putc((char) c);
	return c & 0xff;
}

int
nh_fputs(const char *s, FILE *f)
{
	(void) f;
	while (*s)
		s80_putc(*s++);
	return 0;
}

unsigned
nh_fwrite(const void *buf, unsigned size, unsigned n, FILE *f)
{
	const char *p = (const char *) buf;
	unsigned i;

	(void) f;
	for (i = 0; i < size * n; i++)
		s80_putc(p[i]);
	return n;
}

int
nh_putchar(int c)
{
	s80_putc((char) c);
	return c & 0xff;
}

int
nh_puts(const char *s)
{
	while (*s)
		s80_putc(*s++);
	s80_putc('\n');
	return 0;
}

int
nh_getchar(void)
{
	return (unsigned char) sys_waitkey();
}

static char nh_obuf[BUFSZ];

int
nh_fprintf(FILE *f, const char *fmt, ...)
{
	va_list ap;

	va_start(ap, fmt);
	(void) vsprintf(nh_obuf, fmt, ap);
	va_end(ap);
	return nh_fputs(nh_obuf, f);
}

int
nh_printf(const char *fmt, ...)
{
	va_list ap;

	va_start(ap, fmt);
	(void) vsprintf(nh_obuf, fmt, ap);
	va_end(ap);
	return nh_fputs(nh_obuf, (FILE *) 0);
}

int
fflush(FILE *f)
{
	(void) f;
	return 0;
}

void
nh_setbuf(FILE *f, char *buf)
{
	(void) f, (void) buf;
}

void
perror(const char *s)
{
	if (s && *s) {
		nh_fputs(s, (FILE *) 0);
		nh_fputs(": ", (FILE *) 0);
	}
	nh_puts(nh_errno == ENOENT ? "no such file" : "error");
}

/* ---- the rest of what NetHack's ports supply ---- */

/* sys/share/pcsys.c's: a message and out, for errors before the windows are up */
void
error(const char *s, ...)
{
	va_list ap;

	va_start(ap, s);
	(void) vsprintf(nh_obuf, s, ap);
	va_end(ap);
	nh_puts(nh_obuf);
	sys_debug_exit(1);	/* no BASIC to return to: VICE's debug cartridge, or a halt */
}

/* a file name the file layer takes: letters, digits and '_' only */
void
regularize(char *s)
{
	for (; *s; s++)
		if (!(letter(*s) || (*s >= '0' && *s <= '9')))
			*s = '_';
}

/* a stable sort: the order glibc's qsort() gives (a merge sort), so that host and C64
 * games sort alike */
void
qsort(void *base, unsigned n, unsigned size, int (*cmp)(const void *, const void *))
{
	char *b = (char *) base, *t;
	unsigned i, j, k;

	if (n < 2 || !size)
		return;
	t = (char *) alloc(size);
	for (i = 1; i < n; i++) {
		for (k = 0; k < size; k++)
			t[k] = b[i * size + k];
		for (j = i; j > 0 && (*cmp)(b + (j - 1) * size, t) > 0; j--)
			for (k = 0; k < size; k++)
				b[j * size + k] = b[(j - 1) * size + k];
		for (k = 0; k < size; k++)
			b[j * size + k] = t[k];
	}
	free((genericptr_t) t);
}

#endif /* __OSCAR64C__ && NH_PORT_SYS */
