#!/usr/bin/env python3
"""Offline clone of TEA-Online's `extend/tools/image/massive/cards` (bulk card art).

Reads/writes the card 2D-art records inside WA_MRG.MRG (or reads them straight
out of a MODE2/2352 disc image).  Layout, verified against the US disc:

    WA_MRG.MRG sector S = disc LBA 10102 + S

    sectors 0..721          mini-card table, ONE sector per card, id = S + 1
        +0     1280 B   40x32 8bpp, 40-byte rows
        +1280   128 B   64-entry CLUT, 15-bit BGR555 little endian
        +1408   640 B   0xFF padding

    sectors 722..5775       big card records, SEVEN sectors per card
        record for id N is at byte 0x169000 + 14336*(N-1)   (disc LBA 10817+7*N)
        +0      9792 B  102x96 8bpp art, 102-byte rows
        +9792    512 B  256-entry CLUT
        +10304   672 B  baked title, 96x14 4bpp (NOT touched by the site tool)
        +10976  1280 B  40x32 8bpp mini art  <-- byte-identical to sector N-1
        +12256   128 B  64-entry CLUT        <-- byte-identical to sector N-1 +1280
        +12384  1952 B  zero padding

Commands
    info      layout + sanity check of a WA_MRG / disc
    export    write PNGs (big / mini / title) for a range of ids
    import    bulk-replace big and/or mini art from a directory or .zip of images
    restore   copy stock bytes for a range of ids back from a stock WA/disc
    roundtrip self-test: export --raw then import --exact must be byte-identical

Palette modes for `import`:
    site   reproduce the web tool exactly (5-bit truncation + popularity palette)
    exact  the image is already indexed and small enough: keep its own palette
    auto   exact when possible, site otherwise                      (default)

Never point --wa at a file you care about; the script rewrites it in place.
"""

import argparse
import io
import os
import struct
import sys
import zipfile

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("needs Pillow")

# ---------------------------------------------------------------- geometry --

SECTOR = 2048
WA_LBA = 10102              # /DATA/WA_MRG.MRG on the US disc
WA_SIZE = 0x2400000         # 37,748,736

MINI_BASE = 0               # sectors 0..721
BIG_BASE = 0x169000         # 1,478,656 = sector 722
BIG_STRIDE = 14336          # 7 sectors

BIG_W, BIG_H = 102, 96
BIG_ART = BIG_W * BIG_H     # 9792
BIG_COLORS = 256
MINI_W, MINI_H = 40, 32
MINI_ART = MINI_W * MINI_H  # 1280
MINI_COLORS = 64
TITLE_W, TITLE_H = 96, 14
TITLE_BYTES = TITLE_W // 2 * TITLE_H  # 672

OFF_BIG_ART = 0
OFF_BIG_CLUT = 9792
OFF_TITLE = 10304
OFF_MINI_ART = 10976
OFF_MINI_CLUT = 12256

MAX_ID = 722


def big_record(card_id):
    return BIG_BASE + BIG_STRIDE * (card_id - 1)


def mini_sector(card_id):
    return MINI_BASE + SECTOR * (card_id - 1)


# ------------------------------------------------------------------- I/O ----

class Source:
    """Read-only view of WA_MRG, either a flat .MRG or a MODE2/2352 disc."""

    def __init__(self, path):
        self.path = path
        size = os.path.getsize(path)
        self.raw = size % 2352 == 0 and size > 100 * 1024 * 1024
        self.fh = open(path, "rb")

    def read(self, off, length):
        if not self.raw:
            self.fh.seek(off)
            return self.fh.read(length)
        out = bytearray()
        lba = WA_LBA + off // SECTOR
        skip = off % SECTOR
        while len(out) < length + skip:
            self.fh.seek(lba * 2352 + 24)
            out += self.fh.read(SECTOR)
            lba += 1
        return bytes(out[skip:skip + length])

    def close(self):
        self.fh.close()


def load_wa(path):
    if os.path.getsize(path) % 2352 == 0 and os.path.getsize(path) > 100 * 1024 * 1024:
        sys.exit("--wa must be a writable WA_MRG.MRG copy, not a disc image")
    with open(path, "rb") as fh:
        return bytearray(fh.read())


