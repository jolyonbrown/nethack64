/*
 * far_pre.h - the translations of the speed harness's far build (farify.py, calibrate.py
 * --far; docs/RAM-PLAN.md, T2.11), included before the headers.
 *
 * A far type's pointers stay 16 bits: an address in that type's own space.  Before an
 * access, XL_<tag>() looks the pointer's page up in the type's table, as the spike's hit
 * path does (tests/spikes/fardata.c), and gives the RAM address.  Every page is mapped here
 * (a warm cache); a missing one would count a fault.  -dNH_FAR_VOLATILE makes the tables
 * volatile, so that no translation is reused: one for every access.  -dNH_FAR_COUNT counts
 * the translations of each type (nh_far_count_<tag>), for calibrate.py --far-count.
 */
#ifndef FAR_PRE_H
#define FAR_PRE_H

#ifdef NH_FAR_CC
/* calibrate.py --far-cc: an Oscar64 with far spaces (T2.12) translates by itself, through
 * each space's farxlN (cal.c), from the same tables; nothing is rewritten */
#ifdef NH_FAR_PERMONST
#pragma farspace(1, permonst, attack)
#endif
#ifdef NH_FAR_MONST_S
#pragma farspace(2, monst_s, epri, emin, eshk, egd, edog)
#endif
#ifdef NH_FAR_OBJ_S
#pragma farspace(3, obj_s)
#endif
#ifdef NH_FAR_TRAP_S
#pragma farspace(4, trap_s)
#endif
#define NH_TLB_QUAL
#else

#ifdef NH_FAR_VOLATILE
#define NH_TLB_QUAL	volatile
#else
#define NH_TLB_QUAL
#endif

extern void nh_far_fault(void);

/* pasted by the caller: Oscar64 pastes a nested macro's parameter wrongly (compat #71, r68) */
#ifdef NH_FAR_COUNT
#define NH_FAR_COUNTED(counter)	counter++;
#else
#define NH_FAR_COUNTED(counter)
#endif

#define NH_FAR_SPACE(tag) \
	struct tag; \
	extern NH_TLB_QUAL unsigned char nh_tlb_##tag[256]; \
	extern unsigned long nh_far_count_##tag; \
	static inline struct tag *XL_##tag(const struct tag *p) \
	{ \
		unsigned v = (unsigned) p; \
		unsigned char r = nh_tlb_##tag[v >> 8]; \
		NH_FAR_COUNTED(nh_far_count_##tag) \
		if (!r) \
			nh_far_fault(); \
		return (struct tag *) (((unsigned) r << 8) | (v & 0xff)); \
	}

NH_FAR_SPACE(permonst)
NH_FAR_SPACE(monst_s)
NH_FAR_SPACE(obj_s)
NH_FAR_SPACE(trap_s)
#endif

#endif
