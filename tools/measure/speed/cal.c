/*
 * cal.c - speed calibration harness (docs/RAM-PLAN.md, the speed baseline).
 *
 * The host game's callgrind run counts x86 instructions; the C64 runs 6502 cycles.  To turn
 * one into the other, this runs some of the game's hottest functions, copied verbatim from
 * port/src by extract.py, on one level both ways: compiled by gcc as the host build compiles
 * them (callgrind counts the instructions) and by Oscar64 as the C64 build does (its emulator
 * counts the cycles).
 *
 * -DWORK=n picks the workload.  WORK=0 only sets the level up; the driver (calibrate.py)
 * subtracts it from the others.  Each prints a checksum, and the two builds must agree on it,
 * or they did not do the same work (int is 16 bits on Oscar64 and 32 on the host, long 32 and
 * 64: the checksum keeps to values both represent alike).
 */
#include "hack.h"
#include "mfndpos.h"
#include <stdio.h>

#ifndef WORK
#define WORK 0
#endif
/* parenthesised: Oscar64 does not take sizeof without (compat #6) */
#define NELEM(a) (sizeof(a) / sizeof((a)[0]))

#ifdef __OSCAR64C__
/* Oscar64's emulator has 64 KB of RAM and no ROM: room for level, mons[] and objects[] */
#pragma region(main, 0x0a00, 0xff00, , , {code, data, bss, heap, stack})
#pragma stacksize(1024)
#pragma heapsize(0)
#endif

/* the globals the extracted functions read (decl.c's, and engrave.c's file-scope list) */
dlevel_t level;
#ifdef C64
struct rm_s * const nh_levl_cols[COLNO] = LEVL_COLS_INIT;	/* rm.h */
#endif
struct you_s u;
struct monst_s youmonst;
struct trap_s *ftrap;
long moves = 1000L;
struct dgn_topology dungeon_topology;
struct engr_s *head_engr;
/* only is_axe() reads it, in mfndpos()'s ALLOW_DIG branch, which no workload takes; the real
   table (11 KB and its names) would not fit beside level and mons[] in the emulator's 64 KB */
struct objclass objects[1];

/* mfndpos() calls these only for a trap type that cannot happen, or on a level with a temple:
   never here */
void
impossible(const char *s, ...)
{
	(void) s;
}

char *
in_rooms(xchar x, xchar y, int typewanted)
{
	(void) x; (void) y; (void) typewanted;
	return "";
}

boolean
in_your_sanctuary(struct monst_s *mon, xchar x, xchar y)
{
	(void) mon; (void) x; (void) y;
	return FALSE;
}

/* a level 1 of five rooms, four corridors, doors in each state, water, traps, objects, and
   monsters cal_standing about; the hero is in the second room */
static const xchar cal_rooms[][4] = {	/* the floor's lx, ly, hx, hy; walls around it */
	{ 3, 2, 14, 6 }, { 21, 3, 34, 8 }, { 45, 11, 59, 16 }, { 64, 2, 76, 7 }, { 9, 13, 24, 18 }
};
static const xchar cal_doors[][3] = {	/* x, y, doormask */
	{ 15, 4, D_ISOPEN }, { 20, 5, D_NODOOR }, { 35, 6, D_CLOSED }, { 52, 10, D_BROKEN },
	{ 63, 4, D_NODOOR }, { 60, 13, D_ISOPEN }, { 8, 7, D_NODOOR }, { 12, 12, D_LOCKED }
};
static const xchar cal_corridors[][4] = {	/* L-shaped: along x from (x0,y0), then along y */
	{ 16, 4, 19, 5 }, { 36, 6, 52, 9 }, { 61, 13, 62, 4 }, { 8, 8, 12, 11 }
};
static const xchar cal_traps[][3] = {
	{ 5, 3, ARROW_TRAP }, { 30, 7, PIT }, { 70, 5, SQKY_BOARD }, { 17, 4, BEAR_TRAP }
};
static const short cal_objs[][3] = {
	{ 40, 6, BOULDER }, { 6, 5, ROCK }, { 23, 4, FOOD_RATION }, { 47, 12, DAGGER },
	{ 47, 12, ROCK }, { 66, 3, GOLD_PIECE }, { 14, 18, LARGE_BOX }, { 55, 15, CLOVE_OF_GARLIC }
};
static const short cal_standing[][3] = {	/* x, y, PM_ */
	{ 10, 4, PM_JACKAL }, { 28, 6, PM_NEWT }, { 50, 12, PM_GRID_BUG }, { 70, 4, PM_SEWER_RAT },
	{ 15, 15, PM_KOBOLD }, { 24, 5, PM_LITTLE_DOG }, { 53, 14, PM_FLOATING_EYE },
	{ 18, 17, PM_ACID_BLOB }, { 25, 5, PM_GIANT_EEL }
};
#define NSUBJ 7
static const short subjects[NSUBJ] = {	/* the monsters whose moves mfndpos() looks at */
	PM_JACKAL, PM_NEWT, PM_GRID_BUG, PM_HILL_ORC, PM_GNOME_LORD, PM_LITTLE_DOG, PM_GIANT_EEL
};
static long subjflags[NSUBJ];		/* as m_move() and dog_move() set them */

