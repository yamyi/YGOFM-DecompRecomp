#!/usr/bin/env python3
"""Offline clone of the image half of TEA-Online "Cards" / specsmix
(extend/tools/image/specsmix, chunk cards.*.js): per-card art, baked title,
40x32 thumbnail, and the price/password table, all in WA_MRG.MRG.

Card record (7 sectors, in-file sector 722 + 7*(id-1), disc LBA 10817 + 7*id):
    REC = 0x169000 + 14336*(id-1)
    REC+0      art    102x96 8bpp, 102-byte rows                      9792 B
    REC+9792   CLUT   256 x u16 BGR555                                 512 B
    REC+10304  title  96x14 4bpp, 48-byte rows, low nibble = left px   672 B
                      (index 0 transparent, 1 lightest .. 7 darkest; CLUT is the
                      game's grey ramp, not on disc)
    REC+10976  thumb  40x32 8bpp (1280 B) + 64 x u16 CLUT (128 B)     1408 B
    REC+12384  zero padding to 14336
Thumbnail copy #2: sector id-1 of the file: 0x800*(id-1) (+0 body, +1280 CLUT,
    then 0xFF padding) -- byte-identical to the record copy on the stock disc.
Price/password table: 0xFB9800 + 8*id: u32 price, u32 password as 8 hex digits
    (Blue-eyes: 999999 / 0x89631139 -> "89631139").

  card_images.py inspect WA_MRG.MRG ID
  card_images.py export  WA_MRG.MRG ID OUTDIR [--scale N]     art/title/thumb PNGs
  card_images.py import  WA_MRG.MRG ID --art A.png | --title T.png | --thumb S.png  (any combination)
  card_images.py price   WA_MRG.MRG ID [--price N] [--password HEX8]
  card_images.py restore WA_MRG.MRG ID [--stock DISC.bin|WA_MRG.MRG]
Work on a COPY of WA_MRG.MRG.
"""
import argparse, os, struct, sys
from PIL import Image

REC0, RECSZ = 0x169000, 14336
ART_W, ART_H, ART_OFF = 102, 96, 0
CLUT_OFF = 9792
TITLE_W, TITLE_H, TITLE_OFF = 96, 14, 10304
THUMB_W, THUMB_H, THUMB_OFF = 40, 32, 10976
THUMB2_STRIDE = 2048
PRICE0 = 0xFB9800
STOCK_DISC = '/home/codyj/YuGiOhForbiddenMemoriesRecomp/disc/Yu-Gi-Oh! Forbidden Memories (USA).bin'
WA_LBA = 10102
GREY = [(0, 0, 0, 0)] + [(255 - 32 * i, 255 - 32 * i, 255 - 32 * i, 255) for i in range(1, 8)]  # preview ramp

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

def rec(cid):
    if not 1 <= cid <= 722: sys.exit('card id must be 1..722')
    return REC0 + RECSZ * (cid - 1)

def img8(body, w, h, stride, pal):
    im = Image.new('RGBA', (w, h)); px = im.load()
    for y in range(h):
        for x in range(w):
            i = body[y*stride + x]; px[x, y] = pal[i] if i < len(pal) else (255, 0, 255, 255)
    return im

