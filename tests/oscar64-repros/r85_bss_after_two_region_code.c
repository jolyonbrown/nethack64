/* OSCAR64 REPRO r85 - THE BSS IS NOT CLEARED WHEN THE CODE SECTION SPANS TWO REGIONS.
 * A region declared before main that holds code (as nethack64's C128 layout does, $C000 up),
 * and the rest of the code in main: Linker::PlaceObjects() raised the main region's end of
 * loaded data to the code section's end, which lies in the other region, so the BSS section
 * was moved there: BSSStart = BSSEnd = that end, and the start-up code cleared none of the
 * BSS. Every zero-initialised global then starts with what the RAM held. C89 3.5.7: an object
 * of static storage duration not explicitly initialised is initialised to zero.
 * NetHack: the C128 game (fc22) ran out of heap at its first allocations: malloc's HeapNode,
 * in the BSS, held garbage. The pin (87 commits) and the far fork to 948d9bc, 2026-11-22.
 * Expect when fixed: "Emulation result 0".
 * Workaround: clear the BSS in main(); the far fork's commit 16 fixes the linker.
 * FLAGS: -e -n
 */
#pragma region(hi, 0xc000, 0xc040, , , { code })
#pragma region(main, 0x0900, 0x8000, , , { code, data, bss, heap, stack })

extern void BSSStart, BSSEnd;
int counts[40];
volatile unsigned va;
#define ADDR(x) (va = (unsigned)&x, va)

/* small enough for the high region, so that code is placed there first */
__noinline int work(int i)
{
	counts[i % 40] += i;
	return counts[i % 40];
}

__noinline int more(int a, int b)
{
	int k, s = 0;
	for (k = 0; k < a; k++)
		s += (k * b) ^ (s >> 3) ^ counts[k % 40];
	return s;
}

int main(void)
{
	unsigned s = ADDR(BSSStart), e = ADDR(BSSEnd), c = ADDR(counts);
	if (work(3) != 3 || more(5, 2) != more(5, 2))
		return 2;
	return s < e && s <= c && c + sizeof(counts) <= e ? 0 : 1;
}
