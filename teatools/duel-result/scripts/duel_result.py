#!/usr/bin/env python3
"""Offline clone of TEA-Online's DUEL RESULT tool.

  duel_result.py inspect SLUS_014.11
  duel_result.py apply   SLUS_014.11 out.11 [--starchips N] [--you COLOR] [--com COLOR] [--username]
  duel_result.py restore SLUS_014.11 out.11

COLOR: white yellow blue green grey orange red
"""
import argparse, shutil, struct, sys

OFF_STARS  = 75484     # 0x126DC -> 0x80021EDC
OFF_COLOR  = 74876     # 0x1247C -> 0x80021C7C
OFF_NAME   = 1707284   # 0x1A0D14 -> 0x801B0514
COLORS = ["white", "yellow", "blue", "green", "grey", "orange", "red"]
STOCK_COLOR = bytes([0, 0x14, 2, 0, 3, 0x14, 2, 0])
STOCK_NAME  = bytes([0x24, 0x21, 0x35])
NAME_CTRL   = bytes([0xFC, 0x5A, 0x12])

def load(p):
    d = bytearray(open(p, "rb").read())
    if not (1902591 <= len(d) <= 2097152) or d[:8] != b"PS-X EXE":
        sys.exit("not a SLUS_014.11-sized PS-X EXE")
    return d

def inspect(d):
    lo, hi, b2, b3 = d[OFF_STARS:OFF_STARS+4]
    stars = lo + 256*hi if (b2, b3) == (0x63, 0x24) else 0
    print(f"bonus starchips : {stars}" + ("" if stars or (b2, b3) == (0, 0) else "  (unexpected bytes)"))
    c = d[OFF_COLOR:OFF_COLOR+8]
    if c == STOCK_COLOR:
        print("result colours  : stock (white / white)")
    elif c[2:] == bytes([5, 0x24, 8, 0x57, 0x65, 0xAC]):
        print(f"result colours  : YOU={COLORS[c[0]] if c[0] < 7 else c[0]}  COM={COLORS[c[1]] if c[1] < 7 else c[1]}")
    else:
        print(f"result colours  : unknown bytes {c.hex(' ')}")
    n = d[OFF_NAME:OFF_NAME+3]
    print("result label    : " + {STOCK_NAME: "YOU (stock)", NAME_CTRL: "@player name"}.get(bytes(n), f"unknown {n.hex(' ')}"))

def apply(d, a):
    if a.starchips is not None:
        n = max(0, min(10000, a.starchips))
        d[OFF_STARS:OFF_STARS+4] = bytes([n & 0xFF, n >> 8, 0x63, 0x24]) if n else bytes(4)
    if a.you or a.com:
        y = COLORS.index(a.you or "white"); c = COLORS.index(a.com or "white")
        d[OFF_COLOR:OFF_COLOR+8] = STOCK_COLOR if (y, c) == (0, 0) else bytes([y, c, 5, 0x24, 8, 0x57, 0x65, 0xAC])
    if a.username:
        d[OFF_NAME:OFF_NAME+3] = NAME_CTRL

def restore(d):
    d[OFF_STARS:OFF_STARS+4] = bytes(4)
    d[OFF_COLOR:OFF_COLOR+8] = STOCK_COLOR
    d[OFF_NAME:OFF_NAME+3] = STOCK_NAME

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["inspect", "apply", "restore"]); ap.add_argument("slus"); ap.add_argument("out", nargs="?")
    ap.add_argument("--starchips", type=int); ap.add_argument("--you", choices=COLORS); ap.add_argument("--com", choices=COLORS)
    ap.add_argument("--username", action="store_true")
    a = ap.parse_args(); d = load(a.slus)
    if a.cmd == "inspect": inspect(d); sys.exit()
    if not a.out or a.out == a.slus: sys.exit("give an output path different from the input")
    (apply if a.cmd == "apply" else lambda d, a: restore(d))(d, a)
    open(a.out, "wb").write(d); print("wrote", a.out); inspect(d)
