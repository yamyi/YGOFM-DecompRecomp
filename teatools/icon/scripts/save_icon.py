#!/usr/bin/env python3
"""save_icon.py -- offline clone of TEA-Online "Icon" (extend/tools/icon).

Edits the PS1 memory-card save header (the standard "title frame" block) that
ships inside SLUS_014.11 at file offset 0x1C4800 = RAM 0x801D4000 (decomp
`D_801D4000`), plus the memory-card file name at file 0xB84 = RAM 0x80010384
(decomp `D_80010384`, stock "BASLUS-01411-YUGIOH").

Title frame (Sony's format, all offsets relative to 0x1C4800):

  +0x00  "SC"          magic
  +0x02  0x13          icon flag: 0x11 = 1 frame, 0x12 = 2, 0x13 = 3 frames
  +0x03  0x01          blocks used by the save
  +0x04  64 B          title, 32 full-width Shift-JIS characters
  +0x44  28 B          reserved (zero in the stock file)
  +0x60  16 x u16      CLUT, BGR555 little-endian (bit15 = STP)
  +0x80  3 x 128 B     icon frames, 16x16 4bpp, low nibble = LEFT pixel

The site only ever rewrites the title (+0x04), the CLUT (+0x60), the three
frames (+0x80) and 10 bytes of the file name; it never touches the icon flag,
so a save written by a patched EXE always animates 3 frames.

Usage:
  save_icon.py dump    SLUS PREFIX          # PREFIX.png (48x16, 3 frames) + report
  save_icon.py import  SLUS in.png [-o OUT] [--title T] [--code SLUS-01411] [--frames N]
                                            # PNG must be 16x16, 32x16 or 48x16
  save_icon.py restore SLUS STOCK [-o OUT]
  save_icon.py check   SLUS                 # print header, title, CLUT, file name
"""
import argparse, sys
from PIL import Image

HDR = 0x1C4800          # RAM 0x801D4000
FLAG = HDR + 2
TITLE = HDR + 4         # 64 bytes, RAM 0x801D4004  (site constant 1853444)
CLUT = HDR + 0x60       # 32 bytes, RAM 0x801D4060  (site constant 1853536)
FRAMES = HDR + 0x80     # 384 bytes, RAM 0x801D4080 (site constant 1853568)
NAME = 0xB84            # "BASLUS-01411-YUGIOH", RAM 0x80010384
CODE = 0xB86            # the "SLUS-01411" part the site rewrites (site constant 2950)

# The site's character table (Vue object X): ASCII -> full-width Shift-JIS.
# Anything not listed becomes a full-width space (0x8140).
SJIS = {}
for i, ch in enumerate('abcdefghijklmnopqrstuvwxyz'):
    SJIS[ch] = bytes([0x82, 0x81 + i])
for i, ch in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    SJIS[ch] = bytes([0x82, 0x60 + i])
for i, ch in enumerate('0123456789'):
    SJIS[ch] = bytes([0x82, 0x4F + i])
SJIS.update({'+': b'\x81\x7b', '-': b'\x81\x7c', '*': b'\x81\x96', '/': b'\x81\x5e',
             '&': b'\x81\x95', '$': b'\x81\x90', '%': b'\x81\x93', '!': b'\x81\x49',
             '?': b'\x81\x48', '.': b'\x81\x44', ':': b'\x81\x46', ' ': b'\x81\x40'})
UNSJIS = {v: k for k, v in SJIS.items()}


def to_sjis(s):
    """32 characters, space padded, exactly what the site's setBytesWithTable writes."""
    s = (s[:32] + ' ' * 32)[:32]
    return b''.join(SJIS.get(c, b'\x81\x40') for c in s)


def from_sjis(b):
    return ''.join(UNSJIS.get(bytes(b[2 * i:2 * i + 2]), '?') for i in range(32))


