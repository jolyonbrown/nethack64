/* OSCAR64 REPRO r79 - CRASH WITH -v2: A FUNCTION WHOSE BODY IS AN __asm BLOCK ENDING IN A JMP.
 * The linker's direct-jump check (Linker::Forwards) prints "Direct <from> -> <to>" with -v2
 * for an object that ends in a JMP to another object, and reads both names unguarded. The
 * body of `void f(void) { __asm { jmp target } }` is an object without an identifier, so the
 * compiler crashes (a null mIdent) at that link stage. Without -v2 it compiles, and the
 * code is right. v1.32.273, the pin (87 commits), upstream main 4da3147 (2026-11-22).
 * NetHack: none; it hits the whole-game build's -v2 logs, whose far runtime has such a
 * function (tools/bank/farrt.py's farxzc(), the libc string routines' far translation).
 * Found 2026-11-22: the C128 whole-game link crashed after 628 s.
 * Expect when fixed: compiles (exit 0).
 * Workaround: leave out -v2, or use the far-spaces fork, whose commit 13 prints "*" for a
 * missing name.
 * FLAGS: -n -v2
 * COMPILE-ONLY
 */
__asm target
{
	lda #1
	rts
}

void jumper(void)
{
	__asm { jmp target }
}

int main(void)
{
	jumper();
	return 0;
}
