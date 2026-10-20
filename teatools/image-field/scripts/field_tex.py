#!/usr/bin/env python3
"""Offline clone of TEA-Online's FIELD tool: the 7 duel-field floor textures in
WA_MRG.MRG (one per terrain), the terrain power-bonus table in SLUS_014.11, and the
4bpp duel-UI atlas the site calls "Image Name" (field-name banners).

  field_tex.py inspect  <wa>
  field_tex.py export   <wa> <t> <out.png>              t = terrain 0..6 -> 256x254 png (top 104 | bottom 104 | middle 46)
  field_tex.py import   <wa.mrg> <t> <in.png> <out.mrg>  (16 colours per part, three CLUTs)
  field_tex.py restore  <wa.mrg> <t|all|atlas> --stock <stock wa or .bin> <out.mrg>
  field_tex.py verify   <wa> --stock <stock>
  field_tex.py boost    <SLUS_014.11>                   print the 20x6 terrain bonus table
  field_tex.py set-boost <SLUS_014.11> <type> <terrain> <bonus> [...] <out.11>   bonus in steps of 10, -1280..1270
  field_tex.py restore-boost <SLUS_014.11> --stock <stock SLUS> <out.11>
  field_tex.py export-atlas <wa> <out.png>              the 56x168 "Image Name" canvas (site chunk map)
  field_tex.py import-atlas <wa.mrg> <in.png> <out.mrg>

Terrains: 0 arena (no field), 1 Forest, 2 Wasteland, 3 Mountain, 4 Sogen, 5 Umi, 6 Yami.
<wa> is a WA_MRG.MRG (read/write) or the MODE2/2352 .bin (read-only, WA at LBA 10102).
"""
import argparse, os, struct, sys
from PIL import Image

WA_LBA, WA_SIZE = 10102, 0x2400000
OVL_SECTOR, OVL_COUNT = 0x16C6, 235             # func_8001798C: func_80014E1C(0,0, gDuel_bTerrain*235 + 0x16C6, 0xEB, ...)
TEX_SECTOR_IN_OVL = 203                          # terrain-specific tail: sectors 203..234 differ between the 7 copies
TEX_BASE = (OVL_SECTOR + TEX_SECTOR_IN_OVL) * 2048     # 0xBC8800 (the site's body_offset)
TEX_STRIDE = OVL_COUNT * 2048                    # 0x75800  (the site's `move`)
TEX_ROWS, TEX_SIZE = 256, 0x8000                 # 16 sectors: 254 rows of 4bpp (256 px) + 2 rows holding 8 CLUT slots
CLUT_IN_TEX = 0x7F00                             # row 254 (the site's header_offset = body + 0x7F00)
PARTS = [  # name, strip row0, rows, CLUT slots written (the site duplicates top/bottom into two slots)
    ("top", 0, 104, (0, 1)), ("bottom", 104, 104, (2, 3)), ("middle", 208, 46, (4,))]
TERRAIN = ["arena", "Forest", "Wasteland", "Mountain", "Sogen", "Umi", "Yami"]
BOOST_FILE = 0x811D4                             # gDuel_aTerrainBoost 0x800909D4: s8[20][6], value*10, [type*6 + terrain-1]
TYPES, TERRAINS = 20, 6
NAME_TABLE_FILE, NAME_BASE_FILE = 0x1C6000, 0x1C0800   # global text bank (type names are ids 768..787)
ATLAS_BODY, ATLAS_CLUT = 0xB51000, 0xB609A0      # site: 11866112 / 11930016 (4bpp, 16 colours, greyscale ramp)
ATLAS_CANVAS = (56, 168)
# (strip_px_x, strip_row, w, h, canvas_x, canvas_y) -- the site's `w` chunk list, x converted from bytes to 4bpp pixels
ATLAS_CHUNKS = [(24,64,8,24,0,0),(32,64,8,24,48,0),(40,64,24,24,8,0),(48,64,16,24,32,0),(24,56,40,8,8,0),(112,32,16,16,20,8),
    (24,64,8,24,0,24),(32,64,8,24,48,24),(40,64,24,24,8,24),(48,64,16,24,32,24),(24,56,40,8,8,24),(64,80,32,16,12,32),
    (24,64,8,24,0,48),(32,64,8,24,48,48),(40,64,24,24,8,48),(48,64,16,24,32,48),(24,56,40,8,8,48),(96,48,32,16,4,56),(112,0,16,16,36,56),
    (24,64,8,24,0,72),(32,64,8,24,48,72),(40,64,24,24,8,72),(48,64,16,24,32,72),(24,56,40,8,8,72),(64,64,32,16,4,80),(112,64,16,16,36,80),
    (24,64,8,24,0,96),(32,64,8,24,48,96),(40,64,24,24,8,96),(48,64,16,24,32,96),(24,56,40,8,8,96),(64,48,32,16,4,104),(112,16,16,16,36,104),
    (24,64,8,24,0,120),(32,64,8,24,48,120),(40,64,24,24,8,120),(48,64,16,24,32,120),(24,56,40,8,8,120),(96,80,24,16,16,128),
    (24,64,8,24,0,144),(32,64,8,24,48,144),(40,64,24,24,8,144),(48,64,16,24,32,144),(24,56,40,8,8,144),(96,64,16,16,16,152),(120,80,8,16,32,152)]
