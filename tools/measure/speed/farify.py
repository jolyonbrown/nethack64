#!/usr/bin/env python3
"""farify.py - the speed harness's functions as a compiler with typed far spaces would make
them (docs/RAM-PLAN.md, T2.11): every access through a pointer to one of the named struct
types goes through a translation first, `p->f` becoming `XL_<tag>(p)->f`.

usage: tools/measure/speed/farify.py --src XDIR --inc INCDIR --out OUTDIR --type TAG...
                                     [--cflag FLAG...] [--expand] [--reuse]

XDIR holds extract.py's files (x_*.c) and INCDIR the headers they include (calibrate.py's
C64 view); OUTDIR gets x/ and inc/ rewritten, each file with far_pre.h before its own
includes (the translations) and far_post.h after them.  clang finds the accesses from the types, so
nothing is guessed from the text: a member access through `->`, a subscript and a `*` whose
pointer is `struct TAG *`.  An access spelled inside a macro is rewritten in the macro's
body (mondata.h's `(ptr)->mflags1`), once for every use.  An access that clang spells across
a macro's boundary cannot be rewritten in one place and is reported; so is anything else
left alone.  The experiment's own oracle is calibrate.py's checksum: the far build keeps its
pointers away from the real addresses, so a missed access reads the wrong bytes.

--expand first replaces the body of every function in the copies with its macro expansion
(clang -E, system headers left out, so that NULL and the like stay for the compiler's own),
so that an access made by a macro is spelled in the function and rewritten there, not in the
macro's body.  --reuse (with --expand) models a compiler that translates a pointer once a
value: a parameter or local variable of type `struct TAG *`, never address-taken, not static,
changed only by `=` and defined once (a parameter never assigned, a local set in one place)
gets a shadow holding its translation, set at that definition (`v = E` becomes `(t = (E),
v__x = t ? XL_TAG(t) : 0, v = t)`, a parameter's at entry), and every access through the
variable uses the shadow.  --reuse-all shadows the variables with several definitions too
(a pointer stepped along a list), updating the shadow at each; with the null test and the
extra copies that costs more than it saves where a value gets only one or two accesses
(t_at()'s walk), which a compiler translating at the first access would not.  Pointers
that are not variables (`mon->data->mlet`, a grid's element) are translated at each access
as before.  The translations stay valid because every page stays mapped (ADR-0009 point 4:
pages translated by a function stay pinned until it returns).
"""
import argparse
import collections
import glob
import json
import os
import re
import shutil
import subprocess
import sys

PTR = re.compile(r"^(?:const )?struct (\w+) \*(?: const)?$")


def resolve_locations(node, state):
    """Give every bare location in clang's JSON dump the file it is in: the dump names a
    file only when it changes, in the order it writes the locations."""
    if isinstance(node, dict):
        if "offset" in node:
            if "file" in node:
                state["file"] = node["file"]
            node["_file"] = state["file"]
        for v in node.values():
            resolve_locations(v, state)
    elif isinstance(node, list):
        for v in node:
            resolve_locations(v, state)


def spelling(loc):
    """(file, offset, token length) where the text of a location is, or None."""
    if "spellingLoc" in loc:
        loc = loc["spellingLoc"]
    if "offset" not in loc:
        return None
    return loc["_file"], loc["offset"], loc.get("tokLen", 0)


def type_tag(t, tags):
    for q in (t.get("qualType", ""), t.get("desugaredQualType", "")):
        m = PTR.match(q)
        if m and m.group(1) in tags:
            return m.group(1)
    return None


def far_tag(expr, tags):
    return type_tag(expr.get("type", {}), tags)


def strip_ref(node):
    """The DeclRefExpr under parentheses and implicit casts, or None."""
    while node.get("kind") in ("ImplicitCastExpr", "ParenExpr") and len(node.get("inner", [])) == 1:
        node = node["inner"][0]
    return node if node.get("kind") == "DeclRefExpr" else None


def file_span(rng, path):
    """(begin, end) offsets of a range in file `path`, by spelling or else by expansion."""
    out = []
    for key in ("begin", "end"):
        loc = rng.get(key, {})
        got = None
        for sub in (loc.get("spellingLoc", loc), loc.get("expansionLoc", loc)):
            if "offset" in sub and os.path.realpath(sub.get("_file") or "") == os.path.realpath(path):
                got = (sub["offset"], sub.get("tokLen", 0))
                break
        if got is None:
            return None
        out.append(got)
    return out[0][0], out[1][0] + out[1][1]


