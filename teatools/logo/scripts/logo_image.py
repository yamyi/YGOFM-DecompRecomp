#!/usr/bin/env python3
"""logo_image.py -- offline clone of TEA-Online "Main Logo" (extend/tools/logo).

The "Yu-Gi-Oh! Forbidden Memories" title picture exists twice on the disc, as an
8bpp foreground texture + a 4bpp hieroglyph wallpaper + two CLUTs + a sprite
list that assembles the foreground out of 7 quads:

  SU.MRG      "Main image"      (boot / title screen)
     front  0x10000 (0x10000 B)   CLUT 0x30200 (256 x u16)
     back   0x28000 (0x08000 B)   CLUT 0x30800 (16 x u16)
     sprite block 0x39000, logo group at +0x23A  (file 0x3923A)
  WA_MRG.MRG  "Prologue image"  (the same picture after the prologue)
     front  0xFD3800             CLUT 0xFEB800
     back   0xFE3800             CLUT 0xFEBA00
     sprite blocks 0xFD3000 (logo group at +0x12E = 0xFD312E)
                   0xFEC000 (logo group at +0x12A = 0xFEC12A)

Texture layout (both copies)
  front: an 8bpp 256x256 texture stored as TWO 128-byte-wide column strips --
         file rows   0..255 = texture x   0..127
         file rows 256..511 = texture x 128..255
         so file offset = 0x8000*(u >= 128) + 128*v + (u & 127).
         Only 320x168 of it is the logo; the rest holds the copyright line
         (texture x 0..127, y 208..239) and "PUSH START BUTTON" (x 128..255,
         y 128..175), which this tool does not touch.
  back:  4bpp, 128 bytes/row, 256 rows = 256x256, low nibble = left pixel.
  CLUT:  u16 little-endian BGR555, bit15 = STP.  0x0000 = fully transparent.

The 6 chunks the site exposes as a 320x168 canvas (data coords are in the
128x512 "stacked strips" view, which is what --raw prints):

  data(  0,  0) 128x168 -> canvas(  0,  0)    data(  0,168) 128x40 -> (128,128)
  data(  0,256) 128x128 -> canvas(128,  0)    data(  0,432)  64x80 -> (256, 56)
  data( 64,424)  64x56  -> canvas(256,  0)    data( 64,480)  64x32 -> (256,136)

Usage:
  logo_image.py dump    FILE.MRG PREFIX            # PREFIX_front.png 320x168,
                                                   # PREFIX_raw.png 128x512,
                                                   # PREFIX_back.png 256x256
  logo_image.py import  FILE.MRG [-o OUT] [--front f.png] [--back b.png] [--no-fix]
  logo_image.py restore FILE.MRG STOCK.MRG [-o OUT]
  logo_image.py sprites FILE.MRG [--at 0xADDR]     # decode a sprite block
  logo_image.py check   FILE.MRG                   # stock bytes / fix applied?

FILE.MRG may be SU.MRG or WA_MRG.MRG; the layout is picked by file size.
"""
import argparse, sys
from PIL import Image

# (data_x, data_y, w, h, canvas_x, canvas_y) in the 128x512 stacked-strip view
CHUNKS = [(0, 0, 128, 168, 0, 0), (0, 168, 128, 40, 128, 128), (0, 256, 128, 128, 128, 0),
          (0, 432, 64, 80, 256, 56), (64, 424, 64, 56, 256, 0), (64, 480, 64, 32, 256, 136)]

# The site's "fix": the stock 7-sprite group leaves the right-hand 64px column
# only partially covered (sprite 1 is 64x32 at y=24 instead of 64x56 at y=0, and
# sprite 3 is 56 wide instead of 64), so a full-bleed replacement image would be
# cropped there.  These 46 bytes make the 7 quads tile 320x168 exactly.
FIX = bytes([7, 16, 0, 0,
             0, 128, 0, 2, 224, 9,      # (  0,128) 128x40  uv(  0,128)
             0, 0, 184, 66, 224, 12,    # (256,  0)  64x56  uv(192,168)   <- changed
             0, 136, 152, 67, 224, 6,   # (256,136)  64x32  uv(192,224)
             0, 56, 208, 66, 224, 18,   # (256, 56)  64x80  uv(128,176)   <- changed
             128, 128, 160, 2, 224, 9,  # (128,128) 128x40  uv(  0,168)
             128, 0, 16, 0, 224, 31,    # (128,  0) 128x128 uv(128,  0)
             0, 0, 0, 0, 224, 31])      # (  0,  0) 128x128 uv(  0,  0)

STOCK_GROUP = bytes([7, 16, 0, 0,
                     0, 128, 0, 2, 224, 9,
                     0, 24, 24, 67, 224, 6,     # (256, 24) 64x32 uv(192,224)
                     0, 136, 152, 67, 224, 6,
                     0, 56, 208, 66, 192, 18,   # (256, 56) 56x80 uv(128,176)
                     128, 128, 160, 2, 224, 9,
                     128, 0, 16, 0, 224, 31,
                     0, 0, 0, 0, 224, 31])

