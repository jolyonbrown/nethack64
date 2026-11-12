/* OSCAR64 REPRO r31 - COMPILER ABORT at -Os: the same value stored to three or more
 * consecutive bytes through a pointer, starting at offset 0
 * NetHack: display_pickinv() in invent.c (seen with upstream main plus our fixes, where
 * invent.c gets that far; v1.32.273 stops at an earlier error in invent.c first, 3013
 * "Pointer expected" in obj_to_glyph(), T1.4).  Found 2026-11-12.
 * Cause: BlockSizeCopyReduction (the -Os size pass) turns "LDY #n; STA (p),y; LDY #n+1;
 * STA (p),y; ..." into a loop that starts with "LDY #n-1".  For n = 0 that is LDY #-1,
 * and the NativeCodeInstruction constructor asserts that an immediate is 0..255.  The
 * code is from 2024 (1f492e7) and is the same in v1.32.273 and on main.  A compiler built
 * without assertions would emit LDY #$FF, which is what the loop needs; the Linux
 * makefile builds with assertions on.  -Os with native code only; bytecode is right.
 * Expect when fixed: emulation result 0.  Actual (v1.32.273, the eight-commit patched pin,
 * upstream main 4da3147, -Os): "Assertion `linkerObject || (address >= 0 && address <
 * 256)' failed", SIGABRT.
 * Not fixed by any branch yet (TASKS T1.17).  Probable fix, not tried: "(mIns[si +
 * 0].mAddress - 1) & 0xff" where the LDY is built.
 * Workaround: none applied yet.
 * FLAGS: -e -Os
 */
char buf[8], vv = 7;

__noinline void fill(char * p, char v)
{
	p[0] = v;
	p[1] = v;
	p[2] = v;
	p[3] = v;
}

int main(void)
{
	fill(buf + 1, vv);
	fill(buf + 3, 9);
	return buf[0] != 0 || buf[1] != 7 || buf[2] != 7 || buf[3] != 9 || buf[6] != 9 || buf[7] != 0;
}
