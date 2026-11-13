/* OSCAR64 REPRO r39 - WRONG CODE, no diagnostic: a value read through a pointer before a
 * loop is reused after the loop although the loop calls the function itself (recursion),
 * and that call changed it
 * NetHack: weight() in port/src/mkobj.c has the shape (obj->otyp read, then
 * "for (...) cwt += weight(contents);", then obj->otyp again) and is compiled with the stale
 * value; harmless there, because weight() writes nothing.  Found 2026-11-13 because the
 * listing of mkobj.c changed with the contents of the compiler's heap.
 * Cause: for a loop, LoadStoreForwarding keeps the loads known at loop entry that no
 * instruction of the body destroys (InterCodeBasicBlock::DestroyingMem).  For a call that
 * asks the callee's mStoresIndirect, which is set by the callee's Close().  In a recursive
 * call the callee is the function being compiled: the member is not set yet, and the
 * constructor of InterCodeProcedure does not initialise it.  A fresh heap is zero ("stores
 * nothing"), so the normal compile is the wrong one; with the heap filled with a non-zero
 * byte (MALLOC_PERTURB_=85) the same source compiles correctly.
 * v1.32.273 and the patched pin (ADR-0007): every level, -O0 included, native and
 * bytecode.  Upstream main 4da3147 is right since 4969258 (2026-10-18), which made
 * DestroyingMem ask "!mGlobalsChecked || mStoresIndirect"; 963b29c (2026-09-28) did not.
 * Fix: scratch/heap-init-pin 8286734 (the same test in DestroyingMem), a candidate for the
 * patched pin (TASKS T1.21).
 * Expect when fixed: emulation result 0.  Actual: result 1, total() returns 100, not 1100.
 * Workaround: none that is practical in source (copy the value again after the loop
 * through a volatile pointer); the fix is the pin commit.
 * FLAGS: -e -Os
 */
struct node
{
	struct node	*	next, * child, * up;
	int				v;
};

int total(struct node * p)
{
	struct node	*	q;
	int				s = 0;

	if (p->up)
		p->up->v = 9;
	if (p->v == 7)
		s = 100;
	for (q = p->child; q; q = q->next)
		s += total(q);
	if (p->v == 9)
		s += 1000;
	return s;
}

struct node	root, leaf;

int main(void)
{
	root.child = &leaf;
	root.v = 7;
	leaf.up = &root;
	leaf.v = 1;

	return total(&root) == 1100 ? 0 : 1;
}