LAYOUTS = {
    'SU.MRG':     dict(size=(1572864, 5242880), front=0x10000, fpal=0x30200,
                       back=0x28000, bpal=0x30800, fix=[0x3923A], blocks=[0x39000]),
    'WA_MRG.MRG': dict(size=(37748736, 45088768), front=0xFD3800, fpal=0xFEB800,
                       back=0xFE3800, bpal=0xFEBA00, fix=[0xFD312E, 0xFEC12A],
                       blocks=[0xFD3000, 0xFEC000]),
}


def layout_for(n):
    for k, L in LAYOUTS.items():
        if L['size'][0] <= n <= L['size'][1]:
            return k, L
    sys.exit('unrecognised file size %d (expected SU.MRG or WA_MRG.MRG)' % n)


# ---------------------------------------------------------------- colour ----

def psx_to_rgba(v):
    """BGR555 -> RGBA.  Only an all-zero u16 is transparent (what the site does)."""
    if v == 0:
        return (0, 0, 0, 0)
    return ((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3, 255)


def rgba_to_psx(r, g, b, a):
    """RGBA -> BGR555 exactly the way the site's setNewHeader() writes it:
    channels truncated to 5 bits, STP (bit15) set for every non-black entry."""
    if a == 0 and (r | g | b) == 0:
        return 0
    v = (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)
    return v | 0x8000 if (r or g or b) else 0


def read_pal(d, off, n):
    return [psx_to_rgba(int.from_bytes(d[off + 2 * i:off + 2 * i + 2], 'little')) for i in range(n)]


def quantise(im, ncol, keep_black=True):
    """Reproduce the site's ImageConverter: truncate every channel to 5 bits,
    map opaque black to (8,8,8) so it is not confused with transparent, build a
    palette of the `ncol` most frequent colours sorted by RGB value, then map
    every pixel to the nearest palette entry (transparent -> first entry with
    alpha 0).  Returns (palette as RGBA tuples, 2D list of indices)."""
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
            k = (r, g, b)
            e = hist.get(k)
            if e is None:
                hist[k] = [1, (r, g, b, a)]
            else:
                e[0] += 1
    ent = sorted(hist.values(), key=lambda e: -e[0])[:ncol]
    while len(ent) < ncol:
        ent.append(ent[0])
    pal = sorted((e[1] for e in ent), key=lambda c: (c[0] << 16) | (c[1] << 8) | c[2])
    clear = next((i for i, c in enumerate(pal) if c[3] == 0), 0)
    cache = {}
    idx = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            c = cells[y][x]
            n = cache.get(c)
            if n is None:
                if c[3] == 0:
                    n = clear
                else:
                    best, bd = 0, 1 << 30
                    for i, p in enumerate(pal):
                        if p[3] == 0:
                            continue
                        dd = (c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2 + (c[2] - p[2]) ** 2
                        if dd < bd:
                            best, bd = i, dd
                            if dd == 0:
                                break
                    n = best
                cache[c] = n
            idx[y][x] = n
    if len(hist) > ncol:
        print('quantised %d colours down to %d' % (len(hist), ncol))
    return pal, idx


def write_pal(d, off, pal, bump_black=False):
    for i, c in enumerate(pal):
        r, g, b, a = c
        if bump_black and (r | g | b) == 0:
            r = g = b = 1          # the site's setNewHeaderBG(): opaque black, not transparent
            a = 255
        v = rgba_to_psx(r, g, b, a)
        d[off + 2 * i:off + 2 * i + 2] = v.to_bytes(2, 'little')


# ------------------------------------------------------------- commands -----

def dump(args):
    d = open(args.mrg, 'rb').read()
    name, L = layout_for(len(d))
    print('file looks like', name)
    pal = read_pal(d, L['fpal'], 256)
    raw = Image.new('RGBA', (128, 512))
    rp = raw.load()
    for y in range(512):
        row = L['front'] + 128 * y
        for x in range(128):
            rp[x, y] = pal[d[row + x]]
    front = Image.new('RGBA', (320, 168))
    for dx, dy, w, h, cx, cy in CHUNKS:
        front.paste(raw.crop((dx, dy, dx + w, dy + h)), (cx, cy))
    front.save(args.prefix + '_front.png')
    raw.save(args.prefix + '_raw.png')
    bpal = read_pal(d, L['bpal'], 16)
    back = Image.new('RGBA', (256, 256))
    bp = back.load()
    for y in range(256):
        row = L['back'] + 128 * y
        for x in range(128):
            v = d[row + x]
            bp[2 * x, y] = bpal[v & 15]
            bp[2 * x + 1, y] = bpal[v >> 4]
    back.save(args.prefix + '_back.png')
    print('wrote %s_front.png (320x168), %s_raw.png (128x512), %s_back.png (256x256)'
          % (args.prefix, args.prefix, args.prefix))


def import_(args):
    d = bytearray(open(args.mrg, 'rb').read())
    name, L = layout_for(len(d))
    if not args.front and not args.back:
        sys.exit('nothing to do: pass --front and/or --back')
    if args.front:
        im = Image.open(args.front)
        if im.size != (320, 168):
            sys.exit('--front must be 320x168, got %dx%d' % im.size)
        pal, ix = quantise(im, 256)
        write_pal(d, L['fpal'], pal)
        for dx, dy, w, h, cx, cy in CHUNKS:
            for y in range(h):
                row = L['front'] + 128 * (dy + y) + dx
                src = ix[cy + y]
                for x in range(w):
                    d[row + x] = src[cx + x]
        if not args.no_fix:
            for a in L['fix']:
                d[a:a + len(FIX)] = FIX
    if args.back:
        im = Image.open(args.back)
        if im.size != (256, 256):
            sys.exit('--back must be 256x256, got %dx%d' % im.size)
        pal, ix = quantise(im, 16)
        write_pal(d, L['bpal'], pal, bump_black=True)
        for y in range(256):
            row = L['back'] + 128 * y
            src = ix[y]
            for x in range(128):
                d[row + x] = src[2 * x] | (src[2 * x + 1] << 4)
    out = args.out or args.mrg
    open(out, 'wb').write(d)
    print('wrote', out)


def restore(args):
    d = bytearray(open(args.mrg, 'rb').read())
    s = open(args.stock, 'rb').read()
    name, L = layout_for(len(d))
    if len(s) != len(d):
        sys.exit('stock file has a different size')
    for off, n in ((L['front'], 0x10000), (L['fpal'], 0x200), (L['back'], 0x8000), (L['bpal'], 0x20)):
        d[off:off + n] = s[off:off + n]
    for a in L['fix']:
        d[a:a + len(FIX)] = s[a:a + len(FIX)]
    out = args.out or args.mrg
    open(out, 'wb').write(d)
    print('restored', out)


def check(args):
    d = open(args.mrg, 'rb').read()
    name, L = layout_for(len(d))
    print('file looks like %s (%d bytes)' % (name, len(d)))
    for a in L['fix']:
        cur = d[a:a + len(FIX)]
        what = 'STOCK' if cur == STOCK_GROUP else ('FIXED (site patch applied)' if cur == FIX else 'UNKNOWN')
        print('  logo sprite group @0x%X: %s' % (a, what))
    n = sum(1 for i in range(0, 0x200, 2)
            if int.from_bytes(d[L['fpal'] + i:L['fpal'] + i + 2], 'little') & 0x8000)
    print('  front CLUT @0x%X: %d/256 entries have STP set' % (L['fpal'], n))


# --------------------------------------------------------- sprite blocks ----

def decode_sprite(b, ext):
    """6-byte sprite record.  ext = group flag 0x10 (10-bit screen coords)."""
    A = b[2] | b[3] << 8
    B = b[4] | b[5] << 8
    if ext:
        x = b[0] | ((A >> 14) & 3) << 8
        y = b[1] | ((B >> 14) & 3) << 8
        if x & 0x200: x -= 0x400
        if y & 0x200: y -= 0x400
    else:
        x = b[0] - 256 if b[0] > 127 else b[0]
        y = b[1] - 256 if b[1] > 127 else b[1]
    u = (A & 0x1F) * 8
    v = ((A >> 5) & 0x1F) * 8
    w = (((B >> 5) & 0xF) + 1) * 8
    h = (((B >> 9) & 0xF) + 1) * 8
    return x, y, u, v, w, h, A, B


def decode_group(d, at):
    """group = u8 count, u8 flags, u8, u8, then count x 6-byte sprites."""
    n, flags = d[at], d[at + 1]
    print('group @0x%X: %d sprites, flags 0x%02X, extra %02X %02X'
          % (at, n, flags, d[at + 2], d[at + 3]))
    for e in range(n):
        b = d[at + 4 + 6 * e:at + 10 + 6 * e]
        x, y, u, v, w, h, A, B = decode_sprite(b, flags & 0x10)
        fo = 0x8000 * (u >= 128) + 128 * v + (u & 127)
        print('  %s  screen(%4d,%4d) %3dx%-3d  uv(%3d,%3d)  front+0x%05X  A=%04X B=%04X'
              % (b.hex(' '), x, y, w, h, u, v, fo, A, B))


def sprites(args):
    d = open(args.mrg, 'rb').read()
    name, L = layout_for(len(d))
    if args.at:
        decode_group(d, int(args.at, 0))
        return
    for a in L['fix']:
        decode_group(d, a)
        print()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('dump'); p.add_argument('mrg'); p.add_argument('prefix'); p.set_defaults(f=dump)
    p = sp.add_parser('import'); p.add_argument('mrg'); p.add_argument('-o', '--out')
    p.add_argument('--front'); p.add_argument('--back')
    p.add_argument('--no-fix', action='store_true', help="don't rewrite the 7-sprite group")
    p.set_defaults(f=import_)
    p = sp.add_parser('restore'); p.add_argument('mrg'); p.add_argument('stock')
    p.add_argument('-o', '--out'); p.set_defaults(f=restore)
    p = sp.add_parser('check'); p.add_argument('mrg'); p.set_defaults(f=check)
    p = sp.add_parser('sprites'); p.add_argument('mrg'); p.add_argument('--at'); p.set_defaults(f=sprites)
    a = ap.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
