/*	SCCS Id: @(#)decl.c	3.2	2001/12/10	*/
/* Copyright (c) Stichting Mathematisch Centrum, Amsterdam, 1985. */
/* NetHack may be freely redistributed.  See license for details. */

#include "hack.h"

int NDECL((*afternmv));
int NDECL((*occupation));

/* from xxxmain.c */
const char *hname = 0;		/* name of the game (argv[0] of main) */
int hackpid = 0;		/* current process id */
#if defined(UNIX) || defined(VMS)
int locknum = 0;		/* max num of simultaneous users */
#endif
#ifdef DEF_PAGER
char *catmore = 0;		/* default pager */
#endif

NEARDATA int bases[MAXOCLASSES] = DUMMY;

NEARDATA int multi = 0;
#if 0
NEARDATA int warnlevel = 0;		/* used by movemon and dochugw */
#endif
NEARDATA int nroom = 0;
NEARDATA int nsubroom = 0;
NEARDATA int occtime = 0;

int x_maze_max, y_maze_max;	/* initialized in main, used in mkmaze.c */
int otg_temp;			/* used by object_to_glyph() [otg] */

#ifdef REDO
NEARDATA int in_doagain = 0;
#endif

/*
 *	The following structure will be initialized at startup time with
 *	the level numbers of some "important" things in the game.
 */
struct dgn_topology dungeon_topology = {DUMMY};

#include "quest.h"
struct q_score	quest_status = DUMMY;

NEARDATA int smeq[MAXNROFROOMS+1] = DUMMY;
NEARDATA int doorindex = 0;

NEARDATA char *save_cm = 0;
NEARDATA int killer_format = 0;
const char *killer = 0;
const char *delayed_killer = 0;
#ifdef GOLDOBJ
NEARDATA long done_money = 0;
#endif
char killer_buf[BUFSZ] = DUMMY;
const char *nomovemsg = 0;
/* nul doubles as the zero record that save.c writes after the trap and fruit
 * chains (its "nulls"), so it must be at least as long as either: struct fruit
 * is 48 bytes on a 64-bit host (T1.29).  Under Oscar64 both are shorter, and
 * nul stays 40 bytes. */
const char nul[max(40, max(sizeof(struct fruit), sizeof(struct trap_s)))] = DUMMY;
NEARDATA char plname[PL_NSIZ] = DUMMY;		/* player name */
NEARDATA char pl_character[PL_CSIZ] = DUMMY;
NEARDATA char pl_race = '\0';

NEARDATA char pl_fruit[PL_FSIZ] = DUMMY;
NEARDATA int current_fruit = 0;
NEARDATA struct fruit *ffruit = (struct fruit *)0;

NEARDATA char tune[6] = DUMMY;

/* not DUMMY ({ 0 }): Oscar64 rejects a braced initializer for a scalar (repro r12) */
const char *occtxt = 0;
const char quitchars[] = " \r\n\033";
const char vowels[] = "aeiouAEIOU";
const char ynchars[] = "yn";
const char ynqchars[] = "ynq";
const char ynaqchars[] = "ynaq";
const char ynNaqchars[] = "yn#aq";
NEARDATA long yn_number = 0L;

const char disclosure_options[] = "iavgc";

#if defined(MICRO) || defined(WIN32)
char hackdir[PATHLEN];		/* where rumors, help, record are */
 #ifdef MICRO
char levels[PATHLEN];		/* where levels are */
 #endif
#endif /* MICRO || WIN32 */


#ifdef MFLOPPY
char permbones[PATHLEN];	/* where permanent copy of bones go */
int ramdisk = FALSE;		/* whether to copy bones to levels or not */
int saveprompt = TRUE;
const char *alllevels = "levels.*";
const char *allbones = "bones*.*";
#endif

#ifdef NH_FAR_GLOBS
#pragma bss(farglob)
#endif
struct linfo level_info[MAXLINFO];
#ifdef NH_FAR_GLOBS
#pragma bss(bss)
#endif

