#!/usr/bin/env python3
"""Offline clone of TEA-Online's Drop Editor (extend/tools/drop).

WA_MRG.MRG side (the 39 per-opponent weight blocks):
  drop_tables.py dump    <WA_MRG.MRG | disc.bin> [--opp N]      summary / top weights
  drop_tables.py verify  <WA_MRG.MRG | disc.bin>                 every table must total 2048
  drop_tables.py export  <WA_MRG.MRG | disc.bin> out.csv         same layout as the site's xlsx
  drop_tables.py import  <WA_MRG.MRG> in.csv out.mrg             write weights back
  drop_tables.py lock    <WA_MRG.MRG> out.mrg                    encode drop tiers (site "LOCK")
  drop_tables.py unlock  <WA_MRG.MRG> out.mrg                    decode them again
  drop_tables.py restore <WA_MRG.MRG> out.mrg --stock disc.bin   copy the 39 stock blocks back

SLUS_014.11 side (the LOCK code patch that makes the game decode locked tables):
  drop_tables.py slus-inspect SLUS_014.11
  drop_tables.py slus-lock    SLUS_014.11 out.11
  drop_tables.py slus-restore SLUS_014.11 out.11

Block k (opponent id k+1, k = 0..38) = WA offset 0xE9B000 + 0x1800*k, loaded by the duel
bootstrap to 0x801781D8: 4 x (722 u16 weights + 16 pad) = deck pool, S/A-POW drops,
B/C/D drops, S/A-TEC drops, then 304 bytes of rank-score data. A disc .bin (MODE2/2352,
WA_MRG at LBA 10102) is accepted read-only.
"""
import argparse, csv, random, struct, sys

WA_BASE   = 0xE9B000
BLOCK     = 0x1800
ROW       = 1460
NCARDS    = 722
NOPP      = 39
TABLES    = ["deck", "pow", "bcd", "tec"]
WA_LBA    = 10102
LOCK_ADD, LOCK_SHIFT = 2512, 3          # site: w' = 8*w + 2512 + rand(0..6)

# SLUS patch: j 0x801BFFD0 over "addu a0,a0,v0 / slt v0,a0,a1" in Duel_SelectCardDrop
OFF_HOOK, STOCK_HOOK = 0x12060, bytes.fromhex("21208200" "2a108500")
PATCH_HOOK           = bytes.fromhex("f4ff0608" "00000000")
OFF_STUB, STOCK_STUB = 0x1B07D0, bytes(24)
PATCH_STUB = bytes.fromhex("30f64224" "c3100200" "21208200" "2a108500" "1a860008" "00000000")


class Image:
    """WA_MRG.MRG (writable) or a raw MODE2/2352 disc image (read-only)."""
    def __init__(self, path):
        self.data = bytearray(open(path, "rb").read())
        self.disc = len(self.data) > 100_000_000
        if not self.disc and not (30_000_000 <= len(self.data) <= 42_000_000):
            sys.exit("neither a WA_MRG.MRG (30-42 MB) nor a MODE2/2352 disc image")
    def _fo(self, off):
        if not self.disc:
            return off
        s, r = divmod(off, 2048)
        return (WA_LBA + s) * 2352 + 24 + r
    def read(self, off, n):
        if not self.disc:
            return bytes(self.data[off:off + n])
        out = bytearray()
        while len(out) < n:
            o = off + len(out); s, r = divmod(o, 2048)
            take = min(2048 - r, n - len(out)); fo = self._fo(o)
            out += self.data[fo:fo + take]
        return bytes(out)
    def write(self, off, b):
        if self.disc:
            sys.exit("refusing to write into a disc image; extract WA_MRG.MRG first")
        self.data[off:off + len(b)] = b
    def save(self, path):
        open(path, "wb").write(self.data)


def block_off(k):
    return WA_BASE + BLOCK * k

def read_tables(img, k):
    b = img.read(block_off(k), ROW * 4)
    return [list(struct.unpack_from("<%dH" % NCARDS, b, ROW * n)) for n in range(4)]

def write_tables(img, k, tabs):
    for n, w in enumerate(tabs):
        img.write(block_off(k) + ROW * n, struct.pack("<%dH" % NCARDS, *w))

def dump(img, only=None):
    for k in range(NOPP):
        if only and k + 1 != only:
            continue
        tabs = read_tables(img, k)
        print(f"opponent {k+1:2d}  WA 0x{block_off(k):X}  sector 0x{block_off(k)//2048:X}  LBA {WA_LBA + block_off(k)//2048}")
        for n, w in enumerate(tabs):
            nz = sorted(((v, i + 1) for i, v in enumerate(w) if v), reverse=True)
            top = " ".join(f"{c}x{v}" for v, c in nz[:6])
            print(f"   {TABLES[n]:4s} sum={sum(w):5d} distinct={len(nz):3d}  top: {top}")

def verify(img):
    bad = 0
    for k in range(NOPP):
        for n, w in enumerate(read_tables(img, k)):
            if sum(w) != 2048:
                bad += 1; print(f"opponent {k+1} {TABLES[n]}: sum {sum(w)} != 2048")
    print("all 156 tables total 2048" if not bad else f"{bad} table(s) off")
    return bad == 0