# ---------------------------------------------------------------- palette ---

def clut_to_rgb(blob, n):
    """CLUT bytes -> [(r, g, b, stp)] * n."""
    out = []
    for i in range(n):
        v = struct.unpack_from("<H", blob, 2 * i)[0]
        out.append((((v) & 31) << 3, ((v >> 5) & 31) << 3,
                    ((v >> 10) & 31) << 3, (v >> 15) & 1))
    return out


def rgb_to_clut(entries):
    """[(r, g, b, alpha)] -> CLUT bytes, exactly as the site's writer does.

    JS (chunk `bt`):  black-but-opaque is bumped to (8,8,8); the STP bit is 1
    for any entry with alpha > 0 and 0 otherwise, so a fully transparent slot
    becomes 0x0000 (the PSX's "fully transparent" colour).
    """
    out = bytearray()
    for r, g, b, a in entries:
        if r == 0 and g == 0 and b == 0 and a != 0:
            r = g = b = 8
        v = ((1 if a > 0 else 0) << 15) | ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)
        out += struct.pack("<H", v)
    return bytes(out)


# ------------------------------------------------- the site's quantiser -----

def site_index(rgba, w, h, num_colors, keep_black=True):
    """Faithful port of the tool's ImageConverter.createHeader/createBody.

    rgba: bytes-like, w*h*4, straight from a canvas (transparent pixels are
    (0,0,0,0)).  Returns (indices, palette) with palette = [(r,g,b,a)]*num_colors.
    """
    px = [(rgba[o], rgba[o + 1], rgba[o + 2], rgba[o + 3])
          for o in range(0, 4 * w * h, 4)]

    # createHeader: 5-bit truncation, opaque-black bump, popularity histogram.
    hist = {}
    order_of = {}

    for r, g, b, a in px:
        r, g, b = 8 * (r // 8), 8 * (g // 8), 8 * (b // 8)
        a = 0 if a == 0 else 255
        if r + g + b == 0 and keep_black and a == 255:
            r = g = b = 8
        key = (r, g, b)

        if key in hist:
            hist[key][1] += 1
        else:
            hist[key] = [(r, g, b, a), 1]
            order_of[key] = (r << 16) | (g << 8) | b

    items = list(hist.items())                       # insertion order, like JS
    items.sort(key=lambda kv: -kv[1][1])             # stable, by count desc
    if not items:
        items = [((0, 0, 0), [(0, 0, 0, 0), 0])]
    chosen = [items[i] if i < len(items) else items[0] for i in range(num_colors)]
    chosen.sort(key=lambda kv: order_of[kv[0]])
    palette = [kv[1][0] for kv in chosen]

    # createBody: nearest opaque palette entry, ties won by the LAST match.
    # The JS keys on the truncated colour PLUS alpha and WITHOUT the black bump,
    # so resolve once per distinct key and then map.
    transparent_slot = next((i for i, e in enumerate(palette) if e[3] == 0), None)
    cache = {}
    indices = bytearray(w * h)
    n = 0                      # JS carries `n` across pixels; see the note below
    for i, (r, g, b, a) in enumerate(px):
        key = (8 * (r // 8), 8 * (g // 8), 8 * (b // 8), 0 if a == 0 else 255)
        r, g, b, a = key
        hit = cache.get(key)
        if hit is not None:
            n = hit
        elif a == 0:
            # JS: scans for the first palette slot with alpha 0 and, if there is
            # none, leaves `n` at the PREVIOUS pixel's index -- so this case is
            # deliberately not memoised.
            if transparent_slot is not None:
                n = transparent_slot
                cache[key] = n
        else:
            best = 1 << 24
            n = 0
            for j, (pr, pg, pb, pa) in enumerate(palette):
                if pa == 0:
                    continue
                d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
                if d <= best:
                    best = d
                    n = j
                if best == 0:
                    break
            cache[key] = n
        indices[i] = n
    return bytes(indices), palette


def canvas_rgba(img, w, h):
    """Draw `img` at (0,0) on a transparent w*h canvas, no scaling (drawImage)."""
    img = img.convert("RGBA")
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.paste(img, (0, 0))
    px = bytearray(canvas.tobytes())
    for i in range(0, len(px), 4):        # canvas reports (0,0,0,0), PIL doesn't
        if px[i + 3] == 0:
            px[i] = px[i + 1] = px[i + 2] = 0
    return bytes(px)


def exact_index(img, w, h, num_colors):
    """Use the PNG's own palette when it already fits.  Returns None if it can't."""
    if img.size != (w, h) or img.mode != "P":
        return None
    pal = img.getpalette()
    if pal is None:
        return None
    used = max(img.tobytes()) + 1
    if used > num_colors:
        return None
    entries = []
    for i in range(num_colors):
        r, g, b = pal[3 * i:3 * i + 3] if 3 * i + 2 < len(pal) else (0, 0, 0)
        entries.append((r, g, b, 255))
    return img.tobytes(), entries


# ------------------------------------------------------------------ export --

def png_from_indexed(indices, w, h, clut, ncol):
    im = Image.frombytes("P", (w, h), bytes(indices))
    pal = []
    for r, g, b, _stp in clut[:ncol]:
        pal += [r, g, b]
    pal += [0, 0, 0] * (256 - ncol)
    im.putpalette(pal)
    return im


def cmd_export(a):
    src = Source(a.wa)
    os.makedirs(a.out, exist_ok=True)
    for cid in parse_ids(a.ids):
        rec = src.read(big_record(cid), BIG_STRIDE)
        if "big" in a.what:
            clut = clut_to_rgb(rec[OFF_BIG_CLUT:OFF_BIG_CLUT + 512], BIG_COLORS)
            png = os.path.join(a.out, f"{cid}.png")
            png_from_indexed(rec[:BIG_ART], BIG_W, BIG_H, clut, BIG_COLORS).save(png)
            open(png + ".clut", "wb").write(rec[OFF_BIG_CLUT:OFF_BIG_CLUT + 512])
            if a.raw:
                open(os.path.join(a.out, f"{cid}.big.bin"), "wb").write(
                    rec[:BIG_ART] + rec[OFF_BIG_CLUT:OFF_BIG_CLUT + 512])
        if "mini" in a.what:
            blob = src.read(mini_sector(cid), 1408)
            clut = clut_to_rgb(blob[MINI_ART:], MINI_COLORS)
            png = os.path.join(a.out, f"{cid}.mini.png")
            png_from_indexed(blob[:MINI_ART], MINI_W, MINI_H, clut, MINI_COLORS).save(png)
            open(png + ".clut", "wb").write(blob[MINI_ART:])
            if a.raw:
                open(os.path.join(a.out, f"{cid}.mini.bin"), "wb").write(blob)
        if "title" in a.what:
            t = rec[OFF_TITLE:OFF_TITLE + TITLE_BYTES]
            px = bytearray()
            for byte in t:
                px.append(byte & 15)
                px.append(byte >> 4)
            im = Image.frombytes("P", (TITLE_W, TITLE_H), bytes(px))
            ramp = [0, 0, 0]
            for i in range(1, 8):
                v = 255 - (i - 1) * 32
                ramp += [v, v, v]
            im.putpalette(ramp + [0, 0, 0] * (256 - 8))
            im.save(os.path.join(a.out, f"{cid}.title.png"))
    src.close()
    print(f"wrote {a.what} for {a.ids} into {a.out}")


# ------------------------------------------------------------------ import --

def iter_images(path):
    """Yield (name, bytes) from a directory or a .zip, like the tool's JSZip use."""
    if os.path.isdir(path):
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            if os.path.isfile(full):
                yield name, open(full, "rb").read()
    else:
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                yield info.filename, z.read(info)


def format_id(name):
    """The tool's formatID(): no path separators, leading integer in 1..722."""
    if "\\" in name or "/" in name:
        return None
    digits = ""
    for ch in name:
        if ch.isdigit():
            digits += ch
        else:
            break
    if not digits:
        return None
    n = int(digits)
    return n if 0 < n < 723 else None


def cmd_import(a):
    wa = load_wa(a.wa)
    if len(wa) != WA_SIZE:
        print(f"warning: WA_MRG is {len(wa)} bytes, expected {WA_SIZE}")
    if a.what == "big":
        w, h, ncol = BIG_W, BIG_H, BIG_COLORS
    else:
        w, h, ncol = MINI_W, MINI_H, MINI_COLORS

    cluts = {}
    for name, blob in iter_images(a.dir):
        if name.endswith(".clut"):
            cluts[os.path.basename(name)] = blob

    done = skipped = 0
    for name, blob in iter_images(a.dir):
        if name.endswith(".clut"):
            continue
        cid = format_id(os.path.basename(name) if os.path.isdir(a.dir) else name)
        if cid is None:
            skipped += 1
            continue
        try:
            img = Image.open(io.BytesIO(blob))
            img.load()
        except Exception as exc:
            print(f"  ! {name}: {exc}")
            skipped += 1
            continue

        idx = pal = None
        if a.palette in ("auto", "exact"):
            got = exact_index(img, w, h, ncol)
            if got:
                idx, pal = got
            elif a.palette == "exact":
                print(f"  ! {name}: not an indexed {w}x{h} image with <= {ncol} colours")
                skipped += 1
                continue
        if idx is None:
            idx, pal = site_index(canvas_rgba(img, w, h), w, h, ncol)

        side = cluts.get(os.path.basename(name) + ".clut")
        clut = side if side and len(side) == 2 * ncol else rgb_to_clut(pal)
        if a.what == "big":
            rec = big_record(cid)
            wa[rec:rec + BIG_ART] = idx
            wa[rec + OFF_BIG_CLUT:rec + OFF_BIG_CLUT + 512] = clut
        else:
            rec = big_record(cid)
            wa[rec + OFF_MINI_ART:rec + OFF_MINI_ART + MINI_ART] = idx
            wa[rec + OFF_MINI_CLUT:rec + OFF_MINI_CLUT + 128] = clut
            sec = mini_sector(cid)
            wa[sec:sec + MINI_ART] = idx            # the tool writes both copies
            wa[sec + MINI_ART:sec + MINI_ART + 128] = clut
        done += 1
        if a.verbose:
            print(f"  {name} -> card {cid}")

    with open(a.wa, "wb") as fh:
        fh.write(wa)
    print(f"patched {done} card(s), skipped {skipped}, wrote {a.wa}")


# ----------------------------------------------------------------- restore --

def cmd_restore(a):
    wa = load_wa(a.wa)
    src = Source(getattr(a, "from"))
    for cid in parse_ids(a.ids):
        rec = big_record(cid)
        wa[rec:rec + BIG_STRIDE] = src.read(rec, BIG_STRIDE)
        sec = mini_sector(cid)
        wa[sec:sec + SECTOR] = src.read(sec, SECTOR)
    src.close()
    with open(a.wa, "wb") as fh:
        fh.write(wa)
    print(f"restored {a.ids} from {getattr(a, 'from')}")


# -------------------------------------------------------------------- info --

def cmd_info(a):
    src = Source(a.wa)
    print(f"{a.wa}: {'MODE2/2352 disc' if src.raw else 'flat WA_MRG'}")
    print(f"  mini table  sectors 0..721        bytes 0x0..0x169000")
    print(f"  big records sectors 722..5775     bytes 0x169000..0xB48000")
    bad = dupe = 0
    for cid in parse_ids(a.ids):
        rec = src.read(big_record(cid), BIG_STRIDE)
        mini = src.read(mini_sector(cid), 1408)
        if rec[OFF_MINI_ART:OFF_MINI_ART + 1408] != mini:
            dupe += 1
        if any(rec[12384:]):
            bad += 1
    print(f"  checked {a.ids}: {dupe} mini-copy mismatch(es), {bad} dirty pad(s)")
    for cid in parse_ids(a.ids)[:3]:
        rec = src.read(big_record(cid), BIG_STRIDE)
        clut = clut_to_rgb(rec[OFF_BIG_CLUT:OFF_BIG_CLUT + 512], BIG_COLORS)
        stp = sum(1 for e in clut if e[3])
        print(f"  card {cid}: record @0x{big_record(cid):X} "
              f"disc LBA {10817 + 7 * cid}, {stp}/256 CLUT entries with STP=1")
    src.close()


# --------------------------------------------------------------- roundtrip --

def cmd_roundtrip(a):
    import shutil
    import tempfile
    ids = parse_ids(a.ids)
    tmp = tempfile.mkdtemp(prefix="cardart-")
    work = os.path.join(tmp, "WA_MRG.MRG")
    print("copying WA (this takes a moment)...")
    if os.path.getsize(a.wa) % 2352 == 0:
        src = Source(a.wa)
        with open(work, "wb") as fh:
            for off in range(0, WA_SIZE, 1 << 20):
                fh.write(src.read(off, min(1 << 20, WA_SIZE - off)))
        src.close()
    else:
        shutil.copyfile(a.wa, work)
    before = open(work, "rb").read()

    out = os.path.join(tmp, "png")
    ns = argparse.Namespace(wa=work, out=out, ids=a.ids, what=["big", "mini"], raw=False)
    cmd_export(ns)
    for what in ("big", "mini"):
        sub = os.path.join(tmp, what)
        os.makedirs(sub, exist_ok=True)
        for cid in ids:
            name = f"{cid}.png" if what == "big" else f"{cid}.mini.png"
            shutil.copyfile(os.path.join(out, name), os.path.join(sub, f"{cid}.png"))
            shutil.copyfile(os.path.join(out, name + ".clut"),
                            os.path.join(sub, f"{cid}.png.clut"))
        cmd_import(argparse.Namespace(wa=work, dir=sub, what=what,
                                      palette="exact", verbose=False))
    after = open(work, "rb").read()
    diff = sum(1 for x, y in zip(before, after) if x != y)
    print(f"round-trip over {len(ids)} card(s): {diff} differing byte(s)"
          f" {'-- OK' if diff == 0 else '-- MISMATCH'}")
    print(f"(scratch: {tmp})")
    return 0 if diff == 0 else 1


# -------------------------------------------------------------------- main --

def parse_ids(spec):
    out = []
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-")
            out += list(range(int(lo), int(hi) + 1))
        else:
            out.append(int(part))
    bad = [i for i in out if not 1 <= i <= MAX_ID]
    if bad:
        sys.exit(f"card ids out of range 1..{MAX_ID}: {bad[:5]}")
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("info")
    q.add_argument("--wa", required=True)
    q.add_argument("--ids", default="1-722")
    q.set_defaults(fn=cmd_info)

    q = sub.add_parser("export")
    q.add_argument("--wa", required=True, help="WA_MRG.MRG or a MODE2/2352 .bin")
    q.add_argument("--out", required=True)
    q.add_argument("--ids", default="1")
    q.add_argument("--what", default="big,mini",
                   type=lambda s: [x.strip() for x in s.split(",")])
    q.add_argument("--raw", action="store_true", help="also dump raw index+CLUT blobs")
    q.set_defaults(fn=cmd_export)

    q = sub.add_parser("import")
    q.add_argument("--wa", required=True, help="a WRITABLE copy of WA_MRG.MRG")
    q.add_argument("--dir", required=True, help="directory or .zip of <id>.png files")
    q.add_argument("--what", choices=("big", "mini"), default="big")
    q.add_argument("--palette", choices=("auto", "site", "exact"), default="auto")
    q.add_argument("-v", "--verbose", action="store_true")
    q.set_defaults(fn=cmd_import)

    q = sub.add_parser("restore")
    q.add_argument("--wa", required=True)
    q.add_argument("--from", required=True, dest="from",
                   help="stock WA_MRG.MRG or disc .bin")
    q.add_argument("--ids", default="1-722")
    q.set_defaults(fn=cmd_restore)

    q = sub.add_parser("roundtrip")
    q.add_argument("--wa", required=True)
    q.add_argument("--ids", default="1-4")
    q.set_defaults(fn=cmd_roundtrip)

    a = p.parse_args()
    sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    main()
