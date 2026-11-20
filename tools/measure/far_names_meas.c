/* far_names_meas.c - NH_MNAME()/NH_ONAME()/NH_RNAME() for measure_oscar64.py's files compiled one at
 * a time (MEASURE_EXTRA, with far_meas.c): the whole-game build has them from bankgen.py's
 * nhbank.h, which a file measured alone does not include (T2.12). */
const char *nh_mname(const char *p) { return p; }
const char *nh_oname(const char *p) { return p; }
const char *nh_rname(const char *p) { return p; }
const char *nh_mname_b(const char *p, char *d) { return p; }
const char *nh_oname_b(const char *p, char *d) { return p; }
