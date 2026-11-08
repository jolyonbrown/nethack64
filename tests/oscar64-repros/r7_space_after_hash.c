/* OSCAR64 REPRO r7 - whitespace between '#' and the directive name
 * NetHack uses "# define", "#  ifdef" throughout its headers.
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: tools/oscar_normalize.py moves the spaces before the '#'.
 * FLAGS: -e
 */
#ifdef FOO
# define X 1
#else
# ifdef BAR
#  define X 2
# else
#  define X 0
# endif
#endif
int main(void) { return X; }
