/*	c64conf.h	NetHack 3.4.3 for the Commodore 64 (Oscar64)	*/
/* NetHack may be freely redistributed.  See license for details. */

/*
 * The C64 platform configuration (docs/decisions/ADR-0006).
 *
 * Selected only by -DC64 (oscar64: -dC64); nothing defines C64 by itself,
 * so every existing build (the gcc host build, the UNIX-config measurement)
 * is unchanged.  config1.h undefines UNIX and sets UNWIDENED_PROTOTYPES
 * (both are read before this file); global.h includes this file in place
 * of unixconf.h.  -dC64 defines C64 empty: test it with #ifdef/defined(),
 * never #if C64.  C64 names this platform layer, not the machine: a C128
 * build would define it too (Oscar64 -tm=c128 sets __C128__, not __C64__).
 *
 * Rule: compile the same game as the UNIX host build (tools/host-build.sh,
 * our behaviour oracle) minus platform services a C64 cannot have: signals,
 * fork/exec, user ids, job control, a shell, an external compress program,
 * the termcap tty port.  So the options the host build gets from unixconf.h
 * rather than config.h are re-stated here, and the few places where
 * "#ifdef UNIX" selects game behaviour rather than a service also test C64
 * (rnd.c, hacklib.c setrandom, eat.c).  Changing any of that is a gameplay
 * decision and needs an ADR first (AGENTS.md).
 *
 * Deliberately not MICRO: that profile also changes maze generation, panic
 * save, score keeping and several UI defaults relative to the host build.
 * Its price is C64 in the two non-Unix config-file lists in files.c.
 *
 * This file must also preprocess with gcc on the host (gcc -DC64), because
 * mkstubs.py and a C64-config makedefs see the configuration through gcc.
 * Hence no system.h (it needs <sys/types.h>, and its libc prototypes clash
 * with Oscar64's), only ISO headers.
 *
 * Not here yet: the system layer's interface (file descriptors, errno, time,
 * getenv, qsort, fseek/ftell/rewind).  It belongs to the Phase 2 file layer
 * and the Phase 3 system layer; until then tools/measure/c64meas-c64.h
 * supplies measurement-only stand-ins.  DEFAULT_WINDOW_SYS stays config.h's
 * "tty" until the Phase 3 c64 window port sets it; only makedefs reads it,
 * for the #version text (dat/options), which a C64 build must regenerate.
 */

#ifndef C64CONF_H
#define C64CONF_H

#include <stdlib.h>
#include <string.h>
#include <time.h>	/* gcc: time_t for you.h; Oscar64's has clock() only */

/* Oscar64 has no <signal.h>, and nothing on a C64 raises SIGINT/SIGHUP. */
#define NO_SIGNAL

/*
 * The tty window port (termcap) is not part of the C64 build, so windows.c
 * and mapglyph.c must not reference tty_procs or has_color().  The c64
 * window port (Phase 3) adds its own procs and DEFAULT_WINDOW_SYS.
 * TEXT_TOMBSTONE keeps rip.c's genl_outrip, which the host build has.
 */
#undef TTY_GRAPHICS
#define TEXT_TOMBSTONE

/*
 * The host build gets these from unixconf.h.  Dropping either changes game
 * data (MAIL: objects[], mons[], pm.h, onames.h; TEXTCOLOR: struct permonst)
 * and needs an ADR.  Off UNIX, MAIL is mail.c's fake mail daemon, which is
 * only ever scheduled on AMIGA/MSDOS/TOS: in normal play no mail arrives
 * and no random number is drawn, as on a host whose mailbox stays empty.
 */
#define TEXTCOLOR
#define MAIL

/*
 * The host's RNG contract (unixconf.h, SYSV): Rand() is lrand48(), seeded
 * with srand48((long) time) in hacklib.c, and rnd.c's RND(x) is Rand() % x;
 * rnd.c and hacklib.c test C64 next to UNIX for it.  The bodies come with
 * the Phase 3 system layer; which generator that is, and how it is seeded,
 * is an RNG ADR.  RANDOM is not used: it would switch the game to random()
 * and to srandom((unsigned) time), a 16-bit seed under Oscar64.
 */
extern long lrand48(void);
extern void srand48(long);
#define Rand()	lrand48()

/* One player per machine and no user ids (hack.h does the same for MICRO). */
#define getuid()	1

#define FCMASK	0660	/* creat()/open() mode, as unixconf.h */

/*
 * Off UNIX, files.c sizes SAVEF by FILENAME.  The C64 builds the same
 * "save/<uid><name>" name as UNIX (set_savefile_name), so keep the host
 * size (files.c: SAVESIZE = PL_NSIZ + 13).  CBM DOS names are the file
 * layer's business.
 */
#define FILENAME	(PL_NSIZ + 13)

#define PORT_ID	"C64"

#ifndef index
 #define index	strchr
#endif
#ifndef rindex
 #define rindex	strrchr
#endif

/*
 * Port functions that game code calls unconditionally (error: do.c,
 * o_init.c, restore.c; regularize: files.c).  Oscar64 accepts no implicit
 * declarations; the bodies come with the Phase 3 system layer.  As in
 * beconf.h, these can move to an extern.h section once that layer exists.
 */
extern void VDECL(error, (const char *,...)) PRINTF_F(1,2);
extern void FDECL(regularize, (char *));

#endif /* C64CONF_H */
