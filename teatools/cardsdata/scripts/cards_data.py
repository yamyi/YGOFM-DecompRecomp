#!/usr/bin/env python3
"""Offline clone of TEA-Online's CARDS DATA tool (extend/tools/cardsdata).

Per-card data in SLUS_014.11 (file offset -> RAM = 0x80010000 + off - 0x800):

  stats      0x1C4A44 + (id-1)*4   u32  RAM 0x801D4244 gDuel_adwCardStats
             bits 0-8 ATK/10, 9-17 DEF/10, 18-21 star 2, 22-25 star 1, 26-30 type
  level/attr 0x1C5B33 + (id-1)     u8   RAM 0x801D5333  (attr<<4 | level); the game
             indexes it as 0x801D5332[id]
  names      u16 table 0x1C6000 + id*2 (RAM 0x801D5800 gText_aGlobalOffsets),
             string at 0x1C0800 + off (RAM 0x801D0000 + off), frequency-coded
             bytes, 0xFF terminated, optional colour prefix F8 0A <colour>

  cards_data.py dump    SLUS_014.11 [out.csv]
  cards_data.py apply   SLUS_014.11 out.11 data.csv|data.xlsx
                        [--fields atk,def,star1,star2,type,level,attr] [--names] [--colors]
  cards_data.py verify  SLUS_014.11 --stock STOCK_SLUS
  cards_data.py restore SLUS_014.11 out.11 --stock STOCK_SLUS

apply mirrors the site: rows with an out-of-range value are skipped, fields not
listed keep the file's current value, and --names/--colors repack the WHOLE
name blob (all 722 cards + 24 types + 10 stars + 40 duelist names) exactly the
way the site's writeAllNamesOnSlus() does. That repack is not byte-identical to
the stock layout even with unchanged text, so restore copies the stats, the
level/attr bytes and the name region back from a stock SLUS.
"""
import argparse, csv, re, struct, sys, zipfile

STATS, LEVEL, NAMETAB, NAMESEG, NAMEBLOB = 0x1C4A44, 0x1C5B33, 0x1C6000, 0x1C0800, 0x1C6800
NCARDS = 722
BLOB_LIMIT = 0xA004          # site: overflow when the next free offset reaches 0xA004
ATTRS = ["Light", "Dark", "Earth", "Water", "Fire", "Wind", "Magic", "Trap"]
COLORS = ["white", "yellow", "blue", "green", "grey", "orange", "red", "purple"]

# the site's character table (chunk-common mixin); code -> char
_SITE = {3:"a",21:"b",15:"c",12:"d",1:"e",19:"f",16:"g",9:"h",5:"i",52:"j",22:"k",10:"l",14:"m",6:"n",4:"o",
         20:"p",55:"q",8:"r",7:"s",2:"t",13:"u",25:"v",18:"w",54:"x",17:"y",50:"z",24:"A",45:"B",43:"C",32:"D",
         37:"E",49:"F",41:"G",35:"H",26:"I",59:"J",51:"K",42:"L",30:"M",44:"N",33:"O",47:"P",62:"Q",38:"R",
         29:"S",28:"T",53:"U",57:"V",34:"W",70:"X",36:"Y",63:"Z",48:"-",27:"'",64:'"',31:",",67:"&",85:"@",
         60:"#",68:"/",72:":",80:"*",81:">",84:"<",86:"+",23:"!",0:" ",56:"0",61:"1",58:"2",65:"3",74:"4",
         66:"5",78:"6",69:"7",87:"8",89:"9",11:".",76:"(",75:")",46:"?",39:"[",40:"]",239:" ",226:" "}
DEC = _SITE
ENC = {}
for _k, _v in _SITE.items():          # first code wins, like indexOf on the value list
    ENC.setdefault(_v, _k)

def load(p):
    d = bytearray(open(p, "rb").read())
    if d[:8] != b"PS-X EXE" or not (1572864 <= len(d) <= 3145728):
        sys.exit("not a SLUS_014.11-sized PS-X EXE")
    return d

def read_values(d, cid):
    b0, b1, b2, b3 = d[STATS + 4 * (cid - 1):STATS + 4 * (cid - 1) + 4]
    lv = d[LEVEL + cid - 1]
    return dict(atk=(b0 + 256 * (b1 & 1)) * 10, def_=((b1 >> 1) + 128 * (b2 & 3)) * 10,
                star1=(b2 >> 6) + 4 * (b3 & 3), star2=(b2 >> 2) & 15, type=b3 >> 2,
                level=lv & 15, attr=lv >> 4)