def quantize(im, w, h, ncol):
    im = im.convert('RGBA')
    if im.size != (w, h): im = im.resize((w, h), Image.LANCZOS)
    bg = Image.new('RGBA', (w, h), (0, 0, 0, 255)); bg.alpha_composite(im)
    q = bg.convert('RGB').quantize(colors=ncol, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    p = q.getpalette()[:ncol*3]
    return q.tobytes(), [(p[3*i], p[3*i+1], p[3*i+2], 255) for i in range(ncol)]

def cmd_inspect(a):
    buf = open(a.wa, 'rb').read(); r = rec(a.id)
    print(f'card {a.id}: record 0x{r:06X} sector 0x{r//2048:04X} disc LBA {WA_LBA + r//2048}')
    print(f'  art   0x{r+ART_OFF:06X}  CLUT 0x{r+CLUT_OFF:06X}  title 0x{r+TITLE_OFF:06X}  thumb 0x{r+THUMB_OFF:06X}')
    t2 = THUMB2_STRIDE * (a.id - 1)
    same = buf[r+THUMB_OFF:r+THUMB_OFF+1408] == buf[t2:t2+1408]
    print(f'  thumb copy #2 at 0x{t2:06X}: {"identical" if same else "DIFFERS"}')
    nib = set()
    for b in buf[r+TITLE_OFF:r+TITLE_OFF+672]: nib |= {b & 15, b >> 4}
    print(f'  title nibbles used: {sorted(nib)}')
    price, pw = struct.unpack_from('<II', buf, PRICE0 + 8*a.id)
    print(f'  price {price}  password {pw:08X}')

def cmd_export(a):
    buf = open(a.wa, 'rb').read(); r = rec(a.id); os.makedirs(a.outdir, exist_ok=True)
    pal = clut_decode(buf[r+CLUT_OFF:r+CLUT_OFF+512], 256)
    out = {'art': img8(buf[r+ART_OFF:], ART_W, ART_H, ART_W, pal)}
    tb = buf[r+TITLE_OFF:r+TITLE_OFF+672]
    im = Image.new('RGBA', (TITLE_W, TITLE_H)); px = im.load()
    for y in range(TITLE_H):
        for x in range(TITLE_W):
            b = tb[y*48 + x//2]; n = (b & 15) if x % 2 == 0 else b >> 4
            px[x, y] = GREY[n] if n < 8 else (255, 0, 255, 255)
    out['title'] = im
    th = buf[r+THUMB_OFF:r+THUMB_OFF+1408]
    out['thumb'] = img8(th, THUMB_W, THUMB_H, THUMB_W, clut_decode(th[1280:], 64))
    for k, im in out.items():
        if a.scale > 1: im = im.resize((im.width*a.scale, im.height*a.scale), Image.NEAREST)
        im.save(os.path.join(a.outdir, f'card{a.id:03d}_{k}.png'))
    print('wrote', ', '.join(f'card{a.id:03d}_{k}.png' for k in out), 'to', a.outdir)

def cmd_import(a):
    buf = bytearray(open(a.wa, 'rb').read()); r = rec(a.id)
    if a.art:
        idx, pal = quantize(Image.open(a.art), ART_W, ART_H, 256)
        buf[r+ART_OFF:r+ART_OFF+9792] = idx; buf[r+CLUT_OFF:r+CLUT_OFF+512] = clut_encode(pal); print('art written')
    if a.title:
        im = Image.open(a.title).convert('RGBA')
        if im.size != (TITLE_W, TITLE_H): im = im.resize((TITLE_W, TITLE_H), Image.LANCZOS)
        nib = bytearray(672)
        for y in range(TITLE_H):
            for x in range(TITLE_W):
                rr, gg, bb, al = im.getpixel((x, y))
                # darkness -> 1..7 (1 lightest, 7 darkest); transparent/white -> 0
                lum = (rr + gg + bb) / 3 * al / 255 + 255 * (1 - al / 255)
                n = 0 if al < 16 or lum > 240 else max(1, min(7, round((255 - lum) / 32)))
                if x % 2 == 0: nib[y*48 + x//2] |= n
                else: nib[y*48 + x//2] |= n << 4
        buf[r+TITLE_OFF:r+TITLE_OFF+672] = nib; print('title written')
    if a.thumb:
        idx, pal = quantize(Image.open(a.thumb), THUMB_W, THUMB_H, 64)
        blob = idx + clut_encode(pal)
        buf[r+THUMB_OFF:r+THUMB_OFF+1408] = blob
        t2 = THUMB2_STRIDE * (a.id - 1); buf[t2:t2+1408] = blob; print('thumb written (both copies)')
    open(a.wa, 'wb').write(buf)

def cmd_price(a):
    buf = bytearray(open(a.wa, 'rb').read()); o = PRICE0 + 8*a.id
    if a.price is not None: struct.pack_into('<I', buf, o, max(0, a.price) % 1000000)
    if a.password is not None: struct.pack_into('<I', buf, o+4, int(a.password, 16) & 0xFFFFFFFF)
    open(a.wa, 'wb').write(buf)
    price, pw = struct.unpack_from('<II', buf, o); print(f'card {a.id}: price {price} password {pw:08X}')

def cmd_restore(a):
    buf = bytearray(open(a.wa, 'rb').read()); r = rec(a.id); t2 = THUMB2_STRIDE * (a.id - 1)
    buf[r:r+RECSZ] = stock_bytes(a.stock, r, RECSZ)
    buf[t2:t2+THUMB2_STRIDE] = stock_bytes(a.stock, t2, THUMB2_STRIDE)
    o = PRICE0 + 8*a.id; buf[o:o+8] = stock_bytes(a.stock, o, 8)
    open(a.wa, 'wb').write(buf); print(f'card {a.id} record, thumbnail sector and price entry restored')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest='cmd', required=True)
    q = s.add_parser('inspect'); q.add_argument('wa'); q.add_argument('id', type=int); q.set_defaults(f=cmd_inspect)
    q = s.add_parser('export'); q.add_argument('wa'); q.add_argument('id', type=int); q.add_argument('outdir'); q.add_argument('--scale', type=int, default=1); q.set_defaults(f=cmd_export)
    q = s.add_parser('import'); q.add_argument('wa'); q.add_argument('id', type=int); q.add_argument('--art'); q.add_argument('--title'); q.add_argument('--thumb'); q.set_defaults(f=cmd_import)
    q = s.add_parser('price'); q.add_argument('wa'); q.add_argument('id', type=int); q.add_argument('--price', type=int); q.add_argument('--password'); q.set_defaults(f=cmd_price)
    q = s.add_parser('restore'); q.add_argument('wa'); q.add_argument('id', type=int); q.add_argument('--stock', default=STOCK_DISC); q.set_defaults(f=cmd_restore)
    a = p.parse_args(); a.f(a)
