/* struct type declared separately from the variable */
static void f(const char *s) { (void)s; }
struct procs { void (*raw_print)(const char *); };
struct procs w;
int main(void) { w.raw_print = f; w.raw_print("x"); return 0; }
