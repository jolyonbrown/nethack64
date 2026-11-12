/* wrong code at the DEFAULT level (-O1), -n and -bc, v1.32.273 and main: a function referenced only from a global initialiser is dropped. From the r16 agent. Expected result 0. */
#include <assert.h>
int seen;
void fa(const char * s) { (void)s; seen = 1; }
void fb(const char * s) { (void)s; seen = 2; }
typedef void (* fop)(const char * s);
fop gp = fa;
int main(void) { fop q = fb; assert(gp != q); return 0; }
