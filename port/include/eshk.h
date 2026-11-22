/*	SCCS Id: @(#)eshk.h	3.4	1997/05/01	*/
/* Copyright (c) Stichting Mathematisch Centrum, Amsterdam, 1985. */
/* NetHack may be freely redistributed.  See license for details. */

#ifndef ESHK_H
#define ESHK_H

#define REPAIR_DELAY	5	/* minimum delay between shop damage & repair */

#define BILLSZ	200

struct bill_x {
	unsigned bo_id;
	boolean useup;
	long price;		/* price per unit */
	long bquan;		/* amount used up */
#ifdef NH_FAR_HEAP_SPACES
	char nh_pad[5];		/* T2.14: 16 bytes, so that no entry crosses a far page */
#endif
};

struct eshk_s {
	long robbed;		/* amount stolen by most recent customer */
	long credit;		/* amount credited to customer */
	long debit;		/* amount of debt for using unpaid items */
	long loan;		/* shop-gold picked (part of debit) */
	int shoptype;		/* the value of rooms[shoproom].rtype */
	schar shoproom;		/* index in rooms; set by inshop() */
	schar unused;		/* to force alignment for stupid compilers */
	boolean following;	/* following customer since he owes us sth */
	boolean surcharge;	/* angry shk inflates prices */
	coord shk;		/* usual position shopkeeper */
	coord shd;		/* position shop door */
	d_level shoplevel;	/* level (& dungeon) of his shop */
	int billct;		/* no. of entries of bill[] in use */
#ifdef NH_FAR_HEAP_SPACES
	char nh_pad0[9];	/* T2.14: bill[] at a multiple of 16 in the block (c64heap.c) */
#endif
	struct bill_x bill[BILLSZ];
	struct bill_x *bill_p;
	int visitct;		/* nr of visits by most recent customer */
	char customer[PL_NSIZ]; /* most recent customer */
	char shknam[PL_NSIZ];
};

#ifdef NH_FAR_HEAP_SPACES
/* the shopkeeper's names in the far monster (T2.14): read through a copy (obj.h's
 * nh_hname()), written as strncpy() does */
#define NH_ESHKF(e, f)		((unsigned)(e) + (unsigned)offsetof(struct eshk_s, f))
#define NH_ESHK_CUSTOMER(e)	nh_hname(NH_ESHKF(e, customer), 7, PL_NSIZ)
#define NH_ESHK_SHKNAM(e)	nh_hname(NH_ESHKF(e, shknam), 7, PL_NSIZ)
#define NH_ESHK_SETCUSTOMER(e, s) nh_hstrncpy(NH_ESHKF(e, customer), 7, (s), PL_NSIZ)
#define NH_ESHK_SETSHKNAM(e, s)	nh_hstrncpy(NH_ESHKF(e, shknam), 7, (s), PL_NSIZ)
#else
#define NH_ESHK_CUSTOMER(e)	((e)->customer)
#define NH_ESHK_SHKNAM(e)	((e)->shknam)
#define NH_ESHK_SETCUSTOMER(e, s) (void) strncpy((e)->customer, (s), PL_NSIZ)
#define NH_ESHK_SETSHKNAM(e, s)	(void) strncpy((e)->shknam, (s), PL_NSIZ)
#endif

#define ESHK(mon)	((struct eshk_s *)&(mon)->mextra[0])

#define NOTANGRY(mon)	((mon)->mpeaceful)
#define ANGRY(mon)	(!NOTANGRY(mon))

#endif /* ESHK_H */
