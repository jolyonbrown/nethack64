/*
 * far_post.h - after the headers: the code's own `&mons[i]` are far pointers too, NH_VOFF
 * away from the real table, so that an access farify.py did not translate reads the wrong
 * bytes and the checksum shows it.  The far build compiles with -dmons=nh_mons_real, so the
 * real table has a name of its own: Oscar64 does not take a macro that names itself
 * (compat #70, r67).  The far address is made from an integer: pointer arithmetic outside
 * the table would be undefined, and Oscar64 warns of it (and may fold it as it likes).
 */
#ifndef FAR_POST_H
#define FAR_POST_H
#ifdef NH_FAR_PERMONST
#undef mons
#define mons	((struct permonst *) ((unsigned) nh_mons_real + NH_VOFF))
#endif
#endif
