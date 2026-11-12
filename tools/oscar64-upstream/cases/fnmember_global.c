/* function-pointer member of a global struct: assign, then call */
static int f(int x) { return x + 1; }
struct procs { int (*fn)(int x); };
struct procs w;
int main(void) { w.fn = f; return w.fn(1) == 2 ? 0 : 1; }
