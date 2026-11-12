/* assign a function to a function-pointer member of a struct declared with its variable */
static void f(const char *s) { (void)s; }
struct procs { void (*raw_print)(const char *); } w;
int main(void) { w.raw_print = f; w.raw_print("x"); return 0; }