def write_values(d, cid, v):
    a, df = v["atk"] // 10, v["def_"] // 10
    d[STATS + 4 * (cid - 1)] = a % 256
    d[STATS + 4 * (cid - 1) + 1] = (df % 128) * 2 + a // 256
    d[STATS + 4 * (cid - 1) + 2] = (v["star1"] % 4) * 64 + 4 * v["star2"] + df // 128
    d[STATS + 4 * (cid - 1) + 3] = 4 * v["type"] + v["star1"] // 4
    d[LEVEL + cid - 1] = 16 * v["attr"] + v["level"]

def read_name(d, idx):
    """(text, colour) of global string idx, decoded like the site (unknown codes dropped)."""
    a = NAMESEG + struct.unpack_from("<H", d, NAMETAB + 2 * idx)[0]
    text, color, n = "", 0, 0
    while n < 50:
        c = d[a + n]
        if c == 0xFF: break
        if c == 0xF8:
            color = d[a + n + 2]; n += 3; continue
        text += DEC.get(c, ""); n += 1
    return text, color

def name_lists(d):
    cards = [read_name(d, i) for i in range(1, 723)]
    types = [read_name(d, i) for i in range(768, 792)]
    stars = [read_name(d, i) for i in range(792, 802)]
    opps = [read_name(d, i) for i in range(808, 848)]
    return cards, types, stars, opps

def repack_names(d, cards, types, stars, opps):
    """The site's writeAllNamesOnSlus(): returns False on overflow."""
    allst = cards + [(t, 0) for t, _ in types] + [(t, 0) for t, _ in stars] + [(t, 0) for t, _ in opps]
    pos, u = [0x6000], 0x6001
    for text, color in allst:
        a = len(text.strip()) + (3 if color else 0) + 1
        s = u
        if u + a >= 0x8ACD and u < 0x8ACD: s = 0x8ACE      # keep 0x8ACD as a boundary
        if u + a >= 0x8D9A and u < 0x8D9A: s = 0x9200      # skip the location names (848..863)
        u = s; pos.append(u); u += a
    if u >= BLOB_LIMIT:
        return False
    ent = [("", 0x6000, 0)]
    ent += [(cards[m][0], pos[m + 1], cards[m][1]) for m in range(722)]
    ent += [("", 0x6000, 0)] * 45                                     # 723..767 filler
    ent += [(allst[h - 1][0], pos[h], 0) for h in range(723, 757)]    # 768..801 types + stars
    ent += [(allst[722][0], pos[723], 0)] * 6                         # 802..807 "Dragon" x6
    ent += [(allst[f - 1][0], pos[f], 0) for f in range(757, 797)]    # 808..847 duelists
    for i, (_, p, _) in enumerate(ent):
        struct.pack_into("<H", d, NAMETAB + 2 * i, p)
    for v in range(864, 1024):
        struct.pack_into("<H", d, NAMETAB + 2 * v, ent[768][1])
    d[NAMEBLOB] = 0xFF
    for text, p, color in ent:
        o = NAMEBLOB + p - 0x6000
        if color:
            d[o:o + 3] = bytes([0xF8, 0x0A, color]); o += 3
        for ch in text.strip():
            d[o] = ENC.get(ch, 0); o += 1
        d[o] = 0xFF
    return True

# ---- table input ---------------------------------------------------------
COLS = ["id", "name", "atk", "def", "star1", "star2", "type", "level", "attr", "color"]

def rows_from_csv(path):
    for row in csv.reader(open(path, newline="")):
        if row and row[0].strip().isdigit():
            yield (row + [""] * 10)[:10]

def rows_from_xlsx(path):
    """Minimal reader for the site's template: columns A..J = ID NAME ATTACK DEFENDING
    STAR_ID1 STAR_ID2 TYPE_ID LEVEL ATTR_ID NAME_COLOR_ID (no openpyxl needed)."""
    z = zipfile.ZipFile(path)
    shared = [html_unescape("".join(re.findall(r"<t[^>]*>([^<]*)</t>", si)))
              for si in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode(), re.S)] \
        if "xl/sharedStrings.xml" in z.namelist() else []
    sheet = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet")][0]
    for rn, body in re.findall(r'<row r="(\d+)"[^>]*>(.*?)</row>', z.read(sheet).decode(), re.S):
        if int(rn) < 2: continue
        cells = {}
        for col, attrs, inner in re.findall(r'<c r="([A-Z]+)\d+"([^>]*)>(.*?)</c>', body, re.S):
            t = re.search(r't="(\w+)"', attrs)
            v = re.search(r"<v>([^<]*)</v>", inner)
            if t and t.group(1) == "s" and v: cells[col] = shared[int(v.group(1))]
            elif t and t.group(1) == "inlineStr": cells[col] = html_unescape("".join(re.findall(r"<t[^>]*>([^<]*)</t>", inner)))
            elif v: cells[col] = v.group(1)
        yield [cells.get(c, "") for c in "ABCDEFGHIJ"]

