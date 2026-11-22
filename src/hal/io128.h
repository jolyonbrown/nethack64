/*
 * io128.h - the C128's I/O around a hardware access, for code that runs with the I/O out.
 *
 * The banked game runs with the MMU at $3B (the cartridge at $8000-$BFFF, RAM at $D000-$DFFF:
 * bankgen.py --io-out, T2.13), so the HAL switches the I/O in for each access to the VDC or a
 * CIA and puts back whatever configuration it found (the cartridge's $3B, or $3F with an REU
 * bank in the window). Built with HAL_IO_OUT for the game; without it (the Phase 0 demo, the
 * MMU at $3E with the I/O in throughout) these do nothing.
 * Code that uses them must not run from $D000-$DFFF: switching the I/O in there would replace
 * the code under the CPU. The game's plan keeps the HAL in cartridge banks ($8000-$BFFF).
 */
#ifndef IO128_H
#define IO128_H

#ifdef HAL_IO_OUT
#define IO_IN()		char io128_mmu = *(volatile char *)0xff00; *(volatile char *)0xff00 = io128_mmu & 0xfe
#define IO_OUT()	(*(volatile char *)0xff00 = io128_mmu)
#else
#define IO_IN()		do { } while (0)
#define IO_OUT()	do { } while (0)
#endif

#endif
