/* OSCAR64 REPRO r58 - at -O2 and -Os, a conditional with a string literal and a
 * function call as operands, passed for a parameter that the callee never uses, is
 * rejected: "error 3013: Incompatible conditional types".  The same call compiles at
 * -O0 and -O1, when the callee uses the parameter, or with the result assigned to a
 * variable first.  `ignore(c1 ? "x" : pick())` fails as well as the nested form here.
 * The optimiser drops an argument nothing reads but keeps the call in it, and the
 * conditional left behind no longer type-checks (not investigated further).  On
 * v1.32.273, the pin and upstream main (16acc53).
 * NetHack: none known in the game itself (a callee has to ignore that parameter).
 * The measurement harness's empty stubs hit it: timeout.c 133 (`an(Hallucination ?
 * rndmonnam() : "green slime")`) and do.c 770 (`floating_above(stairs_down ? "stairs"
 * : ladder_down ? "ladder" : surface(u.ux, u.uy))`), 2026-11-14.
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: the harness's stubs read every parameter (tools/measure/mkstubs.py).
 * FLAGS: -e -O2
 */
volatile int vol;
const char *pick(void) { return vol ? "a" : "b"; }
void ignore(const char *s) { }
int c1, c2;
int main(void)
{
	ignore(c1 ? "x" : c2 ? "y" : pick());
	return 0;
}
