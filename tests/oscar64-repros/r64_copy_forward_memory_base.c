/* OSCAR64 REPRO r64 - CRASH: assertion `n >= 0' in GrowingArray<InterVariable*> from
 * InterCodeBasicBlock::LoadStoreForwarding (InterCode.cpp:15126 in the pin), compiling a
 * function that copies a struct from a pointer into a local, passes the local's address
 * to a function that only reads it, reads a field of the local and calls a function.
 * Cause: PropagateVariableCopy forwards the load of dlev.dnum to the copy's source,
 * *(slev + 2), taking the source's memory, temporary, variable index, offset, linker
 * object and stride but not its mMemoryBase, so the load keeps IM_LOCAL (dlev) with
 * variable index -1; LoadStoreForwarding then reads mLocalVars[-1] at the call.  Before
 * it gets there, alias analysis sees a load from "a local" that reads through a pointer.
 * The same mistake as r50's in another pass.  Found with gdb watchpoints on the operand.
 * NetHack: dungeon.c lev_by_name()'s `dlev = slev->dlevel; idx = ledger_no(&dlev);
 * if (dlev.dnum == u.uz.dnum ...`, in the whole-game compile once ledger_no() is called
 * directly (bank calls through linker stubs, 2026-11-15); the per-file measurement never
 * shows it, because its stub ledger_no() may store through the pointer, which ends the
 * forwarding.  v1.32.273, the pin; the same code in upstream main 2d30da6.  -O0 to -O3,
 * native and bytecode.
 * Expect when fixed: emulation result 0.
 * Workaround: none needed in port/ (only the stub build reaches it); fixed by the ADR-0007
 * compiler (commits 70-71, 2026-11-15): the load takes over the source's mMemoryBase and
 * mRestricted too.
 * FLAGS: -e -Os
 */
typedef struct { signed char dnum, dlevel; } d_level;
typedef struct s_level { struct s_level *next; d_level dlevel; char proto[15]; } s_level;

s_level levs[3];
volatile int vn;

__noinline int ledger(d_level *lev) { return lev->dnum * 10 + lev->dlevel; }
__noinline s_level *find(int n) { return &levs[n]; }
__noinline int depthof(d_level *lev) { return lev->dlevel; }

__noinline int lev_by(int n)
{
	s_level *slev = find(n);
	d_level dlev;

	dlev = slev->dlevel;
	int idx = ledger(&dlev);
	int a = dlev.dnum;
	int b = depthof(&slev->dlevel);
	return a * 100 + b + idx;
}

int main(void)
{
	levs[1].dlevel.dnum = 2;
	levs[1].dlevel.dlevel = 5;
	vn = 1;
	return lev_by(vn) == 200 + 5 + 25 ? 0 : 1;
}
