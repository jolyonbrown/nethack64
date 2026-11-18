/* far_meas.c - the translation routines of far spaces 1-3 for measure_oscar64.py with
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

/* the pin slots of the compiler's groups of accesses */
unsigned char farpins[4];
#pragma runtime(farpins, farpins)
