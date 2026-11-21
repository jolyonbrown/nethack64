/* port/sys/c64/c64scanf.c against the C library's sscanf()/fscanf() (gcc, the host), for
 * the formats NetHack uses and the edges around them: the same return value, the same
 * values stored, and for fscanf() the same file position after each call.
 * tests/scanf/run.sh builds and runs it; exit 0 when everything agrees. */
#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include "../../port/sys/c64/c64scanf.c"

static int fails;

struct out { int i[14]; long l[14]; char s[6][64]; };

#define CHECK(what, a, b) do { if (memcmp(&(a), &(b), sizeof(a))) { \
	fails++; printf("FAIL %s\n", what); } } while (0)

static void one(const char *in, const char *fmt, const char *kind)
{
	struct out a, b;
	int ra, rb;
	memset(&a, 0x55, sizeof a); memset(&b, 0x55, sizeof b);
#define ARGS(o) o.i, o.i + 1, o.l, o.s[0], o.s[1], o.i + 2, o.l + 1
	/* every case reads at most: int, int, long, string, string, int, long, in the kinds */
	if (!strcmp(kind, "iil")) {
		ra = nh_sscanf(in, fmt, &a.i[0], &a.i[1], &a.l[0]);
		rb = sscanf(in, fmt, &b.i[0], &b.i[1], &b.l[0]);
	} else if (!strcmp(kind, "l")) {
		ra = nh_sscanf(in, fmt, &a.l[0]);
		rb = sscanf(in, fmt, &b.l[0]);
	} else if (!strcmp(kind, "i")) {
		ra = nh_sscanf(in, fmt, &a.i[0]);
		rb = sscanf(in, fmt, &b.i[0]);
	} else if (!strcmp(kind, "li")) {
		ra = nh_sscanf(in, fmt, &a.l[0], &a.i[0]);
		rb = sscanf(in, fmt, &b.l[0], &b.i[0]);
	} else if (!strcmp(kind, "ss")) {
		ra = nh_sscanf(in, fmt, a.s[0], a.s[1]);
		rb = sscanf(in, fmt, b.s[0], b.s[1]);
	} else if (!strcmp(kind, "ccss")) {
		ra = nh_sscanf(in, fmt, a.s[0], a.s[1], a.s[2], a.s[3]);
		rb = sscanf(in, fmt, b.s[0], b.s[1], b.s[2], b.s[3]);
	} else if (!strcmp(kind, "h")) {
		short x = 0x5555, y = 0x5555;
		ra = nh_sscanf(in, fmt, &x); rb = sscanf(in, fmt, &y);
		a.i[0] = x; b.i[0] = y;
	} else { printf("bad kind %s\n", kind); fails++; return; }
	char what[200];
	snprintf(what, sizeof what, "sscanf(\"%s\", \"%s\") = %d / libc %d", in, fmt, ra, rb);
	if (ra != rb) { fails++; printf("FAIL %s\n", what); return; }
	CHECK(what, a, b);
}

static const char *topten =
	"3.4.3 1234 0 1 2 15 20 1 20061212 20061201 1000 Val-Hum-Fem-Neu Agnes,killed by a jackal\n"
	"3.4.3 99 0 -1 3 0 12 1 20061213 20061212 1000 Wiz-Elf-Mal-Cha Bob,quit\n"
	"3.2.2 50 0 1 1 1 1 1 20061213 20061212 1000 VM Carl,died\n"
	"3.4.3 7 0 1";

