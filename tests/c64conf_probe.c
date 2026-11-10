/* c64conf_probe.c - what Oscar64 sees under the C64 configuration (ADR-0006).
 *
 *   mkdir -p build/probe && oscar64 -e -dC64 -dregister= -i=port/include \
 *       -i=tools/measure -o=build/probe/c64conf_probe.prg tests/c64conf_probe.c
 *
 * (Its own directory, so that its .lbl never becomes tools/vice.py's newest build/*.lbl.)
 * Expect no errors and "Emulation result 0".  An #error names the option that is
 * wrong.  The measurement shim comes first only to supply time_t, which the C64
 * configuration leaves to the system layer (c64conf.h); without -dC64 the probe stops
 * in system.h (<sys/types.h>), as ADR-0006 says it must.
 */
#include "c64meas-c64.h"
#include "hack.h"
#include "tcap.h"

#if defined(UNIX) || defined(MICRO) || defined(COMPRESS) || defined(TTY_GRAPHICS) || \
    defined(SHELL) || defined(SUSPEND) || defined(RANDOM) || defined(TERMINFO) || \
    defined(SYSTEM_H) || defined(POSIX_JOB_CONTROL) || defined(SIG_RET_TYPE)
#error "a Unix-only option is still defined"
#endif
#if !defined(C64) || !defined(UNWIDENED_PROTOTYPES) || !defined(NO_SIGNAL) || \
    !defined(MAIL) || !defined(TEXTCOLOR) || !defined(WIZARD) || \
    !defined(TEXT_TOMBSTONE) || !defined(ZEROCOMP) || !defined(RLECOMP) || \
    !defined(INSURANCE) || !defined(NEWS) || !defined(LOGFILE) || !defined(TERMLIB) || \
    !defined(ASCIIGRAPH) || !defined(NHSTDC) || !defined(REDO)
#error "an expected option is missing"
#endif
#if FILENAME != 45
#error "FILENAME is not the host's SAVESIZE"
#endif

const char port_id[] = PORT_ID;

int main(void)
{
	return port_id[0] == 'C' ? 0 : 1;
}
