#!/usr/bin/env python3
"""Offline clone of TEA-Online "Campaign Characters" (extend/tools/image/campaign/characters).

Each of the 64 campaign dialogue portraits is a 50-sector (0x19000 B) block in
WA_MRG.MRG at 0x1DC0000 + 0x19000*(id-1)  (disc LBA 25334 + 50*(id-1)):

    +0x00000  0x18000  8bpp image, 128-byte rows, 768 rows = three 128x256 VRAM pages
                        streamed to (832-192*side, 256), (896-.., 256), (960-.., 256)
    +0x18000  0x200    CLUT A (256 x 15-bit, STP clear)  -> VRAM (512, 240+2*side)
    +0x18200  0x200    CLUT B (same colours, STP set)    -> VRAM (512, 241+2*side)
    +0x18400  0x400    zero
    +0x18800  0x800    sprite/animation script (copied to RAM 0x801AF000 / 0x801AF800)
    +0x19000  ..       (0x18900.. is 0xFF padding inside the last sector)

    campaign_portraits.py list
    campaign_portraits.py dump    WA_MRG.MRG ID OUTDIR [--template T]
    campaign_portraits.py apply   WA_MRG.MRG ID PNG [--template T | --raw] [--key R,G,B]
    campaign_portraits.py restore WA_MRG.MRG            (from WA_MRG.MRG.portraits.bak)

--raw: PNG is 384x256 = the three pages side by side (what the game shows in
VRAM).  --template T: PNG is the tool's canvas for template T (1..6) and is cut
into the block with the tool's chunk table; the tool's canned animation script
for that template is written at +0x18800 and its 'da' regions are zeroed.
"""
import argparse, warnings, json, os, struct, sys
warnings.filterwarnings("ignore", category=DeprecationWarning)   # Pillow getdata()
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(os.path.join(HERE, 'templates.json')))
WA_LBA = 10102
BASE, STRIDE, NCHAR = 0x1DC0000, 0x19000, 64
IMG_BYTES, CLUT_A, CLUT_B, SCRIPT = 0x18000, 0x18000, 0x18200, 0x18800
ROWB, PAGES = 128, 3

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

