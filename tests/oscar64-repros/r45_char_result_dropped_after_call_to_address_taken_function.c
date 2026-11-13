/* OSCAR64 REPRO r45 - WRONG CODE: a char result made from two values read before a direct
 * call to an address-taken function is never computed: f() returns whatever the callee
 * left in the accumulator
 * NetHack: not searched yet (TASKS T1.26).  It has many functions whose address is taken
 * (command and callback tables) and many char and boolean results.
 * Trigger, native code, each part needed: the callee's address is taken, so its parameter
 * goes on the stack; the call is direct; the callee stores through that pointer; the
 * result is 8 bits wide and combines two values read before the call.  Right: an int
 * result; the sum stored to a global; the call made through the pointer; a callee with no
 * parameter, or one that stores nothing; one value returned.  The intermediate code is
 * right (two loads, CALLN, BINOP, RETV); the 6502 code is the call alone, and ga is gone.
 * Found 2026-11-13 by the verifier of the r44 fix (its probe pl_lostsum.c).  Bisected over
 * the pin's eight commits: commit 3, upstream bf42402 (PR #440, the r25 fix, which stops
 * taking an address-taken function's parameters as constants), exposes it at -O2/-Os/-O3.
 * Expect when fixed: emulation result 0.  Actual, native code (bytecode gives 0 on all):
 * v1.32.273 1 at the default level only; the pin (f001eba), the pin with the 2026-11-13
 * additions (b4dc4eb) and upstream main 4da3147 1 at default, -O2, -Os and -O3, 0 at -O0;
 * with the r44 fix (scratch/r44-fix-pin cf8dd6f) 1 at all five levels.
 * Workaround: return int and narrow in the caller; or store the result to a global; or call
 * through the function pointer: 0 in all ten on v1.32.273, f001eba and b4dc4eb.
 * FLAGS: -e -Os
 */
char ga[4] = {1, 2, 3, 4};
char t[2];
void (* fp)(char *);

__noinline void bump(char * p) { p[0] += 100; }

__noinline char f(char k) { char x = ga[1]; char y = ga[k]; bump(t); return x + y; }

int main(void)
{
	fp = bump;
	fp(t);
	return f(0) != 3;
}
