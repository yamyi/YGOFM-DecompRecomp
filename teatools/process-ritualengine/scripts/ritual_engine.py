#!/usr/bin/env python3
"""Offline clone of TEA-Online's RITUAL ENGINE tool (extend/tools/process/ritualengine).

The tool edits BOTH files:

  SLUS_014.11 : three 8-byte redirections inside Duel_FindRitualRecipe
                (table801a7ad8_recipe_lookup, 0x8002C7E8) ->
                  0x8002C7F4  j 0x80179B48 ; nop      (key compare)
                  0x8002C8B0  j 0x80179BE8 ; nop      (material compare)
                  0x8002C8D0  j 0x80179B48 ; addiu t4,t4,10   (no-match retry)
  WA_MRG.MRG  : 560 bytes of new MIPS at the ritual sector +0x170 (RAM 0x80179B48),
                112 zero bytes of scratch at +0x100 (RAM 0x80179AD8) and up to 24
                5-u16 recipe records at +0x000 (RAM 0x801799D8) -- written into all
                seven terrain copies (stride 0x75800).

Record = 5 x u16 LE: [type<<10 | spell_id, req1, req2, req3, result].
`type` is what this tool adds on top of the plain Ritual Editor:

    0  exact card ids (stock behaviour)
    1  req = card TYPE   (0..23), material ATK must be < result ATK
    2  req = card ATTRIBUTE (0..7), material ATK must be < result ATK
    3  any monster whose ATK is < the result's ATK (reqs ignored)

  ritual_engine.py inspect     SLUS_014.11 [WA_MRG.MRG|disc.bin]
  ritual_engine.py dump        WA_MRG.MRG|disc.bin [out.csv] [--terrain k]
  ritual_engine.py apply-slus  SLUS_014.11 out.11
  ritual_engine.py restore-slus SLUS_014.11 out.11
  ritual_engine.py apply-wa    WA_MRG.MRG|disc.bin out.mrg [--csv recipes.csv]
  ritual_engine.py restore-wa  WA_MRG.MRG|disc.bin out.mrg

CSV columns: type,spell,req1,req2,req3,result (a header row is skipped).
Inputs are never modified; every write goes to the named output copy.
"""
import argparse, csv, os, struct, sys

# ---------------------------------------------------------------- WA geometry
TABLE_OFF = 0xB97800          # RAM 0x801799D8 gDuel_awRitualData
SCRATCH_OFF = TABLE_OFF + 0x100   # RAM 0x80179AD8, 112 bytes
SCRIPT_OFF = TABLE_OFF + 0x170    # RAM 0x80179B48, 560 bytes
COPY_STRIDE = 481280
COPIES = 7
MAX_REC = 24                  # the tool's cap (the scratch block starts at +0x100)
WA_LBA = 10102
WA_SIZE = 0x2400000

