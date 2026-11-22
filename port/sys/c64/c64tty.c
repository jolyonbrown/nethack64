/*	c64tty.c	NetHack 3.4.3 for the Commodore 64 and C128 (Oscar64)	*/
/* NetHack may be freely redistributed.  See license for details. */

/*
 * The tty port's terminal set-up and its keys (NO_TERMS), as
 * sys/share/pctty.c is MS-DOS's: wintty.c calls gettty() and setftty()
 * when it starts, settty() when it ends, and tgetch() for every key
 * (tty_nhgetch).  The keys come from the HAL (src/hal/sys.h): the KERNAL's
 * buffer on a C64, the buffer and the keyboard matrix on a C128, as ASCII,
 * the cursor keys as the vi-keys and DEL as '\b'.  error() is the system
 * layer's still (c64conf.h).
 */

#include "hack.h"

#if defined(TTY_GRAPHICS) && defined(S80_VIDEO)

#include "wintty.h"

/* src/hal/sys.h's, declared here because that header needs Oscar64's own
 * (c64/types.h), which NetHack's files are not compiled with */
extern char sys_waitkey(void);

char erase_char, kill_char;	/* getline.c, topl.c */

void
gettty(void)
{
	erase_char = '\b';
	kill_char = 21;		/* ^U, as on MS-DOS */
	iflags.cbreak = TRUE;
}

void
settty(const char *s)
{
	end_screen();
	if (s)
		raw_print(s);
}

void
setftty(void)
{
	start_screen();
}

/* nothing on a C64 raises an interrupt from the keyboard (NO_SIGNAL) */
void
intron(void)
{
}

void
introff(void)
{
}

int
tgetch(void)
{
	return (unsigned char) sys_waitkey();
}

#endif /* TTY_GRAPHICS && S80_VIDEO */