NEARDATA struct sinfo program_state;

/* 'rogue'-like direction commands (cmd.c) */
const char sdir[] = "hykulnjb><";
const char ndir[] = "47896321><";	/* number pad mode */
const schar xdir[10] = { -1,-1, 0, 1, 1, 1, 0,-1, 0, 0 };
const schar ydir[10] = {  0,-1,-1,-1, 0, 1, 1, 1, 0, 0 };
const schar zdir[10] = {  0, 0, 0, 0, 0, 0, 0, 0, 1,-1 };

NEARDATA schar tbx = 0, tby = 0;	/* mthrowu: target */

/* for xname handling of multiple shot missile volleys:
   number of shots, index of current one, validity check, shoot vs throw */
NEARDATA struct multishot_s m_shot = { 0, 0, STRANGE_OBJECT, FALSE };

NEARDATA struct dig_info digging;

NEARDATA dungeon dungeons[MAXDUNGEON];	/* ini'ed by init_dungeon() */
NEARDATA s_level *sp_levchn;
NEARDATA stairway upstair = { 0, 0 }, dnstair = { 0, 0 };
NEARDATA stairway upladder = { 0, 0 }, dnladder = { 0, 0 };
NEARDATA stairway sstairs = { 0, 0 };
NEARDATA dest_area updest = { 0, 0, 0, 0, 0, 0, 0, 0 };
NEARDATA dest_area dndest = { 0, 0, 0, 0, 0, 0, 0, 0 };
NEARDATA coord inv_pos = { 0, 0 };

NEARDATA boolean in_mklev = FALSE;
NEARDATA boolean stoned = FALSE;	/* done to monsters hit by 'c' */
NEARDATA boolean unweapon = FALSE;
NEARDATA boolean mrg_to_wielded = FALSE;
			 /* weapon picked is merged with wielded one */
NEARDATA struct obj_s *current_wand = 0;	/* wand currently zapped/applied */

NEARDATA boolean in_steed_dismounting = FALSE;

NEARDATA coord bhitpos = DUMMY;
NEARDATA coord doors[DOORMAX] = {DUMMY};

#ifdef NH_FAR_GLOBS
#pragma data(farglob)
#endif
NEARDATA struct mkroom_s rooms[(MAXNROFROOMS+1)*2] = {DUMMY};
#ifdef NH_FAR_GLOBS
#pragma data(data)
#pragma align(rooms, 64)
#endif
NEARDATA struct mkroom_s* subrooms = &rooms[MAXNROFROOMS+1];
struct mkroom_s *upstairs_room, *dnstairs_room, *sstairs_room;

#ifdef NH_FAR_LEVEL
#pragma bss(farlevel)
#endif
dlevel_t level;		/* level map */
#ifdef NH_FAR_LEVEL
#pragma bss(bss)
#endif
#if defined(NH_FAR_LEVEL) || defined(NH_FAR_OBJS) || defined(NH_FAR_GLOBS)
/* rm.h: block moves of far data through a near buffer (T2.12) */
static unsigned char nh_farbuf[64];

/* one function a line, so that bankgen.py can put each in a bank of its own */
#define NH_FARW(sp) \
void nh_farbwrite##sp(int fd, const struct nh_fb##sp *s, unsigned n) \
{ \
	while (n) { \
		unsigned k = n < sizeof(nh_farbuf) ? n : sizeof(nh_farbuf), i; \
		for (i = 0; i < k; i++) nh_farbuf[i] = s[i].b; \
		bwrite(fd, (genericptr_t) nh_farbuf, k); \
		s += k; n -= k; \
	} \
}
#define NH_FARR(sp) \
void nh_farmread##sp(int fd, struct nh_fb##sp *d, unsigned n) \
{ \
	while (n) { \
		unsigned k = n < sizeof(nh_farbuf) ? n : sizeof(nh_farbuf), i; \
		/* a short read stops early and leaves the rest as it was: so does this */ \
		for (i = 0; i < k; i++) nh_farbuf[i] = d[i].b; \
		mread(fd, (genericptr_t) nh_farbuf, k); \
		for (i = 0; i < k; i++) d[i].b = nh_farbuf[i]; \
		d += k; n -= k; \
	} \
}
NH_FARW(2)
NH_FARR(2)
NH_FARW(3)
NH_FARR(3)
#ifdef NH_FAR_GLOBS
NH_FARW(4)
NH_FARR(4)

