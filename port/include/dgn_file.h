/*	SCCS Id: @(#)dgn_file.h 3.4	1993/01/17	*/
/* Copyright (c) 1989 by M. Stephenson				  */
/* NetHack may be freely redistributed.  See license for details. */

#ifndef DGN_FILE_H
#define DGN_FILE_H

#ifndef ALIGN_H
#include "align.h"
#endif

/*
 * Structures manipulated by the dungeon loader & compiler
 */

struct	couple {
	short	base, rand;
};

struct tmpdungeon_s {
	char	name[24],
		protoname[24];
	struct	couple	lev;
	int	flags,
		chance,
		levels,
		branches,
		entry_lev;		/* entry level for this dungeon */
	char	boneschar;
#ifdef NH_FAR_MISC
	char	nh_pad[64 - 63];	/* T3.2: dungeon.c's proto_dungeon far, its entries */
#endif				/* padded to 64 so that none crosses a page */
};

struct tmplevel_s {
	char	name[24];
	struct	couple	lev;
	int	chance, rndlevs, chain, flags;
	char	boneschar;
#ifdef NH_FAR_MISC
	char	nh_pad[64 - 37];
#endif
};

struct tmpbranch_s {
	char	name[24];	/* destination dungeon name */
	struct	couple	lev;
	int	chain;		/* index into tmplevel array (chained branch)*/
	int	type;		/* branch type (see below) */
	int	up;		/* branch is up or down */
#ifdef NH_FAR_MISC
	char	nh_pad[64 - 34];
#endif
};
#ifdef NH_FAR_MISC
/* far types in space 5 (c64conf.h), as dungeon.c's proto_dungeon is: a file record is the
 * entry without its padding (NH_DGN_FSIZE) */
#pragma farspace(5, tmpdungeon_s, tmplevel_s, tmpbranch_s)
#define NH_DGN_FSIZE(type)	((int) offsetof(struct type, nh_pad))
#endif

/*
 *	Values for type for tmpbranch structure.
 */
#define TBR_STAIR   0	/* connection with both ends having a staircase */
#define TBR_NO_UP   1	/* connection with no up staircase */
#define TBR_NO_DOWN 2	/* connection with no down staircase */
#define TBR_PORTAL  3	/* portal connection */

/*
 *	Flags that map into the dungeon flags bitfields.
 */
#define TOWN	    1	/* levels only */
#define HELLISH     2
#define MAZELIKE    4
#define ROGUELIKE   8

#define D_ALIGN_NONE	0
#define D_ALIGN_CHAOTIC	(AM_CHAOTIC << 4)
#define D_ALIGN_NEUTRAL	(AM_NEUTRAL << 4)
#define D_ALIGN_LAWFUL	(AM_LAWFUL << 4)

#define D_ALIGN_MASK	0x70

/*
 *	Max number of prototype levels and branches.
 */
#define LEV_LIMIT	50
#define BRANCH_LIMIT	32

#endif /* DGN_FILE_H */
