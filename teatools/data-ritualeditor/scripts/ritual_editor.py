#!/usr/bin/env python3
"""Offline clone of TEA-Online's Ritual Editor (extend/tools/data/ritualeditor).

The ritual table lives in WA_MRG.MRG, once per terrain package (7 copies,
481280 bytes = 235 sectors apart):

    WA offset 0xB97800 + 0x75800*k   (k = 0..6, in-file sector 5935 + 235k,
                                       disc LBA 16037 + 235k)
    -> RAM 0x801799D8  gDuel_awRitualData, copied by the duel loader (0x800 bytes)

Record = 5 x u16 LE: [type<<10 | spell_id, mat1, mat2, mat3, result]; a record of
five zeros terminates the list. Stock: 24 records + terminator, rest 0xFF.

  ritual_editor.py dump    WA_MRG.MRG|disc.bin [out.csv] [--terrain k] [--slus SLUS_014.11]
  ritual_editor.py verify  WA_MRG.MRG|disc.bin            # compare all 7 copies with stock
  ritual_editor.py apply   WA_MRG.MRG|disc.bin out data.csv [--terrain k]   # default: all 7 copies
  ritual_editor.py restore WA_MRG.MRG|disc.bin out                          # stock table, all 7 copies

CSV columns: type,spell,mat1,mat2,mat3,result (names after that are ignored).
Input may be the 0x2400000-byte WA_MRG.MRG or a MODE2/2352 disc image; the
output file is always a copy, the input is never modified.
"""
import argparse, csv, struct, sys

TABLE_OFF = 0xB97800
COPY_STRIDE = 481280
COPIES = 7
MAX_REC = 24            # the site's cap; the 0x800-byte slot holds up to 203
WA_LBA = 10102
WA_SIZE = 0x2400000