def dec15(v): return ((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3, 0 if v == 0 else 255)
def enc15(c, stp):
    r, g, b, a = c
    if a == 0: return 0
    if (r, g, b) == (0, 0, 0): r = g = b = 8
    return (0x8000 if stp else 0) | (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)

def quantize(img, key=None):
    img = img.convert('RGBA'); px = list(img.getdata())
    if key: px = [(0, 0, 0, 0) if (r, g, b) == key else (r, g, b, a) for r, g, b, a in px]
    opaque = [(r & ~7, g & ~7, b & ~7) for r, g, b, a in px if a]
    pal = [(0, 0, 0, 0)]; remap = {}
    if opaque:
        tmp = Image.new('RGB', (len(opaque), 1)); tmp.putdata(opaque)
        q = tmp.quantize(colors=255, method=Image.Quantize.MEDIANCUT); p = q.getpalette()
        for u in sorted(set(q.getdata())):
            c = (p[3*u] & ~7, p[3*u+1] & ~7, p[3*u+2] & ~7, 255)
            if c[:3] == (0, 0, 0): c = (8, 8, 8, 255)
            if c not in pal: pal.append(c)
            remap[u] = pal.index(c)
        qi = iter(q.getdata())
    idx = [0 if not a else remap[next(qi)] for r, g, b, a in px]
    return pal, idx

def block(cid):
    if not 1 <= cid <= NCHAR: sys.exit('id must be 1..64')
    return BASE + STRIDE*(cid-1)

def cmd_list(a):
    for k in range(1, NCHAR+1):
        off = block(k)
        print(f'{k:2d}  [F6 {k:02X} 00]  WA 0x{off:07X}  LBA {WA_LBA + off//2048}  {T["characters"][str(k)]}')
    print('templates:', ', '.join(f'{k}={v["name"]} ({v["w"]}x{v["h"]})' for k, v in T['templates'].items()))

def cmd_dump(a):
    blob = Blob(a.file); b = block(a.id); os.makedirs(a.outdir, exist_ok=True)
    pal = [dec15(v) for v in struct.unpack('<256H', blob.rd(b + CLUT_A, 512))]
    img = Image.new('RGBA', (128*PAGES, 256)); p = img.load()
    for pg in range(PAGES):
        for y in range(256):
            row = blob.rd(b + (pg*256+y)*ROWB, ROWB)
            for x in range(ROWB): p[pg*128+x, y] = pal[row[x]]
    img.save(f'{a.outdir}/raw_384x256.png')
    open(f'{a.outdir}/script.bin', 'wb').write(blob.rd(b + SCRIPT, 0x800))
    with open(f'{a.outdir}/clut.txt', 'w') as f:
        for name, off in (('A', CLUT_A), ('B', CLUT_B)):
            f.write(name + ': ' + ' '.join('%04X' % v for v in struct.unpack('<256H', blob.rd(b+off, 512))) + '\n')
    if a.template:
        t = T['templates'][str(a.template)]
        canvas = Image.new('RGBA', (t['w'], t['h'])); c = canvas.load()
        for dx, dy, cx, cy, w, h in T['chunks'][t['chunks']]:
            for y in range(h):
                row = blob.rd(b + (dy+y)*ROWB + dx, w)
                for x in range(w): c[cx+x, cy+y] = pal[row[x]]
        canvas.save(f'{a.outdir}/template{a.template}_{t["w"]}x{t["h"]}.png')
    print('wrote', a.outdir, 'for', a.id, T['characters'][str(a.id)])

class Patcher:
    def __init__(self, blob): self.blob = blob; self.bak = []
    def write(self, off, b):
        self.bak.append((off, bytes(self.blob.rd(off, len(b))))); self.blob.wr(off, b)
def load_bak(path):
    d = open(path, 'rb').read(); i = 0; out = []
    while i < len(d):
        off, n = struct.unpack_from('<II', d, i); out.append((off, d[i+8:i+8+n])); i += 8+n
    return out

def cmd_apply(a):
    blob = Blob(a.file, write=True); p = Patcher(blob); b = block(a.id)
    key = tuple(int(x) for x in a.key.split(',')) if a.key else None
    img = Image.open(a.png)
    pal, idx = quantize(img, key)
    p.write(b + CLUT_A, b''.join(struct.pack('<H', enc15(c, False)) for c in pal + [(0, 0, 0, 0)]*(256-len(pal))))
    p.write(b + CLUT_B, b''.join(struct.pack('<H', enc15(c, True)) for c in pal + [(0, 0, 0, 0)]*(256-len(pal))))
    if a.template:
        t = T['templates'][str(a.template)]
        assert img.size == (t['w'], t['h']), f'template {a.template} needs {t["w"]}x{t["h"]}'
        for dx, dy, cx, cy, w, h in T['chunks'][t['chunks']]:
            for y in range(h):
                p.write(b + (dy+y)*ROWB + dx, bytes(idx[(cy+y)*t['w'] + cx + x] for x in range(w)))
        for x0, y0, x1, y1 in t['da']:                    # the tool's cleanBody()
            for y in range(y0, y1): p.write(b + y*ROWB + x0, bytes(x1-x0))
        com = bytes.fromhex(t['com']); p.write(b + SCRIPT, com)
    else:
        assert img.size == (128*PAGES, 256), 'raw PNG must be 384x256'
        for pg in range(PAGES):
            for y in range(256):
                p.write(b + (pg*256+y)*ROWB, bytes(idx[y*384 + pg*128 + x] for x in range(ROWB)))
    bak = a.file + '.portraits.bak'
    old = load_bak(bak) if os.path.exists(bak) else []
    with open(bak, 'wb') as f:
        for off, bb in old + p.bak: f.write(struct.pack('<II', off, len(bb)) + bb)
    blob.save(); print('patched character', a.id, 'with', len(pal), 'colours; backup ->', bak)

def cmd_restore(a):
    blob = Blob(a.file, write=True); bak = a.file + '.portraits.bak'
    if not os.path.exists(bak): sys.exit('no ' + bak)
    for off, bb in reversed(load_bak(bak)): blob.wr(off, bb)
    blob.save(); os.remove(bak); print('restored', a.file)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('list'); s.set_defaults(f=cmd_list)
    s = sp.add_parser('dump'); s.add_argument('file'); s.add_argument('id', type=int); s.add_argument('outdir')
    s.add_argument('--template', type=int); s.set_defaults(f=cmd_dump)
    s = sp.add_parser('apply'); s.add_argument('file'); s.add_argument('id', type=int); s.add_argument('png')
    s.add_argument('--template', type=int); s.add_argument('--raw', action='store_true'); s.add_argument('--key')
    s.set_defaults(f=cmd_apply)
    s = sp.add_parser('restore'); s.add_argument('file'); s.set_defaults(f=cmd_restore)
    a = ap.parse_args(); a.f(a)

if __name__ == '__main__':
    main()
