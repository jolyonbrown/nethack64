/* OSCAR64 REPRO r65 - CRASH: SIGSEGV in NativeCodeInstruction::BitFieldForwarding
 * (called from NativeCodeProcedure::Optimize), compiling a function that reads the bytes
 * of another function's code through a pointer taken from a const table of function
 * pointers, and compares a 16-bit value made of two of them.  The compiler knows which
 * function the pointer points at, so the loads are from a code object.  -O1, -O2 and -Os,
 * native; -O0, -O3 and bytecode compile.  v1.32.273 and the pin.
 * NetHack: none; the game never reads its own code.  Found 2026-11-15 writing the test of
 * the linker's bank call stubs, which looks at a stub's bytes.
 * Expect when fixed: compiles.
 * Workaround: read through a pointer the compiler cannot follow (the stub test passes the
 * address through a volatile).
 * FLAGS: -n -O2
 * COMPILE-ONLY
 */
__noinline int f(int x) { return 2 * x; }
int (* const table[1])(int) = { f };

static unsigned word(const unsigned char * p)
{
	return p[0] + 256 * p[1];
}

volatile char in_window;

int main(void)
{
	const unsigned char * s = (const unsigned char *)table[0];
	in_window = word(s + 4) >= 0x8000 && word(s + 4) < 0xc000;
	return 0;
}
