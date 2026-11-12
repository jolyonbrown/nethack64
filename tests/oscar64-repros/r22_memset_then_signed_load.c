/* OSCAR64 REPRO r22 - WRONG CODE: a signed int read back from a memset(0xff) fill is
 * forwarded as 65535 instead of -1
 * NetHack: none found; every memset in port/src fills with 0, where the sign does not
 * matter (checked 2026-11-12).  Found 2026-11-12 by the review of the upstream r20 fix.
 * LoadStoreForwarding replaces the load of a[1] with the fill value, built from the fill
 * byte without sign extension, so a[1] < 0 is false.  Fails at every level, -O0 included,
 * native and bytecode, on v1.32.273 and upstream main 4da3147.
 * Expect when fixed: compiles, emulation result 0.  Actual at -Os: emulation result 1.
 * Workaround: none needed while NetHack only fills with 0.
 * FLAGS: -e -Os
 */
#include <string.h>
int main(void)
{
	int a[4];
	memset(a, 0xff, sizeof(a));
	int d = a[1] < 0 ? -a[1] : a[1];
	if (d != 1)
		return 1;
	return 0;
}
