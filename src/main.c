/*
 * Phase 0 toolchain test for the NetHack C64 port.
 *
 * Proves, on every build target:
 *   - Oscar64 code runs from an EasyFlash .crt (and as a plain .prg)
 *   - the KERNAL can be brought up from a cartridge start (keyboard works)
 *   - the software 80x25 screen renders a NetHack-shaped layout:
 *       row 0 messages, rows 1-21 the 80x21 map, rows 22-23 status, row 24 info
 *   - an REU, if present, is detected by real DMA and can hold a level
 *
 * Keys: h j k l y u b n (or cursor keys) move the @,
 *       s = stash the map to REU, c = clear the map, r = restore it from REU,
 *       q = quit (resets the machine).
 *
 * Build with -dAUTOTEST for the unattended self-test: it runs a scripted
 * walk and an REU round trip, then exits VICE through the debug cartridge
 * with code 0 (pass) or a failure number.  See tools/vice.py and tests/.
 */
#include "hal/sys.h"
#include "hal/screen80.h"
#include <c64/reu.h>
#include <string.h>
#include <stdio.h>

#ifdef OSCAR_TARGET_CRT_EASYFLASH
/* EasyFlash: bank 0 is copied to RAM at boot, then cartridge ROM stays
 * visible at $8000-$BFFF.  Oscar64's default "main" region runs to $A000,
 * which would put the heap and stack under ROM, so it must end at $8000.
 * (This mirrors oscar64/samples/memmap/easyflash.c.)  The bitmap and colour
 * matrix live at $C000+ - see hal/screen80.h. */
#pragma region( main, 0x0900, 0x8000, , , { code, data, bss, heap, stack } )
#endif

#define MAP_Y0	1		/* map occupies rows 1..21 like NetHack's 80x21 */
#define MAP_ROWS 21

/* a single room plus a corridor, drawn in NetHack's default symbols */
static const char *const room[] = {
	"",
	"",
	"                 -----------                                     ",
	"                 |.........|                                     ",
	"                 |....$....|           ####                      ",
	"                 |.........+############  #                      ",
	"                 |.........|              #     -------          ",
	"                 |....>....|              ######+.....|          ",
	"                 |.........|                    |.....|          ",
	"                 -----------                    -------          ",
	0
};

static char px = 22, py = MAP_Y0 + 5;	/* the @ */
static unsigned reu_banks;
static char under = '.';			/* what the @ is standing on */
static char msg[81];

static void message(const char *s)
{
	s80_gotoxy(0, 0);
	s80_puts(s);
	s80_clear_eol();
}

static void draw_map(void)
{
	for (char y = 0; room[y]; y++)
		s80_puts_at(0, MAP_Y0 + y, room[y]);
	under = s80_text[(unsigned)py * S80_COLS + px];
	s80_putc_at(px, py, '@');
	s80_color_cells(px, py, 1, 1);		/* white */
}

static void draw_status(void)
{
	s80_puts_at(0, 22, "Agent the Stripling      St:16 Dx:14 Co:17 In:9 Wi:10 Ch:8  Neutral");
	s80_puts_at(0, 23, "Dlvl:1 $:0 HP:14(14) Pw:1(1) AC:6 Xp:1/0 T:1");
	sprintf(msg, "REU: %u x 64KB   cart: %s   80x25 soft text   oscar64",
		reu_banks, sys_on_easyflash() ? "EasyFlash" : "none (prg)");
	s80_puts_at(0, 24, msg);
}

static bool walkable(char c)
{
	return c == '.' || c == '#' || c == '+' || c == '$' || c == '>';
}

static void try_move(signed char dx, signed char dy)
{
	char nx = px + dx, ny = py + dy;
	char c = s80_text[(unsigned)ny * S80_COLS + nx];
	if (ny < MAP_Y0 || ny >= MAP_Y0 + MAP_ROWS || !walkable(c))
	{
		message("You can't move there.");
		return;
	}
	s80_color_cells(px, py, 1, 15);
	s80_putc_at(px, py, under);
	under = c;
	px = nx;
	py = ny;
	s80_putc_at(px, py, '@');
	s80_color_cells(px, py, 1, 1);
	if (c == '$')
		message("You see here 37 gold pieces.");
	else if (c == '>')
		message("There is a staircase down here.");
	else
		message("");
}

