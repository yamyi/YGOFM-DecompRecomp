#!/usr/bin/env python3
"""Offline clone of TEA-Online's "x2" tool (extend/tools/data/x2): doubles the
ATK/DEF range of SLUS_014.11 by turning every "stat * 10" into "stat * 20" and
halving the stored per-card values so the cards keep their printed numbers.

  x2.py inspect SLUS_014.11
  x2.py apply   SLUS_014.11 out.11
  x2.py restore SLUS_014.11 out.11 [--stock STOCK_SLUS]

apply is the site's one-shot "MODIFY PROCESS": 23 `sll rd,rt,1` -> `sll rd,rt,2`
(byte 0x40 -> 0x80) plus atk/=2, def/=2 on all 722 stats words.
restore undoes the code bytes and doubles the values back; halving loses the low
bit (135 stock cards have an ATK or DEF that is not a multiple of 20), so pass
--stock to copy the 722 exact words back and get a byte-identical file.
"""
import argparse, struct, sys

# file offsets of the low byte of each `sll ..,1` (stock 0x40, patched 0x80)
SITES = [36868, 36892, 37048, 37072, 86732, 86784, 100488, 100520, 100724, 100756,
         105396, 105460, 119884, 141608, 141640, 142728, 142760, 142964, 142996,
         144812, 144832, 333152, 333188]
STATS = 0x1C4A44          # u32 per card, id-1; RAM 0x801D4244 (gDuel_adwCardStats)
NCARDS = 722

def ram(off): return 0x80010000 + off - 0x800

def load(p):
    d = bytearray(open(p, "rb").read())
    if d[:8] != b"PS-X EXE" or not (1048576 <= len(d) <= 3145728):
        sys.exit("not a SLUS_014.11-sized PS-X EXE")
    return d

def state(d):
    v = {d[o] for o in SITES}
    return "stock" if v == {0x40} else "x2" if v == {0x80} else "mixed/unknown %s" % sorted(hex(x) for x in v)

def words(d):
    return [struct.unpack_from("<I", d, STATS + 4 * i)[0] for i in range(NCARDS)]

def inspect(d):
    st = state(d)
    print("multiplier code :", st, "(x20 shifts)" if st == "x2" else "(x10 shifts)" if st == "stock" else "")
    for o in SITES:
        w = struct.unpack_from("<I", d, o)[0]
        print(f"  file 0x{o:06X} RAM 0x{ram(o):08X} word 0x{w:08X}  sll shamt={ (w>>6)&31 }")
    w = words(d)
    mult = 20 if st == "x2" else 10
    a, df = w[0] & 0x1FF, (w[0] >> 9) & 0x1FF
    print(f"card 1 stored atk/def fields: {a}/{df} -> displayed {a*mult}/{df*mult}")
    print("max representable ATK/DEF   :", 511 * mult, "(Duel_GetBaseCardStat clamps to 9999)")

def apply(d):
    if state(d) != "stock":
        sys.exit("code is not stock; the site refuses to run twice and so do we")
    for o in SITES:
        d[o] = 0x80
    for i, w in enumerate(words(d)):
        a = (w & 0x1FF) // 2
        df = ((w >> 9) & 0x1FF) // 2
        struct.pack_into("<I", d, STATS + 4 * i, (w >> 18 << 18) | (df << 9) | a)

def restore(d, stock):
    for o in SITES:
        d[o] = 0x40
    if stock is not None:
        s = load(stock)
        d[STATS:STATS + 4 * NCARDS] = s[STATS:STATS + 4 * NCARDS]
        return
    lossy = 0
    for i, w in enumerate(words(d)):
        a = min(511, (w & 0x1FF) * 2)
        df = min(511, ((w >> 9) & 0x1FF) * 2)
        struct.pack_into("<I", d, STATS + 4 * i, (w >> 18 << 18) | (df << 9) | a)
    print("restored code; values doubled back (low bit lost where the stock value was odd; use --stock for an exact copy)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["inspect", "apply", "restore"])
    ap.add_argument("slus"); ap.add_argument("out", nargs="?")
    ap.add_argument("--stock", help="stock SLUS_014.11 to copy the exact stats words from (restore only)")
    a = ap.parse_args(); d = load(a.slus)
    if a.cmd == "inspect":
        inspect(d); sys.exit(0)
    if not a.out:
        sys.exit("need an output path")
    if a.cmd == "apply":
        apply(d)
    else:
        restore(d, a.stock)
    open(a.out, "wb").write(d); print("wrote", a.out)