def export(img, out):
    cols = [f"{k+1}:{t}" for k in range(NOPP) for t in TABLES]
    all_t = [read_tables(img, k) for k in range(NOPP)]
    with open(out, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["card"] + cols)
        for c in range(NCARDS):
            w.writerow([c + 1] + [all_t[k][n][c] for k in range(NOPP) for n in range(4)])
    print(f"wrote {out}: {NCARDS} rows x {len(cols)} weight columns")

def imp(img, csvp, out):
    rows = list(csv.reader(open(csvp, newline="")))
    hdr = rows[0]
    idx = {h: i for i, h in enumerate(hdr)}
    tabs = [[[0] * NCARDS for _ in range(4)] for _ in range(NOPP)]
    for r in rows[1:]:
        if not r or not r[0].strip().isdigit():
            continue
        c = int(r[0]) - 1
        if not 0 <= c < NCARDS:
            continue
        for k in range(NOPP):
            for n, t in enumerate(TABLES):
                col = idx.get(f"{k+1}:{t}")
                v = int(float(r[col] or 0)) if col is not None and col < len(r) else 0
                tabs[k][n][c] = v % 65536          # the site does parseInt % 65536 too
    for k in range(NOPP):
        write_tables(img, k, tabs[k])
        for n in range(4):
            if sum(tabs[k][n]) != 2048:
                print(f"warning: opponent {k+1} {TABLES[n]} sums to {sum(tabs[k][n])}, not 2048")
    img.save(out); print(f"wrote {out}")

def lock(img, out, seed=None):
    rnd = random.Random(seed)
    for k in range(NOPP):
        tabs = read_tables(img, k)
        for n in (1, 2, 3):                        # drop tiers only, never the deck pool
            tabs[n] = [(v << LOCK_SHIFT) + LOCK_ADD + rnd.randrange(7) for v in tabs[n]]
        write_tables(img, k, tabs)
    img.save(out); print(f"wrote {out} (drop tiers encoded; needs the slus-lock patch)")

def unlock(img, out):
    for k in range(NOPP):
        tabs = read_tables(img, k)
        for n in (1, 2, 3):
            tabs[n] = [max(0, (v - LOCK_ADD) >> LOCK_SHIFT) for v in tabs[n]]
        write_tables(img, k, tabs)
    img.save(out); print(f"wrote {out} (drop tiers decoded)")

def restore(img, out, stock):
    src = Image(stock)
    img.write(WA_BASE, src.read(WA_BASE, BLOCK * NOPP))
    img.save(out); print(f"wrote {out} (39 blocks copied from {stock})")

# ---- SLUS side ---------------------------------------------------------------
def load_slus(p):
    d = bytearray(open(p, "rb").read())
    if d[:8] != b"PS-X EXE" or not (1902591 <= len(d) <= 2097152):
        sys.exit("not a SLUS_014.11-sized PS-X EXE")
    return d

def slus_inspect(d):
    hook, stub = bytes(d[OFF_HOOK:OFF_HOOK+8]), bytes(d[OFF_STUB:OFF_STUB+24])
    if hook == STOCK_HOOK and stub == STOCK_STUB:
        print("drop LOCK: not installed (stock)")
    elif hook == PATCH_HOOK and stub == PATCH_STUB:
        print("drop LOCK: installed (0x80021860 -> stub 0x801BFFD0: w = (w-2512)>>3)")
    else:
        print(f"drop LOCK: unknown state  hook={hook.hex()} stub={stub.hex()}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["dump", "verify", "export", "import", "lock", "unlock", "restore",
                                    "slus-inspect", "slus-lock", "slus-restore"])
    ap.add_argument("image"); ap.add_argument("arg", nargs="?"); ap.add_argument("out", nargs="?")
    ap.add_argument("--opp", type=int); ap.add_argument("--stock"); ap.add_argument("--seed", type=int)
    a = ap.parse_args()
    if a.cmd.startswith("slus-"):
        d = load_slus(a.image)
        if a.cmd == "slus-inspect":
            slus_inspect(d)
        else:
            d[OFF_HOOK:OFF_HOOK+8] = PATCH_HOOK if a.cmd == "slus-lock" else STOCK_HOOK
            d[OFF_STUB:OFF_STUB+24] = PATCH_STUB if a.cmd == "slus-lock" else STOCK_STUB
            open(a.arg, "wb").write(d); print(f"wrote {a.arg}")
        sys.exit(0)
    img = Image(a.image)
    if a.cmd == "dump":      dump(img, a.opp)
    elif a.cmd == "verify":  sys.exit(0 if verify(img) else 1)
    elif a.cmd == "export":  export(img, a.arg)
    elif a.cmd == "import":  imp(img, a.arg, a.out)
    elif a.cmd == "lock":    lock(img, a.arg, a.seed)
    elif a.cmd == "unlock":  unlock(img, a.arg)
    elif a.cmd == "restore":
        if not a.stock: sys.exit("restore needs --stock <disc.bin or stock WA_MRG.MRG>")
        restore(img, a.arg, a.stock)
