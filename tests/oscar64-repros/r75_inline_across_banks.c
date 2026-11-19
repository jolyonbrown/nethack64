/* OSCAR64 REPRO r75 - CODE TAKEN INTO ANOTHER BANK, ITS LITERALS LEFT BEHIND: a function's
 * string literals stay in the section in force where they are written, but its code, or a
 * constant it returns, can be taken into a caller in another section.  With cartridge banks
 * the caller then reads the literal from the wrong bank.  Here each function in bank 3 ends
 * up in its caller in bank 5, so bank 5 refers to bank 3's literals (warning 2024 from the
 * bank call linker check, pin feature):
 *   complain  - cheap inlining (intermediate code)
 *   name      - a constant function call, evaluated into the callee's section
 *   pick      - automatic inlining (cost below zero), native simple inlining and the
 *               extraction of a constant return value; any one of them takes it
 * v1.32.273 has no bank call check; the pin before commit 83 shows a5, b5 and f5.
 * NetHack: the whole game, near and far: punish (bank 60) prints placebc's "Where are your
 * ball and chain?" from bank 5's address, domonability (bank 28) doremove's "You are not
 * chained to anything!" (2026-11-18; the logs' wrapper had dropped warnings until then).
 * Expect when fixed: no warning 2024 (each call goes through the bank call stub instead).
 * Workaround: none needed: fixed in the pin, commit 83 (2026-11-18).
 * FLAGS: -n -Os
 * COMPILE-ONLY
 * UNDIAGNOSED: 2024
 */
__asm test_bankcall
{
		rts
}

#pragma runtime(bankcall, test_bankcall)

#pragma section( bcode3, 0 )
#pragma region( bank3, 0x8000, 0xc000, , 3, { bcode3 } )
#pragma section( bcode5, 0 )
#pragma region( bank5, 0x8000, 0xc000, , 5, { bcode5 } )

const char * volatile msg;
volatile char flag;

#pragma code( bcode3 )

void complain(void)
{
	msg = "Where are your ball and chain?";
}

const char * name(void)
{
	return "zorkmid";
}

const char * pick(char x)
{
	return "f1";
}

#pragma code( bcode5 )

__noinline void a5(void) { if (flag) complain(); }
__noinline void b5(void) { msg = name(); }
__noinline void f5(void) { msg = pick(flag); }

#pragma code( code )

int main(void)
{
	a5();
	b5();
	f5();
	return 0;
}