# ------------------------------------------------------------- SLUS geometry
JUMPS = {                     # file offset -> patched bytes (all 8 bytes long)
    118772: bytes([210, 230, 5, 8, 0, 0, 0, 0]),        # 0x8002C7F4
    118960: bytes([250, 230, 5, 8, 0, 0, 0, 0]),        # 0x8002C8B0
    118992: bytes([210, 230, 5, 8, 10, 0, 140, 37]),    # 0x8002C8D0
}
STOCK_JUMPS = {
    118772: bytes.fromhex("0000829500000000"),
    118960: bytes.fromhex("0000229500000000"),
    118992: bytes.fromhex("4cb200082110 0000".replace(" ", "")),
}
SCRIPT = bytes([24,128,2,60,216,154,66,36,0,0,82,172,4,0,83,172,8,0,84,172,12,0,85,172,0,0,146,149,0,0,0,0,255,3,83,50,130,162,18,0,3,0,148,50,80,0,69,172,84,0,83,172,88,0,84,172,8,0,149,149,29,128,18,60,64,66,82,38,128,168,21,0,33,144,85,2,0,0,82,142,0,0,0,0,255,1,82,50,92,0,82,172,0,0,0,0,0,0,82,140,4,0,83,140,8,0,84,140,12,0,85,140,84,0,66,140,0,0,0,0,255,3,66,48,3,0,64,16,0,0,0,0,1,178,0,8,0,0,0,0,76,178,0,8,0,0,2,36,0,0,0,0,0,0,0,0,0,0,0,0,24,128,2,60,216,154,66,36,0,0,82,172,4,0,83,172,8,0,84,172,12,0,85,172,88,0,82,140,0,0,51,149,3,0,82,50,0,0,0,0,13,0,64,22,0,0,0,0,0,0,82,140,8,0,84,140,12,0,85,140,3,0,115,16,4,0,83,140,48,178,0,8,0,0,0,0,54,178,0,8,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,20,36,22,0,146,22,0,0,0,0,29,128,20,60,64,66,148,38,128,24,3,0,33,160,131,2,0,0,149,142,0,0,0,0,130,30,21,0,63,0,99,48,255,1,181,50,92,0,84,148,0,0,0,0,43,160,180,2,3,0,128,22,0,0,0,0,1,0,3,36,0,0,19,36,6,231,5,8,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,20,36,30,0,146,22,0,0,0,0,29,128,20,60,64,66,148,38,128,24,3,0,33,160,131,2,0,0,149,142,0,0,0,0,255,1,181,50,92,0,84,148,0,0,0,0,43,160,180,2,12,0,128,18,0,0,0,0,130,24,3,0,29,128,20,60,50,83,148,38,33,160,131,2,0,0,148,146,0,0,0,0,2,25,20,0,6,231,5,8,0,0,0,0,1,0,3,36,1,0,19,36,6,231,5,8,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,29,128,20,60,64,66,148,38,128,24,3,0,33,160,131,2,0,0,149,142,0,0,0,0,255,1,181,50,92,0,84,148,33,24,96,2,43,160,180,2,3,0,128,22,0,0,0,0,1,0,3,36,0,0,19,36,6,231,5,8,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0])

TYPE_NAMES = {0: "cards", 1: "cardtype", 2: "attribute", 3: "anymonster"}
ATTRS = ["Light", "Dark", "Earth", "Water", "Fire", "Wind", "Magic", "Trap"]

# stock table (identical in all 7 copies; same list as data-ritualeditor)
STOCK_RECS = [
    (0, 670, 27, 38, 58, 364), (0, 671, 85, 298, 377, 360), (0, 673, 201, 403, 483, 356),
    (0, 674, 186, 261, 595, 365), (0, 675, 1, 1, 1, 380), (0, 665, 255, 296, 629, 362),
    (0, 666, 29, 31, 101, 357), (0, 667, 371, 372, 373, 374), (0, 676, 249, 395, 511, 701),
    (0, 677, 14, 295, 547, 702), (0, 678, 3, 64, 453, 703), (0, 679, 160, 161, 535, 704),
    (0, 680, 6, 47, 571, 705), (0, 691, 168, 294, 604, 706), (0, 692, 89, 449, 451, 710),
    (0, 693, 102, 182, 220, 720), (0, 694, 178, 269, 288, 709), (0, 695, 166, 405, 416, 715),
    (0, 696, 52, 480, 533, 717), (0, 697, 239, 378, 621, 716), (0, 698, 266, 635, 638, 708),
    (0, 699, 146, 479, 485, 719), (0, 700, 436, 441, 542, 718), (0, 721, 7, 35, 417, 722),
]


