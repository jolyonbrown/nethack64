/*
 * rng.c - lrand48() and srand48(), bit for bit glibc's (T2.7).
 *
 * NetHack's Rand() is lrand48() on the host (unixconf.h, SYSV) and on the C64
 * (c64conf.h), so a C64 game replays seed for seed against the host build.
 * The generator is the 48-bit LCG x' = (0x5DEECE66D x + 0xB) mod 2^48;
 * lrand48() returns x' >> 17, and srand48(s) sets x = (s mod 2^32) << 16 | 0x330E.
 *
 * In C the 48-bit multiply costs about 4,900 cycles a call on the 6502, and a
 * turn makes some 36 calls (docs/RAM-PLAN.md).  Here it is 14 shifted adds and
 * subtracts, the multiplier in canonical signed digits:
 *   0x5DEECE66D = 2^0 - 2^2 - 2^4 + 2^7 - 2^9 + 2^11 - 2^13 + 2^16 - 2^18
 *                 - 2^20 - 2^24 - 2^29 - 2^33 + 2^35
 * grouped by the bit shift of x each needs (a byte's offset costs nothing), so
 * the copy s of x is shifted left one bit at a time, seven times.  Every term
 * stops at bit 47.  The state and the work bytes are ordinary RAM: the
 * generator is not hot enough to earn zero page.
 */
#include "rng.h"

/* x, low byte first; glibc starts from 0 if srand48() is never called */
static unsigned char nh_rng_x[6], nh_rng_s[6], nh_rng_a[6];

void srand48(long seed)
{
	unsigned long s = (unsigned long) seed;

	nh_rng_x[0] = 0x0e;
	nh_rng_x[1] = 0x33;
	nh_rng_x[2] = (unsigned char) s;
	nh_rng_x[3] = (unsigned char) (s >> 8);
	nh_rng_x[4] = (unsigned char) (s >> 16);
	nh_rng_x[5] = (unsigned char) (s >> 24);
}

/* The result is left in accu, as Oscar64's own clock() leaves its own.  The block must
   not start with a comment (compat #69, r66): first a = 0xB, the increment, and s = x. */
