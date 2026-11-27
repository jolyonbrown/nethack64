/* nh_calls.c - every call and return of the host game, for tools/measure/trace/window.py
 * (tools/host-build.sh --calls): which calls make the C128's bank window load an REU bank.
 *
 * gcc's -finstrument-functions calls these two hooks at each function's entry and exit.
 * Each event is one 32-bit word: the function's address less the executable's start
 * (__executable_start, written first as 8 bytes), shifted left one, with
 * the low bit 1 for an entry and 0 for an exit. The words go to the file NH_CALLS_OUT
 * (none written without it). This file is built without the instrumentation.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

static FILE *out;
static int tried;
extern char __executable_start;
static uintptr_t base;
static uint32_t buf[1 << 16];
static unsigned n;

static void flush_out(void)
{
	if (out && n)
		fwrite(buf, sizeof buf[0], n, out);
	n = 0;
	if (out)
		fflush(out);
}

static void put(void *fn, uint32_t enter)
{
	if (!tried) {
		const char *p = getenv("NH_CALLS_OUT");
		tried = 1;
		if (p && (out = fopen(p, "wb")) != 0) {
			base = (uintptr_t) &__executable_start;
			fwrite(&base, sizeof base, 1, out);	/* the base first, 8 bytes */
			atexit(flush_out);
		}
	}
	if (!out)
		return;
	buf[n++] = (uint32_t) (((uintptr_t) fn - base) << 1) | enter;
	if (n == sizeof buf / sizeof buf[0])
		flush_out();
}

void __cyg_profile_func_enter(void *fn, void *site) { (void) site; put(fn, 1); }
void __cyg_profile_func_exit(void *fn, void *site) { (void) site; put(fn, 0); }
