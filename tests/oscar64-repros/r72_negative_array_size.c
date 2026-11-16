/* OSCAR64 REPRO r72 - ACCEPTS INVALID C: an array of negative size compiles without a
 * diagnostic (C89 6.5.4.2: the size "shall have a value greater than zero"), as a typedef, an
 * extern or a struct member, so the usual C89 compile-time assertion checks nothing:
 *     typedef char t_is_64[sizeof (struct t) == 64 ? 1 : -1];
 * NetHack: not in 3.4.3's source; hit 2026-11-16 writing the size checks of ADR-0009's
 * padding (struct permonst to 64 bytes, struct objclass to 32).  v1.32.273 and the pin (78).
 * Expect when fixed: an error for each of the three declarations.
 * Workaround: Oscar64's static_assert(cond, "text") (error 3071; _Static_assert is unknown),
 * under #ifdef __OSCAR64C__ (permonst.h, objclass.h).
 * FLAGS: -n
 * REJECT
 */
struct t { char a[55]; };

typedef char t_is_64[sizeof (struct t) == 64 ? 1 : -1];
extern char t_is_64_too[sizeof (struct t) == 64 ? 1 : -1];
struct t_check { char f[sizeof (struct t) == 64 ? 1 : -1]; };

int main(void)
{
	return 0;
}
