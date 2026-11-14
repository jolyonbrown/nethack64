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

def defs(path, decls=None):
    """Functions the file itself defines, name -> static?, found in its preprocessed
    text: `name ( ... ) {` at file scope, in lines that come from the file and not
    from a header.  The raw `^name (` regex this replaced took a call that starts a
    line for a definition (pray.c's `pline(`) and missed `pline VA_DECL(...)`.
    `decls`, if given, gets each definition's text up to its `{`."""
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
                    if decls is not None:
                        decls[name] = " ".join(x for x, _ in toks[start:i])
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

own_decls = {}
own_defs = defs(os.path.join(srcdir, target), own_decls)
defined = set(own_defs)
for extra in also:
    defined |= set(defs(os.path.join(srcdir, extra)))

# Arrays declared `extern T name[];` that the file uses but no file in this program
# defines (hu_stat is in eat.c, killed_by_prefix in topten.c, ...): Oscar64 stops
# with "Undefined variable type".  Their definitions are copied from the file that
# has them, so that the array, and code that indexes it, keep their real size.  The
# copy comes from that file's preprocessed text, so macros are expanded and #if
# resolved for this configuration (SAVEF[SAVESIZE]: SAVESIZE is files.c's own).
EXTERN_ARRAY = re.compile(r"\bextern\s+[^;()]*?\b([A-Za-z_]\w*)\s*\[\s*\]\s*;")
# raw source: file-scope definitions start in column 0 (indented ones are locals)
RAW_ARRAY = r"(?m)^(?!extern\b|E\b)[A-Za-z_][^;\n(=]*\b%s\s*\[([^\]\n]*)\]"
# preprocessed text: macros such as NEARDATA leave a leading blank, so allow one and
# check the brace depth instead
FILE_SCOPE_ARRAY = r"(?m)^(?!\s*extern\b|E\b)\s*[A-Za-z_][^;\n(=]*\b%s\s*\[([^\]\n]*)\]"

def raw(name):
    return open(os.path.join(srcdir, name), encoding="latin-1").read()

def definition(text, name):
    """The file-scope (brace depth 0) definition of array `name`, through its ';'."""
    for m in re.finditer(FILE_SCOPE_ARRAY % re.escape(name), text):
        toks = TOKEN.findall(text[:m.start()])
        if toks.count("{") != toks.count("}"):
            continue                                   # inside a function or initializer
        i = j = m.start()
        depth = 0
        while j < len(text):
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
                return text[i:j + 1].strip()
            j += 1
    return None

STRING = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'')

def dependencies(ftext, found, seen):
    """File-scope arrays of `ftext` that the initializer of `found` names and the
    headers do not declare, each before its first use (recursively)."""
    out = []
    init = STRING.sub("", found.split("=", 1)[1]) if "=" in found else ""
    for ident in sorted(set(re.findall(r"\b[A-Za-z_]\w*\b", init))):
        if ident in seen or re.search(r"\b%s\b" % re.escape(ident), text):
            continue                                   # done, or known from hack.h
        dep = definition(ftext, ident)
        if dep:
            seen.add(ident)
            out += dependencies(ftext, dep, seen) + [dep]
    return out

program = [raw(target)] + [raw(x) for x in also]
array_defs = []

# used through a macro counts (light.c reaches circle_data through circle_ptr())
target_uses = re.sub(r"\bextern\b[^;]*;", "", own_lines(os.path.join(srcdir, target)))
wanted = sorted(set(EXTERN_ARRAY.findall(preprocess(os.path.join(srcdir, target)))))
for name in wanted:
    if re.search(r"\b%s\b" % re.escape(name), target_uses) is None:
        continue                                   # declared, never used here
    if any(re.search(RAW_ARRAY % re.escape(name), t) for t in program):
        continue                                   # defined in this program
    for f in sorted(os.listdir(srcdir)):
        if not f.endswith(".c") or f == target or f in also:
            continue
        if re.search(RAW_ARRAY % re.escape(name), raw(f)) is None:
            continue
        ftext = own_lines(os.path.join(srcdir, f))
        found = definition(ftext, name)
        if found:
            # shknam.c's shtypes[] names static arrays of the same file (shkgeneral,
            # ...): copy those first, else the copy stops with "Unknown identifier"
            deps = dependencies(ftext, found, {name})
            array_defs.append("/* from %s, preprocessed */\n%s" % (f, "\n".join(deps + [found])))
        break
