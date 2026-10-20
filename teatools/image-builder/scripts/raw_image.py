#!/usr/bin/env python3
"""Offline clone of TEA-Online "Image Builder" (extend/tools/image/builder): a
generic PNG <-> PSX paletted-texture converter for any offset in WA_MRG.MRG or
SLUS_014.11, driven by the same parameters the site's presets carry:

  --body OFF      byte offset of the pixel data (hex or decimal)
  --clut OFF      byte offset of the CLUT (N x u16 BGR555, little endian)
  --w/--h         image size in pixels (the canvas)
  --bpp 4|8       4 = two pixels per byte (low nibble left), 8 = one index per byte
  --colors N      CLUT entries (16 / 64 / 256)
  --stride S      bytes per texture row ("data width"; default = w/ppb)
  --chunks J      optional JSON list of rectangles mapping texture -> canvas, same
                  shape as the site's presets: [{"width":..,"height":..,
                  "data":{"ci":{"x":..,"y":..}},"canvas":{"ci":{"x":..,"y":..}}}]
                  (data = pixel column/row in the texture; the site stores data.ci.x in
                  BYTES for 4bpp images, so do we). Without it the whole w x h block is used.
  --extra-clut OFF [OFF..]  additional CLUTs that receive the same palette (site: "aditionalPalletes")
  --extra-body OFF [OFF..]  additional bodies that receive the same pixels   (site: "aditionalBodies")

  raw_image.py export  FILE OUT.png  <params> [--scale N]
  raw_image.py import  FILE IN.png   <params>            (median-cut to N colours, alpha<128 -> entry 0)
  raw_image.py restore FILE          <params> [--stock DISC.bin|stock copy]
  raw_image.py preset  NAME          print the params for a known image (thumbnail, font, card-art, ...)
Work on a COPY.
"""
import argparse, json, os, struct, sys
from PIL import Image

STOCK_DISC = '/home/codyj/YuGiOhForbiddenMemoriesRecomp/disc/Yu-Gi-Oh! Forbidden Memories (USA).bin'
WA_LBA = 10102
PRESETS = {
    'thumbnail-1': '--body 0xF35000 --clut 0xF35900 --w 48 --h 48 --bpp 8 --colors 64   (dialog portrait n: +2432*(n-1))',
    'font':        '--body 0xB48000 --clut 0xB60800 --w 256 --h 168 --bpp 4 --colors 16',
    'card-art-1':  '--body 0x169000 --clut 0x16B640 --w 102 --h 96 --bpp 8 --colors 256   (card id: +14336*(id-1))',
    'card-thumb-1':'--body 0x16BAE0 --clut 0x16BFE0 --w 40 --h 32 --bpp 8 --colors 64 --extra-body 0x0 --extra-clut 0x500',
    'icons':       '--body 0xB50000 --clut 0xB60400 --w 256 --h 160 --bpp 4 --colors 16 --stride 128   (UI icon sheet, CLUT row 24 of 0xB60100+32*i)',
    'card-frame':  '--body 0xB63000 --clut 0xB83A80 --w 144 --h 200 --bpp 8 --colors 256 --stride 128 --chunks presets/card_frame_monster.json',
}

def parse_int(s): return int(s, 0)

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

def chunks_of(a):
    ppb = 2 if a.bpp == 4 else 1
    if a.chunks:
        raw = json.load(open(a.chunks)) if os.path.exists(a.chunks) else json.loads(a.chunks)
        return [(c['data']['ci']['x'], c['data']['ci']['y'], c['width'], c['height'],
                 c['canvas']['ci']['x'], c['canvas']['ci']['y']) for c in raw], ppb
    return [(0, 0, a.w, a.h, 0, 0)], ppb

