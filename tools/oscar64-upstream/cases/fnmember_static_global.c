/* same, static global */
static int f(int x) { return x + 1; }
struct procs { int (*fn)(int x); };
static struct procs w;
int main(void) { w.fn = f; return w.fn(1) == 2 ? 0 : 1; }
