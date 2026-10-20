#!/usr/bin/env python3
"""Offline clone of TEA-Online's Unique Drop process (extend/tools/process/uniquedrop).

  unique_drop.py inspect SLUS_014.11
  unique_drop.py apply   SLUS_014.11 out.11 --set 1=20 --set 39=380 ...   (opponent id = card id)
  unique_drop.py apply   SLUS_014.11 out.11 --clear 5
  unique_drop.py restore SLUS_014.11 out.11

Installs a stub at 0x801DB2B0 (file 0x1CBAB0) hooked from the epilogue of
Duel_SelectCardDrop (0x80021884, file 0x12084) and a 40-entry u16 table at
0x801DB330 (file 0x1CBB30): when the current opponent's bit in
gFreeDuel_dwUnlockedDuelists (0x801D06F4) is still clear and table[opponent] != 0,
that card is returned instead of the weighted roll. Only the stock (single-drop)
SLUS layout is handled here; the site's multi-drop variant hooks 0x801AACD8 instead.
"""
import argparse, sys

OFF_HOOK, OFF_STUB, OFF_TABLE = 0x12084, 0x1CBAB0, 0x1CBB30
STOCK_HOOK = bytes.fromhex("1400bf8f" "1000b08f")          # lw ra,0x14(sp) / lw s0,0x10(sp)
PATCH_HOOK = bytes.fromhex("ac6c0708" "0a80013c")          # j 0x801DB2B0 / lui at,0x800A
STUB = bytes.fromhex(
    "61b32124" "00002190" "1d80033c" "f4066324" "c3b00100" "21187600" "00006390" "07003730"
    "07001624" "23b0d702" "07b0c302" "0100d632" "0b00c016" "00000000" "1e80033c" "30b36324"
    "40080100" "21186100" "00007694" "00000000" "0300c012" "00000000" "00000000" "2110c002"
    "1080013c" "ffff4324" "21b00000" "21b80000" "1400bf8f" "1000b08f" "23860008" "00000000")
NOPP = 39

def load(p):
    d = bytearray(open(p, "rb").read())
    if d[:8] != b"PS-X EXE" or not (1902591 <= len(d) <= 2097152):
        sys.exit("not a SLUS_014.11-sized PS-X EXE")
    return d

def installed(d):
    return bytes(d[OFF_HOOK:OFF_HOOK+8]) == PATCH_HOOK and bytes(d[OFF_STUB:OFF_STUB+len(STUB)]) == STUB

def table(d):
    return [d[OFF_TABLE + 2*i] | (d[OFF_TABLE + 2*i + 1] << 8) for i in range(NOPP + 1)]

def inspect(d):
    if installed(d):
        print("unique drop process: installed")
        for i, c in enumerate(table(d)):
            if i and c: print(f"  opponent {i:2d} -> card {c}")
    elif bytes(d[OFF_HOOK:OFF_HOOK+8]) == STOCK_HOOK and not any(d[OFF_STUB:OFF_TABLE+80]):
        print("unique drop process: not installed (stock)")
    else:
        print("unique drop process: unknown state (multi-drop variant or foreign patch?)")

def apply(d, sets, clears):
    d[OFF_HOOK:OFF_HOOK+8] = PATCH_HOOK
    d[OFF_STUB:OFF_STUB+len(STUB)] = STUB
    for s in sets:
        o, c = (int(x) for x in s.split("="))
        if not (1 <= o <= NOPP and 0 <= c <= 722): sys.exit(f"bad --set {s}")
        d[OFF_TABLE + 2*o:OFF_TABLE + 2*o + 2] = c.to_bytes(2, "little")
    for o in clears:
        d[OFF_TABLE + 2*o:OFF_TABLE + 2*o + 2] = b"\0\0"

def restore(d):
    d[OFF_HOOK:OFF_HOOK+8] = STOCK_HOOK
    d[OFF_STUB:OFF_TABLE + 2*(NOPP+1)] = bytes(OFF_TABLE + 2*(NOPP+1) - OFF_STUB)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["inspect", "apply", "restore"]); ap.add_argument("slus"); ap.add_argument("out", nargs="?")
    ap.add_argument("--set", action="append", default=[]); ap.add_argument("--clear", action="append", type=int, default=[])
    a = ap.parse_args(); d = load(a.slus)
    if a.cmd == "inspect": inspect(d); sys.exit(0)
    if not a.out: sys.exit("need an output path")
    apply(d, a.set, a.clear) if a.cmd == "apply" else restore(d)
    open(a.out, "wb").write(d); print(f"wrote {a.out}"); inspect(d)
