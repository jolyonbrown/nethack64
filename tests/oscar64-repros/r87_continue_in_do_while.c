/* OSCAR64 REPRO r87 - `continue` IN A do-while JUMPS TO THE BODY, NOT THE CONDITION.
 * C89 3.6.6.2: continue goes to the end of the loop body, so a do-while's condition is
 * evaluated. InterCodeGenerator's EX_DO gave the body's first block as the continue
 * target, so a continue skips the condition and its side effects: here the loop counter
 * is never incremented while the body continues, and the loop runs until cnt reaches 1000.
 * Every level, -O0 too. The pin (v1.32.273 + 87) and the far fork to 78e64e4, 2026-11-23;
 * fixed upstream in 546b627 "Fix continue in do-while loop" (2026-09-26), after the pin.
 * NetHack: sp_lev.c's create_room(), `do { ... r1 = 0; continue; ... } while (++trycnt
 * <= 100 && !r1);`: with only small rectangles left the first level's makerooms() never
 * ended (the C128 game, fc27b, after the character was chosen); any do-while with a
 * continue.
 * Expect when fixed: "Emulation result 0". Fixed by the pin's commit 90 (2026-11-26), a
 * cherry-pick of 546b627, from the far fork.
 * FLAGS: -e -n
 */
int cnt;

int main(void)
{
	int t = 0;
	do {
		cnt++;
		if (cnt < 1000)
			continue;
	} while (++t <= 10);
	return cnt == 11 ? 0 : 1;
}
