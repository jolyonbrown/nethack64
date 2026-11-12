/* OSCAR64 REPRO r32 - WRONG CODE: a pointer read from a constant table at a constant index
 * k > 0 points 2k bytes past its target
 * NetHack: sounds.c dosounds(), line 83: pline(throne_msg[2], uhis()) prints
 * one shouts "Off with his head!" (the string from its 5th byte); pager.c line 680,
 * objexplain[VENOM_CLASS], when drawing.c is compiled before pager.c.  Found 2026-11-12
 * by the review of the r27 fix (shknam-crash).
 * Cause: Expression::ConstantDereference folds tab[k] of a const table to the
 * initializer's element declaration, whose mOffset is the element's offset in the table,
 * and the code generator adds a constant pointer's mOffset to the pointer.  The same
 * happens to a pointer member of a const struct that is not its first member (here
 * ops.name, 2 bytes too far) and to function pointers.  Every level including -O0, native
 * and bytecode, on v1.32.273 and on the eight-commit patched pin (ADR-0007).  Right: a
 * table that is not const (const char *t[]), index 0, a variable index, and tab[k][j]
 * (only the pointer used as a value is folded).
 * Fixed upstream by 1ae3216 ("Fix array in array index const folding", 2026-10-24, not in
 * a release): it clones the element and sets its mOffset to 0.  Backported as
 * nethack64/pin-1ae3216: candidate for the patched pin, Jolyon's decision pending
 * (ADR-0007).
 * Expect when fixed: compiles, emulation result 0.  Actual at -Os: emulation result 3 (1
 * for the table, 2 for the struct member).
 * Workaround: none applied yet (the candidate pin commit is the fix).
 * FLAGS: -e -Os
 */
static const char * const throne_msg[4] = {
	"the tones of courtly conversation.",
	"a sceptre pounded in judgment.",
	"Someone shouts \"Off with %s head!\"",
	"Queen Beruthiel's cats!",
};

struct opsdesc { int id; const char * name; };
static const struct opsdesc ops = { 1, "throne" };

int main(void)
{
	const char * s = throne_msg[2];
	const char * n = ops.name;
	return (s[0] != 'S') + 2 * (n[0] != 't');
}