def psx_to_rgba(v):
    if v == 0:
        return (0, 0, 0, 0)
    return ((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3, 255)


def rgba_to_psx(r, g, b, a):
    """The site's setNewHeader16(): pure black becomes (1,1,1) so it stays opaque,
    and every non-black entry gets STP (bit15) set."""
    if (r | g | b) == 0:
        if a == 0:
            return 0
        r = g = b = 1
    v = (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)
    return v | 0x8000


def quantise(im, ncol=16, keep_black=True):
    """The site's ImageConverter: 5-bit channels, opaque black -> (8,8,8), palette
    = the ncol most frequent colours sorted by RGB value, nearest-colour mapping."""
    im = im.convert('RGBA')
    w, h = im.size
    px = im.load()
    cells = [[None] * w for _ in range(h)]
    hist = {}
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            r, g, b = r & ~7, g & ~7, b & ~7
            a = 0 if a == 0 else 255
            if keep_black and a == 255 and (r | g | b) == 0:
                r = g = b = 8
            cells[y][x] = (r, g, b, a)
            e = hist.get((r, g, b))
            if e is None:
                hist[(r, g, b)] = [1, (r, g, b, a)]
            else:
                e[0] += 1
    ent = sorted(hist.values(), key=lambda e: -e[0])[:ncol]
    while len(ent) < ncol:
        ent.append(ent[0])
    pal = sorted((e[1] for e in ent), key=lambda c: (c[0] << 16) | (c[1] << 8) | c[2])
    clear = next((i for i, c in enumerate(pal) if c[3] == 0), 0)
    idx = [[0] * w for _ in range(h)]
    cache = {}
    for y in range(h):
        for x in range(w):
            c = cells[y][x]
            n = cache.get(c)
            if n is None:
                if c[3] == 0:
                    n = clear
                else:
                    n, bd = 0, 1 << 30
                    for i, p in enumerate(pal):
                        if p[3] == 0:
                            continue
                        dd = (c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2 + (c[2] - p[2]) ** 2
                        if dd < bd:
                            n, bd = i, dd
                    cache[c] = n
                cache[c] = n
            idx[y][x] = n
    if len(hist) > ncol:
        print('quantised %d colours down to %d' % (len(hist), ncol))
    return pal, idx


def report(d):
    flag = d[FLAG]
    print('magic      %r' % d[HDR:HDR + 2])
    print('icon flag  0x%02X (%d frame%s)' % (flag, flag & 0xF, '' if (flag & 0xF) == 1 else 's'))
    print('blocks     %d' % d[HDR + 3])
    print('title      %r' % from_sjis(d[TITLE:TITLE + 64]))
    print('title raw  %s' % d[TITLE:TITLE + 64].hex(' '))
    print('reserved   %s' % ('all zero' if d[HDR + 0x44:HDR + 0x60] == b'\0' * 28 else 'NOT zero'))
    pal = [int.from_bytes(d[CLUT + 2 * i:CLUT + 2 * i + 2], 'little') for i in range(16)]
    print('CLUT       %s' % ' '.join('%04X' % v for v in pal))
    print('file name  %r' % d[NAME:NAME + 19].decode('ascii', 'replace'))


def dump(args):
    d = open(args.slus, 'rb').read()
    report(d)
    pal = [psx_to_rgba(int.from_bytes(d[CLUT + 2 * i:CLUT + 2 * i + 2], 'little')) for i in range(16)]
    im = Image.new('RGBA', (48, 16))
    px = im.load()
    for f in range(3):
        for y in range(16):
            row = FRAMES + 128 * f + 8 * y
            for x in range(8):
                v = d[row + x]
                px[16 * f + 2 * x, y] = pal[v & 15]
                px[16 * f + 2 * x + 1, y] = pal[v >> 4]
    out = args.prefix if args.prefix.endswith('.png') else args.prefix + '.png'
    im.save(out)
    print('wrote', out, '(48x16, three 16x16 frames side by side)')


def import_(args):
    d = bytearray(open(args.slus, 'rb').read())
    im = Image.open(args.png).convert('RGBA')
    if im.size[1] != 16 or im.size[0] not in (16, 32, 48):
        sys.exit('image must be 16x16, 32x16 or 48x16, got %dx%d' % im.size)
    nfr = im.size[0] // 16
    pal, idx = quantise(im, 16)
    for i, c in enumerate(pal):
        d[CLUT + 2 * i:CLUT + 2 * i + 2] = rgba_to_psx(*c).to_bytes(2, 'little')
    for f in range(3):
        src = min(f, nfr - 1)          # fewer than 3 frames -> repeat the last one
        for y in range(16):
            row = FRAMES + 128 * f + 8 * y
            line = idx[y]
            for x in range(8):
                d[row + x] = line[16 * src + 2 * x] | (line[16 * src + 2 * x + 1] << 4)
    if args.title is not None:
        d[TITLE:TITLE + 64] = to_sjis(args.title)
    if args.code:
        c = args.code.upper()
        if len(c) != 10 or c[4] != '-' or not c[5:].isdigit():
            sys.exit('--code must look like SLUS-01411')
        d[CODE:CODE + 10] = c.encode()
    if args.frames:
        if args.frames not in (1, 2, 3):
            sys.exit('--frames must be 1..3')
        d[FLAG] = 0x10 | args.frames
    out = args.out or args.slus
    open(out, 'wb').write(d)
    print('wrote', out)


def restore(args):
    d = bytearray(open(args.slus, 'rb').read())
    s = open(args.stock, 'rb').read()
    if len(s) != len(d):
        sys.exit('stock file has a different size')
    d[HDR:HDR + 0x200] = s[HDR:HDR + 0x200]
    d[NAME:NAME + 20] = s[NAME:NAME + 20]
    out = args.out or args.slus
    open(out, 'wb').write(d)
    print('restored', out)


def check(args):
    report(open(args.slus, 'rb').read())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('dump'); p.add_argument('slus'); p.add_argument('prefix'); p.set_defaults(f=dump)
    p = sp.add_parser('import'); p.add_argument('slus'); p.add_argument('png')
    p.add_argument('-o', '--out'); p.add_argument('--title')
    p.add_argument('--code', help='e.g. SLUS-01411')
    p.add_argument('--frames', type=int, help='1..3, rewrites the icon flag (the site never does)')
    p.set_defaults(f=import_)
    p = sp.add_parser('restore'); p.add_argument('slus'); p.add_argument('stock')
    p.add_argument('-o', '--out'); p.set_defaults(f=restore)
    p = sp.add_parser('check'); p.add_argument('slus'); p.set_defaults(f=check)
    a = ap.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
