#!/usr/bin/env python3
"""Offline clone of TEA-Online's FUSION MAKER (extend/tools/fusionmaker).

  fusion_table.py dump    <WA_MRG.MRG | disc.bin> [--terrain N]
  fusion_table.py export  <WA_MRG.MRG | disc.bin> fusions.csv [--terrain N]
  fusion_table.py import  <WA_MRG.MRG> fusions.csv out.mrg [--terrain N|all] [--safe-tails] [--sort]
  fusion_table.py verify  <WA_MRG.MRG | disc.bin> fusions.csv [--terrain N]
  fusion_table.py lookup  <WA_MRG.MRG | disc.bin> CARD1 CARD2 [--terrain N]
  fusion_table.py restore <WA_MRG.MRG> out.mrg            # stock table into all 7 terrain copies

CSV columns: card1,card2,result  (ids 1..722; card1 <= card2 is enforced on import,
a row is swapped if needed). Same format as the site's FusionTemplate.xlsx. Import keeps
the row order inside each record (--sort orders partners ascending, like the site);
--safe-tails pads odd-count records to a full 5-byte group so no glitch fusion can arise.

The table lives in the per-terrain duel data block of WA_MRG.MRG:
    block t (t = gDuel_bTerrain 0..6) = in-file sector 0x16C6 + 235*t, 235 sectors
    fusion table = block + 0x24800, exactly 0x10000 bytes, loaded to RAM 0x8017C2D8
i.e. WA_MRG offset 0xB87800 + t*0x75800. The site's own constant is 0xB88000 (+0x800,
one sector late for the stock US disc); pass --site-offsets to reproduce that.

Accepts an extracted WA_MRG.MRG or a raw MODE2/2352 .bin of the US disc (WA_MRG at
LBA 10102). Writing into a .bin does not recompute EDC/ECC (emulators ignore it).
"""
import csv, os, struct, sys

WA_LBA        = 10102
BLOCK_SECTOR  = 0x16C6
BLOCK_BYTES   = 235 * 2048          # 0x75800
TABLE_IN_BLK  = 0x24800             # game-correct (stage 3 of the duel loader)
SITE_IN_BLK   = 0x25000             # what the site's JS uses
TABLE_BYTES   = 0x10000
NCARDS        = 722
INDEX_BYTES   = (NCARDS + 1) * 2    # 1446
RAM_BASE      = 0x8017C2D8
TERRAINS      = ["Normal", "Forest", "Wasteland", "Mountain", "Meadow", "Sea", "Dark"]
STOCK_BIN     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_fusion_table.bin")


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

def record(tbl, cid):
    """(count, body_offset) of card cid's record, or None."""
    off = struct.unpack_from("<H", tbl, cid * 2)[0]
    if off == 0: return None
    c = tbl[off]
    if c: return c, off + 1
    return 511 - tbl[off + 1], off + 2