__noinline long lrand48(void)
{
	__asm
	{
		lda #11
		sta nh_rng_a + 0
		lda #0
		sta nh_rng_a + 1
		sta nh_rng_a + 2
		sta nh_rng_a + 3
		sta nh_rng_a + 4
		sta nh_rng_a + 5
		lda nh_rng_x + 0
		sta nh_rng_s + 0
		lda nh_rng_x + 1
		sta nh_rng_s + 1
		lda nh_rng_x + 2
		sta nh_rng_s + 2
		lda nh_rng_x + 3
		sta nh_rng_s + 3
		lda nh_rng_x + 4
		sta nh_rng_s + 4
		lda nh_rng_x + 5
		sta nh_rng_s + 5
		/* a += x << 0 */
		clc
		lda nh_rng_a + 0
		adc nh_rng_s + 0
		sta nh_rng_a + 0
		lda nh_rng_a + 1
		adc nh_rng_s + 1
		sta nh_rng_a + 1
		lda nh_rng_a + 2
		adc nh_rng_s + 2
		sta nh_rng_a + 2
		lda nh_rng_a + 3
		adc nh_rng_s + 3
		sta nh_rng_a + 3
		lda nh_rng_a + 4
		adc nh_rng_s + 4
		sta nh_rng_a + 4
		lda nh_rng_a + 5
		adc nh_rng_s + 5
		sta nh_rng_a + 5
		/* a += x << 16 */
		clc
		lda nh_rng_a + 2
		adc nh_rng_s + 0
		sta nh_rng_a + 2
		lda nh_rng_a + 3
		adc nh_rng_s + 1
		sta nh_rng_a + 3
		lda nh_rng_a + 4
		adc nh_rng_s + 2
		sta nh_rng_a + 4
		lda nh_rng_a + 5
		adc nh_rng_s + 3
		sta nh_rng_a + 5
		/* a -= x << 24 */
		sec
		lda nh_rng_a + 3
		sbc nh_rng_s + 0
		sta nh_rng_a + 3
		lda nh_rng_a + 4
		sbc nh_rng_s + 1
		sta nh_rng_a + 4
		lda nh_rng_a + 5
		sbc nh_rng_s + 2
		sta nh_rng_a + 5
		/* s <<= 1 */
		asl nh_rng_s + 0
		rol nh_rng_s + 1
		rol nh_rng_s + 2
		rol nh_rng_s + 3
		rol nh_rng_s + 4
		rol nh_rng_s + 5
		/* a -= x << 9 */
		sec
		lda nh_rng_a + 1
		sbc nh_rng_s + 0
		sta nh_rng_a + 1
		lda nh_rng_a + 2
		sbc nh_rng_s + 1
		sta nh_rng_a + 2
		lda nh_rng_a + 3
		sbc nh_rng_s + 2
		sta nh_rng_a + 3
		lda nh_rng_a + 4
		sbc nh_rng_s + 3
		sta nh_rng_a + 4
		lda nh_rng_a + 5
		sbc nh_rng_s + 4
		sta nh_rng_a + 5
		/* a -= x << 33 */
		sec
		lda nh_rng_a + 4
		sbc nh_rng_s + 0
		sta nh_rng_a + 4
		lda nh_rng_a + 5
		sbc nh_rng_s + 1
		sta nh_rng_a + 5
		/* s <<= 1 */
		asl nh_rng_s + 0
		rol nh_rng_s + 1
		rol nh_rng_s + 2
		rol nh_rng_s + 3
		rol nh_rng_s + 4
		rol nh_rng_s + 5
		/* a -= x << 2 */
		sec
		lda nh_rng_a + 0
		sbc nh_rng_s + 0
		sta nh_rng_a + 0
		lda nh_rng_a + 1
		sbc nh_rng_s + 1
		sta nh_rng_a + 1
		lda nh_rng_a + 2
		sbc nh_rng_s + 2
		sta nh_rng_a + 2
		lda nh_rng_a + 3
		sbc nh_rng_s + 3
		sta nh_rng_a + 3
		lda nh_rng_a + 4
		sbc nh_rng_s + 4
		sta nh_rng_a + 4
		lda nh_rng_a + 5
		sbc nh_rng_s + 5
		sta nh_rng_a + 5
		/* a -= x << 18 */
		sec
		lda nh_rng_a + 2
		sbc nh_rng_s + 0
		sta nh_rng_a + 2
		lda nh_rng_a + 3
		sbc nh_rng_s + 1
		sta nh_rng_a + 3
		lda nh_rng_a + 4
		sbc nh_rng_s + 2
		sta nh_rng_a + 4
		lda nh_rng_a + 5
		sbc nh_rng_s + 3
		sta nh_rng_a + 5
		/* s <<= 1 */
		asl nh_rng_s + 0
		rol nh_rng_s + 1
		rol nh_rng_s + 2
		rol nh_rng_s + 3
		rol nh_rng_s + 4
		rol nh_rng_s + 5
		/* a += x << 11 */
		clc
		lda nh_rng_a + 1
		adc nh_rng_s + 0
		sta nh_rng_a + 1
		lda nh_rng_a + 2
		adc nh_rng_s + 1
		sta nh_rng_a + 2
		lda nh_rng_a + 3
		adc nh_rng_s + 2
		sta nh_rng_a + 3
		lda nh_rng_a + 4
		adc nh_rng_s + 3
		sta nh_rng_a + 4
		lda nh_rng_a + 5
		adc nh_rng_s + 4
		sta nh_rng_a + 5
		/* a += x << 35 */
		clc
		lda nh_rng_a + 4
		adc nh_rng_s + 0
		sta nh_rng_a + 4
		lda nh_rng_a + 5
		adc nh_rng_s + 1
		sta nh_rng_a + 5
		/* s <<= 1 */
		asl nh_rng_s + 0
		rol nh_rng_s + 1
		rol nh_rng_s + 2
		rol nh_rng_s + 3
		rol nh_rng_s + 4
		rol nh_rng_s + 5
		/* a -= x << 4 */
		sec
		lda nh_rng_a + 0
		sbc nh_rng_s + 0
		sta nh_rng_a + 0
		lda nh_rng_a + 1
		sbc nh_rng_s + 1
		sta nh_rng_a + 1
		lda nh_rng_a + 2
		sbc nh_rng_s + 2
		sta nh_rng_a + 2
		lda nh_rng_a + 3
		sbc nh_rng_s + 3
		sta nh_rng_a + 3
		lda nh_rng_a + 4
		sbc nh_rng_s + 4
		sta nh_rng_a + 4
		lda nh_rng_a + 5
		sbc nh_rng_s + 5
		sta nh_rng_a + 5
		/* a -= x << 20 */
		sec
		lda nh_rng_a + 2
		sbc nh_rng_s + 0
		sta nh_rng_a + 2
		lda nh_rng_a + 3
		sbc nh_rng_s + 1
		sta nh_rng_a + 3
		lda nh_rng_a + 4
		sbc nh_rng_s + 2
		sta nh_rng_a + 4
		lda nh_rng_a + 5
		sbc nh_rng_s + 3
		sta nh_rng_a + 5
		/* s <<= 1 */
		asl nh_rng_s + 0
		rol nh_rng_s + 1
		rol nh_rng_s + 2
		rol nh_rng_s + 3
		rol nh_rng_s + 4
		rol nh_rng_s + 5
		/* a -= x << 13 */
		sec
		lda nh_rng_a + 1
		sbc nh_rng_s + 0
		sta nh_rng_a + 1
		lda nh_rng_a + 2
		sbc nh_rng_s + 1
		sta nh_rng_a + 2
		lda nh_rng_a + 3
		sbc nh_rng_s + 2
		sta nh_rng_a + 3
		lda nh_rng_a + 4
		sbc nh_rng_s + 3
		sta nh_rng_a + 4
		lda nh_rng_a + 5
		sbc nh_rng_s + 4
		sta nh_rng_a + 5
		/* a -= x << 29 */
		sec
		lda nh_rng_a + 3
		sbc nh_rng_s + 0
		sta nh_rng_a + 3
		lda nh_rng_a + 4
		sbc nh_rng_s + 1
		sta nh_rng_a + 4
		lda nh_rng_a + 5
		sbc nh_rng_s + 2
		sta nh_rng_a + 5
		/* s <<= 1 */
		asl nh_rng_s + 0
		rol nh_rng_s + 1
		rol nh_rng_s + 2
		rol nh_rng_s + 3
		rol nh_rng_s + 4
		rol nh_rng_s + 5
		/* s <<= 1 */
		asl nh_rng_s + 0
		rol nh_rng_s + 1
		rol nh_rng_s + 2
		rol nh_rng_s + 3
		rol nh_rng_s + 4
		rol nh_rng_s + 5
		/* a += x << 7 */
		clc
		lda nh_rng_a + 0
		adc nh_rng_s + 0
		sta nh_rng_a + 0
		lda nh_rng_a + 1
		adc nh_rng_s + 1
		sta nh_rng_a + 1
		lda nh_rng_a + 2
		adc nh_rng_s + 2
		sta nh_rng_a + 2
		lda nh_rng_a + 3
		adc nh_rng_s + 3
		sta nh_rng_a + 3
		lda nh_rng_a + 4
		adc nh_rng_s + 4
		sta nh_rng_a + 4
		lda nh_rng_a + 5
		adc nh_rng_s + 5
		sta nh_rng_a + 5
		/* x = a; the result is a >> 17, bits 17-47 */
		lda nh_rng_a + 0
		sta nh_rng_x + 0
		lda nh_rng_a + 1
		sta nh_rng_x + 1
		lda nh_rng_a + 2
		sta nh_rng_x + 2
		lda nh_rng_a + 3
		sta nh_rng_x + 3
		lda nh_rng_a + 4
		sta nh_rng_x + 4
		lda nh_rng_a + 5
		sta nh_rng_x + 5
		lda nh_rng_a + 5
		lsr
		sta accu + 3
		lda nh_rng_a + 4
		ror
		sta accu + 2
		lda nh_rng_a + 3
		ror
		sta accu + 1
		lda nh_rng_a + 2
		ror
		sta accu + 0
	}
}
