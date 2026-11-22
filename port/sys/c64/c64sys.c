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
#include "dlb.h"
#include "screen80.h"
#include "io128.h"

/* errno's values (the measurement's errno.h is empty) */
#define ENOENT	2
#define EBADF	9
#define EMFILE	24
#define ENOSPC	28
#define EINVAL	22

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

/* ---- files: the REU RAM disk (T2.4) ----
 *
 * The REU's top 2 MB (a 4 MB REU, ADR-0008's amendment of 2026-11-22; the code banks and the
 * far spaces have the first 2 MB): 512 blocks of 4 KB. Block 0 is the directory, 128 entries
 * of 32 bytes (the name, NUL-padded, 24; the size, 4, low byte first; the first block, 2; in
 * use, 1); block 1 the allocation table, 2 bytes a block (0 free, $FFFF the last of a file,
 * else the next; blocks 0 and 1 marked last). tools/data/reudisk.py writes the data files
 * into it when the REU image is made; the game's level, save and bones files are made here.
 * Every transfer is a DMA to or from a near buffer, copied to and from the caller's by C,
 * since a caller's buffer may be in the character space (ADR-0010), which no DMA reaches. The
 * REU's registers are written, never read (docs/HARDWARE.md). */

#define NH_DISK		0x200000UL
#define NH_BLK		4096U
#define NH_NBLK		512U
#define NH_NDIR		128
#define NH_DIRSZ	32
#define NH_NAMESZ	24
#define NH_FAT		(NH_DISK + NH_BLK)
#define NH_FREE		0U
#define NH_END		0xffffU
#define NH_NFD		6
#define NH_RCACHE	64

/* the near buffers the DMA reaches (the plan names them near): a directory entry or a
 * table entry, and one file's read-ahead */
static unsigned char nh_dbuf[NH_DIRSZ + 2];
static unsigned char nh_rbuf[NH_RCACHE];
static int nh_rfd = -1;			/* the file nh_rbuf holds, from nh_rpos, nh_rlen bytes */
static long nh_rpos;
static unsigned nh_rlen;

struct nh_fd {
	char used, wr, dirty, dir;
	long pos, size;
	unsigned first, blk, bidx;	/* the block of index bidx in the file, the walk's place */
	int back;			/* ungetc()'s character, or -1 */
};
static struct nh_fd nh_fds[NH_NFD];

/* n bytes between near p and REU address a: cmd $90 stashes (to the REU), $91 fetches */
static void
nh_dma(unsigned char cmd, unsigned char *p, unsigned long a, unsigned n)
{
	IO_IN();
	*(volatile unsigned char *) 0xdf02 = (unsigned char) (unsigned) p;
	*(volatile unsigned char *) 0xdf03 = (unsigned char) ((unsigned) p >> 8);
	*(volatile unsigned char *) 0xdf04 = (unsigned char) a;
	*(volatile unsigned char *) 0xdf05 = (unsigned char) (a >> 8);
	*(volatile unsigned char *) 0xdf06 = (unsigned char) (a >> 16);
	*(volatile unsigned char *) 0xdf07 = (unsigned char) n;
	*(volatile unsigned char *) 0xdf08 = (unsigned char) (n >> 8);
	*(volatile unsigned char *) 0xdf0a = 0;
	*(volatile unsigned char *) 0xdf01 = cmd;
	IO_OUT();
}

static void
nh_dirget(int i)
{
	nh_dma(0x91, nh_dbuf, NH_DISK + (unsigned long) i * NH_DIRSZ, NH_DIRSZ);
}

static void
nh_dirput(int i)
{
	nh_dma(0x90, nh_dbuf, NH_DISK + (unsigned long) i * NH_DIRSZ, NH_DIRSZ);
}

static long
nh_dirsize(void)
{
	return (long) nh_dbuf[24] | (long) nh_dbuf[25] << 8 | (long) nh_dbuf[26] << 16 |
	       (long) nh_dbuf[27] << 24;
}

static unsigned
nh_fatget(unsigned b)
{
	nh_dma(0x91, nh_dbuf + NH_DIRSZ, NH_FAT + 2UL * b, 2);
	return nh_dbuf[NH_DIRSZ] | (unsigned) nh_dbuf[NH_DIRSZ + 1] << 8;
}

static void
nh_fatset(unsigned b, unsigned v)
{
	nh_dbuf[NH_DIRSZ] = (unsigned char) v;
	nh_dbuf[NH_DIRSZ + 1] = (unsigned char) (v >> 8);
	nh_dma(0x90, nh_dbuf + NH_DIRSZ, NH_FAT + 2UL * b, 2);
}