void
nh_farfill4(struct nh_fb4 *d, int c, unsigned n)
{
	while (n--) (d++)->b = (unsigned char) c;
}
#endif

void
nh_farfill3(struct nh_fb3 *d, int c, unsigned n)
{
	while (n--) (d++)->b = (unsigned char) c;
}

#ifdef NH_FAR_HEAP_SPACES
NH_FARW(7)
NH_FARR(7)
NH_FARW(8)
NH_FARR(8)

void
nh_farfill7(struct nh_fb7 *d, int c, unsigned n)
{
	while (n--) (d++)->b = (unsigned char) c;
}

#ifdef NH_FAR_DEFAULT
/* T2.14: these are reached through near pointers (a name's copy as a char *, the chain
 * proxy and the d_level as pointers), so the far default must leave them near; the
 * pragma comes before them, as nhnear.h's names do */
#pragma near(nh_hname_ring, nh_chain_proxy, nh_chain_cont, nh_dltmp)
#endif
/* a monster's or an object's name (NAME(), ONAME()): its n bytes at address a of space sp
 * copied into the next of four near buffers, NUL-ended; a name is at most PL_PSIZ */
static char nh_hname_ring[4][PL_PSIZ + 1];
static unsigned char nh_hname_next;

char *
nh_hname(unsigned a, int sp, unsigned n)
{
	char *d = nh_hname_ring[nh_hname_next];

	nh_hname_next = (nh_hname_next + 1) & 3;
	if (n > PL_PSIZ)
		n = PL_PSIZ;
	nh_farmove((unsigned) d, 0, a, sp, n);
	d[n] = '\0';
	return d;
}

int nh_realloc_ss;	/* obj.h's NH_REALLOC_FROM() */
struct obj_s *nh_chain_proxy, *nh_chain_cont;	/* obj.h's NH_CHAIN_HEAD() */
d_level nh_dltmp;	/* dungeon.h's NH_DLEVEL_F() */

/* strncpy() to a name at address a of space sp: n bytes, NUL-padded (obj.h) */
void
nh_hstrncpy(unsigned a, int sp, const char *s, unsigned n)
{
	char tmp[PL_PSIZ + 1];

	if (n > PL_PSIZ + 1)
		n = PL_PSIZ + 1;
	(void) strncpy(tmp, s, (int) n);
	nh_farmove(a, sp, (unsigned) tmp, 0, n);
}

/* n bytes from address s of space ss to address d of space ds (0 near, 7, 8), through
 * nh_farbuf: a block copy between or within the heap's spaces (realloc_obj, christening,
 * a corpse's monster) */
void
nh_farmove(unsigned d, int ds, unsigned s, int ss, unsigned n)
{
	while (n) {
		unsigned k = n < sizeof(nh_farbuf) ? n : sizeof(nh_farbuf), i;
		if (ss == 7)
			for (i = 0; i < k; i++) nh_farbuf[i] = ((const struct nh_fb7 *) s)[i].b;
		else if (ss == 8)
			for (i = 0; i < k; i++) nh_farbuf[i] = ((const struct nh_fb8 *) s)[i].b;
		else
			for (i = 0; i < k; i++) nh_farbuf[i] = ((const unsigned char *) s)[i];
		if (ds == 7)
			for (i = 0; i < k; i++) ((struct nh_fb7 *) d)[i].b = nh_farbuf[i];
		else if (ds == 8)
			for (i = 0; i < k; i++) ((struct nh_fb8 *) d)[i].b = nh_farbuf[i];
		else
			for (i = 0; i < k; i++) ((unsigned char *) d)[i] = nh_farbuf[i];
		d += k; s += k; n -= k;
	}
}
#endif
#endif

