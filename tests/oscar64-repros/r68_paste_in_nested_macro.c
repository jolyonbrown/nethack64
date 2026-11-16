/* OSCAR64 REPRO r68 - REJECTS VALID C (or names the wrong thing): a macro that pastes its
 * parameter, `#define INNER(t) count_##t`, called from another macro's replacement with that
 * macro's parameter, `#define OUTER(t) INNER(t)`, pastes the parameter's name: OUTER(x)
 * becomes `count_t` (error 3005 "Unknown identifier 'count_t'"), where C substitutes the
 * argument first and gives `count_x` (C99 6.10.3.1).  Without `##`, nested parameters work.
 * v1.32.273 and the pin.  NetHack: none (its code never pastes); found 2026-11-16 in the
 * speed harness (tools/measure/speed/far_pre.h).
 * Expect when fixed: compiles, exit 0.
 * Workaround: paste in the outer macro and hand the inner one the pasted name,
 * `INNER2(count_##t)`.
 * FLAGS: -e
 */
#define INNER(t) count_##t
#define OUTER(t) INNER(t)

int count_x = 7;

int main(void)
{
	return OUTER(x) == 7 ? 0 : 1;
}
