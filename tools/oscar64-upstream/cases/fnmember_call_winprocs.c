/* NetHack's winprocs.h shape: call through (*struct.member)() */
struct window_procs { void (*win_askname)(void); };
static int called;
static void ask(void) { called = 1; }
struct window_procs windowprocs = { ask };
#define askname (*windowprocs.win_askname)
int main(void) { askname(); return called ? 0 : 1; }
