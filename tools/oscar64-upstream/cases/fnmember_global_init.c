/* same, global with initializer: call only */
static int f(int x) { return x + 1; }
struct procs { int (*fn)(int x); };
struct procs w = { f };
int main(void) { return w.fn(1) == 2 ? 0 : 1; }
