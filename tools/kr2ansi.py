#!/usr/bin/env python3
"""
kr2ansi.py - convert NetHack 3.4.3's K&R-style function definitions to ANSI C.

Why: Oscar64 rejects K&R definitions outright, and cc65 rejects NetHack's
pattern of K&R definitions paired with prototypes that use narrow types
(char/xchar/boolean).  So the conversion is needed whichever compiler we use.

NetHack 3.4.3 writes definitions in a very regular style:

    STATIC_OVL int
    dig_check(madeby, verbose, x, y)
        struct monst *madeby;
        boolean       verbose;
        int           x, y;
    {

which this tool rewrites to

    STATIC_OVL int
    dig_check(struct monst *madeby, boolean verbose, int x, int y)
    {

Rules / behaviour
  * Only lines that look like `name(ident, ident, ...)` (optionally with a
    return type prefix on the same line) followed by declaration lines and a
    `{` at column 0 are touched.  VA_DECL-style variadics are left alone (they
    already expand to ANSI under USE_STDARG).
  * Empty parameter lists `name()` followed by `{` become `name(void)`.
  * `register` is dropped from parameters (meaningless for ANSI params).
  * Parameters with no declaration become `int name` (K&R implicit int).
  * Comments found in the declaration block are preserved on a line after
    the new signature.
  * Anything unusual (preprocessor lines inside the declaration block, a
    declared name that is not in the identifier list, unbalanced brackets) is
    NOT converted; it is reported so a human/agent can fix it by hand.

The result must be compiled with UNWIDENED_PROTOTYPES defined so the
prototypes in extern.h (CHAR_P, XCHAR_P, BOOLEAN_P ...) use the narrow types
that now appear in the definitions.  `make -C tools check-ansi` (or
tools/check_ansi.sh) verifies this with gcc.

Usage:
    kr2ansi.py [--dry-run] [--report report.txt] file.c [file.c ...]
"""
import argparse
import re
import sys

HEADER_RE = re.compile(
    r"^(?P<pre>(?:[A-Za-z_][\w]*[\s\*]+)*?)"      # optional return type on same line
    r"(?P<name>[A-Za-z_]\w*)\s*"
    r"\((?P<args>\s*(?:[A-Za-z_]\w*\s*(?:,\s*[A-Za-z_]\w*\s*)*)?)\)"
    r"\s*(?P<comment>/\*.*\*/)?\s*$"
)
KEYWORDS = {"if", "while", "for", "switch", "return", "sizeof", "do", "else",
            "case", "goto", "defined"}
COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
WORD_RE = re.compile(r"[A-Za-z_]\w*")


def split_top(text, sep):
    """Split text on sep at bracket depth 0."""
    parts, depth, cur = [], 0, []
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth < 0:
                raise ValueError("unbalanced brackets")
        if ch == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if depth != 0:
        raise ValueError("unbalanced brackets")
    parts.append("".join(cur))
    return parts


def find_name(decl, names):
    """Return (name, start_of_declarator) for the declarator in decl."""
    best = None
    for m in WORD_RE.finditer(decl):
        if m.group(0) in names:
            rest = decl[m.end():].lstrip()
            if rest == "" or rest[0] in ",;[)":
                best = m  # last suitable occurrence wins (struct obj *obj)
    if best is None:
        return None, None
    name = best.group(0)
    # Function-pointer declarators written with NetHack's FDECL/NDECL macros
    for macro in ("FDECL(", "NDECL(", "VDECL("):
        idx = decl.find(macro)
        if 0 <= idx < best.start():
            return name, idx
    start = best.start()
    while start > 0 and decl[start - 1] in " \t*(":
        start -= 1
    # keep whitespace on the base-type side
    while start < best.start() and decl[start] in " \t":
        start += 1
    return name, start


def parse_decls(block_text, names):
    """Parse K&R declaration text into {name: 'type declarator'}."""
    result = {}
    for stmt in split_top(block_text, ";"):
        stmt = stmt.strip()
        if not stmt:
            continue
        chunks = split_top(stmt, ",")
        name, start = find_name(chunks[0], names)
        if name is None:
            raise ValueError("cannot find parameter name in %r" % stmt)
        base = chunks[0][:start]
        base = re.sub(r"\bregister\b", "", base)
        base = " ".join(base.split())
        if not base:
            base = "int"
        decls = [chunks[0][start:]] + chunks[1:]
        for d in decls:
            d = " ".join(d.split())
            n, _ = find_name(d, names)
            if n is None:
                raise ValueError("cannot find parameter name in %r" % d)
            if n in result:
                raise ValueError("parameter %s declared twice" % n)
            result[n] = "%s %s" % (base, d)
    return result


OPEN_HEADER_RE = re.compile(
    r"^(?:[A-Za-z_][\w]*[\s\*]+)*?[A-Za-z_]\w*\s*\(\s*[A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*\s*,?\s*$")
EMPTY_BRACE_RE = re.compile(
    r"^(?P<head>(?:[A-Za-z_][\w]*[\s\*]+)*?[A-Za-z_]\w*\s*)\(\)(?P<tail>\s*\{.*)$")


