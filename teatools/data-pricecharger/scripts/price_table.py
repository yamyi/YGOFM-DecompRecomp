#!/usr/bin/env python3
"""Offline clone of TEA-Online's Price Charger (extend/tools/data/pricecharger).

  price_table.py dump    <WA_MRG.MRG | disc.bin> [--id N]
  price_table.py export  <WA_MRG.MRG | disc.bin> out.csv            id,price,password
  price_table.py import  <WA_MRG.MRG> in.csv out.mrg                 rows may cover any subset of cards
  price_table.py set     <WA_MRG.MRG> out.mrg --id N [--price P] [--password DDDDDDDD]
  price_table.py nopass  <WA_MRG.MRG> out.mrg                        every password -> FFFFFFFE (site "remove all")
  price_table.py disable <WA_MRG.MRG> out.mrg                        site "disable system": entry 0 -> FF..FF
  price_table.py kill    <WA_MRG.MRG> out.mrg                        entry 1 price -> FFFFFFFF (what actually stops the lookup)
  price_table.py restore <WA_MRG.MRG> out.mrg --stock disc.bin

Table: WA_MRG offset 0xFB9800 (sector 0x1F73, disc LBA 18153), 723 x 8 bytes, index = card id
(entry 0 unused): u32 starchip price, u32 password as 8 BCD digits (0x89631139 = "89631139";
0xFFFFFFFE = card has no password). Loaded to 0x801A8000 by the PASSWORD screen; the module's
lookup starts at entry 1 (gLibrary_aPasswordCardData 0x801A8008) and stops at the first entry
whose PRICE is 0xFFFFFFFF.
"""
import argparse, csv, struct, sys

WA_OFF, ENTRY, NCARDS, WA_LBA = 0xFB9800, 8, 722, 10102
NOPASS = 0xFFFFFFFE

class Image:
    def __init__(self, path):
        self.data = bytearray(open(path, "rb").read())
        self.disc = len(self.data) > 100_000_000
        if not self.disc and not (30_000_000 <= len(self.data) <= 42_000_000):
            sys.exit("neither a WA_MRG.MRG (30-42 MB) nor a MODE2/2352 disc image")
    def read(self, off, n):
        if not self.disc: return bytes(self.data[off:off+n])
        out = bytearray()
        while len(out) < n:
            o = off + len(out); s, r = divmod(o, 2048); take = min(2048 - r, n - len(out))
            fo = (WA_LBA + s) * 2352 + 24 + r; out += self.data[fo:fo+take]
        return bytes(out)
    def write(self, off, b):
        if self.disc: sys.exit("refusing to write into a disc image; extract WA_MRG.MRG first")
        self.data[off:off+len(b)] = b
    def save(self, p): open(p, "wb").write(self.data)

def get(img, cid):
    return struct.unpack("<II", img.read(WA_OFF + ENTRY*cid, ENTRY))
def put(img, cid, price, pw):
    img.write(WA_OFF + ENTRY*cid, struct.pack("<II", price, pw))
def pwstr(pw):
    return "-" if pw == NOPASS else f"{pw:08X}"
def parse_pw(s):
    s = s.strip().upper()
    if s in ("", "-", "NONE"): return NOPASS
    if len(s) > 8 or any(c not in "0123456789ABCDEF" for c in s): sys.exit(f"bad password {s!r}")
    return int(s.zfill(8), 16)              # digits are BCD nibbles, so parse the text as hex

def dump(img, only=None):
    p0, w0 = get(img, 0)
    print(f"entry 0: price {p0:#010x} pw {w0:#010x}  ({'stock zeros' if (p0, w0) == (0, 0) else 'MODIFIED'})")
    for cid in range(1, NCARDS + 1):
        if only and cid != only: continue
        price, pw = get(img, cid)
        print(f"card {cid:3d}: price {price:6d}  password {pwstr(pw)}")
    tail = img.read(WA_OFF + ENTRY*(NCARDS+1), 8)
    print("terminator after card 722:", tail.hex(), "(stock ff*8)")

def export(img, out):
    with open(out, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["id", "price", "password"])
        for cid in range(1, NCARDS + 1):
            price, pw = get(img, cid); w.writerow([cid, price, pwstr(pw)])
    print(f"wrote {out}")

def imp(img, csvp, out):
    n = 0
    for r in csv.DictReader(open(csvp, newline="")):
        cid = int(r["id"]);  price = int(float(r.get("price") or 0)) % 1_000_000
        pw = parse_pw(r.get("password") or "-")
        if 1 <= cid <= NCARDS: put(img, cid, price, pw); n += 1
    img.save(out); print(f"wrote {out}: {n} cards updated")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["dump", "export", "import", "set", "nopass", "disable", "kill", "restore"])
    ap.add_argument("image"); ap.add_argument("arg", nargs="?"); ap.add_argument("out", nargs="?")
    ap.add_argument("--id", type=int); ap.add_argument("--price", type=int); ap.add_argument("--password")
    ap.add_argument("--stock")
    a = ap.parse_args(); img = Image(a.image)
    if a.cmd == "dump":     dump(img, a.id)
    elif a.cmd == "export": export(img, a.arg)
    elif a.cmd == "import": imp(img, a.arg, a.out)
    else:
        out = a.arg
        if a.cmd == "set":
            if not a.id: sys.exit("--id required")
            price, pw = get(img, a.id)
            if a.price is not None: price = max(0, a.price) % 1_000_000
            if a.password is not None: pw = parse_pw(a.password)
            put(img, a.id, price, pw)
        elif a.cmd == "nopass":
            for cid in range(1, NCARDS + 1): put(img, cid, get(img, cid)[0], NOPASS)
        elif a.cmd == "disable": put(img, 0, 0xFFFFFFFF, 0xFFFFFFFF)
        elif a.cmd == "kill":    put(img, 1, 0xFFFFFFFF, get(img, 1)[1])
        elif a.cmd == "restore":
            if not a.stock: sys.exit("restore needs --stock")
            img.write(WA_OFF, Image(a.stock).read(WA_OFF, 0x1800))
        img.save(out); print(f"wrote {out}")
