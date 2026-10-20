#!/usr/bin/env python3
"""Offline clone of TEA-Online "Card Sleeves" (extend/tools/image/cardsleeves).

Big-card face (dynamic + static layers), card back ("sleeve") and the 4bpp text
placeholders live in a 128-byte-wide 8bpp texture column that is stored ten
times in WA_MRG.MRG (7 duel-arena bundles, the library bundle, the password
bundle and the 0x2189 bundle).  The CLUT block (16 rows x 256 colours) follows
it in each bundle.  See ../README.md for the layout.

    card_sleeves.py dump    WA_MRG.MRG OUTDIR [--bundle N] [--clut K]
    card_sleeves.py verify  WA_MRG.MRG
    card_sleeves.py apply   WA_MRG.MRG [--dynamic PNG] [--static PNG] [--sleeve PNG]
                            [--clut-rows 0-6] [--clean-text]
    card_sleeves.py restore WA_MRG.MRG            (from WA_MRG.MRG.cardsleeves.bak)
    card_sleeves.py positions SLUS_014.11 [--set image=19,50 ...] [--restore]

Also accepts a MODE2/2352 disc image instead of WA_MRG.MRG for dump/verify
(read-only).  Never point apply/restore at the decomp's files.
"""
import argparse, warnings, hashlib, os, struct, sys
warnings.filterwarnings("ignore", category=DeprecationWarning)   # Pillow getdata()
from PIL import Image

# ---------------------------------------------------------------- disc access
WA_LBA = 10102
WA_SIZE = 0x2400000

class Blob:
    """WA_MRG.MRG either as a plain file or inside a raw .bin (MODE2/2352)."""
    def __init__(self, path, write=False):
        self.path = path
        self.raw = open(path, 'rb').read()
        self.is_disc = self.raw[16*2352+24+1:16*2352+24+6] == b'CD001'
        if self.is_disc and write:
            sys.exit('refusing to write into a disc image; extract WA_MRG.MRG first')
        self.data = bytearray(self.raw) if write else None
    def rd(self, off, n):
        if not self.is_disc:
            return self.raw[off:off+n]
        out = bytearray()
        while n:
            lba = WA_LBA + off // 2048; rem = off % 2048
            s = self.raw[lba*2352+24:lba*2352+24+2048]
            take = min(n, 2048-rem); out += s[rem:rem+take]; off += take; n -= take
        return bytes(out)
    def wr(self, off, b):
        self.data[off:off+len(b)] = b
    def save(self):
        open(self.path, 'wb').write(self.data)

# ---------------------------------------------------------------- game layout
# (texture base, clut-block base) of the ten copies; disc LBA = 10102 + off/2048
CYCLES = [0, 481280, 962560, 1443840, 1925120, 2406400, 2887680, 3684352, 4409344, 5658624]
BUNDLE_NAMES = ['arena0', 'arena1', 'arena2', 'arena3', 'arena4', 'arena5', 'arena6',
                'library(0x1DCD)', 'password(0x1F2F)', 'bundle 0x2189']
def bundles():
    out = []
    for i, c in enumerate(CYCLES):
        tex = 0xB63000 + c - (0x4000 if i == len(CYCLES)-1 else 0)
        out.append((tex, 0xB83000 + c))
    return out
BUNDLES = bundles()
ROWB = 128                                  # bytes per texture row (64 VRAM halfwords)
CLUT_ROW_BIG = 8                            # block row of card-type palette 0 (VRAM y=248)
N_TYPES = 7                                 # 6 + "extra" (rows 8..14)
# palette index ranges inside a big-card CLUT row
DYN0, DYN_N = 0, 72
STA0, STA_N_A = 72, 40
STA_B0, STA_N_B = 160, 32
SLV0, SLV_N = 112, 48
TXT_CLUT = 240                              # 4bpp text placeholders, row 8 colours 240..255
TEXT_ROW0, TEXT_ROWS = 928, 80              # 4bpp rows

# chunk = (data_x, data_y, canvas_x, canvas_y, w, h) in 128-byte-row coordinates
FACE = [(0, 0, 0, 0, 128, 192), (0, 256, 128, 0, 16, 128), (32, 256, 128, 128, 16, 72),
        (64, 272, 0, 192, 64, 8), (64, 280, 64, 192, 64, 8), (0, 192, 0, 200, 128, 64)]
