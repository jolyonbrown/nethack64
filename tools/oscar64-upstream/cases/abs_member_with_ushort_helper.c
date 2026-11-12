/* wrong code on BOTH v1.32.273 and main 4da3147 at -O2/-Os/-O3 (-n and -bc): returns 1 = manhattan() wrong. v1.32.273 needs the ushort helper present; main fails even without it (abs_member_via_pointer.c). From the r10 agent (side_bug_abs_assert.c), asserts replaced by returns. Expected result 0. */
/* SIDE FINDING (not the register bug): pre-existing wrong code on Oscar64
 * 4da3147 and v1.32.273.  Two asserts on inlined calls, the first through a
 * conditional-expression abs() on a negative struct member, the second a
 * ushort multiply of constants.  Passes -O0 and default, fails -O2/-Os/-O3
 * in both -n and -bc with "Execution failed -1".  Needs the negative
 * coordinate (pt = {3, 4} passes), and both asserts (either alone passes);
 * replacing the asserts by if/printf also passes.  gcc: returns 0.
 *   oscar64 -ea -g -n -O2 side_bug_abs_assert.c
 */
#include <assert.h>
typedef unsigned short ushort;
struct point { int x, y; };
static int manhattan(struct point * pt)
{
	int dx = pt->x < 0 ? -pt->x : pt->x;
	int dy = pt->y < 0 ? -pt->y : pt->y;
	return dx + dy;
}
static ushort scale(ushort v, const ushort f) { return v * f; }
int main(void)
{
	struct point pt = {-3, 4};
	if (manhattan(&pt) != 7) return 1;
	if (scale(300, 100) != 30000) return 2;
	return 0;
}
