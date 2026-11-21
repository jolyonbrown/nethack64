/* port/sys/c64/c64scanf.c under Oscar64 (strings only): tests/scanf/run.sh runs it with -e.
 * The expected values are glibc's (scanf_test.c checks the two agree on the host). */
#include <stdio.h>
#include <string.h>
int ungetc(int c, FILE *fp) { return c; }
#include "../../port/sys/c64/c64scanf.c"

int main(void)
{
	int fails = 0, i = 0, j = 0;
	long l = 0, m = 0;
	short h = 0;
	char a[32], b[32], c2[2];

	if (nh_sscanf("1a2b3c\n", "%6lx\n", &l) != 1 || l != 0x1a2b3cL) fails |= 1;
	if (nh_sscanf("0001a2b3\n", "%8lx\n", &l) != 1 || l != 0x1a2b3L) fails |= 2;
	if (nh_sscanf("   42\n", "%5d\n", &i) != 1 || i != 42) fails |= 4;
	if (nh_sscanf("12345,67\n", "%ld,%d\n", &l, &i) != 2 || l != 12345L || i != 67) fails |= 8;
	if (nh_sscanf("3.4.3 -300", "%d.%d.%d %ld", &i, &j, &i, &m) != 4 || j != 4 || i != 3 || m != -300L) fails |= 16;
	if (nh_sscanf("Agnes,killed by a jackal\n", "%[^,],%[^\n]", a, b) != 2 ||
	    strcmp(a, "Agnes") || strcmp(b, "killed by a jackal")) fails |= 32;
	if (nh_sscanf("", "%d", &i) != EOF || nh_sscanf("-", "%d", &i) != 0 || nh_sscanf("x", "%d", &i) != 0) fails |= 64;
	if (nh_sscanf("VM C", "%c%c %s", c2, c2 + 1, a) != 3 || c2[0] != 'V' || c2[1] != 'M' || strcmp(a, "C")) fails |= 128;
	if (nh_sscanf("-5", "%hd", &h) != 1 || h != -5) fails |= 256;
	if (nh_sscanf("2147483647", "%ld", &l) != 1 || l != 2147483647L) fails |= 512;
	return fails;
}