FACE_W, FACE_H = 144, 264
SLEEVE = [(0, 384, 0, 0, 128, 192), (16, 256, 128, 0, 16, 128), (48, 256, 128, 128, 16, 72),
          (64, 256, 0, 192, 64, 8), (64, 264, 64, 192, 64, 8)]
SLEEVE_W, SLEEVE_H = 144, 200
TEXT = [(0, 928, 0, 0, 28, 16), (0, 944, 0, 16, 28, 16), (0, 960, 0, 32, 28, 16),
        (0, 976, 0, 48, 12, 16), (0, 992, 0, 64, 12, 16)]      # widths in BYTES (2 px each)
TEXT_W, TEXT_H = 56, 80

# SLUS_014.11 big-card layout immediates (addiu low byte), func_80028B08
POS = [('image', 0x19434, 0x1944C, 19, 50), ('text', 0x194C8, 0x194FC, 12, 14),
       ('atk', 0x196B0, 0x196C4, 97, 157), ('def', 0x1973C, 0x19750, 97, 171),
       ('st', 0x197CC, 0x197F0, 119, 32), ('attr', 0x19884, 0x19898, 110, 13)]

# ---------------------------------------------------------------- colour helpers
def dec15(v):
    return ((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3, 0 if v == 0 else 255)
def enc15(rgba):
    r, g, b, a = rgba
    if a == 0: return 0
    if r == 0 and g == 0 and b == 0: r = g = b = 8      # the tool's "keep black" rule
    return 0x8000 | (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)
def read_clut(blob, off, n=256):
    b = blob.rd(off, 2*n)
    return [dec15(struct.unpack_from('<H', b, 2*i)[0]) for i in range(n)]

def quantize(img, ncolors):
    """PNG -> (palette[<=ncolors] with palette[0]=transparent, index per pixel).
    Mirrors the tool: RGB rounded to 5 bits, transparent pixels share one slot."""
    img = img.convert('RGBA')
    px = list(img.getdata())
    opaque = [(r & ~7, g & ~7, b & ~7) for r, g, b, a in px if a]
    pal = [(0, 0, 0, 0)]
    if opaque:
        tmp = Image.new('RGB', (len(opaque), 1)); tmp.putdata(opaque)
        q = tmp.quantize(colors=ncolors-1, method=Image.Quantize.MEDIANCUT)
        p = q.getpalette()[:3*(ncolors-1)]
        used = sorted(set(q.getdata()))
        remap = {}
        for u in used:
            c = (p[3*u] & ~7, p[3*u+1] & ~7, p[3*u+2] & ~7, 255)
            if c[:3] == (0, 0, 0): c = (8, 8, 8, 255)
            if c not in pal: pal.append(c)
            remap[u] = pal.index(c)
        qi = iter(q.getdata())
    idx = []
    for r, g, b, a in px:
        idx.append(0 if not a else remap[next(qi)])
    return pal, idx

# ---------------------------------------------------------------- dump
def paint(blob, tex, chunks, cw, ch, pal, keep=None, bpp=8):
    img = Image.new('RGBA', (cw, ch), (0, 0, 0, 0)); p = img.load()
    for dx, dy, cx, cy, w, h in chunks:
        for y in range(h):
            row = blob.rd(tex + (dy+y)*ROWB + dx, w)
            for x in range(w):
                if bpp == 8:
                    i = row[x]
                    if keep is None or keep(i): p[cx+x, cy+y] = pal[i]
                else:
                    p[cx+2*x, cy+y] = pal[row[x] & 15]; p[cx+2*x+1, cy+y] = pal[row[x] >> 4]
    return img

def cmd_dump(a):
    blob = Blob(a.file); tex, clut = BUNDLES[a.bundle]
    os.makedirs(a.outdir, exist_ok=True)
    pal = read_clut(blob, clut + 512*(CLUT_ROW_BIG + a.clut))
    paint(blob, tex, FACE, FACE_W, FACE_H, pal).save(f'{a.outdir}/face_full.png')
    paint(blob, tex, FACE, FACE_W, FACE_H, pal, lambda i: i < DYN_N).save(f'{a.outdir}/face_dynamic.png')
    paint(blob, tex, FACE, FACE_W, FACE_H, pal,
          lambda i: STA0 <= i < STA0+STA_N_A or STA_B0 <= i < STA_B0+STA_N_B).save(f'{a.outdir}/face_static.png')
    paint(blob, tex, SLEEVE, SLEEVE_W, SLEEVE_H, pal).save(f'{a.outdir}/sleeve.png')
    tp = read_clut(blob, clut + 512*CLUT_ROW_BIG + 2*TXT_CLUT, 16)
    paint(blob, tex, TEXT, TEXT_W, TEXT_H, tp, bpp=4).save(f'{a.outdir}/text_4bpp.png')
    # the four VRAM pages (768..1024, 256..512) side by side, and all 16 CLUT rows
    pages = Image.new('RGBA', (512, 256)); pp = pages.load()
    for pg in range(4):
        for y in range(256):
            row = blob.rd(tex + (pg*256+y)*ROWB, ROWB)
            for x in range(ROWB): pp[pg*128+x, y] = pal[row[x]]
    pages.save(f'{a.outdir}/vram_pages_768_256.png')
    ci = Image.new('RGBA', (256, 16)); cp = ci.load()
    for r in range(16):
        for x, c in enumerate(read_clut(blob, clut + 512*r)): cp[x, r] = c
    ci.resize((512, 128), Image.NEAREST).save(f'{a.outdir}/clut_block.png')
    with open(f'{a.outdir}/clut_rows.txt', 'w') as f:
        for r in range(16):
            f.write(f'row {r:2d} (VRAM y={240+r}): ' +
                    ' '.join('%04X' % struct.unpack_from('<H', blob.rd(clut+512*r, 512), 2*i)[0] for i in range(256)) + '\n')
    print('wrote', a.outdir, 'from', BUNDLE_NAMES[a.bundle], 'tex @0x%X clut @0x%X' % (tex, clut))

def cmd_verify(a):
    blob = Blob(a.file)
    t0, c0 = BUNDLES[0]
    ref_tex = blob.rd(t0, 0x20000); ref_clut = blob.rd(c0, 0x2000)
    print('bundle                 tex@      sector  face+sleeve(rows0-592) rows592-1024 clut-row8,10-15 clut-other')
    for i, (t, c) in enumerate(BUNDLES):
        tx = blob.rd(t, 0x20000); cl = blob.rd(c, 0x2000)
        same_a = tx[:592*ROWB] == ref_tex[:592*ROWB]
        same_b = tx[592*ROWB:] == ref_tex[592*ROWB:]
        rows_same = [cl[512*r:512*r+512] == ref_clut[512*r:512*r+512] for r in range(16)]
        big_ok = rows_same[8] and all(rows_same[10:16])
        other = ''.join('=' if s else 'x' for s in rows_same)
        print(f'{BUNDLE_NAMES[i]:22s} 0x{t:07X} {t//2048:6d}  {"same" if same_a else "DIFF":22s} {"same" if same_b else "DIFF":12s} {"same" if big_ok else "DIFF":15s} {other}')
    print('md5 rows0-592 (bundle0):', hashlib.md5(ref_tex[:592*ROWB]).hexdigest())

# ---------------------------------------------------------------- apply / restore
class Patcher:
    def __init__(self, blob):
        self.blob = blob; self.bak = []
    def write(self, off, b):
        self.bak.append((off, bytes(self.blob.rd(off, len(b))))); self.blob.wr(off, b)
    def save_bak(self, path):
        if os.path.exists(path):
            old = load_bak(path); self.bak = old + self.bak     # keep the oldest bytes first
        with open(path, 'wb') as f:
            for off, b in self.bak: f.write(struct.pack('<II', off, len(b)) + b)
def load_bak(path):
    d = open(path, 'rb').read(); i = 0; out = []
    while i < len(d):
        off, n = struct.unpack_from('<II', d, i); out.append((off, d[i+8:i+8+n])); i += 8+n
    return out

def write_pixels(p, tex, chunks, cw, idx, base, only_opaque, pal):
    for dx, dy, cx, cy, w, h in chunks:
        for y in range(h):
            row = bytearray(p.blob.rd(tex + (dy+y)*ROWB + dx, w))
            for x in range(w):
                i = idx[(cy+y)*cw + cx + x]
                if only_opaque and pal[i][3] == 0: continue
                row[x] = base[i] if isinstance(base, list) else base + i
            p.write(tex + (dy+y)*ROWB + dx, bytes(row))

def write_clut(p, clut, rows, first_index, pal):
    b = b''.join(struct.pack('<H', enc15(c)) for c in pal)
    for r in rows: p.write(clut + 512*r + 2*first_index, b)

def parse_rows(s):
    lo, _, hi = s.partition('-'); hi = hi or lo
    return list(range(int(lo), int(hi)+1))

def cmd_apply(a):
    blob = Blob(a.file, write=True); p = Patcher(blob)
    rows = [CLUT_ROW_BIG + k for k in parse_rows(a.clut_rows)]
    if a.dynamic:
        img = Image.open(a.dynamic); assert img.size == (FACE_W, FACE_H), 'dynamic must be 144x264'
        pal, idx = quantize(img, DYN_N)
        for tex, clut in BUNDLES:
            write_clut(p, clut, rows, DYN0, pal)
            write_pixels(p, tex, FACE, FACE_W, idx, DYN0, False, pal)
    if a.static:
        img = Image.open(a.static); assert img.size == (FACE_W, FACE_H), 'static must be 144x264'
        pal, idx = quantize(img, STA_N_A + STA_N_B)
        base = [STA0 + i if i < STA_N_A else STA_B0 + (i - STA_N_A) for i in range(len(pal))]
        for tex, clut in BUNDLES:
            write_clut(p, clut, rows, STA0, pal[:STA_N_A])
            if len(pal) > STA_N_A: write_clut(p, clut, rows, STA_B0, pal[STA_N_A:])
            write_pixels(p, tex, FACE, FACE_W, idx, base, True, pal)
    if a.sleeve:
        img = Image.open(a.sleeve); assert img.size == (SLEEVE_W, SLEEVE_H), 'sleeve must be 144x200'
        pal, idx = quantize(img, SLV_N)
        for tex, clut in BUNDLES:
            write_clut(p, clut, rows, SLV0, pal)
            write_pixels(p, tex, SLEEVE, SLEEVE_W, idx, SLV0, False, pal)
    if a.clean_text:
        for tex, clut in BUNDLES: p.write(tex + TEXT_ROW0*ROWB, bytes(TEXT_ROWS*ROWB))
    p.save_bak(a.file + '.cardsleeves.bak'); blob.save()
    print('patched', len(p.bak), 'ranges in', a.file, '; backup ->', a.file + '.cardsleeves.bak')

def cmd_restore(a):
    blob = Blob(a.file, write=True); bak = a.file + '.cardsleeves.bak'
    if not os.path.exists(bak): sys.exit('no ' + bak)
    for off, b in reversed(load_bak(bak)): blob.wr(off, b)
    blob.save(); os.remove(bak); print('restored', a.file)

def cmd_positions(a):
    d = bytearray(open(a.file, 'rb').read())
    if a.restore:
        for n, ox, oy, sx, sy in POS: d[ox] = sx; d[oy] = sy
    for s in a.set or []:
        n, _, v = s.partition('='); x, y = (int(t) for t in v.split(','))
        ent = next(e for e in POS if e[0] == n); d[ent[1]] = x; d[ent[2]] = y
    for n, ox, oy, sx, sy in POS:
        wx = struct.unpack_from('<I', d, ox & ~3)[0]; wy = struct.unpack_from('<I', d, oy & ~3)[0]
        print(f'{n:6s} x={d[ox]:3d} (file 0x{ox:X} RAM 0x{0x80010000+ox-0x800:08X} word {wx:08X}, stock {sx})'
              f'  y={d[oy]:3d} (file 0x{oy:X} RAM 0x{0x80010000+oy-0x800:08X} word {wy:08X}, stock {sy})')
    if a.set or a.restore:
        open(a.file, 'wb').write(d); print('written', a.file)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('dump'); s.add_argument('file'); s.add_argument('outdir')
    s.add_argument('--bundle', type=int, default=0); s.add_argument('--clut', type=int, default=0); s.set_defaults(f=cmd_dump)
    s = sp.add_parser('verify'); s.add_argument('file'); s.set_defaults(f=cmd_verify)
    s = sp.add_parser('apply'); s.add_argument('file'); s.add_argument('--dynamic'); s.add_argument('--static')
    s.add_argument('--sleeve'); s.add_argument('--clut-rows', default='0-6'); s.add_argument('--clean-text', action='store_true')
    s.set_defaults(f=cmd_apply)
    s = sp.add_parser('restore'); s.add_argument('file'); s.set_defaults(f=cmd_restore)
    s = sp.add_parser('positions'); s.add_argument('file'); s.add_argument('--set', action='append')
    s.add_argument('--restore', action='store_true'); s.set_defaults(f=cmd_positions)
    a = ap.parse_args(); a.f(a)

if __name__ == '__main__':
    main()
