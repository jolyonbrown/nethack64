#!/usr/bin/env python3
"""
vice.py - drive VICE through its binary monitor, for humans and agents.

The point of this tool is a tight, scriptable loop:
    build -> launch/reload in VICE -> type keys -> read the screen as TEXT
    -> (optionally) take a PNG screenshot -> inspect memory -> repeat
without anyone touching the VICE window.

The 80-column screen is a bitmap, so "reading the screen" means reading the
program's shadow text buffer (label s80_text from the Oscar64 .lbl file).
For ordinary 40-column text mode it reads screen RAM at $0400.

Protocol: VICE binary monitor (VICE >= 3.5), see docs/VICE-AUTOMATION.md.
Every command pauses emulation; this tool resumes it afterwards unless
--stay-paused is given.

Quick reference
  vice.py launch --crt build/nethack-ef.crt --reu 512 [--headless] [--warp]
  vice.py launch --prg build/nethack.prg
  vice.py ping
  vice.py keys "lljjh"            # typed into the KERNAL keyboard buffer
  vice.py screen                  # 80x25 text from s80_text (default .lbl: newest in build/)
  vice.py screen --text40         # 40x25 text from $0400
  vice.py screenshot out.png
  vice.py mem 0xc000 64           # hex dump
  vice.py sym s80_text            # address of a label
  vice.py regs
  vice.py reset | resume | quit
  vice.py wait-text "AUTOTEST PASS" --timeout 20
"""
import argparse
import glob
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time
import zlib

HOST = "127.0.0.1"
DEFAULT_PORT = 6502

CMD_MEM_GET = 0x01
CMD_MEM_SET = 0x02
CMD_CHECKPOINT_SET = 0x12
CMD_REGISTERS_GET = 0x31
CMD_KEYBOARD_FEED = 0x72
CMD_PING = 0x81
CMD_REGISTERS_AVAILABLE = 0x83
CMD_DISPLAY_GET = 0x84
CMD_VICE_INFO = 0x85
CMD_PALETTE_GET = 0x91
CMD_EXIT = 0xAA
CMD_QUIT = 0xBB
CMD_RESET = 0xCC
CMD_AUTOSTART = 0xDD

EVENT_ID = 0xFFFFFFFF

# "Pepto" PAL palette, used if VICE's palette query is unavailable
PEPTO = [
    (0x00, 0x00, 0x00), (0xFF, 0xFF, 0xFF), (0x68, 0x37, 0x2B), (0x70, 0xA4, 0xB2),
    (0x6F, 0x3D, 0x86), (0x58, 0x8D, 0x43), (0x35, 0x28, 0x79), (0xB8, 0xC7, 0x6F),
    (0x6F, 0x4F, 0x25), (0x43, 0x39, 0x00), (0x9A, 0x67, 0x59), (0x44, 0x44, 0x44),
    (0x6C, 0x6C, 0x6C), (0x9A, 0xD2, 0x84), (0x6C, 0x5E, 0xB5), (0x95, 0x95, 0x95),
]


class ViceError(Exception):
    pass