static struct trap_s trapv[NELEM(cal_traps)];
static struct obj_s objv[NELEM(cal_objs)];
static struct monst_s monv[NELEM(cal_standing)];
static struct monst_s subjv[NSUBJ];

static void
setlev(int x, int y, int typ)
{
	if (levl[x][y].typ == STONE)
		levl[x][y].typ = typ;
}

static void
setup(void)
{
	int i, x, y;

	u.ux = 23; u.uy = 6;
	youmonst.data = &mons[PM_HUMAN];
	u.uz.dnum = 0; u.uz.dlevel = 1;
	dungeon_topology.d_sokoban_dnum = 4;
	dungeon_topology.d_water_level.dnum = 7; dungeon_topology.d_water_level.dlevel = 4;
	dungeon_topology.d_rogue_level.dnum = 0; dungeon_topology.d_rogue_level.dlevel = 15;

	for (i = 0; i < (int) (NELEM(cal_rooms)); i++) {
		int lx = cal_rooms[i][0], ly = cal_rooms[i][1], hx = cal_rooms[i][2], hy = cal_rooms[i][3];
		for (x = lx - 1; x <= hx + 1; x++)
			for (y = ly - 1; y <= hy + 1; y++) {
				int typ = ROOM;
				if (y == ly - 1 || y == hy + 1)
					typ = x == lx - 1 ? (y == ly - 1 ? TLCORNER : BLCORNER) :
					      x == hx + 1 ? (y == ly - 1 ? TRCORNER : BRCORNER) : HWALL;
				else if (x == lx - 1 || x == hx + 1)
					typ = VWALL;
				levl[x][y].typ = typ;
				levl[x][y].lit = 1;
			}
	}
	for (i = 0; i < (int) (NELEM(cal_doors)); i++) {
		levl[cal_doors[i][0]][cal_doors[i][1]].typ = DOOR;
		levl[cal_doors[i][0]][cal_doors[i][1]].doormask = cal_doors[i][2];
	}
	for (i = 0; i < (int) (NELEM(cal_corridors)); i++) {
		int x0 = cal_corridors[i][0], y0 = cal_corridors[i][1], x1 = cal_corridors[i][2], y1 = cal_corridors[i][3];
		for (x = x0; x != x1; x += x1 > x0 ? 1 : -1)
			setlev(x, y0, CORR);
		for (y = y0; y != y1; y += y1 > y0 ? 1 : -1)
			setlev(x1, y, CORR);
		setlev(x1, y1, CORR);
	}
	levl[25][5].typ = levl[26][5].typ = POOL;
	levl[50][14].typ = FOUNTAIN;

	for (i = 0; i < (int) (NELEM(cal_traps)); i++) {
		trapv[i].tx = cal_traps[i][0]; trapv[i].ty = cal_traps[i][1]; trapv[i].ttyp = cal_traps[i][2];
		trapv[i].ntrap = ftrap; ftrap = &trapv[i];
	}
	for (i = 0; i < (int) (NELEM(cal_objs)); i++) {
		struct obj_s *o = &objv[i];
		o->otyp = cal_objs[i][2]; o->ox = cal_objs[i][0]; o->oy = cal_objs[i][1]; o->owt = 10;
		o->where = OBJ_FLOOR;
		o->nexthere = level.objects[o->ox][o->oy];
		level.objects[o->ox][o->oy] = o;
	}
	for (i = 0; i < (int) (NELEM(cal_standing)); i++) {
		struct monst_s *m = &monv[i];
		m->data = &mons[cal_standing[i][2]];
		m->mx = cal_standing[i][0]; m->my = cal_standing[i][1];
		m->mux = u.ux; m->muy = u.uy;
		m->mcansee = m->mcanmove = 1;
		if (cal_standing[i][2] == PM_LITTLE_DOG)
			m->mtame = 10, m->mpeaceful = 1;
		level.monsters[m->mx][m->my] = m;
	}
	for (i = 0; i < NSUBJ; i++) {
		struct monst_s *m = &subjv[i];
		m->data = &mons[subjects[i]];
		m->mux = u.ux; m->muy = u.uy;
		m->mcansee = m->mcanmove = 1;
		if (subjects[i] == PM_LITTLE_DOG) {
			m->mtame = 10, m->mpeaceful = 1;
			subjflags[i] = ALLOW_M | ALLOW_TRAPS | ALLOW_SSM | ALLOW_SANCT;
		} else {
			subjflags[i] = ALLOW_U;
			if (subjects[i] == PM_HILL_ORC || subjects[i] == PM_GNOME_LORD)
				subjflags[i] |= OPENDOOR;
		}
		if (subjects[i] == PM_JACKAL)
			m->mtrapseen = 1L << (ARROW_TRAP - 1);
	}
}

