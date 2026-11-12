/* control: function-pointer member of a LOCAL struct (works on main) */
static void f(const char *s) { (void)s; }
struct procs { void (*raw_print)(const char *); };
int main(void) { struct procs w; w.raw_print = f; w.raw_print("x"); return 0; }
