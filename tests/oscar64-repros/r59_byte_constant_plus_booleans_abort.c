/* OSCAR64 REPRO r59 - COMPILER ABORT with native code: a byte constant plus boolean
 * addends, `8 + (d > 3) + (d > 6) + (d > 8)`, stops the compiler in
 * NativeCodeBasicBlock::BinaryAddCarry: "Array.h:244: ... Assertion `n >= 0' failed"
 * (SIGABRT), at every native level; bytecode is right.
 * Cause (Codex, checked here): NativeCodeProcedure::CompileInterBlock fuses
 * `(a + b) + boolean` into BinaryAddCarry when a and b are in 0..255 (IsUByte), which
 * also accepts integer constants, but BinaryAddCarry took both for temporaries and
 * indexed mTempOffset[-1] for the constant 8.  On v1.32.273, the pin (48 commits) and
 * upstream main (16acc53).
 * NetHack: muse.c 903 in rnd_defensive_item(), `rn2(8 + (difficulty > 3) + (difficulty
 * > 6) + (difficulty > 8))`.  Found 2026-11-14 once the measurement harness's stubs read
 * their parameters (TASKS T1.42): with an empty `rn2` stub the optimiser dropped the
 * argument, so the file compiled; a real build would have aborted.
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: none in port/; fixed by the ADR-0007 compiler (commits 58-59, Codex's fix,
 * an immediate LDA/ADC for a constant addend, and test, 2026-11-14).
 * FLAGS: -e
 */
volatile int difficulty;

int main(void)
{
	int i;
	for (i = 0; i != 12; ++i) {
		int d, expected = 8;
		difficulty = i;
		d = difficulty;
		if (i > 3) ++expected;
		if (i > 6) ++expected;
		if (i > 8) ++expected;
		if (8 + (d > 3) + (d > 6) + (d > 8) != expected)
			return 1;
	}
	return 0;
}