/* a free block, now the last of a file, or NH_END if the disk is full */
static unsigned
nh_balloc(void)
{
	static unsigned hint = 2;
	unsigned k, b;

	for (k = 0; k < NH_NBLK - 2; k++) {
		b = 2 + (hint - 2 + k) % (NH_NBLK - 2);
		if (nh_fatget(b) == NH_FREE) {
			nh_fatset(b, NH_END);
			hint = b + 1;
			return b;
		}
	}
	return NH_END;
}

static void
nh_bfree(unsigned b)
{
	unsigned nx;

	while (b != NH_END && b >= 2 && b < NH_NBLK) {
		nx = nh_fatget(b);
		nh_fatset(b, NH_FREE);
		b = nx;
	}
}

/* the directory entry named name (a game string, maybe in the character space), or -1;
 * nh_dbuf then holds it */
static int
nh_find(const char *name)
{
	int i, k;

	for (i = 0; i < NH_NDIR; i++) {
		nh_dirget(i);
		if (!nh_dbuf[30])
			continue;
		for (k = 0; k < NH_NAMESZ; k++)
			if ((char) nh_dbuf[k] != name[k] || !name[k])
				break;
		if (k < NH_NAMESZ && (char) nh_dbuf[k] == name[k])
			return i;		/* both ended together */
	}
	return -1;
}

/* the block of index idx of the file, made (with those before it) if create; NH_END if
 * there is none, or no room */
static unsigned
nh_blkof(struct nh_fd *f, unsigned idx, boolean create)
{
	unsigned nx;

	if (f->first == NH_END) {
		if (!create || (f->first = nh_balloc()) == NH_END)
			return NH_END;
		f->blk = f->first, f->bidx = 0, f->dirty = 1;
	}
	if (idx < f->bidx)
		f->blk = f->first, f->bidx = 0;
	while (f->bidx < idx) {
		nx = nh_fatget(f->blk);
		if (nx == NH_END) {
			if (!create || (nx = nh_balloc()) == NH_END)
				return NH_END;
			nh_fatset(f->blk, nx);
		}
		f->blk = nx;
		f->bidx++;
	}
	return f->blk;
}

static struct nh_fd *
nh_fdp(int fd)
{
	if (fd < 0 || fd >= NH_NFD || !nh_fds[fd].used) {
		nh_errno = EBADF;
		return (struct nh_fd *) 0;
	}
	return &nh_fds[fd];
}

int
open(const char *name, int flags, int mode)
{
	int i, k, fd;
	struct nh_fd *f;

	(void) mode;
	for (fd = 0; fd < NH_NFD && nh_fds[fd].used; fd++)
		;
	if (fd == NH_NFD) {
		nh_errno = EMFILE;
		return -1;
	}
	if ((i = nh_find(name)) < 0) {
		if (!(flags & O_CREAT)) {
			nh_errno = ENOENT;
			return -1;
		}
		for (i = 0; i < NH_NDIR; i++) {
			nh_dirget(i);
			if (!nh_dbuf[30])
				break;
		}
		if (i == NH_NDIR) {
			nh_errno = ENOSPC;
			return -1;
		}
		for (k = 0; k < NH_DIRSZ; k++)
			nh_dbuf[k] = 0;
		for (k = 0; k < NH_NAMESZ - 1 && name[k]; k++)
			nh_dbuf[k] = (unsigned char) name[k];
		nh_dbuf[28] = nh_dbuf[29] = 0xff;	/* no block yet */
		nh_dbuf[30] = 1;
		nh_dirput(i);
	} else if (flags & O_TRUNC) {
		nh_bfree(nh_dbuf[28] | (unsigned) nh_dbuf[29] << 8);
		nh_dirget(i);		/* nh_bfree() used the buffer's table bytes only */
		nh_dbuf[24] = nh_dbuf[25] = nh_dbuf[26] = nh_dbuf[27] = 0;
		nh_dbuf[28] = nh_dbuf[29] = 0xff;
		nh_dirput(i);
		if (nh_rfd >= 0 && nh_fds[nh_rfd].used && nh_fds[nh_rfd].dir == i)
			nh_rfd = -1;
	}
	f = &nh_fds[fd];
	f->used = 1;
	f->wr = (flags & 3) != O_RDONLY;
	f->dirty = 0;
	f->dir = (char) i;
	f->pos = 0;
	f->size = nh_dirsize();
	f->first = f->blk = nh_dbuf[28] | (unsigned) nh_dbuf[29] << 8;
	f->bidx = 0;
	f->back = -1;
	return fd;
}

