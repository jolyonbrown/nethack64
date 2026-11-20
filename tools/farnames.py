#!/usr/bin/env python3
"""farnames.py - read the names of mons[], obj_descr[] and roles[] through an accessor (T2.12).

usage: tools/farnames.py [--check] FILE.c ...

In the C64 build the names (`struct permonst`'s mname, `struct objdescr`'s oc_name and
oc_descr) are string literals in far memory, beside the tables that point to them, so a
name is not a near string: NH_MNAME() and NH_ONAME() (permonst.h, objclass.h) copy one into
a near buffer of a small ring, as a string result crossing banks is copied (nhbank.h).
This wraps each read of such a member, `EXPR->mname` or `EXPR.oc_name`, in the accessor:
`NH_MNAME(EXPR->mname)`.  A store to the member (options.c gives the fruit its name) and
`sizeof` are left alone, and so is a use already wrapped, so the script can be run again.
On the host, and in any build without far names, the accessors are the identity.
The role and race strings (struct Role, struct Race: role.c) go through NH_RNAME() the
same way; a store of one into another such member (`urole.lgod = roles[i].lgod`) keeps
the far address and is not wrapped, since the copy would not outlive the ring.

--check: change nothing, list what would change; exit 1 if anything would.
"""
import argparse
import re
import sys

MEMBERS = {"mname": "NH_MNAME", "oc_name": "NH_ONAME", "oc_descr": "NH_ONAME"}
# role.c's strings (struct Role, struct Race, and the genders' and alignments' that share
# member names): NH_RNAME() returns a near string as it is, so a read of a member of the
# same name in a near table only costs a call
ROLE_MEMBERS = ["lgod", "ngod", "cgod", "filecode", "homebase", "intermed", "noun", "adj", "coll"]
MEMBERS.update({m: "NH_RNAME" for m in ROLE_MEMBERS})
MEMBERS.update({"m": "NH_RNAME", "f": "NH_RNAME"})       # struct RoleName, see below
ACCESS = re.compile(r"(->|\.)\s*(%s)\b" % "|".join(MEMBERS))
# m and f only as struct RoleName's: after name, individual or rank[...] (timeout.c's
# timeout_funcs[].f is a function)
ROLENAME = re.compile(r"(?:\bname|\bindividual|\brank\s*\[[^\]]*\])\s*$")
FAMILY = "|".join(re.escape(m) for m in MEMBERS)
STORED = re.compile(r"(?:->|\.)\s*(?:%s)\s*=$" % FAMILY)
SKIP = re.compile(r'/\*.*?\*/|"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'|^[ \t]*#[^\n]*', re.S | re.M)


def expr_start(code, end):
    """Index where the postfix expression ending just before `end` starts (`a->b[i].c`,
    `f(x)->d`), scanning back over identifiers, members, subscripts and calls."""
    i = end
    while True:
        j = i
        while j > 0 and code[j - 1] in " \t\n":
            j -= 1
        if j > 0 and code[j - 1] in ")]":
            close, open_ = code[j - 1], "(" if code[j - 1] == ")" else "["
            depth, k = 0, j - 1
            while k >= 0:
                if code[k] == close:
                    depth += 1
                elif code[k] == open_:
                    depth -= 1
                    if depth == 0:
                        break
                k -= 1
            i = k
            if open_ == "(":
                # a call (`f(x)`) goes on to the function's name; a bare parenthesis
                # (`(*p)`) is the whole operand
                m = re.search(r"[A-Za-z_]\w*\s*$", code[:i])
                if m and m.group(0).strip() not in ("if", "while", "for", "switch", "return", "sizeof"):
                    i = m.start()
                else:
                    return i
            continue
        m = re.search(r"[A-Za-z_]\w*$", code[:j])
        if not m:
            return i
        i = m.start()
        k = i
        while k > 0 and code[k - 1] in " \t\n":
            k -= 1
        if code[k - 2:k] == "->":
            i = k - 2
        elif k > 0 and code[k - 1] == "." and not (k > 1 and code[k - 2].isdigit()):
            i = k - 1
        else:
            return i


def wrap(text):
    code = SKIP.sub(lambda m: " " * len(m.group(0)) if "\n" not in m.group(0)
                    else re.sub(r"[^\n]", " ", m.group(0)), text)
    edits = []
    for m in ACCESS.finditer(code):
        if m.group(2) in ("m", "f") and not ROLENAME.search(code[:m.start()]):
            continue
        after = code[m.end():].lstrip()
        if after.startswith("=") and not after.startswith("=="):
            continue                                  # a store
        start = expr_start(code, m.start())
        before = code[:start].rstrip()
        if before.endswith("sizeof") or re.search(r"\bNH_[MOR]NAME(?:_B)?\s*\(\s*$", before):
            continue
        if re.match(r"(?:name|individual|rank)\b", code[start:]):
            continue        # a bare member path, a macro's field (options.c's rolestring())
        if STORED.search(before) and code[m.end():].lstrip().startswith(";"):
            continue        # copied into a member of the family: the far address, kept as it is
        if before.endswith("&") and not before.endswith("&&"):
            sys.exit("the address of a name member at offset %d: handle it by hand" % start)
        edits.append((start, m.end(), MEMBERS[m.group(2)]))
    out, pos = [], 0
    for s, e, fn in edits:
        out += [text[pos:s], "%s(%s)" % (fn, text[s:e])]
        pos = e
    out.append(text[pos:])
    return "".join(out), edits


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    total = 0
    for f in a.files:
        text = open(f, encoding="latin-1").read()
        new, edits = wrap(text)
        total += len(edits)
        if a.check:
            for s, e, fn in edits:
                line = text.count("\n", 0, s) + 1
                print("%s:%d: %s(%s)" % (f, line, fn, " ".join(text[s:e].split())))
        elif edits:
            open(f, "w", encoding="latin-1").write(new)
    print("farnames: %d reads %s" % (total, "to wrap" if a.check else "wrapped"), file=sys.stderr)
    return 1 if a.check and total else 0


if __name__ == "__main__":
    sys.exit(main())
