#!/usr/bin/env python3
"""bankgen.py - put NetHack's functions into banks by rewriting copies of its source
(the banking spike, docs/BANKING-SPIKE.md).

usage: tools/bank/bankgen.py --plan PLAN.json --dir DIR [--inc DIR] [--cpp FLAG ...]
                             [--define-in FILE.c] FILE.c ...

Rewrites each FILE.c in DIR in place, so run it on a copy (build/host, a measurement
harness), and writes DIR/nhbank.h.  PLAN.json is {"banks": {"file.c:name": N, ...}}
(tools/measure/bankpart.py --plan-out); a function it does not name stays resident.
For a function the plan puts in bank N:

- `#pragma code(nhbank_N)` goes before its definition, so Oscar64 places it in bank N
  (other compilers ignore the pragma); `#pragma code(code)` goes before resident ones.
- A function-like macro, `#define name(...) name__bN(__VA_ARGS__)`, renames the
  definition.  It is in force in the file's functions of bank N, so their calls go
  straight to name__bN, and undefined in the others, so calls from other banks and from
  resident code, and every use of `name` that is not a call (a function pointer), reach
  `name` itself.
- `name` becomes a resident trampoline, appended to the file: it selects bank N, calls
  name__bN and selects the caller's bank again.  String arguments are copied out of the
  bank window before the switch, and a string result after it (nh_stash()), because the
  caller's literals are not mapped while the callee runs, nor the callee's after it
  returns.

A function the macro cannot reach safely stays resident and is reported: a variadic one
(a trampoline cannot pass `...` on), one whose declarator the parser does not handle,
and one whose name is also a macro or a struct member.

Each banked definition is wrapped in its own `#pragma code(nhbank_N)` ... `#pragma
code(code)`: Oscar64 puts a string literal into the code section in force where it is
written, so a file-scope initialiser between two banked functions (`const char *names[]
= {"a", "b"}`) would otherwise have its strings in a bank, unreadable from every other.

--linker-stubs: for an Oscar64 whose linker sends calls into a bank, and the addresses of
banked functions, through stubs (Linker::InsertBankCalls, enabled by the bank call
routine that nhbank.h then defines).  Only a function that takes or returns a `char *`
is renamed and gets a trampoline, which copies the strings; every other banked function
keeps its name and is called directly, the linker inserting the bank switch.  There is
no entry check on the host then: nothing there sees the linker's stubs.
"""
import argparse
import json
import os
import re
import subprocess
import sys

TOKEN = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'|[A-Za-z_]\w*|\.\.\.|->|\S')
MARKER = re.compile(r'^# (\d+) "([^"]*)"')
IDENT = re.compile(r"[A-Za-z_]\w*$")
C_WORDS = {"int", "char", "short", "long", "unsigned", "signed", "void", "float", "double",
           "const", "volatile", "struct", "union", "enum", "register", "static", "extern"}
