/* rng.h - lrand48() and srand48(), bit for bit glibc's (rng.c, T2.7) */
#ifndef RNG_H
#define RNG_H

long lrand48(void);
void srand48(long seed);

#endif
