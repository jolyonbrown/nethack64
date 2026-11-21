/* c128ef.c - spike: can a C128 in its own mode (not C64 mode) bank an EasyFlash cartridge?
 * (T2.12, the hardware discussion; ADR-0003.)
 *
 * In C128 mode the cartridge port's GAME and EXROM lines do not map memory: the MMU does, and
 * its configuration register can put "external function ROM" at $8000-$BFFF (mid) and at
 * $C000-$FFFF (high), which the C128 reads from the cartridge port. Whether an EasyFlash then
 * shows its banks there, and switches them through $DE00, is what this measures.
 * run_c128ef.py makes an EasyFlash image whose bank b holds 0x80|b in every byte of its ROML
 * chip and 0xC0|b in every byte of its ROMH chip, attaches it with the boot jumper off (the
 * C128 then starts in C128 mode), and autostarts this program.
 *
 * spike_d505: $D505 as read at the start (bit 6 set = C64 mode; bits 4/5 the GAME and EXROM
 *             lines), and whether the program ran at all (spike_done).
 * spike_read[mode][cfg][bank][addr]: what $8000, $A000, $C000 and $E000 read, with the RAM
 *             there filled with 0x11 beforehand; mode is $DE02 = $04 (cartridge "off") or $07
 *             (16K), cfg is the MMU at $2A (external ROM mid and high, I/O in) or $3A (mid
 *             only); banks 0, 1, 2, 31, 62, 63.
 * spike_reu:  1 when an REU round trip of 256 bytes, with the EasyFlash banked in, came back.
 * $DF00-$DFFF is never read (the REU's and EasyFlash RAM's page; AGENTS.md). */
#include <c128/mmu.h>
#include <c64/reu.h>
#include <string.h>

#pragma region( main, 0x1d00, 0x4000, , , { code, data, bss, heap, stack } )

#define EF_BANK (*(volatile char *)0xde00)
#define EF_CTRL (*(volatile char *)0xde02)

static const char banks[6] = { 0, 1, 2, 31, 62, 63 };
static const char modes[2] = { 0x04, 0x07 };
static const char cfgs[2] = { 0x2a, 0x3a };
static const unsigned addrs[4] = { 0x8000, 0xa000, 0xc000, 0xe000 };

volatile char spike_read[2][2][6][4];
volatile char spike_d505;
volatile char spike_reu;
volatile char spike_done;

static char buf[256], back[256];

int main(void)
{
	__asm { sei }
	mmu.cr = 0x3e;
	spike_d505 = *(volatile char *)0xd505;

	for (char m = 0; m < 2; m++)
		for (char c = 0; c < 2; c++)
			for (char b = 0; b < 6; b++)
			{
				mmu.cr = 0x3f;		/* all RAM: mark what is under the ROM */
				for (char a = 0; a < 4; a++)
					*(volatile char *)addrs[a] = 0x11;
				mmu.cr = 0x3e;
				EF_CTRL = modes[m];
				EF_BANK = banks[b];
				mmu.cr = cfgs[c];
				for (char a = 0; a < 4; a++)
					spike_read[m][c][b][a] = *(volatile char *)addrs[a];
				mmu.cr = 0x3e;
			}

	/* the REU with the EasyFlash banked in (16K mode, bank 5) */
	EF_CTRL = 0x07;
	EF_BANK = 5;
	for (unsigned i = 0; i < 256; i++)
		buf[i] = (char)(i * 3 + 1);
	reu_store(0x20000ul, buf, 256);
	memset(back, 0, 256);
	reu_load(0x20000ul, back, 256);
	spike_reu = memcmp(buf, back, 256) == 0;
	EF_CTRL = 0x04;

	mmu.cr = 0x3f;
	spike_done = 1;
	for (;;)
		;
	return 0;
}