#ifdef C64
struct rm_s * const nh_levl_cols[COLNO] = NH_COLS_INIT(level.locations);	/* rm.h */
#ifndef NH_FAR_LEVEL
struct obj_s ** const nh_lobj_cols[COLNO] = NH_COLS_INIT(level.objects);
struct monst_s ** const nh_lmon_cols[COLNO] = NH_COLS_INIT(level.monsters);
#endif
#endif
struct trap_s *ftrap = (struct trap_s *)0;
NEARDATA struct monst_s youmonst = DUMMY;
NEARDATA struct flag_s flags = DUMMY;
NEARDATA struct instance_flags iflags = DUMMY;
NEARDATA struct you_s u = DUMMY;

NEARDATA struct obj_s *invent = (struct obj_s *)0,
	*uwep = (struct obj_s *)0, *uarm = (struct obj_s *)0,
	*uswapwep = (struct obj_s *)0,
	*uquiver = (struct obj_s *)0, /* quiver */
#ifdef TOURIST
	*uarmu = (struct obj_s *)0, /* under-wear, so to speak */
#endif
	*uskin = (struct obj_s *)0, /* dragon armor, if a dragon */
	*uarmc = (struct obj_s *)0, *uarmh = (struct obj_s *)0,
	*uarms = (struct obj_s *)0, *uarmg = (struct obj_s *)0,
	*uarmf = (struct obj_s *)0, *uamul = (struct obj_s *)0,
	*uright = (struct obj_s *)0,
	*uleft = (struct obj_s *)0,
	*ublindf = (struct obj_s *)0,
	*uchain = (struct obj_s *)0,
	*uball = (struct obj_s *)0;

#ifdef TEXTCOLOR
/*
 *  This must be the same order as used for buzz() in zap.c.
 */
const int zapcolors[NUM_ZAP] = {
    HI_ZAP,		/* 0 - missile */
    CLR_ORANGE,		/* 1 - fire */
    CLR_WHITE,		/* 2 - frost */
    HI_ZAP,		/* 3 - sleep */
    CLR_BLACK,		/* 4 - death */
    CLR_WHITE,		/* 5 - lightning */
    CLR_YELLOW,		/* 6 - poison gas */
    CLR_GREEN,		/* 7 - acid */
};
#endif /* text color */

const int shield_static[SHIELD_COUNT] = {
    S_ss1, S_ss2, S_ss3, S_ss2, S_ss1, S_ss2, S_ss4,	/* 7 per row */
    S_ss1, S_ss2, S_ss3, S_ss2, S_ss1, S_ss2, S_ss4,
    S_ss1, S_ss2, S_ss3, S_ss2, S_ss1, S_ss2, S_ss4,
};

#ifdef NH_FAR_GLOBS
#pragma data(farglob)
#endif
NEARDATA struct spell_s spl_book[MAXSPELL + 1] = {DUMMY};
#ifdef NH_FAR_GLOBS
#pragma data(data)
#endif

NEARDATA long moves = 1L, monstermoves = 1L;
	 /* These diverge when player is Fast */
NEARDATA long wailmsg = 0L;

/* objects that are moving to another dungeon level */
NEARDATA struct obj_s *migrating_objs = (struct obj_s *)0;
/* objects not yet paid for */
NEARDATA struct obj_s *billobjs = (struct obj_s *)0;

/* used to zero all elements of a struct obj_s */
NEARDATA struct obj_s zeroobj = DUMMY;

/* originally from dog.c */
NEARDATA char dogname[PL_PSIZ] = DUMMY;
NEARDATA char catname[PL_PSIZ] = DUMMY;
NEARDATA char horsename[PL_PSIZ] = DUMMY;
char preferred_pet;	/* '\0', 'c', 'd', 'n' (none) */
/* monsters that went down/up together with @ */
NEARDATA struct monst_s *mydogs = (struct monst_s *)0;
/* monsters that are moving to another dungeon level */
NEARDATA struct monst_s *migrating_mons = (struct monst_s *)0;

