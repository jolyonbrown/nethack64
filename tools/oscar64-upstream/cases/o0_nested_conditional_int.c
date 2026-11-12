/* Separate, pre-existing Oscar64 bug found while testing fix/r2-nested-conditional.
 * NOT caused by that fix: identical .prg before/after; also present in v1.32.273.
 * Fails ONLY with -n -O0 (native code, no optimisation). Passes with -bc -O0,
 * -n, -n -O2/-Os/-O3, and when the parameters are char instead of int.
 * Expected: Emulation result 4 (f(0,1)).  Observed with -n -O0: -1 (also -1 for
 * f(0,0), which should give 5; f(1,0) correctly gives 3). 4da3147 and v1.32.273.
 *   oscar64 -ea -g -n -O0 preexisting_O0_nested_conditional.c
 */
static int f(int c, int d)
{
	return c ? 3 : (d ? 4 : 5);
}

int main(void)
{
	return f(0, 1);
}
