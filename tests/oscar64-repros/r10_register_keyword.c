/* OSCAR64 REPRO r10 - the `register` storage class is not accepted
 * NetHack: thousands of `register int x;` locals and parameters.
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: compile with -dregister=  (defines it away).
 * FLAGS: -e
 */
int main(void)
{
	register int i, s = 0;
	for (i = 0; i < 4; i++)
		s += i;
	return s == 6 ? 0 : 1;
}