CHARSET = {3:"a",21:"b",15:"c",12:"d",1:"e",19:"f",16:"g",9:"h",5:"i",52:"j",22:"k",10:"l",14:"m",6:"n",4:"o",20:"p",55:"q",8:"r",7:"s",2:"t",
    13:"u",25:"v",18:"w",54:"x",17:"y",50:"z",24:"A",45:"B",43:"C",32:"D",37:"E",49:"F",41:"G",35:"H",26:"I",59:"J",51:"K",42:"L",30:"M",44:"N",
    33:"O",47:"P",62:"Q",38:"R",29:"S",28:"T",53:"U",57:"V",34:"W",70:"X",36:"Y",63:"Z",48:"-",27:"'",0:" ",11:".",23:"!",46:"?"}

class Wa:
    def __init__(self, path):
        self.path, size = path, os.path.getsize(path)
        if size == WA_SIZE: self.kind, self.data = "mrg", bytearray(open(path, "rb").read())
        elif size % 2352 == 0 and size > 16 * 2352:
            self.kind, self.f = "bin", open(path, "rb"); self.f.seek(16 * 2352 + 25)
            if self.f.read(5) != b"CD001": sys.exit(f"{path}: not a MODE2/2352 ISO image")
        else: sys.exit(f"{path}: expected WA_MRG.MRG ({WA_SIZE} bytes) or a .bin disc image")
    def read(self, off, n):
        if self.kind == "mrg": return bytes(self.data[off:off + n])
        out, lba, skip = bytearray(), WA_LBA + off // 2048, off % 2048
        while len(out) < skip + n: self.f.seek(lba * 2352 + 24); out += self.f.read(2048); lba += 1
        return bytes(out[skip:skip + n])
    def write(self, off, b):
        if self.kind != "mrg": sys.exit("cannot write into a disc image; extract WA_MRG.MRG first")
        self.data[off:off + len(b)] = b
    def save(self, path): open(path, "wb").write(self.data); print("wrote", path)

def clut_decode(b, n):
    out = []
    for i in range(n):
        w = b[2*i] | (b[2*i+1] << 8)
        out.append(((w & 31) << 3, ((w >> 5) & 31) << 3, ((w >> 10) & 31) << 3, 0 if w == 0 else 255))
    return out

def clut_encode(colors, transparent0=False):
    """Stock field CLUTs: no STP bits, no zero entries (black is stored as 0x0421-ish dark)."""
    out = bytearray()
    for k, (r, g, b, a) in enumerate(colors):
        w = 0 if (transparent0 and k == 0) else (r >> 3) | (g >> 3) << 5 | (b >> 3) << 10
        if w == 0 and not (transparent0 and k == 0): w = 0x0421
        out += bytes((w & 0xFF, w >> 8))
    return bytes(out)

