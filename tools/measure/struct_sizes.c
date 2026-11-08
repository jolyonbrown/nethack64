#include "hack.h"  /* port/include, normalised: struct tags carry a _s suffix */
#include <stdio.h>
int main(void)
{
	printf("rm %u\n", (unsigned)sizeof(struct rm_s));
	printf("dlevel_t %u\n", (unsigned)sizeof(dlevel_t));
	printf("obj %u\n", (unsigned)sizeof(struct obj_s));
	printf("monst %u\n", (unsigned)sizeof(struct monst_s));
	printf("permonst %u x %u\n", (unsigned)sizeof(struct permonst), (unsigned)NUMMONS);
	printf("objclass %u x %u\n", (unsigned)sizeof(struct objclass), (unsigned)NUM_OBJECTS);
	printf("you %u\n", (unsigned)sizeof(struct you_s));
	printf("trap %u\n", (unsigned)sizeof(struct trap_s));
	printf("flag %u\n", (unsigned)sizeof(struct flag_s));
	printf("int %u long %u ptr %u\n", (unsigned)sizeof(int), (unsigned)sizeof(long), (unsigned)sizeof(void *));
	return 0;
}