class Image:
    """WA_MRG.MRG bytes, either the bare file or inside a MODE2/2352 disc image."""

    def __init__(self, path):
        self.data = bytearray(open(path, "rb").read())
        self.disc = len(self.data) > WA_SIZE and self.data[0x9319:0x931E] == b"CD001"
        if not self.disc and len(self.data) != WA_SIZE:
            print("warning: %d bytes, expected %d for WA_MRG.MRG" % (len(self.data), WA_SIZE),
                  file=sys.stderr)

    def pos(self, off):
        return off if not self.disc else (WA_LBA + off // 2048) * 2352 + 24 + off % 2048

    def read(self, off, n):
        out = bytearray()
        while n:
            k = min(n, 2048 - off % 2048) if self.disc else n
            p = self.pos(off)
            out += self.data[p:p + k]
            off += k
            n -= k
        return bytes(out)

    def write(self, off, b):
        i = 0
        while i < len(b):
            k = min(len(b) - i, 2048 - off % 2048) if self.disc else len(b) - i
            p = self.pos(off)
            self.data[p:p + k] = b[i:i + k]
            off += k
            i += k

    def save(self, path):
        open(path, "wb").write(self.data)


# --------------------------------------------------------------------- SLUS
def load_slus(p):
    d = bytearray(open(p, "rb").read())
    if not (1782579 <= len(d) <= 8388608) or d[:8] != b"PS-X EXE":
        sys.exit("not a SLUS_014.11-sized PS-X EXE")
    return d


def slus_state(d):
    if all(bytes(d[o:o + 8]) == v for o, v in JUMPS.items()):
        return "engine"
    if all(bytes(d[o:o + 8]) == v for o, v in STOCK_JUMPS.items()):
        return "stock"
    return "other"


# ----------------------------------------------------------------------- WA
def parse_recs(b):
    out = []
    for i in range(MAX_REC):
        w = struct.unpack_from("<5H", b, 10 * i)
        if not any(w):
            break
        out.append((w[0] >> 10 & 3, w[0] & 0x3FF, w[1], w[2], w[3], w[4]))
    return out


def encode_recs(recs):
    if len(recs) > MAX_REC:
        sys.exit("at most %d records fit before the scratch block at +0x100" % MAX_REC)
    b = bytearray(250)                       # 24 records + a zero terminator record
    for i, (t, s, r1, r2, r3, res) in enumerate(recs):
        struct.pack_into("<5H", b, 10 * i, (t & 3) << 10 | (s & 0x3FF), r1, r2, r3, res)
    return bytes(b)


def wa_state(img, k=0):
    base = TABLE_OFF + COPY_STRIDE * k
    cur = img.read(base + 0x170, len(SCRIPT))
    if cur == SCRIPT:
        return "engine"
    if set(cur) == {0xFF}:
        return "stock"
    return "other"


def describe(rec):
    t, s, r1, r2, r3, res = rec
    if t == 0:
        mats = "cards %d, %d, %d" % (r1, r2, r3)
    elif t == 1:
        mats = "card types %d, %d, %d (ATK < result)" % (r1, r2, r3)
    elif t == 2:
        f = lambda x: ATTRS[x] if x < 8 else str(x)
        mats = "attributes %s, %s, %s (ATK < result)" % (f(r1), f(r2), f(r3))
    else:
        mats = "any 3 monsters with ATK < result"
    return "spell %-3d  %-10s  %-46s -> %d" % (s, TYPE_NAMES.get(t, t), mats, res)


# ------------------------------------------------------------------ commands
def cmd_inspect(a):
    d = load_slus(a.slus)
    st = slus_state(d)
    print("SLUS_014.11 : " + {"engine": "ritual-engine jumps INSTALLED",
                              "stock": "stock",
                              "other": "neither stock nor ritual-engine at the 3 hook sites"}[st])
    for o in sorted(JUMPS):
        ram = 0x80010000 + o - 0x800
        print("   %#010x (file %#x): %s" % (ram, o, bytes(d[o:o + 8]).hex(" ")))
    if not a.wa:
        return
    img = Image(a.wa)
    for k in range(COPIES):
        base = TABLE_OFF + COPY_STRIDE * k
        s = wa_state(img, k)
        recs = parse_recs(img.read(base, 250))
        print("WA copy %d @ %#x: script %-6s  %d records%s"
              % (k, base, s, len(recs), "  (= stock recipes)" if recs == STOCK_RECS else ""))
    for r in parse_recs(Image(a.wa).read(TABLE_OFF, 250)):
        print("   " + describe(r))


def cmd_dump(a):
    img = Image(a.wa)
    recs = parse_recs(img.read(TABLE_OFF + COPY_STRIDE * a.terrain, 250))
    if a.out:
        with open(a.out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["type", "spell", "req1", "req2", "req3", "result"])
            w.writerows(recs)
        print("wrote %s (%d records)" % (a.out, len(recs)))
    else:
        for r in recs:
            print(describe(r))


def load_csv(path):
    out = []
    for row in csv.reader(open(path)):
        if not row or not row[0].strip().lstrip("-").isdigit():
            continue
        t, s, r1, r2, r3, res = (int(x) for x in row[:6])
        if not 0 <= t <= 3:
            sys.exit("type must be 0..3, got %d" % t)
        out.append((t, s, r1, r2, r3, res))
    return out


def cmd_apply_slus(a):
    d = load_slus(a.slus)
    if slus_state(d) == "other":
        sys.exit("the three hook sites are neither stock nor already patched -- refusing")
    for o, v in JUMPS.items():
        d[o:o + 8] = v
    open(a.out, "wb").write(d)
    print("wrote", a.out)


def cmd_restore_slus(a):
    d = load_slus(a.slus)
    for o, v in STOCK_JUMPS.items():
        d[o:o + 8] = v
    open(a.out, "wb").write(d)
    print("wrote", a.out)


def cmd_apply_wa(a):
    img = Image(a.wa)
    recs = load_csv(a.csv) if a.csv else parse_recs(img.read(TABLE_OFF, 250))
    blob = encode_recs(recs)
    for k in range(COPIES):
        base = TABLE_OFF + COPY_STRIDE * k
        img.write(base, blob)
        img.write(base + 0x100, bytes(112))
        img.write(base + 0x170, SCRIPT)
    img.save(a.out)
    print("wrote %s (%d records x 7 copies)" % (a.out, len(recs)))


def cmd_restore_wa(a):
    img = Image(a.wa)
    blob = encode_recs(STOCK_RECS)
    for k in range(COPIES):
        base = TABLE_OFF + COPY_STRIDE * k
        img.write(base, blob)
        img.write(base + 250, b"\xff" * (0x800 - 250))
    img.save(a.out)
    print("wrote", a.out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("inspect"); p.add_argument("slus"); p.add_argument("wa", nargs="?"); p.set_defaults(fn=cmd_inspect)
    p = sub.add_parser("dump"); p.add_argument("wa"); p.add_argument("out", nargs="?")
    p.add_argument("--terrain", type=int, default=0, choices=range(COPIES)); p.set_defaults(fn=cmd_dump)
    p = sub.add_parser("apply-slus"); p.add_argument("slus"); p.add_argument("out"); p.set_defaults(fn=cmd_apply_slus)
    p = sub.add_parser("restore-slus"); p.add_argument("slus"); p.add_argument("out"); p.set_defaults(fn=cmd_restore_slus)
    p = sub.add_parser("apply-wa"); p.add_argument("wa"); p.add_argument("out")
    p.add_argument("--csv"); p.set_defaults(fn=cmd_apply_wa)
    p = sub.add_parser("restore-wa"); p.add_argument("wa"); p.add_argument("out"); p.set_defaults(fn=cmd_restore_wa)
    a = ap.parse_args()
    for k in ("slus", "wa", "out"):
        v = getattr(a, k, None)
        if v and k != "out" and getattr(a, "out", None) == v:
            sys.exit("output must differ from the input")
    a.fn(a)


if __name__ == "__main__":
    main()