def html_unescape(s):
    return s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")

def to_int(s, default=0):
    try: return int(float(s))
    except (TypeError, ValueError): return default

# ---- commands ------------------------------------------------------------
def dump(d, out):
    f = open(out, "w", newline="") if out else sys.stdout
    w = csv.writer(f); w.writerow(COLS)
    for cid in range(1, NCARDS + 1):
        v = read_values(d, cid); text, color = read_name(d, cid)
        w.writerow([cid, text, v["atk"], v["def_"], v["star1"], v["star2"], v["type"], v["level"], v["attr"], color])
    if out: print("wrote", out)

def apply(d, table, fields, names, colors):
    cards, types, stars, opps = name_lists(d)
    n = 0
    for row in table:
        cid = to_int(row[0], -1)
        if not 1 <= cid <= NCARDS:
            continue
        cur = read_values(d, cid)
        new = dict(atk=to_int(row[2]) // 10 * 10, def_=to_int(row[3]) // 10 * 10, star1=to_int(row[4]),
                   star2=to_int(row[5]), type=to_int(row[6]), level=to_int(row[7]), attr=to_int(row[8]))
        ok = (0 <= new["atk"] <= 5110 and 0 <= new["def_"] <= 5110 and 0 <= new["star1"] <= 15
              and 0 <= new["star2"] <= 15 and 0 <= new["type"] <= 63 and 0 <= new["level"] <= 15 and 0 <= new["attr"] <= 15)
        for k in ("atk", "def_", "star1", "star2", "type", "level", "attr"):
            if k.rstrip("_") not in fields:
                new[k] = cur[k]
        if ok:
            write_values(d, cid, new); n += 1
        if names:
            cards[cid - 1] = (row[1].strip(), cards[cid - 1][1])
        if colors:
            cards[cid - 1] = (cards[cid - 1][0], to_int(row[9]))
    if (names or colors) and not repack_names(d, cards, types, stars, opps):
        sys.exit("Name text overflow: the total space for names (up to 0x801DA004) has been exceeded")
    print(f"{n} cards updated" + (", names repacked" if names or colors else ""))

def regions():
    return [(STATS, 4 * NCARDS), (LEVEL, NCARDS), (NAMETAB, 2048), (NAMEBLOB, BLOB_LIMIT - 0x6000)]

def verify(d, s):
    diffs = 0
    for cid in range(1, NCARDS + 1):
        a, b = read_values(d, cid), read_values(s, cid)
        na, nb = read_name(d, cid), read_name(s, cid)
        if a != b or na != nb:
            diffs += 1
            print(f"card {cid:3d} {nb[0]!r}: " + ", ".join(f"{k} {b[k]}->{a[k]}" for k in a if a[k] != b[k])
                  + (f" name {nb!r}->{na!r}" if na != nb else ""))
    same = all(d[o:o + n] == s[o:o + n] for o, n in regions())
    print(f"{diffs} cards differ; card regions byte-identical: {same}")

def restore(d, s):
    for o, n in regions():
        d[o:o + n] = s[o:o + n]

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["dump", "apply", "verify", "restore"])
    ap.add_argument("slus"); ap.add_argument("arg1", nargs="?"); ap.add_argument("arg2", nargs="?")
    ap.add_argument("--fields", default="atk,def,star1,star2,type,level,attr")
    ap.add_argument("--names", action="store_true"); ap.add_argument("--colors", action="store_true")
    ap.add_argument("--stock", help="stock SLUS_014.11 (verify / restore)")
    a = ap.parse_args(); d = load(a.slus)
    if a.cmd == "dump":
        dump(d, a.arg1)
    elif a.cmd == "verify":
        if not a.stock: sys.exit("--stock required")
        verify(d, load(a.stock))
    else:
        if not a.arg1: sys.exit("need an output path")
        if a.cmd == "apply":
            if not a.arg2: sys.exit("need a CSV or XLSX")
            table = rows_from_xlsx(a.arg2) if a.arg2.lower().endswith(".xlsx") else rows_from_csv(a.arg2)
            apply(d, table, set(a.fields.split(",")), a.names, a.colors)
        else:
            if not a.stock: sys.exit("--stock required")
            restore(d, load(a.stock))
        open(a.arg1, "wb").write(d); print("wrote", a.arg1)
