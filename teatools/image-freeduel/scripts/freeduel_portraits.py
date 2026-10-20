#!/usr/bin/env python3
"""Offline clone of TEA-Online's FREE DUEL image tool: the 40 opponent-grid
portraits in WA_MRG.MRG and the 40 grid names in SLUS_014.11.

  freeduel_portraits.py inspect  <wa>
  freeduel_portraits.py export   <wa> <i|all|sheet> <out.png>
  freeduel_portraits.py import   <wa.mrg> <i> <in.png> <out.mrg>
  freeduel_portraits.py restore  <wa.mrg> <i|all> --stock <stock wa or .bin> <out.mrg>
  freeduel_portraits.py verify   <wa> --stock <stock>
  freeduel_portraits.py names    <SLUS_014.11>
  freeduel_portraits.py rename   <SLUS_014.11> <i> "<name>" [<i> "<name>" ...] <out.11>
  freeduel_portraits.py restore-names <SLUS_014.11> --stock <stock SLUS> <out.11>
  freeduel_portraits.py export-screen <wa> <out.png>      (the grid screen's own 256x256 backdrop)

i = grid cell row*5+col = duelist id: 0 Build Deck tile, 1 Simon Muran .. 39 Duel Master K.
<wa> is a WA_MRG.MRG (read/write) or the MODE2/2352 .bin (read-only, WA at LBA 10102).
"""
import argparse, os, struct, sys
from PIL import Image

WA_LBA, WA_SIZE = 10102, 0x2400000
LOAD_SECTOR, LOAD_COUNT = 0x1E88, 0x57          # Main_InitFreeDuelMenu: func_80014E1C(0,0,0x1E88,0x57,func_8003B808,0,0)
TILES_SECTOR = LOAD_SECTOR + 34                 # arms 0..3 of func_8003B808: 32 VRAM + 1 CLUT + 1 RAM, then 48 -> 0x80100000
TILES_OFF = TILES_SECTOR * 2048                 # 0xF55000 (the site's 16076800)
TILE, IMG, CLUT_N, N = 2432, 2304, 64, 40
NAME_TABLE_FILE, NAME_BASE_FILE = 0x1C6000, 0x1C0800   # gText_aGlobalOffsets 0x801D5800, strings from 0x801D0000
NAME_ID0, NAME_IDN = 808, 848                   # string ids 0x8328.. (FreeDuel_PlaceCursor: 0x8328 + row*5+col)
CHARSET = {3:"a",21:"b",15:"c",12:"d",1:"e",19:"f",16:"g",9:"h",5:"i",52:"j",22:"k",10:"l",14:"m",6:"n",4:"o",20:"p",
    55:"q",8:"r",7:"s",2:"t",13:"u",25:"v",18:"w",54:"x",17:"y",50:"z",24:"A",45:"B",43:"C",32:"D",37:"E",49:"F",41:"G",
    35:"H",26:"I",59:"J",51:"K",42:"L",30:"M",44:"N",33:"O",47:"P",62:"Q",38:"R",29:"S",28:"T",53:"U",57:"V",34:"W",
    70:"X",36:"Y",63:"Z",48:"-",27:"'",64:'"',31:",",67:"&",85:"@",60:"#",68:"/",72:":",80:"*",81:">",84:"<",86:"+",
    23:"!",0:" ",56:"0",61:"1",58:"2",65:"3",74:"4",66:"5",78:"6",69:"7",87:"8",89:"9",11:".",76:"(",75:")",46:"?",39:"[",40:"]"}
REV = {v: k for k, v in CHARSET.items()}

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

def clut_encode(colors):
    """Stock portrait CLUTs set the STP bit on all 64 entries and store black as 0x8000."""
    out = bytearray()
    for r, g, b, a in colors:
        w = ((r >> 3) | (g >> 3) << 5 | (b >> 3) << 10) | 0x8000
        out += bytes((w & 0xFF, w >> 8))
    return bytes(out)

