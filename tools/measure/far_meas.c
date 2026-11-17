/* far_meas.c - the translation routines of far space 1 for measure_oscar64.py with
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
