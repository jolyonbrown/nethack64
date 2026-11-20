/* bankstr.c - strings passed between banks through bankgen.py's split string trampolines
 * (T2.12, docs/BANKING-SPIKE.md).  tests/spikes/run_bankstr.py writes nhbank.h and the
 * wrappers (bankstr_w.c) with bankgen.py's own code, then builds and runs this in VICE.
 *
 * A literal is only readable while its bank is mapped, so a call from bank 2 to a
 * function of bank 16 goes through f__t2 (in bank 2: copies the string arguments onto a
 * stack, released when the call returns) and f__x16 (in bank 16: copies a string result).
 * The failures Codex's review of 2026-11-19 reproduced, each a check here:
 *   - a literal passed on uncopied (Oscar64 folded the window test, compat #79);
 *   - an argument overwritten by nested copies while its call still runs;
 *   - a result wrapper calling its function twice (a macro evaluating its argument twice);
 * and a result that is the copied argument itself, which must outlive the release.
 * spike_result[0]: the checks passed (bits), [1] the checks run.
 */
#include <c64/cia.h>
#include <c64/memmap.h>

#pragma region( main, 0x0900, 0x8000, , , { code, data, bss, heap, stack } )

#define NHBANK_DEFINE
#include "nhbank.h"

volatile unsigned spike_result[4];
volatile char spike_done;

volatile unsigned calls;
volatile char c_entry, c_after, c_nested, seen3;
char target[8] = "target";

void consume__t16(const char *);
void consume__t2(const char *);
void hold__t2(const char *);
char *produce__x16(void);
const char *ident__t2(const char *);

#pragma code( nhbank_3 )

__noinline void consume__b3(const char *s)
{
	seen3 = s[0];
}

#pragma code( nhbank_16 )

__noinline char *produce__b16(void)
{
	calls++;
	return target;
}

/* nested calls that each copy a literal of this bank, while `s` is still in use */
__noinline void hold__b16(const char *s)
{
	c_entry = ((const volatile char *)s)[0];	/* read again after the calls */
	for (char i = 0; i < 6; i++)
		consume__t16("replacement");
	c_after = ((const volatile char *)s)[0];
	c_nested = seen3;
}

__noinline const char *ident__b16(const char *s)
{
	return s;
}

#pragma code( nhbank_2 )

volatile char *r_produce;
volatile char r_ident[4];

__noinline void start(void)
{
	hold__t2("original");
	r_produce = produce__x16();
	const char *p = ident__t2("lit");
	/* the copy p points to was released: another call's copies must not overwrite it */
	consume__t2("xyzzy");
	for (char i = 0; i < 4; i++)
		r_ident[i] = p[i];
}

#pragma code( code )

#include "bankstr_w.c"

unsigned passed, ran;

__noinline void check(unsigned bit, char ok)
{
	ran |= bit;
	if (ok)
		passed |= bit;
}

int main(void)
{
	mmap_set(MMAP_ROM);
	cia_init();

	start();
	check(0x01, c_entry == 'o');
	check(0x02, c_after == 'o');
	check(0x04, c_nested == 'r' && seen3 == 'x');
	check(0x08, calls == 1 && r_produce == target);
	check(0x10, r_ident[0] == 'l' && r_ident[1] == 'i' && r_ident[2] == 't' && r_ident[3] == 0);
	check(0x20, nh_args_top == 0);
	check(0x40, nh_bank == 0);

	spike_result[0] = passed;
	spike_result[1] = ran;
	spike_done = 1;
	for (;;)
		;
	return 0;
}