/* the map is 21 rows x 80 = 1680 bytes: stash it at REU offset 64KB */
#define REU_LEVEL_SLOT 0x010000ul
#define MAP_BYTES (MAP_ROWS * S80_COLS)

static bool stash_level(void)
{
	if (!reu_banks)
		return false;
	reu_store(REU_LEVEL_SLOT, s80_text + MAP_Y0 * S80_COLS, MAP_BYTES);
	return true;
}

static void redraw_rows(char y0, char rows)
{
	for (char y = y0; y < y0 + rows; y++)
		for (char x = 0; x < S80_COLS; x++)
			s80_putc_at(x, y, s80_text[(unsigned)y * S80_COLS + x]);
}

static bool restore_level(void)
{
	if (!reu_banks)
		return false;
	reu_load(REU_LEVEL_SLOT, s80_text + MAP_Y0 * S80_COLS, MAP_BYTES);
	redraw_rows(MAP_Y0, MAP_ROWS);
	return true;
}

static void clear_level(void)
{
	memset(s80_text + MAP_Y0 * S80_COLS, ' ', MAP_BYTES);
	redraw_rows(MAP_Y0, MAP_ROWS);
}

static bool handle_key(char k)
{
	switch (k)
	{
	case 'h': try_move(-1, 0); break;
	case 'l': try_move(1, 0); break;
	case 'k': try_move(0, -1); break;
	case 'j': try_move(0, 1); break;
	case 'y': try_move(-1, -1); break;
	case 'u': try_move(1, -1); break;
	case 'b': try_move(-1, 1); break;
	case 'n': try_move(1, 1); break;
	case 's': message(stash_level() ? "Level stashed in the REU." : "No REU."); break;
	case 'c': clear_level(); message("Map cleared (r restores from the REU)."); break;
	case 'r': message(restore_level() ? "Level restored from the REU." : "No REU."); break;
	case 'q': return false;
	}
	return true;
}

#ifdef AUTOTEST
/* Failure codes are visible as the VICE process exit status. */
enum { T_PASS = 0, T_WALK = 2, T_BLOCK = 3, T_REU_DMA = 4, T_REU_RESTORE = 5 };

static char autotest(void)
{
	/* walk: 3 right, 2 down, 3 left -> standing on the down stairs */
	const char *walk = "llljjhhh";
	for (const char *p = walk; *p; p++)
		handle_key(*p);
	if (px != 22 || py != MAP_Y0 + 7 || under != '>')
		return T_WALK;

	/* walls block movement */
	for (char i = 0; i < 20; i++)
		handle_key('j');
	if (py != MAP_Y0 + 8)
		return T_BLOCK;

	/* REU: stash, wipe, restore, compare (skipped when no REU attached) */
	if (reu_banks)
	{
		static char copy[MAP_BYTES];
		memcpy(copy, s80_text + MAP_Y0 * S80_COLS, MAP_BYTES);
		if (!stash_level())
			return T_REU_DMA;
		clear_level();
		restore_level();
		if (memcmp(copy, s80_text + MAP_Y0 * S80_COLS, MAP_BYTES))
			return T_REU_RESTORE;
	}
	return T_PASS;
}
#endif

int main(void)
{
	sys_init();
	reu_banks = sys_reu_banks();

	s80_init(15, 0);	/* light grey on black, like a NetHack tty */
	draw_map();
	draw_status();
	message("Hello Agent, welcome to NetHack-C64!  You are a neutral human Valkyrie.");

#ifdef AUTOTEST
	{
		char rc = autotest();
		message(rc ? "AUTOTEST FAIL" : "AUTOTEST PASS");
		sys_debug_exit(rc);
	}
#endif

	while (handle_key(sys_waitkey()))
		;

	__asm {
		jmp ($fffc)
	}
	return 0;
}
