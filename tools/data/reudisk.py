#!/usr/bin/env python3
"""reudisk.py - the REU RAM disk's image: the game's data files as sys/c64/c64sys.c reads them.

usage: tools/data/reudisk.py OUT.img NAME=PATH [NAME=PATH ...]
       tools/data/reudisk.py --list IMG

The disk is the REU's top 2 MB (a 4 MB REU, ADR-0008's amendment of 2026-11-22): 512 blocks
of 4 KB. Blocks 0 and 1 are the directory, 256 entries of 32 bytes (the name, NUL-padded, 24
bytes; the size, 4, low byte first; the first block, 2; in use, 1; one spare); block 2 the
allocation table, 2 bytes a block (0 free, $FFFF the last block of a file, otherwise the
next block); blocks 0 to 2 are marked as last. Each file here takes consecutive blocks.
tools/bank/c128_images.py --disk puts the image at the REU's 2 MB.
"""
import argparse
import struct
import sys

BLK, NBLK, NDIR, DIRSZ, NAMESZ, END, FATBLK = 4096, 512, 256, 32, 24, 0xFFFF, 2


def build(files):
    img = bytearray(BLK * NBLK)
    fat = [0] * NBLK
    fat[0] = fat[1] = fat[2] = END
    nxt = 3
    if len(files) > NDIR:
        sys.exit("more than %d files" % NDIR)
    for i, (name, data) in enumerate(files):
        nb = name.encode("latin-1")
        if len(nb) >= NAMESZ:
            sys.exit("%s: the name is longer than %d" % (name, NAMESZ - 1))
        blocks = list(range(nxt, nxt + max(1, (len(data) + BLK - 1) // BLK))) if data else []
        if blocks and blocks[-1] >= NBLK:
            sys.exit("the files do not fit %d KB" % (BLK * NBLK // 1024))
        for k, b in enumerate(blocks):
            fat[b] = blocks[k + 1] if k + 1 < len(blocks) else END
            img[b * BLK:b * BLK + len(data[k * BLK:(k + 1) * BLK])] = data[k * BLK:(k + 1) * BLK]
        nxt += len(blocks)
        first = blocks[0] if blocks else END
        img[i * DIRSZ:(i + 1) * DIRSZ] = nb.ljust(NAMESZ, b"\0") + struct.pack("<LHBx", len(data), first, 1)
    img[FATBLK * BLK:FATBLK * BLK + 2 * NBLK] = struct.pack("<%dH" % NBLK, *fat)
    return img, nxt


def listing(img):
    fat = struct.unpack_from("<%dH" % NBLK, img, FATBLK * BLK)
    for i in range(NDIR):
        e = img[i * DIRSZ:(i + 1) * DIRSZ]
        if not e[30]:
            continue
        name = e[:NAMESZ].split(b"\0")[0].decode("latin-1")
        size, first = struct.unpack_from("<LH", e, NAMESZ)
        n, b = 0, first
        while b != END and n < NBLK:
            n += 1
            b = fat[b]
        print("%-24s %8d B  %3d blocks from %d" % (name, size, n, first if first != END else -1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", action="store_true", help="list an image's files")
    ap.add_argument("out")
    ap.add_argument("files", nargs="*", metavar="NAME=PATH")
    a = ap.parse_args()
    if a.list:
        listing(open(a.out, "rb").read())
        return
    files = []
    for f in a.files:
        name, _, path = f.partition("=")
        files.append((name, open(path, "rb").read()))
    img, used = build(files)
    open(a.out, "wb").write(img)
    print("%s: %d files, %d of %d blocks (%d KB free)" % (a.out, len(files), used, NBLK,
                                                          (NBLK - used) * BLK // 1024))


if __name__ == "__main__":
    main()
