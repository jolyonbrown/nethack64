#!/usr/bin/env python3
"""
ansi_manual_fixes.py - hand-written ANSI conversions that kr2ansi.py skips.

NetHack 3.4.3 has a handful of definitions whose K&R parameter list is
chosen by the preprocessor.  kr2ansi.py refuses to guess at those; this
script rewrites each one to an ANSI header that keeps the same #if structure.

Run it BEFORE kr2ansi.py (it matches pristine 3.4.3 text):

    python3 tools/ansi_manual_fixes.py path/to/src

Each fix is an exact (old, new) text replacement.  If the old text is not
found the script says so and exits non-zero, so a drift in the source is
noticed rather than silently ignored.
"""
import os
import sys

FIXES = {
    "mklev.c": [(
"""#ifdef SPECIALIZATION
topologize(croom, do_ordinary)
register struct mkroom *croom;
boolean do_ordinary;
#else
topologize(croom)
register struct mkroom *croom;
#endif
{""",
"""#ifdef SPECIALIZATION
topologize(struct mkroom *croom, boolean do_ordinary)
#else
topologize(struct mkroom *croom)
#endif
{"""),
    ],
    "pickup.c": [(
"""#ifndef GOLDOBJ
int
collect_obj_classes(ilets, otmp, here, incl_gold, filter, itemcount)
char ilets[];
register struct obj *otmp;
boolean here, incl_gold;
boolean FDECL((*filter),(OBJ_P));
int *itemcount;
#else
int
collect_obj_classes(ilets, otmp, here, filter, itemcount)
char ilets[];
register struct obj *otmp;
boolean here;
boolean FDECL((*filter),(OBJ_P));
int *itemcount;
#endif
{""",
"""#ifndef GOLDOBJ
int
collect_obj_classes(char ilets[], struct obj *otmp, boolean here,
                    boolean incl_gold, boolean FDECL((*filter),(OBJ_P)),
                    int *itemcount)
#else
int
collect_obj_classes(char ilets[], struct obj *otmp, boolean here,
                    boolean FDECL((*filter),(OBJ_P)), int *itemcount)
#endif
{"""), (
"""#ifndef GOLDOBJ
STATIC_OVL boolean
query_classes(oclasses, one_at_a_time, everything, action, objs,
	      here, incl_gold, menu_on_demand)
char oclasses[];
boolean *one_at_a_time, *everything;
const char *action;
struct obj *objs;
boolean here, incl_gold;
int *menu_on_demand;
#else
STATIC_OVL boolean
query_classes(oclasses, one_at_a_time, everything, action, objs,
	      here, menu_on_demand)
char oclasses[];
boolean *one_at_a_time, *everything;
const char *action;
struct obj *objs;
boolean here;
int *menu_on_demand;
#endif
{""",
"""#ifndef GOLDOBJ
STATIC_OVL boolean
query_classes(char oclasses[], boolean *one_at_a_time, boolean *everything,
              const char *action, struct obj *objs, boolean here,
              boolean incl_gold, int *menu_on_demand)
#else
STATIC_OVL boolean
query_classes(char oclasses[], boolean *one_at_a_time, boolean *everything,
              const char *action, struct obj *objs, boolean here,
              int *menu_on_demand)
#endif
{"""),
    ],
    "save.c": [(
"""STATIC_OVL void
savelev0(fd,lev,mode)
#else
void
savelev(fd,lev,mode)
#endif
int fd;
xchar lev;
int mode;
{""",
"""STATIC_OVL void
savelev0(int fd, xchar lev, int mode)
#else
void
savelev(int fd, xchar lev, int mode)
#endif
{"""),
    ],
}


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "."
    failed = 0
    for fname, fixes in FIXES.items():
        path = os.path.join(src, fname)
        with open(path, encoding="latin-1") as f:
            text = f.read()
        for old, new in fixes:
            if new in text:
                print("%s: already applied" % fname)
                continue
            if old not in text:
                print("%s: EXPECTED TEXT NOT FOUND" % fname)
                failed += 1
                continue
            text = text.replace(old, new, 1)
            print("%s: fixed" % fname)
        with open(path, "w", encoding="latin-1") as f:
            f.write(text)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