static_names = {n for n, st in own_defs.items() if st}
# measure_oscar64.py counts the code of exactly these functions as the file's own
with open(os.path.splitext(out)[0] + ".defs", "w") as f:
    f.write("\n".join(sorted(own_defs)) + "\n")

PROTO = re.compile(r"^extern\s+([^;()]*?)\b([A-Za-z_]\w*)\s*\(([^;]*)\)\s*;\s*$", re.M)

def prototypes(src):
    found = []
    for m in PROTO.finditer(src):
        if m.group(2) in ("int", "char", "long", "void", "__attribute__") or "__attribute__" in m.group(3) or "(*" in m.group(1):
            continue
        found.append((m.group(1).strip(), m.group(2), m.group(3).strip()))
    return found

protos = prototypes(text)
# extern.h declares flood_fill_rm and remove_rooms without E (as upstream does):
# take such bare prototypes from NetHack's headers only, not from Oscar64's libc
BARE_PROTO = re.compile(r"^(?!extern\b|typedef\b|static\b)([A-Za-z_][^;()]*?)\b([A-Za-z_]\w*)\s*\(([^;]*)\)\s*;\s*$", re.M)
nh_lines, from_inc = [], False
for line in preprocess(os.path.join(inc, "hack.h"), markers=True).split("\n"):
    m = MARKER.match(line)
    if m:
        from_inc = os.path.dirname(os.path.abspath(m.group(1))) == os.path.abspath(inc)
    elif from_inc:
        nh_lines.append(line)
for m in BARE_PROTO.finditer("\n".join(nh_lines)):
    if m.group(2) not in ("int", "char", "long", "void") and "__attribute__" not in m.group(3):
        protos.append((m.group(1).strip(), m.group(2), m.group(3).strip()))
# functions the file declares itself (sp_lev.c: `extern void mkmap(lev_init *);`):
# their types can come from the file's own headers, so the harness includes those
own_protos = prototypes(own_lines(os.path.join(srcdir, target)))
protos += own_protos
# non-static functions the file defines that no prototype declares (mkmap.c's
# mkmap(), declared in sp_lev.c): nothing would reference them, so the program
# would drop them and every static function only they call
declared = {name for _, name, _ in protos}
undeclared = sorted(n for n, st in own_defs.items() if not st and n not in declared and n != "main")
headers = ["hack.h", "dlb.h"]
if own_protos or undeclared:
    for h in re.findall(r'(?m)^[ \t]*#[ \t]*include[ \t]+"([^"]+\.h)"', raw(target)):
        if h not in headers and h != "artilist.h" and os.path.exists(os.path.join(inc, h)):
            headers.append(h)                          # artilist.h defines an array


def split_params(params):
    parts, depth, cur = [], 0, ""
    for c in params:
        if c == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
            continue
        depth += c in "(["
        depth -= c in ")]"
        cur += c
    return parts + [cur.strip()]


C_TYPE_WORDS = {"int", "char", "short", "long", "unsigned", "signed", "void", "float",
                "double", "const", "volatile", "struct", "union", "enum", "register"}


def param_name(p):
    """The name a prototype parameter already has (extern.h has a few:
    `struct obj_s *obj`), or None."""
    m = re.search(r"\(\s*\*\s*([A-Za-z_]\w*)\s*\)", p)
    if m:
        return m.group(1)                          # int (*fn)(int)
    if re.search(r"\(\s*\*\s*\)", p):
        return None                                # int (*)(int)
    head = p.split("[", 1)[0].strip()
    m = re.search(r"\b([A-Za-z_]\w*)$", head)
    if not m or m.group(1) in C_TYPE_WORDS:
        return None
    rest = head[:m.start()].strip()
    # a type must remain: `xchar` or `const coord` alone is a type with no name
    if "*" in rest or any(w not in ("const", "volatile", "struct", "union", "enum", "register")
                          for w in re.findall(r"[A-Za-z_]\w*", rest)):
        return m.group(1)
    return None


