/*
 * sys.h - machine bring-up, hardware detection and test hooks.
 *
 * Everything here is deliberately small and dependency-free so it can sit
 * in the always-resident common area once the real game is banked.
 */
#ifndef HAL_SYS_H
#define HAL_SYS_H

#include <c64/types.h>

/* Bring the KERNAL up the way a cartridge must (IOINIT, RESTOR, CINT) but
 * without RAMTAS, which would wipe the zero page Oscar64 already set up.
 * After this, GETIN/SETLFS/LOAD/SAVE and the keyboard IRQ all work.
 * Safe to call from a .prg build too (it just re-initialises). */
void sys_init(void);

/* Read one key from the KERNAL keyboard buffer, translated to ASCII.
 * Returns 0 when no key is waiting.  Cursor keys come back as the
 * NetHack vi-keys (h j k l) so the map code never sees PETSCII. */
char sys_getkey(void);

/* Block until a key arrives. */
char sys_waitkey(void);

/* REU: returns number of 64KB banks found (0 = no REU).  Uses a real DMA
 * round trip, so a cartridge with RAM at $DF00 cannot fool it. */
unsigned sys_reu_banks(void);

/* Running from an EasyFlash cartridge image? (compile-time for now). */
bool sys_on_easyflash(void);

/* VICE debug cartridge (-debugcart): writing to $D7FF ends the emulator
 * with that value as its process exit code.  Harmless on real hardware
 * ($D7FF is a VIC-II register mirror there, so only call it in test builds). */
void sys_debug_exit(char code);

#endif
