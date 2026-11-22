#!/usr/bin/env python3
"""c64data.py - NetHack's binary data files, as the host's tools write them, in the C64's layout.

usage: tools/data/c64data.py dungeon HOST_FILE OUT
       tools/data/c64data.py quest HOST_FILE OUT
       tools/data/c64data.py lev HOST_FILE OUT

dgn_comp and makedefs write structs as they lie in the host's memory (x86-64: int 4 bytes,
long 8, padding to each field's size), and the game reads them back the same way, so on the
C64 (int 2, long 4, no padding: Oscar64) the files must be in the C64's layout (T3.2). This
reads the host's file field by field and writes each struct again, with the offsets a file
holds recomputed where the layout moves what they point at. Little-endian on both.

dungeon (dungeon.c's init_dungeons(), dgn_file.h): struct version_info (4 x unsigned long),
  n_dgns (int), then per dungeon a struct tmpdungeon_s and its levels' struct tmplevel_s and
  branches' struct tmpbranch_s.
quest (questpgr.c's load_qtlist(), qtext.h; makedefs.c's put_qt_hdrs()): n_hdr (int), the
  class ids (char[3] each), their headers' offsets (long each); at each, n_msg (int) and
  n_msg struct qtmsg (int msgnum, char delivery, long offset, long size); then the text, at
  the offsets the qtmsgs give.
"""
import argparse
import struct
import sys


class Reader:
    def __init__(self, data):
        self.d, self.p = data, 0

    def take(self, fmt):
        n = struct.calcsize(fmt)
        if self.p + n > len(self.d):
            sys.exit("short file at %d" % self.p)
        v = struct.unpack_from(fmt, self.d, self.p)
        self.p += n
        return v

    def pad(self, align):
        self.p = (self.p + align - 1) // align * align


# host (x86-64, gcc) and C64 (Oscar64) struct layouts, "<" for no padding: the host's are
# written with their padding explicit
HOST_VERSION, C64_VERSION = "<4Q", "<4L"
HOST_INT, C64_INT = "<i", "<h"
# tmpdungeon_s: name[24], protoname[24], couple{short base, rand}, int flags, chance, levels,
# branches, entry_lev, char boneschar (+3 padding on the host)
HOST_TDUNGEON, C64_TDUNGEON = "<24s24shh5ic3x", "<24s24shh5hc"
# tmplevel_s: name[24], couple, int chance, rndlevs, chain, flags, char boneschar (+3)
HOST_TLEVEL, C64_TLEVEL = "<24shh4ic3x", "<24shh4hc"
# tmpbranch_s: name[24], couple, int chain, type, up
HOST_TBRANCH, C64_TBRANCH = "<24shh3i", "<24shh3h"


def c64_int(v, what):
    if not -32768 <= v <= 32767:
        sys.exit("%s %d does not fit a C64 int" % (what, v))
    return v


def dungeon(data):
    r, out = Reader(data), bytearray()
    out += struct.pack(C64_VERSION, *[v & 0xFFFFFFFF for v in r.take(HOST_VERSION)])
    (n_dgns,) = r.take(HOST_INT)
    out += struct.pack(C64_INT, c64_int(n_dgns, "n_dgns"))
    for _ in range(n_dgns):
        name, proto, base, rnd, *ints, bones = r.take(HOST_TDUNGEON)
        out += struct.pack(C64_TDUNGEON, name, proto, base, rnd,
                           *[c64_int(v, "tmpdungeon") for v in ints], bones)
        levels, branches = ints[2], ints[3]
        for _ in range(levels):
            name, base, rnd, *ints, bones = r.take(HOST_TLEVEL)
            out += struct.pack(C64_TLEVEL, name, base, rnd, *[c64_int(v, "tmplevel") for v in ints], bones)
        for _ in range(branches):
            name, base, rnd, *ints = r.take(HOST_TBRANCH)
            out += struct.pack(C64_TBRANCH, name, base, rnd, *[c64_int(v, "tmpbranch") for v in ints])
    if r.p != len(data):
        sys.exit("dungeon: %d bytes left after the last dungeon" % (len(data) - r.p))
    return bytes(out)


