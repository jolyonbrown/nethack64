/* OSCAR64 REPRO r88 - printf'S '*' WIDTH AND PRECISION, AND %s'S PRECISION, ARE NOT SUPPORTED.
 * C89 7.9.6.1: a field width or precision may be '*', taken from an int argument (a negative
 * width a '-' flag, a negative precision as if omitted). Oscar64's sformat() (include/
 * stdio.c) reads only digits there, so "%*s" prints "*s" and the arguments after it are off
 * by one; and %s writes the whole string whatever its precision, "%.10s" included. The
 * pin (v1.32.273 + 87) and the far fork to fe2b21e, 2026-11-23; upstream's stdio.c the
 * same then.
 * NetHack: botl.c's bot1(), Sprintf(nb, "%*s", i-j, " ") pads the status line ("Agent the
 * Stripling  *sSt:18/02" on the C128); weapon.c's #enhance list, "%-*s"; topten.c's "%.10s"
 * names and the length limits in files.c, rumors.c and sounds.c's messages ("%.243s").
 * Expect when fixed: "Emulation result 0".
 * Workaround: the far fork's commit 22 (include/stdio.c); on the pin, the width written
 * into the format with a digit string first.
 * FLAGS: -e -n
 */
#include <stdio.h>
#include <string.h>

int main(void)
{
	char buf[40];
	int bad = 0;

	sprintf(buf, "[%*s]", 4, "ab");
	if (strcmp(buf, "[  ab]")) bad |= 1;
	sprintf(buf, "[%-*s]%d", 4, "ab", 7);
	if (strcmp(buf, "[ab  ]7")) bad |= 2;
	sprintf(buf, "[%*s]", -3, "x");
	if (strcmp(buf, "[x  ]")) bad |= 4;
	sprintf(buf, "[%.*s]", 2, "abcd");
	if (strcmp(buf, "[ab]")) bad |= 8;
	sprintf(buf, "[%.3s|%5.2s]", "abcdef", "xyz");
	if (strcmp(buf, "[abc|   xy]")) bad |= 16;
	return bad;
}
