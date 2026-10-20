#!/usr/bin/env python3
"""Offline clone of TEA-Online "Thumbnail" (extend/tools/image/thumbnail).

The 25 dialog portraits live in WA_MRG.MRG at 0xF35000 + 2432*(n-1), n = 1..25
(in-file sectors 0x1E6A..0x1E87, disc LBA 17888..17917):
    +0     48x48 8bpp indices, 48-byte rows           (2304 B)
    +2304  64-entry CLUT, 15-bit BGR555 little endian (128 B)
Text control `F6 xx 00` with xx = 0x40+n shows portrait n in a dialog box.

  dialog_thumbs.py inspect WA_MRG.MRG
  dialog_thumbs.py export  WA_MRG.MRG OUTDIR [--scale 4]      -> OUTDIR/thumb_NN.png
  dialog_thumbs.py import  WA_MRG.MRG N IMAGE.png             (any size, scaled to 48x48, 64 colours)
  dialog_thumbs.py restore WA_MRG.MRG [N] [--stock DISC.bin|WA_MRG.MRG]

Run on a COPY of WA_MRG.MRG. `restore` pulls the stock bytes from the raw disc
image (MODE2/2352) or a stock WA_MRG copy and reproduces them byte-for-byte.
"""
import argparse, os, struct, sys
from PIL import Image

BASE, STRIDE, COUNT = 0xF35000, 2432, 25
W = H = 48
NCOL = 64
BODY = W * H
STOCK_DISC = '/home/codyj/YuGiOhForbiddenMemoriesRecomp/disc/Yu-Gi-Oh! Forbidden Memories (USA).bin'
WA_LBA = 10102

# ---- 15-bit CLUT helpers ---------------------------------------------------
def clut_decode(raw, n):
    out = []
    for i in range(n):
        v = raw[2 * i] | raw[2 * i + 1] << 8
        r, g, b = (v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3
        out.append((r | r >> 5, g | g >> 5, b | b >> 5, 0 if v == 0 else 255))
    return out

def clut_encode(colors):
    """(r,g,b,a) -> u16: 0 = transparent; opaque colours carry bit 15 like the stock data
    (opaque black therefore becomes 0x8000, not 0x0000)."""
    raw = bytearray()
    for r, g, b, a in colors:
        v = 0 if a < 128 else 0x8000 | (r >> 3) | (g >> 3) << 5 | (b >> 3) << 10
        raw += struct.pack('<H', v)
    return bytes(raw)

def stock_bytes(stock, off, n):
    with open(stock, 'rb') as f:
        f.seek(0, 2); size = f.tell()
        if size > 0x2400000 * 4:                       # raw disc image, 2352-byte sectors
            out = bytearray()
            lba = WA_LBA + off // 2048; skip = off % 2048
            while len(out) < n + skip:
                f.seek(lba * 2352 + 24); out += f.read(2048); lba += 1
            return bytes(out[skip:skip + n])
        f.seek(off); return f.read(n)

def tile_off(n):
    if not 1 <= n <= COUNT: sys.exit('portrait index must be 1..25')
    return BASE + STRIDE * (n - 1)

def read_tile(buf, n):
    o = tile_off(n)
    body = buf[o:o + BODY]; pal = clut_decode(buf[o + BODY:o + STRIDE], NCOL)
    im = Image.new('RGBA', (W, H)); px = im.load()
    for y in range(H):
        for x in range(W):
            px[x, y] = pal[body[y * W + x] & 63] if body[y * W + x] < NCOL else (255, 0, 255, 255)
    return im, body, pal

def cmd_inspect(a):
    buf = open(a.wa, 'rb').read()
    for n in range(1, COUNT + 1):
        o = tile_off(n); body = buf[o:o + BODY]; raw = buf[o + BODY:o + STRIDE]
        used = sorted(set(body)); stp = sum(1 for i in range(NCOL) if raw[2*i+1] & 0x80)
        print(f'#{n:2d} off 0x{o:06X} sector 0x{o//2048:04X} LBA {WA_LBA+o//2048}  code [F6 {0x40+n:02X} 00]'
              f'  indices {used[0]}..{used[-1]} ({len(used)} used)  CLUT entries with STP: {stp}/64')

def cmd_export(a):
    buf = open(a.wa, 'rb').read(); os.makedirs(a.outdir, exist_ok=True)
    for n in range(1, COUNT + 1):
        im, _, _ = read_tile(buf, n)
        if a.scale > 1: im = im.resize((W * a.scale, H * a.scale), Image.NEAREST)
        im.save(os.path.join(a.outdir, f'thumb_{n:02d}.png'))
    print(f'wrote {COUNT} portraits to {a.outdir}')

def cmd_import(a):
    buf = bytearray(open(a.wa, 'rb').read()); o = tile_off(a.n)
    im = Image.open(a.png).convert('RGBA')
    if im.size != (W, H): im = im.resize((W, H), Image.LANCZOS)
    # the game draws these opaque: flatten alpha onto black, then 64-colour median cut
    bg = Image.new('RGBA', (W, H), (0, 0, 0, 255)); bg.alpha_composite(im)
    q = bg.convert('RGB').quantize(colors=NCOL, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = q.getpalette()[:NCOL * 3]; idx = q.tobytes()
    colors = [(pal[3*i], pal[3*i+1], pal[3*i+2], 255) for i in range(NCOL)]
    buf[o:o + BODY] = idx
    buf[o + BODY:o + STRIDE] = clut_encode(colors)
    open(a.wa, 'wb').write(buf); print(f'portrait {a.n} replaced (code [F6 {0x40+a.n:02X} 00])')

def cmd_restore(a):
    buf = bytearray(open(a.wa, 'rb').read())
    ids = [a.n] if a.n else range(1, COUNT + 1)
    for n in ids:
        o = tile_off(n); buf[o:o + STRIDE] = stock_bytes(a.stock, o, STRIDE)
    open(a.wa, 'wb').write(buf); print('restored', list(ids))

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest='cmd', required=True)
    q = s.add_parser('inspect'); q.add_argument('wa'); q.set_defaults(f=cmd_inspect)
    q = s.add_parser('export'); q.add_argument('wa'); q.add_argument('outdir'); q.add_argument('--scale', type=int, default=1); q.set_defaults(f=cmd_export)
    q = s.add_parser('import'); q.add_argument('wa'); q.add_argument('n', type=int); q.add_argument('png'); q.set_defaults(f=cmd_import)
    q = s.add_parser('restore'); q.add_argument('wa'); q.add_argument('n', type=int, nargs='?'); q.add_argument('--stock', default=STOCK_DISC); q.set_defaults(f=cmd_restore)
    a = p.parse_args(); a.f(a)