int
creat(const char *name, int mode)
{
	return open(name, O_WRONLY | O_CREAT | O_TRUNC, mode);
}

int
close(int fd)
{
	struct nh_fd *f = nh_fdp(fd);

	if (!f)
		return -1;
	if (f->dirty) {
		nh_dirget(f->dir);
		nh_dbuf[24] = (unsigned char) f->size;
		nh_dbuf[25] = (unsigned char) (f->size >> 8);
		nh_dbuf[26] = (unsigned char) (f->size >> 16);
		nh_dbuf[27] = (unsigned char) (f->size >> 24);
		nh_dbuf[28] = (unsigned char) f->first;
		nh_dbuf[29] = (unsigned char) (f->first >> 8);
		nh_dirput(f->dir);
	}
	if (nh_rfd == fd)
		nh_rfd = -1;
	f->used = 0;
	return 0;
}

/* the next byte of a file through the read-ahead, or -1 at its end */
static int
nh_getb(int fd, struct nh_fd *f)
{
	unsigned off, k;

	if (f->pos >= f->size)
		return -1;
	if (nh_rfd != fd || f->pos < nh_rpos || f->pos >= nh_rpos + nh_rlen) {
		if (nh_blkof(f, (unsigned) (f->pos / NH_BLK), FALSE) == NH_END)
			return -1;
		off = (unsigned) (f->pos % NH_BLK);
		k = NH_BLK - off;
		if (k > NH_RCACHE)
			k = NH_RCACHE;
		if ((long) k > f->size - f->pos)
			k = (unsigned) (f->size - f->pos);
		nh_dma(0x91, nh_rbuf, NH_DISK + (unsigned long) f->blk * NH_BLK + off, k);
		nh_rfd = fd, nh_rpos = f->pos, nh_rlen = k;
	}
	return nh_rbuf[(unsigned) (f->pos++ - nh_rpos)];
}

int
read(int fd, void *buf, unsigned n)
{
	struct nh_fd *f = nh_fdp(fd);
	char *p = (char *) buf;
	unsigned i;
	int c;

	if (!f)
		return -1;
	for (i = 0; i < n; i++) {
		if (f->back >= 0)
			c = f->back, f->back = -1;
		else if ((c = nh_getb(fd, f)) < 0)
			break;
		p[i] = (char) c;
	}
	return (int) i;
}

int
write(int fd, const void *buf, unsigned n)
{
	struct nh_fd *f = nh_fdp(fd);
	const char *p = (const char *) buf;
	unsigned i, off, k, j;

	if (!f || !f->wr) {
		nh_errno = EBADF;
		return -1;
	}
	if (nh_rfd == fd)
		nh_rfd = -1;
	f->back = -1;
	for (i = 0; i < n; i += k) {
		if (nh_blkof(f, (unsigned) (f->pos / NH_BLK), TRUE) == NH_END) {
			nh_errno = ENOSPC;
			break;
		}
		off = (unsigned) (f->pos % NH_BLK);
		k = NH_BLK - off;
		if (k > NH_RCACHE)
			k = NH_RCACHE;
		if (k > n - i)
			k = n - i;
		for (j = 0; j < k; j++)
			nh_rbuf[j] = (unsigned char) p[i + j];
		nh_dma(0x90, nh_rbuf, NH_DISK + (unsigned long) f->blk * NH_BLK + off, k);
		f->pos += k;
		if (f->pos > f->size)
			f->size = f->pos;
		f->dirty = 1;
	}
	return i ? (int) i : -1;
}

long
lseek(int fd, long off, int whence)
{
	struct nh_fd *f = nh_fdp(fd);

	if (!f)
		return -1L;
	if (whence == SEEK_CUR)
		off += f->pos;
	else if (whence == SEEK_END)
		off += f->size;
	if (off < 0) {
		nh_errno = EINVAL;
		return -1L;
	}
	f->pos = off;
	f->back = -1;
	return off;
}

int
unlink(const char *name)
{
	int i = nh_find(name);
	int fd;

	if (i < 0) {
		nh_errno = ENOENT;
		return -1;
	}
	nh_bfree(nh_dbuf[28] | (unsigned) nh_dbuf[29] << 8);
	nh_dirget(i);
	nh_dbuf[30] = 0;
	nh_dirput(i);
	for (fd = 0; fd < NH_NFD; fd++)
		if (nh_fds[fd].used && nh_fds[fd].dir == i)
			nh_fds[fd].used = 0;	/* as Unix would keep it, but nothing here needs that */
	nh_rfd = -1;
	return 0;
}

