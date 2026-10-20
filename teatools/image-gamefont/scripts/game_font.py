#!/usr/bin/env python3
"""Offline clone of TEA-Online "Game Font" (extend/tools/image/gamefont).

The text font is one 256x168 4bpp sheet in WA_MRG.MRG:
    body  0xB48000  (in-file sector 0x5A40, disc LBA 33206)  128-byte rows, 21504 B,
                    low nibble = left pixel
    CLUT  0xB60800  (sector 0x5A81 +0x000, LBA 33271)          16 x u16 BGR555, 32 B
Grid: rows 0..71  = small glyphs  8x12, 16 cols x 6 rows
      rows 72..167 = large glyphs 16x16, 16 cols x 6 rows (same character order)

  game_font.py export  WA_MRG.MRG OUT.png [--scale 3] [--indexed]
  game_font.py cells   WA_MRG.MRG OUTDIR            one PNG per glyph cell (small_rc / large_rc)
  game_font.py import  WA_MRG.MRG IN.png            256x168 RGB(A); each pixel -> nearest CLUT entry
                                                    (--palette also rewrites the CLUT from the PNG)
  game_font.py restore WA_MRG.MRG [--stock DISC.bin|WA_MRG.MRG]

Only the sheet (and optionally the CLUT) is written, like the site. Work on a COPY.
"""
import argparse, os, struct, sys
from PIL import Image

BODY, CLUT = 0xB48000, 0xB60800
W, H, STRIDE = 256, 168, 128
NBYTES = STRIDE * H
NCOL = 16
SMALL = dict(cw=8, ch=12, cols=16, rows=6, x0=0, y0=0)
LARGE = dict(cw=16, ch=16, cols=16, rows=6, x0=0, y0=72)
CHARS = [list('!"#$%&\'()*+,-./0'), list('123456789:;<=>?') + [None],
         list('ABCDEFGHIJKLMNOP'), list('QRSTUVWXYZ') + [None] * 6,
         [' '] + list('abcdefghijklmno'), list('pqrstuvwxyz') + [' ', ' ', 'α', 'β', 'γ']]
STOCK_DISC = '/home/codyj/YuGiOhForbiddenMemoriesRecomp/disc/Yu-Gi-Oh! Forbidden Memories (USA).bin'
WA_LBA = 10102

