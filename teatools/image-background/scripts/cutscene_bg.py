#!/usr/bin/env python3
"""Offline clone of TEA-Online's three cutscene-background image tools
(BACKGROUND = static, BGCOMP = composite, BGMOV = moving/parallax).

All three edit the same kind of record in WA_MRG.MRG: a 128-byte-wide indexed
pixel strip (streamed to VRAM 16 rows per disc sector) followed by one CLUT
sector.  The script works on a plain WA_MRG.MRG (read/write) or directly on the
MODE2/2352 disc image (read-only, WA_MRG.MRG at LBA 10102).

  cutscene_bg.py inspect  <wa> [--mode static|comp|mov]
  cutscene_bg.py export   <wa> <NN> <out.png> [--mode M] [--layer 1|2|3] [--strip]
  cutscene_bg.py import   <wa.mrg> <NN> <in.png> <out.mrg> [--mode M] [--layer 1|2|3]
  cutscene_bg.py restore  <wa.mrg> <NN> --stock <stock wa or .bin> <out.mrg> [--mode M]
  cutscene_bg.py verify   <wa> --stock <stock wa or .bin> [--mode M]

NN is the game's picture number = the BCD byte in the text-script command
`F7 05 NN MM` (MM = 00 static, 01 composite, 02 moving).  The site's list
numbers static pictures 01..48 = NN, and composite/moving pictures 01.. = NN+1.
"""
import argparse, os, sys
from PIL import Image

# ---------------------------------------------------------------- disc facts
WA_LBA, WA_SIZE = 10102, 0x2400000
BASE_SECTOR = 0x21D5                                  # func_8002DF2C: a2 + NN*stride + 0x21D5
MODES = {                                             # name: (site-mode byte, base offset sectors, stride sectors, count, layers)
    "static": (0, 0x000, 0x21, 50, 1),                # 33 sectors: 32 pixel + 1 CLUT
    "comp":   (1, 0x672, 0x51, 42, 3),                # 81 sectors: 80 pixel + 1 CLUT
    "mov":    (2, 0x13BC, 0x71, 13, 3),               # 113 sectors: 112 pixel + 1 CLUT
}

# chunk = (strip_px_x, strip_row, width_px, height_rows, canvas_x, canvas_y)
# Layer 1/2 strips are 8bpp (128 px per 128-byte row); layer 3 is 4bpp (256 px per row).
STATIC_320x160 = [(0, 0, 128, 160, 0, 0), (0, 256, 128, 160, 128, 0),
                  (0, 416, 64, 80, 256, 0), (64, 416, 64, 80, 256, 80)]
COMP_L1 = STATIC_320x160
COMP_L2 = [(x, y + 512, w, h, cx, cy) for (x, y, w, h, cx, cy) in STATIC_320x160]
COMP_L3 = [(0, 1024, 256, 160, 0, 0), (128, 1184, 64, 80, 256, 0), (192, 1184, 64, 80, 256, 80)]

