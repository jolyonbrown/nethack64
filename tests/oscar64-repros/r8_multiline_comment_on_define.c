/* OSCAR64 REPRO r8 - a comment that starts on a #define line and continues
 * NetHack: global.h  #define PL_PSIZ 63 / * player-given names ... (next line) * /
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: tools/oscar_normalize.py folds the comment onto one line.
 * FLAGS: -e
 */
#define Y 0 /* a comment that
               carries on here */
int main(void) { return Y; }
