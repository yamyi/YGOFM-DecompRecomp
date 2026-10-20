#!/usr/bin/env python3
"""Offline clone of TEA-Online "Mini Card Sleeves" (extend/tools/image/minicardsleeves).

The 56x64 "mini" cards (hand / field view) are four 8bpp tiles in the same
128-byte-wide card texture column that the big card uses, rows 640..768
(VRAM page (896,256), v 128..255), with a 128x48 text strip at rows 592..640.
They exist in the 7 duel-arena bundles and the library bundle only.  Palettes
are CLUT-block rows 1..6 (VRAM y 241..246) at colour indices 64..127, plus a
7th palette in row 1 at indices 192..255.  The 12x16 4bpp "micro" cards live
in the arena bundles at sector 197 (VRAM (832,0) page, u 96..120, v 112..128)
with their 16-colour CLUTs in the boot block at 0xB60840 (VRAM (544+16k,252)).

    mini_sleeves.py dump    WA_MRG.MRG OUTDIR [--bundle N] [--clut K]
    mini_sleeves.py apply   WA_MRG.MRG [--dynamic PNG(168x64)] [--static PNG(168x64)]
                            [--sleeve PNG(56x64)] [--text PNG(128x48)]
                            [--micro-a PNG(12x16)] [--micro-b PNG(12x16)] [--clut-rows 0-6]
    mini_sleeves.py restore WA_MRG.MRG          (from WA_MRG.MRG.minisleeves.bak)
"""
import argparse, warnings, os, struct, sys
warnings.filterwarnings("ignore", category=DeprecationWarning)   # Pillow getdata()
from PIL import Image

WA_LBA = 10102
class Blob:
    def __init__(self, path, write=False):
        self.path = path; self.raw = open(path, 'rb').read()
        self.is_disc = self.raw[16*2352+24+1:16*2352+24+6] == b'CD001'
        if self.is_disc and write: sys.exit('refusing to write into a disc image')
        self.data = bytearray(self.raw) if write else None
    def rd(self, off, n):
        if not self.is_disc: return self.raw[off:off+n]
        out = bytearray()
        while n:
            lba = WA_LBA + off//2048; rem = off % 2048
            s = self.raw[lba*2352+24:lba*2352+24+2048]; take = min(n, 2048-rem)
            out += s[rem:rem+take]; off += take; n -= take
        return bytes(out)
    def wr(self, off, b): self.data[off:off+len(b)] = b
    def save(self): open(self.path, 'wb').write(self.data)

CYCLES = [0, 481280, 962560, 1443840, 1925120, 2406400, 2887680, 3684352]
NAMES = ['arena%d' % i for i in range(7)] + ['library(0x1DCD)']
BUNDLES = [(0xB63000 + c, 0xB83000 + c) for c in CYCLES]     # (texture base, clut block)
ARENAS = BUNDLES[:7]
ROWB = 128
MINI_ROW0 = 592                       # tool body_offset 0xB75800 = 0xB63000 + 592*128
# chunks relative to the texture base: (data_x, data_y, canvas_x, canvas_y, w, h)
TILE_A = (0, 640, 0, 0, 56, 64); TILE_B = (0, 704, 56, 0, 56, 64)
TILE_C = (56, 704, 112, 0, 56, 64); TILE_D = (56, 640, 0, 0, 56, 64)
FACES = [TILE_A, TILE_B, TILE_C]          # dynamic/static: 168x64 = tiles A,B,C
SLEEVE = [TILE_D]                          # 56x64
TEXT = [(0, 592, 0, 0, 128, 48)]           # 128x48
DYN0, STA0, SLV0, TXT0, NCOL = 64, 80, 96, 112, 16
CLUT_ROWS = [1, 2, 3, 4, 5, 6]             # + 7th palette: row 1, index+128
MICRO_ROW0 = 197*16                        # sector 197 of the arena bundle
MICRO_A = (48, MICRO_ROW0, 0, 0, 6, 16)    # 6 bytes = 12 px at 4bpp
MICRO_B = (54, MICRO_ROW0, 0, 0, 6, 16)
MICRO_CLUT = 0xB60840                      # boot block (0x1690+49), 7 x 16 colours -> VRAM (544+16k, 252)

