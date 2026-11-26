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
#include "hal/rng.h"
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
#ifdef __C128__
	sprintf(msg, "REU: %u x 64KB   C128, 80 columns on the VDC   oscar64", reu_banks);
#else
	sprintf(msg, "REU: %u x 64KB   cart: %s   80x25 soft text   oscar64",
		reu_banks, sys_on_easyflash() ? "EasyFlash" : "none (prg)");
#endif
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
#ifdef __C128__
char sys128_decode(const char *down, char joy);	/* src/hal/sys128.c */
#endif

/* Failure codes are visible as the VICE process exit status. */
enum { T_PASS = 0, T_WALK = 2, T_BLOCK = 3, T_REU_DMA = 4, T_REU_RESTORE = 5, T_RNG = 6,
       T_REU_PROBE = 7, T_PUTCA = 8, T_KEYS = 9 };

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

	/* lrand48() gives glibc's numbers (T2.7): the first three and the 1000th after
	   srand48(1731700000), and the first after srand48(-1), a seed of all 32 bits
	   (values from glibc 2.39; tools/check_rng.py runs 20,000 a seed in the emulator) */
	srand48(1731700000L);
	if (lrand48() != 0x0b23b8beL || lrand48() != 0x571fc6d0L || lrand48() != 0x605807daL)
		return T_RNG;
	for (int i = 3; i < 999; i++)
		lrand48();
	if (lrand48() != 0x4e4ab753L)
		return T_RNG;
	srand48(-1L);
	if (lrand48() != 0x26673e37L)
		return T_RNG;

	/* s80_putca: a character with its attribute, in the shadow (and on the C64 the pair's
	   colour in the colour matrix), then the cell put back as it was */
	{
		char old = s80_text[24 * S80_COLS + 79];
		s80_putca(79, 24, 'Z', 7 | S80_REVERSE);
		if (s80_text[24 * S80_COLS + 79] != 'Z')
			return T_PUTCA;
#ifndef __C128__
		if ((S80_COLORMAP[24 * 40 + 39] >> 4) != 7)
			return T_PUTCA;
#endif
		s80_putca(79, 24, old, 15);
		if (s80_text[24 * S80_COLS + 79] != old)
			return T_PUTCA;
#ifndef __C128__
		if ((S80_COLORMAP[24 * 40 + 39] >> 4) != 15)
			return T_PUTCA;
#endif
	}

	/* the keyboard buffer's PETSCII as the game sees it: the left arrow is '_' (travel),
	   RUN/STOP ESC, CRSR-DOWN 'j', a shifted letter upper case (docs/TO-DECIDE.md) */
	{
#ifdef __C128__
		volatile char *buf = (volatile char *)0x034a, *count = (volatile char *)0x00d0;
#else
		volatile char *buf = (volatile char *)0x0277, *count = (volatile char *)0x00c6;
#endif
		static const char in[4] = { 95, 3, 17, 193 }, out[4] = { '_', 27, 'j', 'A' };
		for (char i = 0; i < 4; i++)
			buf[i] = in[i];
		*count = 4;
		for (char i = 0; i < 4; i++)
			if (sys_getkey() != out[i])
				return T_KEYS;
	}
#ifdef __C128__
	/* the C128's matrix and joystick decoding, on made-up scans (VICE cannot press keys
	   from the monitor): KP6, shift + KP7, ESC, left arrow; the stick up-left, fire alone,
	   fire with right; each step a scan, then all keys up */
	{
		static const char col[9] = { 9, 8, 9, 7, 0, 0, 0, 0, 0 };
		static const char bit[9] = { 0x20, 0x40, 0x01, 0x02, 0, 0, 0, 0, 0 };
		static const char joy[9] = { 0, 0, 0, 0, 5, 16, 0, 16, 24 };
		static const char want[9] = { 'l', 'Y', 27, '_', 'y', 0, 's', 0, 'L' };
		static const char after[9] = { 0, 0, 0, 0, 0, 's', 0, 0, 0 };
		static char down[11];
		for (char t = 0; t < 9; t++)
		{
			memset(down, 0, sizeof(down));
			down[col[t]] = bit[t];
			if (t == 1)
				down[1] |= 0x80;		/* left shift */
			if (sys128_decode(down, joy[t]) != want[t])
				return T_KEYS;
			if (t == 5 || t == 7)
				continue;				/* fire stays down for the next step */
			memset(down, 0, sizeof(down));
			if (sys128_decode(down, 0) != after[t])
				return T_KEYS;
		}
	}
#endif

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

		/* the size probe again: the same size, and the bytes it uses unchanged (at
		 * offset 0 and at 128 KB, both of which it writes) */
		static volatile char tag[8], back[8];
		for (int i = 0; i < 8; i++)
			tag[i] = 0x3c + i * 11;
		reu_store(0x000000ul, tag, 8);
		reu_store(0x020000ul, tag, 1);
		if (sys_reu_banks() != reu_banks)
			return T_REU_PROBE;
		reu_load(0x000000ul, back, 8);
		for (int i = 0; i < 8; i++)
			if (back[i] != tag[i])
				return T_REU_PROBE;
		reu_load(0x020000ul, back, 1);
		if (back[0] != tag[0])
			return T_REU_PROBE;
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

#ifdef __C128__
	/* the C128 runs with all RAM mapped (sys128.c): the ROMs back for the reset vector */
	*(volatile char *)0xff00 = 0x00;
#endif
	__asm {
		jmp ($fffc)
	}
	return 0;
}
