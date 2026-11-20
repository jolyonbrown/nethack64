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
                           "decl": [x for x, _ in toks[start:i]], "calls": set(),
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
        if cur is not None and depth > 0 and t == "(" and i + 3 < len(toks) and toks[i + 1][0] == "*" \
                and IDENT.match(toks[i + 2][0]) and toks[i + 3][0] == ")":
            cur["fnptrs"].add(toks[i + 2][0])     # a local function pointer, `(*name)`
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


def keep(raw, li, last, f, keep_extern, keep_static, banked, bufs, report):
    """Wrap the assignments to keeper variables that start on raw[li] in NH_KEEP; the
    statement may end on a later line of the function (up to line `last`)."""
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
        if name not in keep_extern and (buf, KEEP_SIZE) not in bufs:
            bufs.append((buf, KEEP_SIZE))
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
        return code and not code.startswith(("*", "#", "//")) and not code.endswith((";", "}", "{", "*/"))

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
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()

    planj = json.load(open(a.plan))
    plan = planj["banks"]
    # functions to keep out of line (a plan's "noinline": the static helpers Oscar64 would
    # inline into a function that then no longer fits a bank; tools/bank/planfix.py)
    noinline = set(planj.get("noinline", []))
    files = [os.path.basename(f) for f in a.files]
    if a.define_in not in files:
        sys.exit("%s (--define-in) must be one of the files" % a.define_in)
    # objects.c includes itself (its second pass builds the table for makedefs), so code
    # appended to it would be compiled twice: such a file is left alone, all resident
    selfinc = [f for f in files if re.search(r'(?m)^\s*#\s*include\s+"%s"' % re.escape(f),
                                             open(os.path.join(a.dir, f), encoding="latin-1").read())]
    files = [f for f in files if f not in selfinc]

    # pass 1: every file's definitions, so other files can declare a bank's functions
    info, macros = {}, set()
    for f in files:
        path = os.path.join(a.dir, f)
        text = preprocess(path, a.inc, a.cpp)
        info[f] = definitions(tokens(text, path))
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
              "cross_macros": 0, "caller_wrappers": 0, "result_wrappers": 0}
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
        elif any("va_list" in p[0] for p in s[1]):
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
                if cb is None:
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
                keep(raw, li, d.get("end", d["brace"]), f, keep_extern, keep_static, banked, keep_bufs, report)
        for k, run in enumerate(runs):
            b = run["bank"]
            lines = []
            if first:
                if f == a.define_in:
                    lines.append("#define NHBANK_DEFINE")
                lines.append('#include "nhbank.h"')
                lines += ["NH_KEEPBUF(static char %s[%d];)" % (n, size) for n, size in keep_bufs]
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
                if a.linker_stubs:
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

    open(os.path.join(a.dir, "nhbank.h"), "w").write(header(sorted(report["banks"]), keep_extern, a.linker_stubs))
    report["banks"] = sorted(report["banks"])
    if a.report:
        json.dump(report, open(a.report, "w"), indent=1, sort_keys=True)
    print("bankgen: %d functions banked in %d banks (%d with a trampoline), %d resident, "
          "%d kept resident (%s)" % (
        report["banked"], len(report["banks"]), report["trampolines"], report["resident"], len(report["kept_resident"]),
        ", ".join("%s %d" % (w, list(report["kept_resident"].values()).count(w))
                  for w in sorted(set(report["kept_resident"].values())))))


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
                "__noinline %s%s %s__x%d(%s)\n{\n\t%s nh_r = %s__b%d(%s);\n\treturn NH_STASH(nh_r);\n}" % (
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
		beq on
		lda #0
		sta nh_cartoff
		lda #$87
		sta $de02
		lda #$37
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


def header(banks, keep_extern=(), linker_stubs=False):
    bufs_decl = "\n".join("extern char nh_keep_%s[%d];" % (n, KEEP_SIZE) for n in sorted(keep_extern))
    bufs_def = "\n".join("char nh_keep_%s[%d];" % (n, KEEP_SIZE) for n in sorted(keep_extern))
    if linker_stubs:
        bufs_def += "\n" + BANKCALL          # substituted, so no % escaping
    setbank = ("/* through the bank call routine: an REU bank needs fetching (ADR-0008) */\n"
               "extern void nh_setbank(unsigned char b);\n#define NH_BANK(n) nh_setbank(n)"
               if linker_stubs else "#define NH_BANK(n) (nh_bank = (n), eflash.bank = (n))")
    regions = "\n".join("#pragma section( nhbank_%d, 0 )\n#pragma region( nhbank_%d_r, 0x8000, 0xc000, , %d, "
                        "{ nhbank_%d } )" % (b, b, b, b) for b in banks)
    return """/* nhbank.h - written by tools/bank/bankgen.py: the banks, the bank switch and the
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
#define NH_ARG(p) (NH_IN_WINDOW(p) ? nh_stash_arg(p) : (p))
#define NH_ARGMARK() nh_args_top
#define NH_RELEASE(m) (nh_args_top = (m))
#define NH_UNWIND(r, m) nh_unwind((char *)(r), (m))
#define NH_ENTER(n)
/* a pointer about to be kept in a variable: a literal in the bank window, or a
 * trampoline's temporary copy, is copied into the variable's own buffer */
extern char *nh_keep(char *buf, unsigned size, const char *p);
#define NH_KEEP(buf, p) nh_keep((buf), sizeof(buf), (p))
#define NH_KEEPBUF(decl) decl
%s

#ifdef NHBANK_DEFINE
volatile unsigned char nh_bank;
/* a string from a bank that is about to be unmapped: copied into one of a few
 * resident buffers, which callers reuse in turn */
static char nh_stash_buf[4][256];
static unsigned char nh_stash_next;
volatile unsigned nh_addr;
static char nh_args[1024];
unsigned nh_args_top;

char *
nh_stash(const char *s)
{
	char *d = nh_stash_buf[nh_stash_next++ & 3];
	int i;

	for (i = 0; i < 255 && s[i]; i++)
		d[i] = s[i];
	d[i] = 0;
	return d;
}

char *
nh_stash_arg(const char *s)
{
	char *d;
	unsigned n = 0;

	while (n < 255 && s[n])
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

char *
nh_keep(char *buf, unsigned size, const char *p)
{
	unsigned i;

	if (!p || (!NH_IN_WINDOW(p) && (p < nh_stash_buf[0] || p >= nh_stash_buf[4]) &&
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


if __name__ == "__main__":
    main()