int
rename(const char *from, const char *to)
{
	int i, k;

	if (nh_find(to) >= 0)
		(void) unlink(to);
	if ((i = nh_find(from)) < 0) {
		nh_errno = ENOENT;
		return -1;
	}
	for (k = 0; k < NH_NAMESZ; k++)
		nh_dbuf[k] = 0;
	for (k = 0; k < NH_NAMESZ - 1 && to[k]; k++)
		nh_dbuf[k] = (unsigned char) to[k];
	nh_dirput(i);
	return 0;
}

/* ---- streams over the files: a FILE * is the descriptor plus one; anything else that
 * reaches a write (stdout, the stderr of the game's debugging code, which Oscar64 has
 * not) is the console ---- */

#define NH_FD(f)	((int) (unsigned) (f) - 1)
#define NH_ISFILE(f)	((unsigned) (f) >= 1 && (unsigned) (f) <= NH_NFD)

FILE *
nh_fopen(const char *name, const char *mode)
{
	int flags, fd;

	if (mode[0] == 'r')
		flags = mode[1] == '+' || (mode[1] && mode[2] == '+') ? O_RDWR : O_RDONLY;
	else
		flags = O_WRONLY | O_CREAT | (mode[0] == 'a' ? 0 : O_TRUNC);
	if ((fd = open(name, flags, 0)) < 0)
		return (FILE *) 0;
	if (mode[0] == 'a')
		(void) lseek(fd, 0L, SEEK_END);
	return (FILE *) (unsigned) (fd + 1);
}

FILE *
nh_freopen(const char *name, const char *mode, FILE *f)
{
	if (NH_ISFILE(f))
		(void) close(NH_FD(f));
	return nh_fopen(name, mode);
}

int
nh_fclose(FILE *f)
{
	return NH_ISFILE(f) ? close(NH_FD(f)) : 0;
}

int
nh_fgetc(FILE *f)
{
	unsigned char c;

	if (!NH_ISFILE(f))
		return (unsigned char) sys_waitkey();
	return read(NH_FD(f), &c, 1) == 1 ? c : EOF;
}

char *
nh_fgets(char *s, int n, FILE *f)
{
	int i = 0, c = 0;

	while (i < n - 1 && (c = nh_fgetc(f)) != EOF) {
		s[i++] = (char) c;
		if (c == '\n')
			break;
	}
	if (!i)
		return (char *) 0;
	s[i] = 0;
	return s;
}

int
nh_feof(FILE *f)
{
	struct nh_fd *p = NH_ISFILE(f) ? nh_fdp(NH_FD(f)) : (struct nh_fd *) 0;

	return !p || (p->back < 0 && p->pos >= p->size);
}

unsigned
nh_fread(void *buf, unsigned size, unsigned n, FILE *f)
{
	int k;

	if (!NH_ISFILE(f) || !size)
		return 0;
	k = read(NH_FD(f), buf, size * n);
	return k < 0 ? 0 : (unsigned) k / size;
}

int
fseek(FILE *f, long off, int whence)
{
	return NH_ISFILE(f) && lseek(NH_FD(f), off, whence) >= 0 ? 0 : -1;
}

long
ftell(FILE *f)
{
	struct nh_fd *p = NH_ISFILE(f) ? nh_fdp(NH_FD(f)) : (struct nh_fd *) 0;

	return p ? p->pos - (p->back >= 0) : -1L;
}

void
rewind(FILE *f)
{
	(void) fseek(f, 0L, SEEK_SET);
}

int
ungetc(int c, FILE *f)
{
	struct nh_fd *p = NH_ISFILE(f) ? nh_fdp(NH_FD(f)) : (struct nh_fd *) 0;

	if (!p || c == EOF)
		return EOF;
	p->back = c & 0xff;
	return p->back;
}

/* ---- the console: stdout and stderr on the 80-column screen ---- */

int
nh_fputc(int c, FILE *f)
{
	char b = (char) c;

	if (NH_ISFILE(f))
		return write(NH_FD(f), &b, 1) == 1 ? c & 0xff : EOF;
	s80_putc(b);
	return c & 0xff;
}

int
nh_fputs(const char *s, FILE *f)
{
	if (NH_ISFILE(f))
		return write(NH_FD(f), s, (unsigned) strlen(s)) < 0 ? EOF : 0;
	while (*s)
		s80_putc(*s++);
	return 0;
}

unsigned
nh_fwrite(const void *buf, unsigned size, unsigned n, FILE *f)
{
	const char *p = (const char *) buf;
	unsigned i;
	int k;

	if (NH_ISFILE(f)) {
		k = size ? write(NH_FD(f), buf, size * n) : 0;
		return k < 0 ? 0 : (unsigned) k / size;
	}
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
