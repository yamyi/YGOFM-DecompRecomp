#!/usr/bin/env python3
"""Offline clone of TEA-Online's EQUIP MAKER (extend/tools/equipmaker).

  equip_table.py dump    <WA_MRG.MRG | disc.bin> [--terrain N]
  equip_table.py export  <WA_MRG.MRG | disc.bin> equips.csv [--terrain N]
  equip_table.py import  <WA_MRG.MRG> equips.csv out.mrg [--terrain N|all]
  equip_table.py verify  <WA_MRG.MRG | disc.bin> equips.csv [--terrain N]
  equip_table.py lookup  <WA_MRG.MRG | disc.bin> EQUIP CARD [--terrain N]
  equip_table.py restore <WA_MRG.MRG> out.mrg            # stock table into all 7 terrain copies

CSV columns: equip,card  (ids 1..722) -- same as the site's EquipTemplate.xlsx.

The table lives in the per-terrain duel data block of WA_MRG.MRG:
    block t (t = gDuel_bTerrain 0..6) = in-file sector 0x16C6 + 235*t, 235 sectors
    equip table = block + 0x22000, 0x2800 bytes on disc, loaded to RAM 0x8017A1D8
i.e. WA_MRG offset 0xB85000 + t*0x75800. Only the first 0x2100 (8448) bytes survive
in RAM: the fusion table (next load stage) lands at 0x8017C2D8 and overwrites the rest.
The site's own constant is 0xB85800 (+0x800, one sector late for the stock US disc);
pass --site-offsets to reproduce that.

Accepts an extracted WA_MRG.MRG or a raw MODE2/2352 .bin of the US disc (WA_MRG at
LBA 10102). Writing into a .bin does not recompute EDC/ECC (emulators ignore it).
"""
import csv, os, struct, sys

WA_LBA        = 10102
BLOCK_SECTOR  = 0x16C6
BLOCK_BYTES   = 235 * 2048          # 0x75800
TABLE_IN_BLK  = 0x22000             # game-correct (stage 2 of the duel loader)
SITE_IN_BLK   = 0x22800             # what the site's JS uses
FILE_BYTES    = 0x2800              # bytes the loader copies
LIVE_BYTES    = 0x2100              # bytes that survive in RAM (8448, the site's cap)
NCARDS        = 722
RAM_BASE      = 0x8017A1D8
TERRAINS      = ["Normal", "Forest", "Wasteland", "Mountain", "Meadow", "Sea", "Dark"]
STOCK_BIN     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_equip_table.bin")


class Image:
    def __init__(self, path):
        self.path = path; self.data = bytearray(open(path, "rb").read())
        pvd = 16 * 2352 + 24
        self.raw = len(self.data) > pvd + 6 and self.data[pvd+1:pvd+6] == b"CD001"
        if not self.raw and not (30 << 20 <= len(self.data) <= 43 << 20):
            sys.exit("neither a WA_MRG.MRG (30-43 MB) nor a MODE2/2352 disc image")
    def _fo(self, wa_off):
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
        b = bytes(b)
        while b:
            k = min(len(b), 2048 - (wa_off % 2048)) if self.raw else len(b)
            fo = self._fo(wa_off); self.data[fo:fo+k] = b[:k]; wa_off += k; b = b[k:]
    def save(self, path):
        open(path, "wb").write(self.data)


def table_offset(terrain, site=False):
    return BLOCK_SECTOR * 2048 + terrain * BLOCK_BYTES + (SITE_IN_BLK if site else TABLE_IN_BLK)


# ---------------------------------------------------------------- decoding

def groups(tbl):
    """[(key, [members...], offset)] walking exactly like equip_table_lookup: stop at key 0.
    Also stops (with a warning) if the walk leaves the bytes that survive in RAM."""
    out = []; p = 0
    while p + 4 <= len(tbl):
        key, cnt = struct.unpack_from("<HH", tbl, p)
        if key == 0: break
        mem = list(struct.unpack_from(f"<{cnt}H", tbl, p + 4)) if p + 4 + 2 * cnt <= len(tbl) else []
        out.append((key, mem, p)); p += 4 + 2 * cnt
        if p > LIVE_BYTES:
            print(f"  WARNING: walk passes 0x{LIVE_BYTES:X}; in RAM those bytes are the fusion index", file=sys.stderr)
            break
    return out, p + 2