def quantize(img, ncolors):
    """Opaque quantize: exact when the image already has <= ncolors colours, else median cut."""
    rgb = img.convert("RGB"); raw = rgb.tobytes(); px = [raw[i:i + 3] for i in range(0, len(raw), 3)]
    distinct = sorted(set(px))
    if len(distinct) <= ncolors:
        lut = {c: i for i, c in enumerate(distinct)}; idx = [lut[p] for p in px]
        palette = [(c[0], c[1], c[2], 255) for c in distinct]
    else:
        q = rgb.quantize(colors=ncolors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        pal = q.getpalette() or []; k = min(ncolors, len(pal) // 3)
        palette = [(pal[3*i], pal[3*i+1], pal[3*i+2], 255) for i in range(k)]; idx = list(q.tobytes())
    return idx, palette + [(0, 0, 0, 255)] * (ncolors - len(palette))

def tile_off(i):
    if not 0 <= i < N: sys.exit("tile index must be 0..39")
    return TILES_OFF + i * TILE

def tile_image(wa, i):
    t = wa.read(tile_off(i), TILE); pal = clut_decode(t[IMG:], CLUT_N)
    img = Image.new("RGBA", (48, 48)); img.putdata([pal[p] if p < CLUT_N else (255, 0, 255, 255) for p in t[:IMG]])
    return img

def read_names(slus):
    ptr = [struct.unpack_from("<H", slus, NAME_TABLE_FILE + 2 * n)[0] for n in range(NAME_ID0, NAME_IDN + 1)]
    names = []
    for n in range(N):
        p = NAME_BASE_FILE + ptr[n]; s = ""
        while slus[p] != 0xFF: s += CHARSET.get(slus[p], "?"); p += 1
        names.append(s)
    return names, ptr

def encode_name(s):
    out = bytearray()
    for ch in s:
        if ch not in REV: sys.exit(f"character {ch!r} is not in the game's name charset")
        out.append(REV[ch])
    return bytes(out) + b"\xFF"

# ---------------------------------------------------------------- commands
def cmd_inspect(a):
    wa = Wa(a.wa)
    print(f"free-duel load: in-file sector 0x{LOAD_SECTOR:X} x {LOAD_COUNT} (WA 0x{LOAD_SECTOR*2048:X}..0x{(LOAD_SECTOR+LOAD_COUNT)*2048:X}, disc LBA {WA_LBA+LOAD_SECTOR}..{WA_LBA+LOAD_SECTOR+LOAD_COUNT-1})")
    print(f"portrait tiles: WA 0x{TILES_OFF:X} (sector 0x{TILES_SECTOR:X}, disc LBA {WA_LBA+TILES_SECTOR}), {N} x {TILE} bytes = 48x48 8bpp + 64-entry CLUT")
    for i in range(N):
        t = wa.read(tile_off(i), TILE); mx = max(t[:IMG]); c = t[IMG:]
        stp = sum(1 for k in range(CLUT_N) if c[2*k+1] & 0x80)
        print(f"  tile {i:2d}  0x{tile_off(i):X}  max index {mx:2d}  CLUT entries with STP {stp}/64")

def cmd_export(a):
    wa = Wa(a.wa)
    if a.which == "sheet":
        sheet = Image.new("RGBA", (48 * 8, 48 * 5))
        for i in range(N): sheet.paste(tile_image(wa, i), ((i % 8) * 48, (i // 8) * 48))
        sheet.save(a.out); print("wrote", a.out, "(8x5 sheet, index = row*8+col)")
    elif a.which == "all":
        base, ext = os.path.splitext(a.out)
        for i in range(N): tile_image(wa, i).save(f"{base}_{i:02d}{ext or '.png'}")
        print(f"wrote {base}_00..{N-1:02d}{ext or '.png'}")
    else:
        i = int(a.which); tile_image(wa, i).save(a.out); print(f"tile {i} @0x{tile_off(i):X} -> {a.out}")

def cmd_import(a):
    wa = Wa(a.wa); i = int(a.which)
    img = Image.open(a.png)
    if img.size != (48, 48): sys.exit(f"portrait must be 48x48, got {img.size[0]}x{img.size[1]}")
    idx, palette = quantize(img, CLUT_N)            # no transparency: the tile is a solid square
    wa.write(tile_off(i), bytes(idx) + clut_encode(palette)); wa.save(a.out)
    print(f"tile {i} @0x{tile_off(i):X}: wrote 2304 indices + 64-entry CLUT (STP set on all entries)")

def cmd_restore(a):
    wa, stock = Wa(a.wa), Wa(a.stock)
    ids = range(N) if a.which == "all" else [int(a.which)]
    for i in ids: wa.write(tile_off(i), stock.read(tile_off(i), TILE))
    wa.save(a.out); print("restored tiles", list(ids))

def cmd_verify(a):
    wa, stock = Wa(a.wa), Wa(a.stock)
    bad = [i for i in range(N) if wa.read(tile_off(i), TILE) != stock.read(tile_off(i), TILE)]
    print("all 40 tiles stock" if not bad else f"tiles differing from stock: {bad}")

def cmd_names(a):
    slus = open(a.wa, "rb").read(); names, ptr = read_names(slus)
    budget = ptr[N] - ptr[0]
    print(f"table: SLUS file 0x{NAME_TABLE_FILE:X}+2*id (RAM 0x801D5800), strings at file 0x{NAME_BASE_FILE:X}+off (RAM 0x801D0000+off)")
    print(f"ids {NAME_ID0}..{NAME_IDN-1} (0x{0x8000+NAME_ID0:X}..), string bytes 0x{ptr[0]:X}..0x{ptr[N]:X}: budget {budget} bytes incl. 40 terminators "
          f"= {budget-N} characters (used {sum(len(s) for s in names)})")
    for i, s in enumerate(names): print(f"  {i:2d} (row {i//5} col {i%5})  @0x{NAME_BASE_FILE+ptr[i]:X}  {s}")

def cmd_rename(a):
    slus = bytearray(open(a.wa, "rb").read()); names, ptr = read_names(slus)
    for i, s in a.pairs: names[int(i)] = s
    blob = b"".join(encode_name(s) for s in names)
    if len(blob) > ptr[N] - ptr[0]:
        sys.exit(f"names need {len(blob)} bytes, only {ptr[N]-ptr[0]} available (the string after id 847 starts there)")
    off = ptr[0]                                       # repack from the stock start, like the site
    for i, s in enumerate(names):
        struct.pack_into("<H", slus, NAME_TABLE_FILE + 2 * (NAME_ID0 + i), off); off += len(s) + 1
    slus[NAME_BASE_FILE + ptr[0]:NAME_BASE_FILE + ptr[0] + len(blob)] = blob
    open(a.out, "wb").write(slus); print("wrote", a.out, f"({len(blob)}/{ptr[N]-ptr[0]} bytes used)")

def cmd_restore_names(a):
    slus = bytearray(open(a.wa, "rb").read()); stock = open(a.stock, "rb").read()
    _, ptr = read_names(stock)
    lo, hi = NAME_TABLE_FILE + 2 * NAME_ID0, NAME_TABLE_FILE + 2 * (NAME_IDN + 1)
    slus[lo:hi] = stock[lo:hi]
    lo, hi = NAME_BASE_FILE + ptr[0], NAME_BASE_FILE + ptr[N]
    slus[lo:hi] = stock[lo:hi]
    open(a.out, "wb").write(slus); print("wrote", a.out)

def cmd_export_screen(a):
    wa = Wa(a.wa); base = LOAD_SECTOR * 2048
    pal = clut_decode(wa.read(base + 0x10000, 512), 256); pix = wa.read(base, 0x10000)
    strip = Image.new("RGBA", (128, 512)); strip.putdata([pal[p] for p in pix])
    img = Image.new("RGBA", (256, 256)); img.paste(strip.crop((0, 0, 128, 256)), (0, 0)); img.paste(strip.crop((0, 256, 128, 512)), (128, 0))
    img.save(a.out); print("wrote", a.out, "(sectors 0..31 of the load: VRAM (0,256)-(127,511) 8bpp, CLUT sector 32 -> VRAM (0,240))")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["inspect", "export", "import", "restore", "verify", "names", "rename", "restore-names", "export-screen"])
    ap.add_argument("wa", help="WA_MRG.MRG / disc .bin, or SLUS_014.11 for the name commands")
    ap.add_argument("rest", nargs="*"); ap.add_argument("--stock")
    a, extra = ap.parse_known_args(); a.rest += extra; r = a.rest   # --stock may sit anywhere
    if a.cmd == "inspect": cmd_inspect(a)
    elif a.cmd == "export":
        if len(r) != 2: sys.exit("usage: export <wa> <i|all|sheet> <out.png>")
        a.which, a.out = r; cmd_export(a)
    elif a.cmd == "import":
        if len(r) != 3 or r[2] == a.wa: sys.exit("usage: import <wa.mrg> <i> <in.png> <out.mrg>  (out != in)")
        a.which, a.png, a.out = r; cmd_import(a)
    elif a.cmd == "restore":
        if len(r) != 2 or not a.stock: sys.exit("usage: restore <wa.mrg> <i|all> --stock <stock> <out.mrg>")
        a.which, a.out = r; cmd_restore(a)
    elif a.cmd == "verify":
        if not a.stock: sys.exit("verify needs --stock");
        cmd_verify(a)
    elif a.cmd == "names": cmd_names(a)
    elif a.cmd == "rename":
        if len(r) < 3 or len(r) % 2 == 0: sys.exit('usage: rename <SLUS> <i> "<name>" [...] <out.11>')
        a.pairs, a.out = list(zip(r[0:-1:2], r[1:-1:2])), r[-1]; cmd_rename(a)
    elif a.cmd == "restore-names":
        if len(r) != 1 or not a.stock: sys.exit("usage: restore-names <SLUS> --stock <stock SLUS> <out.11>")
        a.out = r[0]; cmd_restore_names(a)
    elif a.cmd == "export-screen":
        if len(r) != 1: sys.exit("usage: export-screen <wa> <out.png>")
        a.out = r[0]; cmd_export_screen(a)
