/* OSCAR64 REPRO r91 - A RETURN ON A BRANCH SKIPS THE EPILOGUE: A BARE RTS.
 * NativeCodeBasicBlock::SplitSinglePath() takes a branch whose target starts with a store
 * of A to the zero page that only the return needs (IsExitARegZP: the value is in ACCU
 * already), and splits the target after the store (SplitBlock(1)), so that the branch goes
 * past it. When the target is the exit block, its temporary RTS moves to the new block, but
 * the procedure keeps the old block as its exit: the epilogue (the soft stack frame given
 * back, the saved zero page temporaries put back) is written there, and the branch reaches
 * a bare RTS. Here "if (candle(o)) return 1; ... return 0": candle()'s 0 returns through
 * the RTS, and snuff()'s 2-byte frame stays on the soft stack. -Os, a function with a
 * frame on the soft stack (recursion through a pointer makes one). The pin
 * (v1.32.273 + 87) and the far fork to e41bc86, 2026-11-24; upstream fixed it on
 * 2026-10-03 (3e2ffb6, "Fix return value part loss": SplitBlock() moves the exit block).
 * Whether a given build of the compiler shows it varies (a git build of v1.32.273 did not,
 * the installed one did): the conditions that lead to the split are not all deterministic.
 * NetHack: six functions of the whole game had such an RTS (known_hitum twice, teleok,
 * snuff_lit, hurtle_step, doattributes, classmon). known_hitum() returns through it when
 * hmon() kills the monster: each kill left 19 bytes on the soft stack and its callers'
 * temporaries unrestored, so domove() put back a zero page byte from the wrong place and
 * moveloop()'s "change" became 62, the newt's x: the hero "turned into" mons[-1] and the
 * game panicked in monsndx() (the C128, fc41, Dlvl 2).
 * Expect when fixed: "Emulation result 0".
 * Fixed by the pin's commit 95 (2026-11-26, from the far fork: upstream's two lines in
 * SplitBlock()).
 * FLAGS: -e -Os -n
 */
struct S { unsigned char flags; int otyp; };

static __noinline void get_loc(struct S *o, signed char *x, signed char *y) { *x = (signed char) o->otyp; *y = 1; }
char snuff(struct S *o);
char (*volatile again)(struct S *) = snuff;
static __noinline char candle(struct S *o) { if (o->otyp == 9) return again(o); return o->otyp == 7; }
static __noinline void say(signed char x, signed char y) { if (x == 99) *(volatile char *)0xd020 = y; }

__noinline char snuff(struct S *o)
{
	signed char x, y;

	if (o->flags & 8) {
		if (o->otyp == 1 || o->otyp == 2 || o->otyp == 3) {
			get_loc(o, &x, &y);
			say(x, y);
			return 1;
		}
		if (candle(o))
			return 1;
	}
	return 0;
}

int main(void)
{
	struct S s;
	char *a, *b;

	s.flags = 8;
	s.otyp = 5;
	a = *(char *volatile *)0x23;	/* the soft stack pointer (SP, zero page $23) */
	snuff(&s);
	b = *(char *volatile *)0x23;
	return a != b;			/* 0 when snuff() gave its frame back */
}