#ifdef NH_FAR_GLOBS
#pragma bss(farglob)		/* no initialiser: bss, not data */
#endif
NEARDATA struct mvitals_s mvitals[NUMMONS];
#ifdef NH_FAR_GLOBS
#pragma bss(bss)
#pragma align(mvitals, 4)
#endif

NEARDATA struct c_color_names_s c_color_names = {
	"black", "amber", "golden",
	"light blue", "red", "green",
	"silver", "blue", "purple",
	"white"
};

const char *c_obj_colors[] = {
	"black",		/* CLR_BLACK */
	"red",			/* CLR_RED */
	"green",		/* CLR_GREEN */
	"brown",		/* CLR_BROWN */
	"blue",			/* CLR_BLUE */
	"magenta",		/* CLR_MAGENTA */
	"cyan",			/* CLR_CYAN */
	"gray",			/* CLR_GRAY */
	"transparent",		/* no_color */
	"orange",		/* CLR_ORANGE */
	"bright green",		/* CLR_BRIGHT_GREEN */
	"yellow",		/* CLR_YELLOW */
	"bright blue",		/* CLR_BRIGHT_BLUE */
	"bright magenta",	/* CLR_BRIGHT_MAGENTA */
	"bright cyan",		/* CLR_BRIGHT_CYAN */
	"white",		/* CLR_WHITE */
};

struct c_common_strings_s c_common_strings = {
	"Nothing happens.",		"That's enough tries!",
	"That is a silly thing to %s.",	"shudder for a moment.",
	"something", "Something", "You can move again.", "Never mind.",
	"vision quickly clears.", {"the", "your"}
};

/* NOTE: the order of these words exactly corresponds to the
   order of oc_material values #define'd in objclass.h. */
const char *materialnm[] = {
	"mysterious", "liquid", "wax", "organic", "flesh",
	"paper", "cloth", "leather", "wooden", "bone", "dragonhide",
	"iron", "metal", "copper", "silver", "gold", "platinum", "mithril",
	"plastic", "glass", "gemstone", "stone"
};

/* Vision */
NEARDATA boolean vision_full_recalc = 0;
NEARDATA struct vrow_s **viz_array = 0;/* used in cansee() and couldsee() macros */

/* Global windowing data, defined here for multi-window-system support */
NEARDATA winid WIN_MESSAGE = WIN_ERR, WIN_STATUS = WIN_ERR;
NEARDATA winid WIN_MAP = WIN_ERR, WIN_INVEN = WIN_ERR;
char toplines[TBUFSZ];
/* Windowing stuff that's really tty oriented, but present for all ports */
struct tc_gbl_data_s tc_gbl_data = { 0,0, 0,0 };	/* AS,AE, LI,CO */

char *fqn_prefix[PREFIX_COUNT] = { (char *)0, (char *)0, (char *)0, (char *)0,
				(char *)0, (char *)0, (char *)0, (char *)0, (char *)0 };

#ifdef PREFIXES_IN_USE
char *fqn_prefix_names[PREFIX_COUNT] = { "hackdir", "leveldir", "savedir",
					"bonesdir", "datadir", "scoredir",
					"lockdir", "configdir", "troubledir" };
#endif

#ifdef NH_NAME_RING_TEST
/* On the C64 a monster's or object's name is copied out of far memory into one of eight
 * buffers used in turn (T2.12, permonst.h).  For the host's AddressSanitizer build each
 * copy is freed eight reads later, so whatever holds one longer is reported. */
const char *
nh_name_test(const char *p)
{
	static char *ring[8];
	static unsigned next;
	char *d;

	if (!p)
		return p;
	free(ring[next & 7]);
	d = ring[next++ & 7] = (char *) malloc(strlen(p) + 1);
	Strcpy(d, p);
	return d;
}
#endif

/* dummy routine used to force linkage */
void
decl_init(void)
{
    return;
}

/*decl.c*/