def dec15(v): return ((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3, 0 if v == 0 else 255)
def enc15(c):
    r, g, b, a = c
    if a == 0: return 0
    if (r, g, b) == (0, 0, 0): r = g = b = 8
    return 0x8000 | (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)
def read_clut(blob, off, n=256):
    b = blob.rd(off, 2*n); return [dec15(struct.unpack_from('<H', b, 2*i)[0]) for i in range(n)]

def quantize(img, ncolors):
    img = img.convert('RGBA'); px = list(img.getdata())
    opaque = [(r & ~7, g & ~7, b & ~7) for r, g, b, a in px if a]
    pal = [(0, 0, 0, 0)]; remap = {}
    if opaque:
        tmp = Image.new('RGB', (len(opaque), 1)); tmp.putdata(opaque)
        q = tmp.quantize(colors=ncolors-1, method=Image.Quantize.MEDIANCUT); p = q.getpalette()
        for u in sorted(set(q.getdata())):
            c = (p[3*u] & ~7, p[3*u+1] & ~7, p[3*u+2] & ~7, 255)
            if c[:3] == (0, 0, 0): c = (8, 8, 8, 255)
            if c not in pal: pal.append(c)
            remap[u] = pal.index(c)
        qi = iter(q.getdata())
    idx = [0 if not a else remap[next(qi)] for r, g, b, a in px]
    return pal, idx

def paint(blob, tex, chunks, cw, ch, pal, keep=None, bpp=8):
    img = Image.new('RGBA', (cw, ch), (0, 0, 0, 0)); p = img.load()
    for dx, dy, cx, cy, w, h in chunks:
        for y in range(h):
            row = blob.rd(tex + (dy+y)*ROWB + dx, w)
            for x in range(w):
                if bpp == 8:
                    if keep is None or keep(row[x]): p[cx+x, cy+y] = pal[row[x]]
                else:
                    p[cx+2*x, cy+y] = pal[row[x] & 15]; p[cx+2*x+1, cy+y] = pal[row[x] >> 4]
    return img

def palette_for(blob, clut, k):
    """256-entry palette the game uses for card-type k (0..6)."""
    if k < 6: return read_clut(blob, clut + 512*(1+k))
    row1 = read_clut(blob, clut + 512*1)
    return row1[128:] + row1[128:]         # 7th palette: index i -> row 1 colour 128+i

def cmd_dump(a):
    blob = Blob(a.file); tex, clut = BUNDLES[a.bundle]; os.makedirs(a.outdir, exist_ok=True)
    pal = palette_for(blob, clut, a.clut)
    paint(blob, tex, FACES, 168, 64, pal).save(f'{a.outdir}/mini_full.png')
    paint(blob, tex, FACES, 168, 64, pal, lambda i: DYN0 <= i < DYN0+NCOL).save(f'{a.outdir}/mini_dynamic.png')
    paint(blob, tex, FACES, 168, 64, pal, lambda i: STA0 <= i < STA0+NCOL).save(f'{a.outdir}/mini_static.png')
    paint(blob, tex, SLEEVE, 56, 64, pal).save(f'{a.outdir}/mini_sleeve.png')
    paint(blob, tex, TEXT, 128, 48, pal).save(f'{a.outdir}/mini_text.png')
    if a.bundle < 7:
        mp = read_clut(blob, MICRO_CLUT + 32*a.clut, 16)
        paint(blob, tex, [MICRO_A], 12, 16, mp, bpp=4).save(f'{a.outdir}/micro_a.png')
        paint(blob, tex, [MICRO_B], 12, 16, mp, bpp=4).save(f'{a.outdir}/micro_b.png')
    print('wrote', a.outdir, 'from', NAMES[a.bundle])

class Patcher:
    def __init__(self, blob): self.blob = blob; self.bak = []
    def write(self, off, b):
        self.bak.append((off, bytes(self.blob.rd(off, len(b))))); self.blob.wr(off, b)
def load_bak(path):
    d = open(path, 'rb').read(); i = 0; out = []
    while i < len(d):
        off, n = struct.unpack_from('<II', d, i); out.append((off, d[i+8:i+8+n])); i += 8+n
    return out
def save_bak(p, path):
    old = load_bak(path) if os.path.exists(path) else []
    with open(path, 'wb') as f:
        for off, b in old + p.bak: f.write(struct.pack('<II', off, len(b)) + b)

def parse_rows(s):
    lo, _, hi = s.partition('-'); return list(range(int(lo), int(hi or lo)+1))

def write_clut(p, clut, ks, first, pal):
    b = b''.join(struct.pack('<H', enc15(c)) for c in pal)
    for k in ks:
        if k < 6: p.write(clut + 512*(1+k) + 2*first, b)
        else:     p.write(clut + 512*1 + 2*(128+first), b)
def write_pixels(p, tex, chunks, cw, idx, base, only_opaque, pal, bpp=8):
    for dx, dy, cx, cy, w, h in chunks:
        for y in range(h):
            row = bytearray(p.blob.rd(tex + (dy+y)*ROWB + dx, w))
            for x in range(w):
                if bpp == 8:
                    i = idx[(cy+y)*cw + cx + x]
                    if only_opaque and pal[i][3] == 0: continue
                    row[x] = base + i
                else:
                    lo = idx[(cy+y)*cw + cx + 2*x]; hi = idx[(cy+y)*cw + cx + 2*x + 1]
                    row[x] = (base + lo) | ((base + hi) << 4)
            p.write(tex + (dy+y)*ROWB + dx, bytes(row))

def cmd_apply(a):
    blob = Blob(a.file, write=True); p = Patcher(blob); ks = parse_rows(a.clut_rows)
    def layer(png, size, chunks, base, only_opaque):
        img = Image.open(png); assert img.size == size, f'{png}: need {size}'
        pal, idx = quantize(img, NCOL)
        for tex, clut in BUNDLES:
            write_clut(p, clut, ks, base, pal); write_pixels(p, tex, chunks, size[0], idx, base, only_opaque, pal)
    if a.dynamic: layer(a.dynamic, (168, 64), FACES, DYN0, False)
    if a.static:  layer(a.static, (168, 64), FACES, STA0, True)
    if a.sleeve:  layer(a.sleeve, (56, 64), SLEEVE, SLV0, False)
    if a.text:    layer(a.text, (128, 48), TEXT, TXT0, False)
    for png, chunk in ((a.micro_a, MICRO_A), (a.micro_b, MICRO_B)):
        if not png: continue
        img = Image.open(png); assert img.size == (12, 16)
        pal, idx = quantize(img, 16)
        b = b''.join(struct.pack('<H', enc15(c)) for c in pal)
        for k in ks: p.write(MICRO_CLUT + 32*k, b)
        for tex, clut in ARENAS: write_pixels(p, tex, [chunk], 12, idx, 0, False, pal, bpp=4)
    save_bak(p, a.file + '.minisleeves.bak'); blob.save()
    print('patched', len(p.bak), 'ranges; backup ->', a.file + '.minisleeves.bak')

def cmd_restore(a):
    blob = Blob(a.file, write=True); bak = a.file + '.minisleeves.bak'
    if not os.path.exists(bak): sys.exit('no ' + bak)
    for off, b in reversed(load_bak(bak)): blob.wr(off, b)
    blob.save(); os.remove(bak); print('restored', a.file)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('dump'); s.add_argument('file'); s.add_argument('outdir')
    s.add_argument('--bundle', type=int, default=0); s.add_argument('--clut', type=int, default=0); s.set_defaults(f=cmd_dump)
    s = sp.add_parser('apply'); s.add_argument('file')
    for o in ('--dynamic', '--static', '--sleeve', '--text', '--micro-a', '--micro-b'): s.add_argument(o)
    s.add_argument('--clut-rows', default='0-6'); s.set_defaults(f=cmd_apply)
    s = sp.add_parser('restore'); s.add_argument('file'); s.set_defaults(f=cmd_restore)
    a = ap.parse_args(); a.f(a)

if __name__ == '__main__':
    main()