def shadows(func, tags, single=True):
    """The variables of a function that --reuse shadows: {decl id: [name, tag, is_param]}.
    single: only those with one definition (a parameter never assigned, a local set in one
    place), which a translation at that definition serves best; a pointer stepped along a
    list is left to a translation at each access."""
    cands, unsafe, defs = {}, set(), collections.Counter()

    def walk(n):
        if isinstance(n, dict):
            k = n.get("kind")
            if k == "VarDecl" and n.get("storageClass") not in ("static", "extern"):
                tag = type_tag(n.get("type", {}), tags)
                if tag:
                    cands[n["id"]] = [n["name"], tag, False]
                    defs[n["id"]] += bool(n.get("inner"))
            elif k == "BinaryOperator" and n.get("opcode") == "=":
                r = strip_ref(n["inner"][0])
                if r:
                    defs[r["referencedDecl"]["id"]] += 1
            elif k == "UnaryOperator" and n.get("opcode") in ("&", "++", "--"):
                r = strip_ref(n["inner"][0])
                if r:
                    unsafe.add(r["referencedDecl"]["id"])
            elif k == "CompoundAssignOperator":
                r = strip_ref(n["inner"][0])
                if r:
                    unsafe.add(r["referencedDecl"]["id"])
            for v in n.get("inner", []):
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    for p in func.get("inner", []):
        if p.get("kind") == "ParmVarDecl" and p.get("name"):
            tag = type_tag(p.get("type", {}), tags)
            if tag:
                cands[p["id"]] = [p["name"], tag, True]
                defs[p["id"]] += 1
    walk(func.get("inner", []))
    return {k: v for k, v in cands.items() if k not in unsafe and (not single or defs[k] <= 1)}


def collect(node, tags, edits, problems, addr_of=False, reuse=None, func=None, single=True):
    """Every expression that is dereferenced as a far type: an edit that wraps its spelled
    range in XL_tag(...), or with --reuse one that puts a shadowed variable's shadow in its
    place.  `&mons[i]` is no access: its address stays a far pointer (addr_of, through
    parentheses).  reuse: {source path: [shadowed functions]} to fill, or None."""
    if isinstance(node, dict):
        kind = node.get("kind")
        if reuse is not None and kind == "FunctionDecl" and any(n.get("kind") == "CompoundStmt"
                                                                 for n in node.get("inner", [])):
            body = next(n for n in node["inner"] if n.get("kind") == "CompoundStmt")
            b = spelling(body.get("range", {}).get("begin", {}))
            if b and b[0] in reuse:
                sh = shadows(node, tags, single)
                for i, (k, v) in enumerate(sorted(sh.items(), key=lambda kv: kv[1][0])):
                    v.append("%s__x%d" % (v[0], i))
                    v.append("%s__t%d" % (v[0], i))
                func = dict(path=b[0], open=b[1] + 1, vars=sh, used_t=set())
                reuse[b[0]].append(func)
        if func is not None and kind == "BinaryOperator" and node.get("opcode") == "=":
            r = strip_ref(node["inner"][0])
            if r and r["referencedDecl"]["id"] in func["vars"]:
                v = func["vars"][r["referencedDecl"]["id"]]
                whole = file_span(node.get("range", {}), func["path"])
                rhs = file_span(node["inner"][1].get("range", {}), func["path"])
                if whole and rhs:
                    edits[func["path"]].add((whole[0], whole[1], "(%s = (" % v[4],
                                             "), %s = (%s ? XL_%s(%s) : 0), %s = %s)" % (v[3], v[4], v[1], v[4], v[0], v[4])))
                    edits[func["path"]].add((whole[0], rhs[0], None, ""))
                    func["used_t"].add(r["referencedDecl"]["id"])
                else:
                    problems.append("%s: an assignment to %s not spelled in the function" % (v[1], v[0]))
        if func is not None and kind == "VarDecl" and node.get("id") in func["vars"] and node.get("inner"):
            v = func["vars"][node["id"]]
            init = file_span(node["inner"][-1].get("range", {}), func["path"])
            if init:
                edits[func["path"]].add((init[0], init[1], "(%s = (" % v[4],
                                         "), %s = (%s ? XL_%s(%s) : 0), %s)" % (v[3], v[4], v[1], v[4], v[4])))
                func["used_t"].add(node["id"])
            else:
                problems.append("%s: the initialiser of %s not spelled in the function" % (v[1], v[0]))
        base = None
        if kind == "MemberExpr" and node.get("isArrow"):
            base = node["inner"][0]
        elif kind == "ArraySubscriptExpr" and not addr_of:
            base = node["inner"][0]
        elif kind == "UnaryOperator" and node.get("opcode") == "*":
            base = node["inner"][0]
        if base is not None:
            tag = far_tag(base, tags)
            if tag:
                ref = strip_ref(base) if func is not None else None
                if ref and ref["referencedDecl"]["id"] in func["vars"]:
                    sp = file_span(ref.get("range", {}), func["path"])
                    if sp:
                        edits[func["path"]].add((sp[0], sp[1], None, func["vars"][ref["referencedDecl"]["id"]][3]))
                    else:
                        problems.append("%s: a shadowed access not spelled in the function" % tag)
                else:
                    r = base.get("range", {})
                    b, e = spelling(r.get("begin", {})), spelling(r.get("end", {}))
                    if not b or not e or b[0] != e[0]:
                        problems.append("%s: an access spelled across a macro boundary (%s, %s)" % (tag, b, e))
                    else:
                        edits[b[0]].add((b[1], e[1] + e[2], "XL_%s(" % tag, ")"))
        child_addr_of = (kind == "UnaryOperator" and node.get("opcode") == "&") or (kind == "ParenExpr" and addr_of)
        for v in node.get("inner", []):
            collect(v, tags, edits, problems, child_addr_of, reuse, func, single)


