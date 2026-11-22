/*	c64main.c	NetHack 3.4.3 for the Commodore 64 and C128 (Oscar64)	*/
/* NetHack may be freely redistributed.  See license for details. */

/*
 * The game's entry (T3.2), as sys/share/pcmain.c makes it, for the bootable build
 * (tools/bank/build_c64.py --main port, which defines NH_PORT_MAIN): the hardware first
 * (src/hal), then NetHack's start in pcmain.c's order. No command line, no lock file (one
 * player, one machine) and, until the file layer (T2.4), no saved game to restore.
 */
#include "hack.h"

#if defined(__OSCAR64C__) && defined(NH_PORT_MAIN)
#include "dlb.h"

extern void sys_init(void);		/* src/hal/sys128.c */
extern void nh_far_init(void);		/* the far runtime (tools/bank/farrt.py) */

int
main(void)
{
	int argc = 1;
	/* a named array: a literal would be in the character space, which a near char * table
	 * cannot hold (ADR-0010) */
	static char arg0[] = "nethack";
	static char *argv[] = { arg0, (char *) 0 };

	sys_init();
	nh_far_init();

	hname = "NetHack";
	hackpid = 1;
	choose_windows(DEFAULT_WINDOW_SYS);
	initoptions();
	init_nhwindows(&argc, argv);
	if (!*plname)
		askname();
	plnamesuffix();		/* strip suffix from name; calls askname() */
	x_maze_max = COLNO - 1;	/* unixmain.c's */
	if (x_maze_max % 2)
		x_maze_max--;
	y_maze_max = ROWNO - 1;
	if (y_maze_max % 2)
		y_maze_max--;

	/* the vision system before mklev() (pcmain.c) */
	vision_init();
	dlb_init();
	display_gamewindows();

	player_selection();
	newgame();
	flags.move = 0;
	set_wear();
	(void) pickup(1);
	read_engr_at(u.ux, u.uy);

	moveloop();
	return 0;
}

#endif /* __OSCAR64C__ && NH_PORT_MAIN */
