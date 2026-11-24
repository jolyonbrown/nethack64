/* OSCAR64 REPRO r90 - AN OBJECT-LIKE MACRO'S OWN NAME IN ITS EXPANSION IS REPLACED AGAIN.
 * C89 3.8.3.4: a macro's name found while rescanning its own replacement is not replaced.
 * With "#define dmg (*v->dmg)", Oscar64 replaces the dmg after -> too: "error 3006: Struct
 * member identifier expected". The pin (v1.32.273 + 87) and the far fork to 56fdc4a,
 * 2026-11-23. COMPILE-ONLY (it is rejected).
 * NetHack: none of its own code; the C64 port's split of mhitu.c's hitmu() and uhitm.c's
 * hmon_hitmon() (2026-11-23), which reached the caller's locals through such macros.
 * Expect when fixed: "Emulation result 0".
 * Workaround: the struct members named apart from the macros (nh_dmg).
 * FLAGS: -e -n
 */
struct v { int *dmg; };

int main(void)
{
	int d = 5;
	struct v vv, *v = &vv;

	vv.dmg = &d;
#define dmg (*v->dmg)
	dmg = 0;
#undef dmg
	return d;
}
