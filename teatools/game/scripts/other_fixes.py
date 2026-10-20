#!/usr/bin/env python3
"""Offline clone of TEA-Online "Other Fixes" (route extend/tools/game, page version V.220214).

Four independent patches on SLUS_014.11 (US, 1,902,592 bytes):

  cpu722      CPU deck generator may draw card ids 721 and 722
              0x14CCC  slti v0,s1,0x2D0 -> 0x2D2          (Duel_ShuffleDeck 0x800244CC)
  dmk         Duel Master K (opponent 39) gets a generated deck instead of a copy of yours
              0x8584   slti v0,v1,0x27  -> 0x127          (func_800179F4 0x80017D84, byte +1 = 0x01)
  exodia-stec Exodia win scores -127 instead of +40 on the rank score (S-TEC instead of S-POW)
              0x9BDC / 0x11DF4 / 0x8BD0  addiu vX,zero,0x28 -> 0xFF81 (-127)
  gs-bonus N  guardian-star bonus amount (stock 500, site caps at 5000; hidden in the UI)
              0x10770 slti v0,v0,N / 0x10784 addiu v0,zero,N (popup count-up, func_8001FDB4)
              0x1D3D0 addiu v0,zero,N (Duel_CalcGuardianStarMatchup return; the -500 branch is NOT patched)

Usage:
  other_fixes.py inspect SLUS
  other_fixes.py apply   SLUS [--cpu722 on|off] [--dmk on|off] [--exodia-stec on|off] [--gs-bonus N] [-o OUT]
  other_fixes.py restore SLUS [-o OUT]        put every site-touched byte back to stock

Work on a COPY.  The stock values below were read from the retail SLUS_014.11.
"""
import argparse
import struct
import sys

SIZE_MIN, SIZE_MAX = 1902591, 2097152


def ram(off):
    return 0x80010000 + off - 0x800


# name -> list of (file offset, stock bytes, patched bytes)
TOGGLES = {
    "cpu722": [(0x14CCC, b"\xD0\x02", b"\xD2\x02")],
    "dmk": [(0x8585, b"\x00", b"\x01")],
    "exodia-stec": [(0x9BDC, b"\x28\x00", b"\x81\xFF"),
                    (0x11DF4, b"\x28\x00", b"\x81\xFF"),
                    (0x8BD0, b"\x28\x00", b"\x81\xFF")],
}
GS_SITES = [0x10770, 0x10784, 0x1D3D0]
GS_STOCK = 500


def state(data, name):
    vals = [(bytes(data[o:o + len(s)]) == s, bytes(data[o:o + len(p)]) == p) for o, s, p in TOGGLES[name]]
    if all(p for _, p in vals):
        return "on"
    if all(s for s, _ in vals):
        return "off"
    return "mixed/unknown"


def gs_value(data):
    v = [struct.unpack_from("<H", data, o)[0] for o in GS_SITES]
    return v[0] if len(set(v)) == 1 else v


def inspect(data):
    for name in TOGGLES:
        print(f"{name:12s} {state(data, name)}")
        for o, s, p in TOGGLES[name]:
            print(f"    0x{o:06X} (RAM 0x{ram(o):08X}) = {bytes(data[o:o+len(s)]).hex(' ')}  stock {s.hex(' ')}  patched {p.hex(' ')}")
    print(f"{'gs-bonus':12s} {gs_value(data)}  (stock {GS_STOCK})")
    for o in GS_SITES:
        print(f"    0x{o:06X} (RAM 0x{ram(o):08X}) = {struct.unpack_from('<H', data, o)[0]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("inspect"); p.add_argument("slus")
    p = sub.add_parser("apply"); p.add_argument("slus"); p.add_argument("-o", "--out")
    for name in TOGGLES:
        p.add_argument("--" + name, choices=["on", "off"])
    p.add_argument("--gs-bonus", type=int)
    p = sub.add_parser("restore"); p.add_argument("slus"); p.add_argument("-o", "--out")
    a = ap.parse_args()

    data = bytearray(open(a.slus, "rb").read())
    if not SIZE_MIN <= len(data) <= SIZE_MAX:
        sys.exit(f"{a.slus}: size {len(data)} outside the tool's accepted range")
    if a.cmd == "inspect":
        return inspect(data)
    if a.cmd == "restore":
        for name in TOGGLES:
            for o, s, _ in TOGGLES[name]:
                data[o:o + len(s)] = s
        for o in GS_SITES:
            struct.pack_into("<H", data, o, GS_STOCK)
    else:
        for name in TOGGLES:
            want = getattr(a, name.replace("-", "_"))
            if want is None:
                continue
            for o, s, p in TOGGLES[name]:
                data[o:o + len(s)] = p if want == "on" else s
        if a.gs_bonus is not None:
            n = max(0, min(5000, a.gs_bonus))      # site clamps 0..5000; keep the immediate positive
            for o in GS_SITES:
                struct.pack_into("<H", data, o, n)
    out = a.out or a.slus
    open(out, "wb").write(data)
    inspect(data)
    print(f"written {out}")


if __name__ == "__main__":
    main()
