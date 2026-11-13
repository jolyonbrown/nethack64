/* Unreduced (2026-11-13; found by the agent tracing heap-dependent output, rechecked by
 * the lead): wrong code at Oscar64's default level only, native code.  caller2() passes &a
 * to ping(), which calls pong(p, 0), which stores 7 through p; the store misses a (the
 * agent saw &a taken at SP+4 where the local is at SP+9).  Rechecked: emulation result 2
 * (caller2 wrong) with -e -n on v1.32.273, the eight-commit pin f001eba, the pin with the
 * heap-initialisation commits and upstream main 4da3147, with a zero-filled compiler heap;
 * 0 at -n -O0, -O2, -Os and -O3; gcc gives 0.  The agent also saw 0 in bytecode at -O2.
 * nethack64 builds with -Os, so it is not exposed as far as tested.
 * TASKS T1.24: reduce, find the cause, report. */
typedef void (*fn)(int *);

void set(int * p)
{
	*p = 5;
}

fn	f = set;

void indirect(int * p)
{
	f(p);
}

int	g;

__noinline int caller(char k)
{
	int	a = k;
	int	b = a + 1;

	indirect(&a);
	g = b;
	return a + a;
}

void ping(int * p);

void pong(int * p, char d)
{
	if (d)
		ping(p);
	else
		*p = 7;
}

void ping(int * p)
{
	pong(p, 0);
}

__noinline int caller2(char k)
{
	int	a = k;
	int	b = a + 1;

	ping(&a);
	g = b;
	return a + a;
}

int main(void)
{
	int	r = 0;
	if (caller(1) != 10) r |= 1;
	if (caller2(1) != 14) r |= 2;
	return r;
}