def game_lookup(tbl, equip, card):
    """Transcription of equip_table_lookup (0x80019A08): returns card if card is in equip's list."""
    p = 0
    while p + 4 <= len(tbl):
        key, cnt = struct.unpack_from("<HH", tbl, p)
        if key == 0: return 0
        p += 4
        if key == equip:
            for i in range(cnt):
                if p + 2 * i + 2 > len(tbl): return 0
                if struct.unpack_from("<H", tbl, p + 2 * i)[0] == card: return card
            return 0
        p += 2 * cnt
    return 0


# ---------------------------------------------------------------- encoding

def serialize(rows):
    """rows: iterable of (equip, card). Site layout: groups in ascending equip id, members
    ascending and unique, u16 0 terminator, 0xFF fill. Errors past the 8448-byte RAM cap."""
    per = {}
    for e, c in rows:
        for v in (e, c):
            if not 1 <= v <= NCARDS: raise ValueError(f"id out of range: {e},{c}")
        per.setdefault(e, set()).add(c)
    out = bytearray()
    for e in sorted(per):
        mem = sorted(per[e])
        out += struct.pack("<HH", e, len(mem)) + struct.pack(f"<{len(mem)}H", *mem)
    out += b"\x00\x00"
    if len(out) > LIVE_BYTES:
        raise ValueError(f"MEMORY OVERFLOW: {len(out)} bytes, only {LIVE_BYTES} survive in RAM")
    used = len(out)
    out += b"\xff" * (FILE_BYTES - len(out))
    return bytes(out), used


# ---------------------------------------------------------------- commands

def read_csv(path):
    rows = []
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row or not row[0].strip().lstrip("-").isdigit(): continue
            rows.append((int(row[0]), int(row[1])))
    return rows


def opt(args, name, default=None):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default


def main(argv):
    args = list(argv)
    site = "--site-offsets" in args
    if site: args.remove("--site-offsets")
    terrain = opt(args, "--terrain", "0")
    if len(args) < 2: sys.exit(__doc__)
    cmd, path = args[0], args[1]

    if cmd == "restore":
        img = Image(path); stock = open(STOCK_BIN, "rb").read()
        assert len(stock) == FILE_BYTES
        for t in range(7): img.write(table_offset(t, site), stock)
        img.save(args[2]); print(f"stock equip table written to all 7 terrain copies -> {args[2]}"); return

    img = Image(path)
    tlist = range(7) if terrain == "all" else [int(terrain)]
    t0 = tlist[0]
    base = table_offset(t0, site)
    tbl = img.read(base, FILE_BYTES)

    if cmd == "dump":
        gs, used = groups(tbl)
        print(f"terrain {t0} ({TERRAINS[t0]}): WA_MRG offset 0x{base:X}  (in-file sector 0x{base//2048:X}, "
              f"disc LBA {WA_LBA + base//2048}, RAM 0x{RAM_BASE:08X})")
        print(f"  groups: {len(gs)}   memberships: {sum(len(m) for _, m, _ in gs)}   "
              f"used {used} / {LIVE_BYTES} live bytes ({LIVE_BYTES - used} free; {FILE_BYTES} on disc)")
        for key, mem, off in gs:
            print(f"    equip {key:3d}: {len(mem):3d} cards @+0x{off:04X}"
                  + (f"  ({mem[0]}..{mem[-1]})" if mem else ""))
        same = all(img.read(table_offset(t, site), FILE_BYTES) == tbl for t in range(7))
        print(f"  all 7 terrain copies identical: {same}")
    elif cmd == "export":
        gs, _ = groups(tbl); n = 0
        with open(args[2], "w", newline="") as f:
            w = csv.writer(f); w.writerow(["equip", "card"])
            for key, mem, _ in gs:
                for c in mem: w.writerow([key, c]); n += 1
        print(f"{n} memberships -> {args[2]}")
    elif cmd == "import":
        rows = read_csv(args[2]); new, used = serialize(rows)
        for t in tlist: img.write(table_offset(t, site), new)
        img.save(args[3])
        print(f"{len(rows)} rows, {used} bytes used ({LIVE_BYTES - used} free), terrain(s) {list(tlist)} -> {args[3]}")
    elif cmd == "verify":
        want = set(read_csv(args[2])); bad = 0
        keys = {e for e, _ in want} | {k for k, _, _ in groups(tbl)[0]}
        for e in sorted(keys):
            for c in range(1, NCARDS + 1):
                g = bool(game_lookup(tbl, e, c)); w = (e, c) in want
                if g != w:
                    bad += 1
                    if bad <= 30: print(f"  equip {e} on {c}: game {g}, csv {w}")
        print(f"{'OK' if not bad else bad} mismatches (terrain {t0})")
    elif cmd == "lookup":
        e, c = int(args[2]), int(args[3])
        print("equips" if game_lookup(tbl, e, c) else "does not equip")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
