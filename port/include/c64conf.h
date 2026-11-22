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
 * (rnd.c, hacklib.c setrandom, eat.c, files.c check_recordfile).  Changing
 * any of that is a gameplay decision and needs an ADR first (AGENTS.md).
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
 * supplies measurement-only stand-ins.  DEFAULT_WINDOW_SYS is config.h's
 * "tty", the port the C64 build has.
 */

#ifndef C64CONF_H
#define C64CONF_H

#include <stdlib.h>
#include <string.h>
#include <time.h>	/* gcc: time_t for you.h; Oscar64's has clock() only */

/* Oscar64 has no <signal.h>, and nothing on a C64 raises SIGINT/SIGHUP. */
#define NO_SIGNAL

/*
 * The window port is NetHack's own tty port without termcap (NO_TERMS), as on
 * MS-DOS (Phase 3): wintty.c, topl.c and getline.c draw through
 * sys/c64/video.c, over the 80-column screen of src/hal/screen80.h
 * (S80_VIDEO), so what the game shows is the host build's screen
 * (tests/host_video_compare.py).  TEXT_TOMBSTONE keeps rip.c's genl_outrip,
 * which the host build has.
 */
#define NO_TERMS
#define S80_VIDEO
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

/*
 * The tty port's terminal set-up (wintty.c), as sys/share/unixtty.c and
 * pctty.c have it, and stdio's fflush() and perror(), which the tty port
 * calls and Oscar64's stdio.h lacks (below): the bodies come with the Phase 3
 * system layer.
 */
extern void NDECL(gettty);
extern void FDECL(settty, (const char *));
extern void NDECL(setftty);
extern void NDECL(intron);
extern void NDECL(introff);
extern int NDECL(tgetch);		/* a key, as pcsys.c's (wintty.c's tty_nhgetch) */
/* the HAL's (src/hal/sys.h, which needs Oscar64's c64/types.h): a key, waited for */
extern char NDECL(sys_waitkey);

#ifdef __OSCAR64C__
/* Oscar64's scanf family parses floats too: with the float routines that is 3.2 KB of
 * resident code for NetHack's few integer and string reads (T2.12).  sys/c64/c64scanf.c
 * has what those use; makedefs, a host program, keeps the C library's. */
#define sscanf	nh_sscanf
#define fscanf	nh_fscanf
extern int nh_sscanf(const char *, const char *, ...);
extern int nh_fscanf(FILE *, const char *, ...);
extern int fflush(FILE *);
extern void perror(const char *);
#endif

#if defined(__OSCAR64C__) && defined(NH_FAR_SPACES)
/* T2.12, a measurement, not yet the build's: far space 4 holds globals of struct types
 * reached through pointers or by index from many banks (the rooms, the monster
 * counts, the glyph buffer: mkroom.h, decl.h, display.c), at $8000-$FFFF of the space,
 * bank 130 (REU 64 KB bank 16 at $8000, past the code banks; crt_split.py).  Each type
 * is padded to a power of two and each table aligned to its entries, so that no entry
 * crosses a page (ADR-0009 point 5). */
#pragma section(farglob, 0)
#pragma farsection(farglob, 4)
#pragma region(farglob, 0x8000, 0x10000, , 130, { farglob })
#define NH_FAR_GLOBS
#endif

#if defined(__OSCAR64C__) && defined(NH_FAR_SPACES) && defined(NH_FAR_DEFAULT)
/* T2.12, a measurement: far space 5, bank 134 (REU 64 KB bank 17), holds every other
 * global of the files that include hack.h, by default (#pragma fardefault at its end, the
 * far-spaces fork's commits 9 and 10: each object keeps to a page, one larger than a page
 * stays near); nhnear.h (bankgen.py, from the plan's "far_default") names what stays near:
 * what code hands on as a near pointer, what a turn touches, and the glue's variables. */
#pragma section(farmisc, 0)
#pragma farsection(farmisc, 5)
#pragma region(farmisc, 0x8000, 0x10000, , 134, { farmisc })
#include "nhnear.h"
#endif

#if defined(__OSCAR64C__) && defined(NH_FAR_SPACES) && defined(NH_FAR_HEAP)
/* T2.12, a measurement, not yet the build's: the heap far (ADR-0009 point 7). The level's
 * monsters, with their extensions, in far space 7, and its objects in far space 8, from
 * allocators of their own; a block larger than a page stays on the near heap, where a far
 * pointer below $8000 reaches it untranslated. Measured 2026-11-22 on the host: the near
 * heap peaks at 11-24 KB in C64 bytes (monsters 16 KB in one game, 201 of them), against a
 * resident side already 2 KB short without one (docs/data/heap-peak-2026-11-22.txt). */
#pragma farspace(7, monst_s, epri, emin, eshk_s, bill_x, egd, fakecorridor, edog_s)
#pragma farspace(8, obj_s)
#define NH_FAR_HEAP_SPACES
#endif

#if defined(__OSCAR64C__) && defined(NH_FAR_SPACES) && defined(NH_FAR_CHARS)
/* T2.13, a measurement (ADR-0010, far characters): far space 6 is the character space, which
 * a byte reached through a pointer may be in (the far-spaces fork's commit 11): addresses
 * $C100-$FBFF, which no near byte takes (the C128 keeps only code from $C000 up), bank 138
 * (REU 16 KB slot 75 from $C100). The string literals of resident code and of file scope go
 * there (#pragma strings); banked code's stay in its bank. Every object keeps to a page. */
#pragma section(farchars, 0)
#pragma farsection(farchars, 6)
#pragma region(farchars, 0xc100, 0xfc00, , 138, { farchars })
#pragma farchars(6)
#pragma strings(code, farchars)
#endif

#endif /* C64CONF_H */
