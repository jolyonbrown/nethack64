#!/usr/bin/env python3
"""Generate an oscar64 measurement harness for one NetHack source file.

usage: mkstubs.py incdir srcdir target.c out.c [also_defined.c ...]
"""
import os, re, subprocess, sys

inc, srcdir, target, out = sys.argv[1:5]
also = sys.argv[5:]
base = os.path.dirname(os.path.abspath(inc))
# the configuration's defines, as oscar64 sees them; measure_oscar64.py sets
# MKSTUBS_DEFS for configs other than the 2026-11-08 UNIX one (the default)
cfg = os.environ["MKSTUBS_DEFS"].split() if "MKSTUBS_DEFS" in os.environ else \
    ["-DSYSTEM_H", "-DNHSTDC", "-DUNWIDENED_PROTOTYPES", "-Dregister="]
def preprocess(path, markers=False):
    pp = subprocess.run(
        ["gcc", "-E", "-nostdinc", "-I", inc, "-I", os.path.join(base, "stub"),
         "-I", os.path.join(base, "fakelibc")] + ([] if markers else ["-P"]) + cfg +
        ["-D__attribute__(x)=", path],
        capture_output=True, text=True, encoding="latin-1")
    if pp.returncode:
        sys.stderr.write(pp.stderr[:3000]); sys.exit(1)
    return pp.stdout

text = preprocess(os.path.join(inc, "hack.h"))

TOKEN = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'|[A-Za-z_]\w*|\S')
MARKER = re.compile(r'^# \d+ "([^"]*)"')

def defs(path):
    """Functions the file itself defines, name -> static?, found in its preprocessed
    text: `name ( ... ) {` at file scope, in lines that come from the file and not
    from a header.  The raw `^name (` regex this replaced took a call that starts a
    line for a definition (pray.c's `pline(`) and missed `pline VA_DECL(...)`."""
    toks = []                      # (token, from this file?)
    own = False
    for line in preprocess(path, markers=True).split("\n"):
        m = MARKER.match(line)
        if m:
            own = os.path.basename(m.group(1)) == os.path.basename(path)
            continue
        toks.extend((t, own) for t in TOKEN.findall(line))
    found, depth, start = {}, 0, 0
    for i, (t, _) in enumerate(toks):
        if t == "{":
            if depth == 0 and i and toks[i - 1][0] == ")":
                d, k = 0, i - 1    # back to the "(" that opens the parameters
                while k >= start:
                    if toks[k][0] == ")":
                        d += 1
                    elif toks[k][0] == "(":
                        d -= 1
                        if d == 0:
                            break
                    k -= 1
                name, mine = toks[k - 1] if k > start else ("", False)
                if mine and re.match(r"[A-Za-z_]\w*$", name):
                    found[name] = "static" in (x for x, _ in toks[start:k - 1])
            depth += 1
        elif t == "}":
            depth -= 1
            if depth == 0:
                start = i + 1
        elif t == ";" and depth == 0:
            start = i + 1
    return found

def own_lines(path):
    """The preprocessed lines that come from the file itself, macros expanded."""
    keep, own = [], False
    for line in preprocess(path, markers=True).split("\n"):
        m = MARKER.match(line)
        if m:
            own = os.path.basename(m.group(1)) == os.path.basename(path)
        elif own:
            keep.append(line)
    return "\n".join(keep)

own_defs = defs(os.path.join(srcdir, target))
defined = set(own_defs)
for extra in also:
    defined |= set(defs(os.path.join(srcdir, extra)))

# Arrays declared `extern T name[];` that the file uses but no file in this program
# defines (hu_stat is in eat.c, killed_by_prefix in topten.c, ...): Oscar64 stops
# with "Undefined variable type".  Their definitions are copied from the file that
# has them, so that the array, and code that indexes it, keep their real size.  A
# definition whose size needs a macro the headers do not give (SAVEF[SAVESIZE]) or
# that is not in port/src (the generated monstr[]) is left out: the error stays.
EXTERN_ARRAY = re.compile(r"\bextern\s+[^;()]*?\b([A-Za-z_]\w*)\s*\[\s*\]\s*;")
FILE_SCOPE_ARRAY = r"(?m)^(?!extern\b|E\b)[A-Za-z_][^;\n(=]*\b%s\s*\[([^\]\n]*)\]"

