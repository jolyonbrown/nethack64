/* OSCAR64 REPRO r25 - WRONG CODE: a function called directly with a constant argument and
 * also through a function pointer gets the constant built into its body
 * NetHack: window-port functions the port calls directly with a constant (blocking FALSE,
 * WIN_MESSAGE) and the game calls through windowprocs with other values; command
 * functions called directly and through cmdlist.  Found 2026-11-12 by the review of the
 * patched-pin backport.
 * GlobalAnalyzer::RegisterProc marks the parameters of an address-taken function as "not
 * constant" on to->mParams instead of the function type's parameters, so constant
 * parameter propagation folds blocking = 0 into tty_display_nhwindow and the call through
 * windowprocs with 1 is ignored.  Wrong at -O2, -Os and -O3, native and bytecode, on
 * v1.32.273.  Fixed upstream by bf42402 (PR #440, 2026-10-24, not in a release), which
 * the proposed patched pin (ADR-0007) carries.
 * Expect when fixed: compiles, emulation result 0.  Actual at -Os: emulation result 1.
 * Workaround: none applied yet.
 * FLAGS: -e -Os
 */
typedef int winid;
typedef signed char boolean;
winid WIN_MESSAGE = 1;
int blocked;

__noinline void tty_display_nhwindow(winid w, boolean blocking)
{
	if (blocking)
		blocked += w;
}

struct window_procs { void (*win_display_nhwindow)(winid, boolean); } windowprocs;
const struct window_procs tty_procs = { tty_display_nhwindow };
#define display_nhwindow (*windowprocs.win_display_nhwindow)

__noinline void tty_more(void) { tty_display_nhwindow(WIN_MESSAGE, 0); }

int main(void)
{
	windowprocs = tty_procs;
	tty_more();
	display_nhwindow(WIN_MESSAGE, 1);
	if (blocked != 1)
		return 1;
	return 0;
}
