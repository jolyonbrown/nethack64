#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#define SIG_RET_TYPE void (*)(int)
#define SIGHUP 1
#define SIGINT 2
#define SIGQUIT 3
typedef long off_t;
typedef int pid_t;
typedef int uid_t;
typedef int gid_t;
typedef long time_t;
time_t time(time_t *);
struct tm { int tm_sec, tm_min, tm_hour, tm_mday, tm_mon, tm_year, tm_wday, tm_yday, tm_isdst; };
struct tm *localtime(const time_t *);
char *ctime(const time_t *);
int open(const char *, int, ...);
int close(int);
int read(int, void *, unsigned);
int write(int, const void *, unsigned);
long lseek(int, long, int);
int creat(const char *, int);
int unlink(const char *);
int link(const char *, const char *);
int getuid(void);
int getgid(void);
int getpid(void);
int chdir(const char *);
char *getenv(const char *);
long random(void);
void srandom(unsigned);
int sleep(unsigned);
int fork(void);
int wait(int *);
int execl(const char *, ...);
int tgetent(char *, const char *);
int tgetnum(const char *);
int tgetflag(const char *);
char *tgetstr(const char *, char **);
char *tgoto(const char *, int, int);
int tputs(const char *, int, int (*)(int));
void (*signal(int, void (*)(int)))(int);
void qsort(void *, unsigned, unsigned, int (*)(const void *, const void *));
int fseek(FILE *, long, int);
long ftell(FILE *);
void rewind(FILE *);
int fflush(FILE *);
#define BUFSIZ 256
extern int errno;
struct passwd { char *pw_name; int pw_uid; };
struct passwd *getpwuid(int);
struct passwd *getpwnam(const char *);
char *getlogin(void);
#define O_RDONLY 0
#define O_WRONLY 1
#define O_RDWR 2
#define O_CREAT 0x100
#define O_TRUNC 0x200
#define O_BINARY 0
#define SEEK_SET 0
#define SEEK_CUR 1
#define SEEK_END 2