def get_px(buf, body, stride, ppb, bx, y, px):   # px = pixel column inside the chunk, bx = byte column of chunk
    if ppb == 1: return buf[body + y*stride + bx + px]
    b = buf[body + y*stride + bx + px//2]; return (b & 15) if px % 2 == 0 else b >> 4

def cmd_export(a):
    buf = open(a.file, 'rb').read(); chunks, ppb = chunks_of(a); stride = a.stride or a.w // ppb
    pal = clut_decode(buf[a.clut:a.clut + 2*a.colors], a.colors)
    im = Image.new('RGBA', (a.w, a.h)); pix = im.load()
    for (dx, dy, w, h, cx, cy) in chunks:
        for y in range(h):
            for x in range(w):
                i = get_px(buf, a.body, stride, ppb, dx, dy + y, x)
                if 0 <= cx + x < a.w and 0 <= cy + y < a.h: pix[cx + x, cy + y] = pal[i] if i < a.colors else (255, 0, 255, 255)
    if a.scale > 1: im = im.resize((a.w*a.scale, a.h*a.scale), Image.NEAREST)
    im.save(a.out); print('wrote', a.out)

def cmd_import(a):
    buf = bytearray(open(a.file, 'rb').read()); chunks, ppb = chunks_of(a); stride = a.stride or a.w // ppb
    im = Image.open(a.png).convert('RGBA')
    if im.size != (a.w, a.h): im = im.resize((a.w, a.h), Image.LANCZOS)
    alpha = im.getchannel('A'); has_alpha = alpha.getextrema()[0] < 128
    ncol = a.colors - 1 if has_alpha else a.colors
    bg = Image.new('RGBA', im.size, (0, 0, 0, 255)); bg.alpha_composite(im)
    q = bg.convert('RGB').quantize(colors=ncol, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    p = q.getpalette()[:ncol*3]; idx = list(q.tobytes()); al = alpha.tobytes()
    pal = [(p[3*i], p[3*i+1], p[3*i+2], 255) for i in range(ncol)]
    if has_alpha:                                   # entry 0 = transparent, like the stock CLUTs
        pal = [(0, 0, 0, 0)] + pal; idx = [0 if al[i] < 128 else idx[i] + 1 for i in range(len(idx))]
    pal += [(0, 0, 0, 255)] * (a.colors - len(pal))
    for clut in [a.clut] + (a.extra_clut or []):
        buf[clut:clut + 2*a.colors] = clut_encode(pal)
    for body in [a.body] + (a.extra_body or []):
        for (dx, dy, w, h, cx, cy) in chunks:
            for y in range(h):
                for x in range(0, w, ppb):
                    v = idx[(cy + y)*a.w + cx + x]
                    if ppb == 2: v |= idx[(cy + y)*a.w + cx + x + 1] << 4
                    buf[body + (dy + y)*stride + dx + x//ppb] = v
    open(a.file, 'wb').write(buf); print('written')

def cmd_restore(a):
    buf = bytearray(open(a.file, 'rb').read()); chunks, ppb = chunks_of(a); stride = a.stride or a.w // ppb
    for clut in [a.clut] + (a.extra_clut or []):
        buf[clut:clut + 2*a.colors] = stock_bytes(a.stock, clut, 2*a.colors)
    for body in [a.body] + (a.extra_body or []):
        for (dx, dy, w, h, cx, cy) in chunks:
            for y in range(h):
                o = body + (dy + y)*stride + dx; buf[o:o + w//ppb] = stock_bytes(a.stock, o, w//ppb)
    open(a.file, 'wb').write(buf); print('restored')

def cmd_preset(a):
    for k, v in PRESETS.items():
        if a.name in ('all', k): print(f'{k:14s} {v}')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest='cmd', required=True)
    def common(q):
        q.add_argument('file'); q.add_argument('--body', type=parse_int, required=True); q.add_argument('--clut', type=parse_int, required=True)
        q.add_argument('--w', type=int, required=True); q.add_argument('--h', type=int, required=True)
        q.add_argument('--bpp', type=int, choices=(4, 8), default=8); q.add_argument('--colors', type=int, default=256)
        q.add_argument('--stride', type=int); q.add_argument('--chunks'); q.add_argument('--extra-clut', type=parse_int, nargs='*'); q.add_argument('--extra-body', type=parse_int, nargs='*')
    q = s.add_parser('export'); common(q); q.add_argument('out'); q.add_argument('--scale', type=int, default=1); q.set_defaults(f=cmd_export)
    q = s.add_parser('import'); common(q); q.add_argument('png'); q.set_defaults(f=cmd_import)
    q = s.add_parser('restore'); common(q); q.add_argument('--stock', default=STOCK_DISC); q.set_defaults(f=cmd_restore)
    q = s.add_parser('preset'); q.add_argument('name', nargs='?', default='all'); q.set_defaults(f=cmd_preset)
    a = p.parse_args(); a.f(a)
