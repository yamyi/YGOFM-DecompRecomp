#!/usr/bin/env python3
"""Offline clone of TEA-Online's Custom Final Code tool (extend/tools/data/finalcode).

  final_code.py inspect SLUS_014.11
  final_code.py apply   SLUS_014.11 out.11 --codes 86985631 37689434 73153736 92886423 53297534
  final_code.py restore SLUS_014.11 out.11

The five "SECRET NO." codes shown after the credits live at file 0x81350 (RAM 0x80090B50,
D_80090B50): 5 x (u16 first four digits, u16 last four digits), little-endian.
Main_RunCredits picks entry (save game id at 0x801D0534) % 5.
"""
import argparse, struct, sys

OFF = 0x81350
STOCK = [86985631, 37689434, 73153736, 92886423, 53297534]

def load(p):
    d = bytearray(open(p, "rb").read())
    if d[:8] != b"PS-X EXE" or not (1902591 <= len(d) <= 2097152):
        sys.exit("not a SLUS_014.11-sized PS-X EXE")
    return d

def read(d):
    return [hi * 10000 + lo for hi, lo in (struct.unpack_from("<HH", d, OFF + 4*i) for i in range(5))]

def write(d, codes):
    for i, c in enumerate(codes):
        c = int(c)
        if not 0 <= c <= 99999999: sys.exit(f"code {c} is not 8 digits")
        struct.pack_into("<HH", d, OFF + 4*i, c // 10000, c % 10000)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["inspect", "apply", "restore"]); ap.add_argument("slus"); ap.add_argument("out", nargs="?")
    ap.add_argument("--codes", nargs=5, type=int)
    a = ap.parse_args(); d = load(a.slus)
    if a.cmd == "inspect":
        for i, c in enumerate(read(d)):
            print(f"code {i+1}: {c:08d}" + ("" if c == STOCK[i] else "  (stock %08d)" % STOCK[i]))
        sys.exit(0)
    if not a.out: sys.exit("need an output path")
    if a.cmd == "apply":
        if not a.codes: sys.exit("--codes c1 c2 c3 c4 c5 required")
        write(d, a.codes)
    else:
        write(d, STOCK)
    open(a.out, "wb").write(d); print(f"wrote {a.out}:", " ".join("%08d" % c for c in read(d)))
