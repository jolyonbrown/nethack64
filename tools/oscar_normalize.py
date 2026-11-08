#!/usr/bin/env python3
"""
oscar_normalize.py - work around two Oscar64 preprocessor limitations that
NetHack 3.4.3's headers trip over (verified against oscar64 v1.32.273):

 1. Whitespace between '#' and the directive name ("# define", "#  ifdef")
    is not recognised in active code.  Leading whitespace *before* the '#'
    is fine, so "#  define X" becomes "  #define X" (indentation kept).

 2. A /* comment */ that starts on a preprocessor line and continues onto
    the next line(s) is not handled; the continuation is parsed as code.
    The comment's continuation lines are folded onto the directive line.

 3. Struct tags share a namespace with functions and variables (C++ style):
    `struct attack` + function attack() is a "Duplicate definition", and a
    parameter `struct obj *obj` makes a later `struct obj *otmp` in the same
    scope fail with "Struct expected".  Every NetHack tag that is also used
    as an ordinary identifier is renamed with a `_s` suffix (tags only; the
    variables and functions keep their names, so game code is untouched).

 4. `sizeof x` without parentheses is not accepted; it becomes `sizeof(x)`.

 5. The `trap` typedef in sp_lev.h collides with `struct trap`; it is
    renamed `sp_trap` in the special-level loader and level compiler.

All rewrites are behaviour-preserving for any conforming compiler, so the
normalised tree still builds with gcc/cc65.

Usage: oscar_normalize.py [--check] file [file ...]
    --check   report files that would change, exit 1 if any (for CI)
"""
import re
import sys

DIRECTIVE_RE = re.compile(r"^([ \t]*)#([ \t]+)([A-Za-z]\w*)")

# Struct/union tags that are also used as ordinary identifiers somewhere in
# NetHack 3.4.3 (a variable, parameter or function of the same name, e.g. the
# 369 `struct obj *obj` declarations).  Oscar64 resolves a later `struct obj`
# to the variable once one is in scope, so every such tag gets a `_s` suffix.
# Renaming a tag is always safe: tags are only ever written as `struct X`.
# libc tags (tm, stat, dirent) are deliberately NOT renamed.
COLLIDING_TAGS = [
    "obj", "trap", "monst", "any", "d_level", "mvitals", "edog", "container",
    "flag", "damage", "s_level", "spell", "branch", "multishot", "eshk",
    "trapinfo", "skills", "stairway", "mi", "dlb_procs", "c_color_names",
    "c_common_strings", "tc_gbl_data", "tc_lcl_data", "engr", "dest_area",
    "prop", "align", "dungeon", "rm", "artifact", "d_flags", "worn",
    "level_map", "wseg", "you", "attack", "menu", "mkroom", "tmpbranch",
    "tmpdungeon", "tmplevel",
]
TAG_RE = re.compile(r"\b(struct|union)(\s+)(%s)\b" % "|".join(COLLIDING_TAGS))

# sp_lev.h: `typedef struct {...} trap;` collides with `struct trap` (rm.h).
# The typedef is renamed to sp_trap wherever it is used as a type name.
SPTRAP_RULES = [
    (re.compile(r"\}\s*trap;"), "} sp_trap;"),
    (re.compile(r"(?<![\w.>])trap(\s*\*)"), r"sp_trap\1"),
    (re.compile(r"\b(NewTab|New)\(trap\b"), r"\1(sp_trap"),
    (re.compile(r"sizeof\(trap\)"), "sizeof(sp_trap)"),
    (re.compile(r"^(\s*)trap(\s+tmptrap\b)", re.M), r"\1sp_trap\2"),
]
SPTRAP_FILES = ("sp_lev.h", "sp_lev.c", "lev_comp.y", "lev_main.c")

# `sizeof x` / `sizeof *p` / `sizeof a.b[2]` without parentheses
SIZEOF_RE = re.compile(r"\bsizeof\s+(?!\()(\**[A-Za-z_]\w*(?:(?:\.|->)\w+|\[[^\]\n]*\])*)")

# `(char *)(otmp)->oextra`: Oscar64 binds the cast before `->`.
CAST_ARROW_RE = re.compile(
    r"(\(\s*(?:const\s+)?(?:unsigned\s+)?[A-Za-z_]\w*\s*\*+\s*\))\s*\(([^()]+)\)\s*->\s*(\w+)")

# `(int FDECL((*),(MONST_P,OBJ_P)))0`: abstract function-pointer casts are not
# parsed.  A cast of the literal 0 is just a null pointer constant, so the
# cast is dropped (all uses are prototyped arguments or initialisers).
FNPTR_NULL_RE = re.compile(
    r"\(\s*[A-Za-z_]\w*\s+(?:NDECL\(\s*\(\*\)\s*\)|FDECL\(\s*\(\*\)\s*,\s*\([^()]*\)\s*\))\s*\)\s*0\b")


def normalise_text(text, path=""):
    text = TAG_RE.sub(lambda m: "%s%s%s_s" % (m.group(1), m.group(2), m.group(3)), text)
    text = SIZEOF_RE.sub(r"sizeof(\1)", text)
    text = CAST_ARROW_RE.sub(r"\1((\2)->\3)", text)
    text = FNPTR_NULL_RE.sub("0", text)
    if path.endswith(SPTRAP_FILES):
        for rx, rep in SPTRAP_RULES:
            text = rx.sub(rep, text)
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = DIRECTIVE_RE.match(line)
        if m:
            line = m.group(1) + m.group(2) + "#" + line[m.end(2):]
        if line.lstrip().startswith("#"):
            # fold an unterminated trailing comment onto this line
            joined = line
            while True:
                code = re.sub(r"/\*.*?\*/", "", joined)
                if "/*" in code and i + 1 < len(lines):
                    i += 1
                    joined = joined.rstrip() + " " + lines[i].strip()
                else:
                    break
            line = joined
        out.append(line)
        i += 1
    return "\n".join(out)


def main():
    args = sys.argv[1:]
    check = False
    if args and args[0] == "--check":
        check = True
        args = args[1:]
    changed = []
    for path in args:
        with open(path, encoding="latin-1") as f:
            text = f.read()
        new = normalise_text(text, path)
        if new != text:
            changed.append(path)
            if not check:
                with open(path, "w", encoding="latin-1") as f:
                    f.write(new)
    for p in changed:
        print(("would change: " if check else "normalised: ") + p)
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