def raw(name):
    return open(os.path.join(srcdir, name), encoding="latin-1").read()

def definition(text, name):
    """The file-scope definition of array `name` in raw source, through its ';'."""
    m = re.search(FILE_SCOPE_ARRAY % re.escape(name), text)
    if not m:
        return None, None
    i = j = m.start()
    depth = 0
    while j < len(text):
        if text.startswith("/*", j):
            j = text.index("*/", j) + 2
            continue
        c = text[j]
        if c in "\"'":
            j += 1
            while text[j] != c:
                j += 2 if text[j] == "\\" else 1
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == ";" and depth == 0:
            return text[i:j + 1], m.group(1).strip()
        j += 1
    return None, None

header_macros = set()
for h in os.listdir(inc):
    if h.endswith(".h"):
        header_macros |= set(re.findall(r"(?m)^\s*#\s*define\s+([A-Za-z_]\w*)",
                                        open(os.path.join(inc, h), encoding="latin-1").read()))
program = [raw(target)] + [raw(x) for x in also]
array_defs = []

# used through a macro counts (light.c reaches circle_data through circle_ptr())
target_uses = re.sub(r"\bextern\b[^;]*;", "", own_lines(os.path.join(srcdir, target)))
wanted = sorted(set(EXTERN_ARRAY.findall(preprocess(os.path.join(srcdir, target)))))
for name in wanted:
    if re.search(r"\b%s\b" % re.escape(name), target_uses) is None:
        continue                                   # declared, never used here
    if any(re.search(FILE_SCOPE_ARRAY % re.escape(name), t) for t in program):
        continue                                   # defined in this program
    for f in sorted(os.listdir(srcdir)):
        if not f.endswith(".c") or f == target or f in also:
            continue
        found, size = definition(raw(f), name)
        if found is None:
            continue
        if all(w in header_macros or w.isdigit() for w in re.findall(r"\w+", size)):
            array_defs.append("/* from %s */\n%s" % (f, found))
        break
static_names = {n for n, st in own_defs.items() if st}
# measure_oscar64.py counts the code of exactly these functions as the file's own
with open(os.path.splitext(out)[0] + ".defs", "w") as f:
    f.write("\n".join(sorted(own_defs)) + "\n")

protos = []
for m in re.finditer(r"^extern\s+([^;()]*?)\b([A-Za-z_]\w*)\s*\(([^;]*)\)\s*;\s*$", text, re.M):
    if m.group(2) in ("int", "char", "long", "void", "__attribute__") or "__attribute__" in m.group(3) or "(*" in m.group(1):
        continue
    protos.append((m.group(1).strip(), m.group(2), m.group(3).strip()))

lines = ['#include "hack.h"', '#include "dlb.h"', "",
         "/* opaque return values so the optimiser cannot fold stubbed calls */",
         "volatile long nh_vl; void * volatile nh_vp;", ""] + array_defs + [""]
refs, seen = [], set()
for ret, name, args in protos:
    if name in seen:
        continue
    seen.add(name)
    if name in defined:
        if name not in static_names:
            refs.append(name)
        continue
    params = args if args else "void"
    is_void = re.fullmatch(r"(?:static\s+)?void", ret) is not None
    lines.append("#undef %s" % name)
    if is_void:
        # r14: a variadic function with an empty body cannot be called with arguments
        body = " nh_vl = 0; " if "..." in params else ""
    elif "*" in ret:
        # r34: Oscar64 merges two reads of the volatile pointer nh_vp; a read of
        # nh_vl through a cast keeps every call's result opaque
        body = " return (%s)(unsigned)nh_vl; " % ret
    else:
        body = " return (%s)nh_vl; " % ret
    lines.append("%s %s(%s) {%s}" % (ret, name, params, body))

lines += ["", "void *nh_refs[] = {"] + ["  (void *)%s," % r for r in refs] + [
    "  0 };", "int main(void) { volatile int i; for (i = 0; nh_refs[i]; i++) ; return i; }"]
open(out, "w").write("\n".join(lines) + "\n")
print("refs:", len(refs), "stubs:", len(seen) - len(refs))