# stock table, verified on the US disc (all 7 copies identical)
STOCK = [
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
    """WA_MRG.MRG bytes, either the bare file or inside a raw disc image."""
    def __init__(self, path):
        self.data = bytearray(open(path, "rb").read())
        self.disc = len(self.data) > WA_SIZE and self.data[0x9319:0x931E] == b"CD001"
        if not self.disc and len(self.data) != WA_SIZE:
            print(f"warning: {len(self.data)} bytes, expected {WA_SIZE} for WA_MRG.MRG", file=sys.stderr)
    def pos(self, off):
        if not self.disc:
            return off
        return (WA_LBA + off // 2048) * 2352 + 24 + off % 2048
    def read(self, off, n):
        out = bytearray()
        while n:
            k = min(n, 2048 - off % 2048) if self.disc else n
            p = self.pos(off); out += self.data[p:p + k]; off += k; n -= k
        return bytes(out)
    def write(self, off, b):
        i = 0
        while i < len(b):
            k = min(len(b) - i, 2048 - off % 2048) if self.disc else len(b) - i
            p = self.pos(off); self.data[p:p + k] = b[i:i + k]; off += k; i += k

def parse(b):
    recs = []
    for i in range(len(b) // 10):
        r = struct.unpack_from("<5H", b, i * 10)
        if not any(r):
            break
        recs.append((r[0] >> 10, r[0] & 1023, r[1] & 1023, r[2] & 1023, r[3] & 1023, r[4] & 1023))
    return recs

def encode(recs):
    """Exactly what the site writes: MAX_REC slots (unused ones zeroed) + a zero terminator."""
    if len(recs) > MAX_REC:
        sys.exit(f"{len(recs)} rituals; the site (and this clone) caps the list at {MAX_REC}")
    b = bytearray()
    for i in range(MAX_REC + 1):
        if i < len(recs):
            t, sp, m1, m2, m3, res = recs[i]
            b += struct.pack("<5H", (t << 10) | sp, m1, m2, m3, res)
        else:
            b += bytes(10)
    return bytes(b)

def read_names(slus):
    if not slus:
        return lambda i: ""
    d = open(slus, "rb").read()
    RAW = {0:' ',1:'e',2:'t',3:'a',4:'o',5:'i',6:'n',7:'s',8:'r',9:'h',10:'l',11:'.',12:'d',13:'u',14:'m',
           15:'c',16:'g',17:'y',18:'w',19:'f',20:'p',21:'b',22:'k',24:'A',25:'v',26:'I',27:"'",28:'T',29:'S',
           30:'M',31:',',32:'D',33:'O',34:'W',35:'H',36:'Y',37:'E',38:'R',41:'G',42:'L',43:'C',44:'N',45:'B',
           47:'P',48:'-',49:'F',50:'z',51:'K',52:'j',53:'U',54:'x',55:'q',56:'0',57:'V',58:'2',59:'J',60:'#',
           61:'1',62:'Q',63:'Z',65:'3',66:'5',67:'&',69:'7',70:'X',74:'4',78:'6',85:'a',87:'8',89:'9'}
    def name(i):
        if not 1 <= i <= 722: return ""
        a = 0x1C0800 + struct.unpack_from("<H", d, 0x1C6000 + 2 * i)[0]; s = ""
        while d[a] != 0xFF:
            s += RAW.get(d[a], "?"); a += 1
        return s
    return name

def dump(img, out, terrain, slus):
    k = 0 if terrain is None else terrain
    recs = parse(img.read(TABLE_OFF + k * COPY_STRIDE, 0x800))
    name = read_names(slus)
    f = open(out, "w", newline="") if out else sys.stdout
    w = csv.writer(f)
    w.writerow(["type", "spell", "mat1", "mat2", "mat3", "result", "spell_name", "mat1_name", "mat2_name", "mat3_name", "result_name"])
    for r in recs:
        w.writerow(list(r) + [name(r[1]), name(r[2]), name(r[3]), name(r[4]), name(r[5])])
    if out: print(f"{len(recs)} rituals -> {out}")

def verify(img):
    ok = True
    for k in range(COPIES):
        recs = parse(img.read(TABLE_OFF + k * COPY_STRIDE, 0x800))
        same = recs == STOCK
        ok &= same
        print(f"copy {k} @0x{TABLE_OFF + k*COPY_STRIDE:X}: {len(recs)} rituals, {'stock' if same else 'MODIFIED'}")
    return ok

def load_csv(path):
    recs = []
    for row in csv.reader(open(path, newline="")):
        if not row or not row[0].strip().lstrip("-").isdigit():
            continue
        v = [int(x) for x in row[:6]]
        if len(v) < 6:
            sys.exit(f"bad row {row}")
        if not (0 <= v[0] <= 3 and all(0 <= x <= 1023 for x in v[1:])):
            sys.exit(f"out of range: {row}")
        recs.append(tuple(v))
    return recs

def write_all(img, recs, terrain):
    b = encode(recs)
    for k in (range(COPIES) if terrain is None else [terrain]):
        img.write(TABLE_OFF + k * COPY_STRIDE, b)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["dump", "verify", "apply", "restore"])
    ap.add_argument("src"); ap.add_argument("arg1", nargs="?"); ap.add_argument("arg2", nargs="?")
    ap.add_argument("--terrain", type=int, choices=range(COPIES), help="one package copy instead of all 7")
    ap.add_argument("--slus", help="SLUS_014.11 to decode card names in dump")
    a = ap.parse_args(); img = Image(a.src)
    if a.cmd == "dump":
        dump(img, a.arg1, a.terrain, a.slus)
    elif a.cmd == "verify":
        sys.exit(0 if verify(img) else 1)
    else:
        if not a.arg1: sys.exit("need an output path")
        if a.cmd == "apply":
            if not a.arg2: sys.exit("need a CSV")
            write_all(img, load_csv(a.arg2), a.terrain)
        else:
            write_all(img, STOCK, None)
        open(a.arg1, "wb").write(img.data); print("wrote", a.arg1)