LEN_HDR = 3
HOST_QTMSG, C64_QTMSG = "<ic3xqq", "<hcll"


def quest(data):
    r = Reader(data)
    (n_hdr,) = r.take(HOST_INT)
    ids = [r.take("<%ds" % LEN_HDR)[0] for _ in range(n_hdr)]
    offsets = [r.take("<q")[0] for _ in range(n_hdr)]
    classes, text_start = [], 0
    for off in offsets:
        r.p = off
        (n_msg,) = r.take(HOST_INT)
        classes.append([r.take(HOST_QTMSG) for _ in range(n_msg)])
        text_start = max(text_start, r.p)
    # the text: from the end of the class records to the end of the file, at the offsets the
    # records give (makedefs.c's adjust_qt_hdrs(): the headers, then the text)
    for msgs in classes:
        for _, _, off, size in msgs:
            if not (text_start <= off and off + size <= len(data)):
                sys.exit("quest: a message at %d+%d outside the text" % (off, size))
    c64_hdr = struct.calcsize(C64_INT) + (LEN_HDR + 4) * n_hdr
    c64_offsets, at = [], c64_hdr
    for msgs in classes:
        c64_offsets.append(at)
        at += struct.calcsize(C64_INT) + struct.calcsize(C64_QTMSG) * len(msgs)
    shift = at - text_start
    out = bytearray(struct.pack(C64_INT, c64_int(n_hdr, "n_hdr")))
    for i in ids:
        out += i
    for o in c64_offsets:
        out += struct.pack("<l", o)
    for msgs in classes:
        out += struct.pack(C64_INT, c64_int(len(msgs), "n_msg"))
        for num, delivery, off, size in msgs:
            out += struct.pack(C64_QTMSG, c64_int(num, "msgnum"), delivery, off + shift, size)
    assert len(out) == at
    out += data[text_start:]
    return bytes(out)


# ---- the special levels (sp_lev.c's load_special(), sp_lev.h; lev_comp writes them) ----
# Only these change layout: the long flags; monster, object, engraving and lev_region (a
# Str_or_Len union, a pointer on the host); gold (an int). Everything else is chars and
# shorts, the same on both. The host's padding is explicit in each format.
HOST_MONSTER, C64_MONSTER = "<i4xi4xhb5b2b6x", "<hhhb5b2b"	# name, appear_as: len in the union
HOST_OBJECT, C64_OBJECT = "<i4xihh5bb2x", "<hhhh5bb"
HOST_ENGR, C64_ENGR = "<2b6xi4xb7x", "<2bhb"
HOST_LREGION, C64_LREGION = "<12b4xi4x", "<12bh"
HOST_GOLD, C64_GOLD = "<2b2xi", "<2bh"