def clut_decode(raw, n):
    out = []
    for i in range(n):
        v = raw[2*i] | raw[2*i+1] << 8
        r, g, b = (v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3
        out.append((r | r >> 5, g | g >> 5, b | b >> 5, 0 if v == 0 else 255))
    return out

def clut_encode(colors):
    raw = bytearray()
    for r, g, b, a in colors:
        raw += struct.pack('<H', 0 if a < 128 else 0x8000 | (r >> 3) | (g >> 3) << 5 | (b >> 3) << 10)
    return bytes(raw)

def stock_bytes(stock, off, n):
    with open(stock, 'rb') as f:
        f.seek(0, 2); size = f.tell()
        if size > 0x2400000 * 4:
            out = bytearray(); lba = WA_LBA + off // 2048; skip = off % 2048
            while len(out) < n + skip:
                f.seek(lba * 2352 + 24); out += f.read(2048); lba += 1
            return bytes(out[skip:skip+n])
        f.seek(off); return f.read(n)

def unpack(buf):
    idx = bytearray(W * H)
    for y in range(H):
        row = buf[BODY + y*STRIDE: BODY + (y+1)*STRIDE]
        for x in range(STRIDE):
            idx[y*W + 2*x] = row[x] & 15; idx[y*W + 2*x + 1] = row[x] >> 4
    return idx

def pack(idx):
    out = bytearray(NBYTES)
    for y in range(H):
        for x in range(STRIDE):
            out[y*STRIDE + x] = (idx[y*W + 2*x] & 15) | (idx[y*W + 2*x + 1] & 15) << 4
    return bytes(out)

def sheet(buf):
    pal = clut_decode(buf[CLUT:CLUT+32], NCOL); idx = unpack(buf)
    im = Image.new('RGBA', (W, H)); im.putdata([pal[i] for i in idx]); return im, pal, idx

def cmd_export(a):
    buf = open(a.wa, 'rb').read(); im, pal, idx = sheet(buf)
    if a.indexed:
        im = Image.new('P', (W, H)); im.putdata(bytes(idx))
        flat = []; [flat.extend(c[:3]) for c in pal]; im.putpalette(flat)
    if a.scale > 1: im = im.resize((W*a.scale, H*a.scale), Image.NEAREST)
    im.save(a.out); print('CLUT:', ' '.join(f'{buf[CLUT+2*i] | buf[CLUT+2*i+1]<<8:04X}' for i in range(NCOL)))

def cmd_cells(a):
    buf = open(a.wa, 'rb').read(); im, _, _ = sheet(buf); os.makedirs(a.outdir, exist_ok=True)
    for name, g in (('small', SMALL), ('large', LARGE)):
        for r in range(g['rows']):
            for c in range(g['cols']):
                x, y = g['x0'] + c*g['cw'], g['y0'] + r*g['ch']
                ch = CHARS[r][c] if c < len(CHARS[r]) else None
                im.crop((x, y, x+g['cw'], y+g['ch'])).save(os.path.join(a.outdir, f'{name}_{r}{c:x}.png'))
    print('cells written; character order per row:'); [print(' ', r) for r in CHARS]

def cmd_import(a):
    buf = bytearray(open(a.wa, 'rb').read())
    im = Image.open(a.png).convert('RGBA')
    if im.size != (W, H): sys.exit(f'need a {W}x{H} image, got {im.size}')
    if a.palette:
        q = im.convert('RGB').quantize(colors=NCOL - 1, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        p = q.getpalette()[:(NCOL-1)*3]
        pal = [(0, 0, 0, 0)] + [(p[3*i], p[3*i+1], p[3*i+2], 255) for i in range(NCOL - 1)]
        buf[CLUT:CLUT+32] = clut_encode(pal)
    else:
        pal = clut_decode(buf[CLUT:CLUT+32], NCOL)
    raw = im.tobytes(); px = [raw[i:i+4] for i in range(0, len(raw), 4)]; idx = bytearray(W * H)
    cache = {}
    for i, (r, g, b, al) in enumerate(px):
        if al < 128: idx[i] = 0; continue           # entry 0 is the transparent one
        key = (r >> 3, g >> 3, b >> 3)
        if key not in cache:
            cache[key] = min(range(1, NCOL), key=lambda k: (pal[k][0]-r)**2 + (pal[k][1]-g)**2 + (pal[k][2]-b)**2)
        idx[i] = cache[key]
    buf[BODY:BODY+NBYTES] = pack(idx); open(a.wa, 'wb').write(buf); print('font sheet written')

def cmd_restore(a):
    buf = bytearray(open(a.wa, 'rb').read())
    buf[BODY:BODY+NBYTES] = stock_bytes(a.stock, BODY, NBYTES); buf[CLUT:CLUT+32] = stock_bytes(a.stock, CLUT, 32)
    open(a.wa, 'wb').write(buf); print('font sheet + CLUT restored')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest='cmd', required=True)
    q = s.add_parser('export'); q.add_argument('wa'); q.add_argument('out'); q.add_argument('--scale', type=int, default=1); q.add_argument('--indexed', action='store_true'); q.set_defaults(f=cmd_export)
    q = s.add_parser('cells'); q.add_argument('wa'); q.add_argument('outdir'); q.set_defaults(f=cmd_cells)
    q = s.add_parser('import'); q.add_argument('wa'); q.add_argument('png'); q.add_argument('--palette', action='store_true'); q.set_defaults(f=cmd_import)
    q = s.add_parser('restore'); q.add_argument('wa'); q.add_argument('--stock', default=STOCK_DISC); q.set_defaults(f=cmd_restore)
    a = p.parse_args(); a.f(a)
