#!/usr/bin/env python3
"""farify.py - the speed harness's functions as a compiler with typed far spaces would make
them (docs/RAM-PLAN.md, T2.11): every access through a pointer to one of the named struct
types goes through a translation first, `p->f` becoming `XL_<tag>(p)->f`.

usage: tools/measure/speed/farify.py --src XDIR --inc INCDIR --out OUTDIR --type TAG...
                                     [--cflag FLAG...]

XDIR holds extract.py's files (x_*.c) and INCDIR the headers they include (calibrate.py's
C64 view); OUTDIR gets x/ and inc/ rewritten, each file with far_pre.h before its own
includes (the translations) and far_post.h after them.  clang finds the accesses from the types, so
nothing is guessed from the text: a member access through `->`, a subscript and a `*` whose
pointer is `struct TAG *`.  An access spelled inside a macro is rewritten in the macro's
body (mondata.h's `(ptr)->mflags1`), once for every use.  An access that clang spells across
a macro's boundary cannot be rewritten in one place and is reported; so is anything else
left alone.  The experiment's own oracle is calibrate.py's checksum: the far build keeps its
pointers away from the real addresses, so a missed access reads the wrong bytes.
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


def far_tag(expr, tags):
    t = expr.get("type", {})
    for q in (t.get("qualType", ""), t.get("desugaredQualType", "")):
        m = PTR.match(q)
        if m and m.group(1) in tags:
            return m.group(1)
    return None


def collect(node, tags, edits, problems, addr_of=False):
    """Every expression that is dereferenced as a far type: its spelled range.  `&mons[i]`
    is no access: its address stays a far pointer (addr_of, through parentheses)."""
    if isinstance(node, dict):
        kind = node.get("kind")
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
                r = base.get("range", {})
                b, e = spelling(r.get("begin", {})), spelling(r.get("end", {}))
                if not b or not e or b[0] != e[0]:
                    problems.append("%s: an access spelled across a macro boundary (%s, %s)" % (tag, b, e))
                else:
                    edits[b[0]].add((b[1], e[1] + e[2], tag))
        child_addr_of = (kind == "UnaryOperator" and node.get("opcode") == "&") or (kind == "ParenExpr" and addr_of)
        for v in node.get("inner", []):
            collect(v, tags, edits, problems, child_addr_of)


def apply_edits(text, spans):
    """Wrap each (begin, end, tag) span in XL_tag( ... ), nested spans inside out."""
    events = []
    for b, e, tag in spans:
        events.append((b, 1, -(e - b), "XL_%s(" % tag))   # opens: the outer first
        events.append((e, 0, (e - b), ")"))                 # closes before opens, the inner first
    events.sort()
    out, pos = [], 0
    for at, _, _, s in events:
        out.append(text[pos:at])
        out.append(s)
        pos = at
    out.append(text[pos:])
    return "".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", required=True)
    ap.add_argument("--inc", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--type", action="append", required=True, dest="types")
    ap.add_argument("--cflag", action="append", default=[], dest="cflags")
    a = ap.parse_args()
    out_x, out_inc = os.path.join(a.out, "x"), os.path.join(a.out, "inc")
    shutil.rmtree(a.out, ignore_errors=True)
    os.makedirs(out_x)
    shutil.copytree(a.inc, out_inc)
    sources = sorted(glob.glob(os.path.join(a.src, "x_*.c")))
    # #line would make clang name port/src for offsets into the copies: parse them without
    for s in sources:
        text = open(s, errors="replace").read()
        open(os.path.join(out_x, os.path.basename(s)), "w").write(re.sub(r"(?m)^#line .*\n", "", text))
    tags = set(a.types)
    edits, problems = collections.defaultdict(set), []
    for s in sorted(glob.glob(os.path.join(out_x, "x_*.c"))):
        r = subprocess.run(["clang", "-fsyntax-only", "-std=gnu89", "-w", "-I" + out_inc] + a.cflags +
                           ["-Xclang", "-ast-dump=json", s], capture_output=True, text=True)
        if not r.stdout:
            sys.exit("clang gave no AST for %s:\n%s" % (s, r.stderr[-2000:]))
        tree = json.loads(r.stdout)
        resolve_locations(tree, {"file": None})
        collect(tree, tags, edits, problems)
    counts = {}
    for path, spans in sorted(edits.items()):
        path = os.path.realpath(path)
        if not (path.startswith(os.path.realpath(out_x)) or path.startswith(os.path.realpath(out_inc))):
            problems.append("an access in %s, outside the copies: left alone" % path)
            continue
        text = open(path, errors="replace").read()
        open(path, "w").write(apply_edits(text, spans))
        counts[os.path.relpath(path, a.out)] = len(spans)
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
