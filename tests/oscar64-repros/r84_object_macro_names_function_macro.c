/* OSCAR64 REPRO r84 - AN OBJECT-LIKE MACRO THAT NAMES A FUNCTION-LIKE ONE CRASHES THE COMPILER.
 * `#define F1(x) g1(x)` and `#define A1 F1`, then `A1(3)`: C89 3.8.3.4 rescans A1's
 * replacement, F1, with the rest of the source, so F1 takes (3) as its arguments and this is
 * g1(3). Oscar64 segfaults in the preprocessor (MacroDict::Insert on a null dictionary,
 * Scanner::NextPreToken): reading the '(' ends A1's expansion, which puts back the argument
 * dictionary in effect outside it (none, at file scope) over the one just made for F1's
 * arguments. Any number of arguments (none is wrong too but does not crash), and __VA_ARGS__.
 * The pin (87 commits) and the far-spaces fork to 34ee85e, 2026-11-22; upstream main not built.
 * NetHack: dlb.h's `#define dlb_fopen fopen` once fopen is a macro (c64conf.h's NH_PORT_SYS
 * stdio redirection, fopen -> nh_fopen) whose target bankgen.py renames with a function-like
 * macro (nh_fopen(...) -> nh_fopen__b4(...)): the bootable C128 build's first link (fc14)
 * died 3 s in, parsing dungeon.c.
 * Expect when fixed: "Emulation result 0".
 * Workaround: no object-like macro whose replacement is the name of a function-like one; on
 * the far fork, commit 15 fixes it (the arguments' scope taken after the '(' is read).
 * FLAGS: -e
 */
int g1(int a) { return a + 1; }

#define F1(x)	g1(x)
#define A1	F1

int main(void)
{
	return A1(3) == 4 ? 0 : 1;
}