def quantize(img, ncolors, transparent=False):
    """-> (indices, RGBA palette[ncolors]); alpha<128 -> index 0 when `transparent`.
    Exact when the image already fits the palette, otherwise median cut."""
    img = img.convert("RGBA"); w, h = img.size; raw = img.tobytes()
    px = [raw[i:i + 4] for i in range(0, len(raw), 4)]
    mask = [p[3] < 128 for p in px] if transparent else [False] * len(px)
    anyt = any(mask); k = ncolors - (1 if anyt else 0)
    distinct = sorted({p[:3] for p, m in zip(px, mask) if not m})
    if len(distinct) <= k:
        lut = {c: i for i, c in enumerate(distinct)}
        palette = [(c[0], c[1], c[2], 255) for c in distinct]; idx = [0 if m else lut[p[:3]] for p, m in zip(px, mask)]
    else:
        rgb = img.convert("RGB")
        if anyt:
            pl, fill = rgb.load(), next(p[:3] for p, m in zip(px, mask) if not m)
            for i, m in enumerate(mask):
                if m: pl[i % w, i // w] = fill
        q = rgb.quantize(colors=k, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        pal = q.getpalette() or []
        palette = [(pal[3*i], pal[3*i+1], pal[3*i+2], 255) for i in range(min(k, len(pal) // 3))]; idx = list(q.tobytes())
    if anyt: palette = [(0, 0, 0, 0)] + palette; idx = [0 if m else i + 1 for i, m in zip(idx, mask)]
    return idx, (palette + [(0, 0, 0, 255)] * ncolors)[:ncolors]

def get4(strip, x, y):
    b = strip[y * 128 + x // 2]; return b & 15 if x % 2 == 0 else b >> 4
def set4(strip, x, y, v):
    i = y * 128 + x // 2; strip[i] = (strip[i] & 0xF0) | v if x % 2 == 0 else (strip[i] & 0x0F) | (v << 4)

def tex_off(t):
    if not 0 <= t < 7: sys.exit("terrain must be 0..6")
    return TEX_BASE + t * TEX_STRIDE

def tex_image(wa, t):
    off = tex_off(t); strip = wa.read(off, TEX_SIZE); cl = strip[CLUT_IN_TEX:CLUT_IN_TEX + 256]
    img = Image.new("RGBA", (256, 254))
    for name, row0, rows, slots in PARTS:
        pal = clut_decode(cl[slots[0] * 32:slots[0] * 32 + 32], 16)
        for y in range(rows):
            for x in range(256): img.putpixel((x, row0 + y), pal[get4(strip, x, row0 + y)])
    return img

# ---------------------------------------------------------------- commands
def cmd_inspect(a):
    wa = Wa(a.wa)
    print(f"duel overlay copies: 7 x {OVL_COUNT} sectors from in-file sector 0x{OVL_SECTOR:X} (WA 0x{OVL_SECTOR*2048:X}, disc LBA {WA_LBA+OVL_SECTOR}); "
          f"terrain t loads sector 0x{OVL_SECTOR:X}+t*{OVL_COUNT}")
    for t in range(7):
        off = tex_off(t); sec = off // 2048; cl = wa.read(off + CLUT_IN_TEX, 256)
        used = [k for k in range(8) if any(cl[k*32:k*32+32])]
        print(f"  t={t} {TERRAIN[t]:9s} texture WA 0x{off:X} (sector 0x{sec:X}, LBA {WA_LBA+sec}) 16 sectors, 4bpp 256x254 + CLUT slots {used} at +0x{CLUT_IN_TEX:X}")
    print(f"'Image Name' atlas: WA 0x{ATLAS_BODY:X} (sector 0x{ATLAS_BODY//2048:X}, LBA {WA_LBA+ATLAS_BODY//2048}), 4bpp, CLUT at 0x{ATLAS_CLUT:X}")
    if wa.kind == "mrg":
        b0 = wa.read(OVL_SECTOR * 2048, TEX_STRIDE)
        for t in range(1, 7):
            bt = wa.read((OVL_SECTOR) * 2048 + t * TEX_STRIDE, TEX_STRIDE)
            diff = [s for s in range(OVL_COUNT) if b0[s*2048:(s+1)*2048] != bt[s*2048:(s+1)*2048]]
            print(f"  copy {t} vs copy 0: differing sectors {diff}")

def cmd_export(a):
    wa = Wa(a.wa); t = int(a.which); tex_image(wa, t).save(a.out); print(f"terrain {t} ({TERRAIN[t]}) @0x{tex_off(t):X} -> {a.out} (256x254: top 0..103, bottom 104..207, middle 208..253)")

def cmd_import(a):
    wa = Wa(a.wa); t = int(a.which); img = Image.open(a.png).convert("RGBA")
    if img.size != (256, 254): sys.exit(f"field image must be 256x254 (top 104 + bottom 104 + middle 46 rows), got {img.size[0]}x{img.size[1]}")
    off = tex_off(t); strip = bytearray(wa.read(off, TEX_SIZE))
    for name, row0, rows, slots in PARTS:
        idx, pal = quantize(img.crop((0, row0, 256, row0 + rows)), 16)
        for y in range(rows):
            for x in range(256): set4(strip, x, row0 + y, idx[y * 256 + x])
        for s in slots: strip[CLUT_IN_TEX + 32*s:CLUT_IN_TEX + 32*s + 32] = clut_encode(pal)
    wa.write(off, strip); wa.save(a.out); print(f"terrain {t} ({TERRAIN[t]}): wrote 3 parts + CLUT slots 0,1 / 2,3 / 4")

def cmd_restore(a):
    wa, stock = Wa(a.wa), Wa(a.stock)
    if a.which in ("atlas", "all"):
        wa.write(ATLAS_BODY, stock.read(ATLAS_BODY, 128 * 100)); wa.write(ATLAS_CLUT, stock.read(ATLAS_CLUT, 32)); print("restored atlas")
    ts = range(7) if a.which == "all" else [] if a.which == "atlas" else [int(a.which)]
    for t in ts: wa.write(tex_off(t), stock.read(tex_off(t), TEX_SIZE))
    wa.save(a.out); print("restored terrains", list(ts))

def cmd_verify(a):
    wa, stock = Wa(a.wa), Wa(a.stock)
    bad = [t for t in range(7) if wa.read(tex_off(t), TEX_SIZE) != stock.read(tex_off(t), TEX_SIZE)]
    if wa.read(ATLAS_BODY, 128 * 100) != stock.read(ATLAS_BODY, 128 * 100) or wa.read(ATLAS_CLUT, 32) != stock.read(ATLAS_CLUT, 32): bad.append("atlas")
    print("all stock" if not bad else f"differs from stock: {bad}")

def type_names(slus):
    out = []
    for n in range(768, 768 + TYPES):
        p = NAME_BASE_FILE + struct.unpack_from("<H", slus, NAME_TABLE_FILE + 2 * n)[0]; s = ""
        while slus[p] != 0xFF: s += CHARSET.get(slus[p], "?"); p += 1
        out.append(s)
    return out

def cmd_boost(a):
    slus = open(a.wa, "rb").read(); names = type_names(slus)
    print(f"gDuel_aTerrainBoost: SLUS file 0x{BOOST_FILE:X} = RAM 0x800909D4, s8[type][terrain-1] * 10")
    print("type              " + "".join(f"{TERRAIN[t]:>10s}" for t in range(1, 7)))
    for ty in range(TYPES):
        row = struct.unpack_from("<6b", slus, BOOST_FILE + 6 * ty)
        print(f"{ty:2d} {names[ty]:15s}" + "".join(f"{10*v:>10d}" for v in row))

def cmd_set_boost(a):
    slus = bytearray(open(a.wa, "rb").read())
    for ty, te, v in a.triples:
        ty, te, v = int(ty), int(te), int(v)
        if not (0 <= ty < TYPES and 1 <= te <= 6 and -1280 <= v <= 1270 and v % 10 == 0): sys.exit("type 0..19, terrain 1..6, bonus multiple of 10 in -1280..1270")
        struct.pack_into("<b", slus, BOOST_FILE + 6 * ty + te - 1, v // 10)
    open(a.out, "wb").write(slus); print("wrote", a.out)

def cmd_restore_boost(a):
    slus = bytearray(open(a.wa, "rb").read()); stock = open(a.stock, "rb").read()
    slus[BOOST_FILE:BOOST_FILE + 120] = stock[BOOST_FILE:BOOST_FILE + 120]; open(a.out, "wb").write(slus); print("wrote", a.out)

def cmd_export_atlas(a):
    wa = Wa(a.wa); strip = wa.read(ATLAS_BODY, 128 * 100); pal = clut_decode(wa.read(ATLAS_CLUT, 32), 16)
    img = Image.new("RGBA", ATLAS_CANVAS, (0, 0, 0, 0))
    for sx, sy, w, h, cx, cy in ATLAS_CHUNKS:
        for y in range(h):
            for x in range(w): img.putpixel((cx + x, cy + y), pal[get4(strip, sx + x, sy + y)])
    img.save(a.out); print("wrote", a.out, f"({ATLAS_CANVAS[0]}x{ATLAS_CANVAS[1]} canvas assembled from {len(ATLAS_CHUNKS)} atlas pieces)")

def cmd_import_atlas(a):
    wa = Wa(a.wa); img = Image.open(a.png).convert("RGBA")
    if img.size != ATLAS_CANVAS: sys.exit(f"atlas canvas must be {ATLAS_CANVAS[0]}x{ATLAS_CANVAS[1]}")
    idx, pal = quantize(img, 16, transparent=True)
    strip = bytearray(wa.read(ATLAS_BODY, 128 * 100))
    for sx, sy, w, h, cx, cy in ATLAS_CHUNKS:
        for y in range(h):
            for x in range(w): set4(strip, sx + x, sy + y, idx[(cy + y) * ATLAS_CANVAS[0] + cx + x])
    wa.write(ATLAS_BODY, strip); wa.write(ATLAS_CLUT, clut_encode(pal, transparent0=True)); wa.save(a.out)
    print("wrote atlas pieces + 16-colour CLUT (entry 0 transparent, as stock)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["inspect", "export", "import", "restore", "verify", "boost", "set-boost", "restore-boost", "export-atlas", "import-atlas"])
    ap.add_argument("wa", help="WA_MRG.MRG / disc .bin, or SLUS_014.11 for the boost commands")
    ap.add_argument("rest", nargs="*"); ap.add_argument("--stock")
    a, extra = ap.parse_known_args(); a.rest += extra; r = a.rest   # --stock may sit anywhere
    need = lambda n, u: (len(r) == n) or sys.exit("usage: " + u)
    if a.cmd == "inspect": cmd_inspect(a)
    elif a.cmd == "export": need(2, "export <wa> <t> <out.png>"); a.which, a.out = r; cmd_export(a)
    elif a.cmd == "import":
        need(3, "import <wa.mrg> <t> <in.png> <out.mrg>")
        if r[2] == a.wa: sys.exit("give an output path different from the input")
        a.which, a.png, a.out = r; cmd_import(a)
    elif a.cmd == "restore": need(2, "restore <wa.mrg> <t|all> --stock <stock> <out.mrg>"); a.which, a.out = r; cmd_restore(a)
    elif a.cmd == "verify": a.stock or sys.exit("verify needs --stock"); cmd_verify(a)
    elif a.cmd == "boost": cmd_boost(a)
    elif a.cmd == "set-boost":
        if len(r) < 4 or (len(r) - 1) % 3: sys.exit("usage: set-boost <SLUS> <type> <terrain> <bonus> [...] <out.11>")
        a.triples, a.out = [r[i:i+3] for i in range(0, len(r) - 1, 3)], r[-1]; cmd_set_boost(a)
    elif a.cmd == "restore-boost": need(1, "restore-boost <SLUS> --stock <stock SLUS> <out.11>"); a.out = r[0]; cmd_restore_boost(a)
    elif a.cmd == "export-atlas": need(1, "export-atlas <wa> <out.png>"); a.out = r[0]; cmd_export_atlas(a)
    elif a.cmd == "import-atlas":
        need(2, "import-atlas <wa.mrg> <in.png> <out.mrg>")
        if r[1] == a.wa: sys.exit("give an output path different from the input")
        a.png, a.out = r; cmd_import_atlas(a)
