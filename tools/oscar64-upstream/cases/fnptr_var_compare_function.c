/* r16 without a struct member: plain pointer variable compared with a function name */
static void f(const char *s) { (void)s; }
int main(void) { void (*p)(const char *) = f; return p == f ? 0 : 1; }
