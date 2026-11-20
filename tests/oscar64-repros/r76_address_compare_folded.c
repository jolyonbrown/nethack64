/* OSCAR64 REPRO r76 - AN OBJECT'S ADDRESS COMPARED WITH A CONSTANT IS FOLDED: when the
 * optimizer knows which object a pointer points to, `(unsigned)p >= 0x8000` becomes false
 * at compile time, wherever the object is placed.  Here `arr` is linked at $A000, and
 * check() is called only with it, so the constant argument is propagated into check(): at
 * -O0 both tests count (hits 11), at -Os and -O2 the first is dropped (hits 10; the
 * listing tests only the address's high byte against zero, for the second).
 * v1.32.273, the pin (to commit 83), upstream 4da3147.
 * NetHack: the banked build's string wrappers (tools/bank/bankgen.py) copy an argument
 * only if it points into the bank window, NH_IN_WINDOW(p); a wrapper called with a literal
 * passed it on uncopied, to be read with another bank mapped (found by Codex's review,
 * 2026-11-19, in VICE).
 * Expect when fixed: hits 11 at every optimisation level (exit 0).
 * Workaround: compare the address after it has been through a volatile (nhbank.h's
 * nh_addr).
 * FLAGS: -n -Os -e
 */
#include <stdio.h>

#pragma section( hi, 0 )
#pragma region( hir, 0xa000, 0xb000, , , { hi } )

volatile int hits;

#pragma data( hi )
char arr[4] = "abc";
#pragma data( data )

__noinline void check(const char * p)
{
	if ((unsigned)p >= 0x8000u)
		hits++;
	if ((unsigned)p >= 1u)
		hits += 10;
}

int main(void)
{
	check(arr);
	printf("hits %d\n", hits);
	return hits == 11 ? 0 : 1;
}
