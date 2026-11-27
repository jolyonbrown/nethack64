/*	c64main.c	NetHack 3.4.3 for the Commodore 64 and C128 (Oscar64)	*/
/* NetHack may be freely redistributed.  See license for details. */

/*
 * The game's entry (T3.2), as sys/share/pcmain.c makes it, for the bootable build
 * (tools/bank/build_c64.py --main port, which defines NH_PORT_MAIN): the hardware first
 * (src/hal), then NetHack's start in pcmain.c's order. No command line and no lock check (one
 * player, one machine). A saved game is restored as pcmain.c does: restore_saved_game() also
 * names the save file (set_savefile_name()), without which dosave0() gives up at once.
 */
#include "hack.h"

#if defined(__OSCAR64C__) && defined(NH_PORT_MAIN)
#include "dlb.h"

extern void sys_init(void);		/* src/hal/sys128.c */
#ifdef __C128__
extern void sys128_speed(char);	/* src/hal/sys128.c: 2 MHz; each REU transfer drops to 1 */
#endif
extern void s80_init(char, char);	/* src/hal/vdc80.c: the VDC's font, colours, a clear screen */
extern void nh_far_init(void);		/* the far runtime (tools/bank/farrt.py) */

void nh_c64_start(void);

/* main() is resident, and Oscar64 inlines a function called once into a caller in the same
 * section: so the start is a function of its own, which the plan banks */
int
main(void)
{
	sys_init();
#ifdef __C128__
	sys128_speed(1);
#endif
	nh_far_init();
	s80_init(15, 0);	/* light grey on black, as src/main.c's demo (a banked function) */
	nh_c64_start();
	return 0;
}

void
nh_c64_start(void)
{
	int argc = 1, fd;
	/* a named array: a literal would be in the character space, which a near char * table
	 * cannot hold (ADR-0010) */
	static char arg0[] = "nethack";
	static char *argv[] = { arg0, (char *) 0 };

	hname = "NetHack";
	hackpid = 1;
	choose_windows(DEFAULT_WINDOW_SYS);
	initoptions();
	init_nhwindows(&argc, argv);
	if (!*plname)
		askname();
	plnamesuffix();		/* strip suffix from name; calls askname() */

	/* pcmain.c without PC_LOCKING: the level files are named from the player, and level 0
	 * (the game state's file, which INSURANCE's save_currentstate() writes) is made now */
	Strcpy(lock, plname);
	Strcat(lock, ".99");
	regularize(lock);
	fd = create_levelfile(0, (char *) 0);
	if (fd < 0) {
		raw_print("Cannot create lock file");
	} else {
		hackpid = 1;
		write(fd, (genericptr_t) &hackpid, sizeof(hackpid));
		close(fd);
	}

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

	if ((fd = restore_saved_game()) >= 0) {
#ifdef WIZARD
		/* Since wizard is actually flags.debug, restoring might
		 * overwrite it.
		 */
		boolean remember_wiz_mode = wizard;
#endif
#ifdef NEWS
		if(iflags.news){
		    display_file(NEWS, FALSE);
		    iflags.news = FALSE;
		}
#endif
		pline("Restoring save file...");
		mark_synch();	/* flush output */

		if(!dorecover(fd))
			goto not_recovered;
#ifdef WIZARD
		if(!wizard && remember_wiz_mode) wizard = TRUE;
#endif
		check_special_room(FALSE);
		if (discover)
			You("are in non-scoring discovery mode.");

		if (discover || wizard) {
			if(yn("Do you want to keep the save file?") == 'n'){
				(void) delete_savefile();
			}
		}

		flags.move = 0;
	} else {
not_recovered:
		player_selection();
		newgame();
		if (discover)
			You("are in non-scoring discovery mode.");

		flags.move = 0;
		set_wear();
		(void) pickup(1);
		read_engr_at(u.ux,u.uy);
	}

	moveloop();
}

#endif /* __OSCAR64C__ && NH_PORT_MAIN */
