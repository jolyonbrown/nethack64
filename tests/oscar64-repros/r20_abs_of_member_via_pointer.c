/* OSCAR64 REPRO r20 - WRONG CODE: abs-style ?: on a struct member read through a pointer
 * NetHack: distance helpers of this shape (dist2, distmin, couldsee callers); exposure not
 * counted yet.  Found 2026-11-12 by the agent fixing r10.
 * `pt->x < 0 ? -pt->x : pt->x` in a small function inlined into the caller gives the wrong
 * value at -O2, -Os and -O3, native and bytecode, so the program returns 1.  -O0 and -O1 are
 * correct.  The scale() helper is not needed: on v1.32.273 the abs helper alone fails when
 * the comparison feeds an `if`, as here; upstream main (48f90e2 and later) also fails it when
 * the comparison is a value, `return d == 3 ? 0 : 1`
 * (tools/oscar64-upstream/cases/abs_member_via_pointer.c).  Cause: constant folding of a load
 * from initialised data reads the stored -3 as 65533 (LoadConstantFold); r21 and r22 are the
 * same mistake at two other sites.
 * Expect when fixed: compiles, emulation result 0.  Actual at -Os: emulation result 1.
 * Workaround: none applied yet.
 * FLAGS: -e -Os
 */
typedef unsigned short ushort;
struct point { int x, y; };
static int manhattan(struct point *pt)
{
	int dx = pt->x < 0 ? -pt->x : pt->x;
	int dy = pt->y < 0 ? -pt->y : pt->y;
	return dx + dy;
}
static ushort scale(ushort v, const ushort f) { return v * f; }
int main(void)
{
	struct point pt = {-3, 4};
	if (manhattan(&pt) != 7)
		return 1;
	if (scale(300, 100) != 30000)
		return 2;
	return 0;
}
