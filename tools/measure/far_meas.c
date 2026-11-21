/* far_meas.c - the translation routines of far spaces 1-5 for measure_oscar64.py with
 * MEASURE_DEFS=-dNH_FAR_SPACES (T2.12): every page maps to itself, so a program measured
 * this way runs as the near one does; what the measurement wants is the code and the
 * compiler's warnings 2026.  MEASURE_EXTRA=tools/measure/far_meas.c. */
unsigned char nh_meas_xoff;

/* page X to RAM page A, Y kept */
__asm farxl1
{
		txa
		rts
}

/* address A/X plus offset Y to its RAM address in A/X */
__asm farxo1
{
		sty nh_meas_xoff
		clc
		adc nh_meas_xoff
		bcc done
		inx
done:	rts
}

#pragma runtime(farxl1, farxl1)
#pragma runtime(farxo1, farxo1)

/* the far pointer at zero page address X to its RAM address in ADDR (page in A too), Y kept */
__asm farxz1
{
		lda $00, x
		sta __addr + 0
		lda $01, x
		sta __addr + 1
		rts
}
#pragma runtime(farxz1, farxz1)

__asm farxl2
{
		txa
		rts
}

__asm farxo2
{
		sty nh_meas_xoff
		clc
		adc nh_meas_xoff
		bcc done2
		inx
done2:	rts
}

#pragma runtime(farxl2, farxl2)
#pragma runtime(farxo2, farxo2)

/* the far pointer at zero page address X to its RAM address in ADDR (page in A too), Y kept */
__asm farxz2
{
		lda $00, x
		sta __addr + 0
		lda $01, x
		sta __addr + 1
		rts
}
#pragma runtime(farxz2, farxz2)

__asm farxl3
{
		txa
		rts
}

__asm farxo3
{
		sty nh_meas_xoff
		clc
		adc nh_meas_xoff
		bcc done3
		inx
done3:	rts
}

#pragma runtime(farxl3, farxl3)
#pragma runtime(farxo3, farxo3)

/* the far pointer at zero page address X to its RAM address in ADDR (page in A too), Y kept */
__asm farxz3
{
		lda $00, x
		sta __addr + 0
		lda $01, x
		sta __addr + 1
		rts
}
#pragma runtime(farxz3, farxz3)

__asm farxl4
{
		txa
		rts
}

__asm farxo4
{
		sty nh_meas_xoff
		clc
		adc nh_meas_xoff
		bcc done4
		inx
done4:	rts
}

#pragma runtime(farxl4, farxl4)
#pragma runtime(farxo4, farxo4)

/* the far pointer at zero page address X to its RAM address in ADDR (page in A too), Y kept */
__asm farxz4
{
		lda $00, x
		sta __addr + 0
		lda $01, x
		sta __addr + 1
		rts
}
#pragma runtime(farxz4, farxz4)

/* far space 5: the globals a far default moves (c64conf.h, NH_FAR_DEFAULT) */
__asm farxl5
{
		txa
		rts
}

__asm farxo5
{
		sty nh_meas_xoff
		clc
		adc nh_meas_xoff
		bcc done5
		inx
done5:	rts
}

#pragma runtime(farxl5, farxl5)
#pragma runtime(farxo5, farxo5)

__asm farxz5
{
		lda $00, x
		sta __addr + 0
		lda $01, x
		sta __addr + 1
		rts
}
#pragma runtime(farxz5, farxz5)

#ifdef NH_FAR_CHARS
/* far space 6, the character space (c64conf.h, NH_FAR_CHARS): an address below $C000 is
 * near and comes back as it is, which here every page does anyway */
__asm farxl6
{
		txa
		rts
}

__asm farxo6
{
		sty nh_meas_xoff
		clc
		adc nh_meas_xoff
		bcc done6
		inx
done6:	rts
}

#pragma runtime(farxl6, farxl6)
#pragma runtime(farxo6, farxo6)

__asm farxz6
{
		lda $00, x
		sta __addr + 0
		lda $01, x
		sta __addr + 1
		rts
}
#pragma runtime(farxz6, farxz6)

/* the library's assembler string routines translate through this (-dOSCAR_FARCHARS) */
void farxzc(void)
{
	__asm { jmp farxz6 }
}
#endif

/* the pin slots of the compiler's groups of accesses */
unsigned char farpins[4];
#pragma runtime(farpins, farpins)

/* far names (permonst.h, objclass.h): every page maps to itself, so a copy from the
 * space is a copy in place */
void nh_farcopy(char *d, const char *p, unsigned n, unsigned char s)
{
	while (n--)
		*d++ = *p++;
}
