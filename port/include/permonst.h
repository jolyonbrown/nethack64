/*	SCCS Id: @(#)permonst.h 3.4	1999/07/02	*/
/* Copyright (c) Stichting Mathematisch Centrum, Amsterdam, 1985. */
/* NetHack may be freely redistributed.  See license for details. */

#ifndef PERMONST_H
#define PERMONST_H

/*	This structure covers all attack forms.
 *	aatyp is the gross attack type (eg. claw, bite, breath, ...)
 *	adtyp is the damage type (eg. physical, fire, cold, spell, ...)
 *	damn is the number of hit dice of damage from the attack.
 *	damd is the number of sides on each die.
 *
 *	Some attacks can do no points of damage.  Additionally, some can
 *	have special effects *and* do damage as well.  If damn and damd
 *	are set, they may have a special meaning.  For example, if set
 *	for a blinding attack, they determine the amount of time blinded.
 */

struct attack_s {
	uchar		aatyp;
	uchar		adtyp, damn, damd;
};

/*	Max # of attacks for any given monster.
 */

#define NATTK		6

/*	Weight of a human body
 */

#define WT_HUMAN	1450

#ifndef ALIGN_H
#include "align.h"
#endif
#include "monattk.h"
#include "monflag.h"

struct permonst {
	const char	*mname;			/* full name */
	char		mlet;			/* symbol */
	schar		mlevel,			/* base monster level */
			mmove,			/* move speed */
			ac,			/* (base) armor class */
			mr;			/* (base) magic resistance */
	aligntyp	maligntyp;		/* basic monster alignment */
	unsigned short	geno;			/* creation/geno mask value */
	struct	attack_s	mattk[NATTK];		/* attacks matrix */
	unsigned short	cwt,			/* weight of corpse */
			cnutrit;		/* its nutritional value */
	short		pxlth;			/* length of extension */
	uchar		msound;			/* noise it makes (6 bits) */
	uchar		msize;			/* physical size (3 bits) */
	uchar		mresists;		/* resistances */
	uchar		mconveys;		/* conveyed by eating */
	unsigned long	mflags1,		/* boolean bitflags */
			mflags2;		/* more boolean bitflags */
	unsigned short	mflags3;		/* yet more boolean bitflags */
 #ifdef TEXTCOLOR
	uchar		mcolor;			/* color to use */
 #endif
#ifdef C64
	/* 64 bytes, not 55 (ADR-0009, point 5): an entry of the far table
	 * never crosses a page, so one translation serves all its fields,
	 * and &mons[i] and monsndx() are shifts instead of Oscar64's
	 * multiply and divide by 55.  Checked below. */
	uchar		mpad_c64[9];
#endif
};

#if defined(C64) && defined(__OSCAR64C__)
static_assert(sizeof (struct permonst) == 64, "struct permonst is 64 bytes (ADR-0009)");
#ifdef NH_FAR_SPACES
/* T2.12, not yet the build's: mons[] in far space 1 (ADR-0009), with its attacks, which
 * code reaches as &ptr->mattk[i]; needs an Oscar64 with far spaces.  The space's addresses
 * are $8000-$FFFF (no near object of these types: nothing collides with the identity
 * pages below); bank 106 is REU 64 KB bank 10 at $8000 (T2.12 layout, crt_split.py). */
#pragma farspace(1, permonst, attack_s)
#pragma section(farmons, 0)
#pragma farsection(farmons, 1)
#pragma region(farmons, 0x8000, 0xe000, , 106, { farmons })
#define NH_FAR_MONS
/* the names, which mons[] points to, at $E000-$FFFF of the space: not a far section (no
 * code reads them in place), but bytes NH_MNAME() copies out (tools/farnames.py wraps
 * every read of mname); kept out of $D000-$DFFF, the I/O page in view, so that a read
 * of one in place by mistake reads only RAM or ROM */
#pragma section(farmnames, 0)
#pragma region(farmnames, 0xe000, 0x10000, , 106, { farmnames })
#define NH_FAR_MNAMES
#endif
#endif

/* NH_MNAME_B(p, buf): a copy in the caller's buffer of NH_NAMEBUF bytes, for a lookup that
 * reads every name (name_to_mon()) and would otherwise cycle the ring under its callers */
#define NH_NAMEBUF 48
#ifdef NH_FAR_MNAMES
/* a near copy of a monster's name in a ring of buffers (the far runtime) */
extern const char *nh_mname(const char *);
extern const char *nh_mname_b(const char *, char *);
#define NH_MNAME(p) nh_mname(p)
#define NH_MNAME_B(p, buf) nh_mname_b((p), (buf))
#elif defined(NH_NAME_RING_TEST)
/* the host's check of how long a copy is held (decl.c) */
extern const char *nh_name_test(const char *);
#define NH_MNAME(p) nh_name_test(p)
#define NH_MNAME_B(p, buf) (p)
#else
#define NH_MNAME(p) (p)
#define NH_MNAME_B(p, buf) (p)
#endif

#ifdef NH_FAR_MONS
#pragma data(farmons)
#endif
extern NEARDATA struct permonst
		mons[];		/* the master list of monster types */
#ifdef NH_FAR_MONS
#pragma data(data)
#endif

#define VERY_SLOW 3
#define SLOW_SPEED 9
#define NORMAL_SPEED 12 /* movement rates */
#define FAST_SPEED 15
#define VERY_FAST 24

#define NON_PM		PM_PLAYERMON		/* "not a monster" */
#define LOW_PM		(NON_PM+1)		/* first monster in mons[] */
#define SPECIAL_PM	PM_LONG_WORM_TAIL	/* [normal] < ~ < [special] */
	/* mons[SPECIAL_PM] through mons[NUMMONS-1], inclusive, are
	   never generated randomly and cannot be polymorphed into */

#endif /* PERMONST_H */