def _columns(width, height):
    """Layer-1 layout of a moving background: 128-px columns stacked 256 rows apart."""
    out, x = [], 0
    while x < width:
        out.append((0, 256 * (x // 128), min(128, width - x), height, x, 0)); x += 128
    return out
MOV_L1_SIZE = [(512, 160), (320, 256), (512, 256), (320, 256), (512, 256), (512, 256), (320, 256),
               (512, 256), (320, 256), (344, 256), (512, 256), (512, 256), (512, 256)]
MOV_L2 = [(0, 1024, 128, 160, 0, 0), (0, 1280, 128, 160, 128, 0),
          (0, 1440, 64, 80, 256, 0), (64, 1440, 64, 80, 256, 80)]
MOV_HAS_L2 = {1, 3, 4, 5, 6, 7, 8}                    # site: elems2[i].chunks non-empty
MOV_L3 = [(0, 1536, 256, 160, 0, 0), (128, 1696, 64, 80, 256, 0), (192, 1696, 64, 80, 256, 80)]
MOV_HAS_L3 = {0, 6, 7, 8, 9, 10, 11, 12}              # site: !elems3B[i]

def layer_spec(mode, nn, layer):
    """-> (chunks, canvas_w, canvas_h, bpp, clut_offset_in_clut_sector, ncolors)"""
    if mode == "static":
        if layer != 1: sys.exit("static backgrounds have one layer")
        return STATIC_320x160, 320, 160, 8, 0x000, 256
    if mode == "comp":
        return {1: (COMP_L1, 320, 160, 8, 0x000, 256), 2: (COMP_L2, 320, 160, 8, 0x200, 256),
                3: (COMP_L3, 320, 160, 4, 0x400, 16)}[layer]
    if layer == 1:
        w, h = MOV_L1_SIZE[nn]; return _columns(w, h), w, h, 8, 0x000, 256
    if layer == 2: return MOV_L2, 320, 160, 8, 0x200, 256
    return MOV_L3, 320, 160, 4, 0x400, 16

def block(mode, nn):
    """-> (wa offset, size, first in-file sector, pixel bytes, clut sector offset)"""
    _, base, stride, count, _ = MODES[mode]
    if not 0 <= nn < count: sys.exit(f"{mode}: NN must be 0..{count-1}")
    sec = BASE_SECTOR + base + nn * stride
    return sec * 2048, stride * 2048, sec, (stride - 1) * 2048, (stride - 1) * 2048

# ---------------------------------------------------------------- container
class Wa:
    """WA_MRG.MRG as a plain file (read/write) or inside a MODE2/2352 .bin (read-only)."""
    def __init__(self, path):
        self.path, size = path, os.path.getsize(path)
        if size == WA_SIZE:
            self.kind, self.data = "mrg", bytearray(open(path, "rb").read())
        elif size % 2352 == 0 and size > 16 * 2352:
            self.kind, self.f = "bin", open(path, "rb")
            self.f.seek(16 * 2352 + 24 + 1)
            if self.f.read(5) != b"CD001": sys.exit(f"{path}: not a MODE2/2352 ISO image")
        else:
            sys.exit(f"{path}: expected WA_MRG.MRG ({WA_SIZE} bytes) or a .bin disc image")
    def read(self, off, n):
        if self.kind == "mrg": return bytes(self.data[off:off + n])
        out, lba, skip = bytearray(), WA_LBA + off // 2048, off % 2048
        while len(out) < skip + n:
            self.f.seek(lba * 2352 + 24); out += self.f.read(2048); lba += 1
        return bytes(out[skip:skip + n])
    def write(self, off, b):
        if self.kind != "mrg": sys.exit("cannot write into a disc image; extract WA_MRG.MRG first")
        self.data[off:off + len(b)] = b
    def save(self, path):
        open(path, "wb").write(self.data); print("wrote", path)

# ---------------------------------------------------------------- pixel formats
def clut_decode(b, n):
    """n little-endian 15-bit words -> RGBA; word 0 is transparent (as the site renders it)."""
    out = []
    for i in range(n):
        w = b[2 * i] | (b[2 * i + 1] << 8)
        out.append(((w & 31) << 3, ((w >> 5) & 31) << 3, ((w >> 10) & 31) << 3, 0 if w == 0 else 255))
    return out

def clut_encode(colors, stp):
    """RGBA -> 15-bit words.  stp: 'none' (stock layers 1/2), 'all' (stock layer 3 sets the
    semi-transparency bit on every colour).  Opaque black becomes (8,8,8) = 0x0421 like the
    site, so it is never mistaken for the transparent word 0."""
    out = bytearray()
    for r, g, b, a in colors:
        w = 0 if a < 128 else (r >> 3) | (g >> 3) << 5 | (b >> 3) << 10
        if a >= 128 and w == 0: w = 0x0421
        if stp == "all" and w: w |= 0x8000
        out += bytes((w & 0xFF, w >> 8))
    return bytes(out)

def quantize(img, ncolors, transparent):
    """PIL image -> (indices, RGBA palette[ncolors]).  Alpha < 128 -> index 0 (transparent)
    when `transparent`, otherwise everything is opaque (the site's layer-1 behaviour).
    Images that already fit the palette are mapped exactly; otherwise median cut."""
    img = img.convert("RGBA"); w, h = img.size; raw = img.tobytes()
    px = [raw[i:i + 4] for i in range(0, len(raw), 4)]
    mask = [p[3] < 128 for p in px] if transparent else [False] * len(px)
    anyt = any(mask); k = ncolors - (1 if anyt else 0)
    distinct = sorted({p[:3] for p, m in zip(px, mask) if not m})
    if len(distinct) <= k:
        lut = {c: i for i, c in enumerate(distinct)}
        palette = [(c[0], c[1], c[2], 255) for c in distinct]
        idx = [0 if m else lut[p[:3]] for p, m in zip(px, mask)]
    else:
        rgb = img.convert("RGB")
        if anyt:                             # keep transparent pixels out of the histogram
            pl, fill = rgb.load(), next(p[:3] for p, m in zip(px, mask) if not m)
            for i, m in enumerate(mask):
                if m: pl[i % w, i // w] = fill
        q = rgb.quantize(colors=k, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        pal = q.getpalette() or []
        palette = [(pal[3 * i], pal[3 * i + 1], pal[3 * i + 2], 255) for i in range(min(k, len(pal) // 3))]
        idx = list(q.tobytes())
    if anyt:
        palette = [(0, 0, 0, 0)] + palette
        idx = [0 if m else i + 1 for i, m in zip(idx, mask)]
    palette += [(0, 0, 0, 0)] * (ncolors - len(palette))
    return idx, palette[:ncolors]

def strip_get(strip, bpp, x, y):
    if bpp == 8: return strip[y * 128 + x]
    b = strip[y * 128 + x // 2]; return b & 15 if x % 2 == 0 else b >> 4

def strip_set(strip, bpp, x, y, v):
    if bpp == 8: strip[y * 128 + x] = v; return
    i = y * 128 + x // 2
    strip[i] = (strip[i] & 0xF0) | v if x % 2 == 0 else (strip[i] & 0x0F) | (v << 4)

def chunks_to_canvas(strip, bpp, chunks, cw, ch, palette):
    img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); px = img.load()
    for sx, sy, w, h, cx, cy in chunks:
        for y in range(h):
            for x in range(w):
                px[cx + x, cy + y] = palette[strip_get(strip, bpp, sx + x, sy + y)]
    return img

def canvas_to_chunks(strip, bpp, chunks, idx, cw):
    for sx, sy, w, h, cx, cy in chunks:
        for y in range(h):
            for x in range(w):
                strip_set(strip, bpp, sx + x, sy + y, idx[(cy + y) * cw + cx + x])

# ---------------------------------------------------------------- commands
def describe(mode, nn):
    off, size, sec, pix, clut = block(mode, nn)
    return (f"{mode} NN={nn:02d}: WA_MRG 0x{off:07X}..0x{off+size:07X}  in-file sector 0x{sec:X} "
            f"(+{size//2048})  disc LBA {WA_LBA+sec}  CLUT sector at 0x{off+clut:07X}")

def cmd_inspect(a):
    wa = Wa(a.wa)
    for mode in ([a.mode] if a.mode else MODES):
        _, base, stride, count, layers = MODES[mode]
        print(f"== {mode}: F7 05 NN {MODES[mode][0]:02X}, {count} records of {stride} sectors "
              f"from sector 0x{BASE_SECTOR+base:X} (WA 0x{(BASE_SECTOR+base)*2048:X})")
        for nn in range(count):
            off, size, sec, pix, clut = block(mode, nn)
            data = wa.read(off, size); nz = sum(1 for b in data[:pix] if b)
            c = data[clut:clut + 0x600]
            l1 = sum(1 for i in range(256) if c[2*i] | c[2*i+1]); note = ""
            if layers == 3:
                l2 = sum(1 for i in range(256) if c[0x200+2*i] | c[0x201+2*i])
                l3 = sum(1 for i in range(16) if c[0x400+2*i] | c[0x401+2*i])
                note = f" clut2={l2:3d} clut3={l3:2d}"
                if mode == "mov": note += f"  L1 {MOV_L1_SIZE[nn][0]}x{MOV_L1_SIZE[nn][1]}"
            blank = "  (blank)" if nz < 16 else ""
            print(f"  NN {nn:02d}  0x{off:07X}  sector 0x{sec:04X}  LBA {WA_LBA+sec}  pixels!=0 {nz:6d}  clut1={l1:3d}{note}{blank}")

def cmd_export(a):
    wa = Wa(a.wa); mode = a.mode or "static"
    off, size, sec, pix, clut = block(mode, a.nn)
    chunks, cw, ch, bpp, coff, ncol = layer_spec(mode, a.nn, a.layer)
    strip = wa.read(off, pix); pal = clut_decode(wa.read(off + clut + coff, 2 * ncol), ncol)
    if a.strip:
        rows = pix // 128; w = 128 if bpp == 8 else 256
        img = Image.new("RGBA", (w, rows)); img.putdata([pal[strip_get(strip, bpp, x, y)] for y in range(rows) for x in range(w)])
    else:
        img = chunks_to_canvas(strip, bpp, chunks, cw, ch, pal)
    img.save(a.out); print(describe(mode, a.nn)); print(f"layer {a.layer}: {img.size[0]}x{img.size[1]} -> {a.out}")

def cmd_import(a):
    wa = Wa(a.wa); mode = a.mode or "static"
    if wa.kind != "mrg": sys.exit("import needs a WA_MRG.MRG file, not a disc image")
    off, size, sec, pix, clut = block(mode, a.nn)
    chunks, cw, ch, bpp, coff, ncol = layer_spec(mode, a.nn, a.layer)
    img = Image.open(a.png)
    if img.size != (cw, ch): sys.exit(f"layer {a.layer} of {mode} NN {a.nn} must be {cw}x{ch}, got {img.size[0]}x{img.size[1]}")
    transparent = a.layer != 1                       # the site: layer 1 solid, layers 2/3 keyed
    idx, palette = quantize(img, ncol, transparent)
    stp = "all" if a.layer == 3 else "none"           # stock convention per layer
    strip = bytearray(wa.read(off, pix))
    canvas_to_chunks(strip, bpp, chunks, idx, cw)
    wa.write(off, strip); wa.write(off + clut + coff, clut_encode(palette, stp))
    wa.save(a.out); print(describe(mode, a.nn)); print(f"layer {a.layer}: wrote {len(chunks)} chunks + {ncol}-colour CLUT (stp={stp})")

def cmd_restore(a):
    wa, stock = Wa(a.wa), Wa(a.stock); mode = a.mode or "static"
    if wa.kind != "mrg": sys.exit("restore needs a WA_MRG.MRG file as input")
    off, size, *_ = block(mode, a.nn)
    wa.write(off, stock.read(off, size)); wa.save(a.out); print("restored", describe(mode, a.nn))

def cmd_verify(a):
    wa, stock = Wa(a.wa), Wa(a.stock); bad = 0
    for mode in ([a.mode] if a.mode else MODES):
        for nn in range(MODES[mode][3]):
            off, size, *_ = block(mode, nn)
            if wa.read(off, size) != stock.read(off, size): bad += 1; print("differs:", describe(mode, nn))
    print("all records stock" if not bad else f"{bad} record(s) differ")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["inspect", "export", "import", "restore", "verify"])
    ap.add_argument("wa"); ap.add_argument("arg1", nargs="?"); ap.add_argument("arg2", nargs="?"); ap.add_argument("arg3", nargs="?")
    ap.add_argument("--mode", choices=list(MODES), default=os.environ.get("CUTSCENE_BG_MODE"))
    ap.add_argument("--layer", type=int, default=1, choices=[1, 2, 3]); ap.add_argument("--strip", action="store_true")
    ap.add_argument("--stock", help="stock WA_MRG.MRG or the .bin disc image")
    a = ap.parse_args()
    if a.cmd == "inspect": cmd_inspect(a); sys.exit()
    if a.cmd == "verify":
        if not a.stock: sys.exit("verify needs --stock")
        cmd_verify(a); sys.exit()
    if a.arg1 is None: sys.exit("missing NN")
    a.nn = int(a.arg1, 0)
    if a.cmd == "export":
        if not a.arg2: sys.exit("missing out.png")
        a.out = a.arg2; cmd_export(a)
    elif a.cmd == "import":
        if not (a.arg2 and a.arg3): sys.exit("usage: import <wa.mrg> <NN> <in.png> <out.mrg>")
        if a.arg3 == a.wa: sys.exit("give an output path different from the input")
        a.png, a.out = a.arg2, a.arg3; cmd_import(a)
    elif a.cmd == "restore":
        if not (a.stock and a.arg2): sys.exit("usage: restore <wa.mrg> <NN> --stock <stock> <out.mrg>")
        a.out = a.arg2; cmd_restore(a)