def entries(tbl, cid):
    """The (partner, result) pairs the record *intends* to hold (count entries)."""
    r = record(tbl, cid)
    if not r: return []
    c, body = r; out = []
    for e in range(c):
        q = body + 5 * (e // 2)
        if q + 5 > len(tbl): break              # garbage table: record runs off the end
        g0 = tbl[q]
        if e % 2 == 0:
            out.append((((g0 << 8) & 0x300) | tbl[q+1], ((g0 << 6) & 0x300) | tbl[q+2]))
        else:
            out.append((((g0 << 4) & 0x300) | tbl[q+3], ((g0 << 2) & 0x300) | tbl[q+4]))
    return out


def game_lookup(tbl, a, b):
    """Transcription of fusion_table_lookup (0x80019A60), tail behaviour included."""
    if b < a: a, b = b, a
    if not (1 <= a <= NCARDS): return 0
    off = struct.unpack_from("<H", tbl, a * 2)[0]
    if off == 0: return 0
    p = off; c = tbl[p]
    if c == 0: c = 0x1FF - tbl[p + 1]; p += 1
    p += 1
    while p + 5 <= len(tbl):
        g0 = tbl[p]
        if (((g0 << 8) & 0x300) | tbl[p+1]) == b: return ((g0 << 6) & 0x300) | tbl[p+2]
        if (((g0 << 4) & 0x300) | tbl[p+3]) == b: return ((g0 << 2) & 0x300) | tbl[p+4]
        p += 5; c -= 2
        if c <= 0: return 0
    return 0


def intended_pairs(tbl):
    """{(card1, card2): result} as the site's DataSet sees it (first hit wins)."""
    out = {}
    for cid in range(1, NCARDS + 1):
        for partner, res in entries(tbl, cid):
            out.setdefault((cid, partner), res)
    return out


def glitch_pairs(tbl, intended=None):
    """Pairs where the game's walk answers something the table does not intend.
    Comes from odd-count records: the last 5-byte group is only 3 bytes long, so the
    game's second-half test reads the next record's first two bytes."""
    intended = intended if intended is not None else intended_pairs(tbl)
    out = []
    for cid in range(1, NCARDS + 1):
        r = record(tbl, cid)
        if not r or r[0] % 2 == 0: continue
        c, body = r; q = body + 5 * (c // 2)
        if q + 5 > len(tbl): continue
        g0 = tbl[q]
        partner = ((g0 << 4) & 0x300) | tbl[q+3]
        res     = ((g0 << 2) & 0x300) | tbl[q+4]
        if partner >= cid and (cid, partner) not in intended and res:
            out.append((cid, partner, res))
    return out


def used_bytes(tbl):
    end = INDEX_BYTES
    for cid in range(1, NCARDS + 1):
        r = record(tbl, cid)
        if not r: continue
        c, body = r
        end = max(end, body + 5 * (c // 2) + (3 if c % 2 else 0))
    return end


# ---------------------------------------------------------------- encoding

def serialize(pairs, safe_tails=False, sort=False):
    """pairs: {(card1, card2): result}. Returns the 0x10000-byte table in the site's
    layout: index[0]=0, records in card order right after the index, 1-byte count
    (0 + 511-count for 256..511), 5-byte groups, 3-byte tail for odd counts.
    safe_tails pads odd records to a full 5-byte group with zeros instead, which
    costs 2 bytes per odd record and removes the glitch fusions."""
    per = {}
    for (a, b), r in pairs.items():
        if b < a: a, b = b, a
        for v in (a, b, r):
            if not 1 <= v <= NCARDS: raise ValueError(f"id out of range in ({a},{b})->{r}")
        per.setdefault(a, {})
        if b in per[a] and per[a][b] != r:
            raise ValueError(f"pair ({a},{b}) listed twice with different results")
        per[a][b] = r
    tbl = bytearray(b"\xff" * TABLE_BYTES)
    tbl[0:INDEX_BYTES] = b"\x00" * INDEX_BYTES
    pos = INDEX_BYTES
    for cid in range(1, NCARDS + 1):
        lst = list(per.get(cid, {}).items())
        if sort: lst.sort()
        if not lst: continue
        n = len(lst)
        if n > 511: raise ValueError(f"card {cid} has {n} partners; the count byte encodes at most 511")
        if pos > 0xFFFF: raise ValueError("table overflow: a record would start past the u16 index range")
        struct.pack_into("<H", tbl, cid * 2, pos)
        hdr = bytes([n]) if n < 256 else bytes([0, 511 - n])
        body = bytearray()
        for i in range(0, n - 1, 2):
            (p1, r1), (p2, r2) = lst[i], lst[i + 1]
            body += bytes([(p1 >> 8) | ((r1 >> 8) << 2) | ((p2 >> 8) << 4) | ((r2 >> 8) << 6),
                           p1 & 0xFF, r1 & 0xFF, p2 & 0xFF, r2 & 0xFF])
        if n % 2:
            p1, r1 = lst[-1]
            body += bytes([(p1 >> 8) | ((r1 >> 8) << 2), p1 & 0xFF, r1 & 0xFF])
            if safe_tails: body += b"\x00\x00"
        rec = hdr + bytes(body)
        if pos + len(rec) > TABLE_BYTES:
            raise ValueError(f"MEMORY OVERFLOW at card {cid}: table needs more than {TABLE_BYTES} bytes")
        tbl[pos:pos + len(rec)] = rec; pos += len(rec)
    return bytes(tbl), pos


# ---------------------------------------------------------------- commands

def read_csv(path):
    pairs = {}
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row or not row[0].strip().lstrip("-").isdigit(): continue
            a, b, r = (int(x) for x in row[:3])
            if b < a: a, b = b, a
            if (a, b) in pairs and pairs[(a, b)] != r:
                sys.exit(f"{path}: pair {a},{b} has two results ({pairs[(a,b)]} and {r})")
            pairs[(a, b)] = r
    return pairs


def opt(args, name, default=None):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default


def main(argv):
    args = list(argv)
    site = "--site-offsets" in args
    if site: args.remove("--site-offsets")
    safe = "--safe-tails" in args
    if safe: args.remove("--safe-tails")
    sort = "--sort" in args
    if sort: args.remove("--sort")
    terrain = opt(args, "--terrain", "0")
    if len(args) < 2: sys.exit(__doc__)
    cmd, path = args[0], args[1]

    if cmd == "restore":
        img = Image(path); stock = open(STOCK_BIN, "rb").read()
        assert len(stock) == TABLE_BYTES
        for t in range(7): img.write(table_offset(t, site), stock)
        img.save(args[2]); print(f"stock fusion table written to all 7 terrain copies -> {args[2]}"); return

    img = Image(path)
    tlist = range(7) if terrain == "all" else [int(terrain)]
    t0 = tlist[0]
    base = table_offset(t0, site)
    tbl = img.read(base, TABLE_BYTES)

    if cmd == "dump":
        intended = intended_pairs(tbl); gl = glitch_pairs(tbl, intended)
        cards = sum(1 for c in range(1, NCARDS + 1) if record(tbl, c))
        used = used_bytes(tbl)
        big = [c for c in range(1, NCARDS + 1) if record(tbl, c) and record(tbl, c)[0] >= 256]
        print(f"terrain {t0} ({TERRAINS[t0]}): WA_MRG offset 0x{base:X}  (in-file sector 0x{base//2048:X}, "
              f"disc LBA {WA_LBA + base//2048}, RAM 0x{RAM_BASE:08X})")
        print(f"  cards with a record: {cards}   pairs: {len(intended)}   used {used} / {TABLE_BYTES} bytes "
              f"({TABLE_BYTES - used} free)")
        print(f"  records using the 2-byte count form (>=256 partners): {big}")
        print(f"  glitch fusions (game answers, table never intended): {len(gl)}")
        for a, b, r in gl: print(f"    {a:3d} + {b:3d} -> {r:3d}")
        same = all(img.read(table_offset(t, site), TABLE_BYTES) == tbl for t in range(7))
        print(f"  all 7 terrain copies identical: {same}")
    elif cmd == "export":
        intended = intended_pairs(tbl); n = 0
        with open(args[2], "w", newline="") as f:
            w = csv.writer(f); w.writerow(["card1", "card2", "result"])
            for cid in range(1, NCARDS + 1):             # record order, so import round-trips
                seen = set()
                for partner, res in entries(tbl, cid):
                    if partner in seen: continue
                    seen.add(partner); w.writerow([cid, partner, res]); n += 1
        print(f"{n} fusions -> {args[2]}")
    elif cmd == "import":
        pairs = read_csv(args[2])
        new, used = serialize(pairs, safe, sort)
        for t in tlist: img.write(table_offset(t, site), new)
        img.save(args[3])
        print(f"{len(pairs)} fusions, {used} bytes used ({TABLE_BYTES - used} free), "
              f"terrain(s) {list(tlist)} -> {args[3]}")
        gl = glitch_pairs(new)
        if gl: print(f"  note: {len(gl)} glitch fusions remain (odd-count records); use --safe-tails to avoid them")
    elif cmd == "verify":
        pairs = read_csv(args[2]); bad = 0
        gl = {(a, b): r for a, b, r in glitch_pairs(tbl)}
        for a in range(1, NCARDS + 1):
            for b in range(a, NCARDS + 1):
                g = game_lookup(tbl, a, b); want = pairs.get((a, b), 0)
                if g != want and gl.get((a, b)) != g:
                    bad += 1
                    if bad <= 30: print(f"  {a} + {b}: game says {g}, csv says {want}")
        print(f"{'OK' if not bad else bad} mismatches over all {NCARDS*(NCARDS+1)//2} pairs (terrain {t0}); "
              f"{len(gl)} glitch fusions (tail overlap, expected)")
    elif cmd == "lookup":
        a, b = int(args[2]), int(args[3])
        print(game_lookup(tbl, a, b) or "no fusion")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