class Vice:
    def __init__(self, port=DEFAULT_PORT, timeout=10.0):
        self.port = port
        self.sock = socket.create_connection((HOST, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.reqid = 1

    def close(self):
        self.sock.close()

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ViceError("connection closed by VICE")
            buf += chunk
        return buf

    def _read_response(self):
        hdr = self._recv_exact(12)
        if hdr[0] != 0x02:
            raise ViceError("bad response header %r" % hdr)
        length, rtype, err, rid = struct.unpack("<IBBI", hdr[2:12])
        body = self._recv_exact(length)
        return rtype, err, rid, body

    def cmd(self, ctype, body=b""):
        rid = self.reqid
        self.reqid += 1
        pkt = struct.pack("<BBIIB", 0x02, 0x02, len(body), rid, ctype) + body
        self.sock.sendall(pkt)
        while True:
            rtype, err, got, rbody = self._read_response()
            if got == EVENT_ID:
                continue  # stopped/resumed/checkpoint events
            if got != rid:
                continue
            if err:
                raise ViceError("command 0x%02x failed, error 0x%02x" % (ctype, err))
            return rtype, rbody

    # --- commands ------------------------------------------------------------
    def ping(self):
        self.cmd(CMD_PING)

    def resume(self):
        self.cmd(CMD_EXIT)

    def mem_get(self, start, length, side_effects=False, bank=0):
        out = b""
        while length > 0:
            n = min(length, 0x8000)
            end = start + n - 1
            body = struct.pack("<BHHBH", 1 if side_effects else 0, start, end, 0, bank)
            _, rb = self.cmd(CMD_MEM_GET, body)
            (ml,) = struct.unpack("<H", rb[:2])
            out += rb[2:2 + (ml or 0x10000)]
            start += n
            length -= n
        return out

    def mem_set(self, start, data, bank=0):
        body = struct.pack("<BHHBH", 0, start, start + len(data) - 1, 0, bank) + bytes(data)
        self.cmd(CMD_MEM_SET, body)

    def keys(self, text):
        data = ascii_to_petscii(text)
        for i in range(0, len(data), 8):  # KERNAL buffer holds 10; stay well under
            chunk = data[i:i + 8]
            self.cmd(CMD_KEYBOARD_FEED, bytes([len(chunk)]) + chunk)
            self.resume()
            time.sleep(0.15)

    def registers(self):
        _, avail = self.cmd(CMD_REGISTERS_AVAILABLE, b"\x00")
        names = {}
        (count,) = struct.unpack("<H", avail[:2])
        p = 2
        for _ in range(count):
            size = avail[p]
            rid = avail[p + 1]
            nlen = avail[p + 3]
            names[rid] = avail[p + 4:p + 4 + nlen].decode()
            p += size + 1
        _, rb = self.cmd(CMD_REGISTERS_GET, b"\x00")
        (count,) = struct.unpack("<H", rb[:2])
        p = 2
        regs = {}
        for _ in range(count):
            size = rb[p]
            rid = rb[p + 1]
            (val,) = struct.unpack("<H", rb[p + 2:p + 4])
            regs[names.get(rid, str(rid))] = val
            p += size + 1
        return regs

    def display(self):
        _, rb = self.cmd(CMD_DISPLAY_GET, b"\x01\x00")
        (fl,) = struct.unpack("<I", rb[:4])
        dw, dh, xo, yo, iw, ih, bpp = struct.unpack("<HHHHHHB", rb[4:4 + 13])
        p = 4 + fl
        (bl,) = struct.unpack("<I", rb[p:p + 4])
        pixels = rb[p + 4:p + 4 + bl]
        return dw, dh, xo, yo, iw, ih, pixels

    def palette(self):
        try:
            _, rb = self.cmd(CMD_PALETTE_GET, b"\x01")
        except ViceError:
            return PEPTO
        (count,) = struct.unpack("<H", rb[:2])
        p = 2
        pal = []
        for _ in range(count):
            size = rb[p]
            pal.append(tuple(rb[p + 1:p + 4]))
            p += size + 1
        return pal

    def reset(self, hard=False):
        self.cmd(CMD_RESET, b"\x01" if hard else b"\x00")

    def autostart(self, path, run=True):
        name = os.path.abspath(path).encode()
        self.cmd(CMD_AUTOSTART, struct.pack("<BHB", 1 if run else 0, 0, len(name)) + name)

    def quit(self):
        try:
            self.cmd(CMD_QUIT)
        except (ViceError, OSError):
            pass


# --- helpers -----------------------------------------------------------------

def ascii_to_petscii(text):
    out = bytearray()
    text = text.replace("\\n", "\n")
    for ch in text:
        c = ord(ch)
        if ch == "\n":
            out.append(13)
        elif 97 <= c <= 122:      # a-z -> unshifted PETSCII letters
            out.append(c - 32)
        elif 65 <= c <= 90:       # A-Z -> shifted letters
            out.append(c + 128)
        elif ch == "\x1b":
            out.append(3)         # RUN/STOP
        else:
            out.append(c & 0x7F)
    return bytes(out)


def screencode_to_ascii(b):
    b &= 0x7F
    if b == 0:
        return "@"
    if 1 <= b <= 26:
        return chr(b + 96)
    if 32 <= b <= 63:
        return chr(b)
    if 65 <= b <= 90:
        return chr(b)
    return "."


def session_file(port):
    return os.path.join("build", ".vice-session-%d.json" % port)


def find_lbl(explicit=None, port=DEFAULT_PORT):
    """Label file: --lbl, else the one next to the image `launch` booted,
    else the newest build/*.lbl."""
    if explicit:
        return explicit
    try:
        with open(session_file(port)) as f:
            lbl = json.load(f).get("lbl")
        if lbl and os.path.exists(lbl):
            return lbl
    except (OSError, ValueError):
        pass
    cands = sorted(glob.glob("build/*.lbl"), key=os.path.getmtime, reverse=True)
    if not cands:
        raise SystemExit("no .lbl file found in build/ (build first or pass --lbl)")
    return cands[0]


def load_labels(path):
    labels = {}
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) == 3 and parts[0] == "al":
                labels[parts[2].lstrip(".")] = int(parts[1], 16)
    return labels


def write_png(path, width, height, rgb_rows):
    raw = b"".join(b"\x00" + bytes(row) for row in rgb_rows)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def wait_port(port, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            s = socket.create_connection((HOST, port), timeout=1)
            s.close()
            return True
        except OSError:
            time.sleep(0.25)
    return False


# --- CLI ---------------------------------------------------------------------

def cmd_launch(a):
    vice = a.vice or os.environ.get("VICE", "x64sc")
    args = [vice, "-binarymonitor", "-binarymonitoraddress", "ip4://127.0.0.1:%d" % a.port,
            "+sound"]
    if a.default:
        args.insert(1, "-default")
    if a.warp:
        args.append("-warp")
    if a.reu:
        args += ["-reu", "-reusize", str(a.reu)]
    if a.debugcart:
        args.append("-debugcart")
    if a.crt:
        args += ["-cartcrt", os.path.abspath(a.crt)]
    if a.prg:
        args += ["-autostartprgmode", "1", "-autostart", os.path.abspath(a.prg)]
    args += a.extra or []
    if a.headless:
        if shutil.which("xvfb-run") is None:
            raise SystemExit("--headless needs xvfb-run (or a VICE built with --enable-headlessui)")
        args = ["xvfb-run", "-a"] + args
    log = open(a.log, "w") if a.log else subprocess.DEVNULL
    proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    if not wait_port(a.port, a.timeout):
        proc.terminate()
        raise SystemExit("VICE did not open the binary monitor on port %d" % a.port)
    image = a.crt or a.prg
    lbl = os.path.splitext(image)[0] + ".lbl" if image else None
    try:
        os.makedirs("build", exist_ok=True)
        with open(session_file(a.port), "w") as f:
            json.dump({"pid": proc.pid, "image": image,
                       "lbl": lbl if lbl and os.path.exists(lbl) else None}, f)
    except OSError:
        pass
    print("VICE pid %d, binary monitor on %d%s" % (proc.pid, a.port,
          ", labels from %s" % lbl if lbl and os.path.exists(lbl) else ""))


def screen_text(v, a):
    if a.text40:
        data = v.mem_get(0x0400, 1000)
        rows = ["".join(screencode_to_ascii(b) for b in data[r * 40:(r + 1) * 40]) for r in range(25)]
    else:
        lblfile = find_lbl(a.lbl, a.port)
        labels = load_labels(lblfile)
        if a.label not in labels:
            raise SystemExit("label %s not in %s" % (a.label, lblfile))
        data = v.mem_get(labels[a.label], a.cols * a.rows)
        rows = []
        for r in range(a.rows):
            line = data[r * a.cols:(r + 1) * a.cols]
            rows.append("".join(chr(b) if 32 <= b < 127 else "?" for b in line))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=int(os.environ.get("VICE_PORT", DEFAULT_PORT)))
    ap.add_argument("--stay-paused", action="store_true", help="do not resume emulation afterwards")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("launch")
    p.add_argument("--crt"); p.add_argument("--prg")
    p.add_argument("--reu", type=int, default=0, help="REU size in KB (0 = none)")
    p.add_argument("--headless", action="store_true")
    p.add_argument("--warp", action="store_true")
    p.add_argument("--debugcart", action="store_true")
    p.add_argument("--default", action="store_true", default=True,
                   help="ignore the user's vicerc (default on)")
    p.add_argument("--vice"); p.add_argument("--log")
    p.add_argument("--timeout", type=float, default=20)
    p.add_argument("extra", nargs="*", help="extra VICE args after --")

    sub.add_parser("ping"); sub.add_parser("resume"); sub.add_parser("quit")
    sub.add_parser("regs")
    p = sub.add_parser("reset"); p.add_argument("--hard", action="store_true")
    p = sub.add_parser("keys"); p.add_argument("text")
    p = sub.add_parser("load"); p.add_argument("path")
    for name in ("screen", "wait-text"):
        p = sub.add_parser(name)
        p.add_argument("--lbl"); p.add_argument("--label", default="s80_text")
        p.add_argument("--cols", type=int, default=80); p.add_argument("--rows", type=int, default=25)
        p.add_argument("--text40", action="store_true")
        if name == "wait-text":
            p.add_argument("text"); p.add_argument("--timeout", type=float, default=20)
    p = sub.add_parser("screenshot"); p.add_argument("out")
    p = sub.add_parser("mem"); p.add_argument("addr"); p.add_argument("length")
    p = sub.add_parser("poke"); p.add_argument("addr"); p.add_argument("bytes", nargs="+")
    p = sub.add_parser("sym"); p.add_argument("name"); p.add_argument("--lbl")
    a = ap.parse_args()

    if a.cmd == "launch":
        return cmd_launch(a)
    if a.cmd == "sym":
        labels = load_labels(find_lbl(a.lbl, a.port))
        print("%s = $%04x" % (a.name, labels[a.name]))
        return

    v = Vice(a.port)
    try:
        if a.cmd == "ping":
            v.ping(); print("pong")
        elif a.cmd == "quit":
            v.quit(); return
        elif a.cmd == "resume":
            pass
        elif a.cmd == "reset":
            v.reset(a.hard)
        elif a.cmd == "load":
            v.autostart(a.path)
        elif a.cmd == "keys":
            v.keys(a.text)
        elif a.cmd == "regs":
            for k, val in v.registers().items():
                print("%-4s %04x" % (k, val))
        elif a.cmd == "screen":
            for row in screen_text(v, a):
                print(row.rstrip())
        elif a.cmd == "wait-text":
            t0 = time.time()
            while True:
                rows = screen_text(v, a)
                if any(a.text in r for r in rows):
                    print("\n".join(r.rstrip() for r in rows))
                    break
                v.resume()
                if time.time() - t0 > a.timeout:
                    print("\n".join(r.rstrip() for r in rows))
                    raise SystemExit("timed out waiting for %r" % a.text)
                time.sleep(0.5)
        elif a.cmd == "screenshot":
            dw, dh, xo, yo, iw, ih, px = v.display()
            pal = v.palette()
            rows = []
            for y in range(ih):
                base = (yo + y) * dw + xo
                rows.append(b"".join(bytes(pal[c % len(pal)]) for c in px[base:base + iw]))
            write_png(a.out, iw, ih, rows)
            print("wrote %s (%dx%d)" % (a.out, iw, ih))
        elif a.cmd == "mem":
            addr = int(a.addr, 0); n = int(a.length, 0)
            data = v.mem_get(addr, n)
            for i in range(0, len(data), 16):
                chunk = data[i:i + 16]
                print("%04x  %-48s %s" % (addr + i, " ".join("%02x" % b for b in chunk),
                      "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)))
        elif a.cmd == "poke":
            v.mem_set(int(a.addr, 0), [int(b, 0) for b in a.bytes])
        if not a.stay_paused and a.cmd != "quit":
            v.resume()
    finally:
        v.close()


if __name__ == "__main__":
    main()