SCALAR_WORDS = {"int", "char", "short", "long", "unsigned", "signed", "float", "double"}


def param_kind(ptype, depth=0):
    """"pointer", "scalar", "struct" or "unknown", following typedefs in hack.h."""
    if re.search(r"[*\[(]", ptype):
        return "pointer"
    words = [w for w in re.findall(r"[A-Za-z_]\w*", ptype) if w not in ("const", "volatile", "register")]
    if not words or words[0] == "enum" or all(w in SCALAR_WORDS for w in words):
        return "scalar"
    if words[0] in ("struct", "union"):
        return "struct"
    m = re.search(r"\btypedef\s+([^;{}]*?)\b%s\s*;" % re.escape(words[-1]), text)
    if m and depth < 8:
        return param_kind(m.group(1), depth + 1)
    if re.search(r"\}\s*%s\s*;" % re.escape(words[-1]), text):
        return "struct"                            # typedef struct { ... } coord;
    return "unknown"


def named_params(params):
    """`(const char *, int (*)(int))` -> names a0, a1, ... and a statement that uses
    each value.  An unused parameter lets the optimiser drop the argument at the call
    (and a call to an empty void stub altogether), so the file being measured would
    lose that code, and a `?:` argument then hits r58.  Taking the parameter's address
    instead would change how every call passes it, which costs the caller more code."""
    if params in ("", "void"):
        return "void", ""
    named, uses = [], []
    for k, p in enumerate(split_params(params)):
        if p == "...":
            named.append(p)
            continue
        n = param_name(p)
        if n:
            named.append(p)
            ptype = p if re.search(r"[*\[(]", p) else p[:p.rindex(n)]
        else:
            n, ptype = "a%d" % k, p
            if re.search(r"\(\s*\*\s*\)", p):
                named.append(re.sub(r"\(\s*\*\s*\)", "(*%s)" % n, p, count=1))
            elif "[" in p:
                named.append(p.replace("[", " %s[" % n, 1))
            else:
                named.append("%s %s" % (p, n))
        kind = param_kind(ptype)
        if kind == "pointer":
            uses.append("nh_vp = (void *)%s;" % n)
        elif kind == "scalar":
            uses.append("nh_vl = (long)%s;" % n)
    return ", ".join(named), " ".join(uses)

lines = ['#include "%s"' % h for h in headers] + [
         "",
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
    params, uses = named_params(args)
    is_void = re.fullmatch(r"(?:static\s+)?void", ret) is not None
    lines.append("#undef %s" % name)
    if is_void:
        # r14: a variadic function with an empty body cannot be called with arguments
        body = " %s " % uses if uses else (" nh_vl = 0; " if "..." in params else "")
    elif "*" in ret:
        # r34: Oscar64 merges two reads of the volatile pointer nh_vp; a read of
        # nh_vl through a cast keeps every call's result opaque
        body = " %sreturn (%s)(unsigned)nh_vl; " % (uses + " " if uses else "", ret)
    else:
        body = " %sreturn (%s)nh_vl; " % (uses + " " if uses else "", ret)
    lines.append("%s %s(%s) {%s}" % (ret, name, params, body))

for name in undeclared:
    lines.append("extern %s;" % own_decls[name])
    refs.append(name)

lines += ["", "void *nh_refs[] = {"] + ["  (void *)%s," % r for r in refs] + [
    "  0 };", "int main(void) { volatile int i; for (i = 0; nh_refs[i]; i++) ; return i; }"]
open(out, "w").write("\n".join(lines) + "\n")
print("refs:", len(refs), "stubs:", len(seen) - len(refs))