CHAR_PTR = re.compile(r"^(?:const\s+)?char\s*\*\s*(?:const\s*)?$")
COMMENT_OR_STRING = re.compile(r'/\*.*?\*/|"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'', re.S)


def preprocess(path, inc, cpp):
    r = subprocess.run(["gcc", "-E"] + ["-I" + d for d in inc] + cpp + [path],
                       capture_output=True, text=True, encoding="latin-1")
    if r.returncode:
        sys.exit("gcc -E %s failed:\n%s" % (path, r.stderr[:3000]))
    return r.stdout


def tokens(text, path):
    """(token, line in `path` or 0 if from another file) for the preprocessed text."""
    out, own, line = [], False, 0
    base = os.path.basename(path)
    for ln in text.split("\n"):
        m = MARKER.match(ln)
        if m:
            own = os.path.basename(m.group(2)) == base
            line = int(m.group(1))
            continue
        if ln.lstrip().startswith("#"):
            # a #pragma the preprocessor passes on (hack.h's fardefault) is no declaration's
            line += 1
            continue
        for t in TOKEN.findall(ln):
            out.append((t, line if own else 0))
        line += 1
    return out


def definitions(toks):
    """The file's own function definitions, in order: name, its line, static?, the
    tokens of its declarator up to the `{`, and the identifiers it calls."""
    found, depth, start, cur = [], 0, 0, None
    for i, (t, line) in enumerate(toks):
        if t == "{":
            if depth == 0 and i and toks[i - 1][0] == ")":
                d, k = 0, i - 1
                while k >= start:
                    if toks[k][0] == ")":
                        d += 1
                    elif toks[k][0] == "(":
                        d -= 1
                        if d == 0:
                            break
                    k -= 1
                name, nline = toks[k - 1] if k > start else ("", 0)
                if nline and IDENT.match(name):
                    cur = {"name": name, "line": nline, "brace": line,
                           "static": any(x == "static" for x, _ in toks[start:k - 1]),
                           "decl": [x for x, _ in toks[start:i]], "calls": set(), "idents": set(),
                           "passed": set(), "bare": set(), "callstack": [], "fieldstores": set(),
                           "stmt": i + 1,
                           "fnptrs": {toks[j + 2][0] for j in range(start, i - 3)
                                      if toks[j][0] == "(" and toks[j + 1][0] == "*"
                                      and toks[j + 3][0] == ")"}}
                    found.append(cur)
            depth += 1
        elif t == "}":
            depth -= 1
            if depth == 0:
                start = i + 1
                if cur is not None:
                    cur["end"] = line
                cur = None
        elif t == ";" and depth == 0:
            start = i + 1
        elif cur is not None and depth > 0 and IDENT.match(t) and i + 1 < len(toks) and toks[i + 1][0] == "(":
            cur["calls"].add(t)
        if cur is not None and depth > 0 and t in (";", "{", "}"):
            cur["stmt"] = i + 1
        elif cur is not None and depth > 0 and t == "=" and toks[i - 1][0] not in ("=", "!", "<", ">") and \
                i + 1 < len(toks) and toks[i + 1][0] != "=" and \
                any(x in ("->", ".") for x, _ in toks[cur["stmt"]:i]):
            # a store to a member: what the right side names may be kept in the struct
            # (`ptr->name = table[i]`), past its bank's being mapped
            k = i + 1
            while k < len(toks) and toks[k][0] not in (";", "{", "}"):
                if IDENT.match(toks[k][0]) and toks[k - 1][0] != "sizeof" and \
                        not (toks[k - 1][0] == "(" and toks[k - 2][0] == "sizeof"):
                    # (name, an element of it rather than the name itself)
                    cur["fieldstores"].add((toks[k][0], k + 1 < len(toks) and toks[k + 1][0] == "["))
                k += 1
        if cur is not None and depth > 0 and IDENT.match(t):
            cur["idents"].add(t)
            # an object passed on in a call: not an element read (t[i]), or an element's
            # address (&t[i]); not a size (sizeof t, SIZE(t)) or a member (.t, ->t)
            nxt, prv = toks[i + 1][0] if i + 1 < len(toks) else "", toks[i - 1][0]
            if nxt != "(" and (nxt != "[" or prv == "&") and prv not in ("sizeof", ".", "->") and \
                    not (prv == "(" and toks[i - 2][0] in ("SIZE", "sizeof")):
                cur["bare"].add(t)                # its address taken, kept or passed on
                if cur["callstack"] and cur["callstack"][-1]:
                    cur["passed"].add((cur["callstack"][-1], t))
        if cur is not None and depth > 0 and t == "(":
            p = toks[i - 1][0]
            callee = p if IDENT.match(p) and p not in C_WORDS and \
                p not in ("if", "while", "for", "switch", "return", "sizeof", "SIZE") else None
            # a parenthesised part of a call's arguments belongs to that call
            cur["callstack"].append(callee or (cur["callstack"][-1] if cur["callstack"] else None))
        elif cur is not None and depth > 0 and t == ")" and cur["callstack"]:
            cur["callstack"].pop()
        if cur is not None and depth > 0 and t == "(" and i + 3 < len(toks) and toks[i + 1][0] == "*" \
                and IDENT.match(toks[i + 2][0]) and toks[i + 3][0] == ")":
            cur["fnptrs"].add(toks[i + 2][0])     # a local function pointer, `(*name)`
    return found


def data_definitions(toks):
    """The file's own file-scope object definitions with an initialiser: name, the line of
    the name, the line of the closing `;`, and the identifiers the initialiser uses."""
    found, depth, start, top_eq = [], 0, 0, False
    for i, (t, line) in enumerate(toks):
        if t in "{([":
            depth += 1
        elif t in "})]":
            depth -= 1
            if depth == 0 and t == "}" and not top_eq:
                start = i + 1                # a function body or a struct, union or enum body
        elif t == "=" and depth == 0:
            top_eq = True
        elif t == ";" and depth == 0:
            stmt = toks[start:i]
            start, had_eq, top_eq = i + 1, top_eq, False
            words = [x for x, _ in stmt]
            if not had_eq or "typedef" in words or "extern" in words:
                continue
            eq = words.index("=")
            k = eq - 1
            while k > 0 and words[k] == "]":           # back over `[N]` dimensions
                while k > 0 and words[k] != "[":
                    k -= 1
                k -= 1
            if k < 0 or not IDENT.match(words[k]) or not stmt[k][1] or "(" in words[:eq]:
                continue
            found.append({"name": words[k], "line": stmt[k][1], "end": line,
                          "static": "static" in words[:k],    # (not after a struct body)
                          # `const char t[]`: passed on, it is a string like a literal
                          "string": words[:k].count("char") == 1 and "const" in words[:k] and
                                    "*" not in words[:k] and words[k + 1:k + 2] == ["["],
                          # elements nothing may change: `const T t[]`, `const T * const t[]`
                          "const": "const" in words[:k] and ("*" not in words[:k] or
                                                            words[k - 1] == "const"),
                          # its elements are values, not pointers: an int or char table
                          "values": "*" not in words[:k] and "struct" not in words[:k] and
                                    any(w in ("char", "int", "short", "long", "uchar", "schar",
                                              "xchar", "boolean", "unsigned") for w in words[:k]),
                          "idents": {x for x in words[eq + 1:] if IDENT.match(x)}})
    return found


def split_top(tok_list, sep=","):
    parts, depth, cur = [], 0, []
    for t in tok_list:
        if t == sep and depth == 0:
            parts.append(cur)
            cur = []
            continue
        depth += t in "(["
        depth -= t in ")]"
        cur.append(t)
    return parts + [cur]


def signature(d):
    """(return type, [(param text, param name, is char pointer)], variadic) from the
    declarator tokens, or None when it is not `ret name(params)`."""
    decl = [t for t in d["decl"] if t not in ("static", "extern", "register")]
    try:
        k = decl.index(d["name"])
    except ValueError:
        return None
    if k == 0 or decl[k - 1] == "(" or k + 1 >= len(decl) or decl[k + 1] != "(" or decl[-1] != ")":
        return None
    ret = " ".join(decl[:k])
    inner = decl[k + 2:-1]
    params, variadic = [], False
    if inner and inner != ["void"]:
        for p in split_top(inner):
            if p == ["..."]:
                variadic = True
                continue
            if "(" in p:
                m = [i for i in range(len(p) - 2) if p[i] == "(" and p[i + 1] == "*" and IDENT.match(p[i + 2])]
                if not m:
                    return None
                pname = p[m[0] + 2]
            else:
                head = p[:p.index("[")] if "[" in p else p
                if len(head) < 2 or not IDENT.match(head[-1]) or head[-1] in C_WORDS or \
                        head[-2] in ("struct", "union", "enum"):
                    return None              # an unnamed parameter, or a bare typedef
                pname = head[-1]
            # the trampoline names its parameters itself: a macro defined later in the file
            # (files.c's tmp_ramdisk) can be in force where the trampolines are appended
            own = "nh_a%d" % len(params)
            text = " ".join(own if t == pname else t for t in p)
            typ = " ".join(t for t in p if t != pname)
            params.append((text, own, bool(CHAR_PTR.match(typ)) and "[" not in p))
    return ret, params, variadic


KEEP_EXTERN = re.compile(r"(?m)^E\s+(?:NEARDATA\s+)?(?:const\s+)?char\s*\*\s*([A-Za-z_]\w*)\s*;")
KEEP_STATIC = re.compile(r"(?m)^(?:static|STATIC_VAR|STATIC_OVL)\s+(?:NEARDATA\s+)?(?:const\s+)?char\s*\*\s*"
                         r"([A-Za-z_]\w*)\s*(?:=[^;(]*)?;")
LITERAL = re.compile(r'"(?:[^"\\\n]|\\.)*"')
KEEP_SIZE = 128
# a file-scope variable that nhbank.h defines (for nhnear.h)
GLUE_VAR = re.compile(r"(?m)^(?:static\s+)?(?:volatile\s+)?(?:unsigned\s+)?(?:char|int|short|long|unsigned)\s+"
                      r"(\w+)(?:\[[^\]]*\])*(?:\s*,\s*(\w+))?(?:\s*,\s*(\w+))?(?:\s*,\s*(\w+))?\s*;")


def keep(raw, li, last, f, keep_extern, keep_static, banked, bufs, report, keep_sizes, kept_extern):
    """Wrap the assignments to keeper variables that start on raw[li] in NH_KEEP; the
    statement may end on a later line of the function (up to line `last`).  A plan's
    "keep" sizes a variable's buffer (keep_sizes, by the buffer's name less "nh_keep_");
    0 leaves its assignments alone."""
    line, n = raw[li], li + 1
    code = LITERAL.sub(lambda m: "\0" * len(m.group(0)), line)   # find `=` outside strings
    out, pos, tail = [], 0, None
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*=(?!=)", code):
        name = m.group(1)
        if name not in keep_extern and name not in keep_static:
            continue
        if m.start() > 0 and code[:m.start()].rstrip()[-1:] in (".", ">"):
            continue                                       # a struct member of that name
        end = code.find(";", m.end())
        if end >= 0:
            rhs, lj = code[m.end():end], li
        else:                                              # the statement goes on
            rest = [code[m.end():]]
            for lj in range(li + 1, min(last, li + 6)):
                c2 = LITERAL.sub(lambda x: "\0" * len(x.group(0)), raw[lj])
                if ";" in c2:
                    rest.append(c2[:c2.index(";")])
                    break
                rest.append(c2)
            else:
                report["keep_unhandled"].append("%s:%d" % (f, n))
                continue
            rhs = " ".join(rest)
        if "=" in rhs.replace("==", "").replace("!=", "").replace("<=", "").replace(">=", "") \
                or top_comma(rhs) or tail is not None:
            report["keep_unhandled"].append("%s:%d" % (f, n))
            continue
        buf = "nh_keep_" + name if name in keep_extern else "nh_keep_%s_%s" % (f[:-2], name)
        size = keep_sizes.get(buf[8:], KEEP_SIZE)
        report["keep_planned"].add(buf[8:])
        if not size:
            report["keep_exempt"] += 1
            continue
        if name in keep_extern:
            kept_extern[name] = size
        elif (buf, size) not in bufs:
            bufs.append((buf, size))
        if lj == li:
            out.append(line[pos:m.end()] + " NH_KEEP(%s, %s)" % (buf, line[m.end():end].strip()))
            pos = end
        else:
            out.append(line[pos:m.end()] + " NH_KEEP(%s," % buf + line[m.end():])
            pos = len(line)
            tail = lj
        report["kept"] += 1
    if banked and tail is None:
        # a literal stored in a struct field (options.c: obj_descr[...].oc_name = "fruit")
        for m in re.finditer(r"(?:->|\.)\s*[A-Za-z_]\w*\s*=\s*(\"(?:[^\"\\\n]|\\.)*\")\s*;", line):
            if m.start(1) < pos:
                continue
            buf = "nh_keep_%s_%d" % (f[:-2], n)
            bufs.append((buf, len(m.group(1))))
            out.append(line[pos:m.start(1)] + "NH_KEEP(%s, %s)" % (buf, m.group(1)))
            pos = m.end(1)
            report["kept_fields"].append("%s:%d" % (f, n))
    if out:
        raw[li] = "".join(out) + line[pos:]
    if tail is not None:
        c2 = LITERAL.sub(lambda x: "\0" * len(x.group(0)), raw[tail])
        k = c2.index(";")
        raw[tail] = raw[tail][:k] + ")" + raw[tail][k:]


def top_comma(text):
    depth = 0
    for c in text:
        depth += c in "(["
        depth -= c in ")]"
        if c == "," and depth == 0:
            return True
    return False


def insertion_line(raw, line):
    """Index (0-based) of the first line of the declaration whose name is on `line`
    (1-based): back over the return type, up to a blank line, a comment, a directive or
    the end of the previous declaration.  A conditional around the declarator alone
    (`void` / `#ifdef X` / `f(a, b)` / `#else` / `f(a)` / `#endif`, mklev.c's topologize)
    is part of the declaration: the return type above it is found too."""
    def code_of(k):
        code = raw[k]
        if "/*" in code:
            code = code[:code.index("/*")]   # `boolean  /* ... */` is a return type
        return code.strip()

    def decl_part(code):
        # a macro invocation alone on its line (decl.c's `NH_FARW(2)`) is a definition of
        # its own, not the return type of the next
        return code and not code.startswith(("*", "#", "//")) and not code.endswith((";", "}", "{", "*/")) \
            and not re.match(r"[A-Z][A-Z0-9_]*\s*\([^()]*\)$", code)

    i = line - 1
    while i > 0:
        code = code_of(i - 1)
        m = re.match(r"#\s*(\w+)", code)
        if m and m.group(1) in ("else", "elif"):
            depth, k = 0, i - 2              # to the #if this branch belongs to
            while k >= 0:
                d = re.match(r"#\s*(\w+)", code_of(k))
                if d and d.group(1) == "endif":
                    depth += 1
                elif d and d.group(1) in ("if", "ifdef", "ifndef"):
                    if depth == 0:
                        break
                    depth -= 1
                k -= 1
            if k <= 0 or not decl_part(code_of(k - 1)):
                break
            i = k                            # the return type is above the #if
            continue
        if m and m.group(1) in ("if", "ifdef", "ifndef") and i >= 2 and decl_part(code_of(i - 2)):
            i -= 1                           # the declarator is in the #if's first branch
            continue
        if not decl_part(code):
            break                            # blank, comment only, directive, previous item
        i -= 1
    return i


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--dir", required=True, help="directory holding the files; rewritten in place")
    ap.add_argument("--inc", action="append", default=[], help="include directory for gcc -E")
    ap.add_argument("--cpp", action="append", default=[], help="extra gcc -E flag (repeatable)")
    ap.add_argument("--define-in", default="decl.c", help="file that defines nh_bank and nh_stash()")
    ap.add_argument("--report", help="write what was done as JSON here")
    ap.add_argument("--linker-stubs", action="store_true",
                    help="the linker switches banks: trampolines only for string-handling functions")
    ap.add_argument("--target", choices=("c64", "c128"), default="c64",
                    help="c128 (T2.13): the bank call routine for a C128 in its own mode (MMU, a Magic Desk "
                         "128 cartridge and the REU), the C128's resident regions, and an overlay per "
                         "bank so that Oscar64 writes each bank as a file (tools/bank/c128_images.py)")
    ap.add_argument("--io-out", action="store_true",
                    help="with --target c128: the I/O out by default (the bank call routine switches it "
                         "in only for the bank register and the REU), one code region $C000-$FBFF")
    ap.add_argument("--far-chars", action="store_true",
                    help="far characters (ADR-0010, NH_FAR_CHARS): with --target c128, the regions above "
                         "the bank window hold code only")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()

    planj = json.load(open(a.plan))
    plan = planj["banks"]
    # functions to keep out of line (a plan's "noinline": the static helpers Oscar64 would
    # inline into a function that then no longer fits a bank; tools/bank/planfix.py)
    noinline = set(planj.get("noinline", []))
    # banks too full for their own glue (read.c's seffects with its literals): their calls go
    # through the resident stubs (section flag 4, the far-spaces fork) and their string calls
    # through the resident trampolines, as before the glue moved into the banks
    resident_glue = set(planj.get("resident_glue", []))
    # functions taking a va_list that may go into a bank all the same (a plan's
    # "va_list_banked", reviewed by hand): theirs holds no string that may be a literal of the
    # caller's bank, only pointers to near data (sys/c64/c64scanf.c's sc_scan)
    va_list_banked = set(planj.get("va_list_banked", []))
    # the keepers' buffers (a plan's "keep": {"vision_cs_left": [0, "why"], ...}): the size
    # of a buffer, by its name less "nh_keep_", with the evidence; 0 where no value assigned
    # to the variable can be a string in a bank or in the glue's buffers (a pointer to near
    # or heap data), the longest literal assigned and its NUL where those are all it holds.
    # A buffer not named keeps KEEP_SIZE; an extern assigned nowhere gets none.
    keep_sizes = {k: (v[0] if isinstance(v, list) else v) for k, v in planj.get("keep", {}).items()}
    kept_extern = {}
    # nhnear.h goes beside c64conf.h, which includes it; empty while the sources are read
    near_h = os.path.join(a.inc[0], "nhnear.h") if a.inc else os.path.join(a.dir, "nhnear.h")
    if planj.get("far_default") is not None:
        open(near_h, "w").write("")
    # the slice (a plan's "slice": {"start": address, "functions": [...], "tables": [...]}):
    # code and read-only tables at start-$BFFF of every bank, the same bytes in each (one
    # Oscar64 region with all the banks), so that they are in view whichever bank is mapped
    # and are called and read directly, as resident code is: for the rest of this script
    # they are resident.  The banks end at start.
    slice_plan = planj.get("slice") or {}
    slice_start = int(str(slice_plan.get("start", "0xc000")), 0)
    slice_funcs = set(slice_plan.get("functions", []))
    slice_tables = set(slice_plan.get("tables", []))
    files = [os.path.basename(f) for f in a.files]
    if a.define_in not in files:
        sys.exit("%s (--define-in) must be one of the files" % a.define_in)
    # objects.c includes itself (its second pass builds the table for makedefs), so code
    # appended to it would be compiled twice: such a file is left alone, all resident
    selfinc = [f for f in files if re.search(r'(?m)^\s*#\s*include\s+"%s"' % re.escape(f),
                                             open(os.path.join(a.dir, f), encoding="latin-1").read())]
    files = [f for f in files if f not in selfinc]

    # pass 1: every file's definitions, so other files can declare a bank's functions
    info, data_info, macros = {}, {}, set()
    for f in files:
        path = os.path.join(a.dir, f)
        text = preprocess(path, a.inc, a.cpp)
        toks = tokens(text, path)
        info[f] = definitions(toks)
        data_info[f] = data_definitions(toks)
        macros |= set(re.findall(r"(?m)^#define\s+([A-Za-z_]\w*)", preprocess_dm(path, a.inc, a.cpp)))
    # Global `char *` variables: one may be given a literal of a banked function, or a
    # trampoline's temporary copy of one, and be read after that bank is unmapped or the
    # copy reused, so assignments to them keep a copy (NH_KEEP, nhbank.h)
    keep_extern = set()
    for d in a.inc:
        for h in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if h.endswith(".h"):
                keep_extern |= set(KEEP_EXTERN.findall(open(os.path.join(d, h), encoding="latin-1").read()))
    # a struct member called like a function (`p->name(...)`) would be renamed too
    members = set()
    for f in files:
        code = COMMENT_OR_STRING.sub(" ", open(os.path.join(a.dir, f), encoding="latin-1").read())
        members |= set(re.findall(r"(?:\.|->)\s*([A-Za-z_]\w*)\s*\(", code))

    report = {"banked": 0, "resident": 0, "kept_resident": {}, "trampolines": 0, "banks": set(),
              "followed_callers": 0, "files_left_alone": selfinc, "entry_checks": 0, "shadowed": [],
              "used_bare": [], "kept": 0, "kept_fields": [], "keep_unhandled": [], "noinline": [],
              "keep_globals": sorted(keep_extern), "linker_stubs": a.linker_stubs, "direct": 0,
              "cross_macros": 0, "caller_wrappers": 0, "result_wrappers": 0,
              "data_banked": 0, "data_left": {}, "slice_functions": [], "slice_tables": [],
              "keep_exempt": 0, "keep_planned": set(), "keep_static_bufs": []}
    bank_of, sig_of = {}, {}

    renamed = set()      # banked functions that are renamed and get a trampoline

    def place(f, d, b):
        key = "%s:%s" % (f, d["name"])
        s = signature(d)
        why = None
        tramp = s is not None and (not a.linker_stubs or strings(s))
        if d["name"] == "main":
            why = "main"
        elif s is None:
            why = "declarator"
        elif s[2]:
            why = "variadic"
        elif any("va_list" in p[0] for p in s[1]) and key not in va_list_banked:
            # it formats `%s` arguments, which may be literals of its caller's bank: resident,
            # it does so with that bank still mapped (vpline, vraw_printf)
            why = "va_list"
        elif tramp and d["name"] in macros:
            why = "also a macro"
        elif tramp and d["name"] in members:
            why = "also a struct member"
        if why:
            report["kept_resident"][key] = why
            return False
        bank_of[key] = int(b)
        sig_of[key] = s
        if tramp:
            renamed.add(key)
        return True

    for f in files:
        for d in info[f]:
            b = plan.get("%s:%s" % (f, d["name"]))
            if b is not None:
                place(f, d, b)
    # Functions the plan does not name have no code of their own in the measurement:
    # Oscar64 inlined them into their caller.  Resident, one would stay a separate
    # function in resident memory, because Oscar64 inlines a function called once only
    # into a caller in the same section; so each goes to its callers' bank when they
    # all share one (a static's callers are in its file), repeatedly, for chains.
    callers = {}
    for f in files:
        for d in info[f]:
            for c in d["calls"]:
                callers.setdefault(c, []).append((f, d))
    changed = True
    while changed:
        changed = False
        for f in files:
            for d in info[f]:
                key = "%s:%s" % (f, d["name"])
                if key in bank_of or key in report["kept_resident"] or key in plan:
                    continue
                cs = [(cf, cd) for cf, cd in callers.get(d["name"], []) if not d["static"] or cf == f]
                banks = {bank_of.get("%s:%s" % (cf, cd["name"])) for cf, cd in cs}
                if cs and len(banks) == 1 and None not in banks and place(f, d, banks.pop()):
                    report["followed_callers"] += 1
                    changed = True
    # Read-only tables (a plan's "bank_data": file-scope definitions that no code writes,
    # tools/bank/tables.py) go into the bank of the code that reads them, with their
    # literals, when all of it is in one bank: nothing else reads them by name, so they
    # are read with that bank mapped, as the bank's own literals are, and reach other
    # banks the same ways (copied as `char *` arguments and results, kept by NH_KEEP).
    # A table another initialiser names (shknam.c's shtypes names shkliquors) stays.
    data_bank = {}

    def fn_bank(f, c):
        """The bank of function c as file f calls it (None: resident, or not ours)."""
        if any(x["name"] == c for x in info[f]):
            return bank_of.get("%s:%s" % (f, c))
        for of in files:
            for x in info[of]:
                if x["name"] == c and not x["static"]:
                    return bank_of.get("%s:%s" % (of, c))
        return None

    for key in planj.get("bank_data", []):
        f, name = key.split(":")
        d = next((x for x in data_info.get(f, []) if x["name"] == name), None)
        if d is None:
            report["data_left"][key] = "no definition"
            continue
        scope = [f] if d["static"] else files
        users = {"%s:%s" % (uf, u["name"]) for uf in scope for u in info[uf] if name in u["idents"]}
        named = [x["name"] for uf in scope for x in data_info[uf] if name in x["idents"]]
        # a table another initialiser names (shknam.c's shtypes names each shopkeeper name
        # list) may go too when the plan's "bank_data_readers" lists every function that
        # reads it through that pointer, by reading the code: they must share its bank
        readers = planj.get("bank_data_readers", {}).get(key)
        if readers is not None:
            users |= set(readers)
            named = []
        banks = {bank_of.get(u) for u in users}
        # passed on as a pointer, a table other than a string must stay in the bank: the
        # callee has to be there too (a string is copied, as a literal is)
        away = sorted({c for uf in scope for u in info[uf] for c, n in u["passed"]
                       if n == name and not d["string"] and fn_bank(uf, c) not in banks})
        # nor may a table whose elements are not const have its address taken: what writes
        # through the pointer (u_init.c's ini_inv() counts down its tables' quantities)
        # would write to the cartridge, or to a copy of the bank thrown away
        if not d["string"] and not d["const"] and any(name in u["bare"] for uf in scope for u in info[uf]):
            report["data_left"][key] = "address taken, not const"
        elif any(n == name and (not elem or not d["values"])
                 for uf in scope for u in info[uf] for n, elem in u["fieldstores"]):
            # its element, a pointer into the bank, could be kept in a struct and read
            # with another bank mapped (NH_KEEP covers variables, not members)
            report["data_left"][key] = "stored in a member"
        elif away and len(banks) == 1:
            report["data_left"][key] = "passed to " + ", ".join(away)
        elif named:
            report["data_left"][key] = "named by " + ", ".join(named)
        elif not users:
            report["data_left"][key] = "no users"
        elif len(banks) != 1 or None in banks:
            report["data_left"][key] = "banks %s" % sorted(banks, key=lambda b: -1 if b is None else b)
        else:
            data_bank.setdefault(f, []).append((d, banks.pop()))
            report["data_banked"] += 1
    # The character space (ADR-0010, --far-chars): the `char` buffers a plan's "char_space"
    # names ("file:name" at file scope, "file:function:name" for a function's static) go to
    # its section, farchars (c64conf.h), initialisers and all.  The compiler reaches them as
    # far data by name and through any byte pointer (the fork's commit 11), so no use
    # changes; what must stay near is what platform code under farchars(off) is handed, and
    # what is stored in a name field (ADR-0010: `pl_fruit`).
    char_space = {}
    if a.far_chars:
        for key in planj.get("char_space", []):
            parts = key.split(":")
            if len(parts) not in (2, 3) or parts[0] not in info:
                sys.exit("bankgen: char_space %r: no such file" % key)
            char_space.setdefault(parts[0], []).append(parts[1:])
    report["char_space"] = []
    # extern functions by name, for calls between files within a bank
    extern_bank = {}
    for f in files:
        for d in info[f]:
            key = "%s:%s" % (f, d["name"])
            if key in renamed and not d["static"]:
                extern_bank[d["name"]] = (bank_of[key], f, d)

    def proto(d, bank, suffix="b"):
        decl = [t for t in d["decl"] if t != "register"]
        return "%s;" % " ".join(decl).replace(" %s (" % d["name"], " %s__%s%d (" % (d["name"], suffix, bank), 1) \
            if " %s (" % d["name"] in " ".join(decl) else None

    # With linker stubs a call across banks needs no trampoline to switch banks, only to
    # copy strings while the bank that holds them is mapped: a call from bank A to a
    # renamed function f of bank N goes to f__tA, in bank A, which copies f's string
    # arguments out of the window and calls f__xN (or f__bN when f returns no string)
    # through the linker's stub; f__xN, in bank N, copies a string result out of the
    # window before it returns.  The resident trampoline f is left for resident callers
    # and f's address; the linker leaves out whichever of these nothing calls.
    def key_of(f, c):
        """The plan key of the renamed function a call to `c` in file f reaches, or None."""
        if any(x["name"] == c for x in info[f]):
            k = "%s:%s" % (f, c)
            return k if k in renamed else None
        if c in extern_bank:
            k = "%s:%s" % (extern_bank[c][1], c)
            return k if k in renamed else None
        return None

    call_banks = {}
    if a.linker_stubs:
        for f in files:
            for d in info[f]:
                cb = bank_of.get("%s:%s" % (f, d["name"]))
                if cb is None or cb in resident_glue:
                    continue
                for c in d["calls"]:
                    k = key_of(f, c)
                    if k is not None and bank_of[k] != cb:
                        call_banks.setdefault(k, set()).add(cb)

    def cross_target(k):
        """(suffix, bank) of what a call from another bank to renamed k goes to."""
        ret, params, _ = sig_of[k]
        return ("t", None) if any(p[2] for p in params) else ("x", bank_of[k])

    for f in files:
        path = os.path.join(a.dir, f)
        raw = open(path, encoding="latin-1").read().split("\n")
        inserts = {}
        defs = info[f]
        # runs of consecutive definitions in the same bank (None: resident)
        runs, cur = [], None
        for d in defs:
            b = bank_of.get("%s:%s" % (f, d["name"]))
            if cur is None or cur["bank"] != b:
                cur = {"bank": b, "defs": []}
                runs.append(cur)
            cur["defs"].append(d)
        defined_macros, declared = set(), set()
        first = True
        # each banked definition in pragmas of its own, so that what lies between
        # definitions is compiled for the resident code section (see the docstring)
        begins, ends = {}, {}
        run_starts = {id(run["defs"][0]) for run in runs}
        for d in defs:
            b = bank_of.get("%s:%s" % (f, d["name"]))
            if b is None:
                continue
            if id(d) not in run_starts:
                begins.setdefault(insertion_line(raw, d["line"]), []).append("#pragma code(nhbank_%d)" % b)
            if d.get("end"):
                ends.setdefault(d["end"], []).append("#pragma code(code)")
        for d, b in data_bank.get(f, []):
            begins.setdefault(insertion_line(raw, d["line"]), []).extend(
                ["#pragma code(nhbank_%d)" % b, "#pragma data(nhbank_%d)" % b])
            ends.setdefault(d["end"], []).extend(["#pragma code(code)", "#pragma data(data)"])
        for d in defs:
            key = "%s:%s" % (f, d["name"])
            if key in slice_funcs:
                if key in bank_of:
                    sys.exit("%s: in a bank and in the slice" % key)
                begins.setdefault(insertion_line(raw, d["line"]), []).append("#pragma code(nhslice)")
                ends.setdefault(d["end"], []).append("#pragma code(code)")
                report["slice_functions"].append(key)
        for d in data_info.get(f, []):
            key = "%s:%s" % (f, d["name"])
            if key in slice_tables:
                if any(x is d for x, _ in data_bank.get(f, [])):
                    sys.exit("%s: in a bank and in the slice" % key)
                begins.setdefault(insertion_line(raw, d["line"]), []).extend(
                    ["#pragma code(nhslice)", "#pragma data(nhslice)"])
                ends.setdefault(d["end"], []).extend(["#pragma code(code)", "#pragma data(data)"])
                report["slice_tables"].append(key)
        wrapped = set()
        for spec in char_space.get(f, []):
            if len(spec) == 1 and any(d["name"] == spec[0] for d, _ in data_bank.get(f, [])):
                sys.exit("%s:%s: in a bank and in the character space" % (f, spec[0]))
            start, end = char_space_lines(raw, spec, defs, data_info.get(f, []), f)
            if start not in wrapped:          # questpgr.c defines three buffers on one line
                wrapped.add(start)
                begins.setdefault(start, []).extend(["#pragma data(farchars)", "#pragma bss(farchars)"])
                ends.setdefault(end, []).extend(["#pragma data(data)", "#pragma bss(bss)"])
            report["char_space"].append(":".join([f] + spec))
        for d in defs:
            b = bank_of.get("%s:%s" % (f, d["name"]))
            if "%s:%s" % (f, d["name"]) in noinline:
                first_line = insertion_line(raw, d["line"])
                raw[first_line] = "__noinline " + raw[first_line]
                report["noinline"].append("%s:%s" % (f, d["name"]))
            if b is None or "%s:%s" % (f, d["name"]) not in renamed:
                continue
            # the definition is renamed in the text, not by the macro, which Oscar64
            # cannot have in force wherever the name appears without a `(` (r61)
            li = d["line"] - 1
            new = re.sub(r"\b%s(\s*\()" % re.escape(d["name"]), r"%s__b%d\1" % (d["name"], b), raw[li], count=1)
            if new == raw[li]:
                sys.exit("%s:%d: cannot find the definition of %s" % (f, d["line"], d["name"]))
            raw[li] = new
            if not a.linker_stubs and d["brace"] and raw[d["brace"] - 1].strip() == "{":
                inserts.setdefault(d["brace"], []).append("NH_ENTER(%d)" % b)
                report["entry_checks"] += 1
        starts = [insertion_line(raw, run["defs"][0]["line"]) for run in runs] + [len(raw)]
        keep_static = set(KEEP_STATIC.findall("\n".join(raw)))
        keep_bufs = []
        for d in defs:
            banked = "%s:%s" % (f, d["name"]) in bank_of
            for li in range(d["brace"] - 1, d.get("end", d["brace"])):
                keep(raw, li, d.get("end", d["brace"]), f, keep_extern, keep_static, banked, keep_bufs, report,
                     keep_sizes, kept_extern)
        for k, run in enumerate(runs):
            b = run["bank"]
            lines = []
            if first:
                if f == a.define_in:
                    lines.append("#define NHBANK_DEFINE")
                lines.append('#include "nhbank.h"')
                lines += ["NH_KEEPBUF(static char %s[%d];)" % (n, size) for n, size in keep_bufs]
                report["keep_static_bufs"] += [n for n, size in keep_bufs]
                first = False
            lines.append("#pragma code(%s)" % ("nhbank_%d" % b if b is not None else "code"))
            lines += ["#undef %s" % n for n in sorted(defined_macros)]
            defined_macros = set()
            if b is not None:
                names = {}
                for d in run["defs"]:
                    if "%s:%s" % (f, d["name"]) in renamed:
                        names[d["name"]] = d                  # the definitions themselves
                for d in run["defs"]:
                    for c in d["calls"]:
                        own = next((x for x in defs if x["name"] == c), None)
                        if own is not None and bank_of.get("%s:%s" % (f, c)) == b and \
                                "%s:%s" % (f, c) in renamed:
                            names[c] = own                    # this file's, same bank
                        elif c in extern_bank and extern_bank[c][0] == b and own is None:
                            names[c] = extern_bank[c][2]      # another file's, same bank
                # a parameter or local `(*name)` that shadows a function of the bank
                # would have its calls renamed too: such names get no macro in this run
                # (their calls in it go through the trampoline)
                shadowed = set().union(*(d["fnptrs"] for d in run["defs"])) - {d["name"] for d in run["defs"]}
                for n in sorted(shadowed & set(names)):
                    report["shadowed"].append("%s:%s" % (f, n))
                    del names[n]
                # Oscar64 expands a function-like macro's name even with no `(` after it
                # (r61): a name the run uses so (a struct member, a function pointer)
                # gets no macro in this run, and its calls here go through the trampoline
                code = COMMENT_OR_STRING.sub(" ", "\n".join(raw[starts[k]:starts[k + 1]]))
                bare = set(re.findall(r"\b([A-Za-z_]\w*)\b(?!\s*\()", code))
                for n in sorted(bare & set(names)):
                    report["used_bare"].append("%s:%s" % (f, n))
                    del names[n]
                for d in run["defs"]:
                    if "%s:%s" % (f, d["name"]) in renamed:
                        names.setdefault(d["name"], d)    # declared, not renamed by macro
                for n in sorted(set(names) - bare - shadowed):
                    lines.append("#define %s(...) %s__b%d(__VA_ARGS__)" % (n, n, b))
                    defined_macros.add(n)
                for n in sorted(names):
                    if n not in declared:
                        p = proto(names[n], b)
                        if p is None:
                            sys.exit("%s: no prototype for %s" % (f, n))
                        lines.append(p)
                        declared.add(n)
                if a.linker_stubs and b not in resident_glue:
                    cross = {}
                    for d in run["defs"]:
                        for c in d["calls"]:
                            ck = key_of(f, c)
                            if ck is not None and bank_of[ck] != b and c not in names:
                                cross[c] = ck
                    for n in sorted(set(cross) - bare - shadowed):
                        ck = cross[n]
                        suffix, tb = cross_target(ck)
                        tb = b if tb is None else tb
                        dn = extern_bank[n][2] if ck.split(":")[0] != f else \
                            next(x for x in info[f] if x["name"] == n)
                        lines.append("#define %s(...) %s__%s%d(__VA_ARGS__)" % (n, n, suffix, tb))
                        defined_macros.add(n)
                        if (n, suffix, tb) not in declared:
                            p = proto(dn, tb, suffix)
                            if p is None:
                                sys.exit("%s: no prototype for %s" % (f, n))
                            lines.append(p)
                            declared.add((n, suffix, tb))
                        report["cross_macros"] += 1
                report["banks"].add(b)
            inserts.setdefault(starts[k], []).extend(lines)
        tail = []
        if first:
            if f == a.define_in:
                tail.append("#define NHBANK_DEFINE")
            tail.append('#include "nhbank.h"')
        tail.append("#pragma code(code)")
        tail += ["#undef %s" % n for n in sorted(defined_macros)]
        for d in defs:
            key = "%s:%s" % (f, d["name"])
            if key not in bank_of:
                report["resident"] += 1
                continue
            report["banked"] += 1
            if key not in renamed:
                report["direct"] += 1
                continue
            report["trampolines"] += 1
            if a.linker_stubs:
                tail += split_trampoline(d, sig_of[key], bank_of[key], sorted(call_banks.get(key, ())), report)
            else:
                tail.append(trampoline(d, sig_of[key], bank_of[key]))
        out = []
        for i, l in enumerate(raw):
            before = ends.get(i, []) + [x for x in inserts.get(i, []) if not x.startswith("NH_ENTER(")] + \
                begins.get(i, [])
            if before:
                out += ["/* bankgen */"] + before
            out.append(l)
            out += [x for x in inserts.get(i + 1, []) if x.startswith("NH_ENTER(")]
        if out and out[-1] == "":
            out.pop()
        out += ["", "/* bankgen: trampolines */"] + tail + [""]
        open(path, "w", encoding="latin-1").write("\n".join(out))

    if a.target == "c128" and not a.linker_stubs:
        sys.exit("--target c128 needs --linker-stubs")
    text = header(sorted(report["banks"]), kept_extern, a.linker_stubs, resident_glue,
                  slice_start if slice_plan else None, a.target,
                  region_banks(a.inc) if a.target == "c128" else (), a.far_chars, a.io_out)
    open(os.path.join(a.dir, "nhbank.h"), "w").write(text)
    # a far default (a plan's "far_default": {"near": [...]}; c64conf.h, NH_FAR_DEFAULT): every
    # other global of NetHack's files goes to far space 5, so what must stay near is named in
    # nhnear.h: the plan's names (their address handed on as a near pointer, the compiler's
    # warning 2026; or touched every turn) and every variable of the glue (read from
    # assembler, volatile, or handed on as char *: none of it may be far)
    far_default = planj.get("far_default")
    if far_default is not None:
        glue = {n for m in GLUE_VAR.findall(text) for n in m if n}
        glue |= {"nh_keep_" + n for n in kept_extern} | set(report["keep_static_bufs"])
        near = sorted(set(far_default.get("near", [])) | glue)
        report["far_default_near"] = len(near)
        lines = ["/* nhnear.h - written by bankgen.py: what the far default leaves near */"]
        for i in range(0, len(near), 8):
            lines.append("#pragma near(%s)" % ", ".join(near[i:i + 8]))
        open(near_h, "w").write("\n".join(lines) + "\n")
    missing = (slice_funcs - set(report["slice_functions"])) | (slice_tables - set(report["slice_tables"]))
    if missing:
        sys.exit("bankgen: the slice names what no file defines: %s" % ", ".join(sorted(missing)))
    missing = set(keep_sizes) - report["keep_planned"]
    if missing:
        sys.exit("bankgen: the plan's keep names no variable assigned: %s" % ", ".join(sorted(missing)))
    report["keep_planned"] = sorted(report["keep_planned"])
    report["keep_buffers"] = dict(sorted(kept_extern.items()))
    report["banks"] = sorted(report["banks"])
    if a.report:
        json.dump(report, open(a.report, "w"), indent=1, sort_keys=True)
    if report["data_banked"] or report["data_left"]:
        print("bankgen: %d read-only tables banked, %d left resident" % (report["data_banked"],
                                                                       len(report["data_left"])))
    print("bankgen: %d functions banked in %d banks (%d with a trampoline), %d resident, "
          "%d kept resident (%s)" % (
        report["banked"], len(report["banks"]), report["trampolines"], report["resident"], len(report["kept_resident"]),
        ", ".join("%s %d" % (w, list(report["kept_resident"].values()).count(w))
                  for w in sorted(set(report["kept_resident"].values())))))


CHAR_DEF = r"^\s*(?:(?:static|NEARDATA|const|unsigned)\s+)*(?:char|uchar)\s+(?:NEARDATA\s+)?[^;=]*\b%s\s*\["


def char_space_lines(raw, spec, defs, data_defs, f):
    """The lines of a char_space definition, as begins/ends take them: the 0-based index of
    its first line and the 1-based number of its last.  spec is [name] at file scope or
    [function, name] for a function's static, a definition of its own line or, at file
    scope, one whose initialiser data_definitions() found the end of."""
    name = spec[-1]
    bodies = [(d["brace"] - 1, d.get("end", d["brace"])) for d in defs]
    if len(spec) == 2:
        fn = next((d for d in defs if d["name"] == spec[0]), None)
        if fn is None:
            sys.exit("bankgen: char_space %s:%s: no such function" % (f, ":".join(spec)))
        span = range(fn["brace"] - 1, fn.get("end", fn["brace"]))
    else:
        span = [i for i in range(len(raw)) if not any(lo <= i < hi for lo, hi in bodies)]
    # a function's own static, not a local of the same name
    hits = [i for i in span if re.match(CHAR_DEF % re.escape(name), raw[i]) and
            (len(spec) == 1 or re.match(r"^\s*static\b", raw[i]))]
    if len(hits) != 1:
        sys.exit("bankgen: char_space %s:%s: %d definitions found" % (f, ":".join(spec), len(hits)))
    i = hits[0]
    code = raw[i].split("/*")[0].rstrip()
    if code.endswith(";"):
        return i, i + 1
    d = next((x for x in data_defs if x["name"] == name and x["line"] == i + 1), None)
    if len(spec) == 1 and d is not None:
        return i, d["end"]
    sys.exit("bankgen: char_space %s:%s: cannot find the end of its definition" % (f, ":".join(spec)))


def preprocess_dm(path, inc, cpp):
    r = subprocess.run(["gcc", "-E", "-dM"] + ["-I" + d for d in inc] + cpp + [path],
                       capture_output=True, text=True, encoding="latin-1")
    return r.stdout if r.returncode == 0 else ""


def strings(sig):
    """Whether a function takes or returns a `char *`, which its trampoline copies."""
    ret, params, _ = sig
    return bool(CHAR_PTR.match(ret)) or any(p[2] for p in params)


def split_trampoline(d, sig, bank, callers, report):
    """With linker stubs (see main): f__xN in f's bank when f returns a string, f__tA in
    each calling bank A when it takes one, and the resident f, as lines for the tail."""
    ret, params, _ = sig
    void = ret == "void"
    static = "static " if d["static"] else ""
    plist = ", ".join(p[0] for p in params) or "void"
    args = ", ".join(p[1] for p in params)
    sret = bool(CHAR_PTR.match(ret))
    target = "%s__%s%d(%s)" % (d["name"], "x" if sret else "b", bank, args)

    def copy_in(name):
        if not any(p[2] for p in params):
            body = ["\t%s%s;" % ("" if void else "return ", target)]
        else:
            # the copies go on a stack that the wrapper releases when the call returns, so
            # nested calls cannot reuse one while its call is running (getobj keeps `word`)
            body = ["\tunsigned nh_m = NH_ARGMARK();"]
            if not void:
                body.append("\t%s nh_r;" % ret)
            body += ["\t%s = NH_ARG(%s);" % (p[1], p[1]) for p in params if p[2]]
            if void:
                body += ["\t%s;" % target, "\tNH_RELEASE(nh_m);"]
            elif sret:
                body += ["\tnh_r = %s;" % target, "\treturn NH_UNWIND(nh_r, nh_m);"]
            else:
                body += ["\tnh_r = %s;" % target, "\tNH_RELEASE(nh_m);", "\treturn nh_r;"]
        return "__noinline %s%s %s(%s)\n{\n%s\n}" % (static, ret, name, plist, "\n".join(body))

    out = []
    if sret:
        out += ["#pragma code(nhbank_%d)" % bank,
                "__noinline %s%s %s__x%d(%s)\n{\n\t%s nh_r = %s__b%d(%s);\n\treturn NH_RES(nh_r);\n}" % (
                    static, ret, d["name"], bank, plist, ret, d["name"], bank, args)]
        report["result_wrappers"] += 1
    if any(p[2] for p in params):
        for cb in callers:
            out += ["#pragma code(nhbank_%d)" % cb, copy_in("%s__t%d" % (d["name"], cb))]
            report["caller_wrappers"] += 1
    out += ["#pragma code(code)", copy_in(d["name"])]
    return out


def trampoline(d, sig, bank):
    ret, params, _ = sig
    void = ret == "void"
    head = "%s%s %s(%s)" % ("static " if d["static"] else "", ret, d["name"],
                            ", ".join(p[0] for p in params) or "void")
    body = ["\tunsigned char nh_ob = NH_SAVE();"]
    if not void:
        body.append("\t%s nh_r;" % ret)
    body += ["\t%s = NH_STASH(%s);" % (p[1], p[1]) for p in params if p[2]]
    body.append("\tNH_BANK(%d);" % bank)
    call = "%s__b%d(%s)" % (d["name"], bank, ", ".join(p[1] for p in params))
    body.append("\t%s%s;" % ("" if void else "nh_r = ", call))
    if not void and CHAR_PTR.match(ret):
        # one call copies the string out of the window and maps the caller's bank again,
        # so its result is already in place: a bank switch that is itself a call would
        # make every trampoline keep the pointer across it (about 26 bytes each)
        body.append("\treturn NH_UNSTASH(nh_r, nh_ob);")
        return "__noinline %s\n{\n%s\n}" % (head, "\n".join(body))
    body.append("\tNH_BANK(nh_ob);")
    if not void:
        body.append("\treturn nh_r;")
    return "__noinline %s\n{\n%s\n}" % (head, "\n".join(body))


BANKCALL = r"""
/* The linker sends a call into a bank from outside it, and every use of a banked
 * function's address, through a stub, `jsr nh_bankcall; .byte bank; .word function`
 * (Oscar64's Linker::InsertBankCalls; a call from another bank may go to a stub in
 * the caller's bank, the far-spaces fork from 2026-11-19).  This reads the function and
 * the bank from the stub, and only then maps the bank, and jumps to the function with A, X and Y as the caller left
 * them (arguments may be in A and X); the function returns to bret, which maps the
 * caller's bank again and returns with A, X and Y as the function left them (results
 * may be in A and X, and the caller may keep values in X or Y).  The old bank and
 * bret's address wait on the hardware stack; no zero page is touched.  Not
 * re-entrant: an interrupt handler must not call banked code.
 *
 * Banks 1-63 are the EasyFlash's, executed in place; banks from 64 on live in the REU
 * (ADR-0008; tools/bank/crt_split.py puts bank b at REU offset (b - 64) * 16 KB) and run
 * in the RAM under the cartridge, $8000-$BFFF, with the cartridge and BASIC switched off.
 * nh_map fetches such a bank by DMA only when the window holds another one, on the way
 * in and on the way back (a caller in an REU bank whose window a call replaced).
 * nh_window 0 means no REU bank in the window, so it needs no initialiser (compat #76:
 * an initialised volatile that only assembler writes is folded to its first value).
 * The REU's registers are written, never read ($DF00-$DFFF, docs/HARDWARE.md). */
unsigned char nh_bc_a, nh_bc_x, nh_bc_y, nh_bc_t;
volatile unsigned char nh_window, nh_cartoff;
volatile unsigned nh_fetches;

/* maps bank A; changes only A and the flags (the bank call routine keeps Y) */
__asm nh_map
{
		sta nh_bank
		cmp #64
		bcs reu
		sta $de00
		lda nh_cartoff
		beq ef
		lda #0
		sta nh_cartoff
		lda #$87
		sta $de02
ef:		lda #$37			/* ROML too: the cartridge startup leaves $36 (tests/spikes/bankslice.c) */
		sta $01
on:		rts
reu:	cmp nh_window
		beq off
		sta nh_window
		lda #$04
		sta $de02
		lda #$36
		sta $01
		inc nh_fetches
		bne cnt
		inc nh_fetches + 1
cnt:	lda nh_window
		sec
		sbc #64
		sta nh_bc_t
		asl
		asl
		asl
		asl
		asl
		asl
		sta $df05
		lda nh_bc_t
		lsr
		lsr
		sta $df06
		lda #0
		sta $df04
		sta $df02
		sta $df07
		sta $df0a
		lda #$80
		sta $df03
		lda #$40
		sta $df08
		lda #$91
		sta $df01
off:	lda nh_cartoff
		bne on
		lda #1
		sta nh_cartoff
		lda #$04
		sta $de02
		lda #$36
		sta $01
		rts
}

__asm nh_bankcall
{
		sta nh_bc_a
		stx nh_bc_x
		sty nh_bc_y
		pla
		sta l1 + 1
		sta l2 + 1
		sta l3 + 1
		pla
		sta l1 + 2
		sta l2 + 2
		sta l3 + 2
		lda nh_bank
		pha
		lda #>bret
		pha
		lda #<bret
		pha
		ldy #2
l2:		lda $ffff, y
		sta bjmp + 1
		iny
l3:		lda $ffff, y
		sta bjmp + 2
		ldy #1
l1:		lda $ffff, y
		jsr nh_map
		lda nh_bc_a
		ldx nh_bc_x
		ldy nh_bc_y
bjmp:	jmp $ffff
bret:	nop
		sta nh_bc_a
		pla
		jsr nh_map
		lda nh_bc_a
		rts
}

/* NH_BANK for the string trampolines: an REU bank, or the cartridge back on */
__noinline void
nh_setbank(unsigned char b)
{
	__asm {
		lda b
		jsr nh_map
	}
}

#pragma runtime(bankcall, nh_bankcall)
"""


NH_MAP_C128 = r"""
/* maps bank A; changes only A and the flags (the bank call routine keeps Y).  A C128 in its
 * own mode (T2.13, tests/spikes/bankreu128.c): banks 1-63 are a Magic Desk 128 cartridge's,
 * executed in place with the MMU at $3A (external function ROM at $8000-$BFFF, I/O in);
 * banks from 64 on live in the REU, as on the C64, and run in the RAM there with the MMU at
 * $3E.  The I/O stays in throughout.  nh_cartoff: 1 while the MMU is at $3E. */
__asm nh_map
{
		sta nh_bank
		cmp #64
		bcs reu
		sta $de00
		lda #$3a
		sta $ff00
		lda #0
		sta nh_cartoff
		rts
reu:	lda #$3e
		sta $ff00
		lda #1
		sta nh_cartoff
		lda nh_bank
		cmp nh_window
		beq on
		sta nh_window
		inc nh_fetches
		bne cnt
		inc nh_fetches + 1
cnt:	lda nh_window
		sec
		sbc #64
		sta nh_bc_t
		asl
		asl
		asl
		asl
		asl
		asl
		sta $df05
		lda nh_bc_t
		lsr
		lsr
		sta $df06
		lda #0
		sta $df04
		sta $df02
		sta $df07
		sta $df0a
		lda #$80
		sta $df03
		lda #$40
		sta $df08
		lda #$91
		sta $df01
on:		rts
}
"""

NH_MAP_C128_IO_OUT = r"""
/* maps bank A; changes only A and the flags (the bank call routine keeps Y).  A C128 in its
 * own mode with the I/O out by default (bankgen.py --io-out; tests/spikes/bankreu128.c
 * -dIO_OUT), so that $D000-$DFFF is RAM: the I/O in only to write the Magic Desk 128's bank
 * register or start the REU's DMA, then the MMU at $3B (the cartridge at $8000-$BFFF, banks
 * 1-63) or $3F (all RAM: an REU bank, 64 on, in the RAM there).  This code is in section
 * nhio, which lies below $8000: code at $D000-$DFFF can't switch the I/O in under itself.
 * nh_cartoff: 1 while the MMU is at $3F. */
__asm nh_map
{
		sta nh_bank
		lda #$3e
		sta $ff00
		lda nh_bank
		cmp #64
		bcs reu
		sta $de00
		lda #$3b
		sta $ff00
		lda #0
		sta nh_cartoff
		rts
reu:	lda #1
		sta nh_cartoff
		lda nh_bank
		cmp nh_window
		beq on
		sta nh_window
		inc nh_fetches
		bne cnt
		inc nh_fetches + 1
cnt:	lda nh_window
		sec
		sbc #64
		sta nh_bc_t
		asl
		asl
		asl
		asl
		asl
		asl
		sta $df05
		lda nh_bc_t
		lsr
		lsr
		sta $df06
		lda #0
		sta $df04
		sta $df02
		sta $df07
		sta $df0a
		lda #$80
		sta $df03
		lda #$40
		sta $df08
		lda #$91
		sta $df01
on:		lda #$3f
		sta $ff00
		rts
}
"""

# the C128's resident RAM in bank 0 with the I/O in (T2.13): below the bank window from the
# end of BASIC's and the KERNAL's workspace, and above it to the common RAM at $FC00, less the
# I/O at $D000.  Code and initialised data only above the window: the start code clears the
# bss as one range, BSSStart to BSSEnd.  The regions above the window come first: the linker fills a section's
# regions in the order they are declared, so with `main` first the code filled it and left
# $C000 up empty (docs/data/wholegame-c128-fc-2026-11-22.txt)
C128_REGIONS = """#pragma region( nh_c128_c000, 0xc000, 0xd000, , , { code, data } )
#pragma region( nh_c128_e000, 0xe000, 0xfc00, , , { code, data } )
#pragma region( main, 0x1d00, 0x8000, , , { code, data, bss, heap, stack } )"""
# with far characters (ADR-0010, c64conf.h's NH_FAR_CHARS) a byte pointer from $C100 up is
# the character space's, so no near data may lie there: code only (the code section's only
# data, its literals, then goes to the character space; the multiplication tables are read
# by absolute index)
C128_REGIONS_FAR_CHARS = C128_REGIONS.replace("{ code, data } )", "{ code } )")
# --io-out (T2.13): the I/O out by default, so one region of code runs from $C000 to the common
# RAM at $FC00; section nhio (the bank call routine, the far runtime) is kept below $8000,
# since code at $D000-$DFFF can't switch the I/O in under itself
C128_REGIONS_IO_OUT = """#pragma section( nhio, 0 )
#pragma region( nh_c128_hi, 0xc000, 0xfc00, , , { code, data } )
#pragma region( main, 0x1d00, 0x8000, , , { nhio, code, data, bss, heap, stack } )"""
# the C128's low RAM that neither BASIC nor the KERNAL's disk routines need once the program
# runs ($0B00-$1AFF: the cassette buffer, RS-232 buffers, sprites, function keys, BASIC's
# variables), as bss: the far runtime's cache frames, which need no clearing
C128_LOW = """#pragma section( nh_c128_low, 0, , , bss )
#pragma region( nh_c128_lowr, 0x0b00, 0x1b00, , , { nh_c128_low } )
#pragma section( nh_c128_glue, 0, , , bss )
#pragma region( nh_c128_gluer, 0x0400, 0x0b00, , , { nh_c128_glue } )
#pragma region( nh_c128_gluer2, 0x1b00, 0x1c00, , , { nh_c128_glue } )"""
# and below the frames the 40-column screen and the KERNAL's and BASIC's work areas, and the
# page above them, which nothing uses with the KERNAL out and the screen on the 80-column
# chip (sys128.c): the bank glue's buffers, which need no clearing either (header()): its
# scratch space, and the copies NH_KEEP makes (each written before the pointer that names it)
C128_GLUE_BUFS = ("static char nh_stash_buf[4][NH_STASH_LEN];", "static char nh_args[1024];")
C128_GLUE_KEEPS = ("delayed_killer", "killer", "nomovemsg", "occtxt")


def region_banks(incs):
    """the banks that the headers' own regions name (the far spaces' sections), so that a
    C128 build writes them as files too"""
    out = set()
    for d in incs:
        for root, _, names in os.walk(d):
            for n in names:
                if n.endswith(".h"):
                    for m in re.finditer(r"#pragma\s+region\s*\(\s*\w+\s*,\s*\w+\s*,\s*\w+\s*,\s*,\s*(\d+)\s*,",
                                         open(os.path.join(root, n), encoding="latin-1").read()):
                        out.add(int(m.group(1)))
    return sorted(out)


def header(banks, keep_extern={}, linker_stubs=False, resident_glue=(), slice_start=None, target="c64",
           more_banks=(), far_chars=False, io_out=False):
    """keep_extern: the extern keepers assigned somewhere, with their buffers' sizes"""
    bufs_decl = "\n".join("extern char nh_keep_%s[%d];" % (n, keep_extern[n]) for n in sorted(keep_extern))
    bufs_def = "\n".join("char nh_keep_%s[%d];" % (n, keep_extern[n]) for n in sorted(keep_extern))
    if linker_stubs:
        bc = BANKCALL
        if target == "c128":
            i, j = bc.index("/* maps bank A;"), bc.index("__asm nh_bankcall")
            bc = bc[:i] + (NH_MAP_C128_IO_OUT if io_out else NH_MAP_C128).strip() + "\n\n" + bc[j:]
            if io_out:
                bc = "#pragma code( nhio )\n" + bc + "\n#pragma code( code )\n"
        bufs_def += "\n" + bc          # substituted, so no % escaping
    setbank = ("/* through the bank call routine: an REU bank needs fetching (ADR-0008) */\n"
               "extern void nh_setbank(unsigned char b);\n#define NH_BANK(n) nh_setbank(n)"
               if linker_stubs else "#define NH_BANK(n) (nh_bank = (n), eflash.bank = (n))")
    end = slice_start or 0xc000
    regions = "\n".join("#pragma section( nhbank_%d, %d )\n#pragma region( nhbank_%d_r, 0x8000, 0x%04x, , %d, "
                        "{ nhbank_%d } )" % (b, 4 if b in resident_glue else 0, b, end, b, b) for b in banks)
    if target == "c128":
        # each bank a file of its own (Linker::WritePrgFile), nethack_ovN.prg beside nethack.prg
        regions += "\n/* C128: the resident regions, and each bank written as a file */\n" + \
            ((C128_REGIONS_IO_OUT.replace("{ code, data } )", "{ code } )") if far_chars else C128_REGIONS_IO_OUT)
             if io_out else (C128_REGIONS_FAR_CHARS if far_chars else C128_REGIONS)) + "\n" + C128_LOW + "\n" + \
            "\n".join("#pragma overlay( nethack_ov%d, %d )" % (b, b) for b in sorted(set(banks) | set(more_banks)))
    if slice_start:
        # the slice: one region in every bank, so the linker writes its bytes into each;
        # Linker::SectionBank() takes a section of several banks for resident code, so
        # calls into it stay direct and calls out of it go through the resident stubs
        regions += ("\n/* the slice: the same code and tables at $%04x-$BFFF of every bank */\n"
                    "#pragma section( nhslice, 0 )\n#pragma region( nhslice_r, 0x%04x, 0xc000, , { %s }, "
                    "{ nhslice } )" % (slice_start, slice_start, ", ".join(str(b) for b in banks)))
    text = """/* nhbank.h - written by tools/bank/bankgen.py: the banks, the bank switch and the
 * string copy that its trampolines use (docs/BANKING-SPIKE.md). */
#ifndef NHBANK_H
#define NHBANK_H

#ifdef __OSCAR64C__
#include <c64/easyflash.h>
%s
/* the cartridge's bank register is write-only, so the bank selected is kept here;
 * volatile, since the bank call routine (assembler) changes it */
extern volatile unsigned char nh_bank;
extern char *nh_stash(const char *s);
/* a string result: copied out if it is in the window, then bank b mapped again */
extern __noinline char *nh_unstash(const char *s, unsigned char b);
#define NH_UNSTASH(p, b) nh_unstash((p), (b))
#define NH_SAVE() nh_bank
%s
/* through a volatile: Oscar64 folds the comparison of a known object's address with a
 * constant, as if every object were below $8000, so a literal passed to a wrapper would
 * not be copied (compat #79, tests/oscar64-repros/r76) */
extern volatile unsigned nh_addr;
#define NH_IN_WINDOW(p) (nh_addr = (unsigned)(p), nh_addr >= 0x8000u && nh_addr < 0xc000u)
#define NH_STASH(p) (NH_IN_WINDOW(p) ? nh_stash(p) : (p))
/* a string argument: copied onto a stack that the wrapper releases after the call (a
 * string result that points into what it releases goes to nh_stash's buffers) */
extern unsigned nh_args_top;
extern char *nh_stash_arg(const char *s);
extern char *nh_unwind(char *r, unsigned m);
/* calls, not macros: each wrapper then spends about 12 bytes on a copy, not 30 */
extern __noinline char *nh_arg(const char *p);
extern __noinline char *nh_res(const char *p);
#define NH_ARG(p) nh_arg(p)
#define NH_RES(p) nh_res(p)
#define NH_ARGMARK() nh_args_top
#define NH_RELEASE(m) (nh_args_top = (m))
#define NH_UNWIND(r, m) nh_unwind((char *)(r), (m))
#define NH_ENTER(n)
/* a pointer about to be kept in a variable: a literal in the bank window, or a
 * trampoline's temporary copy, is copied into the variable's own buffer */
extern char *nh_keep(char *buf, unsigned size, const char *p);
#define NH_KEEP(buf, p) nh_keep((buf), sizeof(buf), (p))
#define NH_KEEPBUF(decl) decl
#if defined(NH_FAR_MNAMES) || defined(NH_FAR_ONAMES) || defined(NH_FAR_RNAMES)
/* far names (permonst.h, objclass.h): NH_MNAME() and NH_ONAME() copy one into a ring of
 * near buffers, long enough for the longest ("cheap plastic imitation of the Amulet of
 * Yendor"); nh_keep() copies out of the ring too */
#define NH_NAME_SLOTS 8
#define NH_NAME_LEN NH_NAMEBUF		/* permonst.h */
extern char nh_name_ring[NH_NAME_SLOTS][NH_NAME_LEN];
#endif
%s

#ifdef NHBANK_DEFINE
volatile unsigned char nh_bank;
/* a string from a bank that is about to be unmapped: copied into one of a few
 * resident buffers, which callers reuse in turn.  Only strings in the bank window are
 * copied, and the largest literal a bank holds is 102 B (engrave.c's; far31's map), so a
 * slot of NH_STASH_LEN holds any whole; build_c64.py --check-only checks it at each link */
#define NH_STASH_LEN 128
static char nh_stash_buf[4][NH_STASH_LEN];
static unsigned char nh_stash_next;
volatile unsigned nh_addr;
static char nh_args[1024];
unsigned nh_args_top;

char *
nh_stash(const char *s)
{
	char *d = nh_stash_buf[nh_stash_next++ & 3];
	int i;

	for (i = 0; i < NH_STASH_LEN - 1 && s[i]; i++)
		d[i] = s[i];
	d[i] = 0;
	return d;
}

char *
nh_stash_arg(const char *s)
{
	char *d;
	unsigned n = 0;

	while (n < NH_STASH_LEN - 1 && s[n])
		n++;
	if (nh_args_top + n + 1 > sizeof(nh_args))
		return nh_stash(s);		/* full: one of the four, as before */
	d = nh_args + nh_args_top;
	nh_args_top += n + 1;
	d[n] = 0;
	while (n--)
		d[n] = s[n];
	return d;
}

__noinline char *
nh_arg(const char *p)
{
	return NH_IN_WINDOW(p) ? nh_stash_arg(p) : (char *)p;
}

__noinline char *
nh_res(const char *p)
{
	return NH_IN_WINDOW(p) ? nh_stash(p) : (char *)p;
}

char *
nh_unwind(char *r, unsigned m)
{
	if (r >= nh_args + m && r < nh_args + nh_args_top)
		r = nh_stash(r);
	nh_args_top = m;
	return r;
}

__noinline char *
nh_unstash(const char *s, unsigned char b)
{
	char *p = NH_STASH(s);
	NH_BANK(b);
	return p;
}

#if defined(NH_FAR_MNAMES) || defined(NH_FAR_ONAMES) || defined(NH_FAR_RNAMES)
char nh_name_ring[NH_NAME_SLOTS][NH_NAME_LEN];
static unsigned char nh_name_next;

/* the far runtime: n bytes at address p of far space s into d */
extern void nh_farcopy(char *d, const char *p, unsigned n, unsigned char s);

/* A name is at $E000-$FFFF of its space (permonst.h); anything below is null or a near
 * string (options.c points the fruit's name at pl_fruit), returned as it is. */
static const char *
nh_name_into(const char *p, unsigned char s, char *d)
{
	unsigned n;

	nh_addr = (unsigned)p;
	if (nh_addr < 0xe000u)
		return p;
	n = 0u - nh_addr;			/* bytes up to the end of the space */
	if (n > NH_NAME_LEN - 1)
		n = NH_NAME_LEN - 1;
	nh_farcopy(d, p, n, s);
	d[n] = 0;
	return d;
}

static const char *
nh_name(const char *p, unsigned char s)
{
	nh_addr = (unsigned)p;
	if (nh_addr < 0xe000u)
		return p;
	return nh_name_into(p, s, nh_name_ring[nh_name_next++ & (NH_NAME_SLOTS - 1)]);
}
#endif
#ifdef NH_FAR_MNAMES
const char *
nh_mname(const char *p)
{
	return nh_name(p, 1);
}

/* into the caller's buffer of NH_NAMEBUF bytes (permonst.h), not the ring */
const char *
nh_mname_b(const char *p, char *d)
{
	return nh_name_into(p, 1, d);
}
#endif
#ifdef NH_FAR_ONAMES
const char *
nh_oname(const char *p)
{
	return nh_name(p, 2);
}

const char *
nh_oname_b(const char *p, char *d)
{
	return nh_name_into(p, 2, d);
}
#endif
#ifdef NH_FAR_RNAMES
const char *
nh_rname(const char *p)
{
	return nh_name(p, 3);
}
#endif

char *
nh_keep(char *buf, unsigned size, const char *p)
{
	unsigned i;

	if (!p || (!NH_IN_WINDOW(p) && (p < nh_stash_buf[0] || p >= nh_stash_buf[4]) &&
#if defined(NH_FAR_MNAMES) || defined(NH_FAR_ONAMES) || defined(NH_FAR_RNAMES)
		   (p < nh_name_ring[0] || p >= nh_name_ring[NH_NAME_SLOTS]) &&
#endif
		   (p < nh_args || p >= nh_args + sizeof(nh_args))))
		return (char *)p;
	for (i = 0; i + 1 < size && p[i]; i++)
		buf[i] = p[i];
	buf[i] = 0;
	return buf;
}
%s
#endif

#else
/* The host build has no banks but keeps the same account of the selected one, and
 * each banked function checks it on entry: a call that reaches a function in another
 * bank without its trampoline, which on the C64 would run whatever that bank window
 * holds, stops the game here.  Weak definitions, because util/ links some of src/'s
 * objects without decl.o. */
#include <stdio.h>
#include <stdlib.h>
#define __noinline
__attribute__((weak)) unsigned char nh_bank;

__attribute__((weak)) int
nh_enter(int n, const char *f)
{
	if (nh_bank != n) {
		fprintf(stderr, "nhbank: %%s (bank %%d) entered with bank %%d selected\\n", f, n, nh_bank);
		abort();
	}
	return 0;
}
#define NH_SAVE() nh_bank
#define NH_BANK(n) (nh_bank = (n))
#define NH_STASH(p) (p)
#define NH_ARG(p) (p)
#define NH_RES(p) (p)
#define NH_ARGMARK() 0u
#define NH_RELEASE(m) ((void)(m))
#define NH_UNWIND(r, m) ((void)(m), (r))
#define NH_UNSTASH(p, b) (NH_BANK(b), (p))
#define NH_ENTER(n) int nh_entered = nh_enter((n), __FUNCTION__);
#define NH_KEEP(buf, p) (p)
#define NH_KEEPBUF(decl)
#endif

#endif
""" % (regions, setbank, bufs_decl, bufs_def)
    if target == "c128":
        for d in C128_GLUE_BUFS + tuple("char nh_keep_%s[%d];" % (n, keep_extern[n])
                                        for n in C128_GLUE_KEEPS if n in keep_extern):
            # the definition, at the start of its line (not the extern declaration)
            text, n = re.subn(r"(?m)^%s$" % re.escape(d),
                              lambda m: "#pragma bss( nh_c128_glue )\n%s\n#pragma bss( bss )" % m.group(0), text)
            if n != 1:
                sys.exit("bankgen: %d definitions %r in nhbank.h" % (n, d))
    return text


if __name__ == "__main__":
    main()
