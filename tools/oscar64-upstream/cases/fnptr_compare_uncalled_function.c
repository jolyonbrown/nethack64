/* with the r16 fix: at -O2/-Os, comparing a function pointer with a function that is never called or assigned fails: 3013 'i16(*)()' != 'void(*)()' (the unused return value seems to be optimised away). NetHack dig.c:147 occupation == dig. */
int (*occupation)(void);
static int dig(void);
int is_digging(void) { if (occupation == dig) return 1; return 0; }
static int dig(void) { return 0; }
int main(void) { return is_digging(); }