/* one more call of each extracted function, in every build.  Oscar64 inlines a function that
   has one call site (with -Os), and in the game each has many; WORK=0 makes these calls too,
   so they cancel out.  (mm_aggression() is static in mon.c, with one caller in the game too.) */
long touched;

static void
touch(void)
{
	coord poss[9];
	long info[9], t = 0L;
	struct monst_s *m = &subjv[0];

	t += isok(1, 1) + dist2(1, 1, 2, 2) + distmin(1, 1, 2, 2) + online2(1, 1, 2, 2);
	t += is_pool(1, 1) + is_lava(1, 1) + on_level(&u.uz, &u.uz);
	t += (strstri("Elbereth", "bere") != 0) + lowc('A');
	m->mx = 5; m->my = 5;
	t += mfndpos(m, poss, info, ALLOW_U);
	t += curr_mon_load(m) + may_passwall(1, 1) + may_dig(1, 1) + bad_rock(m->data, 1, 1);
	t += onscary(5, 5, m) + sengr_at("Elbereth", 5, 5) + (engr_at(5, 5) != 0);
	t += (sobj_at(BOULDER, 40, 6) != 0) + (t_at(5, 3) != 0) + (m_carrying(m, PICK_AXE) != 0);
	t += which_armor(m, W_ARMS) != 0;
	touched = t;
}

int
main(void)
{
	long sum = 0L, calls = 0L;
	int x, y, pass;

	setup();
	touch();
#if WORK == 1
	for (pass = 0; pass < 10; pass++)
		for (y = -2; y <= ROWNO + 1; y++)
			for (x = -2; x <= COLNO + 1; x++)
				sum += isok(x, y), calls++;
#elif WORK == 2
	for (pass = 0; pass < 4; pass++)
		for (y = 0; y < ROWNO; y++)
			for (x = 1; x < COLNO; x++)
				sum += dist2(x, y, u.ux, u.uy) + dist2(x, y, 70, 18), calls += 2;
#elif WORK == 3
	for (pass = 0; pass < 5; pass++)
		for (y = 0; y < ROWNO; y++)
			for (x = 1; x < COLNO; x++)
				sum += is_pool(x, y) + 2 * is_lava(x, y), calls += 2;
#elif WORK == 4
	{
		coord poss[9];
		long info[9];
		int i, j, n;

		for (pass = 0; pass < 1; pass++)
			for (y = 0; y < ROWNO; y++)
				for (x = 1; x < COLNO; x++) {
					if (IS_ROCK(levl[x][y].typ) || level.monsters[x][y])
						continue;
					for (i = 0; i < NSUBJ; i++) {
						struct monst_s *m = &subjv[i];
						m->mx = x; m->my = y;
						level.monsters[x][y] = m;
						n = mfndpos(m, poss, info, subjflags[i]);
						level.monsters[x][y] = (struct monst_s *) 0;
						sum += n, calls++;
						for (j = 0; j < n; j++)
							sum += (long) (((unsigned long) info[j] >> 16) & 0xffffL) + poss[j].x + poss[j].y;
					}
				}
	}
#endif
	(void) x; (void) y; (void) pass;
	printf("work %d calls %ld sum %ld touched %ld\n", WORK, calls, sum, touched);
	return 0;
}
