/* OSCAR64 REPRO r81 - A CONDITIONAL WITH A FUNCTION AS ITS LAST OPERAND AND A FUNCTION POINTER
 * BEFORE IT IS REJECTED: "error 3013: Incompatible conditional types".
 * `c ? (hook_t)0 : hook`, `c ? p : hook` and even `c ? (hook_t)0 : (hook_t)hook` fail, where
 * hook is a function and p a variable of its pointer type; C89 3.3.15 converts the function
 * to a pointer to it, of the same type as the other operand. The other order,
 * `c ? hook : (hook_t)0`, compiles and is right, as do `c ? 0 : hook` (compat #53's fix) and
 * `c ? (hook_t)0 : p`. The pin (87 commits); v1.32.273 stops before it, on line 33's compare
 * of a function pointer with a function (r16, fixed by the pin); upstream main not built.
 * NetHack: getline.c's tty_get_ext_cmd(), `in_doagain ? (getlin_hook_proc)0 :
 * ext_cmd_getlin_hook`, the tty port's extended commands (#), in the C64 build since Phase 3.
 * Found 2026-11-22, measuring getline.c in the C64 configuration.
 * Expect when fixed: compiles, "Emulation result 0".
 * Workaround: the function first, `!in_doagain ? ext_cmd_getlin_hook : (getlin_hook_proc)0`
 * (getline.c, a comment pointing here).
 */
typedef int (*hook_t)(char *);

static int hook(char *s)
{
	return s[0];
}

static int call(hook_t h, char *s)
{
	return h ? h(s) : 0;
}

int flag;

int main(void)
{
	char s[2] = "a";
	hook_t p = hook;
	int a = call(flag ? (hook_t)0 : hook, s);

	return a == 'a' && p == hook ? 0 : 1;
}
