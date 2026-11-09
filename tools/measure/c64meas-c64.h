/* c64meas-c64.h - measurement-only stand-in for the C64 system layer.
 *
 * measure_oscar64.py --config c64 installs this as inc/c64meas.h, included
 * before config1.h exactly like the UNIX shim (c64meas.h).  It declares only
 * what the Phase 2 file layer and the Phase 3 system layer are expected to
 * supply: no signals, fork/exec, uids, passwd or termcap, so any Unix
 * plumbing left in the C64 configuration still shows up as an error.
 * Functions are extern so mkstubs.py stubs them ("linking aside").
 * NOT the port's system layer: its real interface (functions or macros,
 * which O_* values, where errno lives) is decided there.
 */
#include <stdio.h>
typedef long off_t;
typedef long time_t;
struct tm { int tm_sec, tm_min, tm_hour, tm_mday, tm_mon, tm_year, tm_wday, tm_yday, tm_isdst; };
extern time_t time(time_t *);
extern struct tm *localtime(const time_t *);
extern int open(const char *, int, int);
extern int creat(const char *, int);
extern int close(int);
extern int read(int, void *, unsigned);
extern int write(int, const void *, unsigned);
extern long lseek(int, long, int);
extern int unlink(const char *);
extern int rename(const char *, const char *);
extern char *getenv(const char *);
extern void qsort(void *, unsigned, unsigned, int (*)(const void *, const void *));
extern int fseek(FILE *, long, int);
extern long ftell(FILE *);
extern void rewind(FILE *);
/* a function, not a variable, so that mkstubs.py stubs it; still an lvalue */
extern int *c64m_errno(void);
#define errno (*c64m_errno())
#define O_RDONLY 0
#define O_WRONLY 1
#define O_RDWR 2
#define O_CREAT 0x100
#define O_TRUNC 0x200
