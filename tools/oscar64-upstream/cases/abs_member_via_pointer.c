/* wrong code on main 4da3147 at -O2/-Os/-O3 (-n and -bc); v1.32.273 is correct: abs-style ?: on a struct member through a pointer. Expected result 0. */
struct point { int x, y; };
static int ax(struct point * pt) { return pt->x < 0 ? -pt->x : pt->x; }
int main(void)
{
	struct point pt = {-3, 4};
	return ax(&pt) == 3 ? 0 : 1;
}