def apply_edits(text, edits):
    """Apply (begin, end, pre, post) edits: pre and post around the span, nested spans inside
    out; with pre None, post replaces the span's text (an identifier, or `v =`), innermost."""
    events = []
    for b, e, pre, post in edits:
        if pre is None:
            events.append((b, 3, 0, post, e))               # replacements: after the opens
        else:
            events.append((b, 2, -(e - b), pre, None))      # opens: the outer first
            events.append((e, 0, (e - b), post, None))      # closes before opens, the inner first
    events.sort(key=lambda ev: ev[:3])
    out, pos = [], 0
    for at, _, _, s, skip in events:
        assert at >= pos, "an edit inside a replaced span at %d" % at
        out.append(text[pos:at])
        out.append(s)
        pos = skip if skip is not None else at
    out.append(text[pos:])
    return "".join(out)


def match_close(text, i, open_ch, close_ch):
    """The index of the bracket that closes the one at text[i]."""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == open_ch:
            depth += 1
        elif text[j] == close_ch:
            depth -= 1
            if depth == 0:
                return j
    return -1


def expand_bodies(out_x, out_inc, cflags):
    """Replace the body of every function in the copies with its macro expansion (clang -E,
    the system headers empty), so that an access made by a macro is spelled in the function.
    The definitions are found in the expansion in their order, after a marker pragma placed
    after the file's includes."""
    fake = os.path.join(os.path.dirname(out_x), "nosys")
    for path in glob.glob(os.path.join(out_inc, "*.h")) + glob.glob(os.path.join(out_x, "x_*.c")):
        for h in re.findall(r"(?m)^\s*#\s*include\s*<([^>]+)>", open(path, errors="replace").read()):
            f = os.path.join(fake, h.replace("\\", "/"))
            os.makedirs(os.path.dirname(f), exist_ok=True)
            open(f, "a").close()
    for s in sorted(glob.glob(os.path.join(out_x, "x_*.c"))):
        text = open(s, errors="replace").read()
        lines = text.split("\n")
        last = max(i for i, l in enumerate(lines) if re.match(r"^\s*#\s*include\b", l))
        marked = os.path.join(os.path.dirname(out_x), "mark_" + os.path.basename(s))
        open(marked, "w").write("\n".join(lines[:last + 1] + ["#pragma nh_farify_mark"] + lines[last + 1:]))
        r = subprocess.run(["clang", "-E", "-P", "-nostdinc", "-I" + out_inc, "-I" + fake,
                            "-D__OSCAR64C__=1", "-D__C64__=1"] + cflags + [marked], capture_output=True, text=True)
        os.remove(marked)
        if r.returncode:
            sys.exit("clang -E failed for %s:\n%s" % (s, r.stderr[-2000:]))
        expanded = r.stdout
        at = expanded.index("#pragma nh_farify_mark")
        r = subprocess.run(["clang", "-fsyntax-only", "-std=gnu89", "-w", "-I" + out_inc] + cflags +
                           ["-Xclang", "-ast-dump=json", s], capture_output=True, text=True)
        tree = json.loads(r.stdout)
        resolve_locations(tree, {"file": None})
        bodies = []
        for d in tree.get("inner", []):
            if d.get("kind") != "FunctionDecl":
                continue
            body = next((n for n in d.get("inner", []) if n.get("kind") == "CompoundStmt"), None)
            span = file_span(body.get("range", {}), s) if body else None
            if span:
                bodies.append((span[0], span[1], d["name"]))
        new_bodies = []
        for b, e, name in sorted(bodies):
            k = -1
            for m in re.compile(r"(?m)^[ \t]*(?:\w[\w \t*]*[ \t*])?%s[ \t]*\(" % re.escape(name)).finditer(expanded, at):
                close = match_close(expanded, m.end() - 1, "(", ")")
                k = close + 1
                while 0 < k < len(expanded) and expanded[k] in " \t\n":
                    k += 1
                if close >= 0 and expanded[k:k + 1] == "{":
                    break
                k = -1
            if k < 0:
                sys.exit("%s: no definition of %s in its expansion" % (s, name))
            j = match_close(expanded, k, "{", "}")
            new_bodies.append((b, e, expanded[k:j + 1]))
            at = j + 1
        for b, e, body in sorted(new_bodies, reverse=True):
            text = text[:b] + body + text[e:]
        open(s, "w").write(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", required=True)
    ap.add_argument("--inc", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--type", action="append", required=True, dest="types")
    ap.add_argument("--cflag", action="append", default=[], dest="cflags")
    ap.add_argument("--expand", action="store_true", help="macro-expand the functions' bodies first")
    ap.add_argument("--reuse", action="store_true",
                    help="translate a variable with one definition once, there (implies --expand)")
    ap.add_argument("--reuse-all", action="store_true",
                    help="every shadowable variable, at each of its definitions (implies --reuse)")
    ap.add_argument("--no-rewrite", action="store_true",
                    help="only the copies with far_pre.h and far_post.h: for a compiler with far "
                         "spaces, which translates by itself (calibrate.py --far-cc)")
    a = ap.parse_args()
    a.reuse = a.reuse or a.reuse_all
    a.expand = a.expand or a.reuse
    out_x, out_inc = os.path.join(a.out, "x"), os.path.join(a.out, "inc")
    shutil.rmtree(a.out, ignore_errors=True)
    os.makedirs(out_x)
    shutil.copytree(a.inc, out_inc)
    sources = sorted(glob.glob(os.path.join(a.src, "x_*.c")))
    # #line would make clang name port/src for offsets into the copies: parse them without
    for s in sources:
        text = open(s, errors="replace").read()
        open(os.path.join(out_x, os.path.basename(s)), "w").write(re.sub(r"(?m)^#line .*\n", "", text))
    if a.expand:
        expand_bodies(out_x, out_inc, a.cflags)
    tags = set(a.types)
    edits, problems = collections.defaultdict(set), []
    reuse = collections.defaultdict(list) if a.reuse else None
    for s in ([] if a.no_rewrite else sorted(glob.glob(os.path.join(out_x, "x_*.c")))):
        r = subprocess.run(["clang", "-fsyntax-only", "-std=gnu89", "-w", "-I" + out_inc] + a.cflags +
                           ["-Xclang", "-ast-dump=json", s], capture_output=True, text=True)
        if not r.stdout:
            sys.exit("clang gave no AST for %s:\n%s" % (s, r.stderr[-2000:]))
        tree = json.loads(r.stdout)
        resolve_locations(tree, {"file": None})
        if reuse is not None:
            reuse[s] = []
        collect(tree, tags, edits, problems, reuse=reuse, single=not a.reuse_all)
    nshadow = 0
    for path, funcs in (reuse or {}).items():
        for f in funcs:
            decls = []
            for k, (name, tag, is_param, x, t) in sorted(f["vars"].items(), key=lambda kv: kv[1][3]):
                decls.append("struct %s *%s%s;" % (tag, x, " = %s ? XL_%s(%s) : 0" % (name, tag, name) if is_param else ""))
                if k in f["used_t"]:
                    decls.append("struct %s *%s;" % (tag, t))
                nshadow += 1
            if decls:
                edits[path].add((f["open"], f["open"], " " + " ".join(decls), ""))
    counts = {}
    for path, spans in sorted(edits.items()):
        path = os.path.realpath(path)
        if not (path.startswith(os.path.realpath(out_x)) or path.startswith(os.path.realpath(out_inc))):
            problems.append("an access in %s, outside the copies: left alone" % path)
            continue
        text = open(path, errors="replace").read()
        open(path, "w").write(apply_edits(text, spans))
        counts[os.path.relpath(path, a.out)] = len(spans)
    if reuse is not None:
        print("reuse: %d variables shadowed in %d functions" % (nshadow, sum(len(f) for f in reuse.values())))
    here = os.path.dirname(os.path.abspath(__file__))
    for h in ("far_pre.h", "far_post.h"):
        shutil.copy(os.path.join(here, h), os.path.join(out_inc, h))
    for s in sorted(glob.glob(os.path.join(out_x, "x_*.c"))):
        lines = open(s, errors="replace").read().split("\n")
        last = max(i for i, l in enumerate(lines) if re.match(r"^#\s*include\b", l))
        lines.insert(last + 1, '#include "far_post.h"')
        lines.insert(1, '#include "far_pre.h"')
        open(s, "w").write("\n".join(lines))
    for f, n in counts.items():
        print("%-22s %3d accesses translated" % (f, n))
    for p in sorted(set(problems)):
        print("NOT REWRITTEN:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
