#!/usr/bin/env python3
"""Offline clone of TEA-Online's Initial Deck tool.

  starter_sets.py dump   <WA_MRG.MRG | disc.bin>            # print the 7 sets + validity
  starter_sets.py export <WA_MRG.MRG | disc.bin> sets.csv   # CSV: card,set1..set7 (row 0 = draws)
  starter_sets.py import <WA_MRG.MRG> sets.csv out.mrg      # write both copies, validate first

Accepts either the extracted WA_MRG.MRG or a raw MODE2/2352 .bin of the US disc (WA_MRG at LBA 10102).
"""
import csv, struct, sys

OFF_A, MIRROR, ROW, NSETS, NCARDS = 0xF92BD4, 0x2B000, 1464, 7, 722
WA_LBA = 10102

class Image:
    def __init__(self, path):
        self.path = path; self.data = bytearray(open(path, "rb").read())
        pvd = 16 * 2352 + 24                      # MODE2/2352: 12 sync + 4 header + 8 subheader
        self.raw = len(self.data) > pvd + 6 and self.data[pvd+1:pvd+6] == b"CD001"
        if not self.raw and not (30 << 20 <= len(self.data) <= 42 << 20):
            sys.exit("neither a WA_MRG.MRG (30-42 MB) nor a MODE2/2352 disc image")
    def _fo(self, wa_off):              # file offset of a WA_MRG byte
        if not self.raw: return wa_off
        s, r = divmod(wa_off, 2048)
        return (WA_LBA + s) * 2352 + 24 + r
    def read(self, wa_off, n):
        out = bytearray()
        while n:
            k = min(n, 2048 - (wa_off % 2048)) if self.raw else n
            fo = self._fo(wa_off); out += self.data[fo:fo+k]; wa_off += k; n -= k
        return bytes(out)
    def write(self, wa_off, b):
        while b:
            k = min(len(b), 2048 - (wa_off % 2048)) if self.raw else len(b)
            fo = self._fo(wa_off); self.data[fo:fo+k] = b[:k]; wa_off += k; b = b[k:]

def read_sets(img, base):
    t = img.read(base, ROW * NSETS)
    return [struct.unpack_from(f"<{1+NCARDS}H", t, i * ROW) for i in range(NSETS)]

def validate(sets):
    msgs = []
    if sum(s[0] for s in sets) != 40: msgs.append(f"draw counts total {sum(s[0] for s in sets)}, game expects 40")
    for i, s in enumerate(sets):
        if sum(s[1:]) != 2048: msgs.append(f"set {i+1} weights total {sum(s[1:])}, must be 2048")
        if s[721] or s[722]: msgs.append(f"set {i+1} gives weight to card 721/722, which the generator never reaches")
    return msgs

def dump(img):
    a, b = read_sets(img, OFF_A), read_sets(img, OFF_A + MIRROR)
    print("copy A == copy B:", a == b)
    for i, s in enumerate(a):
        nz = sorted(((w, c+1) for c, w in enumerate(s[1:]) if w), reverse=True)
        print(f"set {i+1}: draws {s[0]:2d}  sum {sum(s[1:]):4d}  distinct {len(nz):3d}  top {[(c, w) for w, c in nz[:6]]}")
    print("\n".join(validate(a)) or "table is valid")

def export(img, out):
    a = read_sets(img, OFF_A)
    with open(out, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["card"] + [f"set{i+1}" for i in range(NSETS)])
        w.writerow(["draws"] + [s[0] for s in a])
        for c in range(NCARDS): w.writerow([c+1] + [s[c+1] for s in a])
    print("wrote", out)

def imp(img, csvp, out):
    rows = list(csv.reader(open(csvp)))
    sets = [[0] * (1 + NCARDS) for _ in range(NSETS)]
    for r in rows[1:]:
        if not r or not r[0]: continue
        idx = 0 if r[0] == "draws" else int(r[0])
        for i in range(NSETS): sets[i][idx] = int(float(r[i+1] or 0)) & 0xFFFF
    msgs = validate(sets)
    if msgs: print("REFUSING to write:\n  " + "\n  ".join(msgs)); sys.exit(1)
    for i, s in enumerate(sets):
        b = struct.pack(f"<{1+NCARDS}H", *s)
        for base in (OFF_A, OFF_A + MIRROR): img.write(base + i * ROW, b)
    open(out, "wb").write(img.data); print("wrote", out); dump(Image(out))

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("dump", "export", "import"): sys.exit(__doc__)
    cmd, img = sys.argv[1], Image(sys.argv[2])
    if cmd == "dump": dump(img)
    elif cmd == "export": export(img, sys.argv[3])
    else:
        if img.raw: sys.exit("import writes only to an extracted WA_MRG.MRG, not a disc image")
        imp(img, sys.argv[3], sys.argv[4])
