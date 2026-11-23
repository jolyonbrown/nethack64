/* OSCAR64 REPRO r89 - A GLOBAL REACHED ONLY THROUGH A POINTER IN A STATIC INITIALIZER IS
 * FOLDED TO ITS INITIAL VALUE.
 * The global optimizer replaces a global by its initializer when nothing takes its address
 * or assigns it (ReplaceGlobalConst). An initializer's pointer member, { 2, &ub }, was
 * analysed without the address flag (AnalyzeInit), so ub, assigned only through
 * *wp->p = o, was read as its initial 0 everywhere: "if (ub)" removed. -Os and -O2 (not
 * -O0). The pin (v1.32.273 + 87) and the far fork to 8a5783e, 2026-11-23; upstream's
 * GlobalOptimizer.cpp the same then.
 * NetHack: worn.c's worn[] = { { W_ARMS, &uarms }, ... }, through which setworn() puts on
 * armour; u_init.c's direct "uarms = 0" is under #if 0. do_wear.c's find_ac() then counted
 * body armour alone (uarm is assigned in polyself.c): a Valkyrie's +3 small shield, worn,
 * left her AC 10, not 6 (the C128, fc31). Every slot but uarm, uwep and the rings' alike.
 * Expect when fixed: "Emulation result 0".
 * Workaround: the far fork's commit 23 (a pointer member's object marked address-taken).
 * FLAGS: -e -n -Os
 */
struct obj { int x; };
struct obj *ua = 0, *ub = 0;
const struct w { long m; struct obj **p; } worn[] = { { 1, &ua }, { 2, &ub }, { 0, 0 } };
struct obj shield = { 4 };

__noinline void setworn(struct obj *o, long m)
{
	const struct w *wp;
	for (wp = worn; wp->m; wp++)
		if (wp->m & m)
			*wp->p = o;
}

__noinline int ac(void)
{
	int a = 10;
	if (ua) a -= ua->x;
	if (ub) a -= ub->x;
	return a;
}

int main(void)
{
	setworn(&shield, 2);
	return ac() == 6 ? 0 : 1;
}
