/* OSCAR64 REPRO r78 - WRONG CODE: A FIELD READ FROM THE NEXT OBJECT.  In
 * `for (; o; o = o->nobj) s += o->oclass;` the field's load and the next pointer's load go
 * through the same pointer, the field at the higher offset.  PeepholeReplaceOptimization()
 * sorts two such loads by offset, and checks that the first does not overwrite the pointer
 * but not that the second does: it swaps them, so `o = o->nobj` comes first and the field is
 * read from the next object (the first object is skipped, and the last read is through
 * null).  -O1 and up, native code; v1.32.273, the pin to commit 85, and upstream main
 * 08b01c9 (2026-11-21); right at -O0.  Found 2026-11-21 in the far runtime's spike
 * (tests/spikes/farrt128.c, a list walk), then without far data.
 * NetHack: every walk of a list that reads a field after the link: `for (otmp = invent;
 * otmp; otmp = otmp->nobj)` with `otmp->oclass`, `otmp->quan`, ..., the monster list
 * (nmon), traps (ntrap), engravings, regions.  The host build cannot show it; the banked
 * C64 game does not run yet.
 * Expect when fixed: 10 + 20 + 30 (exit 0).
 * Workaround: none in the source (the pattern is everywhere): the compiler must be fixed.
 * Fixed by the pin's commit 86 (2026-11-22, from the far-spaces fork).
 * FLAGS: -n -e
 */
struct obj { struct obj * nobj; int v; char oclass; };

struct obj objs[3] = { { &objs[1], 1, 10 }, { &objs[2], 2, 20 }, { nullptr, 3, 30 } };

__noinline int walk(struct obj * o)
{
	int s = 0;
	for (; o; o = o->nobj)
		s += o->oclass;
	return s;
}

int main(void)
{
	struct obj * volatile hp = objs;
	return walk(hp) != 60;
}