def normalise(lines):
    """Join K&R headers whose identifier list or trailing comment spans lines."""
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line and not line[0].isspace() and not line.startswith("#"):
            s = line.rstrip("\n")
            # identifier list continued on following line(s)
            if OPEN_HEADER_RE.match(s):
                j = i + 1
                joined = s
                while j < n and ")" not in joined and j - i < 6:
                    joined += " " + lines[j].strip()
                    j += 1
                if HEADER_RE.match(joined):
                    out.append(joined + "\n")
                    i = j
                    continue
            # trailing comment that continues on following line(s)
            if "(" in s and "/*" in s and "*/" not in s:
                j = i + 1
                joined = s
                while j < n and "*/" not in joined and j - i < 6:
                    joined += " " + lines[j].strip()
                    j += 1
                if HEADER_RE.match(joined):
                    out.append(joined + "\n")
                    i = j
                    continue
        out.append(line)
        i += 1
    return out


def convert(lines, path, report):
    out = []
    i = 0
    converted = 0
    lines = normalise(lines)
    n = len(lines)
    while i < n:
        line = lines[i]
        e = EMPTY_BRACE_RE.match(line.rstrip("\n"))
        if (e and not line[0].isspace()
                and e.group("head").split()[-1] not in KEYWORDS):
            out.append("%s(void)%s\n" % (e.group("head"), e.group("tail")))
            converted += 1
            i += 1
            continue
        m = HEADER_RE.match(line.rstrip("\n"))
        if (m and not line[0].isspace() and m.group("name") not in KEYWORDS
                and m.group("args").strip() != "void"     # already ANSI
                and not line.lstrip().startswith("#")):
            # collect the declaration block up to a '{' at column 0
            j = i + 1
            block = []
            ok = True
            mac_pragma = False
            while j < n and not lines[j].startswith("{"):
                s = lines[j]
                # Mac-only "#pragma unused" blocks sit between the K&R
                # declarations and the brace; they are dropped.
                if re.match(r"#\s*if\s+defined\(macintosh\)", s):
                    mac_pragma = True
                    j += 1
                    continue
                if mac_pragma:
                    if re.match(r"#\s*endif", s):
                        mac_pragma = False
                    j += 1
                    continue
                if s.lstrip().startswith("#"):
                    ok = False
                    break
                if s.strip() and not (s[0].isspace() or s.lstrip().startswith("/*")
                                      or WORD_RE.match(s)):
                    ok = False
                    break
                block.append(s)
                j += 1
                if j - i > 40:
                    ok = False
                    break
            if j >= n or not ok:
                if ok is False and m.group("args").strip():
                    report.append("%s:%d: SKIPPED (preprocessor or odd block) %s"
                                  % (path, i + 1, line.strip()))
                out.append(line)
                i += 1
                continue
            block_text = "".join(block)
            # every non-blank, non-comment line must end a declaration
            bare = COMMENT_RE.sub("", block_text)
            if bare.strip() and not bare.strip().endswith(";"):
                out.append(line)
                i += 1
                continue
            comments = COMMENT_RE.findall(block_text)
            argnames = [a.strip() for a in m.group("args").split(",") if a.strip()]
            try:
                decls = parse_decls(bare, set(argnames))
            except ValueError as e:
                report.append("%s:%d: SKIPPED (%s) %s" % (path, i + 1, e, line.strip()))
                out.append(line)
                i += 1
                continue
            extra = set(decls) - set(argnames)
            if extra:
                report.append("%s:%d: SKIPPED (declares %s not in list) %s"
                              % (path, i + 1, ",".join(sorted(extra)), line.strip()))
                out.append(line)
                i += 1
                continue
            params = [decls.get(a, "int %s" % a) for a in argnames] or ["void"]
            pre = m.group("pre") or ""
            head = "%s%s(" % (pre, m.group("name"))
            sig = head + ", ".join(params) + ")"
            if len(sig) > 78:
                indent = " " * len(head)
                sig = head + (",\n" + indent).join(params) + ")"
            if m.group("comment"):
                sig += " " + m.group("comment")
            out.append(sig + "\n")
            for c in comments:
                out.append(c + "\n")
            converted += 1
            i = j  # resume at the '{' line
            continue
        out.append(line)
        i += 1
    return out, converted


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", help="write skipped-definition report here")
    args = ap.parse_args()
    report = []
    total = 0
    for path in args.files:
        with open(path, encoding="latin-1") as f:
            lines = f.readlines()
        out, count = convert(lines, path, report)
        total += count
        if not args.dry_run and out != lines:
            with open(path, "w", encoding="latin-1") as f:
                f.writelines(out)
        print("%-28s %4d definitions converted" % (path, count))
    print("TOTAL %d definitions converted, %d skipped" % (total, len(report)))
    for r in report:
        print(r, file=sys.stderr)
    if args.report:
        with open(args.report, "w") as f:
            f.write("\n".join(report) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