class Lev:
    def __init__(self, data):
        self.r, self.out = Reader(data), bytearray()

    def copy(self, n):
        self.out += self.r.take("<%ds" % n)[0]

    def byte(self, signed=False):
        (v,) = self.r.take("<b" if signed else "<B")
        self.out += struct.pack("<b" if signed else "<B", v)
        return v

    def conv(self, hfmt, cfmt, strings=()):
        v = list(self.r.take(hfmt))
        self.out += struct.pack(cfmt, *v)	# struct.error if a host int does not fit
        for i in strings:		# the union's length, then that many bytes
            self.copy(v[i])
        return v

    def common(self):
        self.copy(8)				# lev_init
        (flags,) = self.r.take("<q")		# long lev_flags
        self.out += struct.pack("<l", flags)
        n = self.byte()				# uchar: the message's length
        self.copy(n)

    def list_of(self, size):
        n = self.byte(True)			# char n
        for _ in range(max(n, 0)):
            self.copy(size)
        return n

    def monsters(self):
        n = self.byte(True)
        for _ in range(max(n, 0)):
            self.conv(HOST_MONSTER, C64_MONSTER, strings=(0, 1))

    def objects(self):
        n = self.byte(True)
        for _ in range(max(n, 0)):
            self.conv(HOST_OBJECT, C64_OBJECT, strings=(0,))

    def golds(self):
        n = self.byte(True)
        for _ in range(max(n, 0)):
            self.conv(HOST_GOLD, C64_GOLD)

    def engravings(self):
        n = self.byte(True)
        for _ in range(max(n, 0)):
            self.conv(HOST_ENGR, C64_ENGR, strings=(2,))

    def rooms(self):
        self.common()
        self.list_of(1)				# robjects
        self.list_of(1)				# rmonst
        nrooms = self.byte(True)		# xchar
        for _ in range(nrooms):
            for _ in range(2):			# name, parent: short size, then the bytes
                (size,) = self.r.take("<h")
                self.out += struct.pack("<h", size)
                if size > 0:
                    self.copy(size)
            self.copy(10)			# x, y, w, h, xalign, yalign, rtype, chance, rlit, filled
            self.list_of(4)			# room_door
            self.list_of(3)			# stair
            self.list_of(4)			# altar
            self.list_of(2)			# fountain
            self.list_of(2)			# sink
            self.list_of(2)			# pool
            self.list_of(4)			# sp_trap
            self.monsters()
            self.objects()
            self.golds()
            self.engravings()
        self.list_of(6)				# corridors (xchar ncorr)

    def maze(self):
        self.common()
        self.byte(True)				# schar filling
        numpart = self.byte(True)		# char numpart
        for _ in range(numpart):
            self.byte(True)			# halign
            self.byte(True)			# valign
            xsize = self.byte(True)
            ysize = self.byte(True)
            if not (self.init_present and xsize <= 1 and ysize <= 1):
                self.copy(xsize * ysize)	# the map
            n = self.byte(True)			# lev_regions
            for _ in range(max(n, 0)):
                self.conv(HOST_LREGION, C64_LREGION, strings=(12,))
            self.list_of(1)			# robjects
            n = self.byte(True)			# rloc_x[n], rloc_y[n]
            self.copy(2 * max(n, 0))
            self.list_of(1)			# rmonst
            self.list_of(7)			# region
            self.list_of(3)			# door
            self.list_of(4)			# drawbridge
            self.list_of(3)			# walk
            self.list_of(4)			# dig
            self.list_of(4)			# pass
            self.list_of(3)			# lad
            self.list_of(3)			# stair
            self.list_of(4)			# altar
            self.list_of(2)			# fountain
            self.list_of(4)			# sp_trap
            self.monsters()
            self.objects()
            self.golds()
            self.engravings()

    def convert(self):
        self.out += struct.pack(C64_VERSION, *[v & 0xFFFFFFFF for v in self.r.take(HOST_VERSION)])
        kind = self.byte()			# char: SP_LEV_ROOMS 1, SP_LEV_MAZE 2
        self.init_present = self.r.d[self.r.p]	# lev_init's first field, next
        if kind == 1:
            self.rooms()
        elif kind == 2:
            self.maze()
        else:
            sys.exit("lev: kind %d" % kind)
        if self.r.p != len(self.r.d):
            sys.exit("lev: %d bytes left at the end" % (len(self.r.d) - self.r.p))
        return bytes(self.out)


def lev(data):
    return Lev(data).convert()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("kind", choices=("dungeon", "quest", "lev"))
    ap.add_argument("host_file")
    ap.add_argument("out")
    a = ap.parse_args()
    data = open(a.host_file, "rb").read()
    out = {"dungeon": dungeon, "quest": quest, "lev": lev}[a.kind](data)
    open(a.out, "wb").write(out)
    print("%s: %d -> %d bytes" % (a.kind, len(data), len(out)))


if __name__ == "__main__":
    main()