static void records(void)
{
	static const char fmt[] = "%d.%d.%d %ld %d %d %d %d %d %d %ld %ld %d ";
	static const char fmt32[] = "%c%c %[^,],%[^\n]%*c";
	static const char fmt33[] = "%s %s %s %s %[^,],%[^\n]%*c";
	FILE *fa = fmemopen((void *) topten, strlen(topten), "r");
	FILE *fb = fmemopen((void *) topten, strlen(topten), "r");
	for (int k = 0; k < 5; k++) {
		struct out a, b;
		memset(&a, 0, sizeof a); memset(&b, 0, sizeof b);
		int ra = nh_fscanf(fa, fmt, a.i, a.i + 1, a.i + 2, a.l, a.i + 3, a.i + 4, a.i + 5,
				   a.i + 6, a.i + 7, a.i + 8, a.l + 1, a.l + 2, a.i + 9);
		int rb = fscanf(fb, fmt, b.i, b.i + 1, b.i + 2, b.l, b.i + 3, b.i + 4, b.i + 5,
				b.i + 6, b.i + 7, b.i + 8, b.l + 1, b.l + 2, b.i + 9);
		if (ra != rb || memcmp(&a, &b, sizeof a) || ftell(fa) != ftell(fb)) {
			fails++; printf("FAIL record %d head: %d/%d at %ld/%ld\n", k, ra, rb, ftell(fa), ftell(fb));
		}
		if (ra != 13) continue;
		if (a.i[0] == 3 && a.i[1] < 3) {
			ra = nh_fscanf(fa, fmt32, a.s[0], a.s[1], a.s[2], a.s[3]);
			rb = fscanf(fb, fmt32, b.s[0], b.s[1], b.s[2], b.s[3]);
		} else {
			ra = nh_fscanf(fa, fmt33, a.s[0], a.s[1], a.s[2], a.s[3], a.s[4], a.s[5]);
			rb = fscanf(fb, fmt33, b.s[0], b.s[1], b.s[2], b.s[3], b.s[4], b.s[5]);
		}
		if (ra != rb || memcmp(&a, &b, sizeof a) || ftell(fa) != ftell(fb)) {
			fails++; printf("FAIL record %d tail: %d/%d at %ld/%ld\n", k, ra, rb, ftell(fa), ftell(fb));
		}
	}
	fclose(fa); fclose(fb);
}

int main(void)
{
	static const char *c[][3] = {
		{ "1a2b3c\n", "%6lx\n", "l" }, { "  ff\n", "%6lx\n", "l" }, { "1234567\n", "%6lx\n", "l" },
		{ "zz", "%6lx\n", "l" }, { "", "%6lx\n", "l" }, { "   ", "%6lx\n", "l" },
		{ "   42\n", "%5d\n", "i" }, { "123456", "%5d\n", "i" }, { "-17", "%5d", "i" },
		{ "+8", "%d", "i" }, { "-", "%d", "i" }, { "x", "%d", "i" }, { "", "%d", "i" },
		{ "0001a2b3\n", "%8lx\n", "l" }, { "DEADBEEF", "%8lx", "l" }, { "1a2b3c4d5", "%8lx", "l" },
		{ "12345,67\n", "%ld,%d\n", "li" }, { "12345;67", "%ld,%d", "li" }, { "12345", "%ld,%d", "li" },
		{ "-300", "%ld", "l" }, { "2147483647", "%ld", "l" }, { "7 dollars", "%ld", "l" },
		{ "3.4.3", "%d.%d.%ld", "iil" }, { "3.4", "%d.%d.%ld", "iil" }, { "3-4", "%d.%d.%ld", "iil" },
		{ "a,b", "%[^,],%[^\n]", "ss" }, { ",b", "%[^,],%[^\n]", "ss" }, { "abc", "%[^,],%[^\n]", "ss" },
		{ "x y", "%s %s", "ss" }, { "  x\t\ny", "%s%s", "ss" }, { "abcdef", "%3s%s", "ss" },
		{ "ab]c", "%[]ab]%s", "ss" }, { "aab", "%[a]%s", "ss" }, { "%5", "%%%s", "ss" },
		{ "VM C,d", "%c%c %[^,],%[^\n]", "ccss" }, { "V", "%c%c %[^,],%[^\n]", "ccss" },
		{ "12", "%hx", "h" }, { "-5", "%hd", "h" }, { " 9", " %u", "i" }, { "5 ", "%*d %d", "i" },
	};
	for (unsigned k = 0; k < sizeof c / sizeof c[0]; k++)
		one(c[k][0], c[k][1], c[k][2]);
	records();
	printf("%s: %d failures\n", fails ? "FAIL" : "ok", fails);
	return fails != 0;
}
