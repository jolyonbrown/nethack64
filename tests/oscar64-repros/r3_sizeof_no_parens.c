/* OSCAR64 REPRO r3 - sizeof applied to an expression without parentheses
 * NetHack: 117 sites, e.g. artifact.c  memset(artiexist, 0, sizeof artiexist)
 * Expect when fixed: compiles, emulation result 0.
 * Workaround: tools/oscar_normalize.py adds the parentheses.
 * FLAGS: -e
 */
int arr[10];
int main(void) { return sizeof arr == 20 ? 0 : 1; }
